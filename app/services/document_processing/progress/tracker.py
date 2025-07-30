"""
Progress tracking system with WebSocket support.

Provides comprehensive progress tracking for async document processing
with real-time updates via WebSockets, persistent storage, and analytics.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

import redis.asyncio as redis
import websockets
from pydantic import BaseModel, Field
from websockets.exceptions import ConnectionClosed

from app.core.config import get_settings
from app.domain.schemas.document_processing import ProcessingStatus, ProcessingProgress


logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class WebSocketConnection:
    """WebSocket connection information."""
    websocket: websockets.WebSocketServerProtocol
    user_id: UUID
    job_ids: Set[UUID]
    connected_at: datetime
    last_ping: datetime


class ProgressSnapshot(BaseModel):
    """Point-in-time progress snapshot."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    job_id: UUID
    status: ProcessingStatus
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    current_step: str
    completed_steps: int
    total_steps: int
    estimated_time_remaining: Optional[float] = None
    throughput_items_per_second: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobProgressHistory(BaseModel):
    """Complete progress history for a job."""
    job_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    snapshots: List[ProgressSnapshot] = Field(default_factory=list)
    final_status: Optional[ProcessingStatus] = None
    total_processing_time: Optional[float] = None
    average_step_time: Optional[float] = None


class ProgressAnalytics(BaseModel):
    """Analytics and metrics for progress tracking."""
    total_jobs_tracked: int = 0
    active_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0
    average_processing_time: float = 0.0
    average_progress_rate: float = 0.0  # percentage per minute
    active_websocket_connections: int = 0
    total_progress_updates_sent: int = 0
    peak_concurrent_jobs: int = 0
    jobs_by_hour: Dict[str, int] = Field(default_factory=dict)


class ProgressTracker:
    """
    Comprehensive progress tracking system with real-time WebSocket updates.
    
    Features:
    - Real-time progress updates via WebSockets
    - Persistent progress history storage
    - Progress analytics and metrics
    - Multi-user support with subscription management
    - Automatic cleanup of old progress data
    - Rate limiting for progress updates
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        websocket_host: str = "localhost",
        websocket_port: int = 8765,
        progress_retention_days: int = 30
    ):
        """
        Initialize progress tracker.
        
        Args:
            redis_url: Redis connection URL for persistence
            websocket_host: WebSocket server host
            websocket_port: WebSocket server port
            progress_retention_days: Days to retain progress history
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.websocket_host = websocket_host
        self.websocket_port = websocket_port
        self.progress_retention_days = progress_retention_days
        
        # Runtime state
        self.redis_pool: Optional[redis.Redis] = None
        self.websocket_server = None
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.job_subscriptions: Dict[UUID, Set[str]] = {}  # job_id -> connection_ids
        self.active_jobs: Dict[UUID, JobProgressHistory] = {}
        self.analytics = ProgressAnalytics()
        
        # Configuration
        self.update_rate_limit = 10  # Max updates per second per job
        self.heartbeat_interval = 30  # Seconds
        self.cleanup_interval = 3600  # Seconds (1 hour)
        
        self._initialized = False
        self._background_tasks: List[asyncio.Task] = []

    async def initialize(self) -> None:
        """Initialize the progress tracking system."""
        if self._initialized:
            return
            
        logger.info("Initializing progress tracker")
        
        try:
            # Initialize Redis connection
            self.redis_pool = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
            
            # Test Redis connection
            await self.redis_pool.ping()
            
            # Start WebSocket server
            await self._start_websocket_server()
            
            # Start background tasks
            self._background_tasks = [
                asyncio.create_task(self._heartbeat_loop()),
                asyncio.create_task(self._cleanup_loop()),
                asyncio.create_task(self._analytics_update_loop())
            ]
            
            self._initialized = True
            logger.info("Progress tracker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize progress tracker: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the progress tracking system."""
        logger.info("Shutting down progress tracker")
        
        try:
            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()
            
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            # Close WebSocket connections
            if self.active_connections:
                close_tasks = [
                    conn.websocket.close() 
                    for conn in self.active_connections.values()
                ]
                await asyncio.gather(*close_tasks, return_exceptions=True)
            
            # Stop WebSocket server
            if self.websocket_server:
                self.websocket_server.close()
                await self.websocket_server.wait_closed()
            
            # Close Redis connection
            if self.redis_pool:
                await self.redis_pool.close()
            
            self._initialized = False
            
        except Exception as e:
            logger.error(f"Error during progress tracker shutdown: {e}")

    async def create_job(
        self,
        job_id: UUID,
        total_steps: int,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Create a new job for progress tracking.
        
        Args:
            job_id: Unique job identifier
            total_steps: Total number of processing steps
            user_id: User who owns the job
            metadata: Additional job metadata
        """
        logger.info(f"Creating job {job_id} for user {user_id} with {total_steps} steps")
        
        try:
            # Create job progress history
            job_history = JobProgressHistory(
                job_id=job_id,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            
            # Create initial progress snapshot
            initial_snapshot = ProgressSnapshot(
                job_id=job_id,
                status=ProcessingStatus.PENDING,
                progress_percentage=0.0,
                current_step="Initializing",
                completed_steps=0,
                total_steps=total_steps,
                metadata=metadata or {}
            )
            
            job_history.snapshots.append(initial_snapshot)
            
            # Store in memory and Redis
            self.active_jobs[job_id] = job_history
            await self._persist_job_history(job_history)
            
            # Update analytics
            self.analytics.total_jobs_tracked += 1
            self.analytics.active_jobs += 1
            self.analytics.peak_concurrent_jobs = max(
                self.analytics.peak_concurrent_jobs,
                self.analytics.active_jobs
            )
            
            # Notify subscribers
            await self._broadcast_progress_update(job_id, initial_snapshot)
            
        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {e}")
            raise

    async def update_job_progress(
        self,
        job_id: UUID,
        progress_percentage: Optional[float] = None,
        current_step: Optional[str] = None,
        completed_steps: Optional[int] = None,
        estimated_time_remaining: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update job progress.
        
        Args:
            job_id: Job identifier
            progress_percentage: Progress percentage (0-100)
            current_step: Current processing step description
            completed_steps: Number of completed steps
            estimated_time_remaining: Estimated seconds until completion
            metadata: Additional metadata
        """
        if job_id not in self.active_jobs:
            logger.warning(f"Job {job_id} not found for progress update")
            return
        
        try:
            job_history = self.active_jobs[job_id]
            last_snapshot = job_history.snapshots[-1] if job_history.snapshots else None
            
            # Apply rate limiting
            if last_snapshot and not await self._should_update_progress(job_id, last_snapshot):
                return
            
            # Create new snapshot
            snapshot = ProgressSnapshot(
                job_id=job_id,
                status=last_snapshot.status if last_snapshot else ProcessingStatus.PROCESSING,
                progress_percentage=progress_percentage or (last_snapshot.progress_percentage if last_snapshot else 0.0),
                current_step=current_step or (last_snapshot.current_step if last_snapshot else "Processing"),
                completed_steps=completed_steps or (last_snapshot.completed_steps if last_snapshot else 0),
                total_steps=last_snapshot.total_steps if last_snapshot else 1,
                estimated_time_remaining=estimated_time_remaining,
                metadata=metadata or {}
            )
            
            # Calculate throughput if possible
            if last_snapshot and completed_steps and last_snapshot.completed_steps:
                time_diff = (snapshot.timestamp - last_snapshot.timestamp).total_seconds()
                if time_diff > 0:
                    steps_diff = completed_steps - last_snapshot.completed_steps
                    snapshot.throughput_items_per_second = steps_diff / time_diff
            
            # Update job history
            job_history.snapshots.append(snapshot)
            job_history.updated_at = datetime.utcnow()
            
            # Persist to Redis
            await self._persist_job_history(job_history)
            
            # Update analytics
            self.analytics.total_progress_updates_sent += 1
            
            # Broadcast to subscribers
            await self._broadcast_progress_update(job_id, snapshot)
            
            logger.debug(f"Updated progress for job {job_id}: {snapshot.progress_percentage:.1f}%")
            
        except Exception as e:
            logger.error(f"Failed to update progress for job {job_id}: {e}")

    async def update_job_status(
        self,
        job_id: UUID,
        status: ProcessingStatus,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update job status.
        
        Args:
            job_id: Job identifier
            status: New processing status
            message: Status message or error description
            metadata: Additional metadata
        """
        if job_id not in self.active_jobs:
            logger.warning(f"Job {job_id} not found for status update")
            return
        
        try:
            job_history = self.active_jobs[job_id]
            last_snapshot = job_history.snapshots[-1] if job_history.snapshots else None
            
            # Create status update snapshot
            snapshot = ProgressSnapshot(
                job_id=job_id,
                status=status,
                progress_percentage=100.0 if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED] else (last_snapshot.progress_percentage if last_snapshot else 0.0),
                current_step=message or status.value.title(),
                completed_steps=last_snapshot.completed_steps if last_snapshot else 0,
                total_steps=last_snapshot.total_steps if last_snapshot else 1,
                error_message=message if status == ProcessingStatus.FAILED else None,
                metadata=metadata or {}
            )
            
            # Update job history
            job_history.snapshots.append(snapshot)
            job_history.updated_at = datetime.utcnow()
            
            # Handle job completion
            if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                job_history.final_status = status
                
                # Calculate total processing time
                if job_history.snapshots:
                    start_time = job_history.snapshots[0].timestamp
                    end_time = snapshot.timestamp
                    job_history.total_processing_time = (end_time - start_time).total_seconds()
                    
                    # Calculate average step time
                    if len(job_history.snapshots) > 1:
                        job_history.average_step_time = job_history.total_processing_time / len(job_history.snapshots)
                
                # Update analytics
                self.analytics.active_jobs -= 1
                if status == ProcessingStatus.COMPLETED:
                    self.analytics.completed_jobs += 1
                elif status == ProcessingStatus.FAILED:
                    self.analytics.failed_jobs += 1
                elif status == ProcessingStatus.CANCELLED:
                    self.analytics.cancelled_jobs += 1
                
                # Update average processing time
                if job_history.total_processing_time:
                    self._update_average_processing_time(job_history.total_processing_time)
                
                # Remove from active jobs
                del self.active_jobs[job_id]
            
            # Persist to Redis
            await self._persist_job_history(job_history)
            
            # Broadcast to subscribers
            await self._broadcast_progress_update(job_id, snapshot)
            
            logger.info(f"Updated status for job {job_id}: {status.value}")
            
        except Exception as e:
            logger.error(f"Failed to update status for job {job_id}: {e}")

    async def get_job_progress(self, job_id: UUID) -> Optional[ProcessingProgress]:
        """
        Get current progress for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            ProcessingProgress or None if job not found
        """
        try:
            # Check active jobs first
            if job_id in self.active_jobs:
                job_history = self.active_jobs[job_id]
                if job_history.snapshots:
                    snapshot = job_history.snapshots[-1]
                    return ProcessingProgress(
                        job_id=job_id,
                        status=snapshot.status,
                        progress_percentage=snapshot.progress_percentage,
                        current_step=snapshot.current_step,
                        total_steps=snapshot.total_steps,
                        completed_steps=snapshot.completed_steps,
                        estimated_time_remaining=snapshot.estimated_time_remaining,
                        error_message=snapshot.error_message,
                        started_at=job_history.created_at,
                        updated_at=snapshot.timestamp
                    )
            
            # Check Redis for completed jobs
            job_data = await self.redis_pool.get(f"job_history:{job_id}")
            if job_data:
                job_history = JobProgressHistory(**json.loads(job_data))
                if job_history.snapshots:
                    snapshot = job_history.snapshots[-1]
                    return ProcessingProgress(
                        job_id=job_id,
                        status=snapshot.status,
                        progress_percentage=snapshot.progress_percentage,
                        current_step=snapshot.current_step,
                        total_steps=snapshot.total_steps,
                        completed_steps=snapshot.completed_steps,
                        estimated_time_remaining=snapshot.estimated_time_remaining,
                        error_message=snapshot.error_message,
                        started_at=job_history.created_at,
                        updated_at=snapshot.timestamp
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get progress for job {job_id}: {e}")
            return None

    async def subscribe_to_job(
        self,
        websocket: websockets.WebSocketServerProtocol,
        user_id: UUID,
        job_ids: List[UUID]
    ) -> str:
        """
        Subscribe WebSocket connection to job progress updates.
        
        Args:
            websocket: WebSocket connection
            user_id: User identifier
            job_ids: List of job IDs to subscribe to
            
        Returns:
            Connection ID for managing the subscription
        """
        connection_id = str(uuid4())
        
        try:
            # Create connection record
            connection = WebSocketConnection(
                websocket=websocket,
                user_id=user_id,
                job_ids=set(job_ids),
                connected_at=datetime.utcnow(),
                last_ping=datetime.utcnow()
            )
            
            self.active_connections[connection_id] = connection
            
            # Update job subscriptions
            for job_id in job_ids:
                if job_id not in self.job_subscriptions:
                    self.job_subscriptions[job_id] = set()
                self.job_subscriptions[job_id].add(connection_id)
            
            # Update analytics
            self.analytics.active_websocket_connections += 1
            
            # Send current progress for subscribed jobs
            for job_id in job_ids:
                progress = await self.get_job_progress(job_id)
                if progress:
                    await self._send_to_connection(connection_id, {
                        "type": "progress_update",
                        "job_id": str(job_id),
                        "data": progress.dict()
                    })
            
            logger.info(f"WebSocket connection {connection_id} subscribed to {len(job_ids)} jobs")
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe connection {connection_id}: {e}")
            raise

    async def unsubscribe_connection(self, connection_id: str) -> None:
        """Unsubscribe a WebSocket connection."""
        if connection_id not in self.active_connections:
            return
        
        try:
            connection = self.active_connections[connection_id]
            
            # Remove from job subscriptions
            for job_id in connection.job_ids:
                if job_id in self.job_subscriptions:
                    self.job_subscriptions[job_id].discard(connection_id)
                    if not self.job_subscriptions[job_id]:
                        del self.job_subscriptions[job_id]
            
            # Remove connection
            del self.active_connections[connection_id]
            
            # Update analytics
            self.analytics.active_websocket_connections -= 1
            
            logger.info(f"Unsubscribed connection {connection_id}")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe connection {connection_id}: {e}")

    async def get_analytics(self) -> ProgressAnalytics:
        """Get comprehensive progress tracking analytics."""
        return self.analytics

    async def get_job_history(
        self,
        job_id: UUID,
        include_snapshots: bool = True
    ) -> Optional[JobProgressHistory]:
        """
        Get complete job history.
        
        Args:
            job_id: Job identifier
            include_snapshots: Whether to include progress snapshots
            
        Returns:
            JobProgressHistory or None if not found
        """
        try:
            # Check active jobs first
            if job_id in self.active_jobs:
                job_history = self.active_jobs[job_id]
                if not include_snapshots:
                    job_history.snapshots = []
                return job_history
            
            # Check Redis
            job_data = await self.redis_pool.get(f"job_history:{job_id}")
            if job_data:
                job_history = JobProgressHistory(**json.loads(job_data))
                if not include_snapshots:
                    job_history.snapshots = []
                return job_history
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get job history for {job_id}: {e}")
            return None

    async def _start_websocket_server(self) -> None:
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on {self.websocket_host}:{self.websocket_port}")
        
        self.websocket_server = await websockets.serve(
            self._handle_websocket_connection,
            self.websocket_host,
            self.websocket_port
        )

    async def _handle_websocket_connection(
        self,
        websocket: websockets.WebSocketServerProtocol,
        path: str
    ) -> None:
        """Handle new WebSocket connection."""
        connection_id = None
        
        try:
            # Wait for subscription message
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get("type") == "subscribe":
                user_id = UUID(data["user_id"])
                job_ids = [UUID(jid) for jid in data["job_ids"]]
                
                connection_id = await self.subscribe_to_job(websocket, user_id, job_ids)
                
                # Send confirmation
                await websocket.send(json.dumps({
                    "type": "subscription_confirmed",
                    "connection_id": connection_id
                }))
                
                # Keep connection alive
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "ping":
                            await websocket.send(json.dumps({"type": "pong"}))
                            if connection_id in self.active_connections:
                                self.active_connections[connection_id].last_ping = datetime.utcnow()
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from connection {connection_id}")
                    except Exception as e:
                        logger.error(f"Error handling message from {connection_id}: {e}")
                        break
            
        except ConnectionClosed:
            logger.info(f"Connection {connection_id} closed")
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {e}")
        finally:
            if connection_id:
                await self.unsubscribe_connection(connection_id)

    async def _broadcast_progress_update(
        self,
        job_id: UUID,
        snapshot: ProgressSnapshot
    ) -> None:
        """Broadcast progress update to subscribed connections."""
        if job_id not in self.job_subscriptions:
            return
        
        message = {
            "type": "progress_update",
            "job_id": str(job_id),
            "data": {
                "status": snapshot.status.value,
                "progress_percentage": snapshot.progress_percentage,
                "current_step": snapshot.current_step,
                "completed_steps": snapshot.completed_steps,
                "total_steps": snapshot.total_steps,
                "estimated_time_remaining": snapshot.estimated_time_remaining,
                "throughput_items_per_second": snapshot.throughput_items_per_second,
                "error_message": snapshot.error_message,
                "timestamp": snapshot.timestamp.isoformat(),
                "metadata": snapshot.metadata
            }
        }
        
        # Send to all subscribed connections
        connection_ids = list(self.job_subscriptions[job_id])
        for connection_id in connection_ids:
            await self._send_to_connection(connection_id, message)

    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> None:
        """Send message to a specific WebSocket connection."""
        if connection_id not in self.active_connections:
            return
        
        try:
            connection = self.active_connections[connection_id]
            await connection.websocket.send(json.dumps(message))
        except ConnectionClosed:
            await self.unsubscribe_connection(connection_id)
        except Exception as e:
            logger.error(f"Failed to send message to connection {connection_id}: {e}")
            await self.unsubscribe_connection(connection_id)

    async def _persist_job_history(self, job_history: JobProgressHistory) -> None:
        """Persist job history to Redis."""
        try:
            key = f"job_history:{job_history.job_id}"
            data = job_history.json()
            
            # Set with expiration
            expiration_seconds = self.progress_retention_days * 24 * 3600
            await self.redis_pool.setex(key, expiration_seconds, data)
            
        except Exception as e:
            logger.error(f"Failed to persist job history {job_history.job_id}: {e}")

    async def _should_update_progress(
        self,
        job_id: UUID,
        last_snapshot: ProgressSnapshot
    ) -> bool:
        """Check if progress should be updated based on rate limiting."""
        time_since_last = (datetime.utcnow() - last_snapshot.timestamp).total_seconds()
        min_interval = 1.0 / self.update_rate_limit
        
        return time_since_last >= min_interval

    async def _heartbeat_loop(self) -> None:
        """Background loop for WebSocket heartbeat."""
        while True:
            try:
                current_time = datetime.utcnow()
                stale_connections = []
                
                for connection_id, connection in self.active_connections.items():
                    time_since_ping = (current_time - connection.last_ping).total_seconds()
                    
                    if time_since_ping > self.heartbeat_interval * 2:
                        stale_connections.append(connection_id)
                    elif time_since_ping > self.heartbeat_interval:
                        # Send ping
                        await self._send_to_connection(connection_id, {"type": "ping"})
                
                # Clean up stale connections
                for connection_id in stale_connections:
                    await self.unsubscribe_connection(connection_id)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _cleanup_loop(self) -> None:
        """Background loop for cleaning up old data."""
        while True:
            try:
                cutoff_time = datetime.utcnow() - timedelta(days=self.progress_retention_days)
                
                # Clean up old job histories from Redis
                # This is a simplified cleanup - in production, you'd want to scan keys
                
                await asyncio.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)

    async def _analytics_update_loop(self) -> None:
        """Background loop for updating analytics."""
        while True:
            try:
                # Update jobs by hour
                current_hour = datetime.utcnow().strftime("%Y-%m-%d %H:00")
                if current_hour not in self.analytics.jobs_by_hour:
                    self.analytics.jobs_by_hour[current_hour] = 0
                
                # Keep only last 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.analytics.jobs_by_hour = {
                    hour: count for hour, count in self.analytics.jobs_by_hour.items()
                    if datetime.strptime(hour, "%Y-%m-%d %H:00") > cutoff_time
                }
                
                await asyncio.sleep(3600)  # Update every hour
                
            except Exception as e:
                logger.error(f"Error in analytics update loop: {e}")
                await asyncio.sleep(3600)

    def _update_average_processing_time(self, processing_time: float) -> None:
        """Update average processing time metric."""
        if self.analytics.average_processing_time == 0:
            self.analytics.average_processing_time = processing_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.analytics.average_processing_time = (
                alpha * processing_time + 
                (1 - alpha) * self.analytics.average_processing_time
            )