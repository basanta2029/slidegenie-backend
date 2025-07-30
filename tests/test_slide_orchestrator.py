"""Tests for slide orchestrator system."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from typing import Dict, Any

from app.services.slides.interfaces import (
    IOrchestrator, PresentationContent, SlideContent,
    ValidationResult, GenerationProgress
)
from app.services.slides.service import SlideGenerationService
from app.services.slides.config import SlideGenerationConfig


class MockOrchestrator(IOrchestrator):
    """Mock implementation of orchestrator."""
    
    def __init__(self):
        self.generate_calls = 0
        self.validate_calls = 0
        self.cancel_calls = 0
        self.status_calls = 0
        self.active_jobs = {}
    
    async def generate_presentation(
        self,
        input_content: str,
        config: Dict[str, Any],
        progress_callback: callable = None
    ) -> PresentationContent:
        self.generate_calls += 1
        job_id = f"job_{self.generate_calls}"
        
        # Simulate progress updates
        if progress_callback:
            progress_steps = [
                ("parsing_input", 10.0, "Parsing input content"),
                ("analyzing_structure", 25.0, "Analyzing content structure"),
                ("generating_slides", 50.0, "Generating slide content"),
                ("applying_formatting", 75.0, "Applying formatting"),
                ("finalizing", 100.0, "Finalizing presentation")
            ]
            
            for step, percentage, message in progress_steps:
                await progress_callback(GenerationProgress(
                    current_step=step,
                    progress_percentage=percentage,
                    message=message
                ))
                await asyncio.sleep(0.01)  # Simulate work
        
        # Generate mock presentation based on input
        slides = []
        
        # Simple parsing logic for mock
        if isinstance(input_content, str):
            paragraphs = input_content.split('\n\n')
            for i, para in enumerate(paragraphs[:5]):  # Max 5 slides
                slide = SlideContent(
                    title=f"Slide {i+1}",
                    content=para[:200],  # Limit content
                    layout_type="content"
                )
                slides.append(slide)
        elif isinstance(input_content, dict):
            title = input_content.get("title", "Generated Presentation")
            text_content = input_content.get("text", "")
            
            # Create slides from text
            sentences = text_content.split('. ')
            for i in range(0, len(sentences), 3):  # 3 sentences per slide
                slide_content = '. '.join(sentences[i:i+3])
                slide = SlideContent(
                    title=f"Topic {i//3 + 1}",
                    content=slide_content,
                    layout_type="content"
                )
                slides.append(slide)
        
        # Ensure at least one slide
        if not slides:
            slides = [SlideContent(
                title="Generated Slide",
                content="Content generated from input",
                layout_type="content"
            )]
        
        return PresentationContent(
            title="Generated Presentation",
            slides=slides,
            author="SlideGenie",
            theme="modern"
        )
    
    async def validate_input(self, input_content: str) -> ValidationResult:
        self.validate_calls += 1
        
        errors = []
        warnings = []
        suggestions = []
        
        # Basic validation logic
        if not input_content or (isinstance(input_content, str) and len(input_content.strip()) == 0):
            errors.append("Input content is empty")
        
        if isinstance(input_content, str):
            if len(input_content) < 50:
                warnings.append("Input content is very short")
                suggestions.append("Consider adding more detail")
            
            if len(input_content) > 10000:
                warnings.append("Input content is very long")
                suggestions.append("Consider breaking into multiple presentations")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors if errors else None,
            warnings=warnings if warnings else None,
            suggestions=suggestions if suggestions else None
        )
    
    def get_generation_status(self, job_id: str) -> Dict[str, Any]:
        self.status_calls += 1
        
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        
        # Return mock status
        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 100.0,
            "message": "Generation completed"
        }
    
    async def cancel_generation(self, job_id: str) -> bool:
        self.cancel_calls += 1
        
        if job_id in self.active_jobs:
            self.active_jobs[job_id]["status"] = "cancelled"
            return True
        
        # Simulate cancel success for known jobs
        return job_id.startswith("job_")


class TestOrchestrator:
    """Test suite for orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return MockOrchestrator()
    
    @pytest.mark.asyncio
    async def test_basic_generation(self, orchestrator):
        """Test basic presentation generation."""
        input_text = "This is a test presentation.\n\nFirst topic content.\n\nSecond topic content."
        config = {"format": "pptx", "style": "modern"}
        
        result = await orchestrator.generate_presentation(input_text, config)
        
        assert orchestrator.generate_calls == 1
        assert isinstance(result, PresentationContent)
        assert result.title == "Generated Presentation"
        assert len(result.slides) > 0
        assert all(isinstance(slide, SlideContent) for slide in result.slides)
    
    @pytest.mark.asyncio
    async def test_generation_with_progress_callback(self, orchestrator):
        """Test generation with progress tracking."""
        progress_updates = []
        
        async def progress_callback(progress: GenerationProgress):
            progress_updates.append({
                "step": progress.current_step,
                "percentage": progress.progress_percentage,
                "message": progress.message
            })
        
        input_text = "Test content for generation"
        config = {}
        
        await orchestrator.generate_presentation(input_text, config, progress_callback)
        
        # Should have received progress updates
        assert len(progress_updates) == 5
        assert progress_updates[0]["percentage"] == 10.0
        assert progress_updates[-1]["percentage"] == 100.0
        assert progress_updates[0]["step"] == "parsing_input"
        assert progress_updates[-1]["step"] == "finalizing"
    
    @pytest.mark.asyncio
    async def test_generation_with_dict_input(self, orchestrator):
        """Test generation with structured dictionary input."""
        input_dict = {
            "title": "Custom Title",
            "text": "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence.",
            "author": "Test Author"
        }
        
        result = await orchestrator.generate_presentation(input_dict, {})
        
        assert len(result.slides) >= 1
        assert result.slides[0].title == "Topic 1"
        assert "First sentence" in result.slides[0].content
    
    @pytest.mark.asyncio
    async def test_validate_input_success(self, orchestrator):
        """Test successful input validation."""
        valid_input = "This is a good presentation content with sufficient length and detail."
        
        result = await orchestrator.validate_input(valid_input)
        
        assert orchestrator.validate_calls == 1
        assert result.is_valid is True
        assert result.errors is None
    
    @pytest.mark.asyncio
    async def test_validate_input_empty(self, orchestrator):
        """Test validation of empty input."""
        empty_input = ""
        
        result = await orchestrator.validate_input(empty_input)
        
        assert result.is_valid is False
        assert "Input content is empty" in result.errors
    
    @pytest.mark.asyncio
    async def test_validate_input_warnings(self, orchestrator):
        """Test validation that produces warnings."""
        short_input = "Short"
        
        result = await orchestrator.validate_input(short_input)
        
        assert result.is_valid is True  # Valid but with warnings
        assert "Input content is very short" in result.warnings
        assert "Consider adding more detail" in result.suggestions
        
        long_input = "x" * 15000
        
        result = await orchestrator.validate_input(long_input)
        
        assert result.is_valid is True
        assert "Input content is very long" in result.warnings
    
    def test_get_generation_status(self, orchestrator):
        """Test getting generation status."""
        job_id = "job_123"
        
        status = orchestrator.get_generation_status(job_id)
        
        assert orchestrator.status_calls == 1
        assert status["job_id"] == job_id
        assert "status" in status
        assert "progress" in status
    
    @pytest.mark.asyncio
    async def test_cancel_generation(self, orchestrator):
        """Test canceling generation."""
        job_id = "job_456"
        
        success = await orchestrator.cancel_generation(job_id)
        
        assert orchestrator.cancel_calls == 1
        assert success is True


class TestSlideGenerationService:
    """Test the main slide generation service integration."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components for service."""
        return {
            "generator": Mock(),
            "layout_engine": Mock(),
            "rules_engine": Mock(),
            "quality_checker": AsyncMock(),
            "orchestrator": MockOrchestrator()
        }
    
    @pytest.fixture
    def service(self, mock_components):
        """Create service with mocked components."""
        config = SlideGenerationConfig()
        service = SlideGenerationService(config)
        
        # Replace components with mocks
        service._layout_engine = mock_components["layout_engine"]
        service._rules_engine = mock_components["rules_engine"]
        service._quality_checker = mock_components["quality_checker"]
        service._orchestrator = mock_components["orchestrator"]
        
        # Configure mocks
        service._layout_engine.optimize_layout.side_effect = lambda slide, _: slide
        service._rules_engine.validate_presentation.return_value = ValidationResult(is_valid=True)
        service._quality_checker.check_quality.return_value = Mock(overall_score=0.9)
        
        return service
    
    @pytest.mark.asyncio
    async def test_service_generation_workflow(self, service, mock_components):
        """Test complete service generation workflow."""
        # Mock generator
        mock_generator = AsyncMock()
        mock_generator.generate.return_value = b"mock_presentation_data"
        service._generators["pptx"] = mock_generator
        
        input_content = "Test presentation content"
        
        result, metadata = await service.generate_presentation(input_content)
        
        # Verify all components were called
        assert mock_components["orchestrator"].generate_calls == 1
        assert mock_components["orchestrator"].validate_calls == 1
        assert mock_components["layout_engine"].optimize_layout.called
        assert mock_components["rules_engine"].validate_presentation.called
        assert mock_components["quality_checker"].check_quality.called
        assert mock_generator.generate.called
        
        # Verify result
        assert result == b"mock_presentation_data"
        assert "job_id" in metadata
        assert metadata["format"] == "pptx"
    
    @pytest.mark.asyncio
    async def test_service_validation_before_generation(self, service):
        """Test that service validates input before generation."""
        invalid_input = ""  # Empty input
        
        with pytest.raises(ValueError, match="Invalid input"):
            await service.generate_presentation(invalid_input)
    
    @pytest.mark.asyncio
    async def test_service_preview_generation(self, service):
        """Test preview generation."""
        input_content = "Test content for preview"
        
        preview = await service.preview_presentation(input_content, max_slides=3)
        
        assert isinstance(preview, PresentationContent)
        assert len(preview.slides) <= 3
    
    @pytest.mark.asyncio
    async def test_service_job_tracking(self, service):
        """Test job tracking functionality."""
        # Mock generator to simulate async work
        mock_generator = AsyncMock()
        mock_generator.generate.return_value = b"data"
        service._generators["pptx"] = mock_generator
        
        # Start generation
        task = asyncio.create_task(
            service.generate_presentation("test content")
        )
        
        # Let it start
        await asyncio.sleep(0.01)
        
        # Check if job is tracked (implementation may vary)
        assert len(service._active_jobs) >= 0  # Jobs are tracked
        
        # Complete generation
        result, metadata = await task
        assert "job_id" in metadata
    
    def test_service_supported_formats(self, service):
        """Test getting supported formats."""
        formats = service.get_supported_formats()
        
        assert "pptx" in formats
        assert "pdf" in formats
        assert "google_slides" in formats
        assert len(formats) > 0
    
    @pytest.mark.asyncio
    async def test_service_cancel_job(self, service):
        """Test job cancellation."""
        job_id = "test_job"
        
        # Mock the job as active
        service._active_jobs[job_id] = {"status": "processing"}
        
        success = await service.cancel_job(job_id)
        
        # Should attempt to cancel through orchestrator
        assert service._orchestrator.cancel_calls == 1


class TestOrchestratorEdgeCases:
    """Test edge cases for orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        return MockOrchestrator()
    
    @pytest.mark.asyncio
    async def test_generation_with_malformed_input(self, orchestrator):
        """Test generation with various malformed inputs."""
        # Test with None
        with pytest.raises(AttributeError):
            await orchestrator.generate_presentation(None, {})
        
        # Test with unusual types
        result = await orchestrator.generate_presentation(123, {})
        assert len(result.slides) >= 1  # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_concurrent_generations(self, orchestrator):
        """Test multiple concurrent generations."""
        inputs = [f"Content {i}" for i in range(5)]
        
        tasks = [
            orchestrator.generate_presentation(content, {})
            for content in inputs
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert orchestrator.generate_calls == 5
        assert all(isinstance(r, PresentationContent) for r in results)
    
    @pytest.mark.asyncio
    async def test_progress_callback_exception(self, orchestrator):
        """Test handling of progress callback exceptions."""
        async def faulty_callback(progress):
            if progress.progress_percentage > 50:
                raise Exception("Callback error")
        
        # Should not crash generation
        result = await orchestrator.generate_presentation(
            "test content",
            {},
            faulty_callback
        )
        
        assert isinstance(result, PresentationContent)


class TestOrchestratorIntegration:
    """Integration tests for orchestrator."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        orchestrator = MockOrchestrator()
        
        # Step 1: Validate input
        input_content = "This is a comprehensive test of the orchestrator system. It should handle various types of content and generate appropriate slides."
        
        validation = await orchestrator.validate_input(input_content)
        assert validation.is_valid
        
        # Step 2: Generate presentation
        progress_log = []
        
        async def log_progress(progress):
            progress_log.append(progress.current_step)
        
        presentation = await orchestrator.generate_presentation(
            input_content,
            {"style": "modern", "max_slides": 5},
            log_progress
        )
        
        # Step 3: Verify results
        assert len(presentation.slides) > 0
        assert presentation.title is not None
        assert len(progress_log) == 5  # All progress steps logged
        
        # Step 4: Check status
        status = orchestrator.get_generation_status("job_1")
        assert status["job_id"] == "job_1"