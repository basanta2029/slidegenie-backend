"""
Comprehensive tests for OAuth providers.

Tests Google and Microsoft OAuth implementations including token exchange,
user info retrieval, and academic email validation.
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
import json
from datetime import datetime, timedelta, timezone

import httpx
from httpx import Response

from app.services.auth.oauth.base import OAuthError, OAuthUserInfo, OAuthTokens
from app.services.auth.oauth.google import GoogleOAuthProvider
from app.services.auth.oauth.microsoft import MicrosoftOAuthProvider
from tests.fixtures.auth import AuthTestData


class TestGoogleOAuthProvider:
    """Test Google OAuth provider implementation."""
    
    @pytest.fixture
    def google_provider(self):
        """Create Google OAuth provider instance."""
        return GoogleOAuthProvider(
            client_id="test-google-client-id",
            client_secret="test-google-client-secret",
            redirect_uri="http://localhost:3000/auth/callback/google",
        )
    
    def test_authorization_url_generation(self, google_provider):
        """Test Google authorization URL generation."""
        # Arrange
        state = "test-state-123"
        
        # Act
        auth_url = google_provider.generate_authorization_url(state)
        
        # Assert
        assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
        assert "client_id=test-google-client-id" in auth_url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback%2Fgoogle" in auth_url
        assert f"state={state}" in auth_url
        assert "scope=openid+email+profile" in auth_url
        assert "access_type=offline" in auth_url
        assert "prompt=consent" in auth_url
    
    @pytest.mark.asyncio
    async def test_exchange_code_success(self, google_provider):
        """Test successful authorization code exchange."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email profile",
            "id_token": "google-id-token",
        }
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            # Act
            tokens = await google_provider.exchange_code_for_tokens(
                code="test-auth-code",
                state="test-state",
            )
        
        # Assert
        assert isinstance(tokens, OAuthTokens)
        assert tokens.access_token == "google-access-token"
        assert tokens.refresh_token == "google-refresh-token"
        assert tokens.expires_in == 3600
        assert tokens.id_token == "google-id-token"
    
    @pytest.mark.asyncio
    async def test_exchange_code_failure(self, google_provider):
        """Test failed authorization code exchange."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid authorization code",
        }
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            # Act & Assert
            with pytest.raises(OAuthError) as exc:
                await google_provider.exchange_code_for_tokens(
                    code="invalid-code",
                    state="test-state",
                )
            
            assert "invalid_grant" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_get_user_info_academic_email(self, google_provider):
        """Test fetching user info with academic email."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "google-user-123",
            "email": "student@stanford.edu",
            "email_verified": True,
            "name": "John Student",
            "given_name": "John",
            "family_name": "Student",
            "picture": "https://example.com/photo.jpg",
            "locale": "en-US",
            "hd": "stanford.edu",  # Google's hosted domain field
        }
        
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            # Act
            user_info = await google_provider.get_user_info("test-access-token")
        
        # Assert
        assert isinstance(user_info, OAuthUserInfo)
        assert user_info.id == "google-user-123"
        assert user_info.email == "student@stanford.edu"
        assert user_info.verified_email is True
        assert user_info.first_name == "John"
        assert user_info.last_name == "Student"
        assert user_info.domain == "stanford.edu"
        assert user_info.is_edu_email is True
        assert user_info.institution == "Stanford University"
        assert user_info.hd == "stanford.edu"
        assert user_info.provider == "google"
    
    @pytest.mark.asyncio
    async def test_get_user_info_non_academic_email(self, google_provider):
        """Test fetching user info with non-academic email."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "google-user-456",
            "email": "user@gmail.com",
            "email_verified": True,
            "name": "Regular User",
            "given_name": "Regular",
            "family_name": "User",
        }
        
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            # Act
            user_info = await google_provider.get_user_info("test-access-token")
        
        # Assert
        assert user_info.email == "user@gmail.com"
        assert user_info.domain == "gmail.com"
        assert user_info.is_edu_email is False
        assert user_info.institution is None
    
    @pytest.mark.asyncio
    async def test_get_user_info_unverified_email(self, google_provider):
        """Test fetching user info with unverified email."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "google-user-789",
            "email": "unverified@example.com",
            "email_verified": False,
            "name": "Unverified User",
        }
        
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            # Act
            user_info = await google_provider.get_user_info("test-access-token")
        
        # Assert
        assert user_info.verified_email is False
    
    @pytest.mark.asyncio
    async def test_refresh_access_token(self, google_provider):
        """Test refreshing access token."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-google-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email profile",
        }
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            # Act
            new_tokens = await google_provider.refresh_access_token("refresh-token")
        
        # Assert
        assert new_tokens.access_token == "new-google-access-token"
        assert new_tokens.refresh_token is None  # Google doesn't return new refresh token


class TestMicrosoftOAuthProvider:
    """Test Microsoft OAuth provider implementation."""
    
    @pytest.fixture
    def microsoft_provider(self):
        """Create Microsoft OAuth provider instance."""
        return MicrosoftOAuthProvider(
            client_id="test-microsoft-client-id",
            client_secret="test-microsoft-client-secret",
            redirect_uri="http://localhost:3000/auth/callback/microsoft",
        )
    
    def test_authorization_url_generation(self, microsoft_provider):
        """Test Microsoft authorization URL generation."""
        # Arrange
        state = "test-state-456"
        
        # Act
        auth_url = microsoft_provider.generate_authorization_url(state)
        
        # Assert
        assert "https://login.microsoftonline.com/common/oauth2/v2.0/authorize" in auth_url
        assert "client_id=test-microsoft-client-id" in auth_url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback%2Fmicrosoft" in auth_url
        assert f"state={state}" in auth_url
        assert "scope=openid+email+profile+offline_access" in auth_url
        assert "prompt=select_account" in auth_url
    
    @pytest.mark.asyncio
    async def test_exchange_code_success(self, microsoft_provider):
        """Test successful authorization code exchange."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "ms-access-token",
            "refresh_token": "ms-refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email profile offline_access",
            "id_token": "ms-id-token",
        }
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            # Act
            tokens = await microsoft_provider.exchange_code_for_tokens(
                code="test-auth-code",
                state="test-state",
            )
        
        # Assert
        assert tokens.access_token == "ms-access-token"
        assert tokens.refresh_token == "ms-refresh-token"
    
    @pytest.mark.asyncio
    async def test_get_user_info_academic_email(self, microsoft_provider):
        """Test fetching user info with academic email from Microsoft."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ms-user-123",
            "mail": "professor@yale.edu",
            "displayName": "Dr. Jane Professor",
            "givenName": "Jane",
            "surname": "Professor",
            "userPrincipalName": "professor@yale.edu",
            "mailboxSettings": {"language": {"locale": "en-US"}},
        }
        
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            # Act
            user_info = await microsoft_provider.get_user_info("test-access-token")
        
        # Assert
        assert user_info.id == "ms-user-123"
        assert user_info.email == "professor@yale.edu"
        assert user_info.first_name == "Jane"
        assert user_info.last_name == "Professor"
        assert user_info.domain == "yale.edu"
        assert user_info.is_edu_email is True
        assert user_info.institution == "Yale University"
        assert user_info.provider == "microsoft"
    
    @pytest.mark.asyncio
    async def test_get_user_info_work_email(self, microsoft_provider):
        """Test fetching user info with work email from Microsoft."""
        # Arrange
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ms-user-456",
            "mail": "researcher@company.com",
            "displayName": "Research User",
            "givenName": "Research",
            "surname": "User",
            "userPrincipalName": "researcher@company.com",
        }
        
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            # Act
            user_info = await microsoft_provider.get_user_info("test-access-token")
        
        # Assert
        assert user_info.email == "researcher@company.com"
        assert user_info.domain == "company.com"
        assert user_info.is_edu_email is False
        assert user_info.verified_email is True  # Microsoft emails are verified


class TestOAuthProviderSecurity:
    """Test OAuth security features."""
    
    @pytest.fixture
    def providers(self):
        """Create OAuth providers for testing."""
        return {
            "google": GoogleOAuthProvider(
                client_id="test-client",
                client_secret="test-secret",
                redirect_uri="http://localhost:3000/callback",
            ),
            "microsoft": MicrosoftOAuthProvider(
                client_id="test-client",
                client_secret="test-secret",
                redirect_uri="http://localhost:3000/callback",
            ),
        }
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("provider_name", ["google", "microsoft"])
    async def test_token_exchange_network_error(self, providers, provider_name):
        """Test handling of network errors during token exchange."""
        provider = providers[provider_name]
        
        with patch("httpx.AsyncClient.post", side_effect=httpx.NetworkError("Connection failed")):
            # Act & Assert
            with pytest.raises(OAuthError) as exc:
                await provider.exchange_code_for_tokens("code", "state")
            
            assert "Token exchange failed" in str(exc.value)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("provider_name", ["google", "microsoft"])
    async def test_user_info_unauthorized(self, providers, provider_name):
        """Test handling of unauthorized access to user info."""
        provider = providers[provider_name]
        
        mock_response = Mock(spec=Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "invalid_token"}
        
        with patch("httpx.AsyncClient.get", return_value=mock_response):
            # Act & Assert
            with pytest.raises(OAuthError) as exc:
                await provider.get_user_info("invalid-token")
            
            assert "Failed to fetch user info" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_validate_user_info_unverified_email(self, providers):
        """Test validation of unverified email addresses."""
        provider = providers["google"]
        
        # Arrange
        user_info = OAuthUserInfo(
            id="test-user",
            email="unverified@example.com",
            name="Test User",
            verified_email=False,
            provider="google",
        )
        
        # Act
        is_valid = await provider.validate_user_info(user_info)
        
        # Assert
        assert is_valid is False
    
    def test_state_parameter_inclusion(self, providers):
        """Test CSRF protection via state parameter."""
        for provider in providers.values():
            # Generate URLs with different states
            url1 = provider.generate_authorization_url("state-123")
            url2 = provider.generate_authorization_url("state-456")
            
            # Assert states are included and different
            assert "state=state-123" in url1
            assert "state=state-456" in url2
            assert url1 != url2
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("malicious_input", [
        "'; DROP TABLE users; --",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
    ])
    async def test_oauth_injection_protection(self, providers, malicious_input):
        """Test protection against injection attacks in OAuth flow."""
        provider = providers["google"]
        
        # Test in authorization URL generation
        url = provider.generate_authorization_url(malicious_input)
        # URL encoding should sanitize the input
        assert malicious_input not in url
        assert "DROP TABLE" not in url
        assert "<script>" not in url


class TestOAuthProviderIntegration:
    """Test OAuth provider integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_oauth_flow_google(self):
        """Test complete OAuth flow for Google."""
        provider = GoogleOAuthProvider(
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:3000/callback",
        )
        
        # Step 1: Generate authorization URL
        state = "secure-random-state"
        auth_url = provider.generate_authorization_url(state)
        assert auth_url is not None
        
        # Step 2: Mock code exchange
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "access_token": "access-123",
                "refresh_token": "refresh-123",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
            
            tokens = await provider.exchange_code_for_tokens("auth-code", state)
            assert tokens.access_token == "access-123"
        
        # Step 3: Mock user info retrieval
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "sub": "user-123",
                "email": "student@mit.edu",
                "email_verified": True,
                "name": "Test Student",
                "hd": "mit.edu",
            }
            
            user_info = await provider.get_user_info(tokens.access_token)
            assert user_info.email == "student@mit.edu"
            assert user_info.is_edu_email is True
    
    @pytest.mark.asyncio
    async def test_oauth_provider_comparison(self):
        """Test consistency between different OAuth providers."""
        # Create providers
        google = GoogleOAuthProvider("client", "secret", "http://localhost/callback")
        microsoft = MicrosoftOAuthProvider("client", "secret", "http://localhost/callback")
        
        # Both should have required properties
        for provider in [google, microsoft]:
            assert provider.authorization_base_url is not None
            assert provider.token_url is not None
            assert provider.user_info_url is not None
            assert provider.scope is not None
            
            # Both should generate valid URLs
            auth_url = provider.generate_authorization_url("test-state")
            assert "client_id=client" in auth_url
            assert "state=test-state" in auth_url