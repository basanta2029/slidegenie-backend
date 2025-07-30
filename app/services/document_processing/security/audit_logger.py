"""
Security audit logging service.

Provides comprehensive security audit logging including:
- Security event tracking
- Compliance logging (GDPR, SOC2, HIPAA)
- Structured audit trails
- Real-time monitoring integration
- Log retention and archival
- Query and reporting capabilities
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import aiofiles
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.infrastructure.cache.redis import RedisClient

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Audit event type enumeration."""
    # File operations
    FILE_UPLOADED = "file_uploaded"
    FILE_SCANNED = "file_scanned"
    FILE_VALIDATED = "file_validated"
    FILE_SANITIZED = "file_sanitized"
    FILE_QUARANTINED = "file_quarantined"
    FILE_RELEASED = "file_released"
    FILE_DELETED = "file_deleted"
    
    # Security events
    THREAT_DETECTED = "threat_detected"
    VIRUS_FOUND = "virus_found"
    MALWARE_BLOCKED = "malware_blocked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    POLICY_VIOLATION = "policy_violation"
    
    # Authentication and authorization
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PERMISSION_DENIED = "permission_denied"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGE = "config_change"
    SERVICE_ERROR = "service_error"
    
    # Compliance events
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    CONSENT_GIVEN = "consent_given"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    RIGHT_TO_FORGET = "right_to_forget"


class AuditLevel(str, Enum):
    """Audit level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComplianceFramework(str, Enum):
    """Compliance framework enumeration."""
    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    NIST = "nist"


class AuditEvent(BaseModel):
    """Audit event model."""
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event identifier")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    level: AuditLevel = Field(default=AuditLevel.INFO, description="Event severity level")
    source: str = Field(default="document_processing", description="Event source system")
    component: str = Field(default="unknown", description="Component that generated the event")
    
    # Actor information
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    
    # Event details
    details: Dict[str, Any] = Field(default_factory=dict, description="Event-specific details")
    outcome: str = Field(default="success", description="Event outcome")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Context information
    file_path: Optional[str] = Field(None, description="File path if applicable")
    file_hash: Optional[str] = Field(None, description="File hash if applicable")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    organization_id: Optional[str] = Field(None, description="Organization identifier")
    
    # Compliance tags
    compliance_frameworks: List[ComplianceFramework] = Field(default_factory=list, description="Applicable compliance frameworks")
    data_classification: Optional[str] = Field(None, description="Data classification level")
    retention_period: Optional[int] = Field(None, description="Retention period in days")
    
    # Additional metadata
    correlation_id: Optional[str] = Field(None, description="Correlation identifier for related events")
    parent_event_id: Optional[str] = Field(None, description="Parent event identifier")
    risk_score: Optional[float] = Field(None, description="Risk score (0-1)")
    tags: List[str] = Field(default_factory=list, description="Event tags")


class AuditLoggerConfig(BaseModel):
    """Audit logger configuration."""
    log_level: AuditLevel = AuditLevel.INFO
    log_file_path: str = "/var/log/security/audit.log"
    structured_logging: bool = True
    real_time_alerts: bool = True
    retention_days: int = 2555  # 7 years for compliance
    max_log_size: int = 100 * 1024 * 1024  # 100MB
    backup_count: int = 10
    compress_backups: bool = True
    
    # Redis integration
    redis_enabled: bool = True
    redis_stream: str = "security_audit_log"
    redis_ttl: int = 86400 * 30  # 30 days
    
    # Compliance settings
    gdpr_enabled: bool = True
    soc2_enabled: bool = True
    encrypt_logs: bool = True
    digital_signatures: bool = False
    
    # Performance settings
    async_logging: bool = True
    batch_size: int = 100
    flush_interval: int = 5  # seconds


class SecurityAuditLogger:
    """
    Comprehensive security audit logging service.
    
    Provides structured audit logging with compliance support.
    """
    
    def __init__(
        self,
        config: Optional[AuditLoggerConfig] = None,
        redis_client: Optional[RedisClient] = None
    ):
        """Initialize security audit logger."""
        self.config = config or AuditLoggerConfig()
        self.redis_client = redis_client
        self.settings = get_settings()
        
        # Setup logging directory
        self.log_dir = Path(self.config.log_file_path).parent
        self.log_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
        
        # Initialize batch processing
        self._event_queue = asyncio.Queue(maxsize=1000)
        self._processing_task = None
        
        # Start background processing
        if self.config.async_logging:
            self._start_background_processing()
        
        logger.info(f"SecurityAuditLogger initialized - Log path: {self.config.log_file_path}")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        details: Optional[Dict[str, Any]] = None,
        level: Optional[AuditLevel] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        file_path: Optional[str] = None,
        file_hash: Optional[str] = None,
        outcome: str = "success",
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None,
        risk_score: Optional[float] = None,
        compliance_frameworks: Optional[List[ComplianceFramework]] = None,
        **kwargs
    ) -> str:
        """
        Log a security audit event.
        
        Args:
            event_type: Type of audit event
            details: Event-specific details
            level: Event severity level
            user_id: User identifier
            session_id: Session identifier
            ip_address: Client IP address
            user_agent: Client user agent
            file_path: File path if applicable
            file_hash: File hash if applicable
            outcome: Event outcome
            error_message: Error message if failed
            correlation_id: Correlation identifier
            risk_score: Risk score (0-1)
            compliance_frameworks: Applicable compliance frameworks
            **kwargs: Additional event details
            
        Returns:
            str: Event ID
        """
        # Create audit event
        event = AuditEvent(
            event_type=event_type,
            level=level or self._determine_event_level(event_type),
            details={**(details or {}), **kwargs},
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            file_path=file_path,
            file_hash=file_hash,
            outcome=outcome,
            error_message=error_message,
            correlation_id=correlation_id,
            risk_score=risk_score,
            compliance_frameworks=compliance_frameworks or self._get_default_compliance_frameworks()
        )
        
        # Add automatic compliance tags
        event = await self._enrich_compliance_data(event)
        
        # Log the event
        if self.config.async_logging:
            await self._queue_event(event)
        else:
            await self._write_event(event)
        
        # Send real-time alerts if needed
        if self._should_send_alert(event):
            await self._send_real_time_alert(event)
        
        return event.event_id
    
    async def log_file_operation(
        self,
        operation: str,
        file_path: str,
        file_hash: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict] = None,
        outcome: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """Log file operation event."""
        event_type_map = {
            "upload": AuditEventType.FILE_UPLOADED,
            "scan": AuditEventType.FILE_SCANNED,
            "validate": AuditEventType.FILE_VALIDATED,
            "sanitize": AuditEventType.FILE_SANITIZED,
            "quarantine": AuditEventType.FILE_QUARANTINED,
            "release": AuditEventType.FILE_RELEASED,
            "delete": AuditEventType.FILE_DELETED,
        }
        
        event_type = event_type_map.get(operation, AuditEventType.FILE_UPLOADED)
        
        return await self.log_event(
            event_type=event_type,
            details=details,
            user_id=user_id,
            session_id=session_id,
            file_path=file_path,
            file_hash=file_hash,
            outcome=outcome,
            error_message=error_message,
            compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2]
        )
    
    async def log_security_incident(
        self,
        incident_type: str,
        severity: AuditLevel,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        file_path: Optional[str] = None,
        threat_indicators: Optional[List[str]] = None
    ) -> str:
        """Log security incident."""
        event_details = {
            **details,
            "incident_type": incident_type,
            "threat_indicators": threat_indicators or []
        }
        
        return await self.log_event(
            event_type=AuditEventType.THREAT_DETECTED,
            level=severity,
            details=event_details,
            user_id=user_id,
            session_id=session_id,
            file_path=file_path,
            risk_score=self._calculate_risk_score(severity, incident_type),
            compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001]
        )
    
    async def log_authentication_event(
        self,
        auth_action: str,
        user_id: str,
        ip_address: str,
        user_agent: str,
        outcome: str = "success",
        failure_reason: Optional[str] = None
    ) -> str:
        """Log authentication event."""
        event_type_map = {
            "login": AuditEventType.LOGIN_ATTEMPT,
            "logout": AuditEventType.LOGOUT,
            "permission_denied": AuditEventType.PERMISSION_DENIED,
        }
        
        event_type = event_type_map.get(auth_action, AuditEventType.LOGIN_ATTEMPT)
        
        details = {
            "auth_action": auth_action,
            "failure_reason": failure_reason
        }
        
        if outcome != "success":
            details["risk_indicators"] = ["failed_authentication"]
        
        return await self.log_event(
            event_type=event_type,
            details=details,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            outcome=outcome,
            error_message=failure_reason,
            level=AuditLevel.WARNING if outcome != "success" else AuditLevel.INFO,
            compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001]
        )
    
    async def log_compliance_event(
        self,
        compliance_action: str,
        framework: ComplianceFramework,
        user_id: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> str:
        """Log compliance-related event."""
        event_type_map = {
            "data_access": AuditEventType.DATA_ACCESS,
            "data_export": AuditEventType.DATA_EXPORT,
            "data_deletion": AuditEventType.DATA_DELETION,
            "consent_given": AuditEventType.CONSENT_GIVEN,
            "consent_withdrawn": AuditEventType.CONSENT_WITHDRAWN,
            "right_to_forget": AuditEventType.RIGHT_TO_FORGET,
        }
        
        event_type = event_type_map.get(compliance_action, AuditEventType.DATA_ACCESS)
        
        return await self.log_event(
            event_type=event_type,
            details={**(details or {}), "compliance_action": compliance_action},
            user_id=user_id,
            compliance_frameworks=[framework],
            data_classification="sensitive" if framework == ComplianceFramework.GDPR else "internal"
        )
    
    async def query_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        levels: Optional[List[AuditLevel]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """Query audit events."""
        try:
            events = []
            
            # Default time range (last 24 hours)
            if start_time is None:
                start_time = datetime.utcnow() - timedelta(days=1)
            if end_time is None:
                end_time = datetime.utcnow()
            
            # Query Redis stream if available
            if self.redis_client and self.config.redis_enabled:
                events.extend(await self._query_redis_events(
                    start_time, end_time, event_types, user_id, levels, limit, offset
                ))
            
            # Query log files
            if len(events) < limit:
                file_events = await self._query_file_events(
                    start_time, end_time, event_types, user_id, levels, 
                    limit - len(events), offset
                )
                events.extend(file_events)
            
            return events[:limit]
        
        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            return []
    
    async def get_event_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        group_by: str = "event_type"
    ) -> Dict[str, Any]:
        """Get audit event statistics."""
        try:
            if start_time is None:
                start_time = datetime.utcnow() - timedelta(days=7)
            if end_time is None:
                end_time = datetime.utcnow()
            
            events = await self.query_events(
                start_time=start_time,
                end_time=end_time,
                limit=10000  # Large limit for statistics
            )
            
            stats = {
                "total_events": len(events),
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "by_type": {},
                "by_level": {},
                "by_outcome": {},
                "by_user": {},
                "risk_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0}
            }
            
            for event in events:
                # Group by type
                event_type = event.event_type.value
                stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1
                
                # Group by level
                level = event.level.value
                stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
                
                # Group by outcome
                outcome = event.outcome
                stats["by_outcome"][outcome] = stats["by_outcome"].get(outcome, 0) + 1
                
                # Group by user
                if event.user_id:
                    stats["by_user"][event.user_id] = stats["by_user"].get(event.user_id, 0) + 1
                
                # Risk distribution
                if event.risk_score is not None:
                    if event.risk_score < 0.3:
                        stats["risk_distribution"]["low"] += 1
                    elif event.risk_score < 0.6:
                        stats["risk_distribution"]["medium"] += 1
                    elif event.risk_score < 0.8:
                        stats["risk_distribution"]["high"] += 1
                    else:
                        stats["risk_distribution"]["critical"] += 1
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get event statistics: {e}")
            return {"error": str(e)}
    
    async def export_audit_log(
        self,
        start_time: datetime,
        end_time: datetime,
        format_type: str = "json",
        compliance_framework: Optional[ComplianceFramework] = None
    ) -> str:
        """Export audit log for compliance reporting."""
        try:
            events = await self.query_events(
                start_time=start_time,
                end_time=end_time,
                limit=100000  # Large limit for export
            )
            
            # Filter by compliance framework if specified
            if compliance_framework:
                events = [e for e in events if compliance_framework in e.compliance_frameworks]
            
            # Generate export
            export_data = {
                "export_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "total_events": len(events),
                    "compliance_framework": compliance_framework.value if compliance_framework else "all",
                    "format": format_type
                },
                "events": [event.dict() for event in events]
            }
            
            # Create export file
            export_filename = f"audit_export_{int(datetime.utcnow().timestamp())}.{format_type}"
            export_path = self.log_dir / "exports" / export_filename
            export_path.parent.mkdir(exist_ok=True, mode=0o750)
            
            if format_type == "json":
                async with aiofiles.open(export_path, 'w') as f:
                    await f.write(json.dumps(export_data, indent=2, default=str))
            elif format_type == "csv":
                import csv
                # Convert to CSV format
                with open(export_path, 'w', newline='') as csvfile:
                    if events:
                        fieldnames = events[0].dict().keys()
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        for event in events:
                            writer.writerow({k: str(v) for k, v in event.dict().items()})
            
            # Set appropriate permissions
            export_path.chmod(0o640)
            
            return str(export_path)
        
        except Exception as e:
            logger.error(f"Failed to export audit log: {e}")
            raise
    
    async def _queue_event(self, event: AuditEvent):
        """Queue event for batch processing."""
        try:
            await self._event_queue.put(event)
        except asyncio.QueueFull:
            logger.error("Audit event queue is full, dropping event")
            # In critical situations, write directly
            await self._write_event(event)
    
    async def _write_event(self, event: AuditEvent):
        """Write event to log file and Redis."""
        try:
            # Write to file
            await self._write_to_file(event)
            
            # Write to Redis stream
            if self.redis_client and self.config.redis_enabled:
                await self._write_to_redis(event)
        
        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")
    
    async def _write_to_file(self, event: AuditEvent):
        """Write event to log file."""
        try:
            log_entry = json.dumps(event.dict(), default=str, separators=(',', ':'))
            
            async with aiofiles.open(self.config.log_file_path, 'a') as f:
                await f.write(f"{log_entry}\n")
        
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")
    
    async def _write_to_redis(self, event: AuditEvent):
        """Write event to Redis stream."""
        try:
            event_data = event.dict()
            
            # Convert datetime objects to strings
            for key, value in event_data.items():
                if isinstance(value, datetime):
                    event_data[key] = value.isoformat()
            
            await self.redis_client.xadd(
                self.config.redis_stream,
                event_data,
                maxlen=10000  # Keep last 10k events
            )
        
        except Exception as e:
            logger.error(f"Failed to write to Redis: {e}")
    
    async def _query_redis_events(
        self,
        start_time: datetime,
        end_time: datetime,
        event_types: Optional[List[AuditEventType]],
        user_id: Optional[str],
        levels: Optional[List[AuditLevel]],
        limit: int,
        offset: int
    ) -> List[AuditEvent]:
        """Query events from Redis stream."""
        try:
            # Read from Redis stream
            messages = await self.redis_client.xrange(
                self.config.redis_stream,
                min="-",
                max="+",
                count=limit + offset
            )
            
            events = []
            for message in messages[offset:]:
                try:
                    event_data = message[1]
                    
                    # Convert string timestamps back to datetime
                    if 'timestamp' in event_data:
                        event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
                    
                    event = AuditEvent(**event_data)
                    
                    # Apply filters
                    if start_time and event.timestamp < start_time:
                        continue
                    if end_time and event.timestamp > end_time:
                        continue
                    if event_types and event.event_type not in event_types:
                        continue
                    if user_id and event.user_id != user_id:
                        continue
                    if levels and event.level not in levels:
                        continue
                    
                    events.append(event)
                
                except Exception as e:
                    logger.error(f"Failed to parse Redis event: {e}")
            
            return events
        
        except Exception as e:
            logger.error(f"Failed to query Redis events: {e}")
            return []
    
    async def _query_file_events(
        self,
        start_time: datetime,
        end_time: datetime,
        event_types: Optional[List[AuditEventType]],
        user_id: Optional[str],
        levels: Optional[List[AuditLevel]],
        limit: int,
        offset: int
    ) -> List[AuditEvent]:
        """Query events from log files."""
        try:
            events = []
            
            if not Path(self.config.log_file_path).exists():
                return events
            
            async with aiofiles.open(self.config.log_file_path, 'r') as f:
                line_count = 0
                async for line in f:
                    if line_count < offset:
                        line_count += 1
                        continue
                    
                    if len(events) >= limit:
                        break
                    
                    try:
                        event_data = json.loads(line.strip())
                        
                        # Convert timestamp
                        if 'timestamp' in event_data:
                            event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
                        
                        event = AuditEvent(**event_data)
                        
                        # Apply filters
                        if start_time and event.timestamp < start_time:
                            continue
                        if end_time and event.timestamp > end_time:
                            continue
                        if event_types and event.event_type not in event_types:
                            continue
                        if user_id and event.user_id != user_id:
                            continue
                        if levels and event.level not in levels:
                            continue
                        
                        events.append(event)
                        line_count += 1
                    
                    except Exception as e:
                        logger.error(f"Failed to parse log line: {e}")
            
            return events
        
        except Exception as e:
            logger.error(f"Failed to query file events: {e}")
            return []
    
    def _determine_event_level(self, event_type: AuditEventType) -> AuditLevel:
        """Determine appropriate log level for event type."""
        critical_events = {
            AuditEventType.VIRUS_FOUND,
            AuditEventType.MALWARE_BLOCKED,
            AuditEventType.PRIVILEGE_ESCALATION,
        }
        
        warning_events = {
            AuditEventType.THREAT_DETECTED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.POLICY_VIOLATION,
            AuditEventType.LOGIN_FAILURE,
            AuditEventType.PERMISSION_DENIED,
        }
        
        if event_type in critical_events:
            return AuditLevel.CRITICAL
        elif event_type in warning_events:
            return AuditLevel.WARNING
        else:
            return AuditLevel.INFO
    
    def _get_default_compliance_frameworks(self) -> List[ComplianceFramework]:
        """Get default compliance frameworks."""
        frameworks = []
        
        if self.config.gdpr_enabled:
            frameworks.append(ComplianceFramework.GDPR)
        if self.config.soc2_enabled:
            frameworks.append(ComplianceFramework.SOC2)
        
        return frameworks
    
    async def _enrich_compliance_data(self, event: AuditEvent) -> AuditEvent:
        """Enrich event with compliance-specific data."""
        # Add retention period based on compliance requirements
        max_retention = 0
        
        for framework in event.compliance_frameworks:
            if framework == ComplianceFramework.GDPR:
                max_retention = max(max_retention, 2555)  # 7 years
            elif framework == ComplianceFramework.SOC2:
                max_retention = max(max_retention, 1825)  # 5 years
            elif framework == ComplianceFramework.HIPAA:
                max_retention = max(max_retention, 2190)  # 6 years
        
        if max_retention > 0:
            event.retention_period = max_retention
        
        # Add data classification
        if not event.data_classification:
            if any(sensitive_event in event.event_type.value for sensitive_event in ['auth', 'login', 'user']):
                event.data_classification = "confidential"
            elif any(security_event in event.event_type.value for security_event in ['threat', 'virus', 'malware']):
                event.data_classification = "restricted"
            else:
                event.data_classification = "internal"
        
        return event
    
    def _should_send_alert(self, event: AuditEvent) -> bool:
        """Determine if event should trigger real-time alert."""
        if not self.config.real_time_alerts:
            return False
        
        alert_events = {
            AuditEventType.VIRUS_FOUND,
            AuditEventType.MALWARE_BLOCKED,
            AuditEventType.THREAT_DETECTED,
            AuditEventType.PRIVILEGE_ESCALATION,
        }
        
        return event.event_type in alert_events or event.level in [AuditLevel.ERROR, AuditLevel.CRITICAL]
    
    async def _send_real_time_alert(self, event: AuditEvent):
        """Send real-time alert for critical events."""
        try:
            # This would integrate with your alerting system
            # For now, just log at critical level
            logger.critical(f"SECURITY ALERT: {event.event_type} - {event.details}")
        
        except Exception as e:
            logger.error(f"Failed to send real-time alert: {e}")
    
    def _calculate_risk_score(self, severity: AuditLevel, incident_type: str) -> float:
        """Calculate risk score based on severity and incident type."""
        base_scores = {
            AuditLevel.DEBUG: 0.1,
            AuditLevel.INFO: 0.2,
            AuditLevel.WARNING: 0.5,
            AuditLevel.ERROR: 0.7,
            AuditLevel.CRITICAL: 0.9,
        }
        
        incident_multipliers = {
            "virus": 1.2,
            "malware": 1.2,
            "intrusion": 1.1,
            "data_breach": 1.3,
            "privilege_escalation": 1.2,
        }
        
        base_score = base_scores.get(severity, 0.5)
        multiplier = incident_multipliers.get(incident_type.lower(), 1.0)
        
        return min(1.0, base_score * multiplier)
    
    def _start_background_processing(self):
        """Start background event processing."""
        async def process_events():
            batch = []
            
            while True:
                try:
                    # Collect events in batch
                    try:
                        event = await asyncio.wait_for(
                            self._event_queue.get(),
                            timeout=self.config.flush_interval
                        )
                        batch.append(event)
                        
                        # Continue collecting until batch is full or timeout
                        while len(batch) < self.config.batch_size:
                            try:
                                event = await asyncio.wait_for(
                                    self._event_queue.get(),
                                    timeout=0.1  # Short timeout for batching
                                )
                                batch.append(event)
                            except asyncio.TimeoutError:
                                break
                    
                    except asyncio.TimeoutError:
                        pass  # Flush on timeout even if batch is not full
                    
                    # Process batch
                    if batch:
                        for event in batch:
                            await self._write_event(event)
                        batch.clear()
                
                except Exception as e:
                    logger.error(f"Background event processing failed: {e}")
                    await asyncio.sleep(1)  # Brief pause before retrying
        
        self._processing_task = asyncio.create_task(process_events())
    
    async def close(self):
        """Close audit logger and cleanup resources."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining events
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                await self._write_event(event)
            except asyncio.QueueEmpty:
                break
        
        logger.info("SecurityAuditLogger closed")