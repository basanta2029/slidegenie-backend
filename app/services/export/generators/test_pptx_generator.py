"""
Comprehensive tests for the PPTX generator.

This test suite validates all aspects of the PPTX generator including:
- Template system functionality
- Academic formatting compliance
- Image processing and optimization
- Equation rendering
- Citation formatting
- Layout algorithms
- Error handling and edge cases
"""

import io
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from typing import List

from app.domain.schemas.generation import Citation, SlideContent
from app.services.export.generators.pptx_generator import (
    AcademicTemplate,
    BrandingConfig,
    CitationFormatter,
    ColorScheme,
    EquationRenderer,
    ImageProcessor,
    LayoutManager,
    PPTXGenerator,
    SlideLayout,
    TemplateConfig,
    TransitionType,
    Typography,
    create_academic_template_config,
    create_ieee_presentation,
    create_nature_presentation,
)


class TestPPTXGenerator:
    """Test suite for PPTXGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = PPTXGenerator()
        self.sample_slides = self._create_sample_slides()
        self.sample_citations = self._create_sample_citations()
    
    def _create_sample_slides(self) -> List[SlideContent]:
        """Create sample slide content for testing."""
        return [
            SlideContent(
                title="Test Presentation",
                subtitle="A comprehensive test",
                body=[
                    {"type": "text", "content": "Test Author\nTest Institution"}
                ],
                layout="title_slide",
                metadata={"slide_type": "title"}
            ),
            SlideContent(
                title="Introduction",
                body=[
                    {
                        "type": "bullet_list",
                        "items": [
                            "First bullet point",
                            "Second bullet point",
                            "Third bullet point"
                        ]
                    }
                ],
                speaker_notes="This is an introduction slide with bullet points."
            ),
            SlideContent(
                title="Mathematical Content",
                body=[
                    {
                        "type": "equation",
                        "latex": r"E = mc^2"
                    },
                    {
                        "type": "text",
                        "content": "Einstein's famous equation"
                    }
                ]
            )
        ]
    
    def _create_sample_citations(self) -> List[Citation]:
        """Create sample citations for testing."""
        return [
            Citation(
                key="test2024",
                authors=["Test Author", "Another Author"],
                title="A Test Paper",
                year=2024,
                venue="Test Conference",
                doi="10.1000/test.2024",
                bibtex_type="article"
            )
        ]
    
    def test_generator_initialization(self):
        """Test generator initialization with default and custom configs."""
        # Test default initialization
        default_gen = PPTXGenerator()
        assert default_gen.config.template == AcademicTemplate.IEEE
        assert default_gen.config.slide_size == (16, 9)
        
        # Test custom configuration
        custom_config = TemplateConfig(
            template=AcademicTemplate.NATURE,
            slide_size=(4, 3)
        )
        custom_gen = PPTXGenerator(custom_config)
        assert custom_gen.config.template == AcademicTemplate.NATURE
        assert custom_gen.config.slide_size == (4, 3)
    
    def test_create_presentation_basic(self):
        """Test basic presentation creation."""
        presentation = self.generator.create_presentation(self.sample_slides)
        
        assert presentation is not None
        assert len(presentation.slides) == len(self.sample_slides)
        
        # Check slide content
        first_slide = presentation.slides[0]
        assert len(first_slide.shapes) > 0  # Should have some content
    
    def test_create_presentation_with_citations(self):
        """Test presentation creation with citations."""
        presentation = self.generator.create_presentation(
            self.sample_slides, 
            citations=self.sample_citations
        )
        
        # Should have one additional slide for references
        assert len(presentation.slides) == len(self.sample_slides) + 1
    
    def test_create_presentation_with_metadata(self):
        """Test presentation creation with metadata."""
        metadata = {
            "title": "Test Presentation",
            "author": "Test Author",
            "subject": "Testing",
            "description": "A test presentation"
        }
        
        presentation = self.generator.create_presentation(
            self.sample_slides,
            metadata=metadata
        )
        
        # Check that metadata was applied
        core_props = presentation.core_properties
        assert core_props.title == metadata["title"]
        assert core_props.author == metadata["author"]
    
    def test_save_presentation_to_buffer(self):
        """Test saving presentation to BytesIO buffer."""
        presentation = self.generator.create_presentation(self.sample_slides)
        
        buffer = io.BytesIO()
        self.generator.save_presentation(buffer)
        
        assert buffer.tell() > 0  # Buffer should have content
        buffer.seek(0)
        content = buffer.read()
        assert len(content) > 1000  # Should be a substantial file
    
    def test_save_presentation_to_file(self):
        """Test saving presentation to file."""
        presentation = self.generator.create_presentation(self.sample_slides)
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            self.generator.save_presentation(tmp_path)
            
            # Check file exists and has content
            assert Path(tmp_path).exists()
            assert Path(tmp_path).stat().st_size > 1000
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_export_to_buffer(self):
        """Test export_to_buffer method."""
        buffer = self.generator.export_to_buffer(
            self.sample_slides,
            citations=self.sample_citations,
            metadata={"title": "Test Export"}
        )
        
        assert isinstance(buffer, io.BytesIO)
        assert buffer.tell() > 0
    
    def test_export_to_file(self):
        """Test export_to_file method."""
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            self.generator.export_to_file(
                self.sample_slides,
                tmp_path,
                citations=self.sample_citations
            )
            
            assert Path(tmp_path).exists()
            assert Path(tmp_path).stat().st_size > 1000
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_template_application(self):
        """Test different template applications."""
        templates = [AcademicTemplate.IEEE, AcademicTemplate.NATURE, AcademicTemplate.ACM]
        
        for template in templates:
            config = TemplateConfig(template=template)
            generator = PPTXGenerator(config)
            presentation = generator.create_presentation(self.sample_slides)
            
            assert presentation is not None
            assert len(presentation.slides) == len(self.sample_slides)
    
    def test_slide_layout_detection(self):
        """Test slide layout detection logic."""
        # Title slide
        title_slide = SlideContent(
            title="Title Slide",
            metadata={"slide_type": "title"}
        )
        layout = self.generator._determine_layout(title_slide)
        assert layout == SlideLayout.TITLE_SLIDE
        
        # Section header
        section_slide = SlideContent(
            title="Section Header",
            body=[],
            metadata={"slide_type": "section"}
        )
        layout = self.generator._determine_layout(section_slide)
        assert layout == SlideLayout.SECTION_HEADER
        
        # Two content
        two_content_slide = SlideContent(
            title="Two Content",
            body=[
                {"type": "text", "content": "Left content"},
                {"type": "text", "content": "Right content"}
            ]
        )
        layout = self.generator._determine_layout(two_content_slide)
        assert layout == SlideLayout.TWO_CONTENT
    
    def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Empty slides list
        with pytest.raises(ValueError):
            self.generator.export_to_buffer([])
        
        # Invalid slide content
        invalid_slides = [SlideContent(title="", body=[])]
        # Should not crash, but might generate error slide
        presentation = self.generator.create_presentation(invalid_slides)
        assert presentation is not None


class TestTemplateConfig:
    """Test suite for template configuration system."""
    
    def test_default_template_config(self):
        """Test default template configuration."""
        config = TemplateConfig()
        
        assert config.template == AcademicTemplate.IEEE
        assert config.slide_size == (16, 9)
        assert config.color_scheme.primary == "#1f4e79"
        assert config.typography.title_font == "Calibri"
    
    def test_academic_template_creation(self):
        """Test academic template creation function."""
        config = create_academic_template_config(
            template=AcademicTemplate.NATURE,
            university_name="Test University",
            logo_path="/path/to/logo.png",
            custom_colors={"primary": "#ff0000"}
        )
        
        assert config.template == AcademicTemplate.NATURE
        assert config.branding.university_name == "Test University"
        assert config.branding.logo_path == "/path/to/logo.png"
        assert config.color_scheme.primary == "#ff0000"
    
    def test_color_scheme_validation(self):
        """Test color scheme validation."""
        scheme = ColorScheme(
            primary="#ff0000",
            secondary="#00ff00",
            accent="#0000ff"
        )
        
        assert scheme.primary == "#ff0000"
        assert scheme.secondary == "#00ff00"
        assert scheme.accent == "#0000ff"
    
    def test_typography_configuration(self):
        """Test typography configuration."""
        typography = Typography(
            title_font="Arial",
            body_font="Times New Roman",
            title_size=48,
            body_size=20
        )
        
        assert typography.title_font == "Arial"
        assert typography.body_font == "Times New Roman"
        assert typography.title_size == 48
        assert typography.body_size == 20


class TestCitationFormatter:
    """Test suite for citation formatting."""
    
    def setup_method(self):
        """Set up citation formatter."""
        self.formatter = CitationFormatter()
        self.sample_citation = Citation(
            key="test2024",
            authors=["John Doe", "Jane Smith"],
            title="A Test Paper on Important Topics",
            year=2024,
            venue="Test Conference Proceedings",
            doi="10.1000/test.2024"
        )
    
    def test_ieee_formatting(self):
        """Test IEEE citation formatting."""
        formatted = self.formatter.format_citation(self.sample_citation, 'ieee')
        
        assert "John Doe and Jane Smith" in formatted
        assert '"A Test Paper on Important Topics"' in formatted
        assert "Test Conference Proceedings" in formatted
        assert "2024" in formatted
        assert "doi: 10.1000/test.2024" in formatted
    
    def test_apa_formatting(self):
        """Test APA citation formatting."""
        formatted = self.formatter.format_citation(self.sample_citation, 'apa')
        
        assert "(2024)" in formatted
        assert "A Test Paper on Important Topics" in formatted
        assert "*Test Conference Proceedings*" in formatted
    
    def test_mla_formatting(self):
        """Test MLA citation formatting."""
        formatted = self.formatter.format_citation(self.sample_citation, 'mla')
        
        assert "John Doe et al." in formatted or "John Doe, Jane Smith" in formatted
        assert '"A Test Paper on Important Topics"' in formatted
        assert "*Test Conference Proceedings*" in formatted
    
    def test_multiple_authors_handling(self):
        """Test handling of multiple authors."""
        many_authors = Citation(
            key="many2024",
            authors=["A", "B", "C", "D", "E"],
            title="Many Authors Paper",
            year=2024
        )
        
        ieee_formatted = self.formatter.format_citation(many_authors, 'ieee')
        assert "et al." in ieee_formatted
    
    def test_missing_fields_handling(self):
        """Test handling of missing citation fields."""
        minimal_citation = Citation(
            key="minimal2024",
            authors=["Author"],
            title="Minimal Citation"
        )
        
        formatted = self.formatter.format_citation(minimal_citation, 'ieee')
        assert "Author" in formatted
        assert "Minimal Citation" in formatted


class TestEquationRenderer:
    """Test suite for equation rendering."""
    
    def setup_method(self):
        """Set up equation renderer."""
        self.renderer = EquationRenderer()
    
    def test_equation_extraction(self):
        """Test LaTeX equation extraction from text."""
        text = "Here is an inline equation $E = mc^2$ and a display equation $$\\int_0^1 x dx = \\frac{1}{2}$$"
        
        equations = self.renderer.extract_equations_from_text(text)
        
        assert len(equations) == 2
        assert equations[0][1] == "E = mc^2"
        assert equations[1][1] == "\\int_0^1 x dx = \\frac{1}{2}"
    
    def test_equation_rendering(self):
        """Test equation rendering to image."""
        latex_code = "E = mc^2"
        
        image_buffer = self.renderer.render_latex_to_image(latex_code)
        
        # Should return a BytesIO object (even if simplified)
        assert image_buffer is not None
        assert isinstance(image_buffer, io.BytesIO)
    
    def test_complex_equation_extraction(self):
        """Test extraction of complex equation environments."""
        text = """
        The following equation shows the relationship:
        \\begin{equation}
        \\frac{\\partial u}{\\partial t} = \\Delta u + f(u)
        \\end{equation}
        This is important for our analysis.
        """
        
        equations = self.renderer.extract_equations_from_text(text)
        
        assert len(equations) == 1
        assert "\\frac{\\partial u}{\\partial t}" in equations[0][1]


class TestImageProcessor:
    """Test suite for image processing."""
    
    def setup_method(self):
        """Set up image processor."""
        self.processor = ImageProcessor()
    
    def test_placeholder_image_creation(self):
        """Test placeholder image creation."""
        placeholder = self.processor._create_placeholder_image((800, 600))
        
        assert isinstance(placeholder, io.BytesIO)
        assert placeholder.tell() > 0
    
    @patch('requests.get')
    def test_url_image_processing(self, mock_get):
        """Test processing image from URL."""
        # Mock successful image download
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # This will fail because the content isn't a real image,
        # but should fall back to placeholder
        result = self.processor.process_image("http://example.com/image.jpg")
        
        assert isinstance(result, io.BytesIO)
    
    def test_image_format_support(self):
        """Test supported image formats."""
        supported = self.processor.supported_formats
        
        assert '.jpg' in supported
        assert '.png' in supported
        assert '.gif' in supported


class TestLayoutManager:
    """Test suite for layout management."""
    
    def setup_method(self):
        """Set up layout manager."""
        self.config = TemplateConfig()
        self.manager = LayoutManager(self.config)
    
    def test_content_area_calculation(self):
        """Test content area calculation."""
        # Mock slide object
        mock_slide = Mock()
        
        left, top, width, height = self.manager.calculate_content_area(mock_slide)
        
        # Should respect margins
        assert left == self.config.margins[0]
        assert top == self.config.margins[1]
        assert width == self.config.slide_size[0] - self.config.margins[0] - self.config.margins[2]
        assert height == self.config.slide_size[1] - self.config.margins[1] - self.config.margins[3]


class TestConvenienceFunctions:
    """Test suite for convenience functions."""
    
    def setup_method(self):
        """Set up test data."""
        self.sample_slides = [
            SlideContent(
                title="Test Slide",
                body=[{"type": "text", "content": "Test content"}]
            )
        ]
        self.sample_citations = [
            Citation(
                key="test2024",
                authors=["Test Author"],
                title="Test Paper",
                year=2024
            )
        ]
    
    def test_create_ieee_presentation(self):
        """Test IEEE presentation creation function."""
        buffer = create_ieee_presentation(
            slides=self.sample_slides,
            citations=self.sample_citations,
            university_name="Test University"
        )
        
        assert isinstance(buffer, io.BytesIO)
        assert buffer.tell() > 0
    
    def test_create_nature_presentation(self):
        """Test Nature presentation creation function."""
        buffer = create_nature_presentation(
            slides=self.sample_slides,
            citations=self.sample_citations,
            university_name="Test University"
        )
        
        assert isinstance(buffer, io.BytesIO)
        assert buffer.tell() > 0


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""
    
    def test_empty_slides_handling(self):
        """Test handling of empty slides."""
        generator = PPTXGenerator()
        
        # Empty slides list should raise error
        with pytest.raises(Exception):
            generator.create_presentation([])
    
    def test_malformed_slide_content(self):
        """Test handling of malformed slide content."""
        generator = PPTXGenerator()
        
        # Slide with no title or content
        empty_slide = SlideContent()
        
        # Should handle gracefully (may create error slide)
        presentation = generator.create_presentation([empty_slide])
        assert presentation is not None
    
    def test_invalid_image_paths(self):
        """Test handling of invalid image paths."""
        generator = PPTXGenerator()
        
        slide_with_bad_image = SlideContent(
            title="Test Slide",
            body=[
                {
                    "type": "image",
                    "path": "/nonexistent/image.jpg"
                }
            ]
        )
        
        # Should handle gracefully and create placeholder
        presentation = generator.create_presentation([slide_with_bad_image])
        assert presentation is not None
    
    def test_large_slide_count(self):
        """Test handling of large numbers of slides."""
        generator = PPTXGenerator()
        
        # Create many slides
        many_slides = [
            SlideContent(
                title=f"Slide {i}",
                body=[{"type": "text", "content": f"Content for slide {i}"}]
            )
            for i in range(100)
        ]
        
        # Should handle without crashing
        presentation = generator.create_presentation(many_slides)
        assert presentation is not None
        assert len(presentation.slides) == 100


# Integration tests

class TestIntegration:
    """Integration tests for the complete PPTX generation pipeline."""
    
    def test_full_academic_presentation(self):
        """Test creating a complete academic presentation."""
        # Create comprehensive slide content
        slides = [
            SlideContent(
                title="Advanced Research in Machine Learning",
                subtitle="Novel Approaches to Deep Neural Networks",
                body=[
                    {"type": "text", "content": "Dr. Jane Smith\nMIT CSAIL\nAAAI Conference 2024"}
                ],
                metadata={"slide_type": "title"}
            ),
            SlideContent(
                title="Research Overview",
                body=[
                    {
                        "type": "bullet_list",
                        "items": [
                            "Novel neural architectures",
                            "Optimization techniques",
                            "Empirical validation",
                            "Real-world applications"
                        ]
                    }
                ]
            ),
            SlideContent(
                title="Mathematical Framework",
                body=[
                    {
                        "type": "equation",
                        "latex": r"\\mathcal{L}(\\theta) = \\frac{1}{n} \\sum_{i=1}^n \\ell(f(x_i; \\theta), y_i)"
                    },
                    {
                        "type": "text",
                        "content": "Where θ represents the model parameters"
                    }
                ]
            ),
            SlideContent(
                title="Experimental Results",
                body=[
                    {
                        "type": "chart",
                        "chart_type": "column",
                        "data": {
                            "categories": ["Dataset A", "Dataset B", "Dataset C"],
                            "series": [
                                {"name": "Baseline", "values": [0.85, 0.78, 0.92]},
                                {"name": "Our Method", "values": [0.91, 0.84, 0.96]}
                            ]
                        }
                    }
                ]
            )
        ]
        
        citations = [
            Citation(
                key="smith2024",
                authors=["Jane Smith", "John Doe"],
                title="Advanced Neural Network Architectures",
                year=2024,
                venue="AAAI",
                doi="10.1000/aaai.2024.123"
            )
        ]
        
        # Create with IEEE template
        config = create_academic_template_config(
            template=AcademicTemplate.IEEE,
            university_name="Massachusetts Institute of Technology",
            custom_colors={"primary": "#8c1515"}
        )
        
        generator = PPTXGenerator(config)
        buffer = generator.export_to_buffer(
            slides=slides,
            citations=citations,
            metadata={
                "title": "Advanced Research in Machine Learning",
                "author": "Dr. Jane Smith",
                "subject": "Machine Learning Research"
            }
        )
        
        # Validate output
        assert isinstance(buffer, io.BytesIO)
        assert buffer.tell() > 5000  # Should be substantial file
        
        # Test file creation
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            with open(tmp_path, 'wb') as f:
                f.write(buffer.getvalue())
            
            assert Path(tmp_path).exists()
            assert Path(tmp_path).stat().st_size > 5000
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    # Run basic tests
    print("Running PPTX Generator Tests...")
    
    # Test basic functionality
    test_gen = TestPPTXGenerator()
    test_gen.setup_method()
    
    try:
        test_gen.test_generator_initialization()
        print("✓ Generator initialization test passed")
        
        test_gen.test_create_presentation_basic()
        print("✓ Basic presentation creation test passed")
        
        test_gen.test_export_to_buffer()
        print("✓ Export to buffer test passed")
        
        # Test citation formatting
        citation_test = TestCitationFormatter()
        citation_test.setup_method()
        citation_test.test_ieee_formatting()
        print("✓ Citation formatting test passed")
        
        # Test equation rendering
        equation_test = TestEquationRenderer()
        equation_test.setup_method()
        equation_test.test_equation_extraction()
        print("✓ Equation extraction test passed")
        
        print("\nAll basic tests passed! ✓")
        print("Run 'pytest' for comprehensive test suite.")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise