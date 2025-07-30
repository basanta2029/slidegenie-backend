"""
OAuth State Manager

Handles secure state management for OAuth flows to prevent CSRF attacks.
Uses Redis for distributed state storage.
"""
import secrets
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from app.infrastructure.cache import get_redis_client
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"  # Future provider
    LINKEDIN = "linkedin"  # Future provider


class OAuthStateData(BaseModel):
    """OAuth state data structure."""
    state: str = Field(..., description="Unique state token")
    provider: OAuthProvider
    redirect_uri: str
    code_verifier: Optional[str] = None  # For PKCE support
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    
    # Optional metadata
    user_id: Optional[str] = None  # For linking flows
    action: str = "login"  # login, link, signup
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Security
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OAuthStateManager:
    """Manages OAuth state tokens for CSRF protection."""
    
    def __init__(self, state_ttl_seconds: int = 600):  # 10 minutes default
        self.state_ttl = state_ttl_seconds
        self.state_prefix = "oauth:state"
    
    async def create_state(
        self,
        provider: OAuthProvider,
        redirect_uri: str,
        action: str = "login",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        use_pkce: bool = False,
    ) -> OAuthStateData:
        """
        Create and store OAuth state.
        
        Args:
            provider: OAuth provider
            redirect_uri: OAuth redirect URI
            action: OAuth action (login, link, signup)
            user_id: Optional user ID for linking flows
            metadata: Optional metadata to store
            ip_address: Client IP address
            user_agent: Client user agent
            use_pkce: Enable PKCE flow
        
        Returns:
            OAuth state data
        """
        # Generate secure random state
        state = self._generate_state()
        
        # Generate PKCE code verifier if requested
        code_verifier = self._generate_code_verifier() if use_pkce else None
        
        # Create state data
        state_data = OAuthStateData(
            state=state,
            provider=provider,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            action=action,
            user_id=user_id,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.state_ttl),
        )
        
        # Store in Redis
        await self._store_state(state, state_data)
        
        logger.info(
            "oauth_state_created",
            provider=provider.value,
            action=action,
            has_user_id=bool(user_id),
            has_pkce=bool(code_verifier),
            state=state[:8],  # Log only first 8 chars
        )
        
        return state_data
    
    async def validate_state(
        self,
        state: str,
        provider: Optional[OAuthProvider] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[OAuthStateData]:
        """
        Validate and retrieve OAuth state.
        
        Args:
            state: State token to validate
            provider: Expected provider (optional check)
            ip_address: Client IP to verify (optional)
        
        Returns:
            OAuth state data if valid, None otherwise
        """
        try:
            # Retrieve from Redis
            state_data = await self._get_state(state)
            if not state_data:
                logger.warning("oauth_state_not_found", state=state[:8])
                return None
            
            # Check expiration
            if datetime.now(timezone.utc) > state_data.expires_at:
                logger.warning(
                    "oauth_state_expired",
                    state=state[:8],
                    expired_at=state_data.expires_at.isoformat()
                )
                await self._delete_state(state)
                return None
            
            # Verify provider if specified
            if provider and state_data.provider != provider:
                logger.warning(
                    "oauth_state_provider_mismatch",
                    state=state[:8],
                    expected=provider.value,
                    actual=state_data.provider.value
                )
                return None
            
            # Verify IP address if specified and stored
            if ip_address and state_data.ip_address and ip_address != state_data.ip_address:
                logger.warning(
                    "oauth_state_ip_mismatch",
                    state=state[:8],
                    expected_ip=state_data.ip_address,
                    actual_ip=ip_address
                )
                # Don't fail on IP mismatch but log it
            
            logger.info(
                "oauth_state_validated",
                state=state[:8],
                provider=state_data.provider.value,
                action=state_data.action,
                age_seconds=(datetime.now(timezone.utc) - state_data.created_at).total_seconds()
            )
            
            return state_data
            
        except Exception as e:
            logger.error("oauth_state_validation_error", error=str(e), state=state[:8])
            return None
    
    async def consume_state(
        self,
        state: str,
        provider: Optional[OAuthProvider] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[OAuthStateData]:
        """
        Validate and consume OAuth state (one-time use).
        
        Args:
            state: State token to validate and consume
            provider: Expected provider (optional check)
            ip_address: Client IP to verify (optional)
        
        Returns:
            OAuth state data if valid, None otherwise
        """
        # Validate state
        state_data = await self.validate_state(state, provider, ip_address)
        if not state_data:
            return None
        
        # Delete state to prevent reuse
        await self._delete_state(state)
        
        logger.info(
            "oauth_state_consumed",
            state=state[:8],
            provider=state_data.provider.value,
            action=state_data.action
        )
        
        return state_data
    
    async def cleanup_expired_states(self) -> int:
        """
        Clean up expired OAuth states.
        
        Returns:
            Number of states cleaned up
        """
        try:
            redis = await get_redis_client()
            pattern = f"{self.state_prefix}:*"
            
            count = 0
            async for key in redis.scan_iter(match=pattern):
                # Get state data
                data = await redis.get(key)
                if not data:
                    continue
                
                try:
                    state_dict = json.loads(data)
                    expires_at = datetime.fromisoformat(state_dict["expires_at"])
                    
                    # Check if expired
                    if datetime.now(timezone.utc) > expires_at:
                        await redis.delete(key)
                        count += 1
                except Exception:
                    # Delete invalid states
                    await redis.delete(key)
                    count += 1
            
            if count > 0:
                logger.info("oauth_states_cleaned", count=count)
            
            return count
            
        except Exception as e:
            logger.error("oauth_state_cleanup_error", error=str(e))
            return 0
    
    async def get_state_stats(self) -> Dict[str, Any]:
        """Get OAuth state statistics."""
        try:
            redis = await get_redis_client()
            pattern = f"{self.state_prefix}:*"
            
            total = 0
            expired = 0
            by_provider = {}
            by_action = {}
            
            async for key in redis.scan_iter(match=pattern):
                total += 1
                
                # Get state data
                data = await redis.get(key)
                if not data:
                    continue
                
                try:
                    state_dict = json.loads(data)
                    expires_at = datetime.fromisoformat(state_dict["expires_at"])
                    
                    # Check if expired
                    if datetime.now(timezone.utc) > expires_at:
                        expired += 1
                    
                    # Count by provider
                    provider = state_dict.get("provider", "unknown")
                    by_provider[provider] = by_provider.get(provider, 0) + 1
                    
                    # Count by action
                    action = state_dict.get("action", "unknown")
                    by_action[action] = by_action.get(action, 0) + 1
                    
                except Exception:
                    pass
            
            return {
                "total_states": total,
                "expired_states": expired,
                "active_states": total - expired,
                "by_provider": by_provider,
                "by_action": by_action,
            }
            
        except Exception as e:
            logger.error("oauth_state_stats_error", error=str(e))
            return {
                "total_states": 0,
                "expired_states": 0,
                "active_states": 0,
                "by_provider": {},
                "by_action": {},
            }
    
    async def _store_state(self, state: str, state_data: OAuthStateData) -> None:
        """Store state in Redis."""
        try:
            redis = await get_redis_client()
            key = f"{self.state_prefix}:{state}"
            
            # Serialize state data
            data = state_data.json()
            
            # Store with TTL
            await redis.setex(key, self.state_ttl, data)
            
        except Exception as e:
            logger.error("oauth_state_store_error", error=str(e), state=state[:8])
            raise
    
    async def _get_state(self, state: str) -> Optional[OAuthStateData]:
        """Retrieve state from Redis."""
        try:
            redis = await get_redis_client()
            key = f"{self.state_prefix}:{state}"
            
            # Get data
            data = await redis.get(key)
            if not data:
                return None
            
            # Deserialize
            state_dict = json.loads(data)
            
            # Handle datetime conversion
            if "created_at" in state_dict:
                state_dict["created_at"] = datetime.fromisoformat(state_dict["created_at"])
            if "expires_at" in state_dict:
                state_dict["expires_at"] = datetime.fromisoformat(state_dict["expires_at"])
            
            return OAuthStateData(**state_dict)
            
        except Exception as e:
            logger.error("oauth_state_get_error", error=str(e), state=state[:8])
            return None
    
    async def _delete_state(self, state: str) -> None:
        """Delete state from Redis."""
        try:
            redis = await get_redis_client()
            key = f"{self.state_prefix}:{state}"
            await redis.delete(key)
            
        except Exception as e:
            logger.error("oauth_state_delete_error", error=str(e), state=state[:8])
    
    def _generate_state(self) -> str:
        """Generate secure random state token."""
        # Use URL-safe base64 encoding for compatibility
        return secrets.token_urlsafe(32)
    
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        # RFC 7636 recommends 43-128 characters
        return secrets.token_urlsafe(64)
    
    def generate_code_challenge(self, code_verifier: str) -> str:
        """
        Generate PKCE code challenge from verifier.
        
        Args:
            code_verifier: PKCE code verifier
        
        Returns:
            Base64 URL-encoded SHA256 hash of verifier
        """
        import hashlib
        import base64
        
        # SHA256 hash of verifier
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        
        # Base64 URL-encode without padding
        code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        
        return code_challenge


# Import at module level for proper usage
from datetime import timedelta


# Create default state manager instance
oauth_state_manager = OAuthStateManager()