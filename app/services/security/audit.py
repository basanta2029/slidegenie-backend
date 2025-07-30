"""
Audit logging service for SlideGenie authentication system.

Provides comprehensive security event logging:
- Authentication events (login, logout, failed attempts)
- Authorization events (permission changes, access denied)
- Security events (suspicious activity, attacks)
- Administrative actions (user management, settings changes)
- Data access logging
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.cache.redis import RedisCache, get_redis

logger = get_logger(__name__)


class SecurityEvent(str, Enum):
    """Security event types for audit logging."""
    
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"
    
    # Registration events
    REGISTRATION_SUCCESS = "registration_success"
    REGISTRATION_FAILURE = "registration_failure"
    EMAIL_VERIFICATION = "email_verification"
    
    # Password events
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_SUCCESS = "password_reset_success"
    PASSWORD_CHANGE = "password_change"
    
    # OAuth events
    OAUTH_LOGIN_ATTEMPT = "oauth_login_attempt"
    OAUTH_LOGIN_SUCCESS = "oauth_login_success"
    OAUTH_LOGIN_FAILURE = "oauth_login_failure"
    OAUTH_ACCOUNT_LINKED = "oauth_account_linked"
    
    # Security events
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Authorization events
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    FORBIDDEN_ACCESS = "forbidden_access"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    
    # API key events
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_USED = "api_key_used"
    INVALID_API_KEY = "invalid_api_key"
    
    # Administrative events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_SUSPENDED = "user_suspended"
    USER_ACTIVATED = "user_activated"
    
    # Data access events
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    
    # System events
    SECURITY_CONFIG_CHANGED = "security_config_changed"
    SYSTEM_ERROR = "system_error"
    SUSPICIOUS_REQUEST = "suspicious_request"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogEntry:
    """Represents an audit log entry."""
    
    def __init__(
        self,
        event: SecurityEvent,
        severity: AuditSeverity,
        timestamp: datetime,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.event = event
        self.severity = severity
        self.timestamp = timestamp
        self.user_id = user_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.session_id = session_id
        self.request_id = request_id
        self.details = details or {}
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "event": self.event.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "details": self.details,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Comprehensive audit logging service.
    
    Features:
    - Structured security event logging
    - Real-time event streaming
    - Event aggregation and analytics
    - Compliance reporting
    - Retention policies
    - Search and filtering
    """
    
    # Event severity mapping
    EVENT_SEVERITY_MAP = {
        SecurityEvent.LOGIN_SUCCESS: AuditSeverity.INFO,
        SecurityEvent.LOGIN_FAILURE: AuditSeverity.WARNING,
        SecurityEvent.LOGOUT: AuditSeverity.INFO,
        SecurityEvent.TOKEN_REFRESH: AuditSeverity.INFO,
        SecurityEvent.TOKEN_REVOKED: AuditSeverity.WARNING,
        SecurityEvent.REGISTRATION_SUCCESS: AuditSeverity.INFO,
        SecurityEvent.REGISTRATION_FAILURE: AuditSeverity.WARNING,
        SecurityEvent.EMAIL_VERIFICATION: AuditSeverity.INFO,
        SecurityEvent.PASSWORD_RESET_REQUEST: AuditSeverity.INFO,
        SecurityEvent.PASSWORD_RESET_SUCCESS: AuditSeverity.INFO,
        SecurityEvent.PASSWORD_CHANGE: AuditSeverity.WARNING,
        SecurityEvent.OAUTH_LOGIN_ATTEMPT: AuditSeverity.INFO,
        SecurityEvent.OAUTH_LOGIN_SUCCESS: AuditSeverity.INFO,
        SecurityEvent.OAUTH_LOGIN_FAILURE: AuditSeverity.WARNING,
        SecurityEvent.OAUTH_ACCOUNT_LINKED: AuditSeverity.INFO,
        SecurityEvent.ACCOUNT_LOCKED: AuditSeverity.ERROR,
        SecurityEvent.ACCOUNT_UNLOCKED: AuditSeverity.WARNING,
        SecurityEvent.SUSPICIOUS_ACTIVITY: AuditSeverity.ERROR,
        SecurityEvent.BRUTE_FORCE_DETECTED: AuditSeverity.CRITICAL,
        SecurityEvent.RATE_LIMIT_EXCEEDED: AuditSeverity.WARNING,
        SecurityEvent.UNAUTHORIZED_ACCESS: AuditSeverity.ERROR,
        SecurityEvent.FORBIDDEN_ACCESS: AuditSeverity.ERROR,
        SecurityEvent.PERMISSION_GRANTED: AuditSeverity.INFO,
        SecurityEvent.PERMISSION_REVOKED: AuditSeverity.WARNING,
        SecurityEvent.ROLE_ASSIGNED: AuditSeverity.INFO,
        SecurityEvent.ROLE_REMOVED: AuditSeverity.WARNING,
        SecurityEvent.API_KEY_CREATED: AuditSeverity.INFO,
        SecurityEvent.API_KEY_REVOKED: AuditSeverity.WARNING,
        SecurityEvent.API_KEY_USED: AuditSeverity.INFO,
        SecurityEvent.INVALID_API_KEY: AuditSeverity.ERROR,
        SecurityEvent.USER_CREATED: AuditSeverity.INFO,
        SecurityEvent.USER_UPDATED: AuditSeverity.INFO,
        SecurityEvent.USER_DELETED: AuditSeverity.WARNING,
        SecurityEvent.USER_SUSPENDED: AuditSeverity.WARNING,
        SecurityEvent.USER_ACTIVATED: AuditSeverity.INFO,
        SecurityEvent.SENSITIVE_DATA_ACCESS: AuditSeverity.WARNING,
        SecurityEvent.DATA_EXPORT: AuditSeverity.WARNING,
        SecurityEvent.DATA_DELETION: AuditSeverity.WARNING,
        SecurityEvent.SECURITY_CONFIG_CHANGED: AuditSeverity.CRITICAL,
        SecurityEvent.SYSTEM_ERROR: AuditSeverity.ERROR,
        SecurityEvent.SUSPICIOUS_REQUEST: AuditSeverity.ERROR,
    }
    
    def __init__(
        self,
        cache: Optional[RedisCache] = None,
        retention_days: int = 90,
        enable_streaming: bool = True,
        batch_size: int = 100,
    ):
        """
        Initialize audit logger.
        
        Args:
            cache: Redis cache instance
            retention_days: Days to retain audit logs
            enable_streaming: Enable real-time event streaming
            batch_size: Batch size for bulk operations
        """
        self.cache = cache or RedisCache(prefix="audit")
        self.retention_days = retention_days
        self.enable_streaming = enable_streaming
        self.batch_size = batch_size
        
        # Stream key for real-time events
        self.stream_key = "audit:stream"
        
        # Index keys for efficient querying
        self.index_keys = {
            "user": "audit:index:user",
            "event": "audit:index:event",
            "severity": "audit:index:severity",
            "ip": "audit:index:ip",
            "date": "audit:index:date",
        }
    
    async def log_event(
        self,
        event: SecurityEvent,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: Optional[AuditSeverity] = None,
    ) -> str:
        """
        Log a security event.
        
        Args:
            event: Security event type
            user_id: User identifier
            ip_address: Client IP address
            user_agent: Client user agent
            session_id: Session identifier
            request_id: Request identifier
            details: Event-specific details
            metadata: Additional metadata
            severity: Override default severity
            
        Returns:
            Log entry ID
        """
        # Determine severity
        if severity is None:
            severity = self.EVENT_SEVERITY_MAP.get(event, AuditSeverity.INFO)
        
        # Create log entry
        entry = AuditLogEntry(
            event=event,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            request_id=request_id,
            details=details,
            metadata=metadata,
        )
        
        # Generate unique ID
        entry_id = f"{int(entry.timestamp.timestamp() * 1000000)}:{event.value}"
        
        try:
            client = await get_redis()
            
            # Store the log entry
            entry_key = f"entry:{entry_id}"
            entry_data = entry.to_json()
            
            # Use pipeline for atomic operations
            async with client.pipeline() as pipe:
                # Store the entry
                pipe.setex(
                    entry_key,
                    self.retention_days * 86400,
                    entry_data,
                )
                
                # Update indexes
                await self._update_indexes(pipe, entry, entry_id)
                
                # Stream the event if enabled
                if self.enable_streaming:
                    pipe.xadd(
                        self.stream_key,
                        {"data": entry_data},
                        maxlen=10000,  # Keep last 10k events in stream
                    )
                
                await pipe.execute()
            
            # Log to application logger based on severity
            log_message = f"Audit: {event.value}"
            if user_id:
                log_message += f" | User: {user_id}"
            if ip_address:
                log_message += f" | IP: {ip_address}"
            
            if severity == AuditSeverity.CRITICAL:
                logger.critical(log_message, extra={"audit_entry": entry.to_dict()})
            elif severity == AuditSeverity.ERROR:
                logger.error(log_message, extra={"audit_entry": entry.to_dict()})
            elif severity == AuditSeverity.WARNING:
                logger.warning(log_message, extra={"audit_entry": entry.to_dict()})
            else:
                logger.info(log_message, extra={"audit_entry": entry.to_dict()})
            
            return entry_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Still log to application logger
            logger.error(f"Audit (fallback): {event.value}", extra={"audit_entry": entry.to_dict()})
            return entry_id
    
    async def _update_indexes(
        self,
        pipe,
        entry: AuditLogEntry,
        entry_id: str,
    ) -> None:
        """
        Update search indexes for the log entry.
        
        Args:
            pipe: Redis pipeline
            entry: Log entry
            entry_id: Entry ID
        """
        timestamp = entry.timestamp.timestamp()
        
        # User index
        if entry.user_id:
            pipe.zadd(f"{self.index_keys['user']}:{entry.user_id}", {entry_id: timestamp})
            pipe.expire(f"{self.index_keys['user']}:{entry.user_id}", self.retention_days * 86400)
        
        # Event type index
        pipe.zadd(f"{self.index_keys['event']}:{entry.event.value}", {entry_id: timestamp})
        pipe.expire(f"{self.index_keys['event']}:{entry.event.value}", self.retention_days * 86400)
        
        # Severity index
        pipe.zadd(f"{self.index_keys['severity']}:{entry.severity.value}", {entry_id: timestamp})
        pipe.expire(f"{self.index_keys['severity']}:{entry.severity.value}", self.retention_days * 86400)
        
        # IP address index
        if entry.ip_address:
            pipe.zadd(f"{self.index_keys['ip']}:{entry.ip_address}", {entry_id: timestamp})
            pipe.expire(f"{self.index_keys['ip']}:{entry.ip_address}", self.retention_days * 86400)
        
        # Date index (daily buckets)
        date_key = entry.timestamp.strftime("%Y-%m-%d")
        pipe.zadd(f"{self.index_keys['date']}:{date_key}", {entry_id: timestamp})
        pipe.expire(f"{self.index_keys['date']}:{date_key}", self.retention_days * 86400)
    
    async def query_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[SecurityEvent] = None,
        severity: Optional[AuditSeverity] = None,
        ip_address: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            severity: Filter by severity
            ip_address: Filter by IP address
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results
            offset: Result offset
            
        Returns:
            List of matching log entries
        """
        try:
            client = await get_redis()
            
            # Build query keys
            query_keys = []
            
            if user_id:
                query_keys.append(f"{self.index_keys['user']}:{user_id}")
            if event_type:
                query_keys.append(f"{self.index_keys['event']}:{event_type.value}")
            if severity:
                query_keys.append(f"{self.index_keys['severity']}:{severity.value}")
            if ip_address:
                query_keys.append(f"{self.index_keys['ip']}:{ip_address}")
            
            # Date range query
            if start_date or end_date:
                date_keys = await self._get_date_range_keys(start_date, end_date)
                query_keys.extend(date_keys)
            
            if not query_keys:
                # No filters, get recent entries
                query_keys.append(f"{self.index_keys['date']}:{datetime.utcnow().strftime('%Y-%m-%d')}")
            
            # Perform intersection of indexes
            if len(query_keys) == 1:
                # Single index query
                entry_ids = await client.zrevrange(
                    query_keys[0],
                    offset,
                    offset + limit - 1,
                )
            else:
                # Multi-index intersection
                temp_key = f"temp:query:{time.time()}"
                await client.zinterstore(temp_key, query_keys)
                await client.expire(temp_key, 60)  # Cleanup after 1 minute
                
                entry_ids = await client.zrevrange(
                    temp_key,
                    offset,
                    offset + limit - 1,
                )
                
                await client.delete(temp_key)
            
            # Fetch log entries
            entries = []
            if entry_ids:
                entry_keys = [f"entry:{entry_id}" for entry_id in entry_ids]
                entry_data = await client.mget(entry_keys)
                
                for data in entry_data:
                    if data:
                        try:
                            entries.append(json.loads(data))
                        except json.JSONDecodeError:
                            continue
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return []
    
    async def _get_date_range_keys(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[str]:
        """
        Get date index keys for date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of date index keys
        """
        keys = []
        
        start = start_date or datetime.utcnow() - timedelta(days=7)
        end = end_date or datetime.utcnow()
        
        current = start
        while current <= end:
            date_key = current.strftime("%Y-%m-%d")
            keys.append(f"{self.index_keys['date']}:{date_key}")
            current += timedelta(days=1)
        
        return keys
    
    async def get_user_activity(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get user activity summary.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            limit: Maximum events to return
            
        Returns:
            User activity summary
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query user events
        events = await self.query_logs(
            user_id=user_id,
            start_date=start_date,
            limit=limit,
        )
        
        # Analyze events
        summary = {
            "user_id": user_id,
            "period_days": days,
            "total_events": len(events),
            "events_by_type": {},
            "events_by_severity": {},
            "recent_events": events[:10],
            "login_count": 0,
            "failed_login_count": 0,
            "last_login": None,
            "suspicious_activity": False,
        }
        
        for event in events:
            # Count by type
            event_type = event.get("event")
            if event_type:
                summary["events_by_type"][event_type] = \
                    summary["events_by_type"].get(event_type, 0) + 1
            
            # Count by severity
            severity = event.get("severity")
            if severity:
                summary["events_by_severity"][severity] = \
                    summary["events_by_severity"].get(severity, 0) + 1
            
            # Track specific events
            if event_type == SecurityEvent.LOGIN_SUCCESS.value:
                summary["login_count"] += 1
                if not summary["last_login"]:
                    summary["last_login"] = event.get("timestamp")
            elif event_type == SecurityEvent.LOGIN_FAILURE.value:
                summary["failed_login_count"] += 1
            elif event_type in [
                SecurityEvent.SUSPICIOUS_ACTIVITY.value,
                SecurityEvent.BRUTE_FORCE_DETECTED.value,
                SecurityEvent.ACCOUNT_LOCKED.value,
            ]:
                summary["suspicious_activity"] = True
        
        return summary
    
    async def get_security_metrics(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get security metrics for monitoring.
        
        Args:
            hours: Hours to analyze
            
        Returns:
            Security metrics
        """
        start_date = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = {
            "period_hours": hours,
            "total_events": 0,
            "failed_logins": 0,
            "successful_logins": 0,
            "account_lockouts": 0,
            "suspicious_activities": 0,
            "rate_limit_hits": 0,
            "unique_users": set(),
            "unique_ips": set(),
            "critical_events": [],
        }
        
        # Query recent events
        for severity in [AuditSeverity.CRITICAL, AuditSeverity.ERROR, AuditSeverity.WARNING]:
            events = await self.query_logs(
                severity=severity,
                start_date=start_date,
                limit=1000,
            )
            
            for event in events:
                metrics["total_events"] += 1
                
                event_type = event.get("event")
                if event_type == SecurityEvent.LOGIN_FAILURE.value:
                    metrics["failed_logins"] += 1
                elif event_type == SecurityEvent.LOGIN_SUCCESS.value:
                    metrics["successful_logins"] += 1
                elif event_type == SecurityEvent.ACCOUNT_LOCKED.value:
                    metrics["account_lockouts"] += 1
                elif event_type == SecurityEvent.SUSPICIOUS_ACTIVITY.value:
                    metrics["suspicious_activities"] += 1
                elif event_type == SecurityEvent.RATE_LIMIT_EXCEEDED.value:
                    metrics["rate_limit_hits"] += 1
                
                if event.get("user_id"):
                    metrics["unique_users"].add(event["user_id"])
                if event.get("ip_address"):
                    metrics["unique_ips"].add(event["ip_address"])
                
                if severity == AuditSeverity.CRITICAL:
                    metrics["critical_events"].append(event)
        
        # Convert sets to counts
        metrics["unique_users"] = len(metrics["unique_users"])
        metrics["unique_ips"] = len(metrics["unique_ips"])
        
        return metrics
    
    async def stream_events(
        self,
        callback: Callable,
        event_filter: Optional[Set[SecurityEvent]] = None,
    ) -> None:
        """
        Stream audit events in real-time.
        
        Args:
            callback: Async callback function for events
            event_filter: Set of event types to filter
        """
        if not self.enable_streaming:
            logger.warning("Event streaming is disabled")
            return
        
        try:
            client = await get_redis()
            last_id = "$"  # Start from latest
            
            while True:
                # Read from stream
                events = await client.xread(
                    {self.stream_key: last_id},
                    block=1000,  # 1 second timeout
                    count=10,
                )
                
                if events:
                    for stream_name, stream_events in events:
                        for event_id, event_data in stream_events:
                            try:
                                entry = json.loads(event_data[b"data"])
                                
                                # Apply filter if specified
                                if event_filter:
                                    event_type = entry.get("event")
                                    if event_type not in [e.value for e in event_filter]:
                                        continue
                                
                                # Call the callback
                                await callback(entry)
                                
                                last_id = event_id
                            except Exception as e:
                                logger.error(f"Error processing stream event: {e}")
                
                await asyncio.sleep(0.1)  # Small delay
                
        except Exception as e:
            logger.error(f"Stream events error: {e}")


# Create default audit logger instance
audit_logger = AuditLogger(
    retention_days=90,
    enable_streaming=True,
)