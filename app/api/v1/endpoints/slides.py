"""API endpoints for slide generation service."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, File, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import json
import io
from datetime import datetime

from app.core.dependencies import get_current_user
from app.domain.schemas.user import User
from app.services.slides import SlideGenerationService, SlideGenerationConfig, OutputFormat
from app.services.slides.config import LayoutStyle, QualityLevel
from app.core.security import RateLimiter
from app.services.auth.authorization.decorators import require_permission


router = APIRouter()

# Initialize service (in production, use dependency injection)
slide_service = SlideGenerationService()

# Rate limiter for generation endpoints
generation_limiter = RateLimiter(max_attempts=10, window_seconds=3600)  # 10 per hour


# Request/Response models
class GenerationRequest(BaseModel):
    """Request model for slide generation."""
    content: str = Field(..., description="Input content for presentation")
    output_format: Optional[OutputFormat] = Field(OutputFormat.PPTX, description="Output format")
    title: Optional[str] = Field(None, description="Presentation title")
    author: Optional[str] = Field(None, description="Presentation author")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional generation options")
    preset: Optional[str] = Field(None, description="Use a preset configuration")


class GenerationOptions(BaseModel):
    """Detailed generation options."""
    layout_style: Optional[LayoutStyle] = Field(None, description="Layout style")
    quality_level: Optional[QualityLevel] = Field(None, description="Quality level")
    max_slides: Optional[int] = Field(None, ge=1, le=100, description="Maximum number of slides")
    enable_animations: Optional[bool] = Field(None, description="Enable slide animations")
    enable_speaker_notes: Optional[bool] = Field(None, description="Generate speaker notes")
    color_scheme: Optional[Dict[str, str]] = Field(None, description="Custom color scheme")
    font_family: Optional[str] = Field(None, description="Font family")
    enable_citations: Optional[bool] = Field(None, description="Enable automatic citations")


class PreviewRequest(BaseModel):
    """Request model for presentation preview."""
    content: str = Field(..., description="Input content")
    max_slides: int = Field(5, ge=1, le=10, description="Number of slides to preview")


class ValidationRequest(BaseModel):
    """Request model for content validation."""
    content: str = Field(..., description="Content to validate")


class GenerationResponse(BaseModel):
    """Response model for generation requests."""
    job_id: str
    status: str
    message: str
    estimated_time: Optional[float] = None


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    progress: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class FormatInfo(BaseModel):
    """Information about a supported format."""
    format: str
    name: str
    description: str
    file_extension: str
    supports_animations: bool
    supports_speaker_notes: bool


class StyleInfo(BaseModel):
    """Information about a presentation style."""
    style: str
    name: str
    description: str
    preview_url: Optional[str] = None


# Endpoints

@router.post("/generate", response_model=GenerationResponse)
@require_permission("slides:generate")
async def generate_presentation(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a presentation from input content.
    
    This endpoint initiates an asynchronous generation process and returns
    a job ID for tracking progress.
    """
    # Rate limiting
    if not generation_limiter.check_limit(f"generate:{current_user.id}"):
        raise HTTPException(status_code=429, detail="Generation rate limit exceeded")
    
    # Prepare content
    content_data = {
        "text": request.content,
        "title": request.title or "Untitled Presentation",
        "author": request.author or current_user.full_name,
        "user_id": current_user.id
    }
    
    # Prepare options
    options = request.options or {}
    if request.output_format:
        options["generator"] = {"format": request.output_format}
    
    # Start generation in background
    async def generate_task():
        try:
            if request.preset:
                result = await slide_service.generate_from_preset(
                    request.preset,
                    content_data,
                    options
                )
            else:
                result = await slide_service.generate_presentation(
                    content_data,
                    request.output_format,
                    options
                )
            # Store result for download (implement storage logic)
        except Exception as e:
            # Log error
            pass
    
    background_tasks.add_task(generate_task)
    
    # Return job info
    job_id = "job_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    
    return GenerationResponse(
        job_id=job_id,
        status="processing",
        message="Presentation generation started",
        estimated_time=30.0  # seconds
    )


@router.post("/generate-advanced", response_model=GenerationResponse)
@require_permission("slides:generate")
async def generate_presentation_advanced(
    request: GenerationOptions,
    content: UploadFile = File(..., description="Content file (txt, md, docx)"),
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a presentation with advanced options and file upload.
    """
    # Rate limiting
    if not generation_limiter.check_limit(f"generate:{current_user.id}"):
        raise HTTPException(status_code=429, detail="Generation rate limit exceeded")
    
    # Read and validate file
    if content.content_type not in ["text/plain", "text/markdown", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    file_content = await content.read()
    
    # Convert options to config format
    config_overrides = {}
    
    if request.layout_style:
        config_overrides["layout"] = {"style": request.layout_style}
    
    if request.quality_level:
        config_overrides["quality"] = {"quality_level": request.quality_level}
    
    if request.max_slides is not None:
        config_overrides["generator"] = {"max_slides": request.max_slides}
    
    # Similar for other options...
    
    # Start generation
    async def generate_task():
        result = await slide_service.generate_presentation(
            file_content.decode('utf-8'),
            options=config_overrides
        )
    
    background_tasks.add_task(generate_task)
    
    job_id = "job_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    
    return GenerationResponse(
        job_id=job_id,
        status="processing",
        message="Advanced presentation generation started",
        estimated_time=45.0
    )


@router.post("/preview")
@require_permission("slides:preview")
async def preview_presentation(
    request: PreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a preview of the presentation.
    
    Returns a simplified version with limited slides for quick review.
    """
    try:
        preview_content = await slide_service.preview_presentation(
            request.content,
            request.max_slides
        )
        
        return {
            "title": preview_content.title,
            "subtitle": preview_content.subtitle,
            "slides_count": len(preview_content.slides),
            "slides": [
                {
                    "title": slide.title,
                    "content": slide.content[:200] + "..." if slide.content and len(slide.content) > 200 else slide.content,
                    "layout_type": slide.layout_type
                }
                for slide in preview_content.slides
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@router.post("/validate")
@require_permission("slides:validate")
async def validate_content(
    request: ValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validate content before generation.
    
    Checks for common issues and provides suggestions.
    """
    try:
        validation_result = await slide_service.validate_content(request.content)
        
        return {
            "is_valid": validation_result.is_valid,
            "errors": validation_result.errors or [],
            "warnings": validation_result.warnings or [],
            "suggestions": validation_result.suggestions or []
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/job/{job_id}", response_model=JobStatusResponse)
@require_permission("slides:status")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a generation job."""
    job_status = slide_service.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify user owns the job (implement this check)
    
    return JobStatusResponse(**job_status)


@router.delete("/job/{job_id}")
@require_permission("slides:cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel an active generation job."""
    success = await slide_service.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already completed")
    
    return {"message": "Job cancelled successfully"}


@router.get("/download/{job_id}")
@require_permission("slides:download")
async def download_presentation(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download a generated presentation."""
    # Implement file retrieval logic
    # This is a placeholder
    
    # Get file from storage
    file_path = f"/tmp/{job_id}.pptx"  # Placeholder
    
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename=presentation_{job_id}.pptx"
            }
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Presentation not found")


@router.get("/formats", response_model=List[FormatInfo])
async def get_supported_formats():
    """Get list of supported output formats."""
    formats = []
    
    for format_enum in OutputFormat:
        format_info = FormatInfo(
            format=format_enum.value,
            name=format_enum.value.upper(),
            description=f"Export as {format_enum.value.upper()}",
            file_extension=f".{format_enum.value}",
            supports_animations=format_enum in [OutputFormat.PPTX, OutputFormat.GOOGLE_SLIDES],
            supports_speaker_notes=True
        )
        formats.append(format_info)
    
    return formats


@router.get("/styles", response_model=List[StyleInfo])
async def get_available_styles():
    """Get available presentation styles."""
    styles = []
    
    for style_enum in LayoutStyle:
        style_info = StyleInfo(
            style=style_enum.value,
            name=style_enum.value.title(),
            description=f"{style_enum.value.title()} presentation style",
            preview_url=f"/static/previews/{style_enum.value}.png"
        )
        styles.append(style_info)
    
    return styles


@router.get("/presets")
async def get_presets():
    """Get available configuration presets."""
    from app.services.slides.config import PRESETS
    
    return {
        name: {
            "name": name.replace("_", " ").title(),
            "description": f"Optimized for {name.replace('_', ' ')}",
            "config": preset.to_dict()
        }
        for name, preset in PRESETS.items()
    }


@router.post("/config/save")
@require_permission("slides:config")
async def save_configuration(
    name: str = Query(..., description="Configuration name"),
    config: SlideGenerationConfig = None,
    current_user: User = Depends(get_current_user)
):
    """Save a custom configuration."""
    # Implement configuration storage
    # This is a placeholder
    
    return {
        "message": "Configuration saved successfully",
        "name": name
    }


@router.get("/config/{name}")
@require_permission("slides:config")
async def load_configuration(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """Load a saved configuration."""
    # Implement configuration retrieval
    # This is a placeholder
    
    return {
        "name": name,
        "config": SlideGenerationConfig().to_dict()
    }