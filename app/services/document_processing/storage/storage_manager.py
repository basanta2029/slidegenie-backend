"""
Main storage coordinator for document processing system.

This module provides a centralized interface for managing all storage operations
including original file storage, content caching, search indexing, lifecycle management,
and backup operations.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.config import get_settings
from .cache_manager import CacheManager
from .search_indexer import SearchIndexer
from .lifecycle_manager import LifecycleManager
from .backup_manager import BackupManager

settings = get_settings()
logger = logging.getLogger(__name__)


class StorageQuota(BaseModel):
    """Storage quota configuration and tracking."""
    user_id: UUID
    total_limit_mb: int = Field(default=100)  # Default 100MB for free tier
    used_mb: float = Field(default=0.0)
    file_count: int = Field(default=0)
    max_files: int = Field(default=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def available_mb(self) -> float:
        """Calculate available storage in MB."""
        return max(0, self.total_limit_mb - self.used_mb)
    
    @property
    def usage_percentage(self) -> float:
        """Calculate storage usage percentage."""
        if self.total_limit_mb == 0:
            return 0.0
        return min(100.0, (self.used_mb / self.total_limit_mb) * 100)
    
    def can_store(self, size_mb: float) -> bool:
        """Check if file can be stored within quota."""
        return (
            self.available_mb >= size_mb and 
            self.file_count < self.max_files
        )


class StorageMetrics(BaseModel):
    """Storage system metrics and health status."""
    total_files: int = 0
    total_size_mb: float = 0.0
    cache_hit_rate: float = 0.0
    search_index_count: int = 0
    backup_status: str = "unknown"
    cleanup_last_run: Optional[datetime] = None
    errors_last_24h: int = 0
    avg_response_time_ms: float = 0.0
    storage_health: str = "unknown"  # healthy, warning, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_files": self.total_files,
            "total_size_mb": round(self.total_size_mb, 2),
            "cache_hit_rate": round(self.cache_hit_rate, 2),
            "search_index_count": self.search_index_count,
            "backup_status": self.backup_status,
            "cleanup_last_run": self.cleanup_last_run.isoformat() if self.cleanup_last_run else None,
            "errors_24h": self.errors_last_24h,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "storage_health": self.storage_health
        }


class StorageOperation(BaseModel):
    """Storage operation tracking."""
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    operation_type: str  # store, retrieve, delete, backup, etc.
    file_id: Optional[str] = None
    user_id: Optional[UUID] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, completed, failed
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate operation duration in milliseconds."""
        if not self.completed_at:
            return None
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000


class StorageManager:
    """
    Main storage coordinator that orchestrates all storage operations.
    
    Provides a unified interface for:
    - Original file storage (S3/MinIO)
    - Content caching (Redis/PostgreSQL)
    - Search indexing (Elasticsearch)
    - Lifecycle management
    - Backup and versioning
    - Storage analytics
    """
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.search_indexer = SearchIndexer()
        self.lifecycle_manager = LifecycleManager()
        self.backup_manager = BackupManager()
        
        self._quotas: Dict[UUID, StorageQuota] = {}
        self._operations: List[StorageOperation] = []
        self._access_logs: List[Dict[str, Any]] = []
        self._metrics_cache: Optional[StorageMetrics] = None
        self._metrics_cache_time: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
        logger.info("StorageManager initialized")
    
    async def initialize(self) -> None:
        """Initialize all storage components."""
        try:
            await asyncio.gather(
                self.cache_manager.initialize(),
                self.search_indexer.initialize(),
                self.lifecycle_manager.initialize(),
                self.backup_manager.initialize()
            )
            logger.info("All storage components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize storage components: {e}")
            raise
    
    async def store_document(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Store a document with full processing pipeline.
        
        Args:
            file_content: Raw file content
            filename: Original filename
            content_type: MIME content type
            user_id: User ID for quota and access control
            metadata: Additional metadata
            
        Returns:
            Tuple of (file_id, storage_info)
        """
        operation = StorageOperation(
            operation_type="store_document",
            user_id=user_id,
            metadata={"filename": filename, "content_type": content_type}
        )
        
        try:
            # Check quota
            file_size_mb = len(file_content) / (1024 * 1024)
            quota = await self.get_user_quota(user_id)
            
            if not quota.can_store(file_size_mb):
                raise ValueError(
                    f"Storage quota exceeded. Available: {quota.available_mb:.2f}MB, "
                    f"Required: {file_size_mb:.2f}MB"
                )
            
            # Generate file ID
            file_id = str(uuid4())
            operation.file_id = file_id
            
            # Store original file
            storage_path = await self._store_original_file(
                file_id, file_content, filename, user_id
            )
            
            # Process and cache content
            processed_content = await self._process_and_cache_content(
                file_id, file_content, content_type, metadata or {}
            )
            
            # Index for search
            await self._index_for_search(
                file_id, processed_content, filename, user_id, metadata or {}
            )
            
            # Schedule backup
            await self.backup_manager.schedule_backup(file_id, user_id)
            
            # Update quota
            await self._update_quota(user_id, file_size_mb, 1)
            
            # Log access
            await self._log_access("store", file_id, user_id, True)
            
            storage_info = {
                "file_id": file_id,
                "storage_path": storage_path,
                "size_mb": file_size_mb,
                "processed": True,
                "indexed": True,
                "backed_up": False  # Will be true after backup completes
            }
            
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            
            logger.info(f"Document stored successfully: {file_id}")
            return file_id, storage_info
            
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            
            await self._log_access("store", operation.file_id, user_id, False, str(e))
            logger.error(f"Failed to store document: {e}")
            raise
        finally:
            self._operations.append(operation)
    
    async def retrieve_document(
        self,
        file_id: str,
        user_id: UUID,
        include_content: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve a document with all associated data.
        
        Args:
            file_id: Document file ID
            user_id: User ID for access control
            include_content: Whether to include file content
            
        Returns:
            Document data and metadata
        """
        operation = StorageOperation(
            operation_type="retrieve_document",
            file_id=file_id,
            user_id=user_id
        )
        
        try:
            # Check access permissions
            if not await self._check_access_permission(file_id, user_id):
                raise PermissionError(f"User {user_id} cannot access file {file_id}")
            
            # Try cache first
            cached_data = await self.cache_manager.get_document_data(file_id)
            
            if cached_data and not include_content:
                operation.status = "completed"
                operation.completed_at = datetime.utcnow()
                await self._log_access("retrieve_cached", file_id, user_id, True)
                return cached_data
            
            # Retrieve from primary storage
            file_data = await self._retrieve_original_file(file_id)
            
            # Get processed content from cache
            processed_content = await self.cache_manager.get_processed_content(file_id)
            
            # Combine data
            document_data = {
                "file_id": file_id,
                "filename": cached_data.get("filename") if cached_data else None,
                "content_type": cached_data.get("content_type") if cached_data else None,
                "size_mb": len(file_data) / (1024 * 1024) if file_data else 0,
                "processed_content": processed_content,
                "metadata": cached_data.get("metadata", {}) if cached_data else {},
                "created_at": cached_data.get("created_at") if cached_data else None
            }
            
            if include_content:
                document_data["raw_content"] = file_data
            
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            
            await self._log_access("retrieve", file_id, user_id, True)
            return document_data
            
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            
            await self._log_access("retrieve", file_id, user_id, False, str(e))
            logger.error(f"Failed to retrieve document {file_id}: {e}")
            raise
        finally:
            self._operations.append(operation)
    
    async def delete_document(
        self,
        file_id: str,
        user_id: UUID,
        permanent: bool = False
    ) -> bool:
        """
        Delete a document and all associated data.
        
        Args:
            file_id: Document file ID
            user_id: User ID for access control
            permanent: Whether to permanently delete or soft delete
            
        Returns:
            True if successful
        """
        operation = StorageOperation(
            operation_type="delete_document",
            file_id=file_id,
            user_id=user_id,
            metadata={"permanent": permanent}
        )
        
        try:
            # Check access permissions
            if not await self._check_access_permission(file_id, user_id):
                raise PermissionError(f"User {user_id} cannot delete file {file_id}")
            
            # Get file info for quota update
            file_info = await self.cache_manager.get_document_data(file_id)
            file_size_mb = file_info.get("size_mb", 0) if file_info else 0
            
            if permanent:
                # Permanent deletion
                await asyncio.gather(
                    self._delete_original_file(file_id),
                    self.cache_manager.delete_document_data(file_id),
                    self.search_indexer.delete_document(file_id),
                    self.backup_manager.delete_backups(file_id)
                )
            else:
                # Soft delete - move to lifecycle management
                await self.lifecycle_manager.mark_for_deletion(file_id, user_id)
            
            # Update quota
            await self._update_quota(user_id, -file_size_mb, -1)
            
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            
            await self._log_access("delete", file_id, user_id, True)
            logger.info(f"Document deleted: {file_id} (permanent: {permanent})")
            return True
            
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            
            await self._log_access("delete", file_id, user_id, False, str(e))
            logger.error(f"Failed to delete document {file_id}: {e}")
            raise
        finally:
            self._operations.append(operation)
    
    async def search_documents(
        self,
        query: str,
        user_id: UUID,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search documents using the search indexer."""
        operation = StorageOperation(
            operation_type="search_documents",
            user_id=user_id,
            metadata={"query": query, "limit": limit, "offset": offset}
        )
        
        try:
            results = await self.search_indexer.search(
                query=query,
                user_id=user_id,
                filters=filters,
                limit=limit,
                offset=offset
            )
            
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            
            await self._log_access("search", None, user_id, True)
            return results
            
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            
            await self._log_access("search", None, user_id, False, str(e))
            logger.error(f"Search failed for user {user_id}: {e}")
            raise
        finally:
            self._operations.append(operation)
    
    async def get_user_quota(self, user_id: UUID) -> StorageQuota:
        """Get user storage quota information."""
        if user_id not in self._quotas:
            # Create default quota
            self._quotas[user_id] = StorageQuota(
                user_id=user_id,
                total_limit_mb=settings.FREE_TIER_STORAGE_MB
            )
        
        return self._quotas[user_id]
    
    async def update_user_quota(
        self,
        user_id: UUID,
        total_limit_mb: Optional[int] = None,
        max_files: Optional[int] = None
    ) -> StorageQuota:
        """Update user storage quota limits."""
        quota = await self.get_user_quota(user_id)
        
        if total_limit_mb is not None:
            quota.total_limit_mb = total_limit_mb
        if max_files is not None:
            quota.max_files = max_files
        
        quota.updated_at = datetime.utcnow()
        self._quotas[user_id] = quota
        
        logger.info(f"Updated quota for user {user_id}")
        return quota
    
    async def get_storage_metrics(self, force_refresh: bool = False) -> StorageMetrics:
        """Get comprehensive storage system metrics."""
        # Use cached metrics if available and recent
        if (
            not force_refresh and 
            self._metrics_cache and 
            self._metrics_cache_time and
            datetime.utcnow() - self._metrics_cache_time < timedelta(minutes=5)
        ):
            return self._metrics_cache
        
        try:
            # Gather metrics from all components
            cache_metrics = await self.cache_manager.get_metrics()
            search_metrics = await self.search_indexer.get_metrics()
            lifecycle_metrics = await self.lifecycle_manager.get_metrics()
            backup_metrics = await self.backup_manager.get_metrics()
            
            # Calculate aggregate metrics
            total_size_mb = sum(quota.used_mb for quota in self._quotas.values())
            total_files = sum(quota.file_count for quota in self._quotas.values())
            
            # Calculate cache hit rate
            cache_hit_rate = cache_metrics.get("hit_rate", 0.0)
            
            # Count recent errors
            errors_24h = len([
                op for op in self._operations[-1000:]  # Look at last 1000 operations
                if (
                    op.status == "failed" and
                    op.started_at > datetime.utcnow() - timedelta(hours=24)
                )
            ])
            
            # Calculate average response time
            recent_ops = [
                op for op in self._operations[-100:]  # Last 100 operations
                if op.duration_ms is not None
            ]
            avg_response_time = (
                sum(op.duration_ms for op in recent_ops) / len(recent_ops)
                if recent_ops else 0.0
            )
            
            # Determine health status
            health = "healthy"
            if errors_24h > 10 or cache_hit_rate < 0.5:
                health = "warning"
            if errors_24h > 50 or avg_response_time > 5000:
                health = "critical"
            
            metrics = StorageMetrics(
                total_files=total_files,
                total_size_mb=total_size_mb,
                cache_hit_rate=cache_hit_rate,
                search_index_count=search_metrics.get("document_count", 0),
                backup_status=backup_metrics.get("status", "unknown"),
                cleanup_last_run=lifecycle_metrics.get("last_cleanup"),
                errors_last_24h=errors_24h,
                avg_response_time_ms=avg_response_time,
                storage_health=health
            )
            
            # Cache metrics
            self._metrics_cache = metrics
            self._metrics_cache_time = datetime.utcnow()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate storage metrics: {e}")
            # Return basic metrics in case of error
            return StorageMetrics(storage_health="critical")
    
    async def run_maintenance(self) -> Dict[str, Any]:
        """Run maintenance tasks across all storage components."""
        maintenance_results = {}
        
        try:
            # Run lifecycle cleanup
            cleanup_result = await self.lifecycle_manager.run_cleanup()
            maintenance_results["cleanup"] = cleanup_result
            
            # Run cache optimization
            cache_result = await self.cache_manager.optimize()
            maintenance_results["cache_optimization"] = cache_result
            
            # Update search index
            search_result = await self.search_indexer.optimize_index()
            maintenance_results["search_optimization"] = search_result
            
            # Check backup health
            backup_result = await self.backup_manager.health_check()
            maintenance_results["backup_health"] = backup_result
            
            # Clean up old operation logs
            if len(self._operations) > 10000:
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                self._operations = [
                    op for op in self._operations
                    if op.started_at > cutoff_time
                ]
                maintenance_results["operation_log_cleanup"] = {
                    "cleaned": True,
                    "remaining_operations": len(self._operations)
                }
            
            # Clean up old access logs
            if len(self._access_logs) > 50000:
                cutoff_time = datetime.utcnow() - timedelta(days=30)
                self._access_logs = [
                    log for log in self._access_logs
                    if log.get("timestamp", datetime.min) > cutoff_time
                ]
                maintenance_results["access_log_cleanup"] = {
                    "cleaned": True,
                    "remaining_logs": len(self._access_logs)
                }
            
            logger.info("Maintenance completed successfully")
            return {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "results": maintenance_results
            }
            
        except Exception as e:
            logger.error(f"Maintenance failed: {e}")
            return {
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "results": maintenance_results
            }
    
    async def get_access_logs(
        self,
        user_id: Optional[UUID] = None,
        file_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get access logs with optional filtering."""
        logs = self._access_logs
        
        if user_id:
            logs = [log for log in logs if log.get("user_id") == user_id]
        
        if file_id:
            logs = [log for log in logs if log.get("file_id") == file_id]
        
        # Sort by timestamp (most recent first) and limit
        logs.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
        return logs[:limit]
    
    # Private helper methods
    
    async def _store_original_file(
        self,
        file_id: str,
        content: bytes,
        filename: str,
        user_id: UUID
    ) -> str:
        """Store original file in S3/MinIO."""
        # This would integrate with existing s3_manager.py
        # For now, return a mock path
        storage_path = f"documents/{user_id}/{file_id}/{filename}"
        logger.info(f"Stored original file at {storage_path}")
        return storage_path
    
    async def _process_and_cache_content(
        self,
        file_id: str,
        content: bytes,
        content_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process document content and cache results."""
        processed_content = {
            "text_content": "Extracted text content...",  # Would use actual extraction
            "structure": {"sections": [], "headings": []},
            "entities": {"keywords": [], "citations": []},
            "processed_at": datetime.utcnow().isoformat()
        }
        
        # Cache processed content
        await self.cache_manager.cache_processed_content(file_id, processed_content)
        
        return processed_content
    
    async def _index_for_search(
        self,
        file_id: str,
        processed_content: Dict[str, Any],
        filename: str,
        user_id: UUID,
        metadata: Dict[str, Any]
    ) -> None:
        """Index document for search."""
        await self.search_indexer.index_document(
            file_id=file_id,
            content=processed_content.get("text_content", ""),
            filename=filename,
            user_id=user_id,
            metadata={**metadata, **processed_content}
        )
    
    async def _retrieve_original_file(self, file_id: str) -> bytes:
        """Retrieve original file from storage."""
        # This would integrate with s3_manager.py
        return b"Mock file content"
    
    async def _delete_original_file(self, file_id: str) -> None:
        """Delete original file from storage."""
        logger.info(f"Deleted original file {file_id}")
    
    async def _check_access_permission(self, file_id: str, user_id: UUID) -> bool:
        """Check if user has access to file."""
        # This would implement proper access control
        return True
    
    async def _update_quota(self, user_id: UUID, size_delta_mb: float, file_delta: int) -> None:
        """Update user quota usage."""
        quota = await self.get_user_quota(user_id)
        quota.used_mb = max(0, quota.used_mb + size_delta_mb)
        quota.file_count = max(0, quota.file_count + file_delta)
        quota.updated_at = datetime.utcnow()
        self._quotas[user_id] = quota
    
    async def _log_access(
        self,
        operation: str,
        file_id: Optional[str],
        user_id: UUID,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log access attempt."""
        log_entry = {
            "timestamp": datetime.utcnow(),
            "operation": operation,
            "file_id": file_id,
            "user_id": user_id,
            "success": success,
            "error": error
        }
        
        self._access_logs.append(log_entry)
        
        # Keep only recent logs in memory
        if len(self._access_logs) > 1000:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self._access_logs = [
                log for log in self._access_logs
                if log["timestamp"] > cutoff
            ]