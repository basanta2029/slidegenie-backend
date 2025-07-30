"""
Password Reset Service for SlideGenie.

Handles password reset requests, token generation, and password updates.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    InvalidTokenError,
    UserNotFoundError,
    InvalidCredentialsError,
)
from app.core.security import get_password_hash
from app.infrastructure.cache import get_redis_client
from app.repositories.user import UserRepository
from app.services.auth.email_service import EmailValidationService
from app.services.auth.token_service import TokenService

logger = structlog.get_logger(__name__)
settings = get_settings()


class PasswordResetService:
    """Service for handling password reset functionality."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.email_service = EmailValidationService()
        self.token_service = TokenService()
        self.reset_token_ttl = 3600  # 1 hour
    
    async def request_password_reset(self, email: str) -> bool:
        """
        Request password reset for user.
        
        Args:
            email: User's email address
            
        Returns:
            Success status
        """
        try:
            # Normalize email
            normalized_email = email.lower().strip()
            
            # Get user
            user = await self.user_repo.get_by_email(normalized_email)
            if not user:
                # Don't reveal if email doesn't exist
                logger.info(
                    "password_reset_requested_nonexistent",
                    email=normalized_email
                )
                return True
            
            # Generate reset token
            reset_token = self._generate_reset_token()
            
            # Store token in Redis with TTL
            await self._store_reset_token(
                user_id=str(user.id),
                token=reset_token,
                ttl=self.reset_token_ttl
            )
            
            # Send reset email
            await self.email_service.send_password_reset_email(
                email=user.email,
                full_name=user.full_name,
                reset_token=reset_token,
            )
            
            logger.info(
                "password_reset_requested",
                user_id=str(user.id),
                email=user.email
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "password_reset_request_error",
                error=str(e),
                email=email
            )
            # Don't expose errors
            return True
    
    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> bool:
        """
        Reset user's password with reset token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            Success status
            
        Raises:
            InvalidTokenError: If token is invalid or expired
            InvalidCredentialsError: If password doesn't meet requirements
        """
        try:
            # Validate reset token
            user_id = await self._validate_reset_token(token)
            if not user_id:
                raise InvalidTokenError("Invalid or expired reset token")
            
            # Get user
            user = await self.user_repo.get(user_id)
            if not user:
                raise UserNotFoundError("User not found")
            
            # Validate password strength
            self._validate_password_strength(new_password)
            
            # Update password
            user.password_hash = get_password_hash(new_password)
            await self.user_repo.update(user)
            
            # Invalidate reset token
            await self._invalidate_reset_token(token)
            
            # Revoke all user tokens
            await self.token_service.revoke_all_user_tokens(user.id)
            
            logger.info(
                "password_reset_completed",
                user_id=str(user.id),
                email=user.email
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "password_reset_error",
                error=str(e),
                token=token[:8] + "..."
            )
            raise
    
    async def _store_reset_token(
        self,
        user_id: str,
        token: str,
        ttl: int,
    ) -> bool:
        """
        Store reset token in Redis.
        
        Args:
            user_id: User ID
            token: Reset token
            ttl: Time to live in seconds
            
        Returns:
            Success status
        """
        try:
            redis = await get_redis_client()
            
            # Store token with user ID as value
            key = f"password_reset:{token}"
            await redis.setex(key, ttl, user_id)
            
            # Also store by user ID for rate limiting
            user_key = f"password_reset:user:{user_id}"
            await redis.setex(user_key, ttl, token)
            
            return True
            
        except Exception as e:
            logger.error(
                "reset_token_store_error",
                error=str(e),
                user_id=user_id
            )
            return False
    
    async def _validate_reset_token(self, token: str) -> Optional[str]:
        """
        Validate reset token and return user ID.
        
        Args:
            token: Reset token
            
        Returns:
            User ID if valid, None otherwise
        """
        try:
            redis = await get_redis_client()
            
            key = f"password_reset:{token}"
            user_id = await redis.get(key)
            
            if user_id:
                return user_id.decode() if isinstance(user_id, bytes) else user_id
            
            return None
            
        except Exception as e:
            logger.error(
                "reset_token_validate_error",
                error=str(e),
                token=token[:8] + "..."
            )
            return None
    
    async def _invalidate_reset_token(self, token: str) -> bool:
        """
        Invalidate reset token.
        
        Args:
            token: Reset token
            
        Returns:
            Success status
        """
        try:
            redis = await get_redis_client()
            
            # Get user ID first
            key = f"password_reset:{token}"
            user_id = await redis.get(key)
            
            # Delete token
            await redis.delete(key)
            
            # Delete user key if exists
            if user_id:
                user_id_str = user_id.decode() if isinstance(user_id, bytes) else user_id
                user_key = f"password_reset:user:{user_id_str}"
                await redis.delete(user_key)
            
            return True
            
        except Exception as e:
            logger.error(
                "reset_token_invalidate_error",
                error=str(e),
                token=token[:8] + "..."
            )
            return False
    
    def _generate_reset_token(self) -> str:
        """
        Generate secure reset token.
        
        Returns:
            Random reset token
        """
        return secrets.token_urlsafe(32)
    
    def _validate_password_strength(self, password: str) -> None:
        """
        Validate password meets security requirements.
        
        Args:
            password: Password to validate
            
        Raises:
            InvalidCredentialsError: If password doesn't meet requirements
        """
        min_length = 12
        
        if len(password) < min_length:
            raise InvalidCredentialsError(
                f"Password must be at least {min_length} characters long"
            )
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in password):
            raise InvalidCredentialsError(
                "Password must contain at least one uppercase letter"
            )
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in password):
            raise InvalidCredentialsError(
                "Password must contain at least one lowercase letter"
            )
        
        # Check for at least one digit
        if not any(c.isdigit() for c in password):
            raise InvalidCredentialsError(
                "Password must contain at least one number"
            )
        
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            raise InvalidCredentialsError(
                "Password must contain at least one special character"
            )


class PasswordStrengthChecker:
    """Service for checking password strength."""
    
    @staticmethod
    def check_strength(password: str) -> dict:
        """
        Check password strength and return analysis.
        
        Args:
            password: Password to analyze
            
        Returns:
            Dictionary with strength analysis
        """
        score = 0
        feedback = []
        
        # Length check
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
            feedback.append("Use at least 12 characters for better security")
        else:
            feedback.append("Password is too short")
        
        # Character variety
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        variety_count = sum([has_lower, has_upper, has_digit, has_special])
        score += variety_count
        
        if not has_lower:
            feedback.append("Add lowercase letters")
        if not has_upper:
            feedback.append("Add uppercase letters")
        if not has_digit:
            feedback.append("Add numbers")
        if not has_special:
            feedback.append("Add special characters")
        
        # Common patterns check
        common_patterns = [
            "password", "123456", "qwerty", "admin",
            "letmein", "welcome", "monkey", "dragon"
        ]
        
        lower_password = password.lower()
        for pattern in common_patterns:
            if pattern in lower_password:
                score -= 2
                feedback.append(f"Avoid common words like '{pattern}'")
                break
        
        # Sequential characters check
        if any(
            ord(password[i]) == ord(password[i-1]) + 1 and
            ord(password[i-1]) == ord(password[i-2]) + 1
            for i in range(2, len(password))
        ):
            score -= 1
            feedback.append("Avoid sequential characters")
        
        # Repeated characters check
        if any(
            password[i] == password[i-1] == password[i-2]
            for i in range(2, len(password))
        ):
            score -= 1
            feedback.append("Avoid repeated characters")
        
        # Determine strength level
        if score >= 6:
            strength = "strong"
        elif score >= 4:
            strength = "medium"
        else:
            strength = "weak"
        
        return {
            "strength": strength,
            "score": max(0, min(10, score)),
            "feedback": feedback,
            "has_lowercase": has_lower,
            "has_uppercase": has_upper,
            "has_digits": has_digit,
            "has_special": has_special,
            "length": len(password),
        }