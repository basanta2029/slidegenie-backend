"""
Test authentication endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.database.models import User
from app.repositories.user import UserRepository

settings = get_settings()


@pytest.mark.asyncio
async def test_register_academic_user(client: AsyncClient, db: AsyncSession):
    """Test user registration with academic email."""
    user_data = {
        "email": "john.doe@harvard.edu",
        "password": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "institution": "Harvard University",
        "role": "researcher"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["user"]["email"] == user_data["email"]
    assert data["user"]["first_name"] == user_data["first_name"]
    assert data["user"]["last_name"] == user_data["last_name"]
    assert data["user"]["institution"] == "Harvard University"  # Should be validated
    assert data["user"]["is_verified"] is False  # Requires email verification
    assert "tokens" in data
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]


@pytest.mark.asyncio
async def test_register_non_academic_user(client: AsyncClient, db: AsyncSession):
    """Test user registration with non-academic email."""
    user_data = {
        "email": "john.doe@gmail.com",
        "password": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "role": "researcher"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["user"]["email"] == user_data["email"]
    assert data["user"]["institution"] is None  # No institution for non-academic
    assert data["user"]["is_verified"] is False


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db: AsyncSession):
    """Test registration with already registered email."""
    user_data = {
        "email": "existing@harvard.edu",
        "password": "SecurePass123!",
        "first_name": "Existing",
        "last_name": "User",
        "role": "researcher"
    }
    
    # Register first time
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    
    # Try to register again
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient, db: AsyncSession):
    """Test registration with weak password."""
    user_data = {
        "email": "weak@harvard.edu",
        "password": "weak",  # Too short and simple
        "first_name": "Weak",
        "last_name": "Password",
        "role": "researcher"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert "Password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db: AsyncSession):
    """Test successful login."""
    # First register a user
    user_data = {
        "email": "login@mit.edu",
        "password": "SecurePass123!",
        "first_name": "Login",
        "last_name": "Test",
        "role": "researcher"
    }
    
    await client.post("/api/v1/auth/register", json=user_data)
    
    # Mark as verified for testing
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(user_data["email"])
    user.is_verified = True
    await user_repo.update(user)
    await db.commit()
    
    # Login
    login_data = {
        "email": user_data["email"],
        "password": user_data["password"],
        "remember_me": False
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["user"]["email"] == user_data["email"]
    assert "tokens" in data
    assert data["user"]["is_verified"] is True


@pytest.mark.asyncio
async def test_login_unverified_academic(client: AsyncClient, db: AsyncSession):
    """Test login with unverified academic email."""
    # Register academic user
    user_data = {
        "email": "unverified@stanford.edu",
        "password": "SecurePass123!",
        "first_name": "Unverified",
        "last_name": "User",
        "role": "researcher"
    }
    
    await client.post("/api/v1/auth/register", json=user_data)
    
    # Try to login without verification
    login_data = {
        "email": user_data["email"],
        "password": user_data["password"],
        "remember_me": False
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 403
    assert "verify" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, db: AsyncSession):
    """Test login with invalid credentials."""
    login_data = {
        "email": "nonexistent@mit.edu",
        "password": "WrongPassword123!",
        "remember_me": False
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, db: AsyncSession):
    """Test token refresh."""
    # Register and login
    user_data = {
        "email": "refresh@yale.edu",
        "password": "SecurePass123!",
        "first_name": "Refresh",
        "last_name": "Test",
        "role": "researcher"
    }
    
    register_response = await client.post("/api/v1/auth/register", json=user_data)
    tokens = register_response.json()["tokens"]
    
    # Refresh token
    refresh_data = {
        "refresh_token": tokens["refresh_token"]
    }
    
    response = await client.post("/api/v1/auth/refresh", json=refresh_data)
    assert response.status_code == 200
    
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["access_token"] != tokens["access_token"]


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, db: AsyncSession):
    """Test logout."""
    # Register and get tokens
    user_data = {
        "email": "logout@princeton.edu",
        "password": "SecurePass123!",
        "first_name": "Logout",
        "last_name": "Test",
        "role": "researcher"
    }
    
    register_response = await client.post("/api/v1/auth/register", json=user_data)
    tokens = register_response.json()["tokens"]
    
    # Logout
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_email_verification(client: AsyncClient, db: AsyncSession):
    """Test email verification."""
    # Register user
    user_data = {
        "email": "verify@columbia.edu",
        "password": "SecurePass123!",
        "first_name": "Verify",
        "last_name": "Test",
        "role": "researcher"
    }
    
    await client.post("/api/v1/auth/register", json=user_data)
    
    # Get verification token from database
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(user_data["email"])
    verification_token = user.verification_token
    
    # Verify email
    verification_data = {
        "token": verification_token
    }
    
    response = await client.post("/api/v1/auth/verify-email", json=verification_data)
    assert response.status_code == 200
    assert "verified successfully" in response.json()["message"]
    
    # Check user is verified
    await db.refresh(user)
    assert user.is_verified is True
    assert user.verification_token is None


@pytest.mark.asyncio
async def test_resend_verification(client: AsyncClient, db: AsyncSession):
    """Test resend verification email."""
    # Register user
    user_data = {
        "email": "resend@cornell.edu",
        "password": "SecurePass123!",
        "first_name": "Resend",
        "last_name": "Test",
        "role": "researcher"
    }
    
    await client.post("/api/v1/auth/register", json=user_data)
    
    # Resend verification
    response = await client.post(
        "/api/v1/auth/resend-verification",
        params={"email": user_data["email"]}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_request(client: AsyncClient, db: AsyncSession):
    """Test password reset request."""
    # Register user
    user_data = {
        "email": "reset@upenn.edu",
        "password": "OldPassword123!",
        "first_name": "Reset",
        "last_name": "Test",
        "role": "researcher"
    }
    
    await client.post("/api/v1/auth/register", json=user_data)
    
    # Request password reset
    reset_request = {
        "email": user_data["email"]
    }
    
    response = await client.post("/api/v1/auth/forgot-password", json=reset_request)
    assert response.status_code == 200
    assert "reset link has been sent" in response.json()["message"]


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, db: AsyncSession):
    """Test get current user endpoint."""
    # Register user
    user_data = {
        "email": "current@caltech.edu",
        "password": "SecurePass123!",
        "first_name": "Current",
        "last_name": "User",
        "role": "professor"
    }
    
    register_response = await client.post("/api/v1/auth/register", json=user_data)
    access_token = register_response.json()["tokens"]["access_token"]
    
    # Get current user
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    
    user_info = response.json()
    assert user_info["email"] == user_data["email"]
    assert user_info["full_name"] == f"{user_data['first_name']} {user_data['last_name']}"
    assert user_info["role"] == user_data["role"]