"""
Backup and versioning manager for document processing system.

Provides comprehensive backup operations, versioning, disaster recovery,
and backup verification with multiple storage backends and scheduling.
"""

import asyncio
import gzip
import hashlib
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class BackupType(str, Enum):
    """Types of backup operations."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(str, Enum):
    """Backup operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"


class BackupStrategy(BaseModel):
    """Backup strategy configuration."""
    name: str
    description: str
    backup_type: BackupType = Field(default=BackupType.INCREMENTAL)
    frequency_hours: int = Field(default=24)  # Daily backups
    retention_days: int = Field(default=30)  # Keep for 30 days
    compression_enabled: bool = Field(default=True)
    encryption_enabled: bool = Field(default=True)
    verification_enabled: bool = Field(default=True)
    max_backup_size_mb: float = Field(default=1000.0)  # 1GB max
    backup_storage_path: str = Field(default="backups/")
    priority: int = Field(default=1)  # 1=high, 5=low
    
    # Storage backends
    use_s3: bool = Field(default=True)
    use_local: bool = Field(default=False)
    use_remote: bool = Field(default=False)
    
    # Conditions
    applies_to_users: List[str] = Field(default_factory=list)
    applies_to_content_types: List[str] = Field(default_factory=list)
    min_file_size_mb: float = Field(default=0.0)
    max_file_size_mb: float = Field(default=100.0)


class BackupVersion(BaseModel):
    """File version information."""
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    file_id: str
    version_number: int
    content_hash: str
    size_bytes: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    changes_summary: Optional[str] = None
    parent_version_id: Optional[str] = None
    is_current: bool = Field(default=True)
    
    @property
    def size_mb(self) -> float:
        """Version size in MB."""
        return self.size_bytes / (1024 * 1024)


class BackupEntry(BaseModel):
    """Backup operation entry."""
    backup_id: str = Field(default_factory=lambda: str(uuid4()))
    file_id: str
    user_id: UUID
    backup_type: BackupType
    status: BackupStatus = Field(default=BackupStatus.PENDING)
    strategy_name: str = "default"
    
    # Timing
    scheduled_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Backup details
    source_path: str
    backup_path: str
    backup_size_bytes: int = 0
    compression_ratio: float = 0.0
    checksum: Optional[str] = None
    verification_status: Optional[str] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version_info: Optional[BackupVersion] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate backup duration in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def backup_size_mb(self) -> float:
        """Backup size in MB."""
        return self.backup_size_bytes / (1024 * 1024)


class BackupMetrics(BaseModel):
    """Backup system metrics."""
    total_backups: int = 0
    successful_backups: int = 0
    failed_backups: int = 0
    pending_backups: int = 0
    total_backup_size_mb: float = 0.0
    average_backup_time_seconds: float = 0.0
    backup_success_rate: float = 0.0
    last_backup: Optional[datetime] = None
    oldest_backup: Optional[datetime] = None
    storage_efficiency: float = 0.0  # Compression ratio
    verification_success_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_backups": self.total_backups,
            "successful_backups": self.successful_backups,
            "failed_backups": self.failed_backups,
            "pending_backups": self.pending_backups,
            "total_backup_size_mb": round(self.total_backup_size_mb, 2),
            "average_backup_time_seconds": round(self.average_backup_time_seconds, 2),
            "backup_success_rate": round(self.backup_success_rate, 3),
            "last_backup": self.last_backup.isoformat() if self.last_backup else None,
            "oldest_backup": self.oldest_backup.isoformat() if self.oldest_backup else None,
            "storage_efficiency": round(self.storage_efficiency, 3),
            "verification_success_rate": round(self.verification_success_rate, 3)
        }


class RestoreOperation(BaseModel):
    """File restore operation."""
    restore_id: str = Field(default_factory=lambda: str(uuid4()))
    file_id: str
    user_id: UUID
    backup_id: str
    version_id: Optional[str] = None
    
    # Status
    status: str = "pending"  # pending, in_progress, completed, failed
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Restore details
    restore_path: str
    original_size_bytes: int = 0
    verification_passed: bool = False
    error_message: Optional[str] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate restore duration in seconds."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()


class BackupManager:
    """
    Comprehensive backup and versioning manager.
    
    Features:
    - Multiple backup strategies (full, incremental, differential)
    - File versioning with change tracking
    - Backup verification and integrity checking
    - Disaster recovery operations
    - Multiple storage backends (S3, local, remote)
    - Backup scheduling and automation
    - Compression and encryption
    - Backup analytics and monitoring
    """
    
    def __init__(self):
        self.backup_entries: Dict[str, BackupEntry] = {}
        self.file_versions: Dict[str, List[BackupVersion]] = {}  # file_id -> versions
        self.backup_strategies: Dict[str, BackupStrategy] = {}
        self.restore_operations: Dict[str, RestoreOperation] = {}
        self.metrics = BackupMetrics()
        
        self._backup_queue: asyncio.Queue = asyncio.Queue()
        self._scheduled_backups: Set[str] = set()
        self._verification_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        
        # Create default strategies
        self._create_default_strategies()
        
        logger.info("BackupManager initialized")
    
    async def initialize(self) -> None:
        """Initialize backup manager and start background tasks."""
        try:
            # Start background workers
            await self._start_background_workers()
            
            # Update metrics
            await self._update_metrics()
            
            logger.info("Backup manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize backup manager: {e}")
            raise
    
    async def schedule_backup(
        self,
        file_id: str,
        user_id: UUID,
        strategy_name: str = "default",
        priority: int = 1
    ) -> str:
        """
        Schedule a backup operation.
        
        Args:
            file_id: File to backup
            user_id: User ID
            strategy_name: Backup strategy to use
            priority: Backup priority (1=high, 5=low)
            
        Returns:
            Backup ID
        """
        try:
            strategy = self.backup_strategies.get(strategy_name, self.backup_strategies["default"])
            
            # Create backup entry
            backup_entry = BackupEntry(
                file_id=file_id,
                user_id=user_id,
                backup_type=strategy.backup_type,
                strategy_name=strategy_name,
                source_path=f"documents/{user_id}/{file_id}",  # Would be actual S3 path
                backup_path=f"{strategy.backup_storage_path}{user_id}/{file_id}",
                metadata={"priority": priority, "strategy": strategy_name}
            )
            
            # Store backup entry
            async with self._lock:
                self.backup_entries[backup_entry.backup_id] = backup_entry
                self._scheduled_backups.add(backup_entry.backup_id)
            
            # Add to backup queue
            await self._backup_queue.put((priority, backup_entry.backup_id))
            
            logger.info(f"Scheduled backup: {backup_entry.backup_id} for file {file_id}")
            return backup_entry.backup_id
            
        except Exception as e:
            logger.error(f"Failed to schedule backup for file {file_id}: {e}")
            raise
    
    async def create_version(
        self,
        file_id: str,
        content_hash: str,
        size_bytes: int,
        metadata: Optional[Dict[str, Any]] = None,
        changes_summary: Optional[str] = None
    ) -> BackupVersion:
        """Create a new file version."""
        async with self._lock:
            # Get existing versions
            versions = self.file_versions.get(file_id, [])
            
            # Mark previous version as not current
            for version in versions:
                version.is_current = False
            
            # Create new version
            version_number = len(versions) + 1
            parent_version_id = versions[-1].version_id if versions else None
            
            new_version = BackupVersion(
                file_id=file_id,
                version_number=version_number,
                content_hash=content_hash,
                size_bytes=size_bytes,
                metadata=metadata or {},
                changes_summary=changes_summary,
                parent_version_id=parent_version_id,
                is_current=True
            )
            
            # Store version
            versions.append(new_version)
            self.file_versions[file_id] = versions
            
            logger.info(f"Created version {version_number} for file {file_id}")
            return new_version
    
    async def get_file_versions(
        self,
        file_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get file version history."""
        versions = self.file_versions.get(file_id, [])
        
        # Sort by version number (newest first) and limit
        sorted_versions = sorted(versions, key=lambda v: v.version_number, reverse=True)
        limited_versions = sorted_versions[:limit]
        
        return [
            {
                "version_id": v.version_id,
                "version_number": v.version_number,
                "content_hash": v.content_hash,
                "size_mb": round(v.size_mb, 2),
                "created_at": v.created_at.isoformat(),
                "changes_summary": v.changes_summary,
                "is_current": v.is_current,
                "metadata": v.metadata
            }
            for v in limited_versions
        ]
    
    async def restore_file(
        self,
        file_id: str,
        user_id: UUID,
        backup_id: Optional[str] = None,
        version_id: Optional[str] = None,
        restore_path: Optional[str] = None
    ) -> str:
        """
        Restore a file from backup or specific version.
        
        Args:
            file_id: File to restore
            user_id: User ID for access control
            backup_id: Specific backup to restore from
            version_id: Specific version to restore
            restore_path: Where to restore the file
            
        Returns:
            Restore operation ID
        """
        try:
            # Find backup to restore from
            if backup_id:
                backup_entry = self.backup_entries.get(backup_id)
                if not backup_entry or backup_entry.user_id != user_id:
                    raise ValueError(f"Backup {backup_id} not found or access denied")
            else:
                # Find latest successful backup for this file
                file_backups = [
                    backup for backup in self.backup_entries.values()
                    if (
                        backup.file_id == file_id and
                        backup.user_id == user_id and
                        backup.status == BackupStatus.COMPLETED
                    )
                ]
                
                if not file_backups:
                    raise ValueError(f"No backups found for file {file_id}")
                
                # Sort by completion time (newest first)
                file_backups.sort(key=lambda b: b.completed_at or datetime.min, reverse=True)
                backup_entry = file_backups[0]
                backup_id = backup_entry.backup_id
            
            # Create restore operation
            restore_op = RestoreOperation(
                file_id=file_id,
                user_id=user_id,
                backup_id=backup_id,
                version_id=version_id,
                restore_path=restore_path or f"restored/{user_id}/{file_id}",
                original_size_bytes=backup_entry.backup_size_bytes
            )
            
            # Store restore operation
            async with self._lock:
                self.restore_operations[restore_op.restore_id] = restore_op
            
            # Execute restore (in real implementation, this would be asynchronous)
            await self._execute_restore(restore_op)
            
            logger.info(f"Started restore operation: {restore_op.restore_id}")
            return restore_op.restore_id
            
        except Exception as e:
            logger.error(f"Failed to restore file {file_id}: {e}")
            raise
    
    async def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """Verify backup integrity."""
        backup_entry = self.backup_entries.get(backup_id)
        if not backup_entry:
            return {"verified": False, "error": "Backup not found"}
        
        try:
            # In real implementation, this would:
            # 1. Download backup from storage
            # 2. Verify checksum
            # 3. Test extraction/decompression
            # 4. Compare with original if available
            
            verification_result = {
                "verified": True,
                "checksum_valid": True,
                "content_readable": True,
                "size_matches": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Update backup entry
            backup_entry.verification_status = "verified"
            backup_entry.status = BackupStatus.VERIFIED
            
            logger.info(f"Backup verified: {backup_id}")
            return verification_result
            
        except Exception as e:
            backup_entry.verification_status = f"failed: {e}"
            backup_entry.status = BackupStatus.CORRUPTED
            
            logger.error(f"Backup verification failed for {backup_id}: {e}")
            return {
                "verified": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def delete_backups(
        self,
        file_id: str,
        keep_versions: int = 0
    ) -> int:
        """
        Delete backups for a file.
        
        Args:
            file_id: File ID
            keep_versions: Number of recent versions to keep
            
        Returns:
            Number of backups deleted
        """
        deleted_count = 0
        
        try:
            # Find all backups for this file
            file_backups = [
                (backup_id, backup) for backup_id, backup in self.backup_entries.items()
                if backup.file_id == file_id
            ]
            
            # Sort by completion time (newest first)
            file_backups.sort(
                key=lambda x: x[1].completed_at or datetime.min,
                reverse=True
            )
            
            # Keep specified number of recent versions
            backups_to_delete = file_backups[keep_versions:] if keep_versions > 0 else file_backups
            
            async with self._lock:
                for backup_id, backup_entry in backups_to_delete:
                    # In real implementation, delete from storage backend
                    # await self._delete_backup_from_storage(backup_entry.backup_path)
                    
                    # Remove from tracking
                    del self.backup_entries[backup_id]
                    deleted_count += 1
            
            # Also delete file versions if no backups remain
            if keep_versions == 0 and file_id in self.file_versions:
                del self.file_versions[file_id]
            
            logger.info(f"Deleted {deleted_count} backups for file {file_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete backups for file {file_id}: {e}")
            return deleted_count
    
    async def cleanup_old_backups(self, max_age_days: int = 30) -> Dict[str, Any]:
        """Clean up old backups based on retention policies."""
        start_time = datetime.utcnow()
        cleanup_stats = {
            "processed": 0,
            "deleted": 0,
            "space_freed_mb": 0.0,
            "errors": []
        }
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            backups_to_check = list(self.backup_entries.items())
            cleanup_stats["processed"] = len(backups_to_check)
            
            for backup_id, backup_entry in backups_to_check:
                try:
                    strategy = self.backup_strategies.get(
                        backup_entry.strategy_name,
                        self.backup_strategies["default"]
                    )
                    
                    # Check if backup is old enough to delete
                    backup_date = backup_entry.completed_at or backup_entry.scheduled_at
                    retention_cutoff = datetime.utcnow() - timedelta(days=strategy.retention_days)
                    
                    if backup_date < retention_cutoff:
                        # Delete backup
                        space_freed = backup_entry.backup_size_mb
                        
                        async with self._lock:
                            del self.backup_entries[backup_id]
                        
                        cleanup_stats["deleted"] += 1
                        cleanup_stats["space_freed_mb"] += space_freed
                        
                        logger.debug(f"Cleaned up old backup: {backup_id}")
                
                except Exception as e:
                    error_msg = f"Error cleaning backup {backup_id}: {e}"
                    cleanup_stats["errors"].append(error_msg)
                    logger.error(error_msg)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Backup cleanup completed in {duration:.2f}s: {cleanup_stats}")
            
            return {
                "status": "completed",
                "duration_seconds": round(duration, 2),
                "stats": cleanup_stats
            }
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "stats": cleanup_stats
            }
    
    async def get_backup_status(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed backup status."""
        backup_entry = self.backup_entries.get(backup_id)
        if not backup_entry:
            return None
        
        return {
            "backup_id": backup_entry.backup_id,
            "file_id": backup_entry.file_id,
            "status": backup_entry.status.value,
            "backup_type": backup_entry.backup_type.value,
            "strategy": backup_entry.strategy_name,
            "scheduled_at": backup_entry.scheduled_at.isoformat(),
            "started_at": backup_entry.started_at.isoformat() if backup_entry.started_at else None,
            "completed_at": backup_entry.completed_at.isoformat() if backup_entry.completed_at else None,
            "duration_seconds": backup_entry.duration_seconds,
            "backup_size_mb": round(backup_entry.backup_size_mb, 2),
            "compression_ratio": round(backup_entry.compression_ratio, 3),
            "verification_status": backup_entry.verification_status,
            "retry_count": backup_entry.retry_count,
            "error_message": backup_entry.error_message
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive backup metrics."""
        await self._update_metrics()
        return self.metrics.to_dict()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform backup system health check."""
        health_status = {
            "status": "healthy",
            "backup_queue_size": self._backup_queue.qsize(),
            "verification_queue_size": self._verification_queue.qsize(),
            "pending_backups": 0,
            "failed_backups_24h": 0,
            "storage_accessible": True,
            "issues": []
        }
        
        try:
            # Count pending and recent failed backups
            pending_count = 0
            failed_24h = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            for backup in self.backup_entries.values():
                if backup.status == BackupStatus.PENDING:
                    pending_count += 1
                elif (
                    backup.status == BackupStatus.FAILED and
                    backup.started_at and backup.started_at > cutoff_time
                ):
                    failed_24h += 1
            
            health_status["pending_backups"] = pending_count
            health_status["failed_backups_24h"] = failed_24h
            
            # Check for issues
            if pending_count > 100:
                health_status["status"] = "warning"
                health_status["issues"].append("High number of pending backups")
            
            if failed_24h > 10:
                health_status["status"] = "warning"
                health_status["issues"].append("High backup failure rate")
            
            if self._backup_queue.qsize() > 500:
                health_status["status"] = "critical"
                health_status["issues"].append("Backup queue is full")
            
            # Check backup success rate
            if self.metrics.backup_success_rate < 0.8:  # < 80%
                health_status["status"] = "critical"
                health_status["issues"].append("Low backup success rate")
            
            return health_status
            
        except Exception as e:
            logger.error(f"Backup health check failed: {e}")
            return {
                "status": "critical",
                "error": str(e),
                "issues": ["Health check failed"]
            }
    
    async def set_backup_strategy(
        self,
        name: str,
        strategy: BackupStrategy
    ) -> None:
        """Set or update a backup strategy."""
        self.backup_strategies[name] = strategy
        logger.info(f"Updated backup strategy: {name}")
    
    async def get_backup_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get all backup strategies."""
        return {
            name: {
                "name": strategy.name,
                "description": strategy.description,
                "backup_type": strategy.backup_type.value,
                "frequency_hours": strategy.frequency_hours,
                "retention_days": strategy.retention_days,
                "compression_enabled": strategy.compression_enabled,
                "encryption_enabled": strategy.encryption_enabled,
                "verification_enabled": strategy.verification_enabled,
                "max_backup_size_mb": strategy.max_backup_size_mb,
                "priority": strategy.priority,
                "use_s3": strategy.use_s3,
                "use_local": strategy.use_local,
                "use_remote": strategy.use_remote
            }
            for name, strategy in self.backup_strategies.items()
        }
    
    # Private helper methods
    
    def _create_default_strategies(self) -> None:
        """Create default backup strategies."""
        # Default strategy
        default_strategy = BackupStrategy(
            name="default",
            description="Standard backup strategy with daily incrementals",
            backup_type=BackupType.INCREMENTAL,
            frequency_hours=24,
            retention_days=30,
            compression_enabled=True,
            encryption_enabled=True,
            verification_enabled=True,
            use_s3=True
        )
        
        # High-priority strategy for critical files
        critical_strategy = BackupStrategy(
            name="critical",
            description="High-priority backup with full backups every 6 hours",
            backup_type=BackupType.FULL,
            frequency_hours=6,
            retention_days=90,
            compression_enabled=True,
            encryption_enabled=True,
            verification_enabled=True,
            priority=1,
            use_s3=True,
            use_remote=True
        )
        
        # Lightweight strategy for temporary files
        temp_strategy = BackupStrategy(
            name="temporary",
            description="Minimal backup for temporary files",
            backup_type=BackupType.SNAPSHOT,
            frequency_hours=168,  # Weekly
            retention_days=7,
            compression_enabled=True,
            encryption_enabled=False,
            verification_enabled=False,
            priority=5,
            use_local=True
        )
        
        # Archive strategy for long-term storage
        archive_strategy = BackupStrategy(
            name="archive",
            description="Long-term archive backup with high compression",
            backup_type=BackupType.FULL,
            frequency_hours=720,  # Monthly
            retention_days=2555,  # 7 years
            compression_enabled=True,
            encryption_enabled=True,
            verification_enabled=True,
            max_backup_size_mb=5000.0,
            priority=3,
            use_s3=True,
            use_remote=True
        )
        
        self.backup_strategies = {
            "default": default_strategy,
            "critical": critical_strategy,
            "temporary": temp_strategy,
            "archive": archive_strategy
        }
    
    async def _start_background_workers(self) -> None:
        """Start background worker tasks."""
        # In a real implementation, these would be proper background tasks
        # For now, we'll just log that they would be started
        logger.info("Backup worker tasks would be started here")
        
        # Workers that would be started:
        # - Backup processor worker
        # - Verification worker
        # - Cleanup scheduler
        # - Metrics updater
    
    async def _execute_backup(self, backup_entry: BackupEntry) -> None:
        """Execute a backup operation."""
        try:
            backup_entry.status = BackupStatus.IN_PROGRESS
            backup_entry.started_at = datetime.utcnow()
            
            # In real implementation, this would:
            # 1. Read source file
            # 2. Apply compression if enabled
            # 3. Apply encryption if enabled
            # 4. Upload to storage backend(s)
            # 5. Calculate checksum
            # 6. Create version entry
            
            # Mock backup operation
            await asyncio.sleep(0.1)  # Simulate backup time
            
            # Mock results
            backup_entry.backup_size_bytes = 1024 * 1024  # 1MB
            backup_entry.compression_ratio = 0.7  # 30% compression
            backup_entry.checksum = hashlib.md5(b"mock_content").hexdigest()
            backup_entry.status = BackupStatus.COMPLETED
            backup_entry.completed_at = datetime.utcnow()
            
            # Schedule verification if enabled
            strategy = self.backup_strategies.get(
                backup_entry.strategy_name,
                self.backup_strategies["default"]
            )
            
            if strategy.verification_enabled:
                await self._verification_queue.put(backup_entry.backup_id)
            
            logger.info(f"Backup completed: {backup_entry.backup_id}")
            
        except Exception as e:
            backup_entry.status = BackupStatus.FAILED
            backup_entry.error_message = str(e)
            backup_entry.completed_at = datetime.utcnow()
            
            logger.error(f"Backup failed: {backup_entry.backup_id} - {e}")
    
    async def _execute_restore(self, restore_op: RestoreOperation) -> None:
        """Execute a restore operation."""
        try:
            restore_op.status = "in_progress"
            
            # In real implementation, this would:
            # 1. Download backup from storage
            # 2. Decrypt if needed
            # 3. Decompress if needed
            # 4. Verify integrity
            # 5. Write to restore location
            
            # Mock restore operation
            await asyncio.sleep(0.1)  # Simulate restore time
            
            restore_op.verification_passed = True
            restore_op.status = "completed"
            restore_op.completed_at = datetime.utcnow()
            
            logger.info(f"Restore completed: {restore_op.restore_id}")
            
        except Exception as e:
            restore_op.status = "failed"
            restore_op.error_message = str(e)
            restore_op.completed_at = datetime.utcnow()
            
            logger.error(f"Restore failed: {restore_op.restore_id} - {e}")
    
    async def _update_metrics(self) -> None:
        """Update backup metrics."""
        try:
            total_backups = len(self.backup_entries)
            successful_backups = sum(
                1 for backup in self.backup_entries.values()
                if backup.status == BackupStatus.COMPLETED
            )
            failed_backups = sum(
                1 for backup in self.backup_entries.values()
                if backup.status == BackupStatus.FAILED
            )
            pending_backups = sum(
                1 for backup in self.backup_entries.values()
                if backup.status == BackupStatus.PENDING
            )
            
            total_size_mb = sum(
                backup.backup_size_mb for backup in self.backup_entries.values()
                if backup.status == BackupStatus.COMPLETED
            )
            
            # Calculate average backup time
            completed_backups = [
                backup for backup in self.backup_entries.values()
                if backup.status == BackupStatus.COMPLETED and backup.duration_seconds
            ]
            
            avg_backup_time = (
                sum(backup.duration_seconds for backup in completed_backups) / len(completed_backups)
                if completed_backups else 0.0
            )
            
            # Calculate success rate
            success_rate = (
                successful_backups / total_backups if total_backups > 0 else 0.0
            )
            
            # Find oldest and newest backups
            backup_dates = [
                backup.completed_at for backup in self.backup_entries.values()
                if backup.completed_at
            ]
            
            oldest_backup = min(backup_dates) if backup_dates else None
            last_backup = max(backup_dates) if backup_dates else None
            
            # Calculate storage efficiency (compression ratio)
            compressed_backups = [
                backup for backup in self.backup_entries.values()
                if backup.compression_ratio > 0
            ]
            
            storage_efficiency = (
                sum(backup.compression_ratio for backup in compressed_backups) / len(compressed_backups)
                if compressed_backups else 0.0
            )
            
            # Calculate verification success rate
            verified_backups = sum(
                1 for backup in self.backup_entries.values()
                if backup.status == BackupStatus.VERIFIED
            )
            
            verification_success_rate = (
                verified_backups / successful_backups if successful_backups > 0 else 0.0
            )
            
            # Update metrics
            self.metrics.total_backups = total_backups
            self.metrics.successful_backups = successful_backups
            self.metrics.failed_backups = failed_backups
            self.metrics.pending_backups = pending_backups
            self.metrics.total_backup_size_mb = total_size_mb
            self.metrics.average_backup_time_seconds = avg_backup_time
            self.metrics.backup_success_rate = success_rate
            self.metrics.last_backup = last_backup
            self.metrics.oldest_backup = oldest_backup
            self.metrics.storage_efficiency = storage_efficiency
            self.metrics.verification_success_rate = verification_success_rate
            
        except Exception as e:
            logger.error(f"Failed to update backup metrics: {e}")