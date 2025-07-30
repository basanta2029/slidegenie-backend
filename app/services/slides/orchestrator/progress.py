"""Progress tracking for slide generation orchestration."""

from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import asyncio
from enum import Enum
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class ProgressEvent(Enum):
    """Types of progress events."""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRYING = "task_retrying"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    GENERATION_STARTED = "generation_started"
    GENERATION_COMPLETED = "generation_completed"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ProgressUpdate:
    """Represents a progress update."""
    event: ProgressEvent
    timestamp: datetime
    task_id: Optional[str] = None
    stage: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    progress_percentage: Optional[float] = None


@dataclass
class TaskMetrics:
    """Metrics for a specific task."""
    task_id: str
    task_type: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[timedelta] = None
    retry_count: int = 0
    status: str = "pending"
    error: Optional[str] = None


@dataclass
class GenerationMetrics:
    """Overall generation metrics."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_task_duration: Optional[float] = None
    total_duration: Optional[timedelta] = None
    throughput: Optional[float] = None  # tasks per second
    estimated_time_remaining: Optional[timedelta] = None


class ProgressTracker:
    """Tracks progress of slide generation orchestration."""
    
    def __init__(self, update_interval: float = 1.0):
        """Initialize the progress tracker."""
        self.update_interval = update_interval
        self.task_metrics: Dict[str, TaskMetrics] = {}
        self.progress_updates: deque = deque(maxlen=1000)
        self.listeners: List[Callable] = []
        self.current_stage: Optional[str] = None
        self.generation_started_at: Optional[datetime] = None
        self.generation_completed_at: Optional[datetime] = None
        self._running = False
        self._update_task: Optional[asyncio.Task] = None
        self._completed_durations: List[float] = []
        
    async def start(self):
        """Start the progress tracker."""
        if self._running:
            return
            
        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())
        logger.info("Progress tracker started")
        
    async def stop(self):
        """Stop the progress tracker."""
        self._running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Progress tracker stopped")
        
    def add_listener(self, listener: Callable):
        """Add a progress update listener."""
        self.listeners.append(listener)
        
    def remove_listener(self, listener: Callable):
        """Remove a progress update listener."""
        if listener in self.listeners:
            self.listeners.remove(listener)
            
    async def track_generation_start(self, total_tasks: int):
        """Track the start of generation."""
        self.generation_started_at = datetime.utcnow()
        
        update = ProgressUpdate(
            event=ProgressEvent.GENERATION_STARTED,
            timestamp=self.generation_started_at,
            message="Slide generation started",
            details={"total_tasks": total_tasks}
        )
        
        await self._emit_update(update)
        
    async def track_generation_complete(self):
        """Track generation completion."""
        self.generation_completed_at = datetime.utcnow()
        
        metrics = self.get_generation_metrics()
        
        update = ProgressUpdate(
            event=ProgressEvent.GENERATION_COMPLETED,
            timestamp=self.generation_completed_at,
            message="Slide generation completed",
            details={
                "metrics": {
                    "total_tasks": metrics.total_tasks,
                    "completed_tasks": metrics.completed_tasks,
                    "failed_tasks": metrics.failed_tasks,
                    "total_duration": str(metrics.total_duration) if metrics.total_duration else None
                }
            },
            progress_percentage=100.0
        )
        
        await self._emit_update(update)
        
    async def track_task_start(self, task_id: str, task_type: str):
        """Track the start of a task."""
        now = datetime.utcnow()
        
        if task_id not in self.task_metrics:
            self.task_metrics[task_id] = TaskMetrics(
                task_id=task_id,
                task_type=task_type
            )
            
        self.task_metrics[task_id].started_at = now
        self.task_metrics[task_id].status = "running"
        
        update = ProgressUpdate(
            event=ProgressEvent.TASK_STARTED,
            timestamp=now,
            task_id=task_id,
            message=f"Started {task_type} task: {task_id}",
            progress_percentage=self._calculate_progress()
        )
        
        await self._emit_update(update)
        
    async def track_task_complete(self, task_id: str, result: Any = None):
        """Track task completion."""
        now = datetime.utcnow()
        
        if task_id in self.task_metrics:
            metrics = self.task_metrics[task_id]
            metrics.completed_at = now
            metrics.status = "completed"
            
            if metrics.started_at:
                metrics.duration = now - metrics.started_at
                self._completed_durations.append(metrics.duration.total_seconds())
                
        update = ProgressUpdate(
            event=ProgressEvent.TASK_COMPLETED,
            timestamp=now,
            task_id=task_id,
            message=f"Completed task: {task_id}",
            details={"result": str(result)[:100] if result else None},
            progress_percentage=self._calculate_progress()
        )
        
        await self._emit_update(update)
        
    async def track_task_failure(self, task_id: str, error: Exception):
        """Track task failure."""
        now = datetime.utcnow()
        
        if task_id in self.task_metrics:
            metrics = self.task_metrics[task_id]
            metrics.completed_at = now
            metrics.status = "failed"
            metrics.error = str(error)
            
            if metrics.started_at:
                metrics.duration = now - metrics.started_at
                
        update = ProgressUpdate(
            event=ProgressEvent.TASK_FAILED,
            timestamp=now,
            task_id=task_id,
            message=f"Task failed: {task_id}",
            details={"error": str(error)},
            progress_percentage=self._calculate_progress()
        )
        
        await self._emit_update(update)
        
    async def track_task_retry(self, task_id: str, retry_count: int):
        """Track task retry."""
        now = datetime.utcnow()
        
        if task_id in self.task_metrics:
            self.task_metrics[task_id].retry_count = retry_count
            
        update = ProgressUpdate(
            event=ProgressEvent.TASK_RETRYING,
            timestamp=now,
            task_id=task_id,
            message=f"Retrying task: {task_id} (attempt {retry_count})",
            progress_percentage=self._calculate_progress()
        )
        
        await self._emit_update(update)
        
    async def track_stage_start(self, stage: str):
        """Track the start of a processing stage."""
        self.current_stage = stage
        
        update = ProgressUpdate(
            event=ProgressEvent.STAGE_STARTED,
            timestamp=datetime.utcnow(),
            stage=stage,
            message=f"Started stage: {stage}"
        )
        
        await self._emit_update(update)
        
    async def track_stage_complete(self, stage: str):
        """Track stage completion."""
        update = ProgressUpdate(
            event=ProgressEvent.STAGE_COMPLETED,
            timestamp=datetime.utcnow(),
            stage=stage,
            message=f"Completed stage: {stage}"
        )
        
        await self._emit_update(update)
        
        if self.current_stage == stage:
            self.current_stage = None
            
    async def log_warning(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log a warning during processing."""
        update = ProgressUpdate(
            event=ProgressEvent.WARNING,
            timestamp=datetime.utcnow(),
            message=message,
            details=details or {}
        )
        
        await self._emit_update(update)
        
    async def log_info(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log informational message."""
        update = ProgressUpdate(
            event=ProgressEvent.INFO,
            timestamp=datetime.utcnow(),
            message=message,
            details=details or {}
        )
        
        await self._emit_update(update)
        
    def get_current_progress(self) -> Dict[str, Any]:
        """Get current progress information."""
        metrics = self.get_generation_metrics()
        
        return {
            "progress_percentage": self._calculate_progress(),
            "current_stage": self.current_stage,
            "metrics": {
                "total_tasks": metrics.total_tasks,
                "completed_tasks": metrics.completed_tasks,
                "failed_tasks": metrics.failed_tasks,
                "running_tasks": self._count_running_tasks(),
                "average_task_duration": metrics.average_task_duration,
                "estimated_time_remaining": (
                    str(metrics.estimated_time_remaining) 
                    if metrics.estimated_time_remaining else None
                )
            },
            "recent_updates": self._get_recent_updates(10),
            "task_breakdown": self._get_task_breakdown()
        }
        
    def get_generation_metrics(self) -> GenerationMetrics:
        """Get overall generation metrics."""
        metrics = GenerationMetrics()
        
        metrics.total_tasks = len(self.task_metrics)
        metrics.completed_tasks = sum(
            1 for m in self.task_metrics.values() 
            if m.status == "completed"
        )
        metrics.failed_tasks = sum(
            1 for m in self.task_metrics.values() 
            if m.status == "failed"
        )
        
        # Calculate average duration
        if self._completed_durations:
            metrics.average_task_duration = statistics.mean(self._completed_durations)
            
        # Calculate total duration
        if self.generation_started_at:
            end_time = self.generation_completed_at or datetime.utcnow()
            metrics.total_duration = end_time - self.generation_started_at
            
            # Calculate throughput
            if metrics.total_duration.total_seconds() > 0:
                metrics.throughput = metrics.completed_tasks / metrics.total_duration.total_seconds()
                
        # Estimate time remaining
        if metrics.average_task_duration and metrics.total_tasks > 0:
            remaining_tasks = metrics.total_tasks - metrics.completed_tasks - metrics.failed_tasks
            if remaining_tasks > 0:
                estimated_seconds = remaining_tasks * metrics.average_task_duration
                metrics.estimated_time_remaining = timedelta(seconds=estimated_seconds)
                
        return metrics
        
    def get_task_metrics(self, task_id: str) -> Optional[TaskMetrics]:
        """Get metrics for a specific task."""
        return self.task_metrics.get(task_id)
        
    def _calculate_progress(self) -> float:
        """Calculate overall progress percentage."""
        if not self.task_metrics:
            return 0.0
            
        total = len(self.task_metrics)
        completed = sum(
            1 for m in self.task_metrics.values() 
            if m.status in ["completed", "failed"]
        )
        
        return (completed / total) * 100 if total > 0 else 0.0
        
    def _count_running_tasks(self) -> int:
        """Count currently running tasks."""
        return sum(
            1 for m in self.task_metrics.values() 
            if m.status == "running"
        )
        
    def _get_recent_updates(self, count: int) -> List[Dict[str, Any]]:
        """Get recent progress updates."""
        recent = list(self.progress_updates)[-count:]
        
        return [
            {
                "event": update.event.value,
                "timestamp": update.timestamp.isoformat(),
                "message": update.message,
                "task_id": update.task_id,
                "stage": update.stage
            }
            for update in recent
        ]
        
    def _get_task_breakdown(self) -> Dict[str, Dict[str, int]]:
        """Get breakdown of tasks by type and status."""
        breakdown = {}
        
        for metrics in self.task_metrics.values():
            task_type = metrics.task_type
            
            if task_type not in breakdown:
                breakdown[task_type] = {
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "running": 0,
                    "pending": 0
                }
                
            breakdown[task_type]["total"] += 1
            breakdown[task_type][metrics.status] += 1
            
        return breakdown
        
    async def _emit_update(self, update: ProgressUpdate):
        """Emit a progress update to listeners."""
        # Store update
        self.progress_updates.append(update)
        
        # Notify listeners
        for listener in self.listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(update)
                else:
                    listener(update)
            except Exception as e:
                logger.error(f"Error in progress listener: {e}")
                
    async def _update_loop(self):
        """Periodic update loop."""
        while self._running:
            try:
                # Emit periodic progress update
                if self.generation_started_at and not self.generation_completed_at:
                    current_progress = self.get_current_progress()
                    
                    update = ProgressUpdate(
                        event=ProgressEvent.INFO,
                        timestamp=datetime.utcnow(),
                        message="Progress update",
                        details=current_progress,
                        progress_percentage=current_progress["progress_percentage"]
                    )
                    
                    await self._emit_update(update)
                    
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in progress update loop: {e}")
                
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for analysis."""
        return {
            "generation": {
                "started_at": self.generation_started_at.isoformat() if self.generation_started_at else None,
                "completed_at": self.generation_completed_at.isoformat() if self.generation_completed_at else None,
                "metrics": self.get_generation_metrics().__dict__
            },
            "tasks": {
                task_id: {
                    "type": metrics.task_type,
                    "status": metrics.status,
                    "started_at": metrics.started_at.isoformat() if metrics.started_at else None,
                    "completed_at": metrics.completed_at.isoformat() if metrics.completed_at else None,
                    "duration": metrics.duration.total_seconds() if metrics.duration else None,
                    "retry_count": metrics.retry_count,
                    "error": metrics.error
                }
                for task_id, metrics in self.task_metrics.items()
            },
            "progress_history": [
                {
                    "event": update.event.value,
                    "timestamp": update.timestamp.isoformat(),
                    "message": update.message,
                    "progress": update.progress_percentage
                }
                for update in self.progress_updates
            ]
        }