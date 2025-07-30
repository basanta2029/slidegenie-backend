"""
Lifecycle manager for document processing system.

Handles file lifecycle management, temporary file cleanup, retention policies,
and automated maintenance tasks with scheduling and monitoring.
"""

import asyncio
import logging
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class FileStatus(str, Enum):
    """File lifecycle status."""
    ACTIVE = "active"
    MARKED_FOR_DELETION = "marked_for_deletion"
    SOFT_DELETED = "soft_deleted"
    ARCHIVED = "archived"
    PURGED = "purged"


class RetentionPolicy(BaseModel):
    """File retention policy configuration."""
    name: str
    description: str
    active_retention_days: int = Field(default=365)  # 1 year active
    soft_delete_retention_days: int = Field(default=30)  # 30 days in trash
    archive_after_days: int = Field(default=180)  # Archive after 6 months
    temp_file_retention_hours: int = Field(default=24)  # 24 hours for temp files
    max_file_size_mb: float = Field(default=100.0)
    applies_to_content_types: List[str] = Field(default_factory=list)
    applies_to_users: List[str] = Field(default_factory=list)  # User tiers: "free", "premium", etc.
    auto_archive: bool = Field(default=True)
    auto_purge: bool = Field(default=False)


class FileLifecycleEntry(BaseModel):
    """File lifecycle tracking entry."""
    file_id: str
    user_id: UUID
    filename: str
    file_path: str
    content_type: str
    size_bytes: int
    status: FileStatus = Field(default=FileStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    marked_for_deletion_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    purged_at: Optional[datetime] = None
    retention_policy: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: Set[str] = Field(default_factory=set)
    
    @property
    def age_days(self) -> float:
        """Calculate file age in days."""
        return (datetime.utcnow() - self.created_at).total_seconds() / 86400
    
    @property
    def last_access_days_ago(self) -> float:
        """Calculate days since last access."""
        return (datetime.utcnow() - self.last_accessed).total_seconds() / 86400
    
    @property
    def size_mb(self) -> float:
        """File size in MB."""
        return self.size_bytes / (1024 * 1024)
    
    def should_archive(self, policy: RetentionPolicy) -> bool:
        """Check if file should be archived based on policy."""
        if not policy.auto_archive or self.status != FileStatus.ACTIVE:
            return False
        
        return (
            self.age_days > policy.archive_after_days or
            self.last_access_days_ago > policy.archive_after_days
        )
    
    def should_soft_delete(self, policy: RetentionPolicy) -> bool:
        """Check if file should be soft deleted based on policy."""
        if self.status != FileStatus.ACTIVE:
            return False
        
        return self.age_days > policy.active_retention_days
    
    def should_purge(self, policy: RetentionPolicy) -> bool:
        """Check if file should be purged based on policy."""
        if not policy.auto_purge:
            return False
        
        if self.status == FileStatus.SOFT_DELETED and self.deleted_at:
            days_since_deletion = (datetime.utcnow() - self.deleted_at).total_seconds() / 86400
            return days_since_deletion > policy.soft_delete_retention_days
        
        return False


class CleanupStats(BaseModel):
    """Cleanup operation statistics."""
    files_processed: int = 0
    files_archived: int = 0
    files_soft_deleted: int = 0
    files_purged: int = 0
    temp_files_cleaned: int = 0
    space_freed_mb: float = 0.0
    errors: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "files_processed": self.files_processed,
            "files_archived": self.files_archived,
            "files_soft_deleted": self.files_soft_deleted,
            "files_purged": self.files_purged,
            "temp_files_cleaned": self.temp_files_cleaned,
            "space_freed_mb": round(self.space_freed_mb, 2),
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 2)
        }


class LifecycleMetrics(BaseModel):
    """Lifecycle management metrics."""
    total_files: int = 0
    active_files: int = 0
    archived_files: int = 0
    soft_deleted_files: int = 0
    temp_files: int = 0
    total_size_mb: float = 0.0
    oldest_file_days: float = 0.0
    cleanup_runs_24h: int = 0
    last_cleanup: Optional[datetime] = None
    errors_24h: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_files": self.total_files,
            "active_files": self.active_files,
            "archived_files": self.archived_files,
            "soft_deleted_files": self.soft_deleted_files,
            "temp_files": self.temp_files,
            "total_size_mb": round(self.total_size_mb, 2),
            "oldest_file_days": round(self.oldest_file_days, 2),
            "cleanup_runs_24h": self.cleanup_runs_24h,
            "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None,
            "errors_24h": self.errors_24h
        }


class LifecycleManager:
    """
    File lifecycle manager with comprehensive retention policies.
    
    Features:
    - Automated cleanup based on retention policies
    - Temporary file management
    - Archive and purge operations
    - Storage quota enforcement
    - Lifecycle analytics and monitoring
    - Scheduled maintenance tasks
    """
    
    def __init__(self):
        self.lifecycle_entries: Dict[str, FileLifecycleEntry] = {}
        self.retention_policies: Dict[str, RetentionPolicy] = {}
        self.metrics = LifecycleMetrics()
        self.temp_dir = Path(tempfile.gettempdir()) / "slidegenie_temp"
        self.archive_dir = Path(settings.MINIO_BUCKET_NAME + "_archive")  # Would be S3/MinIO path
        self._cleanup_history: List[Tuple[datetime, CleanupStats]] = []
        self._scheduled_tasks: Set[str] = set()
        self._lock = asyncio.Lock()
        
        # Create default retention policies
        self._create_default_policies()
        
        logger.info("LifecycleManager initialized")
    
    async def initialize(self) -> None:
        """Initialize lifecycle manager."""
        try:
            # Create temp directory
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create archive directory (would be S3/MinIO bucket)
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Start background cleanup task
            await self._start_background_tasks()
            
            # Update metrics
            await self._update_metrics()
            
            logger.info("Lifecycle manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize lifecycle manager: {e}")
            raise
    
    async def track_file(
        self,
        file_id: str,
        user_id: UUID,
        filename: str,
        file_path: str,
        content_type: str,
        size_bytes: int,
        retention_policy: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Start tracking a file's lifecycle."""
        entry = FileLifecycleEntry(
            file_id=file_id,
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            content_type=content_type,
            size_bytes=size_bytes,
            retention_policy=retention_policy,
            metadata=metadata or {},
            tags=set()
        )
        
        async with self._lock:
            self.lifecycle_entries[file_id] = entry
        
        logger.debug(f"Started tracking file: {file_id}")
    
    async def update_file_access(self, file_id: str) -> None:
        """Update file's last access timestamp."""
        async with self._lock:
            if file_id in self.lifecycle_entries:
                self.lifecycle_entries[file_id].last_accessed = datetime.utcnow()
    
    async def mark_for_deletion(self, file_id: str, user_id: UUID) -> bool:
        """Mark a file for deletion (soft delete)."""
        async with self._lock:
            entry = self.lifecycle_entries.get(file_id)
            if not entry or entry.user_id != user_id:
                return False
            
            entry.status = FileStatus.MARKED_FOR_DELETION
            entry.marked_for_deletion_at = datetime.utcnow()
        
        logger.info(f"File marked for deletion: {file_id}")
        return True
    
    async def restore_file(self, file_id: str, user_id: UUID) -> bool:
        """Restore a file from soft delete."""
        async with self._lock:
            entry = self.lifecycle_entries.get(file_id)
            if not entry or entry.user_id != user_id:
                return False
            
            if entry.status in [FileStatus.MARKED_FOR_DELETION, FileStatus.SOFT_DELETED]:
                entry.status = FileStatus.ACTIVE
                entry.marked_for_deletion_at = None
                entry.deleted_at = None
                entry.last_accessed = datetime.utcnow()
                
                logger.info(f"File restored: {file_id}")
                return True
        
        return False
    
    async def create_temp_file(
        self,
        content: bytes,
        suffix: str = ".tmp",
        prefix: str = "slidegenie_"
    ) -> Tuple[str, Path]:
        """Create a temporary file with automatic cleanup."""
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
                prefix=prefix,
                dir=self.temp_dir
            )
            
            temp_file.write(content)
            temp_file.close()
            
            temp_path = Path(temp_file.name)
            temp_id = temp_path.stem
            
            # Track for cleanup
            await self.track_file(
                file_id=temp_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),  # System user
                filename=temp_path.name,
                file_path=str(temp_path),
                content_type="temporary",
                size_bytes=len(content),
                retention_policy="temporary",
                metadata={"is_temp": True, "created_by": "system"}
            )
            
            logger.debug(f"Created temporary file: {temp_path}")
            return temp_id, temp_path
            
        except Exception as e:
            logger.error(f"Failed to create temporary file: {e}")
            raise
    
    async def cleanup_temp_file(self, temp_id: str) -> bool:
        """Clean up a specific temporary file."""
        try:
            entry = self.lifecycle_entries.get(temp_id)
            if not entry or not entry.metadata.get("is_temp"):
                return False
            
            file_path = Path(entry.file_path)
            if file_path.exists():
                file_path.unlink()
            
            async with self._lock:
                del self.lifecycle_entries[temp_id]
            
            logger.debug(f"Cleaned up temporary file: {temp_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup temporary file {temp_id}: {e}")
            return False
    
    async def run_cleanup(self, force: bool = False) -> CleanupStats:
        """Run comprehensive cleanup operation."""
        start_time = datetime.utcnow()
        stats = CleanupStats()
        
        logger.info("Starting lifecycle cleanup operation")
        
        try:
            # Process each file based on its retention policy
            files_to_process = list(self.lifecycle_entries.values())
            stats.files_processed = len(files_to_process)
            
            for entry in files_to_process:
                try:
                    policy = self.retention_policies.get(
                        entry.retention_policy, 
                        self.retention_policies["default"]
                    )
                    
                    # Check if file should be archived
                    if entry.should_archive(policy):
                        if await self._archive_file(entry):
                            stats.files_archived += 1
                            stats.space_freed_mb += entry.size_mb
                    
                    # Check if file should be soft deleted
                    elif entry.should_soft_delete(policy):
                        if await self._soft_delete_file(entry):
                            stats.files_soft_deleted += 1
                    
                    # Check if file should be purged
                    elif entry.should_purge(policy):
                        if await self._purge_file(entry):
                            stats.files_purged += 1
                            stats.space_freed_mb += entry.size_mb
                    
                except Exception as e:
                    error_msg = f"Error processing file {entry.file_id}: {e}"
                    stats.errors.append(error_msg)
                    logger.error(error_msg)
            
            # Clean up temporary files
            temp_stats = await self._cleanup_temp_files()
            stats.temp_files_cleaned = temp_stats["cleaned"]
            stats.space_freed_mb += temp_stats["space_freed_mb"]
            stats.errors.extend(temp_stats["errors"])
            
            # Update metrics
            await self._update_metrics()
            
            # Record cleanup history
            stats.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            self._cleanup_history.append((datetime.utcnow(), stats))
            
            # Keep only recent cleanup history
            if len(self._cleanup_history) > 100:
                self._cleanup_history = self._cleanup_history[-50:]
            
            logger.info(f"Cleanup completed: {stats.to_dict()}")
            return stats
            
        except Exception as e:
            error_msg = f"Cleanup operation failed: {e}"
            stats.errors.append(error_msg)
            stats.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            logger.error(error_msg)
            return stats
    
    async def get_file_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed file lifecycle status."""
        entry = self.lifecycle_entries.get(file_id)
        if not entry:
            return None
        
        policy = self.retention_policies.get(
            entry.retention_policy, 
            self.retention_policies["default"]
        )
        
        return {
            "file_id": entry.file_id,
            "status": entry.status.value,
            "age_days": round(entry.age_days, 2),
            "last_access_days_ago": round(entry.last_access_days_ago, 2),
            "size_mb": round(entry.size_mb, 2),
            "retention_policy": entry.retention_policy,
            "should_archive": entry.should_archive(policy),
            "should_soft_delete": entry.should_soft_delete(policy),
            "should_purge": entry.should_purge(policy),
            "created_at": entry.created_at.isoformat(),
            "last_accessed": entry.last_accessed.isoformat(),
            "marked_for_deletion_at": entry.marked_for_deletion_at.isoformat() if entry.marked_for_deletion_at else None,
            "archived_at": entry.archived_at.isoformat() if entry.archived_at else None
        }
    
    async def get_user_files(
        self,
        user_id: UUID,
        status_filter: Optional[FileStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get files for a specific user with optional status filtering."""
        user_files = []
        
        for entry in self.lifecycle_entries.values():
            if entry.user_id != user_id:
                continue
            
            if status_filter and entry.status != status_filter:
                continue
            
            file_info = {
                "file_id": entry.file_id,
                "filename": entry.filename,
                "status": entry.status.value,
                "size_mb": round(entry.size_mb, 2),
                "age_days": round(entry.age_days, 2),
                "created_at": entry.created_at.isoformat(),
                "last_accessed": entry.last_accessed.isoformat()
            }
            
            user_files.append(file_info)
        
        # Sort by creation date (newest first) and limit
        user_files.sort(key=lambda x: x["created_at"], reverse=True)
        return user_files[:limit]
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive lifecycle metrics."""
        await self._update_metrics()
        return self.metrics.to_dict()
    
    async def set_retention_policy(
        self,
        name: str,
        policy: RetentionPolicy
    ) -> None:
        """Set or update a retention policy."""
        self.retention_policies[name] = policy
        logger.info(f"Updated retention policy: {name}")
    
    async def get_retention_policies(self) -> Dict[str, Dict[str, Any]]:
        """Get all retention policies."""
        return {
            name: {
                "name": policy.name,
                "description": policy.description,
                "active_retention_days": policy.active_retention_days,
                "soft_delete_retention_days": policy.soft_delete_retention_days,
                "archive_after_days": policy.archive_after_days,
                "temp_file_retention_hours": policy.temp_file_retention_hours,
                "max_file_size_mb": policy.max_file_size_mb,
                "applies_to_content_types": policy.applies_to_content_types,
                "applies_to_users": policy.applies_to_users,
                "auto_archive": policy.auto_archive,
                "auto_purge": policy.auto_purge
            }
            for name, policy in self.retention_policies.items()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform lifecycle management health check."""
        health_status = {
            "status": "healthy",
            "temp_dir_accessible": False,
            "archive_dir_accessible": False,
            "cleanup_running": False,
            "issues": []
        }
        
        try:
            # Check temp directory
            if self.temp_dir.exists() and os.access(self.temp_dir, os.W_OK):
                health_status["temp_dir_accessible"] = True
            else:
                health_status["issues"].append("Temp directory not accessible")
                health_status["status"] = "warning"
            
            # Check archive directory
            if self.archive_dir.exists() and os.access(self.archive_dir, os.W_OK):
                health_status["archive_dir_accessible"] = True
            else:
                health_status["issues"].append("Archive directory not accessible")
                health_status["status"] = "warning"
            
            # Check if cleanup is running too frequently or failing
            recent_cleanups = [
                cleanup for cleanup_time, cleanup in self._cleanup_history
                if cleanup_time > datetime.utcnow() - timedelta(hours=24)
            ]
            
            if len(recent_cleanups) > 24:  # More than once per hour
                health_status["issues"].append("Cleanup running too frequently")
                health_status["status"] = "warning"
            
            error_count = sum(len(cleanup.errors) for cleanup in recent_cleanups)
            if error_count > 10:
                health_status["issues"].append("Too many cleanup errors")
                health_status["status"] = "critical"
            
            # Check temp file accumulation
            temp_files = sum(
                1 for entry in self.lifecycle_entries.values()
                if entry.metadata.get("is_temp")
            )
            
            if temp_files > 1000:
                health_status["issues"].append("Too many temporary files")
                health_status["status"] = "warning"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Lifecycle health check failed: {e}")
            return {
                "status": "critical",
                "error": str(e),
                "issues": ["Health check failed"]
            }
    
    # Private helper methods
    
    def _create_default_policies(self) -> None:
        """Create default retention policies."""
        # Default policy for regular users
        default_policy = RetentionPolicy(
            name="default",
            description="Standard retention policy for regular users",
            active_retention_days=365,  # 1 year
            soft_delete_retention_days=30,  # 30 days in trash
            archive_after_days=180,  # Archive after 6 months
            temp_file_retention_hours=24,  # 24 hours
            max_file_size_mb=100.0,
            auto_archive=True,
            auto_purge=False
        )
        
        # Policy for free tier users
        free_tier_policy = RetentionPolicy(
            name="free_tier",
            description="Retention policy for free tier users",
            active_retention_days=90,  # 3 months
            soft_delete_retention_days=7,  # 7 days in trash
            archive_after_days=60,  # Archive after 2 months
            temp_file_retention_hours=6,  # 6 hours
            max_file_size_mb=50.0,
            applies_to_users=["free"],
            auto_archive=True,
            auto_purge=True
        )
        
        # Policy for premium users
        premium_policy = RetentionPolicy(
            name="premium",
            description="Extended retention policy for premium users",
            active_retention_days=730,  # 2 years
            soft_delete_retention_days=90,  # 90 days in trash
            archive_after_days=365,  # Archive after 1 year
            temp_file_retention_hours=48,  # 48 hours
            max_file_size_mb=500.0,
            applies_to_users=["premium", "pro"],
            auto_archive=True,
            auto_purge=False
        )
        
        # Policy for temporary files
        temp_policy = RetentionPolicy(
            name="temporary",
            description="Aggressive cleanup for temporary files",
            active_retention_days=1,  # 1 day
            soft_delete_retention_days=0,  # No trash retention
            archive_after_days=0,  # No archiving
            temp_file_retention_hours=24,  # 24 hours max
            max_file_size_mb=1000.0,
            auto_archive=False,
            auto_purge=True
        )
        
        self.retention_policies = {
            "default": default_policy,
            "free_tier": free_tier_policy,
            "premium": premium_policy,
            "temporary": temp_policy
        }
    
    async def _archive_file(self, entry: FileLifecycleEntry) -> bool:
        """Archive a file to cold storage."""
        try:
            # In a real implementation, this would move the file to S3 Glacier
            # or another cold storage solution
            
            entry.status = FileStatus.ARCHIVED
            entry.archived_at = datetime.utcnow()
            
            logger.info(f"Archived file: {entry.file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive file {entry.file_id}: {e}")
            return False
    
    async def _soft_delete_file(self, entry: FileLifecycleEntry) -> bool:
        """Soft delete a file (move to trash)."""
        try:
            entry.status = FileStatus.SOFT_DELETED
            entry.deleted_at = datetime.utcnow()
            
            logger.info(f"Soft deleted file: {entry.file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to soft delete file {entry.file_id}: {e}")
            return False
    
    async def _purge_file(self, entry: FileLifecycleEntry) -> bool:
        """Permanently delete a file."""
        try:
            # Remove physical file
            file_path = Path(entry.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Update entry
            entry.status = FileStatus.PURGED
            entry.purged_at = datetime.utcnow()
            
            # Remove from tracking (after a delay for audit purposes)
            # In production, you might want to keep the metadata for auditing
            
            logger.info(f"Purged file: {entry.file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to purge file {entry.file_id}: {e}")
            return False
    
    async def _cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean up expired temporary files."""
        stats = {
            "cleaned": 0,
            "space_freed_mb": 0.0,
            "errors": []
        }
        
        temp_policy = self.retention_policies["temporary"]
        cutoff_time = datetime.utcnow() - timedelta(hours=temp_policy.temp_file_retention_hours)
        
        temp_files = [
            entry for entry in self.lifecycle_entries.values()
            if (
                entry.metadata.get("is_temp") and
                entry.created_at < cutoff_time
            )
        ]
        
        for entry in temp_files:
            try:
                file_path = Path(entry.file_path)
                if file_path.exists():
                    stats["space_freed_mb"] += entry.size_mb
                    file_path.unlink()
                
                # Remove from tracking
                async with self._lock:
                    if entry.file_id in self.lifecycle_entries:
                        del self.lifecycle_entries[entry.file_id]
                
                stats["cleaned"] += 1
                
            except Exception as e:
                error_msg = f"Failed to cleanup temp file {entry.file_id}: {e}"
                stats["errors"].append(error_msg)
                logger.error(error_msg)
        
        if stats["cleaned"] > 0:
            logger.info(f"Cleaned up {stats['cleaned']} temporary files, freed {stats['space_freed_mb']:.2f}MB")
        
        return stats
    
    async def _start_background_tasks(self) -> None:
        """Start background cleanup tasks."""
        # This would typically use a task scheduler like Celery or APScheduler
        # For now, we'll just log that tasks would be started
        logger.info("Background lifecycle tasks would be started here")
        
        # Example of what would be scheduled:
        # - Hourly temp file cleanup
        # - Daily regular cleanup
        # - Weekly archive operations
        # - Monthly purge operations
    
    async def _update_metrics(self) -> None:
        """Update lifecycle metrics."""
        try:
            status_counts = {}
            total_size = 0.0
            oldest_file = None
            
            for entry in self.lifecycle_entries.values():
                # Count by status
                status = entry.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Total size
                total_size += entry.size_mb
                
                # Find oldest file
                if oldest_file is None or entry.created_at < oldest_file:
                    oldest_file = entry.created_at
            
            # Update metrics
            self.metrics.total_files = len(self.lifecycle_entries)
            self.metrics.active_files = status_counts.get("active", 0)
            self.metrics.archived_files = status_counts.get("archived", 0)
            self.metrics.soft_deleted_files = status_counts.get("soft_deleted", 0)
            self.metrics.temp_files = sum(
                1 for entry in self.lifecycle_entries.values()
                if entry.metadata.get("is_temp")
            )
            self.metrics.total_size_mb = total_size
            
            if oldest_file:
                self.metrics.oldest_file_days = (datetime.utcnow() - oldest_file).total_seconds() / 86400
            
            # Count recent cleanup runs
            recent_cleanups = [
                cleanup_time for cleanup_time, _ in self._cleanup_history
                if cleanup_time > datetime.utcnow() - timedelta(hours=24)
            ]
            self.metrics.cleanup_runs_24h = len(recent_cleanups)
            
            if self._cleanup_history:
                self.metrics.last_cleanup = self._cleanup_history[-1][0]
            
            # Count recent errors
            recent_errors = 0
            for cleanup_time, cleanup_stats in self._cleanup_history:
                if cleanup_time > datetime.utcnow() - timedelta(hours=24):
                    recent_errors += len(cleanup_stats.errors)
            
            self.metrics.errors_24h = recent_errors
            
        except Exception as e:
            logger.error(f"Failed to update lifecycle metrics: {e}")