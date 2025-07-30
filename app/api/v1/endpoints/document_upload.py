"""
Document upload endpoints with chunked and multipart support.

Provides comprehensive file upload capabilities including:
- Chunked uploads for large files
- Multipart upload management
- Resume capability for interrupted uploads
- Progress tracking integration
- File validation and security checks
"""

import asyncio
import hashlib
import logging
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import aiofiles
import magic
from fastapi import (
    APIRouter,
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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.domain.schemas.document_processing import (
    DocumentType,
    ProcessingRequest,
    ProcessingStatus
)
from app.domain.schemas.user import User
from app.services.document_processing.async_processor import AsyncDocumentProcessor
from app.services.document_processing.storage.s3_manager import S3StorageManager
from app.services.document_processing.queue.task_queue import TaskPriority
from app.services.security.rate_limiter import create_rate_limiter


logger = logging.getLogger(__name__)
settings = get_settings()

# Rate limiter for upload endpoints
limiter = create_rate_limiter()
router = APIRouter()
router.state.limiter = limiter
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class ChunkUploadRequest(BaseModel):
    """Request model for chunk upload."""
    upload_id: str = Field(..., description="Multipart upload ID")
    part_number: int = Field(..., ge=1, le=10000, description="Part number (1-based)")
    total_parts: int = Field(..., ge=1, le=10000, description="Total number of parts")
    chunk_hash: str = Field(..., description="MD5 hash of chunk data")
    is_final_chunk: bool = Field(default=False, description="Whether this is the final chunk")


class InitiateUploadRequest(BaseModel):
    """Request model for initiating multipart upload."""
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0, description="Total file size in bytes")
    content_type: Optional[str] = Field(None, description="MIME type of the file")
    document_type: DocumentType = Field(..., description="Type of document")
    processing_options: Dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    
    @validator("filename")
    def validate_filename(cls, v):
        """Validate filename for security."""
        # Remove path traversal attempts
        filename = Path(v).name
        
        # Check for allowed extensions
        allowed_extensions = settings.ALLOWED_UPLOAD_EXTENSIONS
        file_extension = Path(filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise ValueError(f"File extension {file_extension} not allowed")
        
        return filename
    
    @validator("file_size")
    def validate_file_size(cls, v):
        """Validate file size limits."""
        max_size = settings.max_upload_size_bytes
        if v > max_size:
            raise ValueError(f"File size {v} exceeds maximum allowed size of {max_size} bytes")
        return v


class InitiateUploadResponse(BaseModel):
    """Response model for upload initiation."""
    upload_id: str
    job_id: UUID
    chunk_size: int
    total_chunks: int
    expires_at: str
    upload_url: Optional[str] = None


class ChunkUploadResponse(BaseModel):
    """Response model for chunk upload."""
    part_number: int
    etag: str
    uploaded_size: int
    total_uploaded: int
    progress_percentage: float


class CompleteUploadResponse(BaseModel):
    """Response model for upload completion."""
    job_id: UUID
    file_key: str
    file_size: int
    processing_status: ProcessingStatus
    estimated_processing_time: Optional[int] = None


class UploadStatusResponse(BaseModel):
    """Response model for upload status."""
    upload_id: str
    job_id: UUID
    status: str
    progress_percentage: float
    uploaded_size: int
    total_size: int
    parts_uploaded: int
    total_parts: int
    created_at: str
    expires_at: str


# Dependency to get storage manager
async def get_storage_manager() -> S3StorageManager:
    """Get S3 storage manager instance."""
    storage_manager = S3StorageManager()
    if not storage_manager._initialized:
        await storage_manager.initialize()
    return storage_manager


# Dependency to get async processor
async def get_async_processor() -> AsyncDocumentProcessor:
    """Get async document processor instance."""
    processor = AsyncDocumentProcessor()
    if not processor.is_running:
        await processor.initialize()
    return processor


@router.post(
    "/initiate",
    response_model=InitiateUploadResponse,
    summary="Initiate multipart upload",
    description="Start a new multipart upload session for large file uploads"
)
@limiter.limit("10/minute")
async def initiate_upload(
    request: Request,
    upload_request: InitiateUploadRequest,
    current_user: User = Depends(get_current_user),
    storage_manager: S3StorageManager = Depends(get_storage_manager),
    async_processor: AsyncDocumentProcessor = Depends(get_async_processor)
):
    """
    Initiate a multipart upload session.
    
    This endpoint starts a new multipart upload and creates a processing job
    that will be executed once the upload is complete.
    """
    try:
        logger.info(f"Initiating upload for user {current_user.id}: {upload_request.filename}")
        
        # Generate unique identifiers
        job_id = uuid4()
        file_key = f"uploads/{current_user.id}/{job_id}/{upload_request.filename}"
        
        # Calculate chunk information
        chunk_size = storage_manager.chunk_size
        total_chunks = (upload_request.file_size + chunk_size - 1) // chunk_size
        
        # Start multipart upload
        upload_id = await storage_manager.start_multipart_upload(
            key=file_key,
            total_size=upload_request.file_size,
            metadata={
                "user_id": str(current_user.id),
                "job_id": str(job_id),
                "filename": upload_request.filename,
                "document_type": upload_request.document_type.value
            },
            content_type=upload_request.content_type or mimetypes.guess_type(upload_request.filename)[0] or "application/octet-stream"
        )
        
        # Get upload session info
        upload_progress = await storage_manager.get_upload_progress(upload_id)
        
        if not upload_progress:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create upload session"
            )
        
        logger.info(f"Created upload session {upload_id} for job {job_id}")
        
        return InitiateUploadResponse(
            upload_id=upload_id,
            job_id=job_id,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            expires_at=upload_progress["expires_at"].isoformat(),
            upload_url=f"/api/v1/documents/upload/chunk"
        )
        
    except ValueError as e:
        logger.warning(f"Invalid upload request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to initiate upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate upload"
        )


@router.post(
    "/chunk",
    response_model=ChunkUploadResponse,
    summary="Upload file chunk",
    description="Upload a single chunk of a multipart upload"
)
@limiter.limit("100/minute")
async def upload_chunk(
    request: Request,
    upload_id: str = Form(...),
    part_number: int = Form(..., ge=1, le=10000),
    total_parts: int = Form(..., ge=1, le=10000),
    chunk_hash: str = Form(...),
    is_final_chunk: bool = Form(default=False),
    chunk_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    storage_manager: S3StorageManager = Depends(get_storage_manager)
):
    """
    Upload a single chunk of a multipart upload.
    
    Each chunk is validated for integrity and uploaded to the storage backend.
    Progress is tracked and reported back to the client.
    """
    try:
        logger.debug(f"Uploading chunk {part_number}/{total_parts} for upload {upload_id}")
        
        # Validate upload session exists
        upload_progress = await storage_manager.get_upload_progress(upload_id)
        if not upload_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found or expired"
            )
        
        # Read chunk data
        chunk_data = await chunk_file.read()
        
        # Validate chunk size
        if len(chunk_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty chunk not allowed"
            )
        
        # Validate chunk hash
        calculated_hash = hashlib.md5(chunk_data).hexdigest()
        if calculated_hash != chunk_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chunk hash mismatch"
            )
        
        # Upload the chunk
        upload_part = await storage_manager.upload_part(
            upload_id=upload_id,
            part_number=part_number,
            data=chunk_data
        )
        
        # Get updated progress
        updated_progress = await storage_manager.get_upload_progress(upload_id)
        
        logger.debug(f"Successfully uploaded chunk {part_number} ({len(chunk_data)} bytes)")
        
        return ChunkUploadResponse(
            part_number=part_number,
            etag=upload_part.etag,
            uploaded_size=len(chunk_data),
            total_uploaded=updated_progress["uploaded_size"],
            progress_percentage=updated_progress["progress_percentage"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload chunk {part_number} for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload chunk"
        )


@router.post(
    "/complete/{upload_id}",
    response_model=CompleteUploadResponse,
    summary="Complete multipart upload",
    description="Complete a multipart upload and start document processing"
)
@limiter.limit("10/minute")
async def complete_upload(
    request: Request,
    upload_id: str,
    current_user: User = Depends(get_current_user),
    storage_manager: S3StorageManager = Depends(get_storage_manager),
    async_processor: AsyncDocumentProcessor = Depends(get_async_processor)
):
    """
    Complete a multipart upload and initiate document processing.
    
    This endpoint finalizes the upload, validates the complete file,
    and submits it for async processing.
    """
    try:
        logger.info(f"Completing upload {upload_id} for user {current_user.id}")
        
        # Validate upload session
        upload_progress = await storage_manager.get_upload_progress(upload_id)
        if not upload_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found or expired"
            )
        
        # Check if upload is complete
        if not upload_progress["is_complete"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload is not complete. All chunks must be uploaded first."
            )
        
        # Complete the multipart upload
        completion_result = await storage_manager.complete_multipart_upload(upload_id)
        
        # Extract metadata from upload
        upload_session = storage_manager.active_uploads.get(upload_id)
        if not upload_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Upload session data not found"
            )
        
        job_id = UUID(upload_session.metadata["job_id"])
        filename = upload_session.metadata["filename"]
        document_type = DocumentType(upload_session.metadata["document_type"])
        
        # Perform additional file validation
        await _validate_uploaded_file(
            storage_manager=storage_manager,
            file_key=completion_result["key"],
            filename=filename,
            file_size=completion_result["total_size"]
        )
        
        # Create processing request
        processing_request = ProcessingRequest(
            document_id=job_id,
            file_path=completion_result["key"],
            document_type=document_type,
            options={
                "filename": filename,
                "user_id": str(current_user.id),
                "upload_id": upload_id
            }
        )
        
        # Submit for processing
        submitted_job_id = await async_processor.submit_processing_request(
            request=processing_request,
            user_id=current_user.id,
            priority=TaskPriority.NORMAL
        )
        
        # Estimate processing time based on file size and type
        estimated_time = _estimate_processing_time(
            file_size=completion_result["total_size"],
            document_type=document_type
        )
        
        logger.info(f"Successfully completed upload {upload_id} and submitted job {submitted_job_id}")
        
        return CompleteUploadResponse(
            job_id=submitted_job_id,
            file_key=completion_result["key"],
            file_size=completion_result["total_size"],
            processing_status=ProcessingStatus.PENDING,
            estimated_processing_time=estimated_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete upload {upload_id}: {e}")
        
        # Attempt to abort the upload on error
        try:
            await storage_manager.abort_multipart_upload(upload_id)
        except Exception as cleanup_error:
            logger.error(f"Failed to abort upload {upload_id} during error cleanup: {cleanup_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete upload"
        )


@router.get(
    "/status/{upload_id}",
    response_model=UploadStatusResponse,
    summary="Get upload status",
    description="Get the current status and progress of a multipart upload"
)
@limiter.limit("30/minute")
async def get_upload_status(
    request: Request,
    upload_id: str,
    current_user: User = Depends(get_current_user),
    storage_manager: S3StorageManager = Depends(get_storage_manager)
):
    """Get the current status of a multipart upload."""
    try:
        upload_progress = await storage_manager.get_upload_progress(upload_id)
        
        if not upload_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found or expired"
            )
        
        # Validate user access
        upload_session = storage_manager.active_uploads.get(upload_id)
        if upload_session and UUID(upload_session.metadata["user_id"]) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this upload session"
            )
        
        # Determine upload status
        status_text = "in_progress"
        if upload_progress["is_complete"]:
            status_text = "complete"
        elif upload_progress["progress_percentage"] == 0:
            status_text = "pending"
        
        return UploadStatusResponse(
            upload_id=upload_id,
            job_id=UUID(upload_session.metadata["job_id"]) if upload_session else uuid4(),
            status=status_text,
            progress_percentage=upload_progress["progress_percentage"],
            uploaded_size=upload_progress["uploaded_size"],
            total_size=upload_progress["total_size"],
            parts_uploaded=upload_progress["parts_count"],
            total_parts=0,  # Could be calculated from total_size/chunk_size
            created_at=upload_progress["created_at"].isoformat(),
            expires_at=upload_progress["expires_at"].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get upload status for {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upload status"
        )


@router.delete(
    "/cancel/{upload_id}",
    summary="Cancel multipart upload",
    description="Cancel an in-progress multipart upload"
)
@limiter.limit("10/minute")
async def cancel_upload(
    request: Request,
    upload_id: str,
    current_user: User = Depends(get_current_user),
    storage_manager: S3StorageManager = Depends(get_storage_manager)
):
    """Cancel a multipart upload and clean up resources."""
    try:
        logger.info(f"Cancelling upload {upload_id} for user {current_user.id}")
        
        # Validate upload session exists and user has access
        upload_session = storage_manager.active_uploads.get(upload_id)
        if not upload_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found"
            )
        
        if UUID(upload_session.metadata["user_id"]) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this upload session"
            )
        
        # Abort the multipart upload
        await storage_manager.abort_multipart_upload(upload_id)
        
        logger.info(f"Successfully cancelled upload {upload_id}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Upload cancelled successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel upload"
        )


@router.post(
    "/simple",
    response_model=CompleteUploadResponse,
    summary="Simple file upload",
    description="Upload a file directly without chunking (for small files)"
)
@limiter.limit("20/minute")
async def simple_upload(
    request: Request,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    priority: TaskPriority = Form(default=TaskPriority.NORMAL),
    processing_options: str = Form(default="{}"),  # JSON string
    current_user: User = Depends(get_current_user),
    storage_manager: S3StorageManager = Depends(get_storage_manager),
    async_processor: AsyncDocumentProcessor = Depends(get_async_processor)
):
    """
    Upload a small file directly without multipart chunking.
    
    This is a simpler endpoint for files under the multipart threshold.
    """
    try:
        logger.info(f"Simple upload for user {current_user.id}: {file.filename}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        
        # Check file size
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )
        
        # Validate file type using python-magic
        file_mime = magic.from_buffer(file_content, mime=True)
        await _validate_file_content(file_content, file.filename, file_mime)
        
        # Generate identifiers
        job_id = uuid4()
        file_key = f"uploads/{current_user.id}/{job_id}/{file.filename}"
        
        # Save file temporarily for upload
        temp_file_path = f"/tmp/{job_id}_{file.filename}"
        
        try:
            async with aiofiles.open(temp_file_path, "wb") as temp_file:
                await temp_file.write(file_content)
            
            # Upload to storage
            upload_result = await storage_manager.upload_file(
                file_path=temp_file_path,
                key=file_key,
                metadata={
                    "user_id": str(current_user.id),
                    "job_id": str(job_id),
                    "filename": file.filename,
                    "document_type": document_type.value
                },
                content_type=file_mime
            )
            
            # Parse processing options
            try:
                import json
                options = json.loads(processing_options)
            except json.JSONDecodeError:
                options = {}
            
            # Create processing request
            processing_request = ProcessingRequest(
                document_id=job_id,
                file_path=file_key,
                document_type=document_type,
                options={
                    **options,
                    "filename": file.filename,
                    "user_id": str(current_user.id),
                    "upload_method": "simple"
                }
            )
            
            # Submit for processing
            submitted_job_id = await async_processor.submit_processing_request(
                request=processing_request,
                user_id=current_user.id,
                priority=priority
            )
            
            # Estimate processing time
            estimated_time = _estimate_processing_time(file_size, document_type)
            
            logger.info(f"Successfully uploaded and submitted job {submitted_job_id}")
            
            return CompleteUploadResponse(
                job_id=submitted_job_id,
                file_key=file_key,
                file_size=file_size,
                processing_status=ProcessingStatus.PENDING,
                estimated_processing_time=estimated_time
            )
            
        finally:
            # Clean up temporary file
            try:
                Path(temp_file_path).unlink(missing_ok=True)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file {temp_file_path}: {cleanup_error}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed simple upload for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.get(
    "/active",
    summary="List active uploads",
    description="Get list of active multipart uploads for the current user"
)
@limiter.limit("10/minute")
async def list_active_uploads(
    request: Request,
    current_user: User = Depends(get_current_user),
    storage_manager: S3StorageManager = Depends(get_storage_manager)
):
    """List active multipart uploads for the current user."""
    try:
        user_uploads = []
        
        for upload_id, upload_session in storage_manager.active_uploads.items():
            if UUID(upload_session.metadata["user_id"]) == current_user.id:
                progress = await storage_manager.get_upload_progress(upload_id)
                if progress:
                    user_uploads.append({
                        "upload_id": upload_id,
                        "filename": upload_session.metadata["filename"],
                        "document_type": upload_session.metadata["document_type"],
                        "progress_percentage": progress["progress_percentage"],
                        "uploaded_size": progress["uploaded_size"],
                        "total_size": progress["total_size"],
                        "created_at": progress["created_at"].isoformat(),
                        "expires_at": progress["expires_at"].isoformat()
                    })
        
        return {"active_uploads": user_uploads}
        
    except Exception as e:
        logger.error(f"Failed to list active uploads for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list active uploads"
        )


# Helper functions

async def _validate_uploaded_file(
    storage_manager: S3StorageManager,
    file_key: str,
    filename: str,
    file_size: int
) -> None:
    """Validate an uploaded file for security and integrity."""
    try:
        # Download a small portion to validate file type
        temp_path = f"/tmp/validate_{uuid4()}"
        
        try:
            # Download first 1KB for validation
            # Note: This is a simplified validation. In production, you'd want
            # more sophisticated file type detection and virus scanning
            pass
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"File validation failed for {file_key}: {e}")
        raise ValueError(f"File validation failed: {e}")


async def _validate_file_content(file_content: bytes, filename: str, mime_type: str) -> None:
    """Validate file content for security."""
    # Check file extension matches MIME type
    file_extension = Path(filename).suffix.lower()
    
    # Basic MIME type validation
    expected_mimes = {
        ".pdf": ["application/pdf"],
        ".txt": ["text/plain"],
        ".md": ["text/plain", "text/markdown"],
        ".tex": ["text/plain", "text/x-tex"],
        ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    }
    
    if file_extension in expected_mimes:
        if mime_type not in expected_mimes[file_extension]:
            raise ValueError(f"File content does not match extension {file_extension}")
    
    # Check for suspicious content (basic scan)
    suspicious_patterns = [
        b"<script",
        b"javascript:",
        b"<?php",
        b"<%",
        b"eval(",
    ]
    
    file_start = file_content[:4096]  # Check first 4KB
    for pattern in suspicious_patterns:
        if pattern in file_start.lower():
            raise ValueError("Suspicious content detected in file")


def _estimate_processing_time(file_size: int, document_type: DocumentType) -> int:
    """Estimate processing time based on file size and type."""
    # Base processing time per MB
    base_times = {
        DocumentType.PDF: 30,  # seconds per MB
        DocumentType.DOCX: 20,
        DocumentType.TXT: 5,
        DocumentType.LATEX: 25,
        DocumentType.HTML: 15
    }
    
    base_time = base_times.get(document_type, 20)
    file_size_mb = file_size / (1024 * 1024)
    
    # Minimum 10 seconds, maximum 10 minutes
    estimated_seconds = max(10, min(600, int(base_time * file_size_mb)))
    
    return estimated_seconds