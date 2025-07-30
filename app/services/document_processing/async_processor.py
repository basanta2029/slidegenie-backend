"""
Comprehensive async document processing coordinator.

This module provides the main orchestration for async document processing,
including task scheduling, resource management, and workflow coordination.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4
from enum import Enum
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.domain.schemas.document_processing import (
    ProcessingStatus, ProcessingRequest, ProcessingResult,
    ProcessingProgress, DocumentType
)
from .storage.s3_manager import S3StorageManager
from .queue.task_queue import TaskQueue, TaskPriority
from .progress.tracker import ProgressTracker


logger = logging.getLogger(__name__)
settings = get_settings()


class ProcessingStage(str, Enum):
    """Processing stages for document handling."""
    UPLOAD = "upload"
    VALIDATION = "validation"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    INDEXING = "indexing"
    COMPLETION = "completion"


class ResourceLimits(BaseModel):
    """Resource limits for processing operations."""
    max_concurrent_tasks: int = Field(default=10, ge=1)
    max_memory_mb: int = Field(default=2048, ge=512)
    max_processing_time_minutes: int = Field(default=60, ge=1)
    max_file_size_mb: int = Field(default=100, ge=1)
    cpu_throttle_threshold: float = Field(default=0.8, ge=0.1, le=1.0)


class ProcessingTask(BaseModel):
    """Individual processing task representation."""
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    stage: ProcessingStage
    priority: TaskPriority
    document_id: UUID
    user_id: UUID
    file_path: str
    document_type: DocumentType
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    dependencies: Set[UUID] = Field(default_factory=set)
    resource_requirements: ResourceLimits = Field(default_factory=ResourceLimits)

    class Config:
        use_enum_values = True


class AsyncDocumentProcessor:
    """
    Main coordinator for async document processing.
    
    Handles task orchestration, resource management, workflow coordination,
    and provides comprehensive monitoring capabilities.
    """

    def __init__(
        self,
        storage_manager: Optional[S3StorageManager] = None,
        task_queue: Optional[TaskQueue] = None,
        progress_tracker: Optional[ProgressTracker] = None,
        resource_limits: Optional[ResourceLimits] = None
    ):
        """
        Initialize the async document processor.
        
        Args:
            storage_manager: S3/MinIO storage manager instance
            task_queue: Task queue manager instance
            progress_tracker: Progress tracking system instance
            resource_limits: Global resource limits configuration
        """
        self.storage_manager = storage_manager or S3StorageManager()
        self.task_queue = task_queue or TaskQueue()
        self.progress_tracker = progress_tracker or ProgressTracker()
        self.resource_limits = resource_limits or ResourceLimits()
        
        # Runtime state
        self.active_tasks: Dict[UUID, ProcessingTask] = {}
        self.completed_tasks: Dict[UUID, ProcessingTask] = {}
        self.failed_tasks: Dict[UUID, ProcessingTask] = {}
        self.task_dependencies: Dict[UUID, Set[UUID]] = {}
        
        # Resource tracking
        self.current_memory_usage: int = 0
        self.current_cpu_usage: float = 0.0
        self.active_task_count: int = 0
        
        # Metrics
        self.total_processed: int = 0
        self.total_failed: int = 0
        self.average_processing_time: float = 0.0
        
        # Control flags
        self.is_running: bool = False
        self.shutdown_requested: bool = False

    async def initialize(self) -> None:
        """Initialize all components and start background tasks."""
        logger.info("Initializing async document processor")
        
        try:
            # Initialize components
            await self.storage_manager.initialize()
            await self.task_queue.initialize()
            await self.progress_tracker.initialize()
            
            # Start background tasks
            self.is_running = True
            asyncio.create_task(self._task_scheduler_loop())
            asyncio.create_task(self._resource_monitor_loop())
            asyncio.create_task(self._cleanup_loop())
            
            logger.info("Async document processor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize async document processor: {e}")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown the processor."""
        logger.info("Shutting down async document processor")
        
        self.shutdown_requested = True
        
        # Wait for active tasks to complete (with timeout)
        timeout = 60  # seconds
        start_time = datetime.utcnow()
        
        while self.active_tasks and (datetime.utcnow() - start_time).seconds < timeout:
            await asyncio.sleep(1)
        
        # Force cancel remaining tasks
        for task in self.active_tasks.values():
            if task.status == ProcessingStatus.PROCESSING:
                await self._cancel_task(task.id)
        
        # Shutdown components
        await self.task_queue.shutdown()
        await self.progress_tracker.shutdown()
        await self.storage_manager.shutdown()
        
        self.is_running = False
        logger.info("Async document processor shutdown complete")

    async def submit_processing_request(
        self,
        request: ProcessingRequest,
        user_id: UUID,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> UUID:
        """
        Submit a document processing request.
        
        Args:
            request: Processing request details
            user_id: ID of the user submitting the request
            priority: Task priority level
            
        Returns:
            UUID: Job ID for tracking the processing request
        """
        job_id = uuid4()
        
        logger.info(f"Submitting processing request {job_id} for user {user_id}")
        
        try:
            # Create processing stages as individual tasks
            tasks = await self._create_processing_pipeline(
                job_id=job_id,
                request=request,
                user_id=user_id,
                priority=priority
            )
            
            # Submit tasks to queue
            for task in tasks:
                await self.task_queue.enqueue_task(
                    task_id=task.id,
                    task_data=task.dict(),
                    priority=priority,
                    delay_seconds=0 if task.stage == ProcessingStage.UPLOAD else None
                )
                
                # Initialize progress tracking
                await self.progress_tracker.create_job(
                    job_id=job_id,
                    total_steps=len(tasks),
                    user_id=user_id
                )
            
            logger.info(f"Successfully submitted {len(tasks)} tasks for job {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to submit processing request {job_id}: {e}")
            raise

    async def get_job_status(self, job_id: UUID) -> Optional[ProcessingProgress]:
        """Get the current status of a processing job."""
        return await self.progress_tracker.get_job_progress(job_id)

    async def cancel_job(self, job_id: UUID, user_id: UUID) -> bool:
        """
        Cancel a processing job and all its associated tasks.
        
        Args:
            job_id: Job ID to cancel
            user_id: ID of the user requesting cancellation
            
        Returns:
            bool: True if successfully cancelled, False otherwise
        """
        logger.info(f"Cancelling job {job_id} for user {user_id}")
        
        try:
            # Find all tasks for this job
            job_tasks = [
                task for task in self.active_tasks.values()
                if task.job_id == job_id and task.user_id == user_id
            ]
            
            if not job_tasks:
                logger.warning(f"No active tasks found for job {job_id}")
                return False
            
            # Cancel all tasks
            cancelled_count = 0
            for task in job_tasks:
                if await self._cancel_task(task.id):
                    cancelled_count += 1
            
            # Update progress tracker
            await self.progress_tracker.update_job_status(
                job_id=job_id,
                status=ProcessingStatus.CANCELLED,
                message="Job cancelled by user"
            )
            
            logger.info(f"Cancelled {cancelled_count} tasks for job {job_id}")
            return cancelled_count > 0
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    async def get_processing_metrics(self) -> Dict[str, Any]:
        """Get comprehensive processing metrics and statistics."""
        return {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "average_processing_time": self.average_processing_time,
            "current_memory_usage_mb": self.current_memory_usage,
            "current_cpu_usage_percent": self.current_cpu_usage * 100,
            "resource_limits": self.resource_limits.dict(),
            "queue_metrics": await self.task_queue.get_metrics(),
            "storage_metrics": await self.storage_manager.get_metrics(),
        }

    async def _create_processing_pipeline(
        self,
        job_id: UUID,
        request: ProcessingRequest,
        user_id: UUID,
        priority: TaskPriority
    ) -> List[ProcessingTask]:
        """Create a pipeline of processing tasks for a document."""
        tasks = []
        
        # Define processing stages and their dependencies
        stages = [
            (ProcessingStage.UPLOAD, set()),
            (ProcessingStage.VALIDATION, {ProcessingStage.UPLOAD}),
            (ProcessingStage.EXTRACTION, {ProcessingStage.VALIDATION}),
            (ProcessingStage.ANALYSIS, {ProcessingStage.EXTRACTION}),
            (ProcessingStage.INDEXING, {ProcessingStage.ANALYSIS}),
            (ProcessingStage.COMPLETION, {ProcessingStage.INDEXING}),
        ]
        
        task_map = {}
        
        for stage, deps in stages:
            task = ProcessingTask(
                job_id=job_id,
                stage=stage,
                priority=priority,
                document_id=request.document_id,
                user_id=user_id,
                file_path=request.file_path,
                document_type=request.document_type,
                metadata={"options": request.options}
            )
            
            # Set dependencies
            for dep_stage in deps:
                if dep_stage in task_map:
                    task.dependencies.add(task_map[dep_stage])
            
            tasks.append(task)
            task_map[stage] = task.id
        
        return tasks

    async def _task_scheduler_loop(self) -> None:
        """Main task scheduling loop."""
        logger.info("Starting task scheduler loop")
        
        while not self.shutdown_requested:
            try:
                if self.active_task_count < self.resource_limits.max_concurrent_tasks:
                    # Get next available task
                    task_data = await self.task_queue.dequeue_task()
                    
                    if task_data:
                        task = ProcessingTask(**task_data)
                        
                        # Check if dependencies are satisfied
                        if await self._are_dependencies_satisfied(task):
                            await self._execute_task(task)
                        else:
                            # Re-queue task with delay
                            await self.task_queue.enqueue_task(
                                task_id=task.id,
                                task_data=task_data,
                                priority=task.priority,
                                delay_seconds=5
                            )
                
                await asyncio.sleep(1)  # Prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in task scheduler loop: {e}")
                await asyncio.sleep(5)  # Back off on error

    async def _execute_task(self, task: ProcessingTask) -> None:
        """Execute a single processing task."""
        task.status = ProcessingStatus.PROCESSING
        task.started_at = datetime.utcnow()
        self.active_tasks[task.id] = task
        self.active_task_count += 1
        
        logger.info(f"Executing task {task.id} (stage: {task.stage}, job: {task.job_id})")
        
        try:
            # Update progress
            await self.progress_tracker.update_task_progress(
                job_id=task.job_id,
                current_step=task.stage.value,
                progress_percentage=self._calculate_stage_progress(task.stage)
            )
            
            # Execute stage-specific logic
            if task.stage == ProcessingStage.UPLOAD:
                await self._handle_upload_stage(task)
            elif task.stage == ProcessingStage.VALIDATION:
                await self._handle_validation_stage(task)
            elif task.stage == ProcessingStage.EXTRACTION:
                await self._handle_extraction_stage(task)
            elif task.stage == ProcessingStage.ANALYSIS:
                await self._handle_analysis_stage(task)
            elif task.stage == ProcessingStage.INDEXING:
                await self._handle_indexing_stage(task)
            elif task.stage == ProcessingStage.COMPLETION:
                await self._handle_completion_stage(task)
            
            # Mark task as completed
            task.status = ProcessingStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            # Move to completed tasks
            self.completed_tasks[task.id] = task
            del self.active_tasks[task.id]
            self.active_task_count -= 1
            self.total_processed += 1
            
            # Update metrics
            processing_time = (task.completed_at - task.started_at).total_seconds()
            self._update_average_processing_time(processing_time)
            
            logger.info(f"Task {task.id} completed successfully in {processing_time:.2f}s")
            
        except Exception as e:
            await self._handle_task_failure(task, str(e))

    async def _handle_task_failure(self, task: ProcessingTask, error_message: str) -> None:
        """Handle task failure with retry logic."""
        logger.error(f"Task {task.id} failed: {error_message}")
        
        task.error_message = error_message
        task.retry_count += 1
        
        if task.retry_count <= task.max_retries:
            # Retry with exponential backoff
            delay_seconds = min(300, 5 * (2 ** task.retry_count))  # Max 5 minutes
            
            logger.info(f"Retrying task {task.id} in {delay_seconds} seconds (attempt {task.retry_count})")
            
            task.status = ProcessingStatus.PENDING
            await self.task_queue.enqueue_task(
                task_id=task.id,
                task_data=task.dict(),
                priority=task.priority,
                delay_seconds=delay_seconds
            )
        else:
            # Max retries exceeded
            task.status = ProcessingStatus.FAILED
            task.completed_at = datetime.utcnow()
            
            self.failed_tasks[task.id] = task
            del self.active_tasks[task.id]
            self.active_task_count -= 1
            self.total_failed += 1
            
            # Update progress tracker
            await self.progress_tracker.update_job_status(
                job_id=task.job_id,
                status=ProcessingStatus.FAILED,
                message=f"Task failed after {task.max_retries} retries: {error_message}"
            )

    async def _are_dependencies_satisfied(self, task: ProcessingTask) -> bool:
        """Check if task dependencies are satisfied."""
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
        return True

    async def _cancel_task(self, task_id: UUID) -> bool:
        """Cancel a specific task."""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = ProcessingStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            
            del self.active_tasks[task_id]
            self.active_task_count -= 1
            
            return True
        return False

    def _calculate_stage_progress(self, stage: ProcessingStage) -> float:
        """Calculate progress percentage for a given stage."""
        stage_weights = {
            ProcessingStage.UPLOAD: 10.0,
            ProcessingStage.VALIDATION: 20.0,
            ProcessingStage.EXTRACTION: 50.0,
            ProcessingStage.ANALYSIS: 70.0,
            ProcessingStage.INDEXING: 90.0,
            ProcessingStage.COMPLETION: 100.0,
        }
        return stage_weights.get(stage, 0.0)

    def _update_average_processing_time(self, processing_time: float) -> None:
        """Update average processing time with new data point."""
        if self.total_processed == 1:
            self.average_processing_time = processing_time
        else:
            # Exponential moving average
            alpha = 0.1  # Smoothing factor
            self.average_processing_time = (
                alpha * processing_time + 
                (1 - alpha) * self.average_processing_time
            )

    async def _resource_monitor_loop(self) -> None:
        """Monitor resource usage and apply throttling if needed."""
        while not self.shutdown_requested:
            try:
                # Monitor CPU and memory usage
                # This is a simplified version - in production, you'd use psutil
                # or similar libraries for accurate system monitoring
                
                # Apply throttling if needed
                if self.current_cpu_usage > self.resource_limits.cpu_throttle_threshold:
                    logger.warning("CPU usage high, applying throttling")
                    await asyncio.sleep(2)  # Add delay between task executions
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in resource monitor loop: {e}")
                await asyncio.sleep(10)

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of completed and failed tasks."""
        while not self.shutdown_requested:
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                # Clean up old completed tasks
                to_remove = [
                    task_id for task_id, task in self.completed_tasks.items()
                    if task.completed_at and task.completed_at < cutoff_time
                ]
                
                for task_id in to_remove:
                    del self.completed_tasks[task_id]
                
                # Clean up old failed tasks
                to_remove = [
                    task_id for task_id, task in self.failed_tasks.items()
                    if task.completed_at and task.completed_at < cutoff_time
                ]
                
                for task_id in to_remove:
                    del self.failed_tasks[task_id]
                
                if to_remove:
                    logger.info(f"Cleaned up {len(to_remove)} old task records")
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)

    # Stage-specific handlers (to be implemented based on specific requirements)
    async def _handle_upload_stage(self, task: ProcessingTask) -> None:
        """Handle document upload stage."""
        # Implement upload logic using storage manager
        pass

    async def _handle_validation_stage(self, task: ProcessingTask) -> None:
        """Handle document validation stage."""
        # Implement validation logic
        pass

    async def _handle_extraction_stage(self, task: ProcessingTask) -> None:
        """Handle document content extraction stage."""
        # Implement extraction logic using existing processors
        pass

    async def _handle_analysis_stage(self, task: ProcessingTask) -> None:
        """Handle document analysis stage."""
        # Implement analysis logic
        pass

    async def _handle_indexing_stage(self, task: ProcessingTask) -> None:
        """Handle document indexing stage."""
        # Implement indexing logic
        pass

    async def _handle_completion_stage(self, task: ProcessingTask) -> None:
        """Handle processing completion stage."""
        # Implement completion logic and notifications
        pass


@asynccontextmanager
async def get_async_processor():
    """Context manager for async document processor."""
    processor = AsyncDocumentProcessor()
    await processor.initialize()
    try:
        yield processor
    finally:
        await processor.shutdown()