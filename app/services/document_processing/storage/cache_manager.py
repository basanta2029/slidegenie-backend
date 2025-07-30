"""
Cache manager for document processing system.

Provides Redis and PostgreSQL caching for processed document content,
metadata, and frequently accessed data with compression and optimization.
"""

import asyncio
import gzip
import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

import redis.asyncio as redis
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.infrastructure.cache.redis import get_redis

settings = get_settings()
logger = logging.getLogger(__name__)


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    default_ttl_seconds: int = Field(default=86400)  # 24 hours
    max_value_size_mb: float = Field(default=10.0)
    compression_threshold_kb: float = Field(default=100.0)  # Compress if > 100KB
    max_cache_size_mb: float = Field(default=1000.0)  # 1GB total cache
    eviction_policy: str = Field(default="lru")
    batch_size: int = Field(default=100)


class CacheStats(BaseModel):
    """Cache statistics and metrics."""
    total_keys: int = 0
    total_size_mb: float = 0.0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    compression_ratio: float = 0.0
    avg_response_time_ms: float = 0.0
    last_cleanup: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hit_count + self.miss_count
        return (self.hit_count / total) if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_keys": self.total_keys,
            "total_size_mb": round(self.total_size_mb, 2),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(self.hit_rate, 3),
            "eviction_count": self.eviction_count,
            "compression_ratio": round(self.compression_ratio, 3),
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None
        }


class CacheEntry(BaseModel):
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0)
    ttl_seconds: int = Field(default=86400)
    size_bytes: int = Field(default=0)
    compressed: bool = Field(default=False)
    tags: Set[str] = Field(default_factory=set)
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds <= 0:
            return False  # No expiration
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry_time
    
    @property
    def age_seconds(self) -> float:
        """Get entry age in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()


class CacheManager:
    """
    Advanced cache manager with Redis and PostgreSQL integration.
    
    Features:
    - Automatic compression for large values
    - LRU eviction with size limits
    - Cache statistics and monitoring
    - Batch operations for efficiency
    - Tag-based cache invalidation
    - Deduplication and optimization
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.stats = CacheStats()
        self._local_cache: Dict[str, CacheEntry] = {}
        self._cache_keys: Set[str] = set()
        self._response_times: List[float] = []
        self._lock = asyncio.Lock()
        
        # Cache key prefixes
        self.DOCUMENT_DATA_PREFIX = "doc:data:"
        self.PROCESSED_CONTENT_PREFIX = "doc:processed:"
        self.METADATA_PREFIX = "doc:meta:"
        self.USER_QUOTA_PREFIX = "user:quota:"
        self.SEARCH_CACHE_PREFIX = "search:cache:"
        self.TEMP_PREFIX = "temp:"
        
        logger.info("CacheManager initialized")
    
    async def initialize(self) -> None:
        """Initialize cache connections and resources."""
        try:
            self.redis_client = await get_redis()
            
            # Load existing cache keys
            await self._load_cache_keys()
            
            # Update statistics
            await self._update_stats()
            
            logger.info("Cache manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            raise
    
    async def cache_document_data(
        self,
        file_id: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Cache document data with metadata.
        
        Args:
            file_id: Document file ID
            data: Document data to cache
            ttl_seconds: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        key = f"{self.DOCUMENT_DATA_PREFIX}{file_id}"
        ttl = ttl_seconds or self.config.default_ttl_seconds
        
        return await self._set_cache_value(
            key, data, ttl, tags={"document", "metadata", file_id}
        )
    
    async def get_document_data(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get cached document data."""
        key = f"{self.DOCUMENT_DATA_PREFIX}{file_id}"
        return await self._get_cache_value(key)
    
    async def cache_processed_content(
        self,
        file_id: str,
        content: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Cache processed document content."""
        key = f"{self.PROCESSED_CONTENT_PREFIX}{file_id}"
        ttl = ttl_seconds or self.config.default_ttl_seconds * 2  # Longer TTL for processed content
        
        return await self._set_cache_value(
            key, content, ttl, tags={"processed", "content", file_id}
        )
    
    async def get_processed_content(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get cached processed content."""
        key = f"{self.PROCESSED_CONTENT_PREFIX}{file_id}"
        return await self._get_cache_value(key)
    
    async def cache_user_quota(
        self,
        user_id: UUID,
        quota_data: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Cache user quota information."""
        key = f"{self.USER_QUOTA_PREFIX}{user_id}"
        ttl = ttl_seconds or 3600  # 1 hour TTL for quota data
        
        return await self._set_cache_value(
            key, quota_data, ttl, tags={"quota", "user", str(user_id)}
        )
    
    async def get_user_quota(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cached user quota information."""
        key = f"{self.USER_QUOTA_PREFIX}{user_id}"
        return await self._get_cache_value(key)
    
    async def cache_search_results(
        self,
        query_hash: str,
        results: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Cache search results."""
        key = f"{self.SEARCH_CACHE_PREFIX}{query_hash}"
        ttl = ttl_seconds or 1800  # 30 minutes for search results
        
        return await self._set_cache_value(
            key, results, ttl, tags={"search", "results"}
        )
    
    async def get_search_results(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached search results."""
        key = f"{self.SEARCH_CACHE_PREFIX}{query_hash}"
        return await self._get_cache_value(key)
    
    async def set_temporary_data(
        self,
        temp_key: str,
        data: Any,
        ttl_seconds: int = 3600
    ) -> bool:
        """Set temporary data with short TTL."""
        key = f"{self.TEMP_PREFIX}{temp_key}"
        return await self._set_cache_value(
            key, data, ttl_seconds, tags={"temporary"}
        )
    
    async def get_temporary_data(self, temp_key: str) -> Optional[Any]:
        """Get temporary data."""
        key = f"{self.TEMP_PREFIX}{temp_key}"
        return await self._get_cache_value(key)
    
    async def delete_document_data(self, file_id: str) -> int:
        """Delete all cached data for a document."""
        keys_to_delete = [
            f"{self.DOCUMENT_DATA_PREFIX}{file_id}",
            f"{self.PROCESSED_CONTENT_PREFIX}{file_id}",
            f"{self.METADATA_PREFIX}{file_id}"
        ]
        
        deleted_count = 0
        for key in keys_to_delete:
            if await self._delete_cache_key(key):
                deleted_count += 1
        
        # Also invalidate by tag
        await self.invalidate_by_tags({file_id})
        
        logger.info(f"Deleted {deleted_count} cache entries for document {file_id}")
        return deleted_count
    
    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Invalidate cache entries by tags."""
        async with self._lock:
            deleted_count = 0
            keys_to_delete = []
            
            # Find keys with matching tags in local cache
            for key, entry in self._local_cache.items():
                if entry.tags.intersection(tags):
                    keys_to_delete.append(key)
            
            # Delete from both local and Redis
            for key in keys_to_delete:
                if await self._delete_cache_key(key):
                    deleted_count += 1
            
            logger.info(f"Invalidated {deleted_count} cache entries by tags: {tags}")
            return deleted_count
    
    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple cache values in a single operation."""
        start_time = datetime.utcnow()
        results = {}
        
        try:
            if self.redis_client:
                # Use Redis pipeline for efficiency
                pipe = self.redis_client.pipeline()
                for key in keys:
                    pipe.get(key)
                
                redis_results = await pipe.execute()
                
                for key, result in zip(keys, redis_results):
                    if result:
                        try:
                            value = await self._deserialize_value(result)
                            results[key] = value
                            self.stats.hit_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to deserialize cached value for {key}: {e}")
                            self.stats.miss_count += 1
                    else:
                        self.stats.miss_count += 1
            
            # Track response time
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._response_times.append(response_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch get failed: {e}")
            self.stats.miss_count += len(keys)
            return {}
    
    async def batch_set(
        self,
        items: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> int:
        """Set multiple cache values in a single operation."""
        ttl = ttl_seconds or self.config.default_ttl_seconds
        success_count = 0
        
        try:
            if self.redis_client:
                pipe = self.redis_client.pipeline()
                
                for key, value in items.items():
                    serialized_value = await self._serialize_value(value)
                    pipe.setex(key, ttl, serialized_value)
                
                results = await pipe.execute()
                success_count = sum(1 for result in results if result)
                
                # Update local cache
                async with self._lock:
                    for key, value in items.items():
                        if key in [r for r, success in zip(items.keys(), results) if success]:
                            size_bytes = len(str(value).encode('utf-8'))
                            entry = CacheEntry(
                                key=key,
                                value=value,
                                ttl_seconds=ttl,
                                size_bytes=size_bytes
                            )
                            self._local_cache[key] = entry
                            self._cache_keys.add(key)
            
            logger.info(f"Batch set completed: {success_count}/{len(items)} items cached")
            return success_count
            
        except Exception as e:
            logger.error(f"Batch set failed: {e}")
            return 0
    
    async def get_cache_size(self) -> Dict[str, Any]:
        """Get current cache size information."""
        total_size_bytes = 0
        key_count = 0
        
        if self.redis_client:
            try:
                # Get Redis memory usage
                info = await self.redis_client.info("memory")
                redis_memory_mb = info.get("used_memory", 0) / (1024 * 1024)
                
                # Count keys with our prefixes
                patterns = [
                    f"{self.DOCUMENT_DATA_PREFIX}*",
                    f"{self.PROCESSED_CONTENT_PREFIX}*",
                    f"{self.METADATA_PREFIX}*",
                    f"{self.USER_QUOTA_PREFIX}*",
                    f"{self.SEARCH_CACHE_PREFIX}*",
                    f"{self.TEMP_PREFIX}*"
                ]
                
                for pattern in patterns:
                    keys = await self.redis_client.keys(pattern)
                    key_count += len(keys)
                
                return {
                    "total_keys": key_count,
                    "redis_memory_mb": round(redis_memory_mb, 2),
                    "local_cache_entries": len(self._local_cache),
                    "estimated_size_mb": round(redis_memory_mb, 2)
                }
                
            except Exception as e:
                logger.error(f"Failed to get cache size: {e}")
        
        return {
            "total_keys": len(self._local_cache),
            "redis_memory_mb": 0.0,
            "local_cache_entries": len(self._local_cache),
            "estimated_size_mb": 0.0
        }
    
    async def optimize(self) -> Dict[str, Any]:
        """Optimize cache by removing expired entries and compressing data."""
        start_time = datetime.utcnow()
        optimization_results = {
            "expired_removed": 0,
            "compressed": 0,
            "deduplicated": 0,
            "memory_freed_mb": 0.0
        }
        
        try:
            # Remove expired entries
            expired_keys = []
            async with self._lock:
                for key, entry in self._local_cache.items():
                    if entry.is_expired:
                        expired_keys.append(key)
            
            for key in expired_keys:
                await self._delete_cache_key(key)
                optimization_results["expired_removed"] += 1
            
            # Compress large uncompressed entries
            if self.redis_client:
                compression_candidates = []
                for key, entry in self._local_cache.items():
                    if (
                        not entry.compressed and 
                        entry.size_bytes > self.config.compression_threshold_kb * 1024
                    ):
                        compression_candidates.append(key)
                
                for key in compression_candidates[:50]:  # Limit to 50 per optimization run
                    entry = self._local_cache.get(key)
                    if entry:
                        compressed_value = await self._compress_value(entry.value)
                        if len(compressed_value) < entry.size_bytes * 0.8:  # Only if 20%+ savings
                            await self.redis_client.setex(
                                key, 
                                entry.ttl_seconds, 
                                compressed_value
                            )
                            entry.compressed = True
                            entry.size_bytes = len(compressed_value)
                            optimization_results["compressed"] += 1
            
            # Update statistics
            await self._update_stats()
            self.stats.last_cleanup = datetime.utcnow()
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(f"Cache optimization completed in {duration_ms:.2f}ms: {optimization_results}")
            
            return {
                "status": "completed",
                "duration_ms": duration_ms,
                "results": optimization_results
            }
            
        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "results": optimization_results
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics."""
        await self._update_stats()
        
        # Calculate average response time
        if self._response_times:
            avg_response_time = sum(self._response_times) / len(self._response_times)
            # Keep only recent response times
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-500:]
        else:
            avg_response_time = 0.0
        
        self.stats.avg_response_time_ms = avg_response_time
        
        # Get cache size info
        size_info = await self.get_cache_size()
        self.stats.total_keys = size_info["total_keys"]
        self.stats.total_size_mb = size_info["estimated_size_mb"]
        
        return self.stats.to_dict()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check."""
        health_status = {
            "status": "healthy",
            "redis_connected": False,
            "response_time_ms": 0.0,
            "memory_usage_ok": True,
            "error_rate_ok": True,
            "issues": []
        }
        
        try:
            # Test Redis connection
            if self.redis_client:
                start_time = datetime.utcnow()
                await self.redis_client.ping()
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                health_status["redis_connected"] = True
                health_status["response_time_ms"] = response_time
                
                if response_time > 1000:  # > 1 second
                    health_status["status"] = "warning"
                    health_status["issues"].append("High Redis response time")
            
            # Check memory usage
            size_info = await self.get_cache_size()
            if size_info["estimated_size_mb"] > self.config.max_cache_size_mb:
                health_status["memory_usage_ok"] = False
                health_status["status"] = "warning"
                health_status["issues"].append("Cache size exceeds limit")
            
            # Check error rate (based on hit rate)
            if self.stats.hit_rate < 0.3:  # < 30% hit rate
                health_status["error_rate_ok"] = False
                if health_status["status"] == "healthy":
                    health_status["status"] = "warning"
                health_status["issues"].append("Low cache hit rate")
            
            if health_status["issues"]:
                health_status["status"] = "warning" if len(health_status["issues"]) == 1 else "critical"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                "status": "critical",
                "redis_connected": False,
                "error": str(e),
                "issues": ["Health check failed"]
            }
    
    # Private helper methods
    
    async def _set_cache_value(
        self,
        key: str,
        value: Any,
        ttl_seconds: int,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a cache value with metadata."""
        try:
            # Check size limit
            value_size = len(str(value).encode('utf-8'))
            if value_size > self.config.max_value_size_mb * 1024 * 1024:
                logger.warning(f"Value too large to cache: {key} ({value_size} bytes)")
                return False
            
            # Serialize value
            serialized_value = await self._serialize_value(value)
            
            # Compress if needed
            if value_size > self.config.compression_threshold_kb * 1024:
                serialized_value = await self._compress_value(serialized_value)
                compressed = True
            else:
                compressed = False
            
            # Store in Redis
            if self.redis_client:
                await self.redis_client.setex(key, ttl_seconds, serialized_value)
            
            # Update local cache and metadata
            async with self._lock:
                entry = CacheEntry(
                    key=key,
                    value=value,
                    ttl_seconds=ttl_seconds,
                    size_bytes=len(serialized_value),
                    compressed=compressed,
                    tags=tags or set()
                )
                self._local_cache[key] = entry
                self._cache_keys.add(key)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache value for key {key}: {e}")
            return False
    
    async def _get_cache_value(self, key: str) -> Optional[Any]:
        """Get a cache value with hit/miss tracking."""
        start_time = datetime.utcnow()
        
        try:
            # Check local cache first for metadata
            entry = self._local_cache.get(key)
            if entry and entry.is_expired:
                await self._delete_cache_key(key)
                self.stats.miss_count += 1
                return None
            
            # Get from Redis
            if self.redis_client:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    value = await self._deserialize_value(cached_data)
                    
                    # Update local cache metadata
                    if entry:
                        entry.last_accessed = datetime.utcnow()
                        entry.access_count += 1
                    
                    self.stats.hit_count += 1
                    
                    # Track response time
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    self._response_times.append(response_time)
                    
                    return value
            
            self.stats.miss_count += 1
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cache value for key {key}: {e}")
            self.stats.miss_count += 1
            return None
    
    async def _delete_cache_key(self, key: str) -> bool:
        """Delete a cache key from all stores."""
        try:
            deleted = False
            
            if self.redis_client:
                result = await self.redis_client.delete(key)
                deleted = result > 0
            
            # Remove from local cache
            async with self._lock:
                if key in self._local_cache:
                    del self._local_cache[key]
                    deleted = True
                
                self._cache_keys.discard(key)
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    async def _serialize_value(self, value: Any) -> bytes:
        """Serialize a value for storage."""
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value, default=str).encode('utf-8')
            else:
                return pickle.dumps(value)
        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            raise
    
    async def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize a stored value."""
        try:
            # Try decompression first
            try:
                data = gzip.decompress(data)
            except:
                pass  # Not compressed
            
            # Try JSON first (more common)
            try:
                return json.loads(data.decode('utf-8'))
            except:
                # Fall back to pickle
                return pickle.loads(data)
                
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise
    
    async def _compress_value(self, value: Any) -> bytes:
        """Compress a value for storage."""
        if isinstance(value, bytes):
            data = value
        else:
            data = await self._serialize_value(value)
        
        return gzip.compress(data, compresslevel=6)
    
    async def _load_cache_keys(self) -> None:
        """Load existing cache keys from Redis."""
        if not self.redis_client:
            return
        
        try:
            patterns = [
                f"{self.DOCUMENT_DATA_PREFIX}*",
                f"{self.PROCESSED_CONTENT_PREFIX}*",
                f"{self.METADATA_PREFIX}*",
                f"{self.USER_QUOTA_PREFIX}*",
                f"{self.SEARCH_CACHE_PREFIX}*",
                f"{self.TEMP_PREFIX}*"
            ]
            
            for pattern in patterns:
                keys = await self.redis_client.keys(pattern)
                self._cache_keys.update(key.decode('utf-8') if isinstance(key, bytes) else key for key in keys)
            
            logger.info(f"Loaded {len(self._cache_keys)} existing cache keys")
            
        except Exception as e:
            logger.error(f"Failed to load cache keys: {e}")
    
    async def _update_stats(self) -> None:
        """Update cache statistics."""
        try:
            size_info = await self.get_cache_size()
            self.stats.total_keys = size_info["total_keys"]
            self.stats.total_size_mb = size_info["estimated_size_mb"]
            
            # Calculate compression ratio
            compressed_entries = sum(1 for entry in self._local_cache.values() if entry.compressed)
            total_entries = len(self._local_cache)
            self.stats.compression_ratio = (
                compressed_entries / total_entries if total_entries > 0 else 0.0
            )
            
        except Exception as e:
            logger.error(f"Failed to update cache stats: {e}")