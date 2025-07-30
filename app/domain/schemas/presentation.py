"""
Schemas for presentation management.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


class PresentationBase(BaseModel):
    """Base presentation schema."""
    title: str = Field(..., min_length=1, max_length=500)
    subtitle: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    abstract: Optional[str] = None
    presentation_type: Optional[str] = None
    academic_level: Optional[str] = None
    field_of_study: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    duration_minutes: Optional[int] = Field(None, ge=5, le=180)
    language: str = Field(default="en", max_length=10)


class PresentationCreate(PresentationBase):
    """Schema for creating presentation."""
    template_id: Optional[UUID] = None
    conference_name: Optional[str] = None
    conference_date: Optional[datetime] = None
    is_public: bool = False


class PresentationUpdate(BaseModel):
    """Schema for updating presentation."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    subtitle: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    abstract: Optional[str] = None
    presentation_type: Optional[str] = None
    academic_level: Optional[str] = None
    field_of_study: Optional[str] = None
    keywords: Optional[List[str]] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=180)
    conference_name: Optional[str] = None
    conference_date: Optional[datetime] = None
    is_public: Optional[bool] = None
    status: Optional[str] = None


class PresentationResponse(PresentationBase):
    """Schema for presentation response."""
    id: UUID
    owner_id: UUID
    template_id: Optional[UUID] = None
    status: str
    slide_count: int
    view_count: int
    is_public: bool
    share_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SlideBase(BaseModel):
    """Base slide schema."""
    title: Optional[str] = Field(None, max_length=500)
    content: Dict[str, Any] = Field(default_factory=dict)
    layout_type: str = Field(default="content", max_length=50)
    speaker_notes: Optional[str] = None
    section: Optional[str] = Field(None, max_length=200)
    duration_seconds: Optional[int] = Field(None, ge=0)


class SlideCreate(SlideBase):
    """Schema for creating slide."""
    slide_number: Optional[int] = None
    transitions: Dict[str, Any] = Field(default_factory=dict)
    animations: Dict[str, Any] = Field(default_factory=dict)


class SlideUpdate(BaseModel):
    """Schema for updating slide."""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[Dict[str, Any]] = None
    layout_type: Optional[str] = Field(None, max_length=50)
    speaker_notes: Optional[str] = None
    section: Optional[str] = Field(None, max_length=200)
    transitions: Optional[Dict[str, Any]] = None
    animations: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    is_hidden: Optional[bool] = None


class SlideResponse(SlideBase):
    """Schema for slide response."""
    id: UUID
    presentation_id: UUID
    slide_number: int
    contains_equations: bool
    contains_code: bool
    contains_citations: bool
    figure_count: int
    is_hidden: bool
    is_backup: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CollaboratorAdd(BaseModel):
    """Schema for adding collaborator."""
    email: EmailStr
    permission_level: str = Field(default="viewer", pattern="^(viewer|editor|admin)$")
    message: Optional[str] = None


class CollaboratorResponse(BaseModel):
    """Schema for collaborator response."""
    id: UUID
    user_id: UUID
    email: str
    full_name: str
    permission_level: str
    invited_by: str
    accepted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True