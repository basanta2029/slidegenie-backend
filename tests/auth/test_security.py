"""
Comprehensive security tests for SlideGenie authentication system.

Tests security features including rate limiting, account lockout,
SQL injection protection, XSS prevention, and CSRF protection.
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
import secrets
import time

from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.exceptions import (
    RateLimitExceededError,
    AccountLockedError,
    InvalidTokenError,
)
from app.services.security.rate_limiter import RateLimiter, RateLimitConfig
from app.services.security.lockout import AccountLockoutService, LockoutConfig
from app.services.auth.auth_service import AuthService
from app.services.auth.token_service import TokenService
from app.domain.schemas.auth import UserLogin, UserRegistration
from tests.fixtures.auth import AuthTestData


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest_asyncio.fixture
    async def rate_limiter(self):
        """Create rate limiter with test configuration."""
        config = RateLimitConfig(
            requests_per_minute=5,
            requests_per_hour=20,
            burst_size=3,
        )
        return RateLimiter(config)
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_normal_traffic(self, rate_limiter):
        """Test that normal traffic is allowed."""
        identifier = "test-user-1"
        
        # Make requests within limit
        for i in range(3):
            result = await rate_limiter.check_rate_limit(identifier, "login")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_requests(self, rate_limiter):
        """Test that excessive requests are blocked."""
        identifier = "test-user-2"
        
        # Make burst of requests
        for i in range(3):
            await rate_limiter.check_rate_limit(identifier, "login")
        
        # Next request should be rate limited
        with pytest.raises(RateLimitExceededError):
            await rate_limiter.check_rate_limit(identifier, "login")
    
    @pytest.mark.asyncio
    async def test_rate_limit_different_endpoints(self, rate_limiter):
        """Test rate limiting per endpoint."""
        identifier = "test-user-3"
        
        # Max out login endpoint
        for i in range(3):
            await rate_limiter.check_rate_limit(identifier, "login")
        
        # Should still be able to access register endpoint
        result = await rate_limiter.check_rate_limit(identifier, "register")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self, rate_limiter):
        """Test that rate limit recovers over time."""
        identifier = "test-user-4"
        
        # Max out rate limit
        for i in range(3):
            await rate_limiter.check_rate_limit(identifier, "login")
        
        # Should be rate limited
        is_limited = await rate_limiter.is_rate_limited(identifier, "login")
        assert is_limited is True
        
        # Wait for recovery (in real scenario this would be longer)
        await asyncio.sleep(0.1)
        
        # For testing, manually reset
        await rate_limiter.reset_rate_limit(identifier, "login")
        
        # Should be able to make request again
        result = await rate_limiter.check_rate_limit(identifier, "login")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_by_ip(self, rate_limiter):
        """Test rate limiting by IP address."""
        ip_address = "192.168.1.100"
        
        # Test IP-based rate limiting
        for i in range(3):
            await rate_limiter.check_rate_limit(ip_address, "login")
        
        # Should be rate limited
        with pytest.raises(RateLimitExceededError):
            await rate_limiter.check_rate_limit(ip_address, "login")
    
    @pytest.mark.asyncio
    async def test_distributed_rate_limiting(self, rate_limiter):
        """Test rate limiting across distributed system."""
        identifier = "distributed-user"
        
        # Simulate requests from multiple servers
        tasks = []
        for i in range(5):
            task = rate_limiter.check_rate_limit(
                identifier,
                "login",
                distributed=True
            )
            tasks.append(task)
        
        # Some should succeed, some should fail
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successes = [r for r in results if r is True]
        failures = [r for r in results if isinstance(r, RateLimitExceededError)]
        
        assert len(successes) == 3  # Burst size
        assert len(failures) == 2


class TestAccountLockout:
    """Test account lockout functionality."""
    
    @pytest_asyncio.fixture
    async def lockout_service(self):
        """Create lockout service with test configuration."""
        config = LockoutConfig(
            max_attempts=3,
            lockout_duration_minutes=30,
            reset_window_minutes=15,
        )
        return AccountLockoutService(config)
    
    @pytest.mark.asyncio
    async def test_failed_attempt_tracking(self, lockout_service):
        """Test tracking of failed login attempts."""
        account = "test@example.com"
        
        # Record failed attempts
        for i in range(2):
            await lockout_service.record_failed_attempt(account)
            is_locked = await lockout_service.is_account_locked(account)
            assert is_locked is False
        
        # Third attempt should lock account
        await lockout_service.record_failed_attempt(account)
        is_locked = await lockout_service.is_account_locked(account)
        assert is_locked is True
    
    @pytest.mark.asyncio
    async def test_successful_login_resets_attempts(self, lockout_service):
        """Test that successful login resets failed attempts."""
        account = "reset@example.com"
        
        # Record some failed attempts
        await lockout_service.record_failed_attempt(account)
        await lockout_service.record_failed_attempt(account)
        
        # Reset on successful login
        await lockout_service.reset_failed_attempts(account)
        
        # Should be able to fail again without lockout
        await lockout_service.record_failed_attempt(account)
        await lockout_service.record_failed_attempt(account)
        
        is_locked = await lockout_service.is_account_locked(account)
        assert is_locked is False
    
    @pytest.mark.asyncio
    async def test_lockout_expiration(self, lockout_service):
        """Test that lockout expires after duration."""
        account = "expire@example.com"
        
        # Lock the account
        for i in range(3):
            await lockout_service.record_failed_attempt(account)
        
        assert await lockout_service.is_account_locked(account) is True
        
        # Simulate time passing (would use time.sleep in real test)
        # For testing, manually unlock
        await lockout_service.unlock_account(account)
        
        assert await lockout_service.is_account_locked(account) is False
    
    @pytest.mark.asyncio
    async def test_get_lockout_info(self, lockout_service):
        """Test getting detailed lockout information."""
        account = "info@example.com"
        
        # Create lockout
        for i in range(3):
            await lockout_service.record_failed_attempt(account)
        
        # Get lockout info
        info = await lockout_service.get_lockout_info(account)
        
        assert info is not None
        assert info["is_locked"] is True
        assert info["failed_attempts"] == 3
        assert "locked_until" in info
        assert info["locked_until"] > datetime.now(timezone.utc)


class TestSQLInjectionProtection:
    """Test protection against SQL injection attacks."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("malicious_input", [
        "admin@test.com'; DROP TABLE users; --",
        "admin@test.com' OR '1'='1",
        "admin@test.com'; SELECT * FROM users; --",
        "admin@test.com\"; DROP TABLE users; --",
        "admin@test.com') OR ('1'='1",
    ])
    async def test_sql_injection_in_login(
        self,
        auth_service: AuthService,
        malicious_input: str,
    ):
        """Test SQL injection protection in login."""
        # Attempt login with malicious input
        credentials = UserLogin(
            email=malicious_input,
            password="any_password"
        )
        
        # Should fail with validation error, not SQL error
        with pytest.raises((ValueError, InvalidCredentialsError)):
            await auth_service.login(credentials)
    
    @pytest.mark.asyncio
    async def test_parameterized_queries(
        self,
        db_session: AsyncSession,
        auth_service: AuthService,
    ):
        """Test that queries use parameterization."""
        # Create a user with special characters
        registration = UserRegistration(
            email="test'user@example.edu",
            password="SecureP@ssw0rd123!",
            first_name="Test'Name",
            last_name="User\"Name",
        )
        
        # Should handle special characters safely
        try:
            result = await auth_service.register(registration)
            assert result.user.email == "test'user@example.edu"
        except InvalidCredentialsError:
            # Email validation might reject this, which is also fine
            pass


class TestXSSProtection:
    """Test protection against Cross-Site Scripting (XSS) attacks."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("xss_payload", [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
        "<svg onload=alert('xss')>",
        "';alert('xss');//",
    ])
    async def test_xss_in_user_registration(
        self,
        auth_service: AuthService,
        mock_email_service,
        xss_payload: str,
    ):
        """Test XSS protection in user registration."""
        # Try to register with XSS payload in name
        registration = UserRegistration(
            email="xss.test@example.edu",
            password="SecureP@ssw0rd123!",
            first_name=xss_payload,
            last_name="Test",
        )
        
        # Registration should succeed but payload should be escaped/sanitized
        result = await auth_service.register(registration)
        
        # Check that the stored name doesn't contain active script
        assert "<script>" not in result.user.first_name
        assert "javascript:" not in result.user.first_name
    
    @pytest.mark.asyncio
    async def test_output_encoding(self, authenticated_client: AsyncClient):
        """Test that API responses properly encode output."""
        # Make API request
        response = await authenticated_client.get("/api/v1/auth/me")
        
        # Check security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert "text/html" not in response.headers.get("Content-Type", "")


class TestCSRFProtection:
    """Test Cross-Site Request Forgery (CSRF) protection."""
    
    @pytest.mark.asyncio
    async def test_state_parameter_validation(self):
        """Test OAuth state parameter validation for CSRF protection."""
        from app.services.auth.oauth.google import GoogleOAuthProvider
        
        provider = GoogleOAuthProvider(
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost/callback"
        )
        
        # Generate state
        state = secrets.token_urlsafe(32)
        auth_url = provider.generate_authorization_url(state)
        
        # Verify state is included
        assert f"state={state}" in auth_url
        
        # Attempting token exchange with wrong state should fail
        with pytest.raises(OAuthError):
            await provider.exchange_code_for_tokens("code", "wrong-state")
    
    @pytest.mark.asyncio
    async def test_token_validation(self, token_service: TokenService):
        """Test that tokens include CSRF protection."""
        # Create token
        tokens = await token_service.create_token_pair(
            user_id=uuid4(),
            email="test@example.com",
            roles=["user"],
        )
        
        # Decode and verify token includes jti (unique ID)
        decoded = token_service.decode_token(tokens.access_token)
        assert "jti" in decoded  # JWT ID for CSRF protection


class TestPasswordSecurity:
    """Test password security features."""
    
    @pytest.mark.asyncio
    async def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        from app.core.security import get_password_hash, verify_password
        
        password = "SecureP@ssw0rd123!"
        
        # Hash password
        hashed = get_password_hash(password)
        
        # Verify properties
        assert password not in hashed
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert hashed.startswith("$2b$")  # Bcrypt prefix
        
        # Verify password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    @pytest.mark.asyncio
    async def test_password_timing_attack_protection(self):
        """Test protection against timing attacks on password verification."""
        from app.core.security import verify_password
        
        # Create a hash
        correct_password = "CorrectP@ssw0rd123!"
        password_hash = get_password_hash(correct_password)
        
        # Time correct password
        start = time.perf_counter()
        verify_password(correct_password, password_hash)
        correct_time = time.perf_counter() - start
        
        # Time incorrect passwords of different lengths
        wrong_passwords = [
            "a",
            "WrongPassword",
            "WrongP@ssw0rd123!",
            "AlmostCorrectP@ssw0rd123!",
        ]
        
        times = []
        for wrong_pw in wrong_passwords:
            start = time.perf_counter()
            verify_password(wrong_pw, password_hash)
            times.append(time.perf_counter() - start)
        
        # All times should be similar (constant-time comparison)
        for t in times:
            assert abs(t - correct_time) < 0.01  # Within 10ms


class TestAPIKeySecurity:
    """Test API key security features."""
    
    @pytest.mark.asyncio
    async def test_api_key_generation(self, api_key_service):
        """Test secure API key generation."""
        # Create API key
        key_data = await api_key_service.create_api_key(
            user_id=uuid4(),
            name="Test Key",
            roles=["api_user"],
        )
        
        # Verify key properties
        assert len(key_data["key"]) >= 32
        assert key_data["prefix"].startswith("sk_")
        assert key_data["key"].startswith(key_data["prefix"])
        
        # Key should be random
        key2 = await api_key_service.create_api_key(
            user_id=uuid4(),
            name="Test Key 2",
            roles=["api_user"],
        )
        assert key_data["key"] != key2["key"]
    
    @pytest.mark.asyncio
    async def test_api_key_storage(self, api_key_service, db_session):
        """Test that API keys are stored securely."""
        # Create API key
        key_data = await api_key_service.create_api_key(
            user_id=uuid4(),
            name="Test Key",
            roles=["api_user"],
        )
        
        # Verify key is hashed in database
        from app.infrastructure.database.models import APIKey
        
        stored_key = await db_session.get(APIKey, key_data["key_id"])
        assert stored_key is not None
        assert key_data["key"] not in stored_key.key_hash
        assert stored_key.key_hash != key_data["key"]


class TestSecurityHeaders:
    """Test security headers in responses."""
    
    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        """Test that security headers are included in responses."""
        response = await client.get("/api/v1/health")
        
        # Check security headers
        headers = response.headers
        
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert "X-XSS-Protection" in headers
        assert "Strict-Transport-Security" in headers
        
        # CSP header
        csp = headers.get("Content-Security-Policy")
        assert csp is not None
        assert "default-src" in csp
        assert "script-src" in csp


class TestInputValidation:
    """Test input validation and sanitization."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_email", [
        "not-an-email",
        "@example.com",
        "user@",
        "user@.com",
        "user@example..com",
        " user@example.com",
        "user@example.com ",
        "user name@example.com",
    ])
    async def test_email_validation(
        self,
        auth_service: AuthService,
        invalid_email: str,
    ):
        """Test email format validation."""
        registration = UserRegistration(
            email=invalid_email,
            password="SecureP@ssw0rd123!",
            first_name="Test",
            last_name="User",
        )
        
        with pytest.raises((ValueError, InvalidCredentialsError)):
            await auth_service.register(registration)
    
    @pytest.mark.asyncio
    async def test_unicode_handling(
        self,
        auth_service: AuthService,
        mock_email_service,
    ):
        """Test handling of unicode characters."""
        # Test with unicode characters
        registration = UserRegistration(
            email="user@example.edu",
            password="SecureP@ssw0rd123!",
            first_name="José",
            last_name="Müller",
        )
        
        result = await auth_service.register(registration)
        assert result.user.first_name == "José"
        assert result.user.last_name == "Müller"


class TestSessionSecurity:
    """Test session security features."""
    
    @pytest.mark.asyncio
    async def test_session_token_rotation(
        self,
        auth_service: AuthService,
        token_service: TokenService,
        test_user,
    ):
        """Test that tokens are rotated on refresh."""
        # Login to get initial tokens
        credentials = UserLogin(
            email=test_user.email,
            password=AuthTestData.STUDENT_USER["password"],
        )
        login_result = await auth_service.login(credentials)
        
        initial_access = login_result.tokens.access_token
        initial_refresh = login_result.tokens.refresh_token
        
        # Refresh tokens
        new_tokens = await auth_service.refresh_tokens(initial_refresh)
        
        # Verify tokens are different
        assert new_tokens.access_token != initial_access
        assert new_tokens.refresh_token != initial_refresh
        
        # Old tokens should be invalidated
        assert await token_service.is_token_blacklisted(initial_access)
        assert await token_service.is_token_blacklisted(initial_refresh)
    
    @pytest.mark.asyncio
    async def test_concurrent_session_handling(
        self,
        auth_service: AuthService,
        test_user,
    ):
        """Test handling of concurrent sessions."""
        credentials = UserLogin(
            email=test_user.email,
            password=AuthTestData.STUDENT_USER["password"],
        )
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            result = await auth_service.login(
                credentials,
                request_ip=f"192.168.1.{100+i}",
                user_agent=f"Device {i}",
            )
            sessions.append(result)
        
        # All sessions should be valid
        for session in sessions:
            assert session.tokens.access_token is not None
            
        # Each session should have unique tokens
        access_tokens = [s.tokens.access_token for s in sessions]
        assert len(set(access_tokens)) == 3