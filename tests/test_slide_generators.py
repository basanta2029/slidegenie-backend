"""Tests for slide generators."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from typing import Dict, Any

from app.services.slides.interfaces import (
    ISlideGenerator, PresentationContent, SlideContent
)
from app.services.slides.config import OutputFormat
from app.services.slides.service import DefaultComponentFactory


class MockSlideGenerator(ISlideGenerator):
    """Mock implementation of slide generator for testing."""
    
    def __init__(self, supported_format: str):
        self.supported_format = supported_format
        self.generate_called = False
        self.export_called = False
    
    async def generate(
        self, 
        content: PresentationContent, 
        output_format: str,
        options: Dict[str, Any] = None
    ) -> bytes:
        self.generate_called = True
        self.last_content = content
        self.last_format = output_format
        self.last_options = options
        return b"mock_presentation_data"
    
    def supports_format(self, format: str) -> bool:
        return format == self.supported_format
    
    async def export_async(self, content, output_format, stream=False):
        self.export_called = True
        if stream:
            async def generate_chunks():
                yield b"chunk1"
                yield b"chunk2"
                yield b"chunk3"
            return generate_chunks()
        else:
            return b"exported_data"


class TestSlideGenerators:
    """Test suite for slide generators."""
    
    @pytest.fixture
    def sample_presentation(self):
        """Create sample presentation content."""
        return PresentationContent(
            title="Test Presentation",
            subtitle="A test subtitle",
            author="Test Author",
            slides=[
                SlideContent(
                    title="Introduction",
                    content="Welcome to the presentation",
                    layout_type="title"
                ),
                SlideContent(
                    title="Main Content",
                    content="This is the main content",
                    bullet_points=["Point 1", "Point 2", "Point 3"],
                    layout_type="content"
                ),
                SlideContent(
                    title="Conclusion",
                    content="Thank you",
                    layout_type="closing"
                )
            ],
            theme="modern"
        )
    
    @pytest.fixture
    def mock_generator(self):
        """Create mock generator."""
        return MockSlideGenerator("pptx")
    
    @pytest.mark.asyncio
    async def test_generator_generate(self, mock_generator, sample_presentation):
        """Test basic generation functionality."""
        result = await mock_generator.generate(
            sample_presentation,
            "pptx",
            {"option1": "value1"}
        )
        
        assert result == b"mock_presentation_data"
        assert mock_generator.generate_called
        assert mock_generator.last_content == sample_presentation
        assert mock_generator.last_format == "pptx"
        assert mock_generator.last_options == {"option1": "value1"}
    
    def test_generator_supports_format(self, mock_generator):
        """Test format support checking."""
        assert mock_generator.supports_format("pptx") is True
        assert mock_generator.supports_format("pdf") is False
        assert mock_generator.supports_format("PPTX") is False  # Case sensitive
    
    @pytest.mark.asyncio
    async def test_generator_streaming_export(self, mock_generator, sample_presentation):
        """Test streaming export functionality."""
        stream = await mock_generator.export_async(
            sample_presentation,
            "pptx",
            stream=True
        )
        
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        
        assert chunks == [b"chunk1", b"chunk2", b"chunk3"]
        assert mock_generator.export_called
    
    @pytest.mark.asyncio
    async def test_generator_non_streaming_export(self, mock_generator, sample_presentation):
        """Test non-streaming export."""
        result = await mock_generator.export_async(
            sample_presentation,
            "pptx",
            stream=False
        )
        
        assert result == b"exported_data"
        assert mock_generator.export_called
    
    def test_default_factory_not_implemented(self):
        """Test that default factory raises NotImplementedError."""
        factory = DefaultComponentFactory()
        
        with pytest.raises(NotImplementedError, match="Generator not implemented"):
            factory.create_generator("pptx")


class TestGeneratorIntegration:
    """Integration tests for generators with service."""
    
    @pytest.fixture
    def mock_factory(self):
        """Create mock factory that returns generators."""
        factory = Mock(spec=DefaultComponentFactory)
        
        # Create different generators for different formats
        generators = {
            "pptx": MockSlideGenerator("pptx"),
            "pdf": MockSlideGenerator("pdf"),
            "google_slides": MockSlideGenerator("google_slides")
        }
        
        factory.create_generator.side_effect = lambda fmt: generators.get(fmt)
        return factory
    
    @pytest.mark.asyncio
    async def test_multiple_format_generation(self, sample_presentation, mock_factory):
        """Test generating in multiple formats."""
        from app.services.slides.service import SlideGenerationService
        
        # Create service with mocked factory
        service = SlideGenerationService(factory=mock_factory)
        
        # Mock other components to avoid NotImplementedError
        service._layout_engine = Mock()
        service._layout_engine.optimize_layout.return_value = sample_presentation.slides[0]
        service._rules_engine = Mock()
        service._rules_engine.validate_presentation.return_value = Mock(is_valid=True)
        service._quality_checker = AsyncMock()
        service._quality_checker.check_quality.return_value = Mock(overall_score=0.9)
        service._orchestrator = AsyncMock()
        service._orchestrator.validate_input.return_value = Mock(is_valid=True)
        service._orchestrator.generate_presentation.return_value = sample_presentation
        
        # Test generation for different formats
        formats = [OutputFormat.PPTX, OutputFormat.PDF]
        
        for fmt in formats:
            result, metadata = await service.generate_presentation(
                "Test content",
                output_format=fmt
            )
            
            assert result == b"mock_presentation_data"
            assert metadata["format"] == fmt.value
    
    @pytest.mark.asyncio
    async def test_generator_caching(self, mock_factory):
        """Test that generators are cached and reused."""
        from app.services.slides.service import SlideGenerationService
        
        service = SlideGenerationService(factory=mock_factory)
        
        # Get generator twice
        gen1 = await service._get_generator("pptx")
        gen2 = await service._get_generator("pptx")
        
        # Should be the same instance
        assert gen1 is gen2
        
        # Factory should only be called once
        mock_factory.create_generator.assert_called_once_with("pptx")


class TestGeneratorEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_presentation(self):
        """Test handling of empty presentation."""
        generator = MockSlideGenerator("pptx")
        
        empty_presentation = PresentationContent(
            title="Empty",
            slides=[]
        )
        
        result = await generator.generate(empty_presentation, "pptx")
        assert result == b"mock_presentation_data"
    
    @pytest.mark.asyncio
    async def test_large_presentation(self):
        """Test handling of large presentations."""
        generator = MockSlideGenerator("pptx")
        
        # Create presentation with many slides
        large_presentation = PresentationContent(
            title="Large Presentation",
            slides=[
                SlideContent(
                    title=f"Slide {i}",
                    content=f"Content for slide {i}" * 100,  # Large content
                    layout_type="content"
                )
                for i in range(100)
            ]
        )
        
        result = await generator.generate(large_presentation, "pptx")
        assert result == b"mock_presentation_data"
        assert len(generator.last_content.slides) == 100
    
    @pytest.mark.asyncio
    async def test_special_characters_in_content(self):
        """Test handling of special characters."""
        generator = MockSlideGenerator("pptx")
        
        special_presentation = PresentationContent(
            title="Special «Characters» Test™",
            slides=[
                SlideContent(
                    title="Unicode: 你好世界 🌍",
                    content="Special chars: < > & \" ' \n \t",
                    bullet_points=["• Bullet", "→ Arrow", "© Copyright"],
                    layout_type="content"
                )
            ]
        )
        
        result = await generator.generate(special_presentation, "pptx")
        assert result == b"mock_presentation_data"
        assert "你好世界" in generator.last_content.slides[0].title


class TestGeneratorPerformance:
    """Performance tests for generators."""
    
    @pytest.mark.asyncio
    async def test_concurrent_generation(self, sample_presentation):
        """Test concurrent generation requests."""
        generator = MockSlideGenerator("pptx")
        
        # Create multiple generation tasks
        tasks = [
            generator.generate(sample_presentation, "pptx", {"task": i})
            for i in range(10)
        ]
        
        # Run concurrently
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 10
        assert all(r == b"mock_presentation_data" for r in results)
    
    @pytest.mark.asyncio
    async def test_streaming_performance(self, sample_presentation):
        """Test streaming export performance."""
        generator = MockSlideGenerator("pptx")
        
        # Time the streaming export
        import time
        start = time.time()
        
        stream = await generator.export_async(
            sample_presentation,
            "pptx",
            stream=True
        )
        
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        
        elapsed = time.time() - start
        
        # Should complete quickly for mock
        assert elapsed < 1.0
        assert len(chunks) == 3


@pytest.mark.parametrize("format,expected", [
    ("pptx", True),
    ("pdf", True),
    ("google_slides", True),
    ("reveal_js", True),
    ("markdown", True),
    ("unknown", False),
])
def test_output_format_validation(format, expected):
    """Test validation of output formats."""
    try:
        OutputFormat(format)
        is_valid = True
    except ValueError:
        is_valid = False
    
    assert is_valid == expected