"""
Comprehensive presentation management endpoints for SlideGenie.

This module provides all presentation-related API endpoints including:
- Presentation generation from text/abstract
- Presentation generation from uploaded documents
- CRUD operations for presentations and slides
- Progress tracking for generation jobs
- Authentication and authorization
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
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
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_current_user_optional
from app.domain.schemas.presentation import (
    PresentationCreate,
    PresentationResponse,
    PresentationUpdate,
    SlideCreate,
    SlideResponse,
    SlideUpdate,
)
from app.domain.schemas.generation import (
    GenerationOptions,
    GenerationProgress,
    GenerationRequest,
    GenerationResponse,
)
from app.domain.schemas.document_processing import (
    ProcessingRequest,
    ProcessingStatus,
    DocumentType,
)
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import User, Presentation, Slide
from app.repositories.presentation import PresentationRepository
from app.repositories.slide import SlideRepository
from app.repositories.generation_job import GenerationJobRepository
from app.services.ai.generation_pipeline import GenerationPipeline
from app.services.document_processing.async_processor import AsyncDocumentProcessor
from app.services.document_processing.storage.s3_manager import S3StorageManager
from app.services.auth.authorization.decorators import require_permissions

logger = structlog.get_logger(__name__)

router = APIRouter()


# Request/Response Models
class PresentationGenerateRequest(GenerationRequest):
    """Request model for text-based presentation generation."""
    title: str
    content: str
    options: Optional[GenerationOptions] = None


class FileGenerationRequest(BaseModel):
    """Request model for file-based presentation generation."""
    title: str
    options: Optional[GenerationOptions] = None


class PresentationListResponse(BaseModel):
    """Response model for presentation list."""
    presentations: List[PresentationResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class SlideAddRequest(SlideCreate):
    """Request model for adding a new slide."""
    pass


# Presentation Generation Endpoints

@router.post(
    "/generate",
    response_model=GenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate presentation from text/abstract",
    description="Generate a complete presentation from provided text content or abstract"
)
async def generate_presentation_from_text(
    request: PresentationGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    """
    Generate a presentation from text content or abstract.
    
    This endpoint creates a new presentation by processing the provided text content
    using AI-powered generation pipeline. The generation happens asynchronously
    and progress can be tracked using the returned job_id.
    
    - **title**: Presentation title
    - **content**: Text content or abstract to generate presentation from
    - **options**: Generation options (slide count, style, etc.)
    
    Returns a job_id that can be used to track generation progress.
    """
    try:
        logger.info(
            "presentation_generation_started", 
            user_id=current_user.id,
            title=request.title,
            content_length=len(request.content)
        )
        
        # Validate user quota
        presentation_repo = PresentationRepository(db)
        user_presentations = await presentation_repo.get_user_presentations(
            current_user.id, limit=1
        )
        
        # Check monthly presentation limit based on subscription
        monthly_limit = {
            "free": 5,
            "academic": 50,
            "professional": 200,
            "institutional": 1000
        }.get(current_user.subscription_tier, 5)
        
        if current_user.monthly_presentations_used >= monthly_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly presentation limit reached ({monthly_limit}). Please upgrade your subscription."
            )
        
        # Create generation job record
        job_repo = GenerationJobRepository(db)
        job_id = uuid.uuid4()
        
        job_data = {
            "id": job_id,
            "user_id": current_user.id,
            "job_type": "full_generation",
            "input_type": "text",
            "input_data": {
                "title": request.title,
                "content": request.content,
                "options": request.options.dict() if request.options else {}
            },
            "status": "pending",
            "priority": 5
        }
        
        await job_repo.create(job_data)
        
        # Start generation in background
        background_tasks.add_task(
            _process_text_generation,
            job_id,
            request.title,
            request.content,
            request.options or GenerationOptions(),
            current_user.id,
            db
        )
        
        # Update user usage
        current_user.monthly_presentations_used += 1
        await db.commit()
        
        return GenerationResponse(
            job_id=job_id,
            status="pending",
            metadata={
                "estimated_duration_minutes": 3,
                "total_steps": 6
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("presentation_generation_error", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start presentation generation"
        )


@router.post(
    "/generate-from-file",
    response_model=GenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate presentation from uploaded document",
    description="Generate a presentation from an uploaded document (PDF, DOCX, etc.)"
)
async def generate_presentation_from_file(
    title: str = Form(..., description="Presentation title"),
    file: UploadFile = File(..., description="Document file to process"),
    options: Optional[str] = Form(None, description="Generation options as JSON string"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    """
    Generate a presentation from an uploaded document.
    
    Supports various document formats:
    - PDF documents
    - Microsoft Word documents (.docx)
    - LaTeX documents (.tex)
    - Plain text files (.txt)
    
    The document is first processed to extract text content, then used to generate
    the presentation using the AI pipeline.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Determine document type
        file_extension = file.filename.lower().split('.')[-1]
        document_type_mapping = {
            'pdf': DocumentType.PDF,
            'docx': DocumentType.DOCX,
            'doc': DocumentType.DOCX,
            'tex': DocumentType.LATEX,
            'txt': DocumentType.TEXT,
        }
        
        document_type = document_type_mapping.get(file_extension)
        if not document_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: {file_extension}"
            )
        
        # Validate file size (100MB limit)
        max_size = 100 * 1024 * 1024  # 100MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 100MB limit"
            )
        
        # Parse options
        generation_options = GenerationOptions()
        if options:
            try:
                options_dict = json.loads(options)
                generation_options = GenerationOptions(**options_dict)
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid options JSON: {str(e)}"
                )
        
        # Check user quota
        monthly_limit = {
            "free": 5,
            "academic": 50,
            "professional": 200,
            "institutional": 1000
        }.get(current_user.subscription_tier, 5)
        
        if current_user.monthly_presentations_used >= monthly_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly presentation limit reached ({monthly_limit})"
            )
        
        # Store file temporarily
        storage_manager = S3StorageManager()
        file_key = f"uploads/{current_user.id}/{uuid.uuid4()}/{file.filename}"
        
        await storage_manager.upload_file(
            file_content,
            file_key,
            content_type=file.content_type or "application/octet-stream"
        )
        
        # Create generation job
        job_repo = GenerationJobRepository(db)
        job_id = uuid.uuid4()
        
        job_data = {
            "id": job_id,
            "user_id": current_user.id,
            "job_type": "full_generation",
            "input_type": "file",
            "input_data": {
                "title": title,
                "file_key": file_key,
                "filename": file.filename,
                "document_type": document_type.value,
                "file_size": len(file_content),
                "options": generation_options.dict()
            },
            "status": "pending",
            "priority": 5
        }
        
        await job_repo.create(job_data)
        
        # Start processing in background
        background_tasks.add_task(
            _process_file_generation,
            job_id,
            title,
            file_key,
            file.filename,
            document_type,
            generation_options,
            current_user.id,
            db
        )
        
        # Update user usage
        current_user.monthly_presentations_used += 1
        await db.commit()
        
        return GenerationResponse(
            job_id=job_id,
            status="pending",
            metadata={
                "filename": file.filename,
                "file_size": len(file_content),
                "document_type": document_type.value,
                "estimated_duration_minutes": 5
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("file_generation_error", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start file-based presentation generation"
        )


# Presentation CRUD Endpoints

@router.get(
    "",
    response_model=PresentationListResponse,
    summary="List user's presentations",
    description="Get a paginated list of user's presentations with filtering options"
)
async def list_presentations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    status: Optional[str] = Query(None, description="Filter by status"),
    presentation_type: Optional[str] = Query(None, description="Filter by presentation type"),
    field_of_study: Optional[str] = Query(None, description="Filter by field of study"),
    conference_name: Optional[str] = Query(None, description="Filter by conference name"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    sort_by: Optional[str] = Query("updated_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PresentationListResponse:
    """
    Get a paginated list of user's presentations.
    
    Supports filtering by:
    - Search query (searches title, description, abstract)
    - Status (draft, ready, presented, archived)
    - Presentation type (conference, lecture, defense, etc.)
    - Field of study
    - Conference name
    - Public/private visibility
    
    Results are sorted by the specified field and order.
    """
    try:
        presentation_repo = PresentationRepository(db)
        
        # Build filters
        filters = {}
        if status:
            filters['status'] = status
        if presentation_type:
            filters['presentation_type'] = presentation_type
        if field_of_study:
            filters['field_of_study'] = field_of_study
        if conference_name:
            filters['conference_name'] = conference_name
        if is_public is not None:
            filters['is_public'] = is_public
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get presentations
        if search:
            presentations, total = await presentation_repo.search(
                query=search,
                user_id=current_user.id,
                filters=filters,
                limit=page_size,
                offset=offset
            )
        else:
            presentations, total = await presentation_repo.get_user_presentations(
                user_id=current_user.id,
                include_collaborations=True,
                status=status,
                limit=page_size,
                offset=offset
            )
        
        # Convert to response models
        presentation_responses = [
            PresentationResponse.from_orm(p) for p in presentations
        ]
        
        return PresentationListResponse(
            presentations=presentation_responses,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total
        )
        
    except Exception as e:
        logger.error("list_presentations_error", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve presentations"
        )


@router.get(
    "/{presentation_id}",
    response_model=PresentationResponse,
    summary="Get presentation details",
    description="Get detailed presentation information including slides"
)
async def get_presentation(
    presentation_id: UUID,
    include_slides: bool = Query(True, description="Include slide data"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> PresentationResponse:
    """
    Get detailed presentation information.
    
    - **presentation_id**: UUID of the presentation
    - **include_slides**: Whether to include slide content in response
    
    Public presentations can be accessed without authentication.
    Private presentations require authentication and proper permissions.
    """
    try:
        presentation_repo = PresentationRepository(db)
        
        # Get presentation with or without slides
        if include_slides:
            presentation = await presentation_repo.get_full_presentation(presentation_id)
        else:
            presentation = await presentation_repo.get(presentation_id)
        
        if not presentation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presentation not found"
            )
        
        # Check access permissions
        can_access = False
        
        if presentation.is_public:
            can_access = True
        elif current_user:
            # Check if user is owner or collaborator
            can_access = (
                presentation.owner_id == current_user.id or
                any(author.id == current_user.id for author in presentation.authors)
            )
        
        if not can_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Increment view count if not owner
        if current_user and presentation.owner_id != current_user.id:
            await presentation_repo.increment_view_count(presentation_id)
            await db.commit()
        
        return PresentationResponse.from_orm(presentation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_presentation_error", error=str(e), presentation_id=presentation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve presentation"
        )


@router.put(
    "/{presentation_id}",
    response_model=PresentationResponse,
    summary="Update presentation metadata",
    description="Update presentation information and metadata"
)
async def update_presentation(
    presentation_id: UUID,
    update_data: PresentationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PresentationResponse:
    """
    Update presentation metadata.
    
    Only the presentation owner can update the presentation.
    Updates are tracked in the version history.
    """
    try:
        presentation_repo = PresentationRepository(db)
        
        # Get presentation
        presentation = await presentation_repo.get(presentation_id)
        if not presentation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presentation not found"
            )
        
        # Check ownership
        if presentation.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the presentation owner can update it"
            )
        
        # Create version snapshot before update
        if any([
            update_data.title,
            update_data.description,
            update_data.abstract,
            update_data.keywords is not None
        ]):
            await presentation_repo.create_version(
                presentation_id,
                current_user.id,
                "Metadata updated"
            )
        
        # Update presentation
        update_dict = update_data.dict(exclude_unset=True)
        updated_presentation = await presentation_repo.update(presentation_id, update_dict)
        
        await db.commit()
        
        logger.info(
            "presentation_updated",
            presentation_id=presentation_id,
            user_id=current_user.id,
            updates=list(update_dict.keys())
        )
        
        return PresentationResponse.from_orm(updated_presentation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_presentation_error", error=str(e), presentation_id=presentation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update presentation"
        )


@router.delete(
    "/{presentation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete presentation",
    description="Soft delete a presentation (can be recovered)"
)
async def delete_presentation(
    presentation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Delete a presentation.
    
    This performs a soft delete - the presentation is marked as deleted
    but can be recovered. Only the presentation owner can delete it.
    """
    try:
        presentation_repo = PresentationRepository(db)
        
        # Get presentation
        presentation = await presentation_repo.get(presentation_id)
        if not presentation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presentation not found"
            )
        
        # Check ownership
        if presentation.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the presentation owner can delete it"
            )
        
        # Soft delete
        await presentation_repo.soft_delete(presentation_id)
        await db.commit()
        
        logger.info(
            "presentation_deleted",
            presentation_id=presentation_id,
            user_id=current_user.id
        )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_presentation_error", error=str(e), presentation_id=presentation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete presentation"
        )


# Slide Management Endpoints

@router.post(
    "/{presentation_id}/slides",
    response_model=SlideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add new slide",
    description="Add a new slide to the presentation"
)
async def add_slide(
    presentation_id: UUID,
    slide_data: SlideAddRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SlideResponse:
    """
    Add a new slide to a presentation.
    
    The slide will be inserted at the specified slide_number, or at the end
    if no slide_number is provided. Existing slides will be renumbered as needed.
    """
    try:
        presentation_repo = PresentationRepository(db)
        slide_repo = SlideRepository(db)
        
        # Get presentation
        presentation = await presentation_repo.get(presentation_id)
        if not presentation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presentation not found"
            )
        
        # Check permissions
        can_edit = (
            presentation.owner_id == current_user.id or
            any(author.id == current_user.id for author in presentation.authors)
        )
        
        if not can_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # Determine slide number
        if slide_data.slide_number is None:
            slide_data.slide_number = presentation.slide_count + 1
        
        # Create slide
        slide_dict = slide_data.dict()
        slide_dict['presentation_id'] = presentation_id
        
        slide = await slide_repo.create(slide_dict)
        
        # Update presentation slide count
        await presentation_repo.update(
            presentation_id,
            {"slide_count": presentation.slide_count + 1}
        )
        
        await db.commit()
        
        logger.info(
            "slide_added",
            presentation_id=presentation_id,
            slide_id=slide.id,
            user_id=current_user.id
        )
        
        return SlideResponse.from_orm(slide)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("add_slide_error", error=str(e), presentation_id=presentation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add slide"
        )


@router.put(
    "/{presentation_id}/slides/{slide_id}",
    response_model=SlideResponse,
    summary="Update slide content",
    description="Update the content and metadata of a specific slide"
)
async def update_slide(
    presentation_id: UUID,
    slide_id: UUID,
    update_data: SlideUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SlideResponse:
    """
    Update slide content and metadata.
    
    Only users with write permissions to the presentation can update slides.
    """
    try:
        presentation_repo = PresentationRepository(db)
        slide_repo = SlideRepository(db)
        
        # Get presentation
        presentation = await presentation_repo.get(presentation_id)
        if not presentation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presentation not found"
            )
        
        # Check permissions
        can_edit = (
            presentation.owner_id == current_user.id or
            any(author.id == current_user.id for author in presentation.authors)
        )
        
        if not can_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # Get slide
        slide = await slide_repo.get(slide_id)
        if not slide or slide.presentation_id != presentation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Slide not found"
            )
        
        # Update slide
        update_dict = update_data.dict(exclude_unset=True)
        updated_slide = await slide_repo.update(slide_id, update_dict)
        
        await db.commit()
        
        logger.info(
            "slide_updated",
            presentation_id=presentation_id,
            slide_id=slide_id,
            user_id=current_user.id,
            updates=list(update_dict.keys())
        )
        
        return SlideResponse.from_orm(updated_slide)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_slide_error", error=str(e), slide_id=slide_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update slide"
        )


# Generation Progress Tracking

@router.get(
    "/jobs/{job_id}/progress",
    response_model=GenerationProgress,
    summary="Get generation progress",
    description="Get the current progress of a presentation generation job"
)
async def get_generation_progress(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationProgress:
    """
    Get the current progress of a presentation generation job.
    
    Returns real-time progress information including:
    - Current status
    - Progress percentage
    - Current processing step
    - Estimated completion time
    """
    try:
        job_repo = GenerationJobRepository(db)
        
        # Get job
        job = await job_repo.get(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation job not found"
            )
        
        # Check ownership
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Calculate progress percentage
        progress = 0.0
        if job.status == "pending":
            progress = 0.0
        elif job.status == "processing":
            # Estimate based on processing steps
            steps = job.processing_steps or []
            total_steps = 6  # Standard number of processing steps
            completed_steps = sum(1 for step in steps if step.get("status") == "completed")
            progress = min(0.9, completed_steps / total_steps)
        elif job.status == "completed":
            progress = 1.0
        elif job.status in ["failed", "cancelled"]:
            progress = 0.0
        
        return GenerationProgress(
            job_id=job_id,
            status=job.status,
            progress=progress,
            current_step=job.processing_steps[-1].get("step", "unknown") if job.processing_steps else "pending",
            message=job.error_message if job.status == "failed" else None,
            estimated_completion=job.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_progress_error", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generation progress"
        )


@router.get(
    "/jobs/{job_id}/stream",
    summary="Stream generation progress",
    description="Get real-time progress updates via Server-Sent Events"
)
async def stream_generation_progress(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream real-time generation progress updates.
    
    Returns Server-Sent Events (SSE) stream with real-time progress updates.
    Clients can listen to this endpoint to get live updates during generation.
    """
    try:
        job_repo = GenerationJobRepository(db)
        
        # Verify job ownership
        job = await job_repo.get(job_id)
        if not job or job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation job not found"
            )
        
        async def generate_progress_stream():
            """Generate Server-Sent Events for progress updates."""
            while True:
                # Get current job status
                current_job = await job_repo.get(job_id)
                if not current_job:
                    break
                
                # Format SSE message
                progress_data = {
                    "job_id": str(job_id),
                    "status": current_job.status,
                    "progress": 0.0,  # Calculate as above
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # Break if job is complete
                if current_job.status in ["completed", "failed", "cancelled"]:
                    break
                
                # Wait before next update
                await asyncio.sleep(2)
        
        return StreamingResponse(
            generate_progress_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("stream_progress_error", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stream progress"
        )


# Background Processing Functions

async def _process_text_generation(
    job_id: UUID,
    title: str,
    content: str,
    options: GenerationOptions,
    user_id: UUID,
    db: AsyncSession,
) -> None:
    """Process text-based presentation generation in background."""
    try:
        job_repo = GenerationJobRepository(db)
        presentation_repo = PresentationRepository(db)
        
        # Update job status
        await job_repo.update(job_id, {
            "status": "processing",
            "started_at": datetime.utcnow()
        })
        
        # Initialize generation pipeline
        pipeline = GenerationPipeline(db)
        
        # Generate presentation
        generation_result = None
        async for update in pipeline.generate_presentation(content, user_id, title, options.dict()):
            if isinstance(update, dict) and update.get("type") == "result":
                generation_result = update["presentation"]
                break
        
        if not generation_result:
            raise Exception("Generation pipeline failed to produce result")
        
        # Create presentation record
        presentation_data = PresentationCreate(
            title=generation_result["title"],
            description=f"Generated from text content ({len(content)} characters)",
            abstract=content[:500] if len(content) > 500 else content,
            presentation_type=options.presentation_type,
            academic_level=options.academic_level,
            duration_minutes=int(generation_result["metadata"]["estimated_duration"]),
            language=options.language,
            template_id=options.template_id,
        )
        
        presentation_dict = presentation_data.dict()
        presentation_dict.update({
            "owner_id": user_id,
            "slide_count": generation_result["metadata"]["total_slides"],
            "status": "draft"
        })
        
        presentation = await presentation_repo.create(presentation_dict)
        
        # Create slides
        slide_repo = SlideRepository(db)
        for i, slide_data in enumerate(generation_result["slides"], 1):
            slide_dict = {
                "presentation_id": presentation.id,
                "slide_number": i,
                "title": slide_data.get("title"),
                "content": slide_data,
                "layout_type": slide_data.get("layout_type", "content"),
                "speaker_notes": slide_data.get("speaker_notes"),
            }
            await slide_repo.create(slide_dict)
        
        # Update job with success
        await job_repo.update(job_id, {
            "status": "completed",
            "presentation_id": presentation.id,
            "completed_at": datetime.utcnow(),
            "result_data": {"presentation_id": str(presentation.id)}
        })
        
        await db.commit()
        
        logger.info(
            "text_generation_completed",
            job_id=job_id,
            presentation_id=presentation.id,
            user_id=user_id
        )
        
    except Exception as e:
        logger.error("text_generation_failed", job_id=job_id, error=str(e))
        
        # Update job with failure
        await job_repo.update(job_id, {
            "status": "failed",
            "completed_at": datetime.utcnow(),
            "error_message": str(e)
        })
        
        await db.commit()


async def _process_file_generation(
    job_id: UUID,
    title: str,
    file_key: str,
    filename: str,
    document_type: DocumentType,
    options: GenerationOptions,
    user_id: UUID,
    db: AsyncSession,
) -> None:
    """Process file-based presentation generation in background."""
    try:
        job_repo = GenerationJobRepository(db)
        
        # Update job status
        await job_repo.update(job_id, {
            "status": "processing",
            "started_at": datetime.utcnow()
        })
        
        # Process document
        async_processor = AsyncDocumentProcessor()
        await async_processor.initialize()
        
        processing_request = ProcessingRequest(
            document_id=uuid.uuid4(),
            file_path=file_key,
            document_type=document_type,
            options={"extract_text": True, "extract_images": True}
        )
        
        processing_job_id = await async_processor.submit_processing_request(
            processing_request,
            user_id
        )
        
        # Wait for processing to complete
        max_wait = 300  # 5 minutes
        wait_time = 0
        
        while wait_time < max_wait:
            progress = await async_processor.get_job_status(processing_job_id)
            if not progress:
                break
            
            if progress.status == ProcessingStatus.COMPLETED:
                # Extract text content from processing result
                # This would depend on the actual processing result structure
                extracted_content = "Extracted document content..."  # Placeholder
                
                # Continue with text generation
                await _process_text_generation(
                    job_id, title, extracted_content, options, user_id, db
                )
                return
            elif progress.status == ProcessingStatus.FAILED:
                raise Exception(f"Document processing failed: {progress.message}")
            
            await asyncio.sleep(5)
            wait_time += 5
        
        raise Exception("Document processing timeout")
        
    except Exception as e:
        logger.error("file_generation_failed", job_id=job_id, error=str(e))
        
        # Update job with failure
        await job_repo.update(job_id, {
            "status": "failed",
            "completed_at": datetime.utcnow(),
            "error_message": str(e)
        })
        
        await db.commit()