"""
Task queue management with Celery and ARQ integration.

Provides comprehensive task queuing with support for both Celery and ARQ,
including priority queues, retry mechanisms, and distributed processing.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID, uuid4

import redis.asyncio as redis
from celery import Celery
from pydantic import BaseModel, Field

from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Task information and metadata."""
    task_id: str
    queue_name: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class QueueMetrics(BaseModel):
    """Queue system metrics."""
    total_tasks_enqueued: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    active_tasks: int = 0
    pending_tasks: int = 0
    average_task_duration: float = 0.0
    queue_lengths: Dict[str, int] = Field(default_factory=dict)
    worker_count: int = 0
    failed_tasks_last_hour: int = 0


class BaseTaskQueue(ABC):
    """Abstract base class for task queue implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the task queue system."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the task queue system."""
        pass

    @abstractmethod
    async def enqueue_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: Optional[int] = None,
        queue_name: Optional[str] = None
    ) -> bool:
        """Enqueue a task for processing."""
        pass

    @abstractmethod
    async def dequeue_task(self, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Dequeue the next available task."""
        pass

    @abstractmethod
    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get the status of a specific task."""
        pass

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        pass

    @abstractmethod
    async def get_metrics(self) -> QueueMetrics:
        """Get queue system metrics."""
        pass


class ARQTaskQueue(BaseTaskQueue):
    """
    ARQ-based task queue implementation.
    
    Uses Redis as the backend with async/await support.
    Ideal for Python async applications.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_queue: str = "default",
        max_jobs: int = 10,
        job_timeout: int = 300
    ):
        """
        Initialize ARQ task queue.
        
        Args:
            redis_url: Redis connection URL
            default_queue: Default queue name
            max_jobs: Maximum concurrent jobs
            job_timeout: Job timeout in seconds
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.default_queue = default_queue
        self.max_jobs = max_jobs
        self.job_timeout = job_timeout
        
        # Runtime state
        self.redis_pool: Optional[redis.Redis] = None
        self.task_registry: Dict[str, TaskInfo] = {}
        self.metrics = QueueMetrics()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize ARQ task queue."""
        if self._initialized:
            return
            
        logger.info("Initializing ARQ task queue")
        
        try:
            # Create Redis connection pool
            self.redis_pool = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
            
            # Test connection
            await self.redis_pool.ping()
            
            self._initialized = True
            logger.info("ARQ task queue initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ARQ task queue: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown ARQ task queue."""
        logger.info("Shutting down ARQ task queue")
        
        try:
            if self.redis_pool:
                await self.redis_pool.close()
            
            self._initialized = False
            
        except Exception as e:
            logger.error(f"Error during ARQ task queue shutdown: {e}")

    async def enqueue_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: Optional[int] = None,
        queue_name: Optional[str] = None
    ) -> bool:
        """Enqueue a task using ARQ."""
        if not self._initialized or not self.redis_pool:
            raise RuntimeError("Task queue not initialized")
        
        queue_name = queue_name or self.default_queue
        
        try:
            # Create task info
            task_info = TaskInfo(
                task_id=task_id,
                queue_name=queue_name,
                priority=priority,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
                metadata={"task_data": task_data}
            )
            
            # Store task info
            self.task_registry[task_id] = task_info
            
            # Prepare task payload
            task_payload = {
                "task_id": task_id,
                "task_data": task_data,
                "priority": priority.value,
                "created_at": task_info.created_at.isoformat(),
                "queue_name": queue_name
            }
            
            # Determine queue key based on priority
            queue_key = self._get_priority_queue_key(queue_name, priority)
            
            if delay_seconds and delay_seconds > 0:
                # Schedule task for later execution
                execute_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
                await self.redis_pool.zadd(
                    f"{queue_key}:delayed",
                    {json.dumps(task_payload): execute_at.timestamp()}
                )
            else:
                # Add to immediate execution queue
                await self.redis_pool.lpush(queue_key, json.dumps(task_payload))
            
            # Update metrics
            self.metrics.total_tasks_enqueued += 1
            self.metrics.pending_tasks += 1
            
            logger.info(f"Enqueued task {task_id} to queue {queue_name} with priority {priority.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue task {task_id}: {e}")
            return False

    async def dequeue_task(self, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Dequeue the next available task."""
        if not self._initialized or not self.redis_pool:
            raise RuntimeError("Task queue not initialized")
        
        queue_name = queue_name or self.default_queue
        
        try:
            # Check for delayed tasks that are ready
            await self._process_delayed_tasks(queue_name)
            
            # Try to get task from priority queues (highest priority first)
            for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
                queue_key = self._get_priority_queue_key(queue_name, priority)
                
                # Use blocking pop with timeout
                result = await self.redis_pool.brpop(queue_key, timeout=1)
                
                if result:
                    _, task_payload_str = result
                    task_payload = json.loads(task_payload_str)
                    task_id = task_payload["task_id"]
                    
                    # Update task status
                    if task_id in self.task_registry:
                        task_info = self.task_registry[task_id]
                        task_info.status = TaskStatus.RUNNING
                        task_info.started_at = datetime.utcnow()
                        
                        # Update metrics
                        self.metrics.pending_tasks -= 1
                        self.metrics.active_tasks += 1
                    
                    logger.debug(f"Dequeued task {task_id} from {queue_key}")
                    return task_payload
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            return None

    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get the status of a specific task."""
        return self.task_registry.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        if not self._initialized or not self.redis_pool:
            raise RuntimeError("Task queue not initialized")
        
        try:
            if task_id not in self.task_registry:
                return False
            
            task_info = self.task_registry[task_id]
            
            if task_info.status not in [TaskStatus.PENDING, TaskStatus.RETRY]:
                return False  # Can only cancel pending tasks
            
            # Remove from queue
            queue_key = self._get_priority_queue_key(task_info.queue_name, task_info.priority)
            
            # Search and remove from regular queue
            queue_items = await self.redis_pool.lrange(queue_key, 0, -1)
            for item in queue_items:
                payload = json.loads(item)
                if payload["task_id"] == task_id:
                    await self.redis_pool.lrem(queue_key, 1, item)
                    break
            
            # Remove from delayed queue
            delayed_key = f"{queue_key}:delayed"
            delayed_items = await self.redis_pool.zrange(delayed_key, 0, -1, withscores=True)
            for item, score in delayed_items:
                payload = json.loads(item)
                if payload["task_id"] == task_id:
                    await self.redis_pool.zrem(delayed_key, item)
                    break
            
            # Update task status
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = datetime.utcnow()
            
            # Update metrics
            self.metrics.pending_tasks -= 1
            
            logger.info(f"Cancelled task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    async def mark_task_complete(
        self,
        task_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Mark a task as completed."""
        if task_id not in self.task_registry:
            return
        
        task_info = self.task_registry[task_id]
        task_info.completed_at = datetime.utcnow()
        task_info.result = result
        task_info.error_message = error_message
        
        if success:
            task_info.status = TaskStatus.SUCCESS
            self.metrics.total_tasks_completed += 1
        else:
            if task_info.retry_count < task_info.max_retries:
                # Retry the task
                task_info.status = TaskStatus.RETRY
                task_info.retry_count += 1
                
                # Re-enqueue with exponential backoff
                delay_seconds = min(300, 5 * (2 ** task_info.retry_count))
                await self.enqueue_task(
                    task_id=task_id,
                    task_data=task_info.metadata["task_data"],
                    priority=task_info.priority,
                    delay_seconds=delay_seconds,
                    queue_name=task_info.queue_name
                )
                
                logger.info(f"Retrying task {task_id} in {delay_seconds} seconds (attempt {task_info.retry_count})")
            else:
                task_info.status = TaskStatus.FAILURE
                self.metrics.total_tasks_failed += 1
        
        # Update metrics
        self.metrics.active_tasks -= 1
        
        # Update average task duration
        if task_info.started_at and task_info.completed_at:
            duration = (task_info.completed_at - task_info.started_at).total_seconds()
            self._update_average_duration(duration)

    async def get_metrics(self) -> QueueMetrics:
        """Get comprehensive queue metrics."""
        if not self._initialized or not self.redis_pool:
            return self.metrics
        
        try:
            # Update queue lengths
            queue_lengths = {}
            for priority in TaskPriority:
                queue_key = self._get_priority_queue_key(self.default_queue, priority)
                length = await self.redis_pool.llen(queue_key)
                if length > 0:
                    queue_lengths[f"{self.default_queue}:{priority.value}"] = length
            
            self.metrics.queue_lengths = queue_lengths
            
            # Count failed tasks in last hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            failed_count = sum(
                1 for task in self.task_registry.values()
                if (task.status == TaskStatus.FAILURE and 
                    task.completed_at and 
                    task.completed_at > cutoff_time)
            )
            self.metrics.failed_tasks_last_hour = failed_count
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Failed to get queue metrics: {e}")
            return self.metrics

    async def _process_delayed_tasks(self, queue_name: str) -> None:
        """Move delayed tasks to immediate execution queues if ready."""
        try:
            current_time = datetime.utcnow().timestamp()
            
            for priority in TaskPriority:
                queue_key = self._get_priority_queue_key(queue_name, priority)
                delayed_key = f"{queue_key}:delayed"
                
                # Get tasks ready for execution
                ready_tasks = await self.redis_pool.zrangebyscore(
                    delayed_key, 0, current_time, withscores=True
                )
                
                for task_payload_str, score in ready_tasks:
                    # Move to immediate queue
                    await self.redis_pool.lpush(queue_key, task_payload_str)
                    await self.redis_pool.zrem(delayed_key, task_payload_str)
                    
        except Exception as e:
            logger.error(f"Failed to process delayed tasks: {e}")

    def _get_priority_queue_key(self, queue_name: str, priority: TaskPriority) -> str:
        """Get the Redis key for a priority queue."""
        return f"queue:{queue_name}:{priority.value}"

    def _update_average_duration(self, duration: float) -> None:
        """Update average task duration metric."""
        if self.metrics.average_task_duration == 0:
            self.metrics.average_task_duration = duration
        else:
            # Exponential moving average
            alpha = 0.1
            self.metrics.average_task_duration = (
                alpha * duration + 
                (1 - alpha) * self.metrics.average_task_duration
            )


class CeleryTaskQueue(BaseTaskQueue):
    """
    Celery-based task queue implementation.
    
    Uses Celery with Redis/RabbitMQ backend for distributed task processing.
    Better for mixed sync/async workloads and integration with existing Celery infrastructure.
    """

    def __init__(
        self,
        broker_url: Optional[str] = None,
        result_backend: Optional[str] = None,
        default_queue: str = "default"
    ):
        """
        Initialize Celery task queue.
        
        Args:
            broker_url: Message broker URL
            result_backend: Result backend URL
            default_queue: Default queue name
        """
        self.broker_url = broker_url or settings.REDIS_URL
        self.result_backend = result_backend or settings.REDIS_URL
        self.default_queue = default_queue
        
        # Create Celery app
        self.celery_app = Celery(
            "slidegenie_tasks",
            broker=self.broker_url,
            backend=self.result_backend
        )
        
        # Configure Celery
        self.celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_routes={
                "document_processing.*": {"queue": "document_processing"},
                "generation.*": {"queue": "generation"},
            },
            task_default_queue=default_queue,
            worker_prefetch_multiplier=1,
            task_acks_late=True,
            worker_disable_rate_limits=False,
        )
        
        # Runtime state
        self.task_registry: Dict[str, TaskInfo] = {}
        self.metrics = QueueMetrics()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Celery task queue."""
        if self._initialized:
            return
            
        logger.info("Initializing Celery task queue")
        
        try:
            # Test broker connection
            # Note: In a real implementation, you'd want to test the connection
            # For now, we'll assume it's working
            
            self._initialized = True
            logger.info("Celery task queue initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Celery task queue: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown Celery task queue."""
        logger.info("Shutting down Celery task queue")
        self._initialized = False

    async def enqueue_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: Optional[int] = None,
        queue_name: Optional[str] = None
    ) -> bool:
        """Enqueue a task using Celery."""
        if not self._initialized:
            raise RuntimeError("Task queue not initialized")
        
        queue_name = queue_name or self.default_queue
        
        try:
            # Create task info
            task_info = TaskInfo(
                task_id=task_id,
                queue_name=queue_name,
                priority=priority,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
                metadata={"task_data": task_data}
            )
            
            self.task_registry[task_id] = task_info
            
            # Convert priority to Celery routing key
            routing_key = self._get_celery_routing_key(queue_name, priority)
            
            # Apply task
            apply_kwargs = {
                "task_id": task_id,
                "queue": queue_name,
                "routing_key": routing_key,
                "priority": self._priority_to_int(priority),
            }
            
            if delay_seconds and delay_seconds > 0:
                eta = datetime.utcnow() + timedelta(seconds=delay_seconds)
                apply_kwargs["eta"] = eta
            
            # Send task to Celery
            # Note: This is a simplified version. In practice, you'd define
            # actual Celery tasks and use apply_async
            result = self.celery_app.send_task(
                "document_processing.process_document",
                args=[task_data],
                **apply_kwargs
            )
            
            # Update metrics
            self.metrics.total_tasks_enqueued += 1
            self.metrics.pending_tasks += 1
            
            logger.info(f"Enqueued Celery task {task_id} to queue {queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue Celery task {task_id}: {e}")
            return False

    async def dequeue_task(self, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Dequeue task - not directly applicable for Celery (handled by workers)."""
        # Celery workers handle dequeuing automatically
        # This method could be used to inspect pending tasks
        return None

    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status from Celery."""
        if task_id in self.task_registry:
            task_info = self.task_registry[task_id]
            
            # Check Celery result
            try:
                result = self.celery_app.AsyncResult(task_id)
                celery_status = result.status
                
                # Map Celery status to our status
                status_mapping = {
                    "PENDING": TaskStatus.PENDING,
                    "STARTED": TaskStatus.RUNNING,
                    "SUCCESS": TaskStatus.SUCCESS,
                    "FAILURE": TaskStatus.FAILURE,
                    "RETRY": TaskStatus.RETRY,
                    "REVOKED": TaskStatus.CANCELLED,
                }
                
                task_info.status = status_mapping.get(celery_status, TaskStatus.PENDING)
                
                if result.ready():
                    if result.successful():
                        task_info.result = result.result
                    else:
                        task_info.error_message = str(result.info)
                
            except Exception as e:
                logger.error(f"Failed to get Celery task status for {task_id}: {e}")
            
            return task_info
        
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a Celery task."""
        try:
            self.celery_app.control.revoke(task_id, terminate=True)
            
            if task_id in self.task_registry:
                task_info = self.task_registry[task_id]
                task_info.status = TaskStatus.CANCELLED
                task_info.completed_at = datetime.utcnow()
            
            logger.info(f"Cancelled Celery task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel Celery task {task_id}: {e}")
            return False

    async def get_metrics(self) -> QueueMetrics:
        """Get Celery queue metrics."""
        try:
            # Get worker stats
            inspect = self.celery_app.control.inspect()
            stats = inspect.stats()
            active_tasks = inspect.active()
            
            if stats:
                self.metrics.worker_count = len(stats)
            
            if active_tasks:
                total_active = sum(len(tasks) for tasks in active_tasks.values())
                self.metrics.active_tasks = total_active
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Failed to get Celery metrics: {e}")
            return self.metrics

    def _get_celery_routing_key(self, queue_name: str, priority: TaskPriority) -> str:
        """Get Celery routing key based on queue and priority."""
        return f"{queue_name}.{priority.value}"

    def _priority_to_int(self, priority: TaskPriority) -> int:
        """Convert priority enum to integer for Celery."""
        priority_map = {
            TaskPriority.LOW: 1,
            TaskPriority.NORMAL: 5,
            TaskPriority.HIGH: 8,
            TaskPriority.CRITICAL: 10,
        }
        return priority_map.get(priority, 5)


class TaskQueue:
    """
    Unified task queue manager that can use either ARQ or Celery.
    
    Automatically selects the appropriate backend based on configuration
    and provides a consistent interface for task management.
    """

    def __init__(
        self,
        backend: str = "arq",
        **kwargs
    ):
        """
        Initialize task queue manager.
        
        Args:
            backend: Queue backend ("arq" or "celery")
            **kwargs: Backend-specific configuration
        """
        self.backend_name = backend.lower()
        
        if self.backend_name == "arq":
            self.backend: BaseTaskQueue = ARQTaskQueue(**kwargs)
        elif self.backend_name == "celery":
            self.backend: BaseTaskQueue = CeleryTaskQueue(**kwargs)
        else:
            raise ValueError(f"Unsupported queue backend: {backend}")
        
        logger.info(f"Initialized task queue with {self.backend_name} backend")

    async def initialize(self) -> None:
        """Initialize the selected backend."""
        await self.backend.initialize()

    async def shutdown(self) -> None:
        """Shutdown the selected backend."""
        await self.backend.shutdown()

    async def enqueue_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: Optional[int] = None,
        queue_name: Optional[str] = None
    ) -> bool:
        """Enqueue a task."""
        return await self.backend.enqueue_task(
            task_id=task_id,
            task_data=task_data,
            priority=priority,
            delay_seconds=delay_seconds,
            queue_name=queue_name
        )

    async def dequeue_task(self, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Dequeue a task."""
        return await self.backend.dequeue_task(queue_name=queue_name)

    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status."""
        return await self.backend.get_task_status(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        return await self.backend.cancel_task(task_id)

    async def get_metrics(self) -> QueueMetrics:
        """Get queue metrics."""
        return await self.backend.get_metrics()

    def get_backend_name(self) -> str:
        """Get the name of the active backend."""
        return self.backend_name