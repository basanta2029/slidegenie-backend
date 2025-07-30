"""
Authentication Test Fixtures for SlideGenie.

Provides reusable fixtures for auth testing including users, tokens,
OAuth providers, and security configurations.
"""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import get_password_hash
from app.domain.schemas.auth import (
    UserRegistration,
    UserLogin,
    AuthResponse,
    UserProfile,
)
from app.infrastructure.database.models import User
from app.repositories.user import UserRepository
from app.services.auth.auth_service import AuthService
from app.services.auth.token_service import TokenService, TokenPair
from app.services.auth.oauth.base import OAuthUserInfo, OAuthTokens
from app.services.auth.authorization.rbac import RoleType, role_manager
from app.services.auth.authorization.permissions import Permission, PermissionAction, ResourceType
from app.services.auth.authorization.api_keys import APIKeyService


class AuthTestData:
    """Test data for authentication tests."""
    
    # Test users
    STUDENT_USER = {
        "email": "john.doe@mit.edu",
        "password": "SecureP@ssw0rd123!",
        "first_name": "John",
        "last_name": "Doe",
        "institution": "MIT",
        "role": "student",
    }
    
    FACULTY_USER = {
        "email": "jane.smith@harvard.edu",
        "password": "Pr0fess0r@Pass!",
        "first_name": "Jane",
        "last_name": "Smith",
        "institution": "Harvard University",
        "role": "faculty",
    }
    
    ADMIN_USER = {
        "email": "admin@slidegenie.edu",
        "password": "Adm1n@SecurePass!",
        "first_name": "Admin",
        "last_name": "User",
        "institution": "SlideGenie",
        "role": "admin",
    }
    
    NON_EDU_USER = {
        "email": "user@gmail.com",
        "password": "RegularP@ss123!",
        "first_name": "Regular",
        "last_name": "User",
        "institution": "Personal",
        "role": "user",
    }
    
    # OAuth test data
    GOOGLE_OAUTH_INFO = OAuthUserInfo(
        id="google_123456",
        email="oauth.user@stanford.edu",
        name="OAuth User",
        first_name="OAuth",
        last_name="User",
        picture="https://example.com/picture.jpg",
        verified_email=True,
        locale="en",
        domain="stanford.edu",
        is_edu_email=True,
        institution="Stanford University",
        hd="stanford.edu",
        provider="google",
        raw_data={"sub": "google_123456"},
    )
    
    MICROSOFT_OAUTH_INFO = OAuthUserInfo(
        id="ms_789012",
        email="ms.user@yale.edu",
        name="Microsoft User",
        first_name="Microsoft",
        last_name="User",
        verified_email=True,
        domain="yale.edu",
        is_edu_email=True,
        institution="Yale University",
        provider="microsoft",
        raw_data={"oid": "ms_789012"},
    )
    
    # Security test data
    WEAK_PASSWORDS = [
        "password123",  # No special char
        "Password!",    # Too short
        "password@123", # No uppercase
        "PASSWORD@123", # No lowercase
        "Password@ABC", # No number
    ]
    
    MALICIOUS_INPUTS = [
        "admin@test.com'; DROP TABLE users; --",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
        "%00",
        "admin@test.com\x00malicious",
        "' OR '1'='1",
    ]
    
    # Token test data
    EXPIRED_TOKEN_CLAIMS = {
        "sub": str(uuid4()),
        "email": "expired@test.edu",
        "roles": ["user"],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    
    INVALID_TOKEN_CLAIMS = {
        "sub": "not-a-uuid",
        "email": "invalid@test.edu",
        "roles": ["fake_role"],
    }


@pytest.fixture
def auth_test_data():
    """Provide auth test data."""
    return AuthTestData()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in database."""
    user_repo = UserRepository(db_session)
    
    user = User(
        email=AuthTestData.STUDENT_USER["email"],
        password_hash=get_password_hash(AuthTestData.STUDENT_USER["password"]),
        full_name=f"{AuthTestData.STUDENT_USER['first_name']} {AuthTestData.STUDENT_USER['last_name']}",
        institution=AuthTestData.STUDENT_USER["institution"],
        role=AuthTestData.STUDENT_USER["role"],
        is_active=True,
        is_verified=True,
    )
    
    created_user = await user_repo.create(user)
    yield created_user
    
    # Cleanup
    await user_repo.delete(created_user.id)


@pytest_asyncio.fixture
async def unverified_user(db_session: AsyncSession) -> User:
    """Create an unverified test user."""
    user_repo = UserRepository(db_session)
    
    user = User(
        email="unverified@mit.edu",
        password_hash=get_password_hash("UnverifiedP@ss123!"),
        full_name="Unverified User",
        institution="MIT",
        role="student",
        is_active=True,
        is_verified=False,
        verification_token=secrets.token_urlsafe(32),
    )
    
    created_user = await user_repo.create(user)
    yield created_user
    
    # Cleanup
    await user_repo.delete(created_user.id)


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user_repo = UserRepository(db_session)
    
    user = User(
        email=AuthTestData.ADMIN_USER["email"],
        password_hash=get_password_hash(AuthTestData.ADMIN_USER["password"]),
        full_name=f"{AuthTestData.ADMIN_USER['first_name']} {AuthTestData.ADMIN_USER['last_name']}",
        institution=AuthTestData.ADMIN_USER["institution"],
        role=AuthTestData.ADMIN_USER["role"],
        is_active=True,
        is_verified=True,
    )
    
    created_user = await user_repo.create(user)
    yield created_user
    
    # Cleanup
    await user_repo.delete(created_user.id)


@pytest.fixture
def auth_service(db_session: AsyncSession) -> AuthService:
    """Create auth service instance."""
    return AuthService(db_session)


@pytest.fixture
def token_service() -> TokenService:
    """Create token service instance."""
    return TokenService()


@pytest_asyncio.fixture
async def auth_tokens(test_user: User, token_service: TokenService) -> TokenPair:
    """Create valid auth tokens for test user."""
    return await token_service.create_token_pair(
        user_id=test_user.id,
        email=test_user.email,
        roles=[test_user.role],
        institution=test_user.institution,
    )


@pytest_asyncio.fixture
async def expired_tokens(test_user: User) -> TokenPair:
    """Create expired auth tokens."""
    # This would need custom token generation logic to create expired tokens
    # For now, we'll use the test data
    access_token = "expired.access.token"
    refresh_token = "expired.refresh.token"
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=-3600,  # Expired 1 hour ago
    )


@pytest.fixture
def mock_oauth_tokens() -> OAuthTokens:
    """Create mock OAuth tokens."""
    return OAuthTokens(
        access_token="mock_oauth_access_token",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="mock_oauth_refresh_token",
        scope="openid email profile",
        id_token="mock_id_token",
    )


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient,
    test_user: User,
    auth_tokens: TokenPair,
) -> AsyncClient:
    """Create authenticated HTTP client."""
    client.headers["Authorization"] = f"Bearer {auth_tokens.access_token}"
    client.headers["X-User-ID"] = str(test_user.id)
    return client


@pytest_asyncio.fixture
async def admin_client(
    client: AsyncClient,
    admin_user: User,
    token_service: TokenService,
) -> AsyncClient:
    """Create admin authenticated HTTP client."""
    tokens = await token_service.create_token_pair(
        user_id=admin_user.id,
        email=admin_user.email,
        roles=[admin_user.role],
        institution=admin_user.institution,
    )
    
    client.headers["Authorization"] = f"Bearer {tokens.access_token}"
    client.headers["X-User-ID"] = str(admin_user.id)
    return client


@pytest.fixture
def mock_email_service(mocker):
    """Mock email service for testing."""
    mock = mocker.patch("app.services.auth.email_service.EmailValidationService")
    mock_instance = mock.return_value
    
    # Mock academic email validation
    mock_instance.validate_academic_email.return_value = asyncio.coroutine(
        lambda email: "MIT" if "mit.edu" in email else None
    )()
    
    # Mock email sending
    mock_instance.send_verification_email.return_value = asyncio.coroutine(
        lambda *args, **kwargs: True
    )()
    
    # Mock is_academic_email
    mock_instance.is_academic_email.return_value = lambda email: email.endswith(".edu")
    
    return mock_instance


@pytest.fixture
def mock_rate_limiter(mocker):
    """Mock rate limiter for testing."""
    mock = mocker.patch("app.services.security.rate_limiter.RateLimiter")
    mock_instance = mock.return_value
    
    mock_instance.check_rate_limit.return_value = asyncio.coroutine(
        lambda *args, **kwargs: True
    )()
    
    mock_instance.is_rate_limited.return_value = asyncio.coroutine(
        lambda *args, **kwargs: False
    )()
    
    return mock_instance


@pytest.fixture
def mock_lockout_service(mocker):
    """Mock lockout service for testing."""
    mock = mocker.patch("app.services.security.lockout.AccountLockoutService")
    mock_instance = mock.return_value
    
    mock_instance.record_failed_attempt.return_value = asyncio.coroutine(
        lambda *args, **kwargs: None
    )()
    
    mock_instance.is_account_locked.return_value = asyncio.coroutine(
        lambda *args, **kwargs: False
    )()
    
    mock_instance.reset_failed_attempts.return_value = asyncio.coroutine(
        lambda *args, **kwargs: None
    )()
    
    return mock_instance


@pytest.fixture
def api_key_service() -> APIKeyService:
    """Create API key service instance."""
    return APIKeyService()


@pytest_asyncio.fixture
async def test_api_key(
    db_session: AsyncSession,
    test_user: User,
    api_key_service: APIKeyService,
) -> Dict[str, str]:
    """Create test API key."""
    key_data = await api_key_service.create_api_key(
        user_id=test_user.id,
        name="Test API Key",
        roles=["api_user"],
        rate_limit=100,
        expires_in_days=30,
    )
    
    yield {
        "key": key_data["key"],
        "key_id": key_data["key_id"],
        "prefix": key_data["prefix"],
    }
    
    # Cleanup
    await api_key_service.revoke_api_key(key_data["key_id"])


@pytest.fixture
def role_permissions() -> Dict[str, List[str]]:
    """Get role permissions mapping."""
    return {
        "user": [
            "create:presentation", "read:presentation", 
            "update:presentation", "delete:presentation",
        ],
        "student": [
            "create:presentation", "read:presentation",
            "update:presentation", "delete:presentation",
        ],
        "faculty": [
            "create:presentation", "read:presentation",
            "update:presentation", "delete:presentation",
            "read:department", "manage:collaboration",
        ],
        "admin": [
            "admin:system", "read:analytics", 
            "manage:template", "delete:presentation",
        ],
    }


@pytest.fixture
def mock_settings(mocker):
    """Mock settings for testing."""
    settings = Settings(
        SECRET_KEY="test-secret-key-for-testing-only",
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        GOOGLE_CLIENT_ID="test-google-client-id",
        GOOGLE_CLIENT_SECRET="test-google-client-secret",
        MICROSOFT_CLIENT_ID="test-microsoft-client-id",
        MICROSOFT_CLIENT_SECRET="test-microsoft-client-secret",
        FRONTEND_URL="http://localhost:3000",
        API_V1_PREFIX="/api/v1",
        ENVIRONMENT="test",
    )
    
    mocker.patch("app.core.config.get_settings", return_value=settings)
    return settings


@pytest.fixture
def security_headers() -> Dict[str, str]:
    """Common security headers for testing."""
    return {
        "X-Real-IP": "192.168.1.100",
        "X-Forwarded-For": "192.168.1.100",
        "User-Agent": "Mozilla/5.0 (Test Suite)",
        "X-Request-ID": str(uuid4()),
    }


@pytest_asyncio.fixture
async def multi_role_user(db_session: AsyncSession) -> User:
    """Create user with multiple roles."""
    user_repo = UserRepository(db_session)
    
    user = User(
        email="multirole@university.edu",
        password_hash=get_password_hash("MultiR0le@Pass!"),
        full_name="Multi Role User",
        institution="University",
        role="faculty",  # Primary role
        additional_roles=["researcher", "department_admin"],
        is_active=True,
        is_verified=True,
    )
    
    created_user = await user_repo.create(user)
    yield created_user
    
    # Cleanup
    await user_repo.delete(created_user.id)