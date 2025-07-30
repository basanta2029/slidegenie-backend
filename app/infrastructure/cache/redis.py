"""
Redis cache configuration and utilities.
"""
import json
from typing import Any, Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Redis connection pool
redis_pool: Optional[redis.ConnectionPool] = None


async def get_redis_pool() -> redis.ConnectionPool:
    """
    Get or create Redis connection pool.
    
    Returns:
        Redis connection pool
    """
    global redis_pool
    
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            str(settings.REDIS_URL),
            decode_responses=True,
            max_connections=50,
        )
    
    return redis_pool


async def get_redis() -> redis.Redis:
    """
    Get Redis client instance.
    
    Returns:
        Redis client
    """
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)


async def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance (alias for compatibility).
    
    Returns:
        Redis client
    """
    return await get_redis()


class RedisCache:
    """
    Redis cache utility class.
    """
    
    def __init__(self, prefix: str = "slidegenie"):
        self.prefix = prefix
    
    def _make_key(self, key: str) -> str:
        """
        Create prefixed cache key.
        
        Args:
            key: Cache key
            
        Returns:
            Prefixed key
        """
        return f"{self.prefix}:{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            client = await get_redis()
            value = await client.get(self._make_key(key))
            
            if value:
                return json.loads(value)
            
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds
            
        Returns:
            Success status
        """
        try:
            client = await get_redis()
            serialized = json.dumps(value)
            
            if expire:
                await client.setex(
                    self._make_key(key),
                    expire,
                    serialized,
                )
            else:
                await client.set(
                    self._make_key(key),
                    serialized,
                )
            
            return True
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Success status
        """
        try:
            client = await get_redis()
            await client.delete(self._make_key(key))
            return True
        except RedisError as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            Existence status
        """
        try:
            client = await get_redis()
            return bool(await client.exists(self._make_key(key)))
        except RedisError as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def increment(
        self,
        key: str,
        amount: int = 1,
    ) -> Optional[int]:
        """
        Increment counter in cache.
        
        Args:
            key: Cache key
            amount: Increment amount
            
        Returns:
            New value or None
        """
        try:
            client = await get_redis()
            return await client.incrby(self._make_key(key), amount)
        except RedisError as e:
            logger.error(f"Redis increment error: {e}")
            return None
    
    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of key-value pairs
        """
        try:
            client = await get_redis()
            prefixed_keys = [self._make_key(k) for k in keys]
            values = await client.mget(prefixed_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            
            return result
        except RedisError as e:
            logger.error(f"Redis get_many error: {e}")
            return {}
    
    async def set_many(
        self,
        mapping: dict[str, Any],
        expire: Optional[int] = None,
    ) -> bool:
        """
        Set multiple values in cache.
        
        Args:
            mapping: Dictionary of key-value pairs
            expire: Expiration time in seconds
            
        Returns:
            Success status
        """
        try:
            client = await get_redis()
            
            # Prepare data
            data = {
                self._make_key(k): json.dumps(v)
                for k, v in mapping.items()
            }
            
            # Use pipeline for atomic operation
            async with client.pipeline() as pipe:
                pipe.mset(data)
                
                if expire:
                    for key in data:
                        pipe.expire(key, expire)
                
                await pipe.execute()
            
            return True
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Redis set_many error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            client = await get_redis()
            full_pattern = self._make_key(pattern)
            
            # Find all matching keys
            keys = []
            async for key in client.scan_iter(match=full_pattern):
                keys.append(key)
            
            # Delete in batches
            if keys:
                return await client.delete(*keys)
            
            return 0
        except RedisError as e:
            logger.error(f"Redis clear_pattern error: {e}")
            return 0


# Create default cache instance
cache = RedisCache()