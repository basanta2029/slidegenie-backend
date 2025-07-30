"""
Enhanced Authentication Service for SlideGenie.

Handles user authentication, registration with academic email validation,
password management, and integration with JWT token service.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from email_validator import validate_email, EmailNotValidError

from app.core.config import get_settings
from app.core.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    UserAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.core.security import verify_password, get_password_hash
from app.domain.schemas.auth import (
    UserRegistration,
    UserLogin,
    AuthResponse,
    UserProfile,
    SessionInfo,
)
from app.infrastructure.database.models import User
from app.repositories.user import UserRepository
from app.services.auth.token_service import TokenService, TokenPair
from app.services.auth.email_service import EmailValidationService

logger = structlog.get_logger(__name__)
settings = get_settings()


class AuthService:
    """Enhanced authentication service with academic features."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_service = TokenService()
        self.email_service = EmailValidationService()
    
    async def register(
        self,
        user_data: UserRegistration,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthResponse:
        """
        Register a new user with academic email validation.
        
        Args:
            user_data: User registration data
            request_ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            AuthResponse with user profile, tokens, and session info
            
        Raises:
            UserAlreadyExistsError: If email already registered
            InvalidEmailError: If email format or domain is invalid
        """
        try:
            # Normalize and validate email
            validated_email = await self._validate_and_normalize_email(user_data.email)
            
            # Check if user already exists
            existing_user = await self.user_repo.get_by_email(validated_email)
            if existing_user:
                logger.warning(
                    "registration_attempt_existing_email",
                    email=validated_email,
                    ip=request_ip
                )
                raise UserAlreadyExistsError("Email already registered")
            
            # Validate academic email domain
            institution = await self.email_service.validate_academic_email(
                validated_email
            )
            
            # Validate password strength
            self._validate_password_strength(user_data.password)
            
            # Create user
            password_hash = get_password_hash(user_data.password)
            user = User(
                email=validated_email,
                password_hash=password_hash,
                full_name=f"{user_data.first_name} {user_data.last_name}",
                institution=institution or user_data.institution,
                role=user_data.role or "researcher",
                is_active=True,
                is_verified=False,  # Require email verification
                verification_token=self._generate_verification_token(),
            )
            
            # Save user
            created_user = await self.user_repo.create(user)
            
            # Send verification email
            await self.email_service.send_verification_email(
                email=validated_email,
                full_name=created_user.full_name,
                verification_token=created_user.verification_token,
            )
            
            # Create token pair
            token_pair = await self.token_service.create_token_pair(
                user_id=created_user.id,
                email=created_user.email,
                roles=[created_user.role],
                institution=created_user.institution,
            )
            
            # Create session info
            session_info = SessionInfo(
                session_id=token_pair.access_token.split('.')[2][:16],  # Use part of token as session ID
                user_id=created_user.id,
                created_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                ip_address=request_ip,
                user_agent=user_agent,
            )
            
            # Create user profile
            user_profile = UserProfile(
                id=created_user.id,
                email=created_user.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                institution=created_user.institution,
                role=created_user.role,
                is_active=created_user.is_active,
                is_verified=created_user.is_verified,
                created_at=created_user.created_at,
                last_login=None,
            )
            
            logger.info(
                "user_registered",
                user_id=str(created_user.id),
                email=validated_email,
                institution=created_user.institution,
                ip=request_ip
            )
            
            return AuthResponse(
                user=user_profile,
                tokens=token_pair,
                session=session_info,
            )
            
        except Exception as e:
            logger.error(
                "registration_error",
                error=str(e),
                email=user_data.email,
                ip=request_ip
            )
            raise
    
    async def login(
        self,
        credentials: UserLogin,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthResponse:
        """
        Authenticate user and create session.
        
        Args:
            credentials: User login credentials
            request_ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            AuthResponse with user profile, tokens, and session info
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            EmailNotVerifiedError: If email not verified
        """
        try:
            # Normalize email
            normalized_email = credentials.email.lower().strip()
            
            # Get user
            user = await self.user_repo.get_by_email(normalized_email)
            if not user:
                logger.warning(
                    "login_attempt_unknown_email",
                    email=normalized_email,
                    ip=request_ip
                )
                raise InvalidCredentialsError("Invalid email or password")
            
            # Verify password
            if not verify_password(credentials.password, user.password_hash):
                logger.warning(
                    "login_attempt_invalid_password",
                    user_id=str(user.id),
                    email=normalized_email,
                    ip=request_ip
                )
                raise InvalidCredentialsError("Invalid email or password")
            
            # Check if user is active
            if not user.is_active:
                logger.warning(
                    "login_attempt_inactive_user",
                    user_id=str(user.id),
                    email=normalized_email
                )
                raise InvalidCredentialsError("Account is deactivated")
            
            # For academic email addresses, require verification
            if self.email_service.is_academic_email(user.email) and not user.is_verified:
                logger.warning(
                    "login_attempt_unverified_academic",
                    user_id=str(user.id),
                    email=normalized_email
                )
                raise EmailNotVerifiedError(
                    "Please verify your academic email address before logging in"
                )
            
            # Create token pair
            token_pair = await self.token_service.create_token_pair(
                user_id=user.id,
                email=user.email,
                roles=[user.role],
                institution=user.institution,
            )
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            await self.user_repo.update(user)
            
            # Create session info
            session_info = SessionInfo(
                session_id=token_pair.access_token.split('.')[2][:16],
                user_id=user.id,
                created_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                ip_address=request_ip,
                user_agent=user_agent,
            )
            
            # Create user profile
            name_parts = user.full_name.split(' ', 1)
            user_profile = UserProfile(
                id=user.id,
                email=user.email,
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else '',
                institution=user.institution,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                last_login=user.last_login,
            )
            
            logger.info(
                "user_logged_in",
                user_id=str(user.id),
                email=user.email,
                institution=user.institution,
                ip=request_ip
            )
            
            return AuthResponse(
                user=user_profile,
                tokens=token_pair,
                session=session_info,
            )
            
        except Exception as e:
            logger.error(
                "login_error",
                error=str(e),
                email=credentials.email,
                ip=request_ip
            )
            raise
    
    async def refresh_tokens(
        self,
        refresh_token: str,
        request_ip: Optional[str] = None,
    ) -> TokenPair:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            request_ip: Client IP address
            
        Returns:
            New token pair
            
        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        try:
            new_tokens = await self.token_service.refresh_token(refresh_token)
            
            if not new_tokens:
                logger.warning(
                    "refresh_token_invalid",
                    ip=request_ip
                )
                raise InvalidTokenError("Invalid refresh token")
            
            logger.info(
                "tokens_refreshed",
                ip=request_ip
            )
            
            return new_tokens
            
        except Exception as e:
            logger.error(
                "token_refresh_error",
                error=str(e),
                ip=request_ip
            )
            raise
    
    async def logout(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> bool:
        """
        Logout user and blacklist tokens.
        
        Args:
            access_token: User's access token
            refresh_token: User's refresh token (optional)
            
        Returns:
            Success status
        """
        try:
            success = True
            
            # Revoke access token
            if not await self.token_service.revoke_token(access_token):
                success = False
            
            # Revoke refresh token if provided
            if refresh_token:
                if not await self.token_service.revoke_token(refresh_token):
                    success = False
            
            logger.info(
                "user_logged_out",
                has_refresh_token=bool(refresh_token),
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "logout_error",
                error=str(e)
            )
            return False
    
    async def verify_email(
        self,
        verification_token: str,
    ) -> bool:
        """
        Verify user's email address.
        
        Args:
            verification_token: Email verification token
            
        Returns:
            Success status
            
        Raises:
            InvalidTokenError: If token is invalid
            UserNotFoundError: If user not found
        """
        try:
            # Find user by verification token
            user = await self.user_repo.get_by_verification_token(verification_token)
            if not user:
                raise InvalidTokenError("Invalid verification token")
            
            # Mark as verified
            user.is_verified = True
            user.verification_token = None
            await self.user_repo.update(user)
            
            logger.info(
                "email_verified",
                user_id=str(user.id),
                email=user.email
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "email_verification_error",
                error=str(e),
                token=verification_token[:8] + "..."
            )
            raise
    
    async def resend_verification_email(
        self,
        email: str,
    ) -> bool:
        """
        Resend verification email.
        
        Args:
            email: User's email address
            
        Returns:
            Success status
            
        Raises:
            UserNotFoundError: If user not found
        """
        try:
            normalized_email = email.lower().strip()
            user = await self.user_repo.get_by_email(normalized_email)
            
            if not user:
                raise UserNotFoundError("User not found")
            
            if user.is_verified:
                return True  # Already verified
            
            # Generate new verification token if needed
            if not user.verification_token:
                user.verification_token = self._generate_verification_token()
                await self.user_repo.update(user)
            
            # Send email
            await self.email_service.send_verification_email(
                email=user.email,
                full_name=user.full_name,
                verification_token=user.verification_token,
            )
            
            logger.info(
                "verification_email_resent",
                user_id=str(user.id),
                email=user.email
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "resend_verification_error",
                error=str(e),
                email=email
            )
            raise
    
    async def _validate_and_normalize_email(self, email: str) -> str:
        """
        Validate and normalize email address.
        
        Args:
            email: Raw email address
            
        Returns:
            Normalized email address
            
        Raises:
            InvalidEmailError: If email format is invalid
        """
        try:
            validated = validate_email(email)
            return validated.email.lower()
        except EmailNotValidError as e:
            raise InvalidCredentialsError(f"Invalid email format: {str(e)}")
    
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
    
    def _generate_verification_token(self) -> str:
        """
        Generate secure verification token.
        
        Returns:
            Random verification token
        """
        return secrets.token_urlsafe(32)
