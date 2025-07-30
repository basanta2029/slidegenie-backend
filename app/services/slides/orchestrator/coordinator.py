"""Generation coordinator for parallel slide generation."""

import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from collections import defaultdict

from .base import BaseOrchestrator, Task, TaskStatus, TaskPriority, OrchestratorConfig

logger = logging.getLogger(__name__)


@dataclass
class SlideGenerationTask(Task):
    """Specialized task for slide generation."""
    slide_index: int = 0
    slide_type: str = "content"
    template_id: Optional[str] = None
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationContext:
    """Context shared across slide generation tasks."""
    presentation_id: str
    theme: Dict[str, Any]
    global_style: Dict[str, Any]
    shared_resources: Dict[str, Any] = field(default_factory=dict)
    generated_slides: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    consistency_rules: List[Dict[str, Any]] = field(default_factory=list)


class GenerationCoordinator(BaseOrchestrator):
    """Coordinates parallel slide generation with consistency."""
    
    def __init__(
        self, 
        config: Optional[OrchestratorConfig] = None,
        slide_generator: Optional[Callable] = None,
        consistency_manager: Optional[Any] = None,
        style_manager: Optional[Any] = None
    ):
        """Initialize the generation coordinator."""
        super().__init__(config)
        self.slide_generator = slide_generator
        self.consistency_manager = consistency_manager
        self.style_manager = style_manager
        self.generation_context: Optional[GenerationContext] = None
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._slide_tasks: Dict[int, str] = {}  # slide_index -> task_id
        
    async def prepare_presentation_generation(
        self,
        presentation_data: Dict[str, Any],
        slides_data: List[Dict[str, Any]]
    ) -> List[SlideGenerationTask]:
        """Prepare tasks for presentation generation."""
        logger.info(f"Preparing generation for {len(slides_data)} slides")
        
        # Create generation context
        self.generation_context = GenerationContext(
            presentation_id=presentation_data.get("id", ""),
            theme=presentation_data.get("theme", {}),
            global_style=presentation_data.get("style", {}),
            consistency_rules=presentation_data.get("consistency_rules", [])
        )
        
        # Create slide generation tasks
        tasks = []
        for index, slide_data in enumerate(slides_data):
            task = SlideGenerationTask(
                id=f"slide_{index}",
                type="slide_generation",
                priority=self._calculate_slide_priority(index, slide_data),
                slide_index=index,
                slide_type=slide_data.get("type", "content"),
                template_id=slide_data.get("template_id"),
                content=slide_data.get("content", {}),
                metadata=slide_data.get("metadata", {}),
                data=slide_data
            )
            
            # Add dependencies based on slide relationships
            dependencies = self._analyze_slide_dependencies(index, slide_data, slides_data)
            task.dependencies = dependencies
            self._dependency_graph[task.id] = dependencies
            
            tasks.append(task)
            self._slide_tasks[index] = task.id
            
        # Add special coordination tasks
        tasks.extend(self._create_coordination_tasks(presentation_data, tasks))
        
        return tasks
        
    def _calculate_slide_priority(self, index: int, slide_data: Dict[str, Any]) -> TaskPriority:
        """Calculate priority for slide generation."""
        # Title and section slides have higher priority
        slide_type = slide_data.get("type", "content")
        
        if slide_type == "title" or index == 0:
            return TaskPriority.CRITICAL
        elif slide_type in ["section", "chapter"]:
            return TaskPriority.HIGH
        elif slide_type in ["summary", "conclusion"]:
            return TaskPriority.NORMAL
        else:
            return TaskPriority.NORMAL
            
    def _analyze_slide_dependencies(
        self, 
        index: int, 
        slide_data: Dict[str, Any], 
        all_slides: List[Dict[str, Any]]
    ) -> Set[str]:
        """Analyze dependencies between slides."""
        dependencies = set()
        
        # Slides depend on title slide for consistent styling
        if index > 0:
            dependencies.add("slide_0")
            
        # Section slides depend on previous section
        if slide_data.get("type") == "section":
            for i in range(index - 1, -1, -1):
                if all_slides[i].get("type") == "section":
                    dependencies.add(f"slide_{i}")
                    break
                    
        # Content slides with references depend on referenced slides
        references = slide_data.get("references", [])
        for ref in references:
            ref_index = ref.get("slide_index")
            if ref_index is not None and ref_index < index:
                dependencies.add(f"slide_{ref_index}")
                
        # Custom dependencies
        for dep in slide_data.get("depends_on", []):
            if isinstance(dep, int) and dep < index:
                dependencies.add(f"slide_{dep}")
                
        return dependencies
        
    def _create_coordination_tasks(
        self, 
        presentation_data: Dict[str, Any],
        slide_tasks: List[SlideGenerationTask]
    ) -> List[Task]:
        """Create special coordination tasks."""
        coordination_tasks = []
        
        # Consistency check task
        consistency_task = Task(
            id="consistency_check",
            type="coordination",
            priority=TaskPriority.HIGH,
            dependencies={task.id for task in slide_tasks},
            data={"action": "validate_consistency"}
        )
        coordination_tasks.append(consistency_task)
        
        # Style finalization task
        style_task = Task(
            id="style_finalization",
            type="coordination",
            priority=TaskPriority.NORMAL,
            dependencies={"consistency_check"},
            data={"action": "finalize_styles"}
        )
        coordination_tasks.append(style_task)
        
        # Export preparation task
        export_task = Task(
            id="export_preparation",
            type="coordination",
            priority=TaskPriority.NORMAL,
            dependencies={"style_finalization"},
            data={"action": "prepare_export"}
        )
        coordination_tasks.append(export_task)
        
        return coordination_tasks
        
    async def execute_task(self, task: Task) -> Any:
        """Execute a specific task."""
        if isinstance(task, SlideGenerationTask):
            return await self._execute_slide_generation(task)
        elif task.type == "coordination":
            return await self._execute_coordination_task(task)
        else:
            raise ValueError(f"Unknown task type: {task.type}")
            
    async def _execute_slide_generation(self, task: SlideGenerationTask) -> Dict[str, Any]:
        """Execute slide generation task."""
        logger.info(f"Generating slide {task.slide_index} of type {task.slide_type}")
        
        try:
            # Get dependencies results
            dependency_results = await self._get_dependency_results(task)
            
            # Generate slide content
            if self.slide_generator:
                slide_result = await self.slide_generator(
                    task=task,
                    context=self.generation_context,
                    dependencies=dependency_results
                )
            else:
                # Simulate generation
                slide_result = {
                    "slide_index": task.slide_index,
                    "type": task.slide_type,
                    "content": task.content,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
            # Apply consistency rules
            if self.consistency_manager:
                slide_result = await self.consistency_manager.apply_rules(
                    slide_result,
                    self.generation_context
                )
                
            # Store generated slide
            if self.generation_context:
                self.generation_context.generated_slides[task.slide_index] = slide_result
                
            return slide_result
            
        except Exception as e:
            logger.error(f"Failed to generate slide {task.slide_index}: {e}")
            raise
            
    async def _execute_coordination_task(self, task: Task) -> Any:
        """Execute coordination task."""
        action = task.data.get("action")
        logger.info(f"Executing coordination task: {action}")
        
        if action == "validate_consistency":
            return await self._validate_consistency()
        elif action == "finalize_styles":
            return await self._finalize_styles()
        elif action == "prepare_export":
            return await self._prepare_export()
        else:
            raise ValueError(f"Unknown coordination action: {action}")
            
    async def _get_dependency_results(self, task: Task) -> Dict[str, Any]:
        """Get results from task dependencies."""
        results = {}
        
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if dep_task and dep_task.status == TaskStatus.COMPLETED:
                results[dep_id] = dep_task.result
                
        return results
        
    async def _validate_consistency(self) -> Dict[str, Any]:
        """Validate consistency across all slides."""
        if not self.generation_context:
            return {"status": "skipped", "reason": "no_context"}
            
        issues = []
        slides = self.generation_context.generated_slides
        
        # Check style consistency
        if self.consistency_manager:
            consistency_report = await self.consistency_manager.validate_presentation(
                slides,
                self.generation_context.consistency_rules
            )
            issues.extend(consistency_report.get("issues", []))
        else:
            # Basic consistency checks
            styles = set()
            for slide in slides.values():
                style = slide.get("style", {}).get("theme")
                if style:
                    styles.add(style)
                    
            if len(styles) > 1:
                issues.append({
                    "type": "style_inconsistency",
                    "message": f"Multiple styles detected: {styles}"
                })
                
        return {
            "status": "completed",
            "issues": issues,
            "is_consistent": len(issues) == 0
        }
        
    async def _finalize_styles(self) -> Dict[str, Any]:
        """Finalize styles across all slides."""
        if not self.generation_context:
            return {"status": "skipped", "reason": "no_context"}
            
        finalized_count = 0
        
        if self.style_manager:
            for slide_index, slide in self.generation_context.generated_slides.items():
                finalized_slide = await self.style_manager.finalize_slide_style(
                    slide,
                    self.generation_context.global_style,
                    self.generation_context.theme
                )
                self.generation_context.generated_slides[slide_index] = finalized_slide
                finalized_count += 1
        else:
            # Apply basic style finalization
            for slide in self.generation_context.generated_slides.values():
                slide["style"] = {
                    **self.generation_context.global_style,
                    **slide.get("style", {})
                }
                finalized_count += 1
                
        return {
            "status": "completed",
            "finalized_count": finalized_count
        }
        
    async def _prepare_export(self) -> Dict[str, Any]:
        """Prepare presentation for export."""
        if not self.generation_context:
            return {"status": "skipped", "reason": "no_context"}
            
        # Sort slides by index
        sorted_slides = sorted(
            self.generation_context.generated_slides.items(),
            key=lambda x: x[0]
        )
        
        export_data = {
            "presentation_id": self.generation_context.presentation_id,
            "theme": self.generation_context.theme,
            "global_style": self.generation_context.global_style,
            "slides": [slide for _, slide in sorted_slides],
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "slide_count": len(sorted_slides),
                "generator_version": "1.0.0"
            }
        }
        
        return {
            "status": "completed",
            "export_data": export_data
        }
        
    async def validate_task(self, task: Task) -> bool:
        """Validate if a task can be executed."""
        if isinstance(task, SlideGenerationTask):
            # Validate slide generation prerequisites
            if not self.generation_context:
                logger.error("No generation context available")
                return False
                
            # Check if dependencies are completed
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    logger.warning(f"Dependency {dep_id} not completed for task {task.id}")
                    return False
                    
            return True
            
        return True
        
    def get_slide_generation_progress(self) -> Dict[str, Any]:
        """Get detailed progress of slide generation."""
        if not self.generation_context:
            return {"status": "not_started"}
            
        total_slides = len(self._slide_tasks)
        completed_slides = sum(
            1 for task_id in self._slide_tasks.values()
            if self.tasks.get(task_id, Task(id="", type="")).status == TaskStatus.COMPLETED
        )
        
        progress = {
            "total_slides": total_slides,
            "completed_slides": completed_slides,
            "progress_percentage": (completed_slides / total_slides * 100) if total_slides > 0 else 0,
            "slides": {}
        }
        
        for slide_index, task_id in self._slide_tasks.items():
            task = self.tasks.get(task_id)
            if task:
                progress["slides"][slide_index] = {
                    "status": task.status.value,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None
                }
                
        return progress