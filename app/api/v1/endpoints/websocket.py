"""
WebSocket endpoints for real-time progress updates.

Provides WebSocket connections for real-time communication including:
- Document processing progress updates
- Upload progress tracking
- System notifications
- Multi-user collaboration features
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status
)
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.core.dependencies import get_current_user_websocket
from app.domain.schemas.user import User
from app.services.document_processing.async_processor import AsyncDocumentProcessor
from app.services.document_processing.progress.tracker import ProgressTracker
from app.services.document_processing.storage.s3_manager import S3StorageManager


logger = logging.getLogger(__name__)  
settings = get_settings()

router = APIRouter()


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""
    type: str = Field(..., description="Message type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionRequest(BaseModel):
    """WebSocket subscription request."""
    type: str = Field(..., pattern="^subscribe$")
    user_id: str = Field(..., description="User ID for authentication")
    job_ids: List[str] = Field(default_factory=list, description="Job IDs to subscribe to")
    channels: List[str] = Field(default_factory=list, description="Channel names to subscribe to")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "subscribe",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "job_ids": ["job-123", "job-456"],
                "channels": ["progress", "notifications"]
            }
        }


class WebSocketConnection:
    """Manages individual WebSocket connection state."""
    
    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: UUID
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.subscribed_jobs: Set[UUID] = set()
        self.subscribed_channels: Set[str] = set()
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.is_active = True

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to WebSocket connection."""
        try:
            await self.websocket.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            logger.error(f"Failed to send message to connection {self.connection_id}: {e}")
            self.is_active = False
            return False

    async def send_error(self, error_message: str, error_code: str = "GENERAL_ERROR") -> None:
        """Send error message to client."""
        await self.send_message({
            "type": "error",
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_pong(self) -> None:
        """Send pong response to ping."""
        await self.send_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })


class WebSocketManager:
    """Manages all WebSocket connections and message routing."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[UUID, Set[str]] = {}
        self.job_subscriptions: Dict[UUID, Set[str]] = {}
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        
        # Dependencies
        self.progress_tracker: Optional[ProgressTracker] = None
        self.async_processor: Optional[AsyncDocumentProcessor] = None
        self.storage_manager: Optional[S3StorageManager] = None
        
        # Statistics
        self.total_connections = 0
        self.messages_sent = 0
        self.errors_count = 0

    async def initialize_dependencies(self):
        """Initialize service dependencies."""
        try:
            self.progress_tracker = ProgressTracker()
            await self.progress_tracker.initialize()
            
            self.async_processor = AsyncDocumentProcessor()
            if not self.async_processor.is_running:
                await self.async_processor.initialize()
            
            self.storage_manager = S3StorageManager()
            if not self.storage_manager._initialized:
                await self.storage_manager.initialize()
                
            logger.info("WebSocket manager dependencies initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket dependencies: {e}")
            raise

    async def connect(
        self,
        websocket: WebSocket,
        user_id: UUID
    ) -> WebSocketConnection:
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        connection_id = str(uuid4())
        connection = WebSocketConnection(websocket, connection_id, user_id)
        
        # Store connection
        self.connections[connection_id] = connection
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        self.total_connections += 1
        
        logger.info(f"WebSocket connection {connection_id} established for user {user_id}")
        
        # Send connection confirmation
        await connection.send_message({
            "type": "connected",
            "connection_id": connection_id,
            "message": "WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return connection

    async def disconnect(self, connection_id: str) -> None:
        """Handle WebSocket disconnection."""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Remove from user connections
        if connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]
        
        # Remove from job subscriptions
        for job_id in connection.subscribed_jobs:
            if job_id in self.job_subscriptions:
                self.job_subscriptions[job_id].discard(connection_id)
                if not self.job_subscriptions[job_id]:
                    del self.job_subscriptions[job_id]
        
        # Remove from channel subscriptions
        for channel in connection.subscribed_channels:
            if channel in self.channel_subscriptions:
                self.channel_subscriptions[channel].discard(connection_id)
                if not self.channel_subscriptions[channel]:
                    del self.channel_subscriptions[channel]
        
        # Remove connection
        del self.connections[connection_id]
        
        logger.info(f"WebSocket connection {connection_id} disconnected")

    async def subscribe_to_jobs(
        self,
        connection_id: str,
        job_ids: List[UUID]
    ) -> None:
        """Subscribe connection to job progress updates."""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        for job_id in job_ids:
            # Add to connection subscriptions
            connection.subscribed_jobs.add(job_id)
            
            # Add to global job subscriptions
            if job_id not in self.job_subscriptions:
                self.job_subscriptions[job_id] = set()
            self.job_subscriptions[job_id].add(connection_id)
            
            # Send current progress if available
            if self.async_processor:
                progress = await self.async_processor.get_job_status(job_id)
                if progress:
                    await connection.send_message({
                        "type": "job_progress",
                        "job_id": str(job_id),
                        "data": progress.dict(),
                        "timestamp": datetime.utcnow().isoformat()
                    })

    async def subscribe_to_channels(
        self,
        connection_id: str,
        channels: List[str]
    ) -> None:
        """Subscribe connection to specific channels."""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        for channel in channels:
            # Add to connection subscriptions
            connection.subscribed_channels.add(channel)
            
            # Add to global channel subscriptions
            if channel not in self.channel_subscriptions:
                self.channel_subscriptions[channel] = set()
            self.channel_subscriptions[channel].add(connection_id)

    async def broadcast_job_progress(
        self,
        job_id: UUID,
        progress_data: Dict[str, Any]
    ) -> None:
        """Broadcast job progress to subscribed connections."""
        if job_id not in self.job_subscriptions:
            return
        
        message = {
            "type": "job_progress", 
            "job_id": str(job_id),
            "data": progress_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all subscribed connections
        connection_ids = list(self.job_subscriptions[job_id])
        for connection_id in connection_ids:
            if connection_id in self.connections:
                success = await self.connections[connection_id].send_message(message)
                if success:
                    self.messages_sent += 1
                else:
                    self.errors_count += 1
                    # Connection failed, remove it
                    await self.disconnect(connection_id)

    async def broadcast_to_channel(
        self,
        channel: str,
        message_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Broadcast message to all connections subscribed to a channel."""
        if channel not in self.channel_subscriptions:
            return
        
        message = {
            "type": message_type,
            "channel": channel,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        connection_ids = list(self.channel_subscriptions[channel])
        for connection_id in connection_ids:
            if connection_id in self.connections:
                success = await self.connections[connection_id].send_message(message)
                if success:
                    self.messages_sent += 1
                else:
                    self.errors_count += 1
                    await self.disconnect(connection_id)

    async def send_to_user(
        self,
        user_id: UUID,
        message_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Send message to all connections of a specific user."""
        if user_id not in self.user_connections:
            return
        
        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        connection_ids = list(self.user_connections[user_id])
        for connection_id in connection_ids:
            if connection_id in self.connections:
                success = await self.connections[connection_id].send_message(message)
                if success:
                    self.messages_sent += 1
                else:
                    self.errors_count += 1
                    await self.disconnect(connection_id)

    async def handle_ping(self, connection_id: str) -> None:
        """Handle ping message from client."""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.last_ping = datetime.utcnow()
            await connection.send_pong()

    async def cleanup_stale_connections(self) -> None:
        """Clean up stale connections that haven't pinged recently."""
        current_time = datetime.utcnow()
        stale_connections = []
        
        for connection_id, connection in self.connections.items():
            time_since_ping = (current_time - connection.last_ping).total_seconds()
            if time_since_ping > 300:  # 5 minutes without ping
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            await self.disconnect(connection_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            "active_connections": len(self.connections),
            "total_connections": self.total_connections,
            "messages_sent": self.messages_sent,
            "errors_count": self.errors_count,
            "job_subscriptions": len(self.job_subscriptions),
            "channel_subscriptions": len(self.channel_subscriptions),
            "user_connections": len(self.user_connections)
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


@router.on_event("startup")
async def startup_websocket_manager():
    """Initialize WebSocket manager on startup."""
    await websocket_manager.initialize_dependencies()


@router.websocket("/progress")
async def websocket_progress_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
):
    """
    WebSocket endpoint for real-time progress updates.
    
    Clients can subscribe to job progress updates and receive real-time
    notifications about document processing status.
    """
    connection: Optional[WebSocketConnection] = None
    
    try:
        # Authenticate user
        user = await get_current_user_websocket(token)
        
        # Establish connection
        connection = await websocket_manager.connect(websocket, user.id)
        
        # Handle messages
        while True:
            try:
                # Receive message from client
                message_text = await websocket.receive_text()
                message_data = json.loads(message_text)
                
                # Validate message structure
                message_type = message_data.get("type")
                
                if message_type == "subscribe":
                    # Handle subscription request
                    try:
                        sub_request = SubscriptionRequest(**message_data)
                        
                        # Subscribe to jobs
                        if sub_request.job_ids:
                            job_uuids = [UUID(job_id) for job_id in sub_request.job_ids]
                            await websocket_manager.subscribe_to_jobs(
                                connection.connection_id,
                                job_uuids
                            )
                        
                        # Subscribe to channels
                        if sub_request.channels:
                            await websocket_manager.subscribe_to_channels(
                                connection.connection_id,
                                sub_request.channels
                            )
                        
                        # Send confirmation
                        await connection.send_message({
                            "type": "subscription_confirmed",
                            "subscribed_jobs": sub_request.job_ids,
                            "subscribed_channels": sub_request.channels,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                    except ValidationError as e:
                        await connection.send_error(
                            f"Invalid subscription request: {e}",
                            "VALIDATION_ERROR"
                        )
                
                elif message_type == "ping":
                    # Handle ping
                    await websocket_manager.handle_ping(connection.connection_id)
                
                elif message_type == "get_job_status":
                    # Handle job status request
                    job_id = message_data.get("job_id")
                    if job_id:
                        try:
                            job_uuid = UUID(job_id)
                            progress = await websocket_manager.async_processor.get_job_status(job_uuid)
                            
                            await connection.send_message({
                                "type": "job_status_response",
                                "job_id": job_id,
                                "data": progress.dict() if progress else None,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                            
                        except ValueError:
                            await connection.send_error(
                                "Invalid job ID format",
                                "INVALID_JOB_ID"
                            )
                    else:
                        await connection.send_error(
                            "job_id is required",
                            "MISSING_JOB_ID"
                        )
                
                elif message_type == "cancel_job":
                    # Handle job cancellation request
                    job_id = message_data.get("job_id")
                    if job_id:
                        try:
                            job_uuid = UUID(job_id)
                            success = await websocket_manager.async_processor.cancel_job(
                                job_uuid, 
                                user.id
                            )
                            
                            await connection.send_message({
                                "type": "job_cancel_response",
                                "job_id": job_id,
                                "success": success,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                            
                        except ValueError:
                            await connection.send_error(
                                "Invalid job ID format",
                                "INVALID_JOB_ID"
                            )
                    else:
                        await connection.send_error(
                            "job_id is required",
                            "MISSING_JOB_ID"
                        )
                
                else:
                    await connection.send_error(
                        f"Unknown message type: {message_type}",
                        "UNKNOWN_MESSAGE_TYPE"
                    )
                    
            except json.JSONDecodeError:
                await connection.send_error(
                    "Invalid JSON format",
                    "JSON_DECODE_ERROR"
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await connection.send_error(
                    "Internal error processing message",
                    "PROCESSING_ERROR"
                )
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except HTTPException as e:
        logger.warning(f"WebSocket authentication failed: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        if connection:
            await websocket_manager.disconnect(connection.connection_id)


@router.websocket("/notifications")
async def websocket_notifications_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
):
    """
    WebSocket endpoint for general notifications.
    
    Provides system-wide notifications, announcements, and
    other real-time updates not related to specific jobs.
    """
    connection: Optional[WebSocketConnection] = None
    
    try:
        # Authenticate user
        user = await get_current_user_websocket(token)
        
        # Establish connection
        connection = await websocket_manager.connect(websocket, user.id)
        
        # Auto-subscribe to user-specific notifications
        await websocket_manager.subscribe_to_channels(
            connection.connection_id,
            ["notifications", f"user_{user.id}"]
        )
        
        # Send welcome message
        await connection.send_message({
            "type": "welcome",
            "message": "Connected to notifications channel",
            "channels": ["notifications", f"user_{user.id}"],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Handle messages
        while True:
            try:
                message_text = await websocket.receive_text()
                message_data = json.loads(message_text)
                
                message_type = message_data.get("type")
                
                if message_type == "ping":
                    await websocket_manager.handle_ping(connection.connection_id)
                
                elif message_type == "subscribe_channel":
                    # Subscribe to additional channels
                    channel = message_data.get("channel")
                    if channel:
                        await websocket_manager.subscribe_to_channels(
                            connection.connection_id,
                            [channel]
                        )
                        
                        await connection.send_message({
                            "type": "channel_subscribed",
                            "channel": channel,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    else:
                        await connection.send_error(
                            "channel is required",
                            "MISSING_CHANNEL"
                        )
                
                else:
                    await connection.send_error(
                        f"Unknown message type: {message_type}",
                        "UNKNOWN_MESSAGE_TYPE"
                    )
                    
            except json.JSONDecodeError:
                await connection.send_error(
                    "Invalid JSON format",
                    "JSON_DECODE_ERROR"
                )
            except Exception as e:
                logger.error(f"Error handling notification WebSocket message: {e}")
                await connection.send_error(
                    "Internal error processing message",
                    "PROCESSING_ERROR"
                )
    
    except WebSocketDisconnect:
        logger.info("Notifications WebSocket client disconnected")
    except HTTPException as e:
        logger.warning(f"Notifications WebSocket authentication failed: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logger.error(f"Notifications WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        if connection:
            await websocket_manager.disconnect(connection.connection_id)


@router.get(
    "/stats",
    summary="WebSocket statistics",
    description="Get WebSocket connection and usage statistics"
)
async def get_websocket_stats(
    current_user: User = Depends(get_current_user)
):
    """Get WebSocket statistics and metrics."""
    try:
        stats = websocket_manager.get_stats()
        
        # Add additional runtime information
        stats.update({
            "uptime_seconds": (datetime.utcnow() - datetime.utcnow()).total_seconds(),
            "dependencies_initialized": {
                "progress_tracker": websocket_manager.progress_tracker is not None,
                "async_processor": websocket_manager.async_processor is not None,
                "storage_manager": websocket_manager.storage_manager is not None
            }
        })
        
        return {"websocket_stats": stats}
        
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve WebSocket statistics"
        )


# Background task to clean up stale connections
@router.on_event("startup")
async def start_cleanup_task():
    """Start background task for cleaning up stale connections."""
    async def cleanup_loop():
        while True:
            try:
                await websocket_manager.cleanup_stale_connections()
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                logger.error(f"Error in WebSocket cleanup loop: {e}")
                await asyncio.sleep(60)
    
    asyncio.create_task(cleanup_loop())


# Utility functions for external services to broadcast messages

async def broadcast_job_progress(job_id: UUID, progress_data: Dict[str, Any]) -> None:
    """Utility function to broadcast job progress updates."""
    await websocket_manager.broadcast_job_progress(job_id, progress_data)


async def broadcast_system_notification(message: str, notification_type: str = "info") -> None:
    """Utility function to broadcast system-wide notifications."""
    await websocket_manager.broadcast_to_channel(
        "notifications",
        "system_notification",
        {
            "message": message,
            "notification_type": notification_type
        }
    )


async def send_user_notification(
    user_id: UUID, 
    message: str, 
    notification_type: str = "info"
) -> None:
    """Utility function to send notification to specific user."""
    await websocket_manager.send_to_user(
        user_id,
        "user_notification",
        {
            "message": message,
            "notification_type": notification_type
        }
    )