"""
Background Jobs and Queue System service interfaces for Agent 5.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID
from datetime import datetime


class IJobQueueService(ABC):
    """Interface for job queue management."""
    
    @abstractmethod
    async def enqueue_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: int = 5,
        scheduled_at: Optional[datetime] = None,
    ) -> UUID:
        """Enqueue a new job."""
        pass
    
    @abstractmethod
    async def get_job_status(
        self,
        job_id: UUID,
    ) -> Dict[str, Any]:
        """Get current job status."""
        pass
    
    @abstractmethod
    async def cancel_job(
        self,
        job_id: UUID,
    ) -> bool:
        """Cancel a pending or running job."""
        pass
    
    @abstractmethod
    async def retry_job(
        self,
        job_id: UUID,
        delay_seconds: Optional[int] = None,
    ) -> bool:
        """Retry a failed job."""
        pass
    
    @abstractmethod
    async def list_jobs(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        """List jobs with filters."""
        pass


class IProgressTrackingService(ABC):
    """Interface for job progress tracking."""
    
    @abstractmethod
    async def update_progress(
        self,
        job_id: UUID,
        progress: float,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update job progress."""
        pass
    
    @abstractmethod
    async def add_job_log(
        self,
        job_id: UUID,
        level: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add log entry for job."""
        pass
    
    @abstractmethod
    async def get_job_progress(
        self,
        job_id: UUID,
    ) -> Dict[str, Any]:
        """Get detailed job progress."""
        pass
    
    @abstractmethod
    async def subscribe_to_progress(
        self,
        job_id: UUID,
        callback: Callable[[Dict[str, Any]], None],
    ) -> str:
        """Subscribe to job progress updates."""
        pass
    
    @abstractmethod
    async def unsubscribe_from_progress(
        self,
        subscription_id: str,
    ) -> bool:
        """Unsubscribe from progress updates."""
        pass


class IExportJobService(ABC):
    """Interface for export job processing."""
    
    @abstractmethod
    async def process_pptx_export(
        self,
        job_id: UUID,
        presentation_id: UUID,
        options: Dict[str, Any],
    ) -> str:
        """Process PowerPoint export job."""
        pass
    
    @abstractmethod
    async def process_pdf_export(
        self,
        job_id: UUID,
        presentation_id: UUID,
        options: Dict[str, Any],
    ) -> str:
        """Process PDF export job."""
        pass
    
    @abstractmethod
    async def process_latex_export(
        self,
        job_id: UUID,
        presentation_id: UUID,
        options: Dict[str, Any],
    ) -> str:
        """Process LaTeX export job."""
        pass
    
    @abstractmethod
    async def process_video_export(
        self,
        job_id: UUID,
        presentation_id: UUID,
        options: Dict[str, Any],
    ) -> str:
        """Process video export job."""
        pass
    
    @abstractmethod
    async def get_export_status(
        self,
        export_id: UUID,
    ) -> Dict[str, Any]:
        """Get export job status."""
        pass


class IGenerationJobService(ABC):
    """Interface for presentation generation jobs."""
    
    @abstractmethod
    async def process_generation_job(
        self,
        job_id: UUID,
        input_type: str,
        input_data: Dict[str, Any],
    ) -> UUID:
        """Process presentation generation job."""
        pass
    
    @abstractmethod
    async def process_slide_generation(
        self,
        job_id: UUID,
        presentation_id: UUID,
        slide_data: Dict[str, Any],
    ) -> UUID:
        """Process single slide generation."""
        pass
    
    @abstractmethod
    async def process_bulk_generation(
        self,
        job_id: UUID,
        presentations: List[Dict[str, Any]],
    ) -> List[UUID]:
        """Process bulk presentation generation."""
        pass
    
    @abstractmethod
    async def estimate_generation_time(
        self,
        input_type: str,
        input_size: int,
        options: Dict[str, Any],
    ) -> int:
        """Estimate generation time in seconds."""
        pass


class IScheduledJobService(ABC):
    """Interface for scheduled job management."""
    
    @abstractmethod
    async def schedule_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        run_at: datetime,
        recurrence: Optional[str] = None,
    ) -> UUID:
        """Schedule a job for future execution."""
        pass
    
    @abstractmethod
    async def cancel_scheduled_job(
        self,
        job_id: UUID,
    ) -> bool:
        """Cancel a scheduled job."""
        pass
    
    @abstractmethod
    async def update_schedule(
        self,
        job_id: UUID,
        new_run_at: datetime,
    ) -> bool:
        """Update job schedule."""
        pass
    
    @abstractmethod
    async def list_scheduled_jobs(
        self,
        user_id: Optional[UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """List scheduled jobs."""
        pass


class IPriorityQueueService(ABC):
    """Interface for priority queue management."""
    
    @abstractmethod
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        pass
    
    @abstractmethod
    async def update_job_priority(
        self,
        job_id: UUID,
        new_priority: int,
    ) -> bool:
        """Update job priority in queue."""
        pass
    
    @abstractmethod
    async def get_estimated_wait_time(
        self,
        priority: int = 5,
    ) -> int:
        """Get estimated wait time for priority level."""
        pass
    
    @abstractmethod
    async def clear_failed_jobs(
        self,
        older_than_days: int = 7,
    ) -> int:
        """Clear old failed jobs."""
        pass