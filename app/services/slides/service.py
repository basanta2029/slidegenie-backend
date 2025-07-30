"""Main slide generation service implementation."""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import uuid
from pathlib import Path
import tempfile
import json
from concurrent.futures import ThreadPoolExecutor
import time

from .config import SlideGenerationConfig, OutputFormat, get_preset
from .extensions import ExtensionRegistry, GeneratorExtension
from .interfaces import (
    ISlideGenerator, ILayoutEngine, IRulesEngine, 
    IQualityChecker, IOrchestrator, IComponentFactory,
    PresentationContent, SlideContent, ValidationResult,
    QualityReport, GenerationProgress
)


logger = logging.getLogger(__name__)


class SlideGenerationService:
    """Main service for slide generation with all components integrated."""
    
    def __init__(
        self,
        config: Optional[SlideGenerationConfig] = None,
        factory: Optional[IComponentFactory] = None,
        extension_registry: Optional[ExtensionRegistry] = None
    ):
        self.config = config or SlideGenerationConfig()
        self.factory = factory or DefaultComponentFactory()
        self.extension_registry = extension_registry or ExtensionRegistry()
        
        # Component instances
        self._generators: Dict[str, ISlideGenerator] = {}
        self._layout_engine: Optional[ILayoutEngine] = None
        self._rules_engine: Optional[IRulesEngine] = None
        self._quality_checker: Optional[IQualityChecker] = None
        self._orchestrator: Optional[IOrchestrator] = None
        
        # Job tracking
        self._active_jobs: Dict[str, Dict[str, Any]] = {}
        
        # Performance
        self._executor = ThreadPoolExecutor(max_workers=self.config.orchestrator.max_workers)
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all service components."""
        # Create components using factory
        self._layout_engine = self.factory.create_layout_engine(
            self.config.layout.style.value
        )
        
        self._rules_engine = self.factory.create_rules_engine({
            "enable_content_rules": self.config.rules.enable_content_rules,
            "enable_design_rules": self.config.rules.enable_design_rules,
            "enable_accessibility_rules": self.config.rules.enable_accessibility_rules,
            "enable_citation_rules": self.config.rules.enable_citation_rules
        })
        
        self._quality_checker = self.factory.create_quality_checker(
            self.config.quality.quality_level.value
        )
        
        self._orchestrator = self.factory.create_orchestrator({
            "enable_parallel_processing": self.config.orchestrator.enable_parallel_processing,
            "enable_caching": self.config.orchestrator.enable_caching,
            "enable_progress_tracking": self.config.orchestrator.enable_progress_tracking
        })
        
        # Load enabled extensions
        for ext_name in self.config.enabled_extensions:
            ext_config = self.config.extension_config.get(ext_name, {})
            try:
                self.extension_registry.enable(ext_name, ext_config)
            except Exception as e:
                logger.error(f"Failed to enable extension {ext_name}: {e}")
    
    async def generate_presentation(
        self,
        input_content: Union[str, Dict[str, Any]],
        output_format: Optional[OutputFormat] = None,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Generate a complete presentation from input content.
        
        Args:
            input_content: Raw content or structured data
            output_format: Desired output format
            options: Additional generation options
            progress_callback: Callback for progress updates
            
        Returns:
            Tuple of (presentation_bytes, metadata)
        """
        job_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Track job
        self._active_jobs[job_id] = {
            "status": "initializing",
            "started_at": datetime.utcnow(),
            "progress": 0.0
        }
        
        try:
            # Use configured format if not specified
            if output_format is None:
                output_format = self.config.generator.format
            
            # Merge options with config
            generation_config = self.config
            if options:
                generation_config = self.config.merge_with(options)
            
            # Progress tracking wrapper
            async def progress_wrapper(progress: GenerationProgress):
                self._active_jobs[job_id]["progress"] = progress.progress_percentage
                self._active_jobs[job_id]["status"] = progress.current_step
                if progress_callback:
                    await progress_callback(progress)
            
            # Step 1: Validate input
            await progress_wrapper(GenerationProgress(
                current_step="validating_input",
                progress_percentage=5.0,
                message="Validating input content"
            ))
            
            validation_result = await self._orchestrator.validate_input(input_content)
            if not validation_result.is_valid:
                raise ValueError(f"Invalid input: {', '.join(validation_result.errors)}")
            
            # Step 2: Generate presentation content
            await progress_wrapper(GenerationProgress(
                current_step="generating_content",
                progress_percentage=20.0,
                message="Generating presentation structure"
            ))
            
            presentation_content = await self._orchestrator.generate_presentation(
                input_content,
                generation_config.to_dict(),
                progress_wrapper
            )
            
            # Step 3: Apply layouts
            await progress_wrapper(GenerationProgress(
                current_step="applying_layouts",
                progress_percentage=40.0,
                message="Applying slide layouts"
            ))
            
            presentation_content = await self._apply_layouts(
                presentation_content,
                generation_config
            )
            
            # Step 4: Validate with rules
            await progress_wrapper(GenerationProgress(
                current_step="validating_rules",
                progress_percentage=50.0,
                message="Validating against rules"
            ))
            
            rules_result = self._rules_engine.validate_presentation(presentation_content)
            if not rules_result.is_valid and generation_config.rules.enable_content_rules:
                # Try to fix violations
                presentation_content = await self._fix_rule_violations(
                    presentation_content,
                    rules_result
                )
            
            # Step 5: Quality assurance
            await progress_wrapper(GenerationProgress(
                current_step="quality_check",
                progress_percentage=60.0,
                message="Performing quality checks"
            ))
            
            if generation_config.quality.quality_level.value != "draft":
                quality_report = await self._quality_checker.check_quality(
                    presentation_content,
                    generation_config.quality.quality_level.value
                )
                
                # Improve if below threshold
                if quality_report.overall_score < 0.7:
                    presentation_content, quality_report = await self._quality_checker.improve_quality(
                        presentation_content,
                        target_score=0.8
                    )
            
            # Step 6: Apply extensions
            await progress_wrapper(GenerationProgress(
                current_step="applying_extensions",
                progress_percentage=70.0,
                message="Applying extensions"
            ))
            
            presentation_content = await self._apply_extensions(
                presentation_content,
                generation_config
            )
            
            # Step 7: Generate output
            await progress_wrapper(GenerationProgress(
                current_step="generating_output",
                progress_percentage=85.0,
                message=f"Generating {output_format.value} output"
            ))
            
            generator = await self._get_generator(output_format.value)
            output_bytes = await generator.generate(
                presentation_content,
                output_format.value,
                generation_config.generator.custom_settings
            )
            
            # Step 8: Finalize
            await progress_wrapper(GenerationProgress(
                current_step="finalizing",
                progress_percentage=95.0,
                message="Finalizing presentation"
            ))
            
            # Collect metadata
            end_time = time.time()
            metadata = {
                "job_id": job_id,
                "format": output_format.value,
                "slides_count": len(presentation_content.slides),
                "generation_time": end_time - start_time,
                "quality_score": quality_report.overall_score if 'quality_report' in locals() else None,
                "applied_extensions": [ext.name for ext in self.extension_registry.list_extensions(enabled_only=True)],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Complete
            await progress_wrapper(GenerationProgress(
                current_step="completed",
                progress_percentage=100.0,
                message="Presentation generated successfully"
            ))
            
            self._active_jobs[job_id]["status"] = "completed"
            self._active_jobs[job_id]["completed_at"] = datetime.utcnow()
            
            return output_bytes, metadata
            
        except Exception as e:
            self._active_jobs[job_id]["status"] = "failed"
            self._active_jobs[job_id]["error"] = str(e)
            logger.error(f"Generation failed for job {job_id}: {e}")
            raise
        
        finally:
            # Cleanup job after some time
            asyncio.create_task(self._cleanup_job(job_id))
    
    async def generate_from_preset(
        self,
        preset_name: str,
        input_content: Union[str, Dict[str, Any]],
        overrides: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Generate presentation using a preset configuration."""
        preset_config = get_preset(preset_name)
        
        # Apply overrides if provided
        if overrides:
            preset_config = preset_config.merge_with(overrides)
        
        # Temporarily use preset config
        original_config = self.config
        self.config = preset_config
        
        try:
            return await self.generate_presentation(input_content)
        finally:
            self.config = original_config
    
    async def validate_content(
        self,
        input_content: Union[str, Dict[str, Any]]
    ) -> ValidationResult:
        """Validate input content before generation."""
        return await self._orchestrator.validate_input(input_content)
    
    async def preview_presentation(
        self,
        input_content: Union[str, Dict[str, Any]],
        max_slides: int = 5
    ) -> PresentationContent:
        """Generate a preview of the presentation."""
        # Create preview config
        preview_config = self.config.merge_with({
            "generator": {
                "max_slides": max_slides,
                "enable_visual_suggestions": False
            },
            "quality": {
                "quality_level": "draft"
            }
        })
        
        # Generate preview content
        preview_content = await self._orchestrator.generate_presentation(
            input_content,
            preview_config.to_dict(),
            None
        )
        
        # Limit slides
        preview_content.slides = preview_content.slides[:max_slides]
        
        return preview_content
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        formats = [format.value for format in OutputFormat]
        
        # Add formats from extensions
        for ext in self.extension_registry.get_extensions_by_type(GeneratorExtension):
            # Extensions should implement a method to list their formats
            # This is a simplified approach
            formats.extend(["custom_format"])  # Placeholder
        
        return list(set(formats))
    
    def get_available_styles(self) -> List[str]:
        """Get available presentation styles."""
        return self._layout_engine.get_available_layouts("")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a generation job."""
        return self._active_jobs.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel an active generation job."""
        if job_id in self._active_jobs:
            # Attempt to cancel through orchestrator
            success = await self._orchestrator.cancel_generation(job_id)
            if success:
                self._active_jobs[job_id]["status"] = "cancelled"
                self._active_jobs[job_id]["cancelled_at"] = datetime.utcnow()
            return success
        return False
    
    # Private helper methods
    
    async def _get_generator(self, format: str) -> ISlideGenerator:
        """Get or create generator for format."""
        if format not in self._generators:
            # Check extensions first
            for ext in self.extension_registry.get_extensions_by_type(GeneratorExtension):
                if ext.supports_format(format):
                    self._generators[format] = ext
                    return ext
            
            # Use factory
            self._generators[format] = self.factory.create_generator(format)
        
        return self._generators[format]
    
    async def _apply_layouts(
        self,
        content: PresentationContent,
        config: SlideGenerationConfig
    ) -> PresentationContent:
        """Apply layouts to all slides."""
        for i, slide in enumerate(content.slides):
            # Optimize layout based on content
            optimized_slide = self._layout_engine.optimize_layout(
                slide,
                {
                    "style": config.layout.style.value,
                    "enable_accessibility": config.layout.enable_accessibility,
                    "enable_responsive": config.layout.enable_responsive_design
                }
            )
            content.slides[i] = optimized_slide
        
        return content
    
    async def _fix_rule_violations(
        self,
        content: PresentationContent,
        validation_result: ValidationResult
    ) -> PresentationContent:
        """Attempt to fix rule violations."""
        # This is a simplified implementation
        # Real implementation would be more sophisticated
        
        for error in validation_result.errors:
            logger.warning(f"Attempting to fix: {error}")
        
        return content
    
    async def _apply_extensions(
        self,
        content: PresentationContent,
        config: SlideGenerationConfig
    ) -> PresentationContent:
        """Apply all enabled processor extensions."""
        # Apply processor extensions
        from .extensions import ProcessorExtension
        
        for ext in self.extension_registry.get_extensions_by_type(ProcessorExtension):
            content_dict = self._presentation_to_dict(content)
            processed_dict = ext.process_content(content_dict)
            content = self._dict_to_presentation(processed_dict)
        
        return content
    
    async def _cleanup_job(self, job_id: str, delay: int = 3600):
        """Clean up job after delay."""
        await asyncio.sleep(delay)
        if job_id in self._active_jobs:
            del self._active_jobs[job_id]
    
    def _presentation_to_dict(self, presentation: PresentationContent) -> Dict[str, Any]:
        """Convert presentation to dictionary."""
        return {
            "title": presentation.title,
            "subtitle": presentation.subtitle,
            "author": presentation.author,
            "date": presentation.date.isoformat() if presentation.date else None,
            "slides": [
                {
                    "title": slide.title,
                    "content": slide.content,
                    "bullet_points": slide.bullet_points,
                    "speaker_notes": slide.speaker_notes,
                    "layout_type": slide.layout_type,
                    "visual_elements": slide.visual_elements,
                    "metadata": slide.metadata
                }
                for slide in presentation.slides
            ],
            "theme": presentation.theme,
            "metadata": presentation.metadata
        }
    
    def _dict_to_presentation(self, data: Dict[str, Any]) -> PresentationContent:
        """Convert dictionary to presentation."""
        return PresentationContent(
            title=data["title"],
            subtitle=data.get("subtitle"),
            author=data.get("author"),
            date=datetime.fromisoformat(data["date"]) if data.get("date") else None,
            slides=[
                SlideContent(**slide_data)
                for slide_data in data.get("slides", [])
            ],
            theme=data.get("theme"),
            metadata=data.get("metadata", {})
        )
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self._executor.shutdown(wait=True)
        self.extension_registry.cleanup()


# Default implementations (placeholders for other agents' work)

class DefaultComponentFactory(IComponentFactory):
    """Default factory implementation."""
    
    def create_generator(self, format: str) -> ISlideGenerator:
        # Placeholder - Agent 1 will implement
        raise NotImplementedError("Generator not implemented yet")
    
    def create_layout_engine(self, style: str) -> ILayoutEngine:
        # Placeholder - Agent 2 will implement
        raise NotImplementedError("Layout engine not implemented yet")
    
    def create_rules_engine(self, config: Dict[str, Any]) -> IRulesEngine:
        # Placeholder - Agent 3 will implement
        raise NotImplementedError("Rules engine not implemented yet")
    
    def create_quality_checker(self, level: str) -> IQualityChecker:
        # Placeholder - Agent 4 will implement
        raise NotImplementedError("Quality checker not implemented yet")
    
    def create_orchestrator(self, config: Dict[str, Any]) -> IOrchestrator:
        # Placeholder - Agent 5 will implement
        raise NotImplementedError("Orchestrator not implemented yet")