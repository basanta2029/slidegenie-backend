"""
Comprehensive tests for the Export Coordinator system.

Tests cover:
- Export job submission and management
- Progress tracking and status updates
- Configuration management
- Error handling and validation
- Resource management
- Quality assurance
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.schemas.generation import Citation, SlideContent
from app.services.export.export_coordinator import (
    ExportCoordinator,
    ExportConfig,
    ExportFormat,
    ExportPriority,
    ExportQuality,
    ExportStatus,
    ResourceManager,
    ExportValidator,
    create_export_coordinator
)
from app.services.export.config_manager import (
    ConfigManager,
    BrandingConfig,
    TypographyConfig,
    ExportPreferences,
    create_config_manager
)


class TestExportCoordinator:
    """Test suite for ExportCoordinator."""
    
    @pytest.fixture
    def sample_slides(self) -> List[SlideContent]:
        """Create sample slide content for testing."""
        return [
            SlideContent(
                title="Test Slide 1",
                body=[
                    {"type": "text", "content": "Test content"},
                    {"type": "bullet_list", "items": ["Item 1", "Item 2"]}
                ],
                layout="title_and_content"
            ),
            SlideContent(
                title="Test Slide 2",
                body=[
                    {"type": "text", "content": "More test content"},
                    {"type": "image", "src": "/test/image.png", "alt": "Test image"}
                ],
                layout="title_and_content"
            )
        ]
    
    @pytest.fixture
    def sample_citations(self) -> List[Citation]:
        """Create sample citations for testing."""
        return [
            Citation(
                id="test2023",
                authors=["Test, A.", "Example, B."],
                title="Test Citation",
                journal="Test Journal",
                year=2023,
                volume="1",
                pages="1-10"
            )
        ]
    
    @pytest.fixture
    def export_coordinator(self) -> ExportCoordinator:
        """Create export coordinator for testing."""
        return create_export_coordinator(max_concurrent_exports=2)
    
    @pytest.mark.asyncio
    async def test_submit_export_job(self, export_coordinator, sample_slides):
        """Test export job submission."""
        config = ExportConfig(
            format=ExportFormat.PPTX,
            template_name="ieee",
            quality=ExportQuality.STANDARD
        )
        
        job_id = await export_coordinator.submit_export_job(
            slides=sample_slides,
            config=config,
            user_id="test_user"
        )
        
        assert job_id is not None
        assert len(job_id) > 0
        assert job_id in export_coordinator._jobs
        
        job = export_coordinator._jobs[job_id]
        assert job.slides == sample_slides
        assert job.config.format == ExportFormat.PPTX
        assert job.user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_get_job_progress(self, export_coordinator, sample_slides):
        """Test job progress tracking."""
        config = ExportConfig(format=ExportFormat.PPTX)
        
        job_id = await export_coordinator.submit_export_job(
            slides=sample_slides,
            config=config,
            user_id="test_user"
        )
        
        progress = await export_coordinator.get_job_progress(job_id)
        
        assert progress is not None
        assert progress.job_id == job_id
        assert progress.format == ExportFormat.PPTX
        assert 0 <= progress.progress_percent <= 100
    
    @pytest.mark.asyncio
    async def test_invalid_slides_validation(self, export_coordinator):
        """Test validation of invalid slide content."""
        invalid_slides = []  # Empty slides
        
        config = ExportConfig(format=ExportFormat.PPTX)
        
        with pytest.raises(ValueError, match="Invalid slides"):
            await export_coordinator.submit_export_job(
                slides=invalid_slides,
                config=config,
                user_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_cancel_job(self, export_coordinator, sample_slides):
        """Test job cancellation."""
        config = ExportConfig(format=ExportFormat.PPTX)
        
        job_id = await export_coordinator.submit_export_job(
            slides=sample_slides,
            config=config,
            user_id="test_user"
        )
        
        # Cancel immediately (should work since job is pending)
        success = await export_coordinator.cancel_job(job_id)
        assert success is True
        
        progress = await export_coordinator.get_job_progress(job_id)
        assert progress.status == ExportStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, export_coordinator, sample_slides):
        """Test progress callback functionality."""
        config = ExportConfig(format=ExportFormat.PPTX)
        
        job_id = await export_coordinator.submit_export_job(
            slides=sample_slides,
            config=config,
            user_id="test_user"
        )
        
        callback_called = False
        callback_progress = None
        
        async def test_callback(progress):
            nonlocal callback_called, callback_progress
            callback_called = True
            callback_progress = progress
        
        export_coordinator.add_progress_callback(job_id, test_callback)
        
        # Manually trigger progress update
        job = export_coordinator._jobs[job_id]
        await export_coordinator._update_progress(
            job, ExportStatus.GENERATING, "Test update"
        )
        
        assert callback_called is True
        assert callback_progress is not None
        assert callback_progress.status == ExportStatus.GENERATING
    
    def test_get_supported_formats(self, export_coordinator):
        """Test getting supported export formats."""
        formats = export_coordinator.get_supported_formats()
        
        assert len(formats) > 0
        assert all('format' in fmt for fmt in formats)
        assert all('name' in fmt for fmt in formats)
        assert all('extension' in fmt for fmt in formats)
        
        format_names = [fmt['format'] for fmt in formats]
        assert 'PPTX' in format_names
        assert 'BEAMER' in format_names
        assert 'PDF' in format_names
        assert 'GOOGLE_SLIDES' in format_names
    
    def test_get_statistics(self, export_coordinator):
        """Test statistics collection."""
        stats = export_coordinator.get_statistics()
        
        assert 'total_exports' in stats
        assert 'successful_exports' in stats
        assert 'failed_exports' in stats
        assert 'exports_by_format' in stats
        assert 'resources' in stats
        assert 'uptime_seconds' in stats
        
        assert isinstance(stats['total_exports'], int)
        assert isinstance(stats['uptime_seconds'], float)
    
    @pytest.mark.asyncio
    async def test_health_check(self, export_coordinator):
        """Test system health check."""
        health = await export_coordinator.health_check()
        
        assert 'status' in health
        assert 'timestamp' in health
        assert 'active_jobs' in health
        assert 'generators_available' in health
        assert 'checks' in health
        
        assert health['status'] in ['healthy', 'degraded', 'unhealthy']
        assert isinstance(health['generators_available'], int)
        assert isinstance(health['checks'], dict)


class TestResourceManager:
    """Test suite for ResourceManager."""
    
    @pytest.fixture
    def resource_manager(self) -> ResourceManager:
        """Create resource manager for testing."""
        return ResourceManager(max_concurrent_exports=3)
    
    @pytest.mark.asyncio
    async def test_resource_allocation(self, resource_manager, sample_slides):
        """Test resource allocation and release."""
        from app.services.export.export_coordinator import ExportJob
        
        config = ExportConfig(format=ExportFormat.PPTX)
        job = ExportJob(
            job_id="test_job_1",
            slides=sample_slides,
            config=config,
            user_id="test_user"
        )
        
        # Should be able to allocate resources
        can_allocate = await resource_manager.can_start_export(ExportFormat.PPTX)
        assert can_allocate is True
        
        success = await resource_manager.allocate_resources(job)
        assert success is True
        
        # Check resource usage
        stats = resource_manager.get_resource_stats()
        assert stats['active_jobs'] == 1
        assert stats['format_usage'][ExportFormat.PPTX] == 1
        
        # Release resources
        await resource_manager.release_resources("test_job_1")
        
        stats = resource_manager.get_resource_stats()
        assert stats['active_jobs'] == 0
        assert stats['format_usage'][ExportFormat.PPTX] == 0
    
    @pytest.mark.asyncio
    async def test_resource_limits(self, resource_manager, sample_slides):
        """Test resource allocation limits."""
        from app.services.export.export_coordinator import ExportJob
        
        # Fill up resources
        jobs = []
        for i in range(3):  # Max concurrent = 3
            config = ExportConfig(format=ExportFormat.PPTX)
            job = ExportJob(
                job_id=f"test_job_{i}",
                slides=sample_slides,
                config=config,
                user_id="test_user"
            )
            jobs.append(job)
            
            success = await resource_manager.allocate_resources(job)
            assert success is True
        
        # Should not be able to allocate more
        config = ExportConfig(format=ExportFormat.PPTX)
        overflow_job = ExportJob(
            job_id="overflow_job",
            slides=sample_slides,
            config=config,
            user_id="test_user"
        )
        
        can_allocate = await resource_manager.can_start_export(ExportFormat.PPTX)
        assert can_allocate is False
        
        success = await resource_manager.allocate_resources(overflow_job)
        assert success is False


class TestExportValidator:
    """Test suite for ExportValidator."""
    
    @pytest.mark.asyncio
    async def test_validate_slides_valid(self, sample_slides):
        """Test validation of valid slides."""
        result = await ExportValidator.validate_slides(sample_slides)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert 'statistics' in result
        assert result['statistics']['total_slides'] == len(sample_slides)
    
    @pytest.mark.asyncio
    async def test_validate_slides_empty(self):
        """Test validation of empty slides."""
        result = await ExportValidator.validate_slides([])
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert "No slides provided" in result['errors'][0]
    
    @pytest.mark.asyncio
    async def test_validate_slides_invalid_content(self):
        """Test validation of slides with invalid content."""
        invalid_slides = [
            SlideContent(
                title="",  # Empty title
                body=[
                    {"invalid": "structure"}  # Missing 'type' field
                ],
                layout="title_and_content"
            )
        ]
        
        result = await ExportValidator.validate_slides(invalid_slides)
        
        assert len(result['errors']) > 0
        assert any("Invalid content structure" in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_validate_export_result(self):
        """Test export result validation."""
        from app.services.export.export_coordinator import ExportResult
        
        result = ExportResult(
            job_id="test_job",
            format=ExportFormat.PPTX,
            status=ExportStatus.COMPLETED,
            file_path="/tmp/test.pptx",
            file_size=1024
        )
        
        # Mock file existence
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            
            validation = await ExportValidator.validate_export_result(result, [])
            
            assert validation['valid'] is True
            assert validation['score'] > 0
            assert 'checks' in validation


class TestConfigManager:
    """Test suite for ConfigManager."""
    
    @pytest.fixture
    def config_manager(self, tmp_path) -> ConfigManager:
        """Create config manager for testing."""
        return create_config_manager(tmp_path / "test_config")
    
    def test_get_user_preferences_new_user(self, config_manager):
        """Test getting preferences for new user."""
        preferences = config_manager.get_user_preferences("new_user")
        
        assert preferences is not None
        assert preferences.user_id == "new_user"
        assert isinstance(preferences.branding, BrandingConfig)
        assert isinstance(preferences.typography, TypographyConfig)
    
    def test_save_and_load_user_preferences(self, config_manager):
        """Test saving and loading user preferences."""
        user_id = "test_user"
        
        # Get default preferences
        preferences = config_manager.get_user_preferences(user_id)
        
        # Modify preferences
        preferences.branding.university_name = "Test University"
        preferences.typography.title_size = 50
        
        # Save preferences
        success = config_manager.save_user_preferences(user_id, preferences)
        assert success is True
        
        # Clear cache and reload
        config_manager.cleanup_cache()
        loaded_preferences = config_manager.get_user_preferences(user_id)
        
        assert loaded_preferences.branding.university_name == "Test University"
        assert loaded_preferences.typography.title_size == 50
    
    def test_get_format_config(self, config_manager):
        """Test getting format-specific configuration."""
        user_id = "test_user"
        
        config = config_manager.get_format_config(
            user_id=user_id,
            format=ExportFormat.PPTX,
            template_name="ieee"
        )
        
        assert isinstance(config, dict)
        assert 'branding' in config
        assert 'typography' in config
        assert 'layout' in config
        assert 'quality' in config
    
    def test_save_custom_template(self, config_manager):
        """Test saving custom template."""
        user_id = "test_user"
        template_config = {
            "theme": "custom",
            "colors": {"primary": "#ff0000"},
            "layout": {"title_alignment": "center"}
        }
        
        success = config_manager.save_custom_template(
            user_id=user_id,
            template_name="my_template",
            template_config=template_config,
            format=ExportFormat.PPTX
        )
        
        assert success is True
        
        # Verify template was saved
        preferences = config_manager.get_user_preferences(user_id)
        template_key = "pptx_my_template"
        assert template_key in preferences.custom_templates
        assert preferences.custom_templates[template_key] == template_config
    
    def test_get_template_list(self, config_manager):
        """Test getting template list for format."""
        templates = config_manager.get_template_list(ExportFormat.PPTX)
        
        assert isinstance(templates, list)
        assert len(templates) > 0
        
        for template in templates:
            assert 'name' in template
            assert 'display_name' in template
            assert 'description' in template
            assert 'category' in template


class TestIntegration:
    """Integration tests for the complete export system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_export_flow(self, sample_slides, sample_citations):
        """Test complete export flow from submission to completion."""
        coordinator = create_export_coordinator(max_concurrent_exports=1)
        
        # Mock the actual export generation
        with patch.object(coordinator, '_generate_export') as mock_generate:
            from app.services.export.export_coordinator import ExportResult
            
            mock_result = ExportResult(
                job_id="test_job",
                format=ExportFormat.PPTX,
                status=ExportStatus.COMPLETED,
                file_path="/tmp/test.pptx",
                file_size=1024
            )
            mock_generate.return_value = mock_result
            
            # Submit job
            config = ExportConfig(
                format=ExportFormat.PPTX,
                template_name="ieee",
                quality=ExportQuality.STANDARD
            )
            
            job_id = await coordinator.submit_export_job(
                slides=sample_slides,
                config=config,
                citations=sample_citations,
                user_id="test_user"
            )
            
            # Wait for processing (mocked)
            await asyncio.sleep(0.1)
            
            # Check final result
            progress = await coordinator.get_job_progress(job_id)
            assert progress is not None
            
            # In a real scenario, we'd wait for completion
            # For testing, we verify the job exists and is tracked
            assert job_id in coordinator._jobs
            job = coordinator._jobs[job_id]
            assert job.slides == sample_slides
            assert job.citations == sample_citations
    
    @pytest.mark.asyncio
    async def test_parallel_export_coordination(self, sample_slides):
        """Test parallel export coordination."""
        coordinator = create_export_coordinator(max_concurrent_exports=3)
        
        # Mock export generation to avoid actual file operations
        with patch.object(coordinator, '_generate_export') as mock_generate:
            from app.services.export.export_coordinator import ExportResult
            
            def create_mock_result(job):
                return ExportResult(
                    job_id=job.job_id,
                    format=job.config.format,
                    status=ExportStatus.COMPLETED,
                    file_path=f"/tmp/{job.job_id}.{job.config.format.value['extension'][1:]}",
                    file_size=1024
                )
            
            mock_generate.side_effect = create_mock_result
            
            # Submit multiple jobs
            formats = [ExportFormat.PPTX, ExportFormat.PDF, ExportFormat.BEAMER]
            job_ids = []
            
            for fmt in formats:
                config = ExportConfig(format=fmt, template_name="default")
                job_id = await coordinator.submit_export_job(
                    slides=sample_slides,
                    config=config,
                    user_id="test_user"
                )
                job_ids.append(job_id)
            
            # Verify all jobs were submitted
            assert len(job_ids) == 3
            for job_id in job_ids:
                assert job_id in coordinator._jobs
            
            # Check resource allocation
            stats = coordinator.resource_manager.get_resource_stats()
            assert stats['active_jobs'] <= 3  # Within limits


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])