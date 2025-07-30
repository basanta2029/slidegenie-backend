"""
Authentication schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class TokenRefresh(BaseModel):
    """Token refresh request schema."""
    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    sub: str  # User ID
    email: str
    roles: List[str]
    institution: Optional[str] = None
    type: str = "access"  # 'access' or 'refresh'
    session_id: str
    iat: int
    exp: int
    nbf: Optional[int] = None
    jti: Optional[str] = None  # JWT ID for blacklisting


class UserRegistration(BaseModel):
    """User registration data."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    institution: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field("researcher", pattern="^(researcher|student|professor|admin)$")


class UserLogin(BaseModel):
    """User login credentials."""
    email: EmailStr
    password: str
    remember_me: bool = False


class PasswordReset(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8)


class EmailVerification(BaseModel):
    """Email verification."""
    token: str


class UserProfile(BaseModel):
    """User profile data."""
    id: UUID
    email: str
    first_name: str
    last_name: str
    institution: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserRead(BaseModel):
    """User read schema for authorization."""
    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool = True
    roles: List[str] = Field(default_factory=lambda: ["user"])
    institution_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    user_id: UUID
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response."""
    user: UserProfile
    tokens: TokenPair
    session: SessionInfo