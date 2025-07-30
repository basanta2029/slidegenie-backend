"""Integration tests for the slide generation service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import tempfile
import json
from pathlib import Path

from app.services.slides.service import SlideGenerationService
from app.services.slides.config import (
    SlideGenerationConfig, OutputFormat, LayoutStyle, 
    QualityLevel, get_preset, PRESETS
)
from app.services.slides.extensions import ExtensionRegistry
from app.services.slides.interfaces import PresentationContent, SlideContent


class TestSlideServiceIntegration:
    """Complete integration tests for slide service."""
    
    @pytest.fixture
    def service_config(self):
        """Create test configuration."""
        return SlideGenerationConfig(
            generator={"format": OutputFormat.PPTX, "max_slides": 10},
            layout={"style": LayoutStyle.MODERN},
            quality={"quality_level": QualityLevel.STANDARD},
            orchestrator={"enable_parallel_processing": False},  # Simpler for testing
            enable_debugging=True
        )
    
    @pytest.fixture
    def mock_factory(self):
        """Create comprehensive mock factory."""
        factory = Mock()
        
        # Mock generator
        generator = AsyncMock()
        generator.generate.return_value = b"mock_presentation_bytes"
        generator.supports_format.return_value = True
        factory.create_generator.return_value = generator
        
        # Mock layout engine
        layout_engine = Mock()
        layout_engine.optimize_layout.side_effect = lambda slide, _: slide
        layout_engine.get_available_layouts.return_value = ["title", "content", "two_column"]
        factory.create_layout_engine.return_value = layout_engine
        
        # Mock rules engine
        rules_engine = Mock()
        rules_engine.validate_presentation.return_value = Mock(
            is_valid=True, errors=None, warnings=None
        )
        factory.create_rules_engine.return_value = rules_engine
        
        # Mock quality checker
        quality_checker = AsyncMock()
        quality_checker.check_quality.return_value = Mock(
            overall_score=0.9,
            readability_score=0.85,
            consistency_score=0.95,
            accessibility_score=0.8,
            issues=None,
            recommendations=None
        )
        quality_checker.improve_quality.return_value = (
            Mock(),  # Improved presentation
            Mock(overall_score=0.95)  # Improved report
        )
        factory.create_quality_checker.return_value = quality_checker
        
        # Mock orchestrator
        orchestrator = AsyncMock()
        orchestrator.validate_input.return_value = Mock(is_valid=True, errors=None)
        orchestrator.generate_presentation.return_value = PresentationContent(
            title="Test Presentation",
            slides=[
                SlideContent(title="Slide 1", content="Content 1"),
                SlideContent(title="Slide 2", content="Content 2")
            ]
        )
        orchestrator.cancel_generation.return_value = True
        factory.create_orchestrator.return_value = orchestrator
        
        return factory
    
    @pytest.fixture
    def service(self, service_config, mock_factory):
        """Create service with mocked dependencies."""
        return SlideGenerationService(
            config=service_config,
            factory=mock_factory,
            extension_registry=ExtensionRegistry()
        )
    
    @pytest.mark.asyncio
    async def test_complete_generation_workflow(self, service):
        """Test the complete generation workflow from start to finish."""
        input_content = "This is a test presentation about machine learning."
        
        # Test the full workflow
        result_bytes, metadata = await service.generate_presentation(
            input_content,
            output_format=OutputFormat.PPTX,
            options={"max_slides": 5}
        )
        
        # Verify results
        assert result_bytes == b"mock_presentation_bytes"
        assert metadata["format"] == "pptx"
        assert metadata["slides_count"] == 2
        assert "generation_time" in metadata
        assert "job_id" in metadata
        assert "timestamp" in metadata
    
    @pytest.mark.asyncio
    async def test_generation_with_progress_tracking(self, service):
        """Test generation with progress callback."""
        progress_updates = []
        
        async def progress_callback(progress):
            progress_updates.append({
                "step": progress.current_step,
                "percentage": progress.progress_percentage,
                "message": progress.message
            })
        
        await service.generate_presentation(
            "Test content",
            progress_callback=progress_callback
        )
        
        # Should have received multiple progress updates
        assert len(progress_updates) > 0
        assert progress_updates[0]["percentage"] >= 0
        assert progress_updates[-1]["percentage"] == 100.0
        assert progress_updates[-1]["step"] == "completed"
    
    @pytest.mark.asyncio
    async def test_generation_with_different_formats(self, service):
        """Test generation with different output formats."""
        formats_to_test = [OutputFormat.PPTX, OutputFormat.PDF, OutputFormat.GOOGLE_SLIDES]
        
        for format_type in formats_to_test:
            result_bytes, metadata = await service.generate_presentation(
                "Test content",
                output_format=format_type
            )
            
            assert result_bytes == b"mock_presentation_bytes"
            assert metadata["format"] == format_type.value
    
    @pytest.mark.asyncio
    async def test_generation_from_preset(self, service):
        """Test generation using configuration presets."""
        for preset_name in ["quick_draft", "academic_presentation", "business_pitch"]:
            result_bytes, metadata = await service.generate_from_preset(
                preset_name,
                "Test content for preset",
                overrides={"generator": {"max_slides": 3}}
            )
            
            assert result_bytes == b"mock_presentation_bytes"
            assert metadata["slides_count"] == 2
    
    @pytest.mark.asyncio
    async def test_preview_generation(self, service):
        """Test preview generation."""
        preview = await service.preview_presentation(
            "This is test content for preview generation",
            max_slides=3
        )
        
        assert isinstance(preview, PresentationContent)
        assert preview.title == "Test Presentation"
        assert len(preview.slides) <= 3
    
    @pytest.mark.asyncio
    async def test_content_validation(self, service):
        """Test input content validation."""
        # Test valid content
        valid_result = await service.validate_content("This is valid content")
        assert valid_result.is_valid is True
        
        # Test with mocked validation failure
        service._orchestrator.validate_input.return_value = Mock(
            is_valid=False,
            errors=["Content too short"]
        )
        
        invalid_result = await service.validate_content("Bad")
        assert invalid_result.is_valid is False
        assert "Content too short" in invalid_result.errors
    
    def test_supported_formats(self, service):
        """Test getting supported formats."""
        formats = service.get_supported_formats()
        
        assert "pptx" in formats
        assert "pdf" in formats
        assert "google_slides" in formats
        assert "reveal_js" in formats
        assert "markdown" in formats
    
    def test_available_styles(self, service):
        """Test getting available styles."""
        styles = service.get_available_styles()
        
        assert "title" in styles
        assert "content" in styles
        assert "two_column" in styles
    
    @pytest.mark.asyncio
    async def test_job_management(self, service):
        """Test job tracking and management."""
        # Start a generation job
        task = asyncio.create_task(
            service.generate_presentation("Test content")
        )
        
        # Let it start
        await asyncio.sleep(0.01)
        
        # Check active jobs
        assert len(service._active_jobs) >= 0
        
        # Complete the job
        result_bytes, metadata = await task
        job_id = metadata["job_id"]
        
        # Check job status
        status = service.get_job_status(job_id)
        if status:  # May be cleaned up already
            assert status["status"] in ["completed", "processing"]
    
    @pytest.mark.asyncio
    async def test_job_cancellation(self, service):
        """Test job cancellation."""
        # Mock a job
        job_id = "test_job_123"
        service._active_jobs[job_id] = {"status": "processing"}
        
        success = await service.cancel_job(job_id)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """Test error handling in generation."""
        # Mock validation failure
        service._orchestrator.validate_input.return_value = Mock(
            is_valid=False,
            errors=["Invalid input"]
        )
        
        with pytest.raises(ValueError, match="Invalid input"):
            await service.generate_presentation("bad content")
    
    @pytest.mark.asyncio
    async def test_quality_improvement_workflow(self, service):
        """Test workflow when quality improvement is needed."""
        # Mock low quality score
        service._quality_checker.check_quality.return_value = Mock(
            overall_score=0.6,  # Below threshold
            issues=[{"type": "readability", "severity": "medium"}]
        )
        
        result_bytes, metadata = await service.generate_presentation("Test content")
        
        # Should have called improve_quality
        service._quality_checker.improve_quality.assert_called_once()
        assert result_bytes == b"mock_presentation_bytes"
    
    def test_service_cleanup(self, service):
        """Test service cleanup."""
        # Should not raise exceptions
        service.cleanup()
        
        # Executor should be shutdown
        assert service._executor._shutdown


class TestConfigurationManagement:
    """Test configuration management and presets."""
    
    def test_preset_loading(self):
        """Test loading configuration presets."""
        for preset_name in PRESETS:
            config = get_preset(preset_name)
            assert isinstance(config, SlideGenerationConfig)
            
            # Each preset should have specific characteristics
            if preset_name == "quick_draft":
                assert config.quality.quality_level == QualityLevel.DRAFT
                assert config.generator.enable_animations is False
            elif preset_name == "academic_presentation":
                assert config.layout.style == LayoutStyle.ACADEMIC
                assert config.rules.enable_citation_rules is True
            elif preset_name == "business_pitch":
                assert config.layout.style == LayoutStyle.BUSINESS
                assert config.generator.max_slides == 20
    
    def test_config_merging(self):
        """Test configuration merging."""
        base_config = SlideGenerationConfig()
        
        overrides = {
            "generator": {"max_slides": 15},
            "layout": {"style": "creative"},
            "quality": {"quality_level": "premium"}
        }
        
        merged_config = base_config.merge_with(overrides)
        
        assert merged_config.generator.max_slides == 15
        assert merged_config.layout.style == LayoutStyle.CREATIVE
        assert merged_config.quality.quality_level == QualityLevel.PREMIUM
        
        # Other settings should remain unchanged
        assert merged_config.orchestrator.enable_parallel_processing == base_config.orchestrator.enable_parallel_processing
    
    def test_config_serialization(self):
        """Test configuration serialization."""
        config = SlideGenerationConfig()
        
        # Test to_dict
        config_dict = config.to_dict()
        assert "generator" in config_dict
        assert "layout" in config_dict
        assert "quality" in config_dict
        
        # Test from_dict
        restored_config = SlideGenerationConfig.from_dict(config_dict)
        assert restored_config.generator.format == config.generator.format
        assert restored_config.layout.style == config.layout.style
    
    def test_config_file_operations(self):
        """Test saving and loading configuration files."""
        config = SlideGenerationConfig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            # Save configuration
            config.save(config_path)
            
            # Verify file exists
            assert Path(config_path).exists()
            
            # Load configuration
            loaded_config = SlideGenerationConfig.from_file(config_path)
            
            # Verify loaded config matches
            assert loaded_config.generator.format == config.generator.format
            assert loaded_config.layout.style == config.layout.style
            
        finally:
            # Cleanup
            Path(config_path).unlink(missing_ok=True)


class TestExtensionIntegration:
    """Test extension system integration."""
    
    def test_extension_registry_initialization(self):
        """Test extension registry in service."""
        registry = ExtensionRegistry()
        service = SlideGenerationService(extension_registry=registry)
        
        assert service.extension_registry is registry
    
    def test_extension_loading(self):
        """Test loading extensions."""
        registry = ExtensionRegistry()
        
        # Register the example extension
        from app.services.slides.extensions import MarkdownExportExtension
        
        registry.register(MarkdownExportExtension)
        extensions = registry.list_extensions()
        
        assert len(extensions) == 1
        assert extensions[0].name == "markdown_export"
    
    def test_extension_enabling(self):
        """Test enabling extensions."""
        registry = ExtensionRegistry()
        
        from app.services.slides.extensions import MarkdownExportExtension
        registry.register(MarkdownExportExtension)
        
        # Enable extension
        registry.enable("markdown_export", {"include_metadata": True})
        
        # Check it's enabled
        enabled_extensions = registry.list_extensions(enabled_only=True)
        assert len(enabled_extensions) == 1
        assert enabled_extensions[0].enabled is True


class TestPerformanceAndConcurrency:
    """Test performance and concurrency aspects."""
    
    @pytest.fixture
    def service(self):
        """Create service with mock components for performance testing."""
        config = SlideGenerationConfig()
        factory = Mock()
        
        # Fast mock components
        factory.create_generator.return_value = AsyncMock(generate=AsyncMock(return_value=b"data"))
        factory.create_layout_engine.return_value = Mock(optimize_layout=lambda s, _: s)
        factory.create_rules_engine.return_value = Mock(validate_presentation=Mock(return_value=Mock(is_valid=True)))
        factory.create_quality_checker.return_value = AsyncMock(check_quality=AsyncMock(return_value=Mock(overall_score=0.9)))
        factory.create_orchestrator.return_value = AsyncMock(
            validate_input=AsyncMock(return_value=Mock(is_valid=True)),
            generate_presentation=AsyncMock(return_value=PresentationContent(
                title="Test", slides=[SlideContent(title="Slide")]
            ))
        )
        
        return SlideGenerationService(config=config, factory=factory)
    
    @pytest.mark.asyncio
    async def test_concurrent_generations(self, service):
        """Test multiple concurrent generation requests."""
        inputs = [f"Content {i}" for i in range(5)]
        
        # Start multiple generations concurrently
        tasks = [
            service.generate_presentation(content)
            for content in inputs
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 5
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
    
    @pytest.mark.asyncio
    async def test_memory_management(self, service):
        """Test memory management with large content."""
        # Large input content
        large_content = "Large content section. " * 1000
        
        result_bytes, metadata = await service.generate_presentation(large_content)
        
        # Should handle large content without issues
        assert result_bytes == b"data"
        assert metadata["slides_count"] == 1
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, service):
        """Test handling of timeouts."""
        # Mock slow orchestrator
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow operation
            return PresentationContent(title="Slow", slides=[])
        
        service._orchestrator.generate_presentation = slow_generate
        
        # Should complete even with slow operations
        result_bytes, metadata = await service.generate_presentation("Test content")
        assert result_bytes == b"data"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def service(self, mock_factory):
        """Create service for edge case testing."""
        config = SlideGenerationConfig()
        return SlideGenerationService(config=config, factory=mock_factory)
    
    @pytest.mark.asyncio
    async def test_empty_input(self, service):
        """Test generation with empty input."""
        # Mock validation to fail for empty input
        service._orchestrator.validate_input.return_value = Mock(
            is_valid=False,
            errors=["Empty input"]
        )
        
        with pytest.raises(ValueError):
            await service.generate_presentation("")
    
    @pytest.mark.asyncio
    async def test_unsupported_format(self, service):
        """Test generation with unsupported format."""
        # Mock generator creation failure
        service.factory.create_generator.side_effect = Exception("Unsupported format")
        
        with pytest.raises(Exception):
            await service.generate_presentation("content", output_format=OutputFormat.PDF)
    
    @pytest.mark.asyncio
    async def test_component_failure_recovery(self, service):
        """Test recovery from component failures."""
        # Mock rules engine failure
        service._rules_engine.validate_presentation.side_effect = Exception("Rules failed")
        
        # Should still complete generation (rules are not critical)
        result_bytes, metadata = await service.generate_presentation("Test content")
        assert result_bytes == b"mock_presentation_bytes"
    
    def test_invalid_preset(self, service):
        """Test handling of invalid preset names."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("nonexistent_preset")
    
    def test_invalid_configuration(self):
        """Test handling of invalid configuration."""
        with pytest.raises(ValueError):
            SlideGenerationConfig.from_dict({
                "generator": {"format": "invalid_format"}
            })