"""
API Key management system for SlideGenie.

Handles API key generation, validation, rate limiting, and scope management 
for programmatic access to the SlideGenie platform.
"""

import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.infrastructure.cache import get_redis_client

logger = structlog.get_logger(__name__)
settings = get_settings()


class APIKeyScope(str):
    """API key scopes for different access levels."""
    # Read operations
    READ_PRESENTATIONS = "read:presentations"
    READ_TEMPLATES = "read:templates"
    READ_PROFILE = "read:profile"
    READ_ANALYTICS = "read:analytics"
    
    # Write operations
    WRITE_PRESENTATIONS = "write:presentations"
    WRITE_TEMPLATES = "write:templates"
    WRITE_PROFILE = "write:profile"
    
    # Management operations
    MANAGE_PRESENTATIONS = "manage:presentations"
    MANAGE_TEMPLATES = "manage:templates"
    MANAGE_USERS = "manage:users"
    
    # Generation operations
    GENERATE_PRESENTATIONS = "generate:presentations"
    EXECUTE_AI = "execute:ai"
    
    # Export operations
    EXPORT_PRESENTATIONS = "export:presentations"
    EXPORT_DATA = "export:data"
    
    # Admin operations
    ADMIN_SYSTEM = "admin:system"
    ADMIN_ANALYTICS = "admin:analytics"


class APIKeyTier(str):
    """API key tiers with different limits."""
    FREE = "free"
    ACADEMIC = "academic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class APIKeyMetadata(BaseModel):
    """API key metadata and usage information."""
    name: str
    description: Optional[str] = None
    tier: APIKeyTier = APIKeyTier.FREE
    scopes: Set[str] = Field(default_factory=set)
    
    # Usage limits
    rate_limit_per_hour: int = 100
    rate_limit_per_day: int = 1000
    monthly_requests_limit: Optional[int] = None
    
    # Access restrictions
    ip_whitelist: List[str] = Field(default_factory=list)
    allowed_origins: List[str] = Field(default_factory=list)
    
    # Usage tracking
    total_requests: int = 0
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    last_used_user_agent: Optional[str] = None
    
    # Validity
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class APIKey(BaseModel):
    """API key model."""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    key_prefix: str  # First 8 characters for identification
    key_hash: str    # Hashed full key for validation
    metadata: APIKeyMetadata
    
    @classmethod
    def create(
        cls,
        user_id: UUID,
        name: str,
        scopes: Set[str],
        tier: APIKeyTier = APIKeyTier.FREE,
        expires_days: Optional[int] = None,
        **kwargs
    ) -> tuple['APIKey', str]:
        """Create new API key with full key value."""
        # Generate API key
        full_key = cls._generate_api_key()
        key_prefix = full_key[:8]
        key_hash = cls._hash_key(full_key)
        
        # Set expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        # Create metadata
        metadata = APIKeyMetadata(
            name=name,
            tier=tier,
            scopes=scopes,
            expires_at=expires_at,
            **kwargs
        )
        
        # Set tier-based limits
        cls._apply_tier_limits(metadata, tier)
        
        api_key = cls(
            user_id=user_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
            metadata=metadata,
        )
        
        return api_key, full_key
    
    @staticmethod
    def _generate_api_key() -> str:
        """Generate a secure API key."""
        # Format: sg_<32_char_random_string>
        random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        return f"sg_{random_part}"
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def _apply_tier_limits(metadata: APIKeyMetadata, tier: APIKeyTier) -> None:
        """Apply tier-specific limits to API key."""
        if tier == APIKeyTier.FREE:
            metadata.rate_limit_per_hour = 100
            metadata.rate_limit_per_day = 1000
            metadata.monthly_requests_limit = 5000
        elif tier == APIKeyTier.ACADEMIC:
            metadata.rate_limit_per_hour = 500
            metadata.rate_limit_per_day = 5000
            metadata.monthly_requests_limit = 25000
        elif tier == APIKeyTier.PROFESSIONAL:
            metadata.rate_limit_per_hour = 2000
            metadata.rate_limit_per_day = 20000
            metadata.monthly_requests_limit = 100000
        elif tier == APIKeyTier.ENTERPRISE:
            metadata.rate_limit_per_hour = 10000
            metadata.rate_limit_per_day = 100000
            metadata.monthly_requests_limit = None  # Unlimited
    
    def validate_key(self, provided_key: str) -> bool:
        """Validate provided key against stored hash."""
        return self._hash_key(provided_key) == self.key_hash
    
    def has_scope(self, required_scope: str) -> bool:
        """Check if API key has required scope."""
        return required_scope in self.metadata.scopes
    
    def has_any_scope(self, required_scopes: List[str]) -> bool:
        """Check if API key has any of the required scopes."""
        return any(scope in self.metadata.scopes for scope in required_scopes)
    
    def can_access_from_ip(self, ip_address: str) -> bool:
        """Check if API key allows access from IP."""
        if not self.metadata.ip_whitelist:
            return True
        return ip_address in self.metadata.ip_whitelist
    
    def update_usage(self, ip_address: str, user_agent: str) -> None:
        """Update usage statistics."""
        self.metadata.total_requests += 1
        self.metadata.last_used_at = datetime.now(timezone.utc)
        self.metadata.last_used_ip = ip_address
        self.metadata.last_used_user_agent = user_agent


class APIKeyService:
    """Service for managing API keys."""
    
    def __init__(self):
        self._keys: Dict[str, APIKey] = {}  # key_hash -> APIKey
        self._user_keys: Dict[UUID, List[APIKey]] = {}  # user_id -> [APIKey]
    
    async def create_api_key(
        self,
        user_id: UUID,
        name: str,
        scopes: Set[str],
        tier: APIKeyTier = APIKeyTier.FREE,
        expires_days: Optional[int] = None,
        description: Optional[str] = None,
        ip_whitelist: Optional[List[str]] = None,
    ) -> tuple[APIKey, str]:
        """Create new API key."""
        # Validate scopes
        valid_scopes = self._get_valid_scopes_for_tier(tier)
        invalid_scopes = scopes - valid_scopes
        if invalid_scopes:
            raise ValueError(f"Invalid scopes for tier {tier}: {invalid_scopes}")
        
        # Check user key limits
        user_keys = await self.get_user_api_keys(user_id)
        if len(user_keys) >= self._get_max_keys_for_tier(tier):
            raise ValueError(f"Maximum API keys reached for tier {tier}")
        
        # Create API key
        api_key, full_key = APIKey.create(
            user_id=user_id,
            name=name,
            scopes=scopes,
            tier=tier,
            expires_days=expires_days,
            description=description,
            ip_whitelist=ip_whitelist or [],
        )
        
        # Store API key
        self._keys[api_key.key_hash] = api_key
        if user_id not in self._user_keys:
            self._user_keys[user_id] = []
        self._user_keys[user_id].append(api_key)
        
        logger.info(
            "api_key_created",
            user_id=str(user_id),
            key_id=str(api_key.id),
            key_prefix=api_key.key_prefix,
            tier=tier,
            scopes=list(scopes),
        )
        
        return api_key, full_key
    
    async def validate_api_key(self, provided_key: str) -> Optional[APIKey]:
        """Validate API key and return key object if valid."""
        if not provided_key.startswith("sg_"):
            return None
        
        key_hash = APIKey._hash_key(provided_key)
        api_key = self._keys.get(key_hash)
        
        if not api_key:
            logger.warning("api_key_not_found", key_prefix=provided_key[:8])
            return None
        
        # Check if key is active
        if not api_key.metadata.is_active:
            logger.warning("inactive_api_key_used", key_id=str(api_key.id))
            return None
        
        # Check if key is expired
        if api_key.metadata.is_expired:
            logger.warning("expired_api_key_used", key_id=str(api_key.id))
            return None
        
        # Validate key
        if not api_key.validate_key(provided_key):
            logger.warning("invalid_api_key_used", key_id=str(api_key.id))
            return None
        
        return api_key
    
    async def check_rate_limit(
        self,
        api_key: APIKey,
        ip_address: str,
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if API key has exceeded rate limits."""
        redis = await get_redis_client()
        now = datetime.now(timezone.utc)
        
        # Check hourly limit
        hour_key = f"api_rate:{api_key.key_hash}:hour:{now.strftime('%Y%m%d%H')}"
        hour_count = await redis.get(hour_key)
        hour_count = int(hour_count) if hour_count else 0
        
        if hour_count >= api_key.metadata.rate_limit_per_hour:
            return False, {
                "limit_type": "hourly",
                "limit": api_key.metadata.rate_limit_per_hour,
                "current": hour_count,
                "reset_at": now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
            }
        
        # Check daily limit
        day_key = f"api_rate:{api_key.key_hash}:day:{now.strftime('%Y%m%d')}"
        day_count = await redis.get(day_key)
        day_count = int(day_count) if day_count else 0
        
        if day_count >= api_key.metadata.rate_limit_per_day:
            return False, {
                "limit_type": "daily",
                "limit": api_key.metadata.rate_limit_per_day,
                "current": day_count,
                "reset_at": now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
            }
        
        # Check monthly limit
        if api_key.metadata.monthly_requests_limit:
            month_key = f"api_rate:{api_key.key_hash}:month:{now.strftime('%Y%m')}"
            month_count = await redis.get(month_key)
            month_count = int(month_count) if month_count else 0
            
            if month_count >= api_key.metadata.monthly_requests_limit:
                return False, {
                    "limit_type": "monthly",
                    "limit": api_key.metadata.monthly_requests_limit,
                    "current": month_count,
                    "reset_at": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32),
                }
        
        return True, {}
    
    async def record_api_usage(
        self,
        api_key: APIKey,
        ip_address: str,
        user_agent: str,
    ) -> None:
        """Record API key usage."""
        redis = await get_redis_client()
        now = datetime.now(timezone.utc)
        
        # Update usage counters
        hour_key = f"api_rate:{api_key.key_hash}:hour:{now.strftime('%Y%m%d%H')}"
        day_key = f"api_rate:{api_key.key_hash}:day:{now.strftime('%Y%m%d')}"
        month_key = f"api_rate:{api_key.key_hash}:month:{now.strftime('%Y%m')}"
        
        # Increment counters with appropriate TTL
        await redis.incr(hour_key)
        await redis.expire(hour_key, 3600)  # 1 hour
        
        await redis.incr(day_key)
        await redis.expire(day_key, 86400)  # 1 day
        
        await redis.incr(month_key)
        await redis.expire(month_key, 2678400)  # 31 days
        
        # Update API key metadata
        api_key.update_usage(ip_address, user_agent)
        
        logger.debug(
            "api_usage_recorded",
            key_id=str(api_key.id),
            ip_address=ip_address,
            total_requests=api_key.metadata.total_requests,
        )
    
    async def get_user_api_keys(self, user_id: UUID) -> List[APIKey]:
        """Get all API keys for a user."""
        return self._user_keys.get(user_id, [])
    
    async def revoke_api_key(self, user_id: UUID, key_id: UUID) -> bool:
        """Revoke an API key."""
        user_keys = await self.get_user_api_keys(user_id)
        
        for api_key in user_keys:
            if api_key.id == key_id:
                api_key.metadata.is_active = False
                logger.info("api_key_revoked", user_id=str(user_id), key_id=str(key_id))
                return True
        
        return False
    
    async def delete_api_key(self, user_id: UUID, key_id: UUID) -> bool:
        """Delete an API key."""
        user_keys = await self.get_user_api_keys(user_id)
        
        for i, api_key in enumerate(user_keys):
            if api_key.id == key_id:
                # Remove from storage
                if api_key.key_hash in self._keys:
                    del self._keys[api_key.key_hash]
                user_keys.pop(i)
                
                logger.info("api_key_deleted", user_id=str(user_id), key_id=str(key_id))
                return True
        
        return False
    
    async def get_api_key_usage_stats(self, api_key: APIKey) -> Dict[str, Any]:
        """Get usage statistics for API key."""
        redis = await get_redis_client()
        now = datetime.now(timezone.utc)
        
        # Get current usage
        hour_key = f"api_rate:{api_key.key_hash}:hour:{now.strftime('%Y%m%d%H')}"
        day_key = f"api_rate:{api_key.key_hash}:day:{now.strftime('%Y%m%d')}"
        month_key = f"api_rate:{api_key.key_hash}:month:{now.strftime('%Y%m')}"
        
        hour_count = await redis.get(hour_key)
        day_count = await redis.get(day_key)
        month_count = await redis.get(month_key)
        
        return {
            "key_id": str(api_key.id),
            "total_requests": api_key.metadata.total_requests,
            "last_used_at": api_key.metadata.last_used_at,
            "current_hour_usage": int(hour_count) if hour_count else 0,
            "current_day_usage": int(day_count) if day_count else 0,
            "current_month_usage": int(month_count) if month_count else 0,
            "limits": {
                "hourly": api_key.metadata.rate_limit_per_hour,
                "daily": api_key.metadata.rate_limit_per_day,
                "monthly": api_key.metadata.monthly_requests_limit,
            },
            "remaining": {
                "hourly": api_key.metadata.rate_limit_per_hour - (int(hour_count) if hour_count else 0),
                "daily": api_key.metadata.rate_limit_per_day - (int(day_count) if day_count else 0),
                "monthly": (
                    api_key.metadata.monthly_requests_limit - (int(month_count) if month_count else 0)
                    if api_key.metadata.monthly_requests_limit else None
                ),
            },
        }
    
    def _get_valid_scopes_for_tier(self, tier: APIKeyTier) -> Set[str]:
        """Get valid scopes for API key tier."""
        base_scopes = {
            APIKeyScope.READ_PRESENTATIONS,
            APIKeyScope.READ_TEMPLATES,
            APIKeyScope.READ_PROFILE,
        }
        
        if tier in [APIKeyTier.ACADEMIC, APIKeyTier.PROFESSIONAL, APIKeyTier.ENTERPRISE]:
            base_scopes.update({
                APIKeyScope.WRITE_PRESENTATIONS,
                APIKeyScope.WRITE_TEMPLATES,
                APIKeyScope.GENERATE_PRESENTATIONS,
                APIKeyScope.EXPORT_PRESENTATIONS,
            })
        
        if tier in [APIKeyTier.PROFESSIONAL, APIKeyTier.ENTERPRISE]:
            base_scopes.update({
                APIKeyScope.MANAGE_PRESENTATIONS,
                APIKeyScope.MANAGE_TEMPLATES,
                APIKeyScope.READ_ANALYTICS,
                APIKeyScope.EXECUTE_AI,
            })
        
        if tier == APIKeyTier.ENTERPRISE:
            base_scopes.update({
                APIKeyScope.MANAGE_USERS,
                APIKeyScope.ADMIN_ANALYTICS,
                APIKeyScope.EXPORT_DATA,
            })
        
        return base_scopes
    
    def _get_max_keys_for_tier(self, tier: APIKeyTier) -> int:
        """Get maximum number of API keys for tier."""
        limits = {
            APIKeyTier.FREE: 2,
            APIKeyTier.ACADEMIC: 5,
            APIKeyTier.PROFESSIONAL: 10,
            APIKeyTier.ENTERPRISE: 50,
        }
        return limits.get(tier, 2)


class APIKeyManager:
    """High-level API key management interface."""
    
    def __init__(self):
        self.service = APIKeyService()
    
    async def authenticate_request(
        self,
        api_key: str,
        required_scopes: List[str],
        ip_address: str,
        user_agent: str,
    ) -> tuple[bool, Optional[APIKey], Optional[Dict[str, Any]]]:
        """Authenticate API request with rate limiting."""
        # Validate API key
        key_obj = await self.service.validate_api_key(api_key)
        if not key_obj:
            return False, None, {"error": "Invalid API key"}
        
        # Check IP whitelist
        if not key_obj.can_access_from_ip(ip_address):
            logger.warning(
                "api_key_ip_denied",
                key_id=str(key_obj.id),
                ip_address=ip_address,
            )
            return False, key_obj, {"error": "IP address not allowed"}
        
        # Check scopes
        if required_scopes and not key_obj.has_any_scope(required_scopes):
            logger.warning(
                "api_key_insufficient_scope",
                key_id=str(key_obj.id),
                required=required_scopes,
                available=list(key_obj.metadata.scopes),
            )
            return False, key_obj, {"error": "Insufficient permissions"}
        
        # Check rate limits
        rate_ok, rate_info = await self.service.check_rate_limit(key_obj, ip_address)
        if not rate_ok:
            logger.warning(
                "api_key_rate_limited",
                key_id=str(key_obj.id),
                limit_info=rate_info,
            )
            return False, key_obj, {"error": "Rate limit exceeded", "details": rate_info}
        
        # Record usage
        await self.service.record_api_usage(key_obj, ip_address, user_agent)
        
        return True, key_obj, None


# Global API key manager instance
api_key_manager = APIKeyManager()