"""
Base document processor interface and abstract classes.

Defines the standard interface for all document processors in SlideGenie,
ensuring consistent behavior across different document types.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import structlog
from pydantic import BaseModel

from app.domain.schemas.document_processing import (
    ProcessingRequest,
    ProcessingResult,
    ProcessingProgress,
    DocumentElement,
    DocumentMetadata,
    DocumentType,
    ProcessingStatus,
)

logger = structlog.get_logger(__name__)


class DocumentProcessorError(Exception):
    """Base exception for document processor errors."""
    pass


class UnsupportedDocumentTypeError(DocumentProcessorError):
    """Raised when document type is not supported."""
    pass


class InvalidDocumentError(DocumentProcessorError):
    """Raised when document is corrupted or invalid."""
    pass


class ProcessingTimeoutError(DocumentProcessorError):
    """Raised when processing takes too long."""
    pass


class ExtractionError(DocumentProcessorError):
    """Raised when specific extraction fails."""
    pass


class ProcessorCapability(BaseModel):
    """Capability description for a processor."""
    name: str
    description: str
    supported: bool = True
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = {}


class IDocumentProcessor(ABC):
    """
    Base interface for all document processors.
    
    This interface defines the standard methods that all document processors
    must implement to ensure consistent behavior across different document types.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize processor with configuration."""
        self.config = config or {}
        self.logger = structlog.get_logger(self.__class__.__name__)
        
    @property
    @abstractmethod
    def supported_types(self) -> List[DocumentType]:
        """Return list of supported document types."""
        pass
        
    @property
    @abstractmethod
    def capabilities(self) -> Dict[str, ProcessorCapability]:
        """Return processor capabilities."""
        pass
        
    @abstractmethod
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """
        Process a document according to the request specifications.
        
        Args:
            request: Processing request with document path and options
            
        Returns:
            ProcessingResult with extracted elements and metadata
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        pass
        
    @abstractmethod
    async def extract_text(
        self, 
        file_path: Union[str, Path], 
        preserve_layout: bool = True
    ) -> List[DocumentElement]:
        """
        Extract text elements from document.
        
        Args:
            file_path: Path to document file
            preserve_layout: Whether to preserve layout information
            
        Returns:
            List of text elements with positioning information
        """
        pass
        
    @abstractmethod
    async def extract_metadata(self, file_path: Union[str, Path]) -> DocumentMetadata:
        """
        Extract document metadata.
        
        Args:
            file_path: Path to document file
            
        Returns:
            DocumentMetadata object with extracted information
        """
        pass
        
    @abstractmethod
    async def validate_document(self, file_path: Union[str, Path]) -> bool:
        """
        Validate that document can be processed.
        
        Args:
            file_path: Path to document file
            
        Returns:
            True if document is valid and processable
            
        Raises:
            InvalidDocumentError: If document is invalid
        """
        pass
        
    @abstractmethod
    async def get_progress(self, job_id: UUID) -> Optional[ProcessingProgress]:
        """
        Get processing progress for a job.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            ProcessingProgress if job exists, None otherwise
        """
        pass
        
    @abstractmethod
    async def cancel_processing(self, job_id: UUID) -> bool:
        """
        Cancel an ongoing processing job.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if cancellation was successful
        """
        pass
    
    def supports_type(self, document_type: DocumentType) -> bool:
        """Check if processor supports a document type."""
        return document_type in self.supported_types
        
    def has_capability(self, capability: str) -> bool:
        """Check if processor has a specific capability."""
        return (capability in self.capabilities and 
                self.capabilities[capability].supported)
                
    async def health_check(self) -> bool:
        """
        Perform processor health check.
        
        Returns:
            True if processor is healthy and ready
        """
        try:
            # Override in subclasses for specific health checks
            return True
        except Exception as e:
            self.logger.error("processor_health_check_failed", error=str(e))
            return False


class BaseDocumentProcessor(IDocumentProcessor):
    """
    Base implementation with common functionality.
    
    Provides common functionality that can be shared across different
    document processor implementations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._processing_jobs: Dict[UUID, ProcessingProgress] = {}
        
    async def get_progress(self, job_id: UUID) -> Optional[ProcessingProgress]:
        """Get processing progress for a job."""
        return self._processing_jobs.get(job_id)
        
    async def cancel_processing(self, job_id: UUID) -> bool:
        """Cancel an ongoing processing job."""
        if job_id in self._processing_jobs:
            progress = self._processing_jobs[job_id]
            if progress.status == ProcessingStatus.PROCESSING:
                progress.status = ProcessingStatus.CANCELLED
                self.logger.info("processing_job_cancelled", job_id=str(job_id))
                return True
        return False
        
    def _update_progress(
        self,
        job_id: UUID,
        progress_percentage: float,
        current_step: str,
        completed_steps: int,
        total_steps: int,
        status: ProcessingStatus = ProcessingStatus.PROCESSING
    ) -> None:
        """Update processing progress."""
        if job_id in self._processing_jobs:
            progress = self._processing_jobs[job_id]
            progress.progress_percentage = progress_percentage
            progress.current_step = current_step
            progress.completed_steps = completed_steps
            progress.total_steps = total_steps
            progress.status = status
            
    def _start_job(self, job_id: UUID, total_steps: int = 10) -> None:
        """Start tracking a processing job."""
        from datetime import datetime
        
        progress = ProcessingProgress(
            job_id=job_id,
            status=ProcessingStatus.PROCESSING,
            progress_percentage=0.0,
            current_step="Initializing",
            total_steps=total_steps,
            completed_steps=0,
            started_at=datetime.utcnow()
        )
        self._processing_jobs[job_id] = progress
        
    def _complete_job(self, job_id: UUID, success: bool = True, error: Optional[str] = None) -> None:
        """Mark a processing job as completed."""
        if job_id in self._processing_jobs:
            progress = self._processing_jobs[job_id]
            progress.status = ProcessingStatus.COMPLETED if success else ProcessingStatus.FAILED
            progress.progress_percentage = 100.0
            progress.completed_steps = progress.total_steps
            progress.current_step = "Complete" if success else "Failed"
            if error:
                progress.error_message = error
                
    def _validate_file_path(self, file_path: Union[str, Path]) -> Path:
        """Validate and convert file path."""
        path = Path(file_path)
        if not path.exists():
            raise InvalidDocumentError(f"File not found: {file_path}")
        if not path.is_file():
            raise InvalidDocumentError(f"Path is not a file: {file_path}")
        return path
        
    def _get_file_size(self, file_path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        return Path(file_path).stat().st_size
        
    def _check_file_size_limit(self, file_path: Union[str, Path], max_size_mb: int = 100) -> None:
        """Check if file size is within limits."""
        size_bytes = self._get_file_size(file_path)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > max_size_mb:
            raise InvalidDocumentError(
                f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)"
            )


class ProcessorRegistry:
    """Registry for document processors."""
    
    def __init__(self):
        self._processors: Dict[DocumentType, IDocumentProcessor] = {}
        
    def register(self, document_type: DocumentType, processor: IDocumentProcessor) -> None:
        """Register a processor for a document type."""
        self._processors[document_type] = processor
        logger.info(
            "processor_registered",
            document_type=document_type.value,
            processor_class=processor.__class__.__name__
        )
        
    def get(self, document_type: DocumentType) -> Optional[IDocumentProcessor]:
        """Get processor for a document type."""
        return self._processors.get(document_type)
        
    def get_supported_types(self) -> List[DocumentType]:
        """Get all supported document types."""
        return list(self._processors.keys())
        
    def has_processor(self, document_type: DocumentType) -> bool:
        """Check if processor exists for document type."""
        return document_type in self._processors


# Global processor registry instance
processor_registry = ProcessorRegistry()