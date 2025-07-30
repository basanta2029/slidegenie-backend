"""
Schemas for AI generation services.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """Base generation request schema."""
    input_type: str = Field(..., description="Type of input: text, pdf, abstract")
    content: str = Field(..., description="Input content")
    options: Dict[str, Any] = Field(default_factory=dict)


class SlideContent(BaseModel):
    """Schema for slide content."""
    title: Optional[str] = None
    subtitle: Optional[str] = None
    body: List[Dict[str, Any]] = Field(default_factory=list)
    layout: str = "content"
    speaker_notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """Schema for citation data."""
    key: str
    authors: List[str]
    title: str
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    bibtex_type: str = "article"
    raw_bibtex: Optional[str] = None


class GenerationResponse(BaseModel):
    """Response from generation service."""
    job_id: UUID
    status: str
    presentation_id: Optional[UUID] = None
    slides: List[SlideContent] = Field(default_factory=list)
    references: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GenerationProgress(BaseModel):
    """Generation progress update."""
    job_id: UUID
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    current_step: str
    message: Optional[str] = None
    estimated_completion: Optional[datetime] = None


class GenerationOptions(BaseModel):
    """Options for content generation."""
    slide_count: int = Field(default=15, ge=5, le=100)
    include_references: bool = True
    include_speaker_notes: bool = True
    language: str = "en"
    academic_level: str = "research"  # undergraduate, graduate, research
    presentation_type: str = "conference"  # conference, lecture, defense, seminar
    template_id: Optional[UUID] = None
    citation_style: str = "apa"
    
    class Config:
        json_schema_extra = {
            "example": {
                "slide_count": 15,
                "include_references": True,
                "include_speaker_notes": True,
                "language": "en",
                "academic_level": "research",
                "presentation_type": "conference",
                "citation_style": "ieee"
            }
        }