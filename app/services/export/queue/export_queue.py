"""
Comprehensive Export Queue System for SlideGenie.

Handles asynchronous processing of large presentations with:
- Job queuing and prioritization
- Email notifications on completion
- Temporary download links with 24-hour expiration
- Batch export capabilities
- Progress tracking with WebSocket updates
- Error recovery and retry mechanisms
- Export history and analytics
"""

import asyncio
import hashlib
import hmac
import io
import json
import logging
import secrets
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

import aiofiles
import structlog
from pydantic import BaseModel, Field, validator

from app.core.config import get_settings
from app.core.exceptions import ExportError, InvalidRequestError, QuotaExceededError
from app.domain.schemas.generation import Citation, SlideContent
from app.domain.schemas.user import User
from app.services.auth.email_service import EmailValidationService
from app.services.document_processing.queue.task_queue import TaskQueue, TaskPriority, TaskStatus
from app.services.export.export_service import ExportFormat, ExportService
from app.api.v1.endpoints.websocket import broadcast_job_progress, send_user_notification

logger = structlog.get_logger(__name__)
settings = get_settings()


class ExportJobStatus(str, Enum):
    """Export job status values."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ExportJobPriority(str, Enum):
    """Export job priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BatchExportType(str, Enum):
    """Batch export types."""
    MULTI_FORMAT = "multi_format"  # Same presentation, multiple formats
    MULTI_PRESENTATION = "multi_presentation"  # Multiple presentations, same format
    MIXED = "mixed"  # Multiple presentations, multiple formats


class ExportJobRequest(BaseModel):
    """Export job request model."""
    user_id: UUID = Field(..., description="User ID requesting the export")
    presentation_id: Optional[UUID] = Field(None, description="Presentation ID if from saved presentation")
    slides: List[SlideContent] = Field(..., description="Slide content to export")
    formats: List[ExportFormat] = Field(..., description="Export formats requested")
    template_config: Dict[str, Any] = Field(default_factory=dict, description="Template configuration")
    citations: Optional[List[Citation]] = Field(None, description="Citations to include")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Presentation metadata")
    priority: ExportJobPriority = Field(ExportJobPriority.NORMAL, description="Job priority")
    notification_email: Optional[str] = Field(None, description="Email for completion notification")
    expiry_hours: int = Field(24, ge=1, le=168, description="Download link expiry hours (1-168)")
    batch_name: Optional[str] = Field(None, description="Batch job name")
    
    @validator('formats')
    def validate_formats(cls, v):
        if not v:
            raise ValueError("At least one export format must be specified")
        if len(v) > 5:
            raise ValueError("Maximum 5 formats allowed per job")
        return v
    
    @validator('slides')
    def validate_slides(cls, v):
        if not v:
            raise ValueError("At least one slide must be provided")
        if len(v) > 500:
            raise ValueError("Maximum 500 slides allowed per job")
        return v


class ExportJobResult(BaseModel):
    """Export job result model."""
    job_id: UUID
    format: ExportFormat
    file_size: int
    file_path: str
    download_url: str
    expires_at: datetime
    checksum: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExportJob(BaseModel):
    """Export job model."""
    job_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    presentation_id: Optional[UUID] = None
    status: ExportJobStatus = ExportJobStatus.QUEUED
    priority: ExportJobPriority = ExportJobPriority.NORMAL
    formats: List[ExportFormat]
    slides: List[SlideContent]
    template_config: Dict[str, Any] = Field(default_factory=dict)
    citations: Optional[List[Citation]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notification_email: Optional[str] = None
    expiry_hours: int = 24
    batch_name: Optional[str] = None
    
    # Processing details
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0
    current_stage: str = "queued"
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Results
    results: List[ExportJobResult] = Field(default_factory=list)
    total_size: int = 0
    
    # Analytics
    processing_time_seconds: Optional[float] = None
    queue_time_seconds: Optional[float] = None
    worker_id: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ExportQuota(BaseModel):
    """User export quota model."""
    user_id: UUID
    daily_exports: int = 0
    monthly_exports: int = 0
    daily_limit: int = 50
    monthly_limit: int = 1000
    daily_reset_at: datetime = Field(default_factory=lambda: datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
    monthly_reset_at: datetime = Field(default_factory=lambda: datetime.utcnow().replace(day=1).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32))


class TemporaryLinkManager:
    """Manages temporary download links with security."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()
        self.base_url = settings.API_BASE_URL
    
    def generate_secure_token(self, job_id: UUID, format: str, expires_at: datetime) -> str:
        """Generate secure download token."""
        payload = f"{job_id}:{format}:{expires_at.isoformat()}"
        signature = hmac.new(
            self.secret_key,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token_data = {
            "job_id": str(job_id),
            "format": format,
            "expires_at": expires_at.isoformat(),
            "signature": signature
        }
        
        # Base64 encode the token
        import base64
        token_json = json.dumps(token_data)
        return base64.urlsafe_b64encode(token_json.encode()).decode()
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode download token."""
        try:
            import base64
            token_json = base64.urlsafe_b64decode(token.encode()).decode()
            token_data = json.loads(token_json)
            
            # Verify expiration
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.utcnow() > expires_at:
                return None
            
            # Verify signature
            payload = f"{token_data['job_id']}:{token_data['format']}:{token_data['expires_at']}"
            expected_signature = hmac.new(
                self.secret_key,
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(token_data["signature"], expected_signature):
                return None
            
            return token_data
            
        except Exception as e:
            logger.error("Token verification failed", error=str(e))
            return None
    
    def generate_download_url(self, job_id: UUID, format: str, expires_at: datetime) -> str:
        """Generate secure download URL."""
        token = self.generate_secure_token(job_id, format, expires_at)
        return f"{self.base_url}/api/v1/exports/download/{token}"


class EmailNotificationService:
    """Handles export completion email notifications."""
    
    def __init__(self, email_service: EmailValidationService):
        self.email_service = email_service
    
    async def send_completion_notification(
        self,
        job: ExportJob,
        user: User,
        results: List[ExportJobResult]
    ) -> bool:
        """Send export completion notification email."""
        try:
            notification_email = job.notification_email or user.email
            
            if job.status == ExportJobStatus.COMPLETED:
                return await self._send_success_notification(
                    notification_email, user.full_name, job, results
                )
            else:
                return await self._send_failure_notification(
                    notification_email, user.full_name, job
                )
                
        except Exception as e:
            logger.error("Failed to send notification email", error=str(e), job_id=str(job.job_id))
            return False
    
    async def _send_success_notification(
        self,
        email: str,
        full_name: str,
        job: ExportJob,
        results: List[ExportJobResult]
    ) -> bool:
        """Send successful export notification."""
        subject = f"Your SlideGenie export is ready!"
        
        # Prepare download links
        download_links = []
        for result in results:
            download_links.append({
                "format": result.format.value.upper(),
                "url": result.download_url,
                "size": self._format_file_size(result.file_size),
                "expires": result.expires_at.strftime("%B %d, %Y at %I:%M %p UTC")
            })
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Your SlideGenie Export is Ready</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2563eb;">SlideGenie</h1>
            <p style="font-size: 18px; color: #666;">Export Complete!</p>
        </div>
        
        <h2>Hello {full_name},</h2>
        
        <p>Great news! Your presentation export has been completed successfully.</p>
        
        <div style="background-color: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #1e40af;">Export Details</h3>
            <ul style="margin: 0; padding-left: 20px;">
                <li><strong>Job ID:</strong> {job.job_id}</li>
                <li><strong>Slides:</strong> {len(job.slides)} slides</li>
                <li><strong>Formats:</strong> {len(results)} file(s)</li>
                <li><strong>Total Size:</strong> {self._format_file_size(job.total_size)}</li>
                <li><strong>Processing Time:</strong> {job.processing_time_seconds:.1f} seconds</li>
            </ul>
        </div>
        
        <h3>Download Your Files</h3>
        <p>Click the links below to download your exported presentation files:</p>
        
        <div style="margin: 20px 0;">
        {self._generate_download_links_html(download_links)}
        </div>
        
        <div style="background-color: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; color: #92400e;">
                <strong>Important:</strong> These download links will expire on {results[0].expires_at.strftime("%B %d, %Y at %I:%M %p UTC")}. 
                Please download your files before this date.
            </p>
        </div>
        
        <div style="margin-top: 40px; text-align: center; font-size: 12px; color: #999;">
            <p>&copy; 2024 SlideGenie. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Your SlideGenie Export is Ready!

Hello {full_name},

Great news! Your presentation export has been completed successfully.

Export Details:
- Job ID: {job.job_id}
- Slides: {len(job.slides)} slides
- Formats: {len(results)} file(s)
- Total Size: {self._format_file_size(job.total_size)}
- Processing Time: {job.processing_time_seconds:.1f} seconds

Download Your Files:
{self._generate_download_links_text(download_links)}

IMPORTANT: These download links will expire on {results[0].expires_at.strftime("%B %d, %Y at %I:%M %p UTC")}. 
Please download your files before this date.

© 2024 SlideGenie. All rights reserved.
        """
        
        return await self.email_service._send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    async def _send_failure_notification(
        self,
        email: str,
        full_name: str,
        job: ExportJob
    ) -> bool:
        """Send failed export notification."""
        subject = f"SlideGenie export failed"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SlideGenie Export Failed</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #dc2626;">SlideGenie</h1>
            <p style="font-size: 18px; color: #666;">Export Failed</p>
        </div>
        
        <h2>Hello {full_name},</h2>
        
        <p>We're sorry, but your presentation export could not be completed.</p>
        
        <div style="background-color: #fef2f2; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #dc2626;">Error Details</h3>
            <ul style="margin: 0; padding-left: 20px;">
                <li><strong>Job ID:</strong> {job.job_id}</li>
                <li><strong>Error:</strong> {job.error_message or 'Unknown error occurred'}</li>
                <li><strong>Retry Attempts:</strong> {job.retry_count}/{job.max_retries}</li>
            </ul>
        </div>
        
        <p>Our team has been notified and will investigate the issue. You can try exporting again, or contact support if the problem persists.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.API_BASE_URL}/support" 
               style="background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                Contact Support
            </a>
        </div>
        
        <div style="margin-top: 40px; text-align: center; font-size: 12px; color: #999;">
            <p>&copy; 2024 SlideGenie. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
SlideGenie Export Failed

Hello {full_name},

We're sorry, but your presentation export could not be completed.

Error Details:
- Job ID: {job.job_id}
- Error: {job.error_message or 'Unknown error occurred'}
- Retry Attempts: {job.retry_count}/{job.max_retries}

Our team has been notified and will investigate the issue. You can try exporting again, or contact support if the problem persists.

Contact Support: {settings.API_BASE_URL}/support

© 2024 SlideGenie. All rights reserved.
        """
        
        return await self.email_service._send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def _generate_download_links_html(self, download_links: List[Dict[str, Any]]) -> str:
        """Generate HTML for download links."""
        html_links = []
        for link in download_links:
            html_links.append(f"""
            <div style="margin: 10px 0; padding: 15px; border: 1px solid #e5e7eb; border-radius: 5px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{link['format']}</strong> ({link['size']})
                        <br><small style="color: #666;">Expires: {link['expires']}</small>
                    </div>
                    <a href="{link['url']}" 
                       style="background-color: #2563eb; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                        Download
                    </a>
                </div>
            </div>
            """)
        return "".join(html_links)
    
    def _generate_download_links_text(self, download_links: List[Dict[str, Any]]) -> str:
        """Generate text for download links."""
        text_links = []
        for link in download_links:
            text_links.append(f"- {link['format']} ({link['size']}): {link['url']} (Expires: {link['expires']})")
        return "\n".join(text_links)


class ExportAnalytics:
    """Tracks export analytics and metrics."""
    
    def __init__(self):
        self.metrics = {
            "total_exports": 0,
            "successful_exports": 0,
            "failed_exports": 0,
            "total_processing_time": 0.0,
            "format_usage": {},
            "user_exports": {},
            "hourly_exports": {},
            "daily_exports": {},
            "error_counts": {}
        }
    
    async def record_job_start(self, job: ExportJob) -> None:
        """Record job start metrics."""
        self.metrics["total_exports"] += 1
        
        # Track format usage
        for format in job.formats:
            format_str = format.value
            self.metrics["format_usage"][format_str] = self.metrics["format_usage"].get(format_str, 0) + 1
        
        # Track user exports
        user_str = str(job.user_id)
        self.metrics["user_exports"][user_str] = self.metrics["user_exports"].get(user_str, 0) + 1
        
        # Track hourly exports
        hour_key = job.created_at.strftime("%Y-%m-%d-%H")
        self.metrics["hourly_exports"][hour_key] = self.metrics["hourly_exports"].get(hour_key, 0) + 1
        
        # Track daily exports
        day_key = job.created_at.strftime("%Y-%m-%d")
        self.metrics["daily_exports"][day_key] = self.metrics["daily_exports"].get(day_key, 0) + 1
    
    async def record_job_completion(self, job: ExportJob) -> None:
        """Record job completion metrics."""
        if job.status == ExportJobStatus.COMPLETED:
            self.metrics["successful_exports"] += 1
        elif job.status == ExportJobStatus.FAILED:
            self.metrics["failed_exports"] += 1
            
            # Track error types
            error_type = self._categorize_error(job.error_message)
            self.metrics["error_counts"][error_type] = self.metrics["error_counts"].get(error_type, 0) + 1
        
        # Track processing time
        if job.processing_time_seconds:
            self.metrics["total_processing_time"] += job.processing_time_seconds
    
    def _categorize_error(self, error_message: Optional[str]) -> str:
        """Categorize error message into type."""
        if not error_message:
            return "unknown"
        
        error_lower = error_message.lower()
        if "timeout" in error_lower:
            return "timeout"
        elif "memory" in error_lower or "oom" in error_lower:
            return "memory"
        elif "format" in error_lower:
            return "format"
        elif "quota" in error_lower or "limit" in error_lower:
            return "quota"
        elif "network" in error_lower or "connection" in error_lower:
            return "network"
        else:
            return "processing"
    
    async def get_analytics_report(self) -> Dict[str, Any]:
        """Get comprehensive analytics report."""
        success_rate = 0.0
        if self.metrics["total_exports"] > 0:
            success_rate = self.metrics["successful_exports"] / self.metrics["total_exports"] * 100
        
        avg_processing_time = 0.0
        if self.metrics["successful_exports"] > 0:
            avg_processing_time = self.metrics["total_processing_time"] / self.metrics["successful_exports"]
        
        return {
            "overview": {
                "total_exports": self.metrics["total_exports"],
                "successful_exports": self.metrics["successful_exports"],
                "failed_exports": self.metrics["failed_exports"],
                "success_rate_percent": round(success_rate, 2),
                "average_processing_time_seconds": round(avg_processing_time, 2)
            },
            "format_usage": self.metrics["format_usage"],
            "top_users": dict(sorted(self.metrics["user_exports"].items(), key=lambda x: x[1], reverse=True)[:10]),
            "recent_hourly": dict(sorted(self.metrics["hourly_exports"].items())[-24:]),
            "recent_daily": dict(sorted(self.metrics["daily_exports"].items())[-30:]),
            "error_breakdown": self.metrics["error_counts"]
        }


class ExportQueueManager:
    """
    Comprehensive export queue manager for SlideGenie.
    
    Handles asynchronous processing of large presentations with job queuing,
    email notifications, temporary download links, batch processing, and analytics.
    """
    
    def __init__(
        self,
        task_queue: Optional[TaskQueue] = None,
        storage_path: Optional[Path] = None,
        secret_key: Optional[str] = None
    ):
        """
        Initialize export queue manager.
        
        Args:
            task_queue: Task queue implementation (defaults to ARQ)
            storage_path: Path for temporary file storage
            secret_key: Secret key for secure token generation
        """
        self.task_queue = task_queue or TaskQueue(backend="arq")
        self.export_service = ExportService()
        self.storage_path = storage_path or Path(settings.TEMP_STORAGE_PATH or "/tmp/slidegenie_exports")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.link_manager = TemporaryLinkManager(secret_key or settings.SECRET_KEY)
        self.email_service = EmailNotificationService(EmailValidationService())
        self.analytics = ExportAnalytics()
        
        # In-memory storage (in production, use Redis/database)
        self.jobs: Dict[UUID, ExportJob] = {}
        self.user_quotas: Dict[UUID, ExportQuota] = {}
        self.batch_jobs: Dict[str, List[UUID]] = {}
        
        # Resource management
        self.max_concurrent_jobs = 10
        self.current_jobs = 0
        self.worker_id = f"worker-{uuid4().hex[:8]}"
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the export queue manager."""
        if self._initialized:
            return
        
        try:
            # Initialize task queue
            await self.task_queue.initialize()
            
            # Start background cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_files())
            
            self._initialized = True
            logger.info("Export queue manager initialized", worker_id=self.worker_id)
            
        except Exception as e:
            logger.error("Failed to initialize export queue manager", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the export queue manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        await self.task_queue.shutdown()
        self._initialized = False
        logger.info("Export queue manager shutdown")
    
    async def submit_export_job(
        self,
        request: ExportJobRequest,
        user: User
    ) -> ExportJob:
        """
        Submit new export job for processing.
        
        Args:
            request: Export job request
            user: User submitting the job
            
        Returns:
            Created export job
            
        Raises:
            QuotaExceededError: If user has exceeded export quota
            InvalidRequestError: If request is invalid
        """
        if not self._initialized:
            raise RuntimeError("Export queue manager not initialized")
        
        # Check user quota
        await self._check_user_quota(request.user_id, len(request.formats))
        
        # Validate request
        self._validate_export_request(request)
        
        # Create export job
        job = ExportJob(
            user_id=request.user_id,
            presentation_id=request.presentation_id,
            slides=request.slides,
            formats=request.formats,
            template_config=request.template_config,
            citations=request.citations,
            metadata=request.metadata,
            priority=request.priority,
            notification_email=request.notification_email,
            expiry_hours=request.expiry_hours,
            batch_name=request.batch_name
        )
        
        # Store job
        self.jobs[job.job_id] = job
        
        # Update user quota
        await self._update_user_quota(request.user_id, len(request.formats))
        
        # Record analytics
        await self.analytics.record_job_start(job)
        
        # Queue job for processing
        task_priority = self._convert_priority(job.priority)
        
        await self.task_queue.enqueue_task(
            task_id=str(job.job_id),
            task_data={
                "job_id": str(job.job_id),
                "type": "export_job"
            },
            priority=task_priority,
            queue_name="export_queue"
        )
        
        # Track batch if specified
        if job.batch_name:
            if job.batch_name not in self.batch_jobs:
                self.batch_jobs[job.batch_name] = []
            self.batch_jobs[job.batch_name].append(job.job_id)
        
        logger.info("Export job submitted", 
                   job_id=str(job.job_id), 
                   user_id=str(user.id),
                   formats=len(request.formats),
                   slides=len(request.slides))
        
        # Send WebSocket notification
        await send_user_notification(
            user.id,
            f"Export job {job.job_id} has been queued for processing",
            "info"
        )
        
        return job
    
    async def submit_batch_export(
        self,
        requests: List[ExportJobRequest],
        batch_name: str,
        user: User,
        batch_type: BatchExportType = BatchExportType.MIXED
    ) -> List[ExportJob]:
        """
        Submit multiple export jobs as a batch.
        
        Args:
            requests: List of export job requests
            batch_name: Name for the batch
            user: User submitting the batch
            batch_type: Type of batch export
            
        Returns:
            List of created export jobs
        """
        if not requests:
            raise InvalidRequestError("No export requests provided")
        
        if len(requests) > 20:
            raise InvalidRequestError("Maximum 20 jobs allowed per batch")
        
        # Calculate total quota needed
        total_formats = sum(len(req.formats) for req in requests)
        await self._check_user_quota(user.id, total_formats)
        
        # Set batch name on all requests
        for req in requests:
            req.batch_name = batch_name
        
        # Submit all jobs
        jobs = []
        for req in requests:
            try:
                job = await self.submit_export_job(req, user)
                jobs.append(job)
            except Exception as e:
                logger.error("Failed to submit batch job", 
                           error=str(e), 
                           batch_name=batch_name,
                           request_index=len(jobs))
                # Continue with other jobs
        
        if not jobs:
            raise ExportError("Failed to submit any jobs in batch")
        
        logger.info("Batch export submitted", 
                   batch_name=batch_name,
                   jobs_count=len(jobs),
                   batch_type=batch_type.value)
        
        return jobs
    
    async def process_export_job(self, job_id: UUID) -> None:
        """
        Process an export job.
        
        Args:
            job_id: ID of job to process
        """
        if job_id not in self.jobs:
            logger.error("Job not found", job_id=str(job_id))
            return
        
        job = self.jobs[job_id]
        
        try:
            # Check if we can process more jobs
            if self.current_jobs >= self.max_concurrent_jobs:
                logger.info("Max concurrent jobs reached, requeueing", job_id=str(job_id))
                await asyncio.sleep(5)  # Brief delay before retry
                await self.task_queue.enqueue_task(
                    task_id=str(job_id),
                    task_data={"job_id": str(job_id), "type": "export_job"},
                    priority=self._convert_priority(job.priority),
                    delay_seconds=30,
                    queue_name="export_queue"
                )
                return
            
            # Start processing
            self.current_jobs += 1
            job.status = ExportJobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            job.queue_time_seconds = (job.started_at - job.created_at).total_seconds()
            job.worker_id = self.worker_id
            
            logger.info("Starting export job processing", job_id=str(job_id))
            
            # Send progress update
            await self._update_job_progress(job, 10, "Initializing export")
            
            # Process each format
            results = []
            formats_completed = 0
            
            for format in job.formats:
                try:
                    await self._update_job_progress(
                        job, 
                        10 + (formats_completed * 80 // len(job.formats)), 
                        f"Exporting to {format.value.upper()}"
                    )
                    
                    # Export to format
                    result = await self._export_format(job, format)
                    results.append(result)
                    
                    formats_completed += 1
                    
                except Exception as e:
                    logger.error("Format export failed", 
                               job_id=str(job_id), 
                               format=format.value, 
                               error=str(e))
                    job.error_message = f"Failed to export {format.value}: {str(e)}"
                    raise
            
            # Finalize job
            await self._update_job_progress(job, 90, "Finalizing export")
            
            job.results = results
            job.total_size = sum(r.file_size for r in results)
            job.status = ExportJobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.processing_time_seconds = (job.completed_at - job.started_at).total_seconds()
            
            await self._update_job_progress(job, 100, "Export completed")
            
            # Send completion notification
            if job.notification_email:
                # Get user for notification
                from app.repositories.user import UserRepository
                user_repo = UserRepository()
                user = await user_repo.get_by_id(job.user_id)
                
                if user:
                    await self.email_service.send_completion_notification(job, user, results)
            
            logger.info("Export job completed successfully", 
                       job_id=str(job_id),
                       processing_time=job.processing_time_seconds,
                       total_size=job.total_size)
            
        except Exception as e:
            # Handle job failure
            job.status = ExportJobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            
            if job.started_at:
                job.processing_time_seconds = (job.completed_at - job.started_at).total_seconds()
            
            logger.error("Export job failed", 
                        job_id=str(job_id), 
                        error=str(e),
                        retry_count=job.retry_count)
            
            # Retry logic
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = ExportJobStatus.QUEUED
                
                # Exponential backoff
                delay_seconds = min(300, 30 * (2 ** job.retry_count))
                
                await self.task_queue.enqueue_task(
                    task_id=str(job_id),
                    task_data={"job_id": str(job_id), "type": "export_job"},
                    priority=self._convert_priority(job.priority),
                    delay_seconds=delay_seconds,
                    queue_name="export_queue"
                )
                
                logger.info("Export job scheduled for retry", 
                           job_id=str(job_id),
                           retry_count=job.retry_count,
                           delay_seconds=delay_seconds)
            else:
                # Send failure notification
                if job.notification_email:
                    from app.repositories.user import UserRepository
                    user_repo = UserRepository()
                    user = await user_repo.get_by_id(job.user_id)
                    
                    if user:
                        await self.email_service.send_completion_notification(job, user, [])
        
        finally:
            self.current_jobs = max(0, self.current_jobs - 1)
            
            # Record analytics
            await self.analytics.record_job_completion(job)
    
    async def _export_format(self, job: ExportJob, format: ExportFormat) -> ExportJobResult:
        """Export job to specific format."""
        try:
            # Generate output filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{job.job_id}_{timestamp}.{format.value}"
            output_path = self.storage_path / filename
            
            # Export presentation
            result_path = self.export_service.export_presentation(
                slides=job.slides,
                format=format,
                template_config=job.template_config,
                citations=job.citations,
                metadata=job.metadata,
                output_path=str(output_path)
            )
            
            # Get file info
            file_size = output_path.stat().st_size
            
            # Calculate checksum
            checksum = await self._calculate_file_checksum(output_path)
            
            # Generate download URL
            expires_at = datetime.utcnow() + timedelta(hours=job.expiry_hours)
            download_url = self.link_manager.generate_download_url(
                job.job_id, format.value, expires_at
            )
            
            return ExportJobResult(
                job_id=job.job_id,
                format=format,
                file_size=file_size,
                file_path=str(output_path),
                download_url=download_url,
                expires_at=expires_at,
                checksum=checksum,
                metadata={
                    "created_at": datetime.utcnow().isoformat(),
                    "worker_id": self.worker_id
                }
            )
            
        except Exception as e:
            logger.error("Failed to export format", 
                        job_id=str(job.job_id), 
                        format=format.value, 
                        error=str(e))
            raise ExportError(f"Export to {format.value} failed: {str(e)}")
    
    async def get_job_status(self, job_id: UUID) -> Optional[ExportJob]:
        """Get job status."""
        return self.jobs.get(job_id)
    
    async def cancel_job(self, job_id: UUID, user_id: UUID) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job ID to cancel
            user_id: User ID requesting cancellation
            
        Returns:
            True if cancelled successfully
        """
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        # Check ownership
        if job.user_id != user_id:
            return False
        
        # Can only cancel queued jobs
        if job.status not in [ExportJobStatus.QUEUED]:
            return False
        
        # Cancel task in queue
        await self.task_queue.cancel_task(str(job_id))
        
        # Update job status
        job.status = ExportJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        
        logger.info("Export job cancelled", job_id=str(job_id), user_id=str(user_id))
        
        # Send notification
        await send_user_notification(
            user_id,
            f"Export job {job_id} has been cancelled",
            "info"
        )
        
        return True
    
    async def get_user_jobs(
        self,
        user_id: UUID,
        status: Optional[ExportJobStatus] = None,
        limit: int = 50
    ) -> List[ExportJob]:
        """Get user's export jobs."""
        user_jobs = [
            job for job in self.jobs.values()
            if job.user_id == user_id
        ]
        
        # Filter by status
        if status:
            user_jobs = [job for job in user_jobs if job.status == status]
        
        # Sort by creation time (newest first)
        user_jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return user_jobs[:limit]
    
    async def get_batch_status(self, batch_name: str) -> Dict[str, Any]:
        """Get status of batch export."""
        if batch_name not in self.batch_jobs:
            return {"error": "Batch not found"}
        
        job_ids = self.batch_jobs[batch_name]
        jobs = [self.jobs[jid] for jid in job_ids if jid in self.jobs]
        
        if not jobs:
            return {"error": "No jobs found in batch"}
        
        # Calculate batch statistics
        total_jobs = len(jobs)
        completed_jobs = len([j for j in jobs if j.status == ExportJobStatus.COMPLETED])
        failed_jobs = len([j for j in jobs if j.status == ExportJobStatus.FAILED])
        processing_jobs = len([j for j in jobs if j.status == ExportJobStatus.PROCESSING])
        queued_jobs = len([j for j in jobs if j.status == ExportJobStatus.QUEUED])
        
        total_progress = sum(j.progress_percent for j in jobs) / total_jobs if total_jobs > 0 else 0
        
        return {
            "batch_name": batch_name,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "processing_jobs": processing_jobs,
            "queued_jobs": queued_jobs,
            "overall_progress": round(total_progress, 1),
            "jobs": [
                {
                    "job_id": str(job.job_id),
                    "status": job.status,
                    "progress": job.progress_percent,
                    "current_stage": job.current_stage,
                    "created_at": job.created_at,
                    "error_message": job.error_message
                }
                for job in jobs
            ]
        }
    
    async def download_file(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Download file using secure token.
        
        Args:
            token: Secure download token
            
        Returns:
            File info if valid, None otherwise
        """
        # Verify token
        token_data = self.link_manager.verify_token(token)
        if not token_data:
            return None
        
        job_id = UUID(token_data["job_id"])
        format_str = token_data["format"]
        
        # Get job
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        # Find result for format
        result = None
        for r in job.results:
            if r.format.value == format_str:
                result = r
                break
        
        if not result:
            return None
        
        # Check if file exists
        file_path = Path(result.file_path)
        if not file_path.exists():
            return None
        
        # Return file info
        return {
            "file_path": str(file_path),
            "filename": f"presentation_{job_id}.{format_str}",
            "content_type": self._get_content_type(format_str),
            "file_size": result.file_size,
            "checksum": result.checksum
        }
    
    async def get_queue_metrics(self) -> Dict[str, Any]:
        """Get export queue metrics."""
        queue_metrics = await self.task_queue.get_metrics()
        
        # Job status counts
        status_counts = {}
        for status in ExportJobStatus:
            status_counts[status.value] = len([
                j for j in self.jobs.values() if j.status == status
            ])
        
        # Resource usage
        resource_usage = {
            "current_concurrent_jobs": self.current_jobs,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "total_jobs": len(self.jobs),
            "active_batches": len(self.batch_jobs),
            "storage_used_bytes": await self._calculate_storage_usage()
        }
        
        return {
            "queue_metrics": queue_metrics.dict(),
            "job_status_counts": status_counts,
            "resource_usage": resource_usage,
            "worker_id": self.worker_id
        }
    
    async def get_analytics_report(self) -> Dict[str, Any]:
        """Get comprehensive analytics report."""
        return await self.analytics.get_analytics_report()
    
    # Private helper methods
    
    async def _check_user_quota(self, user_id: UUID, formats_count: int) -> None:
        """Check if user has sufficient quota."""
        if user_id not in self.user_quotas:
            self.user_quotas[user_id] = ExportQuota(user_id=user_id)
        
        quota = self.user_quotas[user_id]
        
        # Reset counters if needed
        now = datetime.utcnow()
        if now >= quota.daily_reset_at:
            quota.daily_exports = 0
            quota.daily_reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        if now >= quota.monthly_reset_at:
            quota.monthly_exports = 0
            next_month = now.replace(day=1) + timedelta(days=32)
            quota.monthly_reset_at = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Check limits
        if quota.daily_exports + formats_count > quota.daily_limit:
            raise QuotaExceededError(f"Daily export limit exceeded ({quota.daily_limit})")
        
        if quota.monthly_exports + formats_count > quota.monthly_limit:
            raise QuotaExceededError(f"Monthly export limit exceeded ({quota.monthly_limit})")
    
    async def _update_user_quota(self, user_id: UUID, formats_count: int) -> None:
        """Update user quota after successful submission."""
        if user_id in self.user_quotas:
            quota = self.user_quotas[user_id]
            quota.daily_exports += formats_count
            quota.monthly_exports += formats_count
    
    def _validate_export_request(self, request: ExportJobRequest) -> None:
        """Validate export request."""
        # Validate export service can handle the request
        try:
            self.export_service.validate_export_request(
                slides=request.slides,
                format=request.formats[0],  # Use first format for validation
                template_config=request.template_config
            )
        except Exception as e:
            raise InvalidRequestError(f"Invalid export request: {str(e)}")
    
    def _convert_priority(self, priority: ExportJobPriority) -> TaskPriority:
        """Convert export priority to task priority."""
        mapping = {
            ExportJobPriority.LOW: TaskPriority.LOW,
            ExportJobPriority.NORMAL: TaskPriority.NORMAL,
            ExportJobPriority.HIGH: TaskPriority.HIGH,
            ExportJobPriority.URGENT: TaskPriority.CRITICAL
        }
        return mapping.get(priority, TaskPriority.NORMAL)
    
    async def _update_job_progress(self, job: ExportJob, progress: float, stage: str) -> None:
        """Update job progress and notify via WebSocket."""
        job.progress_percent = progress
        job.current_stage = stage
        
        # Send WebSocket update
        await broadcast_job_progress(job.job_id, {
            "job_id": str(job.job_id),
            "status": job.status.value,
            "progress_percent": progress,
            "current_stage": stage,
            "updated_at": datetime.utcnow().isoformat()
        })
    
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def _get_content_type(self, format_str: str) -> str:
        """Get content type for format."""
        content_types = {
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "pdf": "application/pdf",
            "html": "text/html",
            "json": "application/json"
        }
        return content_types.get(format_str, "application/octet-stream")
    
    async def _calculate_storage_usage(self) -> int:
        """Calculate total storage usage."""
        total_size = 0
        for result in [r for job in self.jobs.values() for r in job.results]:
            file_path = Path(result.file_path)
            if file_path.exists():
                total_size += file_path.stat().st_size
        return total_size
    
    async def _cleanup_expired_files(self) -> None:
        """Background task to clean up expired files."""
        while True:
            try:
                now = datetime.utcnow()
                
                # Find expired results
                expired_results = []
                for job in self.jobs.values():
                    for result in job.results:
                        if now > result.expires_at:
                            expired_results.append(result)
                
                # Delete expired files
                for result in expired_results:
                    try:
                        file_path = Path(result.file_path)
                        if file_path.exists():
                            file_path.unlink()
                            logger.info("Deleted expired file", file_path=str(file_path))
                    except Exception as e:
                        logger.error("Failed to delete expired file", 
                                   file_path=result.file_path, 
                                   error=str(e))
                
                # Clean up old jobs (older than 30 days)
                cutoff_date = now - timedelta(days=30)
                old_job_ids = [
                    job_id for job_id, job in self.jobs.items()
                    if job.created_at < cutoff_date
                ]
                
                for job_id in old_job_ids:
                    del self.jobs[job_id]
                    logger.info("Cleaned up old job", job_id=str(job_id))
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error("Error in cleanup task", error=str(e))
                await asyncio.sleep(3600)


# Worker function for processing export jobs
async def process_export_job_worker(export_manager: ExportQueueManager) -> None:
    """Worker function to process export jobs from queue."""
    while True:
        try:
            # Dequeue next job
            task_data = await export_manager.task_queue.dequeue_task("export_queue")
            
            if task_data:
                job_id = UUID(task_data["job_id"])
                await export_manager.process_export_job(job_id)
            else:
                # No jobs available, wait
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error("Error in export job worker", error=str(e))
            await asyncio.sleep(5)


# Convenience functions for common operations

async def create_export_queue_manager(
    task_queue_backend: str = "arq",
    storage_path: Optional[str] = None,
    secret_key: Optional[str] = None
) -> ExportQueueManager:
    """Create and initialize export queue manager."""
    task_queue = TaskQueue(backend=task_queue_backend)
    storage_path_obj = Path(storage_path) if storage_path else None
    
    manager = ExportQueueManager(
        task_queue=task_queue,
        storage_path=storage_path_obj,
        secret_key=secret_key
    )
    
    await manager.initialize()
    return manager


async def submit_single_export(
    slides: List[SlideContent],
    formats: List[ExportFormat],
    user: User,
    template_config: Optional[Dict[str, Any]] = None,
    notification_email: Optional[str] = None,
    priority: ExportJobPriority = ExportJobPriority.NORMAL
) -> ExportJob:
    """Convenience function to submit single export job."""
    manager = await create_export_queue_manager()
    
    request = ExportJobRequest(
        user_id=user.id,
        slides=slides,
        formats=formats,
        template_config=template_config or {},
        priority=priority,
        notification_email=notification_email
    )
    
    return await manager.submit_export_job(request, user)


async def submit_multi_format_export(
    slides: List[SlideContent],
    formats: List[ExportFormat],
    user: User,
    template_config: Optional[Dict[str, Any]] = None,
    batch_name: Optional[str] = None
) -> ExportJob:
    """Export single presentation to multiple formats."""
    manager = await create_export_queue_manager()
    
    request = ExportJobRequest(
        user_id=user.id,
        slides=slides,
        formats=formats,
        template_config=template_config or {},
        batch_name=batch_name or f"multi_format_{uuid4().hex[:8]}"
    )
    
    return await manager.submit_export_job(request, user)