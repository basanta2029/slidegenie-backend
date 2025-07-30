"""
Rate limiting service using Redis for SlideGenie authentication system.

Provides flexible rate limiting with multiple strategies:
- Fixed window rate limiting
- Sliding window rate limiting  
- Distributed rate limiting across multiple servers
- Per-IP, per-user, and per-endpoint rate limits
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.cache.redis import RedisCache, get_redis

logger = get_logger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitResult:
    """Result of rate limit check."""
    
    def __init__(
        self,
        allowed: bool,
        limit: int,
        remaining: int,
        reset_time: datetime,
        retry_after: Optional[int] = None,
    ):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        return {
            "allowed": self.allowed,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_time": self.reset_time.isoformat(),
            "retry_after": self.retry_after,
        }


class RateLimiter:
    """
    Redis-based rate limiter with multiple strategies.
    
    Supports:
    - Fixed window: Simple counter within time windows
    - Sliding window: More accurate limiting using sorted sets
    - Token bucket: Smooth rate limiting with burst capacity
    """
    
    def __init__(
        self,
        cache: Optional[RedisCache] = None,
        default_limit: int = 60,
        default_window: int = 60,
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
    ):
        """
        Initialize rate limiter.
        
        Args:
            cache: Redis cache instance
            default_limit: Default requests per window
            default_window: Default window size in seconds
            strategy: Rate limiting strategy
        """
        self.cache = cache or RedisCache(prefix="rate_limit")
        self.default_limit = default_limit
        self.default_window = default_window
        self.strategy = strategy
        
        # Predefined rate limits for different endpoints
        self.endpoint_limits = {
            "auth:login": {"limit": 5, "window": 300},  # 5 attempts per 5 minutes
            "auth:register": {"limit": 3, "window": 3600},  # 3 attempts per hour
            "auth:refresh": {"limit": 10, "window": 60},  # 10 per minute
            "auth:reset_password": {"limit": 3, "window": 3600},  # 3 per hour
            "auth:verify_email": {"limit": 5, "window": 300},  # 5 per 5 minutes
            "api:general": {"limit": 100, "window": 60},  # 100 per minute
            "upload:file": {"limit": 10, "window": 300},  # 10 uploads per 5 minutes
        }
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        endpoint: Optional[str] = None,
    ) -> RateLimitResult:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit: Request limit (overrides default)
            window: Window size in seconds (overrides default)
            endpoint: Endpoint name for specific limits
            
        Returns:
            RateLimitResult with limit status
        """
        # Get endpoint-specific limits if provided
        if endpoint and endpoint in self.endpoint_limits:
            endpoint_config = self.endpoint_limits[endpoint]
            limit = limit or endpoint_config["limit"]
            window = window or endpoint_config["window"]
        
        # Use defaults if not specified
        limit = limit or self.default_limit
        window = window or self.default_window
        
        # Choose strategy
        if self.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window_check(identifier, limit, window)
        elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window_check(identifier, limit, window)
        elif self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_check(identifier, limit, window)
        else:
            # Fallback to sliding window
            return await self._sliding_window_check(identifier, limit, window)
    
    async def _fixed_window_check(
        self,
        identifier: str,
        limit: int,
        window: int,
    ) -> RateLimitResult:
        """
        Fixed window rate limiting using simple counter.
        
        Args:
            identifier: Unique identifier
            limit: Request limit
            window: Window size in seconds
            
        Returns:
            RateLimitResult
        """
        now = int(time.time())
        window_start = now - (now % window)
        key = f"fixed:{identifier}:{window_start}"
        
        try:
            client = await get_redis()
            
            # Use pipeline for atomic operations
            async with client.pipeline() as pipe:
                pipe.incr(key)
                pipe.expire(key, window)
                results = await pipe.execute()
            
            current_count = results[0]
            remaining = max(0, limit - current_count)
            allowed = current_count <= limit
            reset_time = datetime.fromtimestamp(window_start + window)
            retry_after = None if allowed else window - (now % window)
            
            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after,
            )
            
        except Exception as e:
            logger.error(f"Fixed window rate limit error: {e}")
            # Fail open - allow request if Redis is down
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_time=datetime.now() + timedelta(seconds=window),
            )
    
    async def _sliding_window_check(
        self,
        identifier: str,
        limit: int,
        window: int,
    ) -> RateLimitResult:
        """
        Sliding window rate limiting using sorted sets.
        
        Args:
            identifier: Unique identifier
            limit: Request limit
            window: Window size in seconds
            
        Returns:
            RateLimitResult
        """
        now = time.time()
        window_start = now - window
        key = f"sliding:{identifier}"
        
        try:
            client = await get_redis()
            
            # Use pipeline for atomic operations
            async with client.pipeline() as pipe:
                # Remove old entries
                pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current requests
                pipe.zcard(key)
                
                # Add current request with timestamp as score
                pipe.zadd(key, {str(now): now})
                
                # Set expiration
                pipe.expire(key, window)
                
                results = await pipe.execute()
            
            current_count = results[1] + 1  # +1 for the request we just added
            remaining = max(0, limit - current_count)
            allowed = current_count <= limit
            reset_time = datetime.fromtimestamp(now + window)
            
            # If not allowed, remove the request we just added
            if not allowed:
                await client.zrem(key, str(now))
                retry_after = int(window)
            else:
                retry_after = None
            
            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after,
            )
            
        except Exception as e:
            logger.error(f"Sliding window rate limit error: {e}")
            # Fail open - allow request if Redis is down
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_time=datetime.now() + timedelta(seconds=window),
            )
    
    async def _token_bucket_check(
        self,
        identifier: str,
        limit: int,
        window: int,
    ) -> RateLimitResult:
        """
        Token bucket rate limiting for smooth rate limiting.
        
        Args:
            identifier: Unique identifier
            limit: Token bucket capacity
            window: Time to refill bucket (in seconds)
            
        Returns:
            RateLimitResult
        """
        now = time.time()
        key = f"bucket:{identifier}"
        refill_rate = limit / window  # tokens per second
        
        try:
            client = await get_redis()
            
            # Get current bucket state
            bucket_data = await client.hmget(
                key,
                ["tokens", "last_refill"]
            )
            
            current_tokens = float(bucket_data[0] or limit)
            last_refill = float(bucket_data[1] or now)
            
            # Calculate tokens to add based on elapsed time
            elapsed = now - last_refill
            tokens_to_add = elapsed * refill_rate
            current_tokens = min(limit, current_tokens + tokens_to_add)
            
            # Check if we have tokens available
            allowed = current_tokens >= 1.0
            
            if allowed:
                current_tokens -= 1.0
            
            # Update bucket state
            await client.hmset(key, {
                "tokens": current_tokens,
                "last_refill": now,
            })
            await client.expire(key, window * 2)
            
            remaining = int(current_tokens)
            reset_time = datetime.fromtimestamp(
                now + ((limit - current_tokens) / refill_rate)
            )
            retry_after = None if allowed else int((1.0 - current_tokens) / refill_rate)
            
            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after,
            )
            
        except Exception as e:
            logger.error(f"Token bucket rate limit error: {e}")
            # Fail open - allow request if Redis is down
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_time=datetime.now() + timedelta(seconds=window),
            )
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        endpoint: Optional[str] = None,
    ) -> Dict:
        """
        Get current rate limit status without consuming a request.
        
        Args:
            identifier: Unique identifier
            endpoint: Endpoint name for specific limits
            
        Returns:
            Dictionary with current status
        """
        # Get endpoint-specific limits if provided
        limit = self.default_limit
        window = self.default_window
        
        if endpoint and endpoint in self.endpoint_limits:
            endpoint_config = self.endpoint_limits[endpoint]
            limit = endpoint_config["limit"]
            window = endpoint_config["window"]
        
        try:
            if self.strategy == RateLimitStrategy.SLIDING_WINDOW:
                now = time.time()
                window_start = now - window
                key = f"sliding:{identifier}"
                
                client = await get_redis()
                
                # Clean old entries and count current
                async with client.pipeline() as pipe:
                    pipe.zremrangebyscore(key, 0, window_start)
                    pipe.zcard(key)
                    results = await pipe.execute()
                
                current_count = results[1]
                remaining = max(0, limit - current_count)
                
                return {
                    "limit": limit,
                    "remaining": remaining,
                    "current": current_count,
                    "window": window,
                    "strategy": self.strategy.value,
                }
        
        except Exception as e:
            logger.error(f"Get rate limit status error: {e}")
        
        return {
            "limit": limit,
            "remaining": limit,
            "current": 0,
            "window": window,
            "strategy": self.strategy.value,
        }
    
    async def reset_rate_limit(
        self,
        identifier: str,
        endpoint: Optional[str] = None,
    ) -> bool:
        """
        Reset rate limit for identifier.
        
        Args:
            identifier: Unique identifier
            endpoint: Endpoint name (used for key generation)
            
        Returns:
            Success status
        """
        try:
            client = await get_redis()
            patterns = [
                f"fixed:{identifier}:*",
                f"sliding:{identifier}",
                f"bucket:{identifier}",
            ]
            
            keys_deleted = 0
            for pattern in patterns:
                keys = []
                async for key in client.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    keys_deleted += await client.delete(*keys)
            
            logger.info(f"Reset rate limit for {identifier}, deleted {keys_deleted} keys")
            return True
            
        except Exception as e:
            logger.error(f"Reset rate limit error: {e}")
            return False
    
    async def increment_custom_counter(
        self,
        identifier: str,
        counter_name: str,
        increment: int = 1,
        expire: Optional[int] = None,
    ) -> int:
        """
        Increment a custom counter for tracking purposes.
        
        Args:
            identifier: Unique identifier
            counter_name: Name of the counter
            increment: Amount to increment
            expire: Expiration time in seconds
            
        Returns:
            New counter value
        """
        key = f"counter:{counter_name}:{identifier}"
        
        try:
            client = await get_redis()
            
            async with client.pipeline() as pipe:
                pipe.incrby(key, increment)
                if expire:
                    pipe.expire(key, expire)
                results = await pipe.execute()
            
            return results[0]
            
        except Exception as e:
            logger.error(f"Increment custom counter error: {e}")
            return 0
    
    async def get_counter_value(
        self,
        identifier: str,
        counter_name: str,
    ) -> int:
        """
        Get current value of a custom counter.
        
        Args:
            identifier: Unique identifier
            counter_name: Name of the counter
            
        Returns:
            Current counter value
        """
        key = f"counter:{counter_name}:{identifier}"
        
        try:
            client = await get_redis()
            value = await client.get(key)
            return int(value) if value else 0
            
        except Exception as e:
            logger.error(f"Get counter value error: {e}")
            return 0


# Create default rate limiter instance
rate_limiter = RateLimiter(
    default_limit=20,  # 20 requests per minute by default
    default_window=60,
    strategy=RateLimitStrategy.SLIDING_WINDOW,
)