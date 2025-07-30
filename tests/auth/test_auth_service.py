"""
Comprehensive tests for AuthService.

Tests user registration, login, email verification, token refresh,
and logout functionality with focus on academic email validation.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    UserAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidTokenError,
)
from app.domain.schemas.auth import (
    UserRegistration,
    UserLogin,
    AuthResponse,
)
from app.services.auth.auth_service import AuthService
from app.services.auth.token_service import TokenService
from tests.fixtures.auth import AuthTestData


class TestAuthServiceRegistration:
    """Test user registration functionality."""
    
    @pytest.mark.asyncio
    async def test_register_success_academic_email(
        self,
        auth_service: AuthService,
        mock_email_service,
        db_session: AsyncSession,
    ):
        """Test successful registration with academic email."""
        # Arrange
        registration_data = UserRegistration(
            email="new.student@mit.edu",
            password="SecureP@ssw0rd123!",
            first_name="New",
            last_name="Student",
            institution="MIT",
            role="student",
        )
        
        # Act
        result = await auth_service.register(
            registration_data,
            request_ip="127.0.0.1",
            user_agent="Test Browser",
        )
        
        # Assert
        assert isinstance(result, AuthResponse)
        assert result.user.email == "new.student@mit.edu"
        assert result.user.first_name == "New"
        assert result.user.last_name == "Student"
        assert result.user.institution == "MIT"
        assert result.user.role == "student"
        assert result.user.is_active is True
        assert result.user.is_verified is False  # Requires email verification
        assert result.tokens.access_token is not None
        assert result.tokens.refresh_token is not None
        assert result.session.ip_address == "127.0.0.1"
        assert result.session.user_agent == "Test Browser"
        
        # Verify email was sent
        mock_email_service.send_verification_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        auth_service: AuthService,
        test_user,
        mock_email_service,
    ):
        """Test registration with already registered email."""
        # Arrange
        registration_data = UserRegistration(
            email=test_user.email,  # Already exists
            password="AnotherP@ssw0rd123!",
            first_name="Duplicate",
            last_name="User",
        )
        
        # Act & Assert
        with pytest.raises(UserAlreadyExistsError) as exc:
            await auth_service.register(registration_data)
        
        assert "Email already registered" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_register_invalid_email_format(
        self,
        auth_service: AuthService,
        mock_email_service,
    ):
        """Test registration with invalid email format."""
        # Arrange
        registration_data = UserRegistration(
            email="invalid-email-format",
            password="SecureP@ssw0rd123!",
            first_name="Invalid",
            last_name="Email",
        )
        
        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc:
            await auth_service.register(registration_data)
        
        assert "Invalid email format" in str(exc.value)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("weak_password,error_msg", [
        ("short", "at least 12 characters"),
        ("nouppercase123!", "uppercase letter"),
        ("NOLOWERCASE123!", "lowercase letter"),
        ("NoNumbers!@#", "at least one number"),
        ("NoSpecialChar123", "special character"),
    ])
    async def test_register_weak_password(
        self,
        auth_service: AuthService,
        mock_email_service,
        weak_password: str,
        error_msg: str,
    ):
        """Test registration with weak passwords."""
        # Arrange
        registration_data = UserRegistration(
            email="weak.pass@mit.edu",
            password=weak_password,
            first_name="Weak",
            last_name="Password",
        )
        
        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc:
            await auth_service.register(registration_data)
        
        assert error_msg in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_register_non_academic_email(
        self,
        auth_service: AuthService,
        mock_email_service,
    ):
        """Test registration with non-academic email."""
        # Arrange
        registration_data = UserRegistration(
            email="user@gmail.com",
            password="SecureP@ssw0rd123!",
            first_name="Regular",
            last_name="User",
            institution="Personal",
        )
        
        # Mock non-academic response
        mock_email_service.validate_academic_email.return_value = None
        
        # Act
        result = await auth_service.register(registration_data)
        
        # Assert - Should still succeed but with personal institution
        assert result.user.email == "user@gmail.com"
        assert result.user.institution == "Personal"
    
    @pytest.mark.asyncio
    async def test_register_case_insensitive_email(
        self,
        auth_service: AuthService,
        mock_email_service,
    ):
        """Test email normalization during registration."""
        # Arrange
        registration_data = UserRegistration(
            email="UPPER.CASE@MIT.EDU",
            password="SecureP@ssw0rd123!",
            first_name="Upper",
            last_name="Case",
        )
        
        # Act
        result = await auth_service.register(registration_data)
        
        # Assert
        assert result.user.email == "upper.case@mit.edu"  # Normalized to lowercase


class TestAuthServiceLogin:
    """Test user login functionality."""
    
    @pytest.mark.asyncio
    async def test_login_success(
        self,
        auth_service: AuthService,
        test_user,
    ):
        """Test successful login with valid credentials."""
        # Arrange
        credentials = UserLogin(
            email=AuthTestData.STUDENT_USER["email"],
            password=AuthTestData.STUDENT_USER["password"],
        )
        
        # Act
        result = await auth_service.login(
            credentials,
            request_ip="127.0.0.1",
            user_agent="Test Browser",
        )
        
        # Assert
        assert isinstance(result, AuthResponse)
        assert result.user.email == test_user.email
        assert result.user.last_login is not None
        assert result.tokens.access_token is not None
        assert result.tokens.refresh_token is not None
        assert result.session.ip_address == "127.0.0.1"
    
    @pytest.mark.asyncio
    async def test_login_invalid_email(
        self,
        auth_service: AuthService,
    ):
        """Test login with non-existent email."""
        # Arrange
        credentials = UserLogin(
            email="nonexistent@mit.edu",
            password="AnyP@ssw0rd123!",
        )
        
        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc:
            await auth_service.login(credentials)
        
        assert "Invalid email or password" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        auth_service: AuthService,
        test_user,
    ):
        """Test login with wrong password."""
        # Arrange
        credentials = UserLogin(
            email=test_user.email,
            password="WrongP@ssw0rd123!",
        )
        
        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc:
            await auth_service.login(credentials)
        
        assert "Invalid email or password" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_login_unverified_academic_email(
        self,
        auth_service: AuthService,
        unverified_user,
    ):
        """Test login with unverified academic email."""
        # Arrange
        credentials = UserLogin(
            email=unverified_user.email,
            password="UnverifiedP@ss123!",
        )
        
        # Act & Assert
        with pytest.raises(EmailNotVerifiedError) as exc:
            await auth_service.login(credentials)
        
        assert "verify your academic email" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        auth_service: AuthService,
        test_user,
        db_session: AsyncSession,
    ):
        """Test login with inactive account."""
        # Arrange
        test_user.is_active = False
        await db_session.commit()
        
        credentials = UserLogin(
            email=test_user.email,
            password=AuthTestData.STUDENT_USER["password"],
        )
        
        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc:
            await auth_service.login(credentials)
        
        assert "Account is deactivated" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_login_case_insensitive_email(
        self,
        auth_service: AuthService,
        test_user,
    ):
        """Test login with different email case."""
        # Arrange
        credentials = UserLogin(
            email=test_user.email.upper(),  # Use uppercase
            password=AuthTestData.STUDENT_USER["password"],
        )
        
        # Act
        result = await auth_service.login(credentials)
        
        # Assert - Should succeed with normalized email
        assert result.user.email == test_user.email.lower()


class TestAuthServiceEmailVerification:
    """Test email verification functionality."""
    
    @pytest.mark.asyncio
    async def test_verify_email_success(
        self,
        auth_service: AuthService,
        unverified_user,
        db_session: AsyncSession,
    ):
        """Test successful email verification."""
        # Act
        result = await auth_service.verify_email(unverified_user.verification_token)
        
        # Assert
        assert result is True
        
        # Refresh user from DB
        await db_session.refresh(unverified_user)
        assert unverified_user.is_verified is True
        assert unverified_user.verification_token is None
    
    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(
        self,
        auth_service: AuthService,
    ):
        """Test email verification with invalid token."""
        # Act & Assert
        with pytest.raises(InvalidTokenError) as exc:
            await auth_service.verify_email("invalid-token-12345")
        
        assert "Invalid verification token" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_resend_verification_email(
        self,
        auth_service: AuthService,
        unverified_user,
        mock_email_service,
    ):
        """Test resending verification email."""
        # Act
        result = await auth_service.resend_verification_email(unverified_user.email)
        
        # Assert
        assert result is True
        mock_email_service.send_verification_email.assert_called()
    
    @pytest.mark.asyncio
    async def test_resend_verification_already_verified(
        self,
        auth_service: AuthService,
        test_user,
        mock_email_service,
    ):
        """Test resending verification for already verified user."""
        # Act
        result = await auth_service.resend_verification_email(test_user.email)
        
        # Assert - Should return True without sending email
        assert result is True
        mock_email_service.send_verification_email.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_resend_verification_nonexistent_user(
        self,
        auth_service: AuthService,
    ):
        """Test resending verification for non-existent user."""
        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await auth_service.resend_verification_email("nonexistent@mit.edu")


class TestAuthServiceTokenRefresh:
    """Test token refresh functionality."""
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_success(
        self,
        auth_service: AuthService,
        auth_tokens,
    ):
        """Test successful token refresh."""
        # Act
        new_tokens = await auth_service.refresh_tokens(
            auth_tokens.refresh_token,
            request_ip="127.0.0.1",
        )
        
        # Assert
        assert new_tokens.access_token != auth_tokens.access_token
        assert new_tokens.refresh_token != auth_tokens.refresh_token
        assert new_tokens.token_type == "Bearer"
        assert new_tokens.expires_in > 0
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_token(
        self,
        auth_service: AuthService,
    ):
        """Test token refresh with invalid refresh token."""
        # Act & Assert
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_tokens("invalid-refresh-token")
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_expired(
        self,
        auth_service: AuthService,
        expired_tokens,
    ):
        """Test token refresh with expired refresh token."""
        # Act & Assert
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_tokens(expired_tokens.refresh_token)


class TestAuthServiceLogout:
    """Test logout functionality."""
    
    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        auth_service: AuthService,
        auth_tokens,
    ):
        """Test successful logout."""
        # Act
        result = await auth_service.logout(
            access_token=auth_tokens.access_token,
            refresh_token=auth_tokens.refresh_token,
        )
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_logout_access_token_only(
        self,
        auth_service: AuthService,
        auth_tokens,
    ):
        """Test logout with only access token."""
        # Act
        result = await auth_service.logout(
            access_token=auth_tokens.access_token,
        )
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_logout_invalid_tokens(
        self,
        auth_service: AuthService,
    ):
        """Test logout with invalid tokens."""
        # Act - Should not raise exception
        result = await auth_service.logout(
            access_token="invalid-access-token",
            refresh_token="invalid-refresh-token",
        )
        
        # Assert - Returns False for invalid tokens
        assert result is False


class TestAuthServiceSecurityFeatures:
    """Test security-related features."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("malicious_input", AuthTestData.MALICIOUS_INPUTS)
    async def test_register_sql_injection_protection(
        self,
        auth_service: AuthService,
        mock_email_service,
        malicious_input: str,
    ):
        """Test SQL injection protection in registration."""
        # Arrange
        registration_data = UserRegistration(
            email=malicious_input,
            password="SecureP@ssw0rd123!",
            first_name="Malicious",
            last_name="User",
        )
        
        # Act & Assert - Should fail validation, not SQL error
        with pytest.raises((InvalidCredentialsError, ValueError)):
            await auth_service.register(registration_data)
    
    @pytest.mark.asyncio
    async def test_concurrent_registration_same_email(
        self,
        auth_service: AuthService,
        mock_email_service,
    ):
        """Test race condition protection for duplicate registrations."""
        import asyncio
        
        # Arrange
        email = "concurrent@mit.edu"
        registration_data = UserRegistration(
            email=email,
            password="SecureP@ssw0rd123!",
            first_name="Concurrent",
            last_name="User",
        )
        
        # Act - Try to register same email concurrently
        tasks = [
            auth_service.register(registration_data)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert - Only one should succeed
        successes = [r for r in results if isinstance(r, AuthResponse)]
        failures = [r for r in results if isinstance(r, UserAlreadyExistsError)]
        
        assert len(successes) == 1
        assert len(failures) == 4
    
    @pytest.mark.asyncio
    async def test_timing_attack_protection(
        self,
        auth_service: AuthService,
        test_user,
    ):
        """Test protection against timing attacks on login."""
        import time
        
        # Test with valid user, wrong password
        start1 = time.time()
        try:
            await auth_service.login(UserLogin(
                email=test_user.email,
                password="WrongPassword123!",
            ))
        except InvalidCredentialsError:
            pass
        time1 = time.time() - start1
        
        # Test with non-existent user
        start2 = time.time()
        try:
            await auth_service.login(UserLogin(
                email="nonexistent@mit.edu",
                password="AnyPassword123!",
            ))
        except InvalidCredentialsError:
            pass
        time2 = time.time() - start2
        
        # Assert - Times should be similar (within reasonable variance)
        # This prevents attackers from determining if email exists
        assert abs(time1 - time2) < 0.1  # Within 100ms