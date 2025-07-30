"""Example usage of the slide generation orchestrator."""

import asyncio
from pathlib import Path
from typing import Dict, Any, List
import logging

from .coordinator import GenerationCoordinator, SlideGenerationTask
from .consistency import ConsistencyManager
from .style_manager import StyleManager
from .export_pipeline import ExportPipeline, ExportOptions, ExportFormat
from .progress import ProgressTracker, ProgressUpdate
from .state import StateManager
from .base import OrchestratorConfig

logger = logging.getLogger(__name__)


class SlideGenieOrchestrator:
    """Complete orchestrator implementation for SlideGenie."""
    
    def __init__(self, config: OrchestratorConfig = None):
        """Initialize the orchestrator with all components."""
        # Core components
        self.config = config or OrchestratorConfig()
        self.consistency_manager = ConsistencyManager()
        self.style_manager = StyleManager()
        self.export_pipeline = ExportPipeline()
        self.progress_tracker = ProgressTracker()
        self.state_manager = StateManager(
            persistence_dir=Path("./orchestrator_state"),
            enable_persistence=True
        )
        
        # Main coordinator
        self.coordinator = GenerationCoordinator(
            config=self.config,
            slide_generator=self._generate_slide,
            consistency_manager=self.consistency_manager,
            style_manager=self.style_manager
        )
        
        # Setup progress tracking
        self.progress_tracker.add_listener(self._handle_progress_update)
        
    async def generate_presentation(
        self,
        presentation_data: Dict[str, Any],
        slides_data: List[Dict[str, Any]],
        theme_id: str = "professional",
        export_formats: List[ExportFormat] = None
    ) -> Dict[str, Any]:
        """Generate a complete presentation with all slides."""
        try:
            # Initialize components
            await self.state_manager.initialize()
            await self.progress_tracker.start()
            
            # Store initial state
            await self.state_manager.set("presentation", presentation_data)
            await self.state_manager.set("theme_id", theme_id)
            await self.state_manager.set("total_slides", len(slides_data))
            
            # Track generation start
            await self.progress_tracker.track_generation_start(len(slides_data))
            
            # Prepare tasks
            tasks = await self.coordinator.prepare_presentation_generation(
                presentation_data,
                slides_data
            )
            
            # Add tasks to coordinator
            await self.coordinator.add_tasks(tasks)
            
            # Store task information in state
            await self.state_manager.set("tasks", {
                task.id: {
                    "type": task.type,
                    "status": task.status.value,
                    "priority": task.priority.value
                }
                for task in tasks
            })
            
            # Run orchestration
            logger.info(f"Starting orchestration for {len(tasks)} tasks")
            results = await self.coordinator.run()
            
            # Track completion
            await self.progress_tracker.track_generation_complete()
            
            # Get final presentation data
            final_presentation = await self._finalize_presentation(theme_id)
            
            # Export if requested
            export_results = {}
            if export_formats:
                export_results = await self._export_presentation(
                    final_presentation,
                    export_formats
                )
                
            # Store final results
            await self.state_manager.set("results", {
                "presentation": final_presentation,
                "export_results": export_results,
                "metrics": self.progress_tracker.get_generation_metrics().__dict__
            })
            
            return {
                "success": True,
                "presentation": final_presentation,
                "exports": export_results,
                "metrics": results,
                "progress": self.progress_tracker.export_metrics()
            }
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            await self.progress_tracker.log_warning(
                f"Orchestration failed: {str(e)}",
                {"error_type": type(e).__name__}
            )
            
            return {
                "success": False,
                "error": str(e),
                "progress": self.progress_tracker.export_metrics()
            }
            
        finally:
            await self.progress_tracker.stop()
            
    async def _generate_slide(
        self,
        task: SlideGenerationTask,
        context: Any,
        dependencies: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a single slide (mock implementation)."""
        # Track task start
        await self.progress_tracker.track_task_start(task.id, task.type)
        
        try:
            # Simulate slide generation
            await asyncio.sleep(0.5)  # Simulate processing time
            
            # Generate slide based on type
            if task.slide_type == "title":
                slide = await self._generate_title_slide(task, context)
            elif task.slide_type == "content":
                slide = await self._generate_content_slide(task, context, dependencies)
            elif task.slide_type == "section":
                slide = await self._generate_section_slide(task, context)
            else:
                slide = await self._generate_generic_slide(task, context)
                
            # Apply theme
            theme_id = await self.state_manager.get("theme_id", "professional")
            slide = await self.style_manager.apply_theme(slide, theme_id)
            
            # Store in state
            await self.state_manager.set(f"slides.{task.slide_index}", slide)
            
            # Track completion
            await self.progress_tracker.track_task_complete(task.id, slide)
            
            return slide
            
        except Exception as e:
            await self.progress_tracker.track_task_failure(task.id, e)
            raise
            
    async def _generate_title_slide(
        self,
        task: SlideGenerationTask,
        context: Any
    ) -> Dict[str, Any]:
        """Generate a title slide."""
        return {
            "slide_index": task.slide_index,
            "type": "title",
            "content": {
                "title": task.content.get("title", "Presentation Title"),
                "subtitle": task.content.get("subtitle", ""),
                "author": task.content.get("author", ""),
                "date": task.content.get("date", "")
            },
            "style": {
                "layout": "center",
                "background": context.theme.get("colors", {}).get("background", "#ffffff")
            }
        }
        
    async def _generate_content_slide(
        self,
        task: SlideGenerationTask,
        context: Any,
        dependencies: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a content slide."""
        # Check dependencies for consistent styling
        title_slide = dependencies.get("slide_0")
        base_style = {}
        
        if title_slide:
            base_style = title_slide.get("style", {})
            
        return {
            "slide_index": task.slide_index,
            "type": "content",
            "content": {
                "title": task.content.get("title", f"Slide {task.slide_index + 1}"),
                "body": task.content.get("body", ""),
                "bullets": task.content.get("bullets", []),
                "images": task.content.get("images", [])
            },
            "style": {
                **base_style,
                "layout": task.content.get("layout", "standard")
            }
        }
        
    async def _generate_section_slide(
        self,
        task: SlideGenerationTask,
        context: Any
    ) -> Dict[str, Any]:
        """Generate a section slide."""
        return {
            "slide_index": task.slide_index,
            "type": "section",
            "content": {
                "title": task.content.get("title", "Section Title"),
                "subtitle": task.content.get("subtitle", "")
            },
            "style": {
                "layout": "section",
                "background": context.theme.get("colors", {}).get("accent", "#f0f0f0")
            }
        }
        
    async def _generate_generic_slide(
        self,
        task: SlideGenerationTask,
        context: Any
    ) -> Dict[str, Any]:
        """Generate a generic slide."""
        return {
            "slide_index": task.slide_index,
            "type": task.slide_type,
            "content": task.content,
            "style": task.data.get("style", {})
        }
        
    async def _finalize_presentation(self, theme_id: str) -> Dict[str, Any]:
        """Finalize the presentation with all generated slides."""
        # Get all slides from state
        slides_data = await self.state_manager.get("slides", {})
        presentation_data = await self.state_manager.get("presentation", {})
        
        # Convert to list and sort by index
        slides = []
        for idx in sorted(slides_data.keys(), key=int):
            slides.append(slides_data[idx])
            
        # Get theme
        theme = self.style_manager.themes.get(theme_id)
        
        return {
            "id": presentation_data.get("id"),
            "title": presentation_data.get("title"),
            "theme": theme.name if theme else theme_id,
            "theme_data": theme.__dict__ if theme else {},
            "slides": slides,
            "metadata": {
                "slide_count": len(slides),
                "generated_at": await self.state_manager.get("generation_started_at"),
                "theme_id": theme_id
            }
        }
        
    async def _export_presentation(
        self,
        presentation: Dict[str, Any],
        formats: List[ExportFormat]
    ) -> Dict[str, Any]:
        """Export presentation to requested formats."""
        export_options = []
        
        for format in formats:
            options = ExportOptions(
                format=format,
                include_notes=True,
                include_animations=True,
                compress_images=True,
                image_quality=85
            )
            export_options.append(options)
            
        # Export to multiple formats
        results = await self.export_pipeline.export_multiple_formats(
            presentation,
            export_options
        )
        
        # Convert results to serializable format
        export_results = {}
        for format, result in results.items():
            export_results[format.value] = {
                "success": len(result.errors) == 0,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata
            }
            
        return export_results
        
    async def _handle_progress_update(self, update: ProgressUpdate):
        """Handle progress updates."""
        # Store progress in state
        await self.state_manager.set(
            f"progress.{update.timestamp.timestamp()}",
            {
                "event": update.event.value,
                "message": update.message,
                "progress": update.progress_percentage,
                "task_id": update.task_id
            }
        )
        
        # Log important events
        if update.event.value in ["task_failed", "warning"]:
            logger.warning(f"Progress: {update.message}")
        else:
            logger.info(f"Progress: {update.message}")


async def example_usage():
    """Example of using the orchestrator."""
    # Create orchestrator
    orchestrator = SlideGenieOrchestrator()
    
    # Sample presentation data
    presentation_data = {
        "id": "pres_123",
        "title": "AI-Powered Presentations",
        "theme": {
            "colors": {
                "primary": "#1e3a8a",
                "background": "#ffffff"
            }
        }
    }
    
    # Sample slides data
    slides_data = [
        {
            "type": "title",
            "content": {
                "title": "AI-Powered Presentations",
                "subtitle": "The Future of Content Creation",
                "author": "SlideGenie Team"
            }
        },
        {
            "type": "section",
            "content": {
                "title": "Introduction",
                "subtitle": "Welcome to the future"
            }
        },
        {
            "type": "content",
            "content": {
                "title": "What is SlideGenie?",
                "body": "An AI-powered presentation generation platform",
                "bullets": [
                    "Automated slide creation",
                    "Intelligent design choices",
                    "Consistent styling"
                ]
            }
        },
        {
            "type": "content",
            "content": {
                "title": "Key Features",
                "bullets": [
                    "AI content generation",
                    "Multiple export formats",
                    "Real-time collaboration",
                    "Custom themes"
                ]
            },
            "depends_on": [0]  # Depends on title slide for styling
        }
    ]
    
    # Generate presentation
    result = await orchestrator.generate_presentation(
        presentation_data,
        slides_data,
        theme_id="professional",
        export_formats=[ExportFormat.HTML, ExportFormat.JSON]
    )
    
    if result["success"]:
        print(f"Generated {len(result['presentation']['slides'])} slides successfully!")
        print(f"Export results: {result['exports']}")
        print(f"Metrics: {result['metrics']}")
    else:
        print(f"Generation failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(example_usage())