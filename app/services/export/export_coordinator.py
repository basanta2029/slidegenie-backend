"""
Comprehensive export coordinator for orchestrating all export formats and managing
the complete export pipeline.

This module provides:
- Format orchestration across PowerPoint, LaTeX Beamer, PDF, and Google Slides
- Unified progress tracking and status management
- Error recovery with format-specific fallback strategies
- Resource management and load balancing
- Export validation and quality assurance
- Template consistency across formats
- Configuration management for export preferences
"""

import asyncio
import io
import json
import logging
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from uuid import UUID

from app.core.logging import get_logger
from app.domain.schemas.generation import Citation, SlideContent
from app.services.export.generators.pptx_generator import PPTXGenerator, AcademicTemplate
from app.services.export.generators.beamer_generator import BeamerGenerator, BeamerTheme
from app.services.export.generators.pdf_generator import PDFGenerator
from app.services.export.generators.google_slides_generator import GoogleSlidesGenerator

logger = get_logger(__name__)


class ExportFormat(Enum):
    """Supported export formats with metadata."""
    PPTX = {"name": "PowerPoint", "extension": ".pptx", "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
    BEAMER = {"name": "LaTeX Beamer", "extension": ".tex", "mime_type": "application/x-latex"}
    PDF = {"name": "PDF", "extension": ".pdf", "mime_type": "application/pdf"}
    GOOGLE_SLIDES = {"name": "Google Slides", "extension": ".gslides", "mime_type": "application/vnd.google-apps.presentation"}


class ExportStatus(Enum):
    """Export job status values."""
    PENDING = "pending"
    PREPARING = "preparing"
    GENERATING = "generating"
    VALIDATING = "validating"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportPriority(Enum):
    """Export job priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class ExportQuality(Enum):
    """Export quality levels."""
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    PREMIUM = "premium"


@dataclass
class ExportProgress:
    """Progress tracking for export operations."""
    job_id: str
    format: ExportFormat
    status: ExportStatus
    progress_percent: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Result of an export operation."""
    job_id: str
    format: ExportFormat
    status: ExportStatus
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    buffer: Optional[io.BytesIO] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_size: Optional[int] = None
    download_expires: Optional[datetime] = None
    sharing_urls: Dict[str, str] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportConfig:
    """Configuration for export operations."""
    format: ExportFormat
    template_name: str = "default"
    quality: ExportQuality = ExportQuality.STANDARD
    priority: ExportPriority = ExportPriority.NORMAL
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    branding: Dict[str, Any] = field(default_factory=dict)
    output_options: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    fallback_formats: List[ExportFormat] = field(default_factory=list)


@dataclass
class ExportJob:
    """Export job definition."""
    job_id: str
    slides: List[SlideContent]
    config: ExportConfig
    citations: Optional[List[Citation]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    callback_url: Optional[str] = None
    progress: ExportProgress = None
    
    def __post_init__(self):
        if self.progress is None:
            self.progress = ExportProgress(
                job_id=self.job_id,
                format=self.config.format,
                status=ExportStatus.PENDING
            )


class ResourceManager:
    """Manages resources and load balancing for export operations."""
    
    def __init__(self, max_concurrent_exports: int = 5):
        self.max_concurrent_exports = max_concurrent_exports
        self._active_jobs: Dict[str, ExportJob] = {}
        self._resource_usage: Dict[ExportFormat, int] = {fmt: 0 for fmt in ExportFormat}
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_exports)
        self._lock = asyncio.Lock()
    
    async def can_start_export(self, format: ExportFormat) -> bool:
        """Check if export can be started based on resource availability."""
        async with self._lock:
            active_count = len(self._active_jobs)
            format_count = self._resource_usage.get(format, 0)
            
            # Global limit
            if active_count >= self.max_concurrent_exports:
                return False
            
            # Format-specific limits
            format_limits = {
                ExportFormat.GOOGLE_SLIDES: 2,  # API rate limits
                ExportFormat.BEAMER: 3,  # LaTeX compilation
                ExportFormat.PDF: 4,  # PDF generation
                ExportFormat.PPTX: 5   # Lightweight
            }
            
            return format_count < format_limits.get(format, 3)
    
    async def allocate_resources(self, job: ExportJob) -> bool:
        """Allocate resources for an export job."""
        async with self._lock:
            if await self.can_start_export(job.config.format):
                self._active_jobs[job.job_id] = job
                self._resource_usage[job.config.format] += 1
                return True
            return False
    
    async def release_resources(self, job_id: str):
        """Release resources for a completed job."""
        async with self._lock:
            if job_id in self._active_jobs:
                job = self._active_jobs.pop(job_id)
                self._resource_usage[job.config.format] -= 1
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get current resource usage statistics."""
        return {
            "active_jobs": len(self._active_jobs),
            "max_concurrent": self.max_concurrent_exports,
            "format_usage": dict(self._resource_usage),
            "available_slots": self.max_concurrent_exports - len(self._active_jobs)
        }


class ExportValidator:
    """Validates export results and ensures quality."""
    
    @staticmethod
    async def validate_slides(slides: List[SlideContent]) -> Dict[str, Any]:
        """Validate slide content before export."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        if not slides:
            validation_result["valid"] = False
            validation_result["errors"].append("No slides provided")
            return validation_result
        
        # Content validation
        for i, slide in enumerate(slides):
            slide_num = i + 1
            
            if not slide.title and not slide.body:
                validation_result["errors"].append(
                    f"Slide {slide_num}: No title or content"
                )
            
            if slide.title and len(slide.title) > 200:
                validation_result["warnings"].append(
                    f"Slide {slide_num}: Title too long ({len(slide.title)} chars)"
                )
            
            # Validate body content
            for j, item in enumerate(slide.body):
                if not isinstance(item, dict) or 'type' not in item:
                    validation_result["errors"].append(
                        f"Slide {slide_num}, item {j+1}: Invalid content structure"
                    )
        
        # Statistics
        validation_result["statistics"] = {
            "total_slides": len(slides),
            "slides_with_titles": sum(1 for s in slides if s.title),
            "slides_with_content": sum(1 for s in slides if s.body),
            "total_content_items": sum(len(s.body) for s in slides)
        }
        
        validation_result["valid"] = len(validation_result["errors"]) == 0
        return validation_result
    
    @staticmethod
    async def validate_export_result(
        result: ExportResult, 
        validation_rules: List[str]
    ) -> Dict[str, Any]:
        """Validate export result quality."""
        validation_result = {
            "valid": True,
            "score": 0.0,
            "checks": {},
            "recommendations": []
        }
        
        checks = validation_result["checks"]
        
        # File existence check
        if result.file_path and Path(result.file_path).exists():
            checks["file_exists"] = True
            file_size = Path(result.file_path).stat().st_size
            checks["file_size"] = file_size
            
            if file_size > 0:
                checks["file_not_empty"] = True
            else:
                checks["file_not_empty"] = False
                validation_result["valid"] = False
        elif result.buffer:
            checks["buffer_exists"] = True
            buffer_size = len(result.buffer.getvalue())
            checks["buffer_size"] = buffer_size
            checks["buffer_not_empty"] = buffer_size > 0
        else:
            checks["output_exists"] = False
            validation_result["valid"] = False
        
        # Format-specific validation
        if result.format == ExportFormat.PPTX:
            await ExportValidator._validate_pptx_result(result, checks)
        elif result.format == ExportFormat.PDF:
            await ExportValidator._validate_pdf_result(result, checks)
        elif result.format == ExportFormat.BEAMER:
            await ExportValidator._validate_beamer_result(result, checks)
        elif result.format == ExportFormat.GOOGLE_SLIDES:
            await ExportValidator._validate_google_slides_result(result, checks)
        
        # Calculate overall score
        total_checks = len(checks)
        passed_checks = sum(1 for v in checks.values() if v is True)
        validation_result["score"] = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        return validation_result
    
    @staticmethod
    async def _validate_pptx_result(result: ExportResult, checks: Dict[str, Any]):
        """Validate PPTX-specific result."""
        if result.file_path:
            file_path = Path(result.file_path)
            checks["correct_extension"] = file_path.suffix.lower() == ".pptx"
            
            # Try to verify it's a valid PPTX file
            try:
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    files = zip_file.namelist()
                    checks["valid_pptx_structure"] = any(
                        f.startswith('ppt/') for f in files
                    )
            except Exception:
                checks["valid_pptx_structure"] = False
    
    @staticmethod
    async def _validate_pdf_result(result: ExportResult, checks: Dict[str, Any]):
        """Validate PDF-specific result."""
        if result.file_path:
            file_path = Path(result.file_path)
            checks["correct_extension"] = file_path.suffix.lower() == ".pdf"
            
            # Check PDF header
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(8)
                    checks["valid_pdf_header"] = header.startswith(b'%PDF-')
            except Exception:
                checks["valid_pdf_header"] = False
    
    @staticmethod
    async def _validate_beamer_result(result: ExportResult, checks: Dict[str, Any]):
        """Validate Beamer LaTeX-specific result."""
        if result.file_path:
            file_path = Path(result.file_path)
            checks["correct_extension"] = file_path.suffix.lower() == ".tex"
            
            # Check for Beamer document class
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # Check first 1000 chars
                    checks["has_beamer_class"] = "\\documentclass" in content and "beamer" in content
                    checks["has_begin_document"] = "\\begin{document}" in content
            except Exception:
                checks["has_beamer_class"] = False
                checks["has_begin_document"] = False
    
    @staticmethod
    async def _validate_google_slides_result(result: ExportResult, checks: Dict[str, Any]):
        """Validate Google Slides-specific result."""
        checks["has_sharing_url"] = bool(result.sharing_urls.get("view"))
        checks["has_file_id"] = bool(result.metadata.get("file_id"))
        checks["upload_successful"] = result.status == ExportStatus.COMPLETED


class ExportCoordinator:
    """
    Central coordinator for all export operations.
    
    Manages the complete export pipeline including format orchestration,
    progress tracking, error recovery, resource management, and quality assurance.
    """
    
    def __init__(self, max_concurrent_exports: int = 5):
        self.logger = get_logger(self.__class__.__name__)
        self.resource_manager = ResourceManager(max_concurrent_exports)
        self.validator = ExportValidator()
        
        # Active jobs tracking
        self._jobs: Dict[str, ExportJob] = {}
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        self._completion_callbacks: Dict[str, List[Callable]] = {}
        
        # Export generators
        self._generators = {}
        self._initialize_generators()
        
        # Template configurations
        self._template_configs = self._load_template_configs()
        
        # Statistics
        self._stats = {
            "total_exports": 0,
            "successful_exports": 0,
            "failed_exports": 0,
            "exports_by_format": {fmt: 0 for fmt in ExportFormat},
            "average_processing_time": {},
            "start_time": datetime.now()
        }
    
    def _initialize_generators(self):
        """Initialize format-specific generators."""
        self._generators = {
            ExportFormat.PPTX: PPTXGenerator,
            ExportFormat.BEAMER: BeamerGenerator,
            ExportFormat.PDF: PDFGenerator,
            ExportFormat.GOOGLE_SLIDES: GoogleSlidesGenerator
        }
    
    def _load_template_configs(self) -> Dict[ExportFormat, Dict[str, Any]]:
        """Load template configurations for all formats."""
        return {
            ExportFormat.PPTX: {
                "ieee": {"template": AcademicTemplate.IEEE, "colors": {"primary": "#003f7f"}},
                "acm": {"template": AcademicTemplate.ACM, "colors": {"primary": "#0066cc"}},
                "nature": {"template": AcademicTemplate.NATURE, "colors": {"primary": "#006633"}},
                "mit": {"template": AcademicTemplate.MIT, "colors": {"primary": "#8c1515"}}
            },
            ExportFormat.BEAMER: {
                "berlin": {"theme": BeamerTheme.BERLIN, "color_theme": "default"},
                "madrid": {"theme": BeamerTheme.MADRID, "color_theme": "whale"},
                "warsaw": {"theme": BeamerTheme.WARSAW, "color_theme": "orchid"}
            },
            ExportFormat.PDF: {
                "standard": {"quality": "high", "compression": "moderate"},
                "presentation": {"quality": "premium", "compression": "low"},
                "handout": {"quality": "standard", "compression": "high"}
            },
            ExportFormat.GOOGLE_SLIDES: {
                "academic": {"theme": "academic", "layout": "standard"},
                "corporate": {"theme": "corporate", "layout": "professional"},
                "creative": {"theme": "creative", "layout": "dynamic"}
            }
        }
    
    async def submit_export_job(
        self,
        slides: List[SlideContent],
        config: ExportConfig,
        citations: Optional[List[Citation]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> str:
        """
        Submit a new export job.
        
        Args:
            slides: Slide content to export
            config: Export configuration
            citations: Optional citations
            metadata: Optional metadata
            user_id: Optional user ID
            callback_url: Optional callback URL for completion notification
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        # Validate input
        validation_result = await self.validator.validate_slides(slides)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid slides: {', '.join(validation_result['errors'])}")
        
        # Create job
        job = ExportJob(
            job_id=job_id,
            slides=slides,
            config=config,
            citations=citations,
            metadata=metadata or {},
            user_id=user_id,
            callback_url=callback_url
        )
        
        self._jobs[job_id] = job
        self.logger.info(f"Export job {job_id} submitted for format {config.format.name}")
        
        # Start processing asynchronously
        asyncio.create_task(self._process_export_job(job))
        
        return job_id
    
    async def _process_export_job(self, job: ExportJob):
        """Process an export job through the complete pipeline."""
        job_id = job.job_id
        
        try:
            # Wait for resource allocation
            await self._wait_for_resources(job)
            
            # Update progress
            await self._update_progress(job, ExportStatus.PREPARING, "Preparing export")
            
            # Generate export
            result = await self._generate_export(job)
            
            # Validate result
            await self._update_progress(job, ExportStatus.VALIDATING, "Validating export")
            validation_result = await self.validator.validate_export_result(
                result, job.config.validation_rules
            )
            result.validation_results = validation_result
            
            # Finalize
            await self._update_progress(job, ExportStatus.FINALIZING, "Finalizing export")
            await self._finalize_export(job, result)
            
            # Complete
            await self._complete_export(job, result)
            
        except Exception as e:
            self.logger.error(f"Export job {job_id} failed: {e}")
            await self._handle_export_error(job, e)
        finally:
            await self.resource_manager.release_resources(job_id)
    
    async def _wait_for_resources(self, job: ExportJob):
        """Wait for resource allocation with timeout."""
        timeout = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.resource_manager.allocate_resources(job):
                return
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Resource allocation timeout for job {job.job_id}")
    
    async def _generate_export(self, job: ExportJob) -> ExportResult:
        """Generate export using appropriate generator."""
        await self._update_progress(job, ExportStatus.GENERATING, "Generating export")
        
        format = job.config.format
        generator_class = self._generators.get(format)
        
        if not generator_class:
            raise ValueError(f"No generator available for format {format.name}")
        
        # Create generator with configuration
        generator_config = self._create_generator_config(job)
        generator = generator_class(generator_config)
        
        # Generate export
        start_time = time.time()
        
        try:
            if format == ExportFormat.GOOGLE_SLIDES:
                # Google Slides returns URL and metadata
                result_data = await self._generate_google_slides(generator, job)
                result = ExportResult(
                    job_id=job.job_id,
                    format=format,
                    status=ExportStatus.COMPLETED,
                    file_url=result_data.get("url"),
                    sharing_urls=result_data.get("sharing_urls", {}),
                    metadata=result_data.get("metadata", {})
                )
            else:
                # Other formats return file or buffer
                output = await self._generate_file_export(generator, job)
                result = ExportResult(
                    job_id=job.job_id,
                    format=format,
                    status=ExportStatus.COMPLETED,
                    file_path=output.get("file_path"),
                    buffer=output.get("buffer"),
                    file_size=output.get("file_size"),
                    metadata=output.get("metadata", {})
                )
            
            # Record processing time
            processing_time = time.time() - start_time
            self._record_processing_time(format, processing_time)
            
            return result
            
        except Exception as e:
            # Try fallback formats
            if job.config.fallback_formats:
                self.logger.warning(f"Primary format {format.name} failed, trying fallbacks")
                return await self._try_fallback_formats(job, e)
            raise
    
    async def _generate_google_slides(self, generator, job: ExportJob) -> Dict[str, Any]:
        """Generate Google Slides export."""
        # This would interface with the Google Slides generator
        return await generator.create_presentation(
            slides=job.slides,
            citations=job.citations,
            metadata=job.metadata
        )
    
    async def _generate_file_export(self, generator, job: ExportJob) -> Dict[str, Any]:
        """Generate file-based export (PPTX, PDF, Beamer)."""
        if hasattr(generator, 'export_to_buffer'):
            buffer = await generator.export_to_buffer(
                slides=job.slides,
                citations=job.citations,
                metadata=job.metadata
            )
            return {
                "buffer": buffer,
                "file_size": len(buffer.getvalue()) if buffer else 0
            }
        else:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=job.config.format.value["extension"],
                delete=False
            ) as tmp_file:
                tmp_path = tmp_file.name
            
            await generator.export_to_file(
                slides=job.slides,
                output_path=tmp_path,
                citations=job.citations,
                metadata=job.metadata
            )
            
            file_size = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
            
            return {
                "file_path": tmp_path,
                "file_size": file_size
            }
    
    async def _try_fallback_formats(self, job: ExportJob, original_error: Exception) -> ExportResult:
        """Try fallback formats when primary format fails."""
        for fallback_format in job.config.fallback_formats:
            try:
                self.logger.info(f"Trying fallback format {fallback_format.name}")
                
                # Create new job with fallback format
                fallback_job = ExportJob(
                    job_id=job.job_id,
                    slides=job.slides,
                    config=ExportConfig(
                        format=fallback_format,
                        template_name=job.config.template_name,
                        quality=job.config.quality,
                        custom_settings=job.config.custom_settings
                    ),
                    citations=job.citations,
                    metadata=job.metadata
                )
                
                return await self._generate_export(fallback_job)
                
            except Exception as e:
                self.logger.warning(f"Fallback format {fallback_format.name} also failed: {e}")
                continue
        
        # All fallbacks failed
        raise original_error
    
    def _create_generator_config(self, job: ExportJob) -> Dict[str, Any]:
        """Create generator-specific configuration."""
        base_config = {
            "template": job.config.template_name,
            "quality": job.config.quality.value,
            **job.config.custom_settings
        }
        
        # Add format-specific template config
        format_templates = self._template_configs.get(job.config.format, {})
        template_config = format_templates.get(job.config.template_name, {})
        base_config.update(template_config)
        
        # Add branding
        if job.config.branding:
            base_config["branding"] = job.config.branding
        
        return base_config
    
    async def _finalize_export(self, job: ExportJob, result: ExportResult):
        """Finalize export (cleanup, file management, etc.)."""
        # Set download expiration
        if result.file_path or result.buffer:
            result.download_expires = datetime.now() + timedelta(hours=24)
        
        # Update file size in result
        if result.file_path and Path(result.file_path).exists():
            result.file_size = Path(result.file_path).stat().st_size
    
    async def _complete_export(self, job: ExportJob, result: ExportResult):
        """Complete export job successfully."""
        await self._update_progress(job, ExportStatus.COMPLETED, "Export completed")
        
        # Update statistics
        self._stats["successful_exports"] += 1
        self._stats["exports_by_format"][job.config.format] += 1
        
        # Store result
        job.result = result
        
        # Call completion callbacks
        callbacks = self._completion_callbacks.get(job.job_id, [])
        for callback in callbacks:
            try:
                await callback(job, result)
            except Exception as e:
                self.logger.error(f"Completion callback failed: {e}")
        
        self.logger.info(f"Export job {job.job_id} completed successfully")
    
    async def _handle_export_error(self, job: ExportJob, error: Exception):
        """Handle export job error."""
        await self._update_progress(
            job, 
            ExportStatus.FAILED, 
            f"Export failed: {str(error)}",
            error_message=str(error)
        )
        
        # Update statistics
        self._stats["failed_exports"] += 1
        
        self.logger.error(f"Export job {job.job_id} failed: {error}")
    
    async def _update_progress(
        self,
        job: ExportJob,
        status: ExportStatus,
        message: str,
        progress_percent: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Update job progress."""
        job.progress.status = status
        job.progress.current_step = message
        
        if progress_percent is not None:
            job.progress.progress_percent = progress_percent
        else:
            # Auto-calculate progress based on status
            status_progress = {
                ExportStatus.PENDING: 0,
                ExportStatus.PREPARING: 10,
                ExportStatus.GENERATING: 50,
                ExportStatus.VALIDATING: 80,
                ExportStatus.FINALIZING: 90,
                ExportStatus.COMPLETED: 100,
                ExportStatus.FAILED: 0
            }
            job.progress.progress_percent = status_progress.get(status, 0)
        
        if error_message:
            job.progress.error_message = error_message
        
        # Update estimated completion
        if status == ExportStatus.GENERATING:
            estimated_time = self._estimate_completion_time(job)
            job.progress.estimated_completion = datetime.now() + timedelta(seconds=estimated_time)
        
        # Call progress callbacks
        callbacks = self._progress_callbacks.get(job.job_id, [])
        for callback in callbacks:
            try:
                await callback(job.progress)
            except Exception as e:
                self.logger.error(f"Progress callback failed: {e}")
    
    def _estimate_completion_time(self, job: ExportJob) -> float:
        """Estimate completion time for a job."""
        format = job.config.format
        slide_count = len(job.slides)
        
        # Base times per format (seconds)
        base_times = {
            ExportFormat.PPTX: 1.0,
            ExportFormat.PDF: 2.0,
            ExportFormat.BEAMER: 5.0,
            ExportFormat.GOOGLE_SLIDES: 3.0
        }
        
        # Time per slide
        per_slide_times = {
            ExportFormat.PPTX: 0.2,
            ExportFormat.PDF: 0.3,
            ExportFormat.BEAMER: 0.5,
            ExportFormat.GOOGLE_SLIDES: 0.4
        }
        
        base_time = base_times.get(format, 2.0)
        slide_time = per_slide_times.get(format, 0.3) * slide_count
        
        # Quality multiplier
        quality_multipliers = {
            ExportQuality.DRAFT: 0.7,
            ExportQuality.STANDARD: 1.0,
            ExportQuality.HIGH: 1.5,
            ExportQuality.PREMIUM: 2.0
        }
        
        multiplier = quality_multipliers.get(job.config.quality, 1.0)
        
        return (base_time + slide_time) * multiplier
    
    def _record_processing_time(self, format: ExportFormat, processing_time: float):
        """Record processing time for statistics."""
        if format not in self._stats["average_processing_time"]:
            self._stats["average_processing_time"][format] = []
        
        times = self._stats["average_processing_time"][format]
        times.append(processing_time)
        
        # Keep only last 100 times
        if len(times) > 100:
            times.pop(0)
    
    # Public API methods
    
    async def get_job_progress(self, job_id: str) -> Optional[ExportProgress]:
        """Get progress for a specific job."""
        job = self._jobs.get(job_id)
        return job.progress if job else None
    
    async def get_job_result(self, job_id: str) -> Optional[ExportResult]:
        """Get result for a completed job."""
        job = self._jobs.get(job_id)
        return getattr(job, 'result', None) if job else None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job if possible."""
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if job.progress.status in [ExportStatus.PENDING, ExportStatus.PREPARING]:
            await self._update_progress(job, ExportStatus.CANCELLED, "Job cancelled")
            await self.resource_manager.release_resources(job_id)
            return True
        
        return False
    
    def add_progress_callback(self, job_id: str, callback: Callable):
        """Add progress callback for a job."""
        if job_id not in self._progress_callbacks:
            self._progress_callbacks[job_id] = []
        self._progress_callbacks[job_id].append(callback)
    
    def add_completion_callback(self, job_id: str, callback: Callable):
        """Add completion callback for a job."""
        if job_id not in self._completion_callbacks:
            self._completion_callbacks[job_id] = []
        self._completion_callbacks[job_id].append(callback)
    
    def get_supported_formats(self) -> List[Dict[str, Any]]:
        """Get list of supported export formats with metadata."""
        return [
            {
                "format": fmt.name,
                "name": fmt.value["name"],
                "extension": fmt.value["extension"],
                "mime_type": fmt.value["mime_type"],
                "templates": list(self._template_configs.get(fmt, {}).keys())
            }
            for fmt in ExportFormat
        ]
    
    def get_template_options(self, format: ExportFormat) -> Dict[str, Any]:
        """Get template options for a specific format."""
        return self._template_configs.get(format, {})
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get export service statistics."""
        stats = self._stats.copy()
        
        # Calculate averages
        for format, times in stats["average_processing_time"].items():
            if times:
                stats[f"avg_time_{format.name.lower()}"] = sum(times) / len(times)
        
        # Add resource stats
        stats["resources"] = self.resource_manager.get_resource_stats()
        
        # Add uptime
        stats["uptime_seconds"] = (datetime.now() - stats["start_time"]).total_seconds()
        
        return stats
    
    async def cleanup_expired_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_jobs = [
            job_id for job_id, job in self._jobs.items()
            if job.created_at < cutoff_time and 
            job.progress.status in [ExportStatus.COMPLETED, ExportStatus.FAILED, ExportStatus.CANCELLED]
        ]
        
        for job_id in expired_jobs:
            job = self._jobs.pop(job_id)
            
            # Clean up temporary files
            if hasattr(job, 'result') and job.result and job.result.file_path:
                try:
                    Path(job.result.file_path).unlink(missing_ok=True)
                except Exception as e:
                    self.logger.warning(f"Failed to clean up file {job.result.file_path}: {e}")
            
            # Clean up callbacks
            self._progress_callbacks.pop(job_id, None)
            self._completion_callbacks.pop(job_id, None)
        
        self.logger.info(f"Cleaned up {len(expired_jobs)} expired jobs")
        return len(expired_jobs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the export coordinator."""
        health = {
            "status": "healthy",
            "timestamp": datetime.now(),
            "active_jobs": len(self._jobs),
            "resource_usage": self.resource_manager.get_resource_stats(),
            "generators_available": len(self._generators),
            "checks": {}
        }
        
        # Check generators
        for format, generator_class in self._generators.items():
            try:
                # Basic instantiation test
                generator_class({})
                health["checks"][f"{format.name.lower()}_generator"] = "ok"
            except Exception as e:
                health["checks"][f"{format.name.lower()}_generator"] = f"error: {e}"
                health["status"] = "degraded"
        
        return health


# Factory function for easy instantiation
def create_export_coordinator(max_concurrent_exports: int = 5) -> ExportCoordinator:
    """Create an export coordinator instance."""
    return ExportCoordinator(max_concurrent_exports)