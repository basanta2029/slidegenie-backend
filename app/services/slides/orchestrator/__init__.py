"""Slide generation orchestrator package."""

from .base import (
    BaseOrchestrator,
    Task,
    TaskStatus,
    TaskPriority,
    OrchestratorConfig
)
from .coordinator import (
    GenerationCoordinator,
    SlideGenerationTask,
    GenerationContext
)
from .consistency import (
    ConsistencyManager,
    ConsistencyRule,
    ConsistencyIssue
)
from .style_manager import (
    StyleManager,
    StyleRule,
    StyleTheme
)
from .export_pipeline import (
    ExportPipeline,
    ExportFormat,
    ExportOptions,
    ExportResult
)
from .progress import (
    ProgressTracker,
    ProgressEvent,
    ProgressUpdate,
    TaskMetrics,
    GenerationMetrics
)
from .state import (
    StateManager,
    StateChangeType,
    StateSnapshot,
    StateChange
)

__all__ = [
    # Base
    "BaseOrchestrator",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "OrchestratorConfig",
    
    # Coordinator
    "GenerationCoordinator",
    "SlideGenerationTask",
    "GenerationContext",
    
    # Consistency
    "ConsistencyManager",
    "ConsistencyRule",
    "ConsistencyIssue",
    
    # Style Manager
    "StyleManager",
    "StyleRule",
    "StyleTheme",
    
    # Export Pipeline
    "ExportPipeline",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    
    # Progress Tracking
    "ProgressTracker",
    "ProgressEvent",
    "ProgressUpdate",
    "TaskMetrics",
    "GenerationMetrics",
    
    # State Management
    "StateManager",
    "StateChangeType",
    "StateSnapshot",
    "StateChange"
]