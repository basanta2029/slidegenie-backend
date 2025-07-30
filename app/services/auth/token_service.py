"""
JWT Token Management Service

Handles token generation, validation, and blacklisting with Redis.
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

import structlog
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings
from app.infrastructure.cache import get_redis_client

logger = structlog.get_logger(__name__)
settings = get_settings()


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # User ID
    email: str
    roles: list[str]
    institution: Optional[str] = None
    type: str  # 'access' or 'refresh'
    session_id: str
    iat: int
    exp: int
    nbf: Optional[int] = None
    jti: Optional[str] = None  # JWT ID for blacklisting


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class TokenService:
    """Service for JWT token operations."""
    
    def __init__(self):
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.SECRET_KEY
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        self.issuer = settings.JWT_ISSUER
    
    async def create_token_pair(
        self,
        user_id: UUID,
        email: str,
        roles: list[str],
        institution: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> TokenPair:
        """Create access and refresh token pair."""
        # Generate session ID if not provided
        if not session_id:
            session_id = self._generate_session_id()
        
        # Create access token
        access_token_data = {
            "sub": str(user_id),
            "email": email,
            "roles": roles,
            "institution": institution,
            "type": "access",
            "session_id": session_id,
            "jti": self._generate_jti(),
        }
        access_token = self._create_token(
            data=access_token_data,
            expires_delta=timedelta(minutes=self.access_token_expire_minutes)
        )
        
        # Create refresh token
        refresh_token_data = {
            "sub": str(user_id),
            "email": email,
            "roles": roles,
            "institution": institution,
            "type": "refresh",
            "session_id": session_id,
            "jti": self._generate_jti(),
        }
        refresh_token = self._create_token(
            data=refresh_token_data,
            expires_delta=timedelta(days=self.refresh_token_expire_days)
        )
        
        logger.info(
            "token_pair_created",
            user_id=str(user_id),
            session_id=session_id,
            has_institution=bool(institution),
        )
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
            refresh_expires_in=self.refresh_token_expire_days * 24 * 60 * 60,
        )
    
    def _create_token(self, data: Dict[str, Any], expires_delta: timedelta) -> str:
        """Create a JWT token with given data and expiration."""
        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        
        to_encode = data.copy()
        to_encode.update({
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "nbf": int(now.timestamp()),
            "iss": self.issuer,
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )
        return encoded_jwt
    
    async def decode_token(self, token: str) -> Optional[TokenPayload]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
            )
            
            # Check if token is blacklisted
            if await self._is_token_blacklisted(payload.get("jti")):
                logger.warning("blacklisted_token_attempted", jti=payload.get("jti"))
                return None
            
            return TokenPayload(**payload)
            
        except JWTError as e:
            logger.error("token_decode_error", error=str(e))
            return None
        except Exception as e:
            logger.error("unexpected_token_error", error=str(e))
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[TokenPair]:
        """Generate new token pair from refresh token."""
        payload = await self.decode_token(refresh_token)
        
        if not payload or payload.type != "refresh":
            logger.warning("invalid_refresh_token_attempt")
            return None
        
        # Blacklist the old refresh token
        await self._blacklist_token(refresh_token, payload.jti)
        
        # Create new token pair
        return await self.create_token_pair(
            user_id=UUID(payload.sub),
            email=payload.email,
            roles=payload.roles,
            institution=payload.institution,
            session_id=payload.session_id,
        )
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding it to blacklist."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Allow expired tokens to be revoked
            )
            
            jti = payload.get("jti")
            if not jti:
                return False
            
            return await self._blacklist_token(token, jti)
            
        except JWTError:
            return False
    
    async def revoke_all_user_tokens(self, user_id: UUID) -> bool:
        """Revoke all tokens for a user."""
        # Implementation would require tracking all active tokens per user
        # For now, we'll invalidate the user's sessions
        return await SessionManager().invalidate_all_user_sessions(str(user_id))
    
    async def _blacklist_token(self, token: str, jti: str) -> bool:
        """Add token to Redis blacklist."""
        try:
            redis = await get_redis_client()
            
            # Extract expiration from token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            exp_timestamp = payload.get("exp", 0)
            now_timestamp = int(datetime.now(timezone.utc).timestamp())
            ttl = max(exp_timestamp - now_timestamp, 0)
            
            if ttl > 0:
                key = f"token:blacklist:{jti}"
                await redis.setex(key, ttl, "1")
                logger.info("token_blacklisted", jti=jti, ttl=ttl)
                return True
            
            return False
            
        except Exception as e:
            logger.error("token_blacklist_error", error=str(e))
            return False
    
    async def _is_token_blacklisted(self, jti: Optional[str]) -> bool:
        """Check if token is in blacklist."""
        if not jti:
            return False
        
        try:
            redis = await get_redis_client()
            key = f"token:blacklist:{jti}"
            return bool(await redis.exists(key))
        except Exception as e:
            logger.error("token_blacklist_check_error", error=str(e))
            # Fail closed - treat as blacklisted on error
            return True
    
    def _generate_jti(self) -> str:
        """Generate unique JWT ID."""
        return secrets.token_urlsafe(32)
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return secrets.token_urlsafe(24)


class BlacklistService:
    """Service for managing token blacklist."""
    
    async def add_to_blacklist(self, jti: str, ttl: int) -> bool:
        """Add JTI to blacklist with TTL."""
        try:
            redis = await get_redis_client()
            key = f"token:blacklist:{jti}"
            await redis.setex(key, ttl, "1")
            return True
        except Exception as e:
            logger.error("blacklist_add_error", error=str(e), jti=jti)
            return False
    
    async def is_blacklisted(self, jti: str) -> bool:
        """Check if JTI is blacklisted."""
        try:
            redis = await get_redis_client()
            key = f"token:blacklist:{jti}"
            return bool(await redis.exists(key))
        except Exception as e:
            logger.error("blacklist_check_error", error=str(e), jti=jti)
            # Fail closed
            return True
    
    async def remove_from_blacklist(self, jti: str) -> bool:
        """Remove JTI from blacklist."""
        try:
            redis = await get_redis_client()
            key = f"token:blacklist:{jti}"
            result = await redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("blacklist_remove_error", error=str(e), jti=jti)
            return False
    
    async def get_blacklist_stats(self) -> Dict[str, int]:
        """Get blacklist statistics."""
        try:
            redis = await get_redis_client()
            keys = await redis.keys("token:blacklist:*")
            return {
                "total_blacklisted": len(keys),
                "memory_usage": await redis.memory_usage("token:blacklist:*") or 0,
            }
        except Exception as e:
            logger.error("blacklist_stats_error", error=str(e))
            return {"total_blacklisted": 0, "memory_usage": 0}


class SessionManager:
    """Service for managing user sessions."""
    
    def __init__(self):
        self.session_ttl = settings.SESSION_TTL_SECONDS
    
    async def create_session(
        self,
        user_id: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a new session."""
        try:
            redis = await get_redis_client()
            
            # Store session data
            session_key = f"session:{session_id}"
            session_data = {
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }
            
            await redis.setex(
                session_key,
                self.session_ttl,
                json.dumps(session_data)
            )
            
            # Add to user's session set
            user_sessions_key = f"user:sessions:{user_id}"
            await redis.sadd(user_sessions_key, session_id)
            await redis.expire(user_sessions_key, self.session_ttl)
            
            logger.info("session_created", user_id=user_id, session_id=session_id)
            return True
            
        except Exception as e:
            logger.error("session_create_error", error=str(e))
            return False
    
    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate and return session data."""
        try:
            redis = await get_redis_client()
            session_key = f"session:{session_id}"
            
            data = await redis.get(session_key)
            if not data:
                return None
            
            session_data = json.loads(data)
            
            # Update last activity
            session_data["last_activity"] = datetime.now(timezone.utc).isoformat()
            await redis.setex(
                session_key,
                self.session_ttl,
                json.dumps(session_data)
            )
            
            return session_data
            
        except Exception as e:
            logger.error("session_validate_error", error=str(e))
            return None
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a specific session."""
        try:
            redis = await get_redis_client()
            
            # Get session data to find user
            session_key = f"session:{session_id}"
            data = await redis.get(session_key)
            
            if data:
                session_data = json.loads(data)
                user_id = session_data.get("user_id")
                
                # Remove from user's session set
                if user_id:
                    user_sessions_key = f"user:sessions:{user_id}"
                    await redis.srem(user_sessions_key, session_id)
            
            # Delete session
            result = await redis.delete(session_key)
            
            logger.info("session_invalidated", session_id=session_id)
            return bool(result)
            
        except Exception as e:
            logger.error("session_invalidate_error", error=str(e))
            return False
    
    async def invalidate_all_user_sessions(self, user_id: str) -> bool:
        """Invalidate all sessions for a user."""
        try:
            redis = await get_redis_client()
            
            # Get all user sessions
            user_sessions_key = f"user:sessions:{user_id}"
            session_ids = await redis.smembers(user_sessions_key)
            
            # Delete each session
            for session_id in session_ids:
                session_key = f"session:{session_id}"
                await redis.delete(session_key)
            
            # Delete user session set
            await redis.delete(user_sessions_key)
            
            logger.info(
                "all_user_sessions_invalidated",
                user_id=user_id,
                session_count=len(session_ids)
            )
            return True
            
        except Exception as e:
            logger.error("user_sessions_invalidate_error", error=str(e))
            return False
    
    async def get_active_sessions(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all active sessions for a user."""
        try:
            redis = await get_redis_client()
            
            # Get all user sessions
            user_sessions_key = f"user:sessions:{user_id}"
            session_ids = await redis.smembers(user_sessions_key)
            
            sessions = []
            for session_id in session_ids:
                session_key = f"session:{session_id}"
                data = await redis.get(session_key)
                if data:
                    session_data = json.loads(data)
                    session_data["session_id"] = session_id
                    sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            logger.error("get_active_sessions_error", error=str(e))
            return []
    
    async def extend_session(self, session_id: str, additional_ttl: int) -> bool:
        """Extend session TTL."""
        try:
            redis = await get_redis_client()
            session_key = f"session:{session_id}"
            
            # Get current TTL
            current_ttl = await redis.ttl(session_key)
            if current_ttl <= 0:
                return False
            
            # Extend TTL
            new_ttl = current_ttl + additional_ttl
            return bool(await redis.expire(session_key, new_ttl))
            
        except Exception as e:
            logger.error("session_extend_error", error=str(e))
            return False


# Import json at the top
import json