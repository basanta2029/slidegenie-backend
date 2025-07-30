"""Base orchestrator class for slide generation coordination."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
from enum import Enum
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task execution priority."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Represents a generation task."""
    id: str
    type: str
    priority: TaskPriority
    dependencies: Set[str] = field(default_factory=set)
    data: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[Exception] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    max_concurrent_tasks: int = 10
    task_timeout: float = 300.0  # 5 minutes
    retry_delay: float = 5.0
    enable_caching: bool = True
    enable_progress_tracking: bool = True
    consistency_check_interval: float = 10.0
    resource_pool_size: int = 5


class BaseOrchestrator(ABC):
    """Base class for slide generation orchestration."""
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """Initialize the orchestrator."""
        self.config = config or OrchestratorConfig()
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self._lock = asyncio.Lock()
        self._shutdown = False
        self._task_semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)
        
    @abstractmethod
    async def execute_task(self, task: Task) -> Any:
        """Execute a specific task."""
        pass
        
    @abstractmethod
    async def validate_task(self, task: Task) -> bool:
        """Validate if a task can be executed."""
        pass
        
    async def add_task(self, task: Task) -> None:
        """Add a task to the orchestrator."""
        async with self._lock:
            self.tasks[task.id] = task
            logger.info(f"Added task {task.id} of type {task.type}")
            
    async def add_tasks(self, tasks: List[Task]) -> None:
        """Add multiple tasks to the orchestrator."""
        for task in tasks:
            await self.add_task(task)
            
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to be executed."""
        ready_tasks = []
        
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
                
            # Check if all dependencies are completed
            if all(dep in self.completed_tasks for dep in task.dependencies):
                ready_tasks.append(task)
                
        # Sort by priority (highest first)
        ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)
        return ready_tasks
        
    async def run_task(self, task: Task) -> None:
        """Run a single task with error handling and retries."""
        async with self._task_semaphore:
            if self._shutdown:
                return
                
            async with self._lock:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                self.running_tasks.add(task.id)
                
            try:
                # Validate task
                if not await self.validate_task(task):
                    raise ValueError(f"Task {task.id} failed validation")
                    
                # Execute task with timeout
                task.result = await asyncio.wait_for(
                    self.execute_task(task),
                    timeout=self.config.task_timeout
                )
                
                # Mark as completed
                async with self._lock:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow()
                    self.running_tasks.discard(task.id)
                    self.completed_tasks.add(task.id)
                    
                logger.info(f"Task {task.id} completed successfully")
                
            except asyncio.TimeoutError:
                await self._handle_task_failure(
                    task, 
                    TimeoutError(f"Task {task.id} timed out after {self.config.task_timeout}s")
                )
                
            except Exception as e:
                await self._handle_task_failure(task, e)
                
    async def _handle_task_failure(self, task: Task, error: Exception) -> None:
        """Handle task failure with retry logic."""
        task.error = error
        
        async with self._lock:
            self.running_tasks.discard(task.id)
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                logger.warning(
                    f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries}): {error}"
                )
                
                # Schedule retry
                await asyncio.sleep(self.config.retry_delay)
                task.status = TaskStatus.PENDING
                
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                self.failed_tasks.add(task.id)
                logger.error(f"Task {task.id} failed after {task.max_retries} retries: {error}")
                
    async def run(self) -> Dict[str, Any]:
        """Run the orchestrator until all tasks are completed."""
        logger.info("Starting orchestrator")
        start_time = datetime.utcnow()
        
        try:
            while not self._shutdown:
                # Get ready tasks
                ready_tasks = self.get_ready_tasks()
                
                if not ready_tasks and not self.running_tasks:
                    # No more tasks to run
                    break
                    
                # Start ready tasks
                tasks_to_start = []
                for task in ready_tasks:
                    if len(self.running_tasks) < self.config.max_concurrent_tasks:
                        tasks_to_start.append(task)
                        
                # Run tasks concurrently
                if tasks_to_start:
                    await asyncio.gather(
                        *[self.run_task(task) for task in tasks_to_start],
                        return_exceptions=True
                    )
                    
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            raise
            
        finally:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            results = {
                "duration": duration,
                "total_tasks": len(self.tasks),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "tasks": {
                    task_id: {
                        "status": task.status.value,
                        "result": task.result,
                        "error": str(task.error) if task.error else None,
                        "duration": (
                            (task.completed_at - task.started_at).total_seconds()
                            if task.started_at and task.completed_at else None
                        )
                    }
                    for task_id, task in self.tasks.items()
                }
            }
            
            logger.info(
                f"Orchestrator completed in {duration:.2f}s: "
                f"{len(self.completed_tasks)} completed, {len(self.failed_tasks)} failed"
            )
            
            return results
            
    async def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator."""
        logger.info("Shutting down orchestrator")
        self._shutdown = True
        
        # Cancel running tasks
        for task_id in list(self.running_tasks):
            task = self.tasks.get(task_id)
            if task:
                task.status = TaskStatus.CANCELLED
                
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "total_tasks": len(self.tasks),
            "pending_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "is_running": not self._shutdown
        }
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        task = self.tasks.get(task_id)
        if not task:
            return None
            
        return {
            "id": task.id,
            "type": task.type,
            "status": task.status.value,
            "priority": task.priority.value,
            "dependencies": list(task.dependencies),
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "retry_count": task.retry_count,
            "error": str(task.error) if task.error else None
        }
        
    @asynccontextmanager
    async def resource_pool(self):
        """Context manager for resource pooling."""
        # Acquire resource
        resource = None
        try:
            # Implementation depends on specific resource type
            yield resource
        finally:
            # Release resource
            pass