"""
Export API endpoints for presentation export operations.

Provides REST endpoints for:
- Export job submission and management
- Progress tracking and status updates
- Download link generation
- Export history and analytics
- Template management
"""

import asyncio
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import structlog
from fastapi import (
    APIRouter, 
    BackgroundTasks, 
    Depends, 
    File,
    Form,
    HTTPException, 
    Query,
    Request,
    Response,
    UploadFile,
    status
)
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.domain.schemas.generation import Citation, SlideContent
from app.domain.schemas.user import UserRead
from app.services.export.export_coordinator import (
    ExportCoordinator,
    ExportConfig,
    ExportFormat,
    ExportPriority,
    ExportQuality,
    ExportStatus,
    create_export_coordinator
)

logger = get_logger(__name__)
router = APIRouter(prefix="/export", tags=["export"])

# Global export coordinator instance
_export_coordinator: Optional[ExportCoordinator] = None


async def get_export_coordinator() -> ExportCoordinator:
    """Get or create export coordinator instance."""
    global _export_coordinator
    if _export_coordinator is None:
        settings = get_settings()
        max_concurrent = getattr(settings, 'MAX_CONCURRENT_EXPORTS', 5)
        _export_coordinator = create_export_coordinator(max_concurrent)
    return _export_coordinator


# Request/Response Models

class ExportRequest(BaseModel):
    """Export request model."""
    slides: List[SlideContent] = Field(..., min_items=1, max_items=100)
    format: str = Field(..., description="Export format (pptx, beamer, pdf, google_slides)")
    template_name: str = Field(default="default", description="Template name")
    quality: str = Field(default="standard", description="Export quality (draft, standard, high, premium)")
    priority: str = Field(default="normal", description="Job priority (low, normal, high, urgent)")
    citations: Optional[List[Citation]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    custom_settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    branding: Optional[Dict[str, Any]] = Field(default_factory=dict)
    fallback_formats: Optional[List[str]] = Field(default_factory=list)
    callback_url: Optional[str] = Field(default=None, description="Webhook URL for completion notification")
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = [fmt.name.lower() for fmt in ExportFormat]
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid format. Must be one of: {valid_formats}")
        return v.lower()
    
    @validator('quality')
    def validate_quality(cls, v):
        valid_qualities = [q.value for q in ExportQuality]
        if v.lower() not in valid_qualities:
            raise ValueError(f"Invalid quality. Must be one of: {valid_qualities}")
        return v.lower()
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = [p.name.lower() for p in ExportPriority]
        if v.lower() not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {valid_priorities}")
        return v.lower()


class ExportResponse(BaseModel):
    """Export job submission response."""
    job_id: str
    status: str
    message: str
    estimated_completion_time: Optional[datetime] = None
    download_url: Optional[str] = None
    progress_url: str


class ProgressResponse(BaseModel):
    """Export progress response."""
    job_id: str
    status: str
    progress_percent: float
    current_step: str
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class ExportResultResponse(BaseModel):
    """Export result response."""
    job_id: str
    status: str
    format: str
    download_url: Optional[str] = None
    file_url: Optional[str] = None
    sharing_urls: Dict[str, str] = Field(default_factory=dict)
    file_size: Optional[int] = None
    download_expires: Optional[datetime] = None
    validation_results: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TemplateOption(BaseModel):
    """Template option model."""
    name: str
    display_name: str
    description: Optional[str] = None
    preview_url: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)


class FormatInfo(BaseModel):
    """Format information model."""
    format: str
    name: str
    extension: str
    mime_type: str
    templates: List[str]
    description: Optional[str] = None


class ExportHistoryItem(BaseModel):
    """Export history item."""
    job_id: str
    format: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    file_size: Optional[int] = None
    slide_count: int
    template_name: str


class ExportStats(BaseModel):
    """Export statistics."""
    total_exports: int
    successful_exports: int
    failed_exports: int
    exports_by_format: Dict[str, int]
    average_processing_times: Dict[str, float]
    active_jobs: int
    uptime_seconds: float


# API Endpoints

@router.post("/jobs", response_model=ExportResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_export_job(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> ExportResponse:
    """
    Submit a new export job.
    
    Creates a new export job and starts processing asynchronously.
    Returns job ID and progress tracking information.
    """
    try:
        # Parse format enum
        format_enum = ExportFormat[request.format.upper()]
        
        # Parse quality and priority enums
        quality_enum = ExportQuality(request.quality)
        priority_enum = ExportPriority[request.priority.upper()]
        
        # Parse fallback formats
        fallback_formats = []
        for fmt in request.fallback_formats:
            try:
                fallback_formats.append(ExportFormat[fmt.upper()])
            except KeyError:
                logger.warning(f"Invalid fallback format: {fmt}")
        
        # Create export config
        config = ExportConfig(
            format=format_enum,
            template_name=request.template_name,
            quality=quality_enum,
            priority=priority_enum,
            custom_settings=request.custom_settings,
            branding=request.branding,
            fallback_formats=fallback_formats
        )
        
        # Submit job
        job_id = await coordinator.submit_export_job(
            slides=request.slides,
            config=config,
            citations=request.citations,
            metadata=request.metadata,
            user_id=str(current_user.id),
            callback_url=request.callback_url
        )
        
        # Estimate completion time
        estimated_time = coordinator._estimate_completion_time(
            type('Job', (), {
                'slides': request.slides,
                'config': config
            })()
        )
        estimated_completion = datetime.now() + timedelta(seconds=estimated_time)
        
        logger.info(f"Export job {job_id} submitted by user {current_user.id}")
        
        return ExportResponse(
            job_id=job_id,
            status="accepted",
            message="Export job submitted successfully",
            estimated_completion_time=estimated_completion,
            progress_url=f"/api/v1/export/jobs/{job_id}/progress"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to submit export job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit export job"
        )


@router.get("/jobs/{job_id}/progress", response_model=ProgressResponse)
async def get_job_progress(
    job_id: str,
    current_user: UserRead = Depends(get_current_user),
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> ProgressResponse:
    """
    Get progress for a specific export job.
    
    Returns current status, progress percentage, and estimated completion time.
    """
    try:
        progress = await coordinator.get_job_progress(job_id)
        
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return ProgressResponse(
            job_id=progress.job_id,
            status=progress.status.value,
            progress_percent=progress.progress_percent,
            current_step=progress.current_step,
            start_time=progress.start_time,
            estimated_completion=progress.estimated_completion,
            error_message=progress.error_message,
            warnings=progress.warnings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job progress"
        )


@router.get("/jobs/{job_id}/result", response_model=ExportResultResponse)
async def get_job_result(
    job_id: str,
    current_user: UserRead = Depends(get_current_user),
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> ExportResultResponse:
    """
    Get result for a completed export job.
    
    Returns download URLs, file information, and validation results.
    """
    try:
        result = await coordinator.get_job_result(job_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or not completed"
            )
        
        if result.status != ExportStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job not completed. Status: {result.status.value}"
            )
        
        # Generate download URL if file exists
        download_url = None
        if result.file_path or result.buffer:
            download_url = f"/api/v1/export/jobs/{job_id}/download"
        
        return ExportResultResponse(
            job_id=result.job_id,
            status=result.status.value,
            format=result.format.name.lower(),
            download_url=download_url,
            file_url=result.file_url,
            sharing_urls=result.sharing_urls,
            file_size=result.file_size,
            download_expires=result.download_expires,
            validation_results=result.validation_results,
            metadata=result.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job result"
        )


@router.get("/jobs/{job_id}/download")
async def download_export_file(
    job_id: str,
    current_user: UserRead = Depends(get_current_user),
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
):
    """
    Download the exported file.
    
    Returns the file as a streaming response with appropriate headers.
    """
    try:
        result = await coordinator.get_job_result(job_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        if result.status != ExportStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job not completed"
            )
        
        # Check if download has expired
        if result.download_expires and datetime.now() > result.download_expires:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Download link has expired"
            )
        
        # Determine file info
        format_info = result.format.value
        filename = f"presentation_{job_id}{format_info['extension']}"
        
        if result.file_path:
            # Return file response
            return FileResponse(
                path=result.file_path,
                filename=filename,
                media_type=format_info['mime_type']
            )
        elif result.buffer:
            # Return streaming response from buffer
            result.buffer.seek(0)
            return StreamingResponse(
                io.BytesIO(result.buffer.read()),
                media_type=format_info['mime_type'],
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not available"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download export file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download export file"
        )


@router.delete("/jobs/{job_id}")
async def cancel_export_job(
    job_id: str,
    current_user: UserRead = Depends(get_current_user),
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> Dict[str, Any]:
    """
    Cancel an export job if possible.
    
    Can only cancel jobs that are pending or in preparation phase.
    """
    try:
        success = await coordinator.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job cannot be cancelled (not found or already processing)"
            )
        
        logger.info(f"Export job {job_id} cancelled by user {current_user.id}")
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )


@router.get("/formats", response_model=List[FormatInfo])
async def get_supported_formats(
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> List[FormatInfo]:
    """
    Get list of supported export formats with metadata.
    
    Returns format information including available templates.
    """
    try:
        formats = coordinator.get_supported_formats()
        
        format_descriptions = {
            "PPTX": "Microsoft PowerPoint presentation",
            "BEAMER": "LaTeX Beamer presentation",
            "PDF": "Portable Document Format",
            "GOOGLE_SLIDES": "Google Slides presentation"
        }
        
        return [
            FormatInfo(
                format=fmt["format"].lower(),
                name=fmt["name"],
                extension=fmt["extension"],
                mime_type=fmt["mime_type"],
                templates=fmt["templates"],
                description=format_descriptions.get(fmt["format"])
            )
            for fmt in formats
        ]
        
    except Exception as e:
        logger.error(f"Failed to get supported formats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get supported formats"
        )


@router.get("/formats/{format}/templates", response_model=List[TemplateOption])
async def get_format_templates(
    format: str,
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> List[TemplateOption]:
    """
    Get available templates for a specific format.
    
    Returns template information including settings and preview URLs.
    """
    try:
        # Parse format enum
        try:
            format_enum = ExportFormat[format.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format: {format}"
            )
        
        templates = coordinator.get_template_options(format_enum)
        
        # Convert to response format
        template_list = []
        for template_name, settings in templates.items():
            template_list.append(TemplateOption(
                name=template_name,
                display_name=template_name.title(),
                description=f"{format.upper()} template: {template_name}",
                settings=settings
            ))
        
        return template_list
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get format templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get format templates"
        )


@router.get("/jobs", response_model=List[ExportHistoryItem])
async def get_export_history(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    format_filter: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None),
    current_user: UserRead = Depends(get_current_user),
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> List[ExportHistoryItem]:
    """
    Get export history for the current user.
    
    Returns paginated list of export jobs with filtering options.
    """
    try:
        # This would typically query a database
        # For now, return from in-memory jobs (simplified)
        
        all_jobs = []
        for job_id, job in coordinator._jobs.items():
            # Filter by user (in a real implementation, this would be stored)
            if hasattr(job, 'user_id') and job.user_id != str(current_user.id):
                continue
            
            # Apply filters
            if format_filter and job.config.format.name.lower() != format_filter.lower():
                continue
            
            if status_filter and job.progress.status.value != status_filter.lower():
                continue
            
            # Get completion time
            completed_at = None
            if job.progress.status in [ExportStatus.COMPLETED, ExportStatus.FAILED]:
                # In a real implementation, this would be stored
                completed_at = datetime.now()  # Placeholder
            
            all_jobs.append(ExportHistoryItem(
                job_id=job.job_id,
                format=job.config.format.name.lower(),
                status=job.progress.status.value,
                created_at=job.created_at,
                completed_at=completed_at,
                file_size=getattr(getattr(job, 'result', None), 'file_size', None),
                slide_count=len(job.slides),
                template_name=job.config.template_name
            ))
        
        # Sort by creation time (newest first)
        all_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        return all_jobs[offset:offset + limit]
        
    except Exception as e:
        logger.error(f"Failed to get export history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export history"
        )


@router.get("/stats", response_model=ExportStats)
async def get_export_statistics(
    current_user: UserRead = Depends(get_current_user),
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> ExportStats:
    """
    Get export service statistics.
    
    Returns overall statistics about export operations and system health.
    """
    try:
        stats = coordinator.get_statistics()
        
        # Convert format keys to lowercase
        exports_by_format = {
            fmt.name.lower(): count 
            for fmt, count in stats["exports_by_format"].items()
        }
        
        # Extract average processing times
        avg_times = {}
        for key, value in stats.items():
            if key.startswith("avg_time_"):
                format_name = key.replace("avg_time_", "")
                avg_times[format_name] = value
        
        return ExportStats(
            total_exports=stats["total_exports"],
            successful_exports=stats["successful_exports"],
            failed_exports=stats["failed_exports"],
            exports_by_format=exports_by_format,
            average_processing_times=avg_times,
            active_jobs=stats["resources"]["active_jobs"],
            uptime_seconds=stats["uptime_seconds"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get export statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export statistics"
        )


@router.post("/cleanup")
async def cleanup_expired_jobs(
    max_age_hours: int = Query(default=24, ge=1, le=168),  # 1 hour to 1 week
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> Dict[str, Any]:
    """
    Clean up expired export jobs.
    
    Removes old completed jobs and their associated files.
    Requires admin privileges (in a real implementation).
    """
    try:
        # In a real implementation, check admin privileges
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Run cleanup in background
        background_tasks.add_task(coordinator.cleanup_expired_jobs, max_age_hours)
        
        return {
            "message": f"Cleanup started for jobs older than {max_age_hours} hours",
            "status": "accepted"
        }
        
    except Exception as e:
        logger.error(f"Failed to start cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start cleanup"
        )


@router.get("/health")
async def export_health_check(
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
) -> Dict[str, Any]:
    """
    Perform health check on export service.
    
    Returns service status and availability of export generators.
    """
    try:
        health = await coordinator.health_check()
        
        # Convert datetime to string for JSON serialization
        health["timestamp"] = health["timestamp"].isoformat()
        
        return health
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


# WebSocket endpoint for real-time progress updates

@router.websocket("/jobs/{job_id}/progress/ws")
async def websocket_progress_updates(
    websocket,
    job_id: str,
    coordinator: ExportCoordinator = Depends(get_export_coordinator)
):
    """
    WebSocket endpoint for real-time progress updates.
    
    Streams progress updates for a specific export job.
    """
    await websocket.accept()
    
    try:
        # Add progress callback
        async def progress_callback(progress):
            try:
                await websocket.send_json({
                    "job_id": progress.job_id,
                    "status": progress.status.value,
                    "progress_percent": progress.progress_percent,
                    "current_step": progress.current_step,
                    "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
                    "error_message": progress.error_message,
                    "warnings": progress.warnings
                })
            except Exception as e:
                logger.error(f"Failed to send progress update: {e}")
        
        coordinator.add_progress_callback(job_id, progress_callback)
        
        # Keep connection alive
        while True:
            try:
                # Send ping every 30 seconds
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping", "timestamp": datetime.now().isoformat()})
            except Exception:
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        await websocket.close()