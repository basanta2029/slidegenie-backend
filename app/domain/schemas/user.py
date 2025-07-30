"""
User schemas.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None


class UserInDB(UserBase):
    """User in database schema."""
    id: UUID
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class User(UserInDB):
    """User response schema."""
    pass


class UserWithStats(User):
    """User with statistics schema."""
    presentations_count: int = 0
    storage_used_mb: float = 0.0
    last_login: Optional[datetime] = None