"""
Test suite for PDF generator functionality.

This module provides comprehensive tests for all PDF generation features:
- Different PDF formats (presentation, handout, notes, print-optimized)
- Various quality settings and layouts
- Template configurations for academic styles
- Image processing and optimization
- Font handling and text rendering
- Watermarks and page decorations
"""

import os
import tempfile
import unittest
from pathlib import Path
from typing import List

from pdf_generator import (
    PDFGenerator,
    PDFConfig,
    PDFSlide,
    PDFFormat,
    PDFQuality,
    HandoutLayout,
    PageSize,
    PageOrientation,
    create_presentation_pdf,
    create_handout_pdf,
    create_notes_pdf,
    create_print_pdf,
    get_ieee_config,
    get_acm_config,
    get_nature_config
)
from app.domain.schemas.generation import Citation


class TestPDFGenerator(unittest.TestCase):
    """Test cases for PDF generator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create sample slides
        self.sample_slides = [
            PDFSlide(
                title="Introduction to Machine Learning",
                content="""
                Machine learning is a subset of artificial intelligence that focuses on the development of algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience.
                
                Key concepts include:
                • Supervised learning
                • Unsupervised learning
                • Reinforcement learning
                • Deep learning
                """,
                notes="This slide introduces the basic concepts of machine learning. Spend about 3 minutes explaining each type of learning with examples.",
                slide_number=1,
                citations=[
                    Citation(
                        title="Pattern Recognition and Machine Learning",
                        authors="Christopher Bishop",
                        year="2006",
                        url="https://example.com/bishop2006"
                    )
                ]
            ),
            PDFSlide(
                title="Neural Networks Architecture",
                content="""
                Neural networks are computational models inspired by biological neural networks. They consist of interconnected nodes (neurons) organized in layers.
                
                Basic architecture:
                • Input layer: Receives data
                • Hidden layers: Process information
                • Output layer: Produces results
                • Activation functions: Introduce non-linearity
                """,
                notes="Draw a simple neural network diagram on the whiteboard. Explain forward propagation step by step.",
                slide_number=2,
                images=[
                    {
                        "path": "https://via.placeholder.com/400x300/0066CC/FFFFFF?text=Neural+Network",
                        "alt_text": "Basic neural network architecture diagram",
                        "caption": "Figure 1: Simple feedforward neural network"
                    }
                ]
            ),
            PDFSlide(
                title="Training Process",
                content="""
                Training a neural network involves adjusting weights and biases to minimize prediction errors.
                
                Key steps:
                1. Initialize weights randomly
                2. Forward pass: Compute predictions
                3. Calculate loss function
                4. Backward pass: Compute gradients
                5. Update weights using optimization algorithm
                6. Repeat until convergence
                """,
                notes="Emphasize the iterative nature of training. Mention common optimization algorithms like SGD, Adam, and RMSprop.",
                slide_number=3
            ),
            PDFSlide(
                title="Applications and Future Directions",
                content="""
                Machine learning applications are rapidly expanding across various domains:
                
                Current applications:
                • Computer vision and image recognition
                • Natural language processing
                • Recommendation systems
                • Autonomous vehicles
                • Medical diagnosis
                
                Future directions:
                • Explainable AI
                • Federated learning
                • Quantum machine learning
                • Neuromorphic computing
                """,
                notes="Discuss recent breakthroughs and ongoing research challenges. Mention ethical considerations in AI development.",
                slide_number=4,
                citations=[
                    Citation(
                        title="Deep Learning",
                        authors="Ian Goodfellow, Yoshua Bengio, Aaron Courville",
                        year="2016",
                        url="https://example.com/goodfellow2016"
                    )
                ]
            )
        ]
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_presentation_pdf_generation(self):
        """Test standard presentation PDF generation."""
        output_path = os.path.join(self.temp_dir, "test_presentation.pdf")
        
        config = PDFConfig(
            format=PDFFormat.PRESENTATION,
            quality=PDFQuality.STANDARD,
            page_size=PageSize.A4,
            orientation=PageOrientation.LANDSCAPE,
            include_toc=True,
            include_bookmarks=True
        )
        
        generator = PDFGenerator(config)
        result = generator.generate_pdf(self.sample_slides, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 1000)  # Should have some content
    
    def test_handout_pdf_generation(self):
        """Test handout PDF generation with different layouts."""
        layouts_to_test = [
            HandoutLayout.LAYOUT_2x2,
            HandoutLayout.LAYOUT_2x3,
            HandoutLayout.LAYOUT_3x3
        ]
        
        for layout in layouts_to_test:
            with self.subTest(layout=layout):
                output_path = os.path.join(self.temp_dir, f"test_handout_{layout.name}.pdf")
                
                config = PDFConfig(
                    format=PDFFormat.HANDOUT,
                    handout_layout=layout,
                    quality=PDFQuality.STANDARD,
                    page_size=PageSize.A4,
                    orientation=PageOrientation.PORTRAIT
                )
                
                generator = PDFGenerator(config)
                result = generator.generate_pdf(self.sample_slides, output_path)
                
                self.assertTrue(result, f"Failed to generate handout with layout {layout}")
                self.assertTrue(os.path.exists(output_path))
    
    def test_notes_pdf_generation(self):
        """Test notes PDF generation."""
        output_path = os.path.join(self.temp_dir, "test_notes.pdf")
        
        config = PDFConfig(
            format=PDFFormat.NOTES,
            quality=PDFQuality.STANDARD,
            page_size=PageSize.A4,
            orientation=PageOrientation.PORTRAIT,
            include_page_numbers=True,
            include_footers=True
        )
        
        generator = PDFGenerator(config)
        result = generator.generate_pdf(self.sample_slides, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
    
    def test_print_optimized_pdf(self):
        """Test print-optimized PDF generation."""
        output_path = os.path.join(self.temp_dir, "test_print.pdf")
        
        config = PDFConfig(
            format=PDFFormat.PRINT_OPTIMIZED,
            quality=PDFQuality.PRINT_READY,
            high_contrast=True,
            image_dpi=300,
            compress_images=False
        )
        
        generator = PDFGenerator(config)
        result = generator.generate_pdf(self.sample_slides, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
    
    def test_watermark_functionality(self):
        """Test watermark addition."""
        output_path = os.path.join(self.temp_dir, "test_watermark.pdf")
        
        config = PDFConfig(
            format=PDFFormat.PRESENTATION,
            watermark_text="CONFIDENTIAL",
            watermark_opacity=0.2,
            watermark_rotation=45
        )
        
        generator = PDFGenerator(config)
        result = generator.generate_pdf(self.sample_slides, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
    
    def test_different_page_sizes(self):
        """Test different page sizes and orientations."""
        test_configs = [
            (PageSize.A4, PageOrientation.PORTRAIT),
            (PageSize.A4, PageOrientation.LANDSCAPE),
            (PageSize.LETTER, PageOrientation.PORTRAIT),
            (PageSize.A3, PageOrientation.LANDSCAPE)
        ]
        
        for page_size, orientation in test_configs:
            with self.subTest(page_size=page_size, orientation=orientation):
                output_path = os.path.join(self.temp_dir, f"test_{page_size.name}_{orientation.value}.pdf")
                
                config = PDFConfig(
                    format=PDFFormat.PRESENTATION,
                    page_size=page_size,
                    orientation=orientation
                )
                
                generator = PDFGenerator(config)
                result = generator.generate_pdf(self.sample_slides, output_path)
                
                self.assertTrue(result)
                self.assertTrue(os.path.exists(output_path))
    
    def test_quality_settings(self):
        """Test different quality settings."""
        qualities = [PDFQuality.DRAFT, PDFQuality.STANDARD, PDFQuality.HIGH_QUALITY]
        
        for quality in qualities:
            with self.subTest(quality=quality):
                output_path = os.path.join(self.temp_dir, f"test_{quality.value}.pdf")
                
                config = PDFConfig(
                    format=PDFFormat.PRESENTATION,
                    quality=quality
                )
                
                generator = PDFGenerator(config)
                result = generator.generate_pdf(self.sample_slides, output_path)
                
                self.assertTrue(result)
                self.assertTrue(os.path.exists(output_path))
    
    def test_academic_templates(self):
        """Test academic template configurations."""
        template_configs = [
            ("ieee", get_ieee_config()),
            ("acm", get_acm_config()),
            ("nature", get_nature_config())
        ]
        
        for template_name, config in template_configs:
            with self.subTest(template=template_name):
                output_path = os.path.join(self.temp_dir, f"test_{template_name}.pdf")
                
                generator = PDFGenerator(config)
                result = generator.generate_pdf(self.sample_slides, output_path)
                
                self.assertTrue(result, f"Failed to generate PDF with {template_name} template")
                self.assertTrue(os.path.exists(output_path))
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test presentation PDF
        output_path = os.path.join(self.temp_dir, "convenience_presentation.pdf")
        result = create_presentation_pdf(self.sample_slides, output_path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        
        # Test handout PDF
        output_path = os.path.join(self.temp_dir, "convenience_handout.pdf")
        result = create_handout_pdf(self.sample_slides, output_path, HandoutLayout.LAYOUT_2x2)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        
        # Test notes PDF
        output_path = os.path.join(self.temp_dir, "convenience_notes.pdf")
        result = create_notes_pdf(self.sample_slides, output_path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        
        # Test print PDF
        output_path = os.path.join(self.temp_dir, "convenience_print.pdf")
        result = create_print_pdf(self.sample_slides, output_path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
    
    def test_custom_margins_and_fonts(self):
        """Test custom margins and font settings."""
        output_path = os.path.join(self.temp_dir, "test_custom.pdf")
        
        config = PDFConfig(
            format=PDFFormat.PRESENTATION,
            margin_top=50,
            margin_bottom=50,
            margin_left=100,
            margin_right=100,
            title_font="Helvetica-Bold",
            body_font="Times-Roman",
            font_size_title=20,
            font_size_body=14,
            primary_color="#003366",
            accent_color="#0066CC"
        )
        
        generator = PDFGenerator(config)
        result = generator.generate_pdf(self.sample_slides, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
    
    def test_metadata_addition(self):
        """Test PDF metadata addition."""
        output_path = os.path.join(self.temp_dir, "test_metadata.pdf")
        
        metadata = {
            'Title': 'Test Presentation',
            'Author': 'Test Author',
            'Subject': 'Machine Learning Tutorial',
            'Keywords': 'ML, AI, Neural Networks'
        }
        
        generator = PDFGenerator()
        result = generator.generate_pdf(self.sample_slides, output_path, metadata)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
    
    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test with invalid output path
        invalid_path = "/invalid/path/test.pdf"
        generator = PDFGenerator()
        result = generator.generate_pdf(self.sample_slides, invalid_path)
        self.assertFalse(result)
        
        # Test with empty slides
        output_path = os.path.join(self.temp_dir, "test_empty.pdf")
        result = generator.generate_pdf([], output_path)
        # Should handle empty slides gracefully
        self.assertTrue(result)


class TestPDFConfiguration(unittest.TestCase):
    """Test PDF configuration options."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PDFConfig()
        
        self.assertEqual(config.format, PDFFormat.PRESENTATION)
        self.assertEqual(config.quality, PDFQuality.STANDARD)
        self.assertEqual(config.page_size, PageSize.A4)
        self.assertEqual(config.orientation, PageOrientation.PORTRAIT)
        self.assertTrue(config.include_toc)
        self.assertTrue(config.include_bookmarks)
    
    def test_custom_config(self):
        """Test custom configuration creation."""
        config = PDFConfig(
            format=PDFFormat.HANDOUT,
            quality=PDFQuality.HIGH_QUALITY,
            page_size=PageSize.LETTER,
            orientation=PageOrientation.LANDSCAPE,
            handout_layout=HandoutLayout.LAYOUT_3x3,
            watermark_text="DRAFT",
            include_toc=False
        )
        
        self.assertEqual(config.format, PDFFormat.HANDOUT)
        self.assertEqual(config.quality, PDFQuality.HIGH_QUALITY)
        self.assertEqual(config.page_size, PageSize.LETTER)
        self.assertEqual(config.orientation, PageOrientation.LANDSCAPE)
        self.assertEqual(config.handout_layout, HandoutLayout.LAYOUT_3x3)
        self.assertEqual(config.watermark_text, "DRAFT")
        self.assertFalse(config.include_toc)
    
    def test_template_configs(self):
        """Test predefined template configurations."""
        ieee_config = get_ieee_config()
        self.assertEqual(ieee_config.citation_style, "ieee")
        self.assertEqual(ieee_config.primary_color, "#003366")
        
        acm_config = get_acm_config()
        self.assertEqual(acm_config.citation_style, "acm")
        self.assertEqual(acm_config.primary_color, "#FF6900")
        
        nature_config = get_nature_config()
        self.assertEqual(nature_config.citation_style, "nature")
        self.assertTrue(nature_config.high_contrast)


def run_demo():
    """Run a demonstration of PDF generation capabilities."""
    print("PDF Generator Demo")
    print("=" * 50)
    
    # Create sample data
    demo_slides = [
        PDFSlide(
            title="Demo: PDF Generation Features",
            content="""
            This demonstration showcases the comprehensive PDF generation capabilities:
            
            • Multiple output formats (presentation, handout, notes, print-optimized)
            • Various quality settings and page layouts
            • Academic template configurations
            • Image processing and optimization
            • Watermarks and page decorations
            • Table of contents and bookmarks
            """,
            notes="This is a demonstration of the PDF generator's capabilities.",
            slide_number=1
        ),
        PDFSlide(
            title="Technical Features",
            content="""
            Advanced technical features include:
            
            • High-quality image processing with compression
            • Custom font support and text rendering
            • Flexible page layouts and margins
            • Accessibility features for tagged PDFs
            • Metadata support for document properties
            • Error handling and validation
            """,
            notes="Highlight the technical sophistication of the system.",
            slide_number=2
        )
    ]
    
    # Create output directory
    output_dir = "pdf_demo_output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Generate different PDF formats
        print("1. Generating presentation PDF...")
        create_presentation_pdf(demo_slides, f"{output_dir}/demo_presentation.pdf")
        
        print("2. Generating handout PDF (2x2 layout)...")
        create_handout_pdf(demo_slides, f"{output_dir}/demo_handout.pdf", HandoutLayout.LAYOUT_2x2)
        
        print("3. Generating notes PDF...")
        create_notes_pdf(demo_slides, f"{output_dir}/demo_notes.pdf")
        
        print("4. Generating print-optimized PDF...")
        create_print_pdf(demo_slides, f"{output_dir}/demo_print.pdf")
        
        # Generate with academic templates
        print("5. Generating IEEE style PDF...")
        ieee_generator = PDFGenerator(get_ieee_config())
        ieee_generator.generate_pdf(demo_slides, f"{output_dir}/demo_ieee.pdf")
        
        print("6. Generating ACM style PDF...")
        acm_generator = PDFGenerator(get_acm_config())
        acm_generator.generate_pdf(demo_slides, f"{output_dir}/demo_acm.pdf")
        
        # Generate with watermark
        print("7. Generating PDF with watermark...")
        watermark_config = PDFConfig(
            format=PDFFormat.PRESENTATION,
            watermark_text="CONFIDENTIAL",
            watermark_opacity=0.15
        )
        watermark_generator = PDFGenerator(watermark_config)
        watermark_generator.generate_pdf(demo_slides, f"{output_dir}/demo_watermark.pdf")
        
        print(f"\nDemo complete! Check the '{output_dir}' directory for generated PDFs.")
        
    except Exception as e:
        print(f"Demo failed: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo()
    else:
        unittest.main()