"""
Mock OAuth providers for testing.

Provides mock implementations of OAuth providers to test
authentication flows without external dependencies.
"""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from unittest.mock import AsyncMock

import httpx
import pytest


class MockOAuthProvider:
    """Base mock OAuth provider."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.client_id = f"mock_{provider_name}_client_id"
        self.client_secret = f"mock_{provider_name}_client_secret"
        self.redirect_uri = f"http://localhost:3000/auth/callback/{provider_name}"
        
        # Track calls for testing
        self.call_log: Dict[str, int] = {}
        self.last_call_data: Dict[str, Any] = {}
    
    def _log_call(self, method_name: str, **kwargs):
        """Log method calls for testing verification."""
        self.call_log[method_name] = self.call_log.get(method_name, 0) + 1
        self.last_call_data[method_name] = kwargs
    
    async def get_authorization_url(
        self,
        scopes: list[str],
        state: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, str]:
        """Generate mock authorization URL."""
        self._log_call("get_authorization_url", scopes=scopes, state=state, **kwargs)
        
        state = state or secrets.token_urlsafe(32)
        scope_string = " ".join(scopes)
        
        url = (
            f"https://mock-{self.provider_name}-oauth.com/authorize"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={scope_string}"
            f"&state={state}"
            f"&response_type=code"
        )
        
        return url, state
    
    async def exchange_code_for_token(
        self,
        code: str,
        state: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        self._log_call("exchange_code_for_token", code=code, state=state, **kwargs)
        
        # Simulate different responses based on code
        if code == "invalid_code":
            raise httpx.HTTPStatusError(
                "Invalid authorization code",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(400),
            )
        
        if code == "expired_code":
            raise httpx.HTTPStatusError(
                "Authorization code expired",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(400),
            )
        
        return {
            "access_token": f"mock_{self.provider_name}_access_token",
            "refresh_token": f"mock_{self.provider_name}_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "email profile",
        }
    
    async def get_user_info(self, access_token: str, **kwargs) -> Dict[str, Any]:
        """Get user information from OAuth provider."""
        self._log_call("get_user_info", access_token=access_token, **kwargs)
        
        # Simulate different responses based on token
        if access_token == "invalid_token":
            raise httpx.HTTPStatusError(
                "Invalid access token",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(401),
            )
        
        return {
            "id": f"mock_{self.provider_name}_user_id",
            "email": f"user@{self.provider_name}-university.edu",
            "first_name": f"{self.provider_name.title()}",
            "last_name": "User",
            "institution": f"{self.provider_name.title()} University",
            "verified": True,
            "picture": f"https://mock-{self.provider_name}.com/avatar.jpg",
        }
    
    async def refresh_access_token(
        self,
        refresh_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        self._log_call("refresh_access_token", refresh_token=refresh_token, **kwargs)
        
        if refresh_token == "invalid_refresh_token":
            raise httpx.HTTPStatusError(
                "Invalid refresh token",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(400),
            )
        
        return {
            "access_token": f"new_mock_{self.provider_name}_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "email profile",
        }
    
    async def revoke_token(self, token: str, **kwargs) -> bool:
        """Revoke an access or refresh token."""
        self._log_call("revoke_token", token=token, **kwargs)
        
        # Simulate revocation failure for specific tokens
        if token == "unrevokable_token":
            return False
        
        return True
    
    def validate_state(self, received_state: str, expected_state: str) -> bool:
        """Validate OAuth state parameter."""
        self._log_call("validate_state", received_state=received_state, expected_state=expected_state)
        return received_state == expected_state
    
    def get_call_count(self, method_name: str) -> int:
        """Get number of times a method was called."""
        return self.call_log.get(method_name, 0)
    
    def get_last_call_data(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Get data from last method call."""
        return self.last_call_data.get(method_name)
    
    def reset_call_log(self):
        """Reset call tracking."""
        self.call_log.clear()
        self.last_call_data.clear()


class MockGoogleOAuthProvider(MockOAuthProvider):
    """Mock Google OAuth provider."""
    
    def __init__(self):
        super().__init__("google")
        self.discovery_url = "https://accounts.google.com/.well-known/openid_configuration"
    
    async def get_user_info(self, access_token: str, **kwargs) -> Dict[str, Any]:
        """Get Google user information."""
        self._log_call("get_user_info", access_token=access_token, **kwargs)
        
        if access_token == "invalid_token":
            raise httpx.HTTPStatusError(
                "Invalid access token",
                request=httpx.Request("GET", "https://googleapis.com"),
                response=httpx.Response(401),
            )
        
        return {
            "id": "google_user_123456789",
            "email": "student@stanford.edu",
            "first_name": "Google",
            "last_name": "Student",
            "institution": "Stanford University",
            "verified": True,
            "picture": "https://lh3.googleusercontent.com/avatar.jpg",
            "locale": "en",
            "hd": "stanford.edu",  # G Suite domain
        }
    
    async def verify_id_token(self, id_token: str, **kwargs) -> Dict[str, Any]:
        """Verify Google ID token (OpenID Connect)."""
        self._log_call("verify_id_token", id_token=id_token, **kwargs)
        
        if id_token == "invalid_id_token":
            raise ValueError("Invalid ID token signature")
        
        return {
            "iss": "https://accounts.google.com",
            "sub": "google_user_123456789",
            "aud": self.client_id,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "email": "student@stanford.edu",
            "email_verified": True,
            "name": "Google Student",
            "given_name": "Google",
            "family_name": "Student",
            "picture": "https://lh3.googleusercontent.com/avatar.jpg",
            "hd": "stanford.edu",
        }


class MockMicrosoftOAuthProvider(MockOAuthProvider):
    """Mock Microsoft OAuth provider."""
    
    def __init__(self):
        super().__init__("microsoft")
        self.tenant_id = "common"  # Multi-tenant application
    
    async def get_user_info(self, access_token: str, **kwargs) -> Dict[str, Any]:
        """Get Microsoft user information."""
        self._log_call("get_user_info", access_token=access_token, **kwargs)
        
        if access_token == "invalid_token":
            raise httpx.HTTPStatusError(
                "Invalid access token",
                request=httpx.Request("GET", "https://graph.microsoft.com"),
                response=httpx.Response(401),
            )
        
        return {
            "id": "microsoft_user_abc123",
            "email": "researcher@mit.edu",
            "first_name": "Microsoft",
            "last_name": "Researcher",
            "institution": "MIT",
            "verified": True,
            "displayName": "Microsoft Researcher",
            "jobTitle": "Graduate Researcher",
            "department": "Computer Science",
            "companyName": "MIT",
            "userPrincipalName": "researcher@mit.edu",
        }
    
    async def get_organization_info(self, access_token: str) -> Dict[str, Any]:
        """Get user's organization information from Microsoft Graph."""
        self._log_call("get_organization_info", access_token=access_token)
        
        return {
            "id": "mit_org_123",
            "displayName": "Massachusetts Institute of Technology",
            "businessPhones": ["+1-617-253-1000"],
            "city": "Cambridge",
            "country": "United States",
            "postalCode": "02139",
            "state": "Massachusetts",
            "street": "77 Massachusetts Avenue",
        }


class MockOAuthError:
    """Mock OAuth error responses."""
    
    @staticmethod
    def invalid_client_error():
        """Mock invalid client error."""
        return {
            "error": "invalid_client",
            "error_description": "Client authentication failed",
            "error_uri": "https://tools.ietf.org/html/rfc6749#section-5.2",
        }
    
    @staticmethod
    def invalid_grant_error():
        """Mock invalid grant error."""
        return {
            "error": "invalid_grant",
            "error_description": "The provided authorization grant is invalid",
            "error_uri": "https://tools.ietf.org/html/rfc6749#section-5.2",
        }
    
    @staticmethod
    def access_denied_error():
        """Mock access denied error."""
        return {
            "error": "access_denied",
            "error_description": "The resource owner denied the request",
            "error_uri": "https://tools.ietf.org/html/rfc6749#section-4.1.2.1",
        }
    
    @staticmethod
    def invalid_scope_error():
        """Mock invalid scope error."""
        return {
            "error": "invalid_scope",
            "error_description": "The requested scope is invalid",
            "error_uri": "https://tools.ietf.org/html/rfc6749#section-5.2",
        }


class MockEmailService:
    """Mock email service for testing."""
    
    def __init__(self):
        self.sent_emails: list[Dict[str, Any]] = []
        self.email_tokens: Dict[str, Dict[str, Any]] = {}
        self.failure_emails: set[str] = set()
    
    async def send_verification_email(
        self,
        email: str,
        first_name: str,
        verification_token: str,
        **kwargs
    ) -> bool:
        """Send email verification email."""
        if email in self.failure_emails:
            return False
        
        self.sent_emails.append({
            "type": "verification",
            "to": email,
            "first_name": first_name,
            "token": verification_token,
            "sent_at": datetime.now(timezone.utc),
        })
        
        # Store token for validation
        self.email_tokens[verification_token] = {
            "email": email,
            "type": "verification",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        }
        
        return True
    
    async def send_password_reset_email(
        self,
        email: str,
        first_name: str,
        reset_token: str,
        **kwargs
    ) -> bool:
        """Send password reset email."""
        if email in self.failure_emails:
            return False
        
        self.sent_emails.append({
            "type": "password_reset",
            "to": email,
            "first_name": first_name,
            "token": reset_token,
            "sent_at": datetime.now(timezone.utc),
        })
        
        # Store token for validation
        self.email_tokens[reset_token] = {
            "email": email,
            "type": "password_reset",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        
        return True
    
    async def send_welcome_email(
        self,
        email: str,
        first_name: str,
        **kwargs
    ) -> bool:
        """Send welcome email."""
        if email in self.failure_emails:
            return False
        
        self.sent_emails.append({
            "type": "welcome",
            "to": email,
            "first_name": first_name,
            "sent_at": datetime.now(timezone.utc),
        })
        
        return True
    
    async def send_security_alert_email(
        self,
        email: str,
        first_name: str,
        alert_type: str,
        details: Dict[str, Any],
        **kwargs
    ) -> bool:
        """Send security alert email."""
        if email in self.failure_emails:
            return False
        
        self.sent_emails.append({
            "type": "security_alert",
            "to": email,
            "first_name": first_name,
            "alert_type": alert_type,
            "details": details,
            "sent_at": datetime.now(timezone.utc),
        })
        
        return True
    
    def generate_email_token(self, token_type: str = "verification") -> str:
        """Generate email verification/reset token."""
        return f"mock_{token_type}_token_{secrets.token_urlsafe(32)}"
    
    def verify_email_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify email token and return associated data."""
        token_data = self.email_tokens.get(token)
        if not token_data:
            return None
        
        # Check if token has expired
        if datetime.now(timezone.utc) > token_data["expires_at"]:
            return None
        
        return token_data
    
    def invalidate_token(self, token: str) -> bool:
        """Invalidate an email token."""
        return self.email_tokens.pop(token, None) is not None
    
    def add_failing_email(self, email: str):
        """Add email to failure list (simulates email delivery failure)."""
        self.failure_emails.add(email)
    
    def remove_failing_email(self, email: str):
        """Remove email from failure list."""
        self.failure_emails.discard(email)
    
    def get_sent_emails(self, email_type: Optional[str] = None) -> list[Dict[str, Any]]:
        """Get sent emails, optionally filtered by type."""
        if email_type:
            return [email for email in self.sent_emails if email["type"] == email_type]
        return self.sent_emails.copy()
    
    def clear_sent_emails(self):
        """Clear sent emails list."""
        self.sent_emails.clear()
        self.email_tokens.clear()


class MockRateLimitService:
    """Mock rate limiting service for testing."""
    
    def __init__(self):
        self.request_counts: Dict[str, int] = {}
        self.blocked_ips: set[str] = set()
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limit."""
        # Check if IP is blocked
        if identifier in self.blocked_ips:
            return False, {
                "allowed": False,
                "limit": limit,
                "remaining": 0,
                "reset_time": datetime.now(timezone.utc) + timedelta(seconds=window_seconds),
                "blocked": True,
            }
        
        # Get current count
        current_count = self.request_counts.get(identifier, 0)
        
        # Check if limit exceeded
        if current_count >= limit:
            return False, {
                "allowed": False,
                "limit": limit,
                "remaining": 0,
                "reset_time": datetime.now(timezone.utc) + timedelta(seconds=window_seconds),
                "blocked": False,
            }
        
        # Increment count
        self.request_counts[identifier] = current_count + 1
        
        return True, {
            "allowed": True,
            "limit": limit,
            "remaining": limit - (current_count + 1),
            "reset_time": datetime.now(timezone.utc) + timedelta(seconds=window_seconds),
            "blocked": False,
        }
    
    def block_ip(self, ip_address: str, duration_seconds: Optional[int] = None):
        """Block an IP address."""
        self.blocked_ips.add(ip_address)
        
        if duration_seconds:
            # In a real implementation, this would use a scheduler
            # For testing, we'll just track it
            self.rate_limits[ip_address] = {
                "blocked_until": datetime.now(timezone.utc) + timedelta(seconds=duration_seconds),
                "reason": "rate_limit_exceeded",
            }
    
    def unblock_ip(self, ip_address: str):
        """Unblock an IP address."""
        self.blocked_ips.discard(ip_address)
        self.rate_limits.pop(ip_address, None)
    
    def reset_counts(self, identifier: Optional[str] = None):
        """Reset request counts."""
        if identifier:
            self.request_counts.pop(identifier, None)
        else:
            self.request_counts.clear()
    
    def get_current_count(self, identifier: str) -> int:
        """Get current request count for identifier."""
        return self.request_counts.get(identifier, 0)
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked."""
        return identifier in self.blocked_ips


class MockCaptchaService:
    """Mock CAPTCHA service for testing."""
    
    def __init__(self):
        self.valid_tokens: set[str] = set()
        self.used_tokens: set[str] = set()
        self.failure_tokens: set[str] = set()
    
    def generate_captcha_challenge(self) -> Dict[str, Any]:
        """Generate CAPTCHA challenge."""
        token = f"captcha_token_{secrets.token_urlsafe(16)}"
        self.valid_tokens.add(token)
        
        return {
            "token": token,
            "challenge_type": "image",
            "challenge_data": "base64_encoded_image_data",
            "expires_in": 300,  # 5 minutes
        }
    
    async def verify_captcha_response(
        self,
        token: str,
        response: str,
        **kwargs
    ) -> bool:
        """Verify CAPTCHA response."""
        # Check if token is valid and not used
        if token not in self.valid_tokens or token in self.used_tokens:
            return False
        
        # Check if token is in failure list
        if token in self.failure_tokens:
            return False
        
        # Mark token as used
        self.used_tokens.add(token)
        self.valid_tokens.discard(token)
        
        # Simple validation - in real implementation would check actual response
        return response.lower() != "invalid"
    
    def add_failing_token(self, token: str):
        """Add token to failure list."""
        self.failure_tokens.add(token)
    
    def clear_tokens(self):
        """Clear all tokens."""
        self.valid_tokens.clear()
        self.used_tokens.clear()
        self.failure_tokens.clear()


# Pytest fixtures for mock services
@pytest.fixture
def mock_google_oauth() -> MockGoogleOAuthProvider:
    """Create mock Google OAuth provider."""
    return MockGoogleOAuthProvider()


@pytest.fixture
def mock_microsoft_oauth() -> MockMicrosoftOAuthProvider:
    """Create mock Microsoft OAuth provider."""
    return MockMicrosoftOAuthProvider()


@pytest.fixture
def mock_email_service() -> MockEmailService:
    """Create mock email service."""
    return MockEmailService()


@pytest.fixture
def mock_rate_limit_service() -> MockRateLimitService:
    """Create mock rate limit service."""
    return MockRateLimitService()


@pytest.fixture
def mock_captcha_service() -> MockCaptchaService:
    """Create mock CAPTCHA service."""
    return MockCaptchaService()


@pytest.fixture
def oauth_test_scenarios():
    """OAuth testing scenarios."""
    return {
        "successful_flow": {
            "code": "valid_authorization_code",
            "state": "secure_state_token",
            "expected_token": "mock_google_access_token",
            "expected_user": {
                "email": "student@stanford.edu",
                "first_name": "Google",
                "last_name": "Student",
            },
        },
        "invalid_code": {
            "code": "invalid_code",
            "state": "secure_state_token",
            "should_fail": True,
            "error_type": "invalid_grant",
        },
        "expired_code": {
            "code": "expired_code",
            "state": "secure_state_token",
            "should_fail": True,
            "error_type": "invalid_grant",
        },
        "state_mismatch": {
            "code": "valid_authorization_code",
            "state": "wrong_state_token",
            "should_fail": True,
            "error_type": "invalid_state",
        },
    }