"""
SlideGenie PDF Generator Integration Example.

This module demonstrates how to integrate the PDF generator with the SlideGenie
presentation system, showing conversion from SlideGenie's internal format to 
PDF slides and handling of various presentation features.
"""

from typing import Dict, List, Optional, Any
from dataclasses import asdict

from pdf_generator import (
    PDFGenerator,
    PDFConfig,
    PDFSlide,
    PDFFormat,
    PDFQuality,
    HandoutLayout,
    PageSize,
    PageOrientation,
    get_ieee_config,
    get_acm_config,
    get_nature_config
)
from app.domain.schemas.generation import Citation, SlideContent


class SlideGeniePDFExporter:
    """
    SlideGenie PDF export service that converts presentations to various PDF formats.
    
    This class provides the main interface between SlideGenie's presentation system
    and the PDF generator, handling format conversion and configuration management.
    """
    
    def __init__(self):
        self.supported_formats = {
            'presentation': PDFFormat.PRESENTATION,
            'handout': PDFFormat.HANDOUT,
            'notes': PDFFormat.NOTES,
            'print': PDFFormat.PRINT_OPTIMIZED
        }
        
        self.quality_levels = {
            'draft': PDFQuality.DRAFT,
            'standard': PDFQuality.STANDARD,
            'high': PDFQuality.HIGH_QUALITY,
            'print_ready': PDFQuality.PRINT_READY
        }
        
        self.academic_templates = {
            'ieee': get_ieee_config,
            'acm': get_acm_config,
            'nature': get_nature_config
        }
    
    def export_presentation(self, 
                          presentation_data: Dict[str, Any],
                          output_path: str,
                          export_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Export a SlideGenie presentation to PDF.
        
        Args:
            presentation_data: SlideGenie presentation data
            output_path: Path where PDF should be saved
            export_options: PDF export configuration options
            
        Returns:
            Dictionary with export results and metadata
        """
        try:
            # Parse export options
            options = export_options or {}
            
            # Convert SlideGenie data to PDF slides
            pdf_slides = self._convert_slides(presentation_data.get('slides', []))
            
            # Create PDF configuration
            config = self._create_pdf_config(options)
            
            # Generate PDF
            generator = PDFGenerator(config)
            
            # Prepare metadata
            metadata = self._extract_metadata(presentation_data)
            
            # Generate PDF
            success = generator.generate_pdf(pdf_slides, output_path, metadata)
            
            if success:
                # Get file information
                import os
                file_size = os.path.getsize(output_path)
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'file_size': file_size,
                    'format': config.format.value,
                    'quality': config.quality.value,
                    'slide_count': len(pdf_slides),
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'error': 'PDF generation failed',
                    'output_path': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_path': None
            }
    
    def _convert_slides(self, slides_data: List[Dict[str, Any]]) -> List[PDFSlide]:
        """Convert SlideGenie slide data to PDF slides."""
        pdf_slides = []
        
        for i, slide_data in enumerate(slides_data, 1):
            # Handle different slide content formats
            if isinstance(slide_data.get('content'), dict):
                # Structured content
                content_obj = slide_data['content']
                title = content_obj.get('title', '')
                content = self._format_slide_content(content_obj)
            else:
                # Simple content
                title = slide_data.get('title', f'Slide {i}')
                content = str(slide_data.get('content', ''))
            
            # Extract images
            images = self._extract_images(slide_data)
            
            # Extract citations
            citations = self._extract_citations(slide_data)
            
            # Create PDF slide
            pdf_slide = PDFSlide(
                title=title,
                content=content,
                notes=slide_data.get('speaker_notes', ''),
                images=images,
                citations=citations,
                slide_number=i,
                layout_type=slide_data.get('layout', 'title_and_content')
            )
            
            pdf_slides.append(pdf_slide)
        
        return pdf_slides
    
    def _format_slide_content(self, content_obj: Dict[str, Any]) -> str:
        """Format structured slide content into text."""
        formatted_content = []
        
        # Handle different content types
        if 'sections' in content_obj:
            for section in content_obj['sections']:
                if section.get('type') == 'bullet_points':
                    formatted_content.append("• " + "\n• ".join(section.get('items', [])))
                elif section.get('type') == 'numbered_list':
                    items = section.get('items', [])
                    for j, item in enumerate(items, 1):
                        formatted_content.append(f"{j}. {item}")
                elif section.get('type') == 'text':
                    formatted_content.append(section.get('content', ''))
                elif section.get('type') == 'code':
                    code_content = section.get('content', '')
                    formatted_content.append(f"```\n{code_content}\n```")
        
        # Handle simple text content
        elif 'text' in content_obj:
            formatted_content.append(content_obj['text'])
        
        # Handle bullet points
        elif 'bullet_points' in content_obj:
            formatted_content.append("• " + "\n• ".join(content_obj['bullet_points']))
        
        return "\n\n".join(formatted_content)
    
    def _extract_images(self, slide_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract image data from slide."""
        images = []
        
        # Check for images in slide data
        if 'images' in slide_data:
            for img_data in slide_data['images']:
                image_info = {
                    'path': img_data.get('url') or img_data.get('path'),
                    'alt_text': img_data.get('alt_text', ''),
                    'caption': img_data.get('caption', ''),
                    'width': img_data.get('width'),
                    'height': img_data.get('height')
                }
                images.append(image_info)
        
        # Check for embedded images in content
        content = slide_data.get('content', {})
        if isinstance(content, dict) and 'images' in content:
            for img_data in content['images']:
                image_info = {
                    'path': img_data.get('url') or img_data.get('src'),
                    'alt_text': img_data.get('alt', ''),
                    'caption': img_data.get('caption', '')
                }
                images.append(image_info)
        
        return images
    
    def _extract_citations(self, slide_data: Dict[str, Any]) -> List[Citation]:
        """Extract citations from slide data."""
        citations = []
        
        # Check for citations in slide data
        if 'citations' in slide_data:
            for citation_data in slide_data['citations']:
                citation = Citation(
                    title=citation_data.get('title', ''),
                    authors=citation_data.get('authors', ''),
                    year=str(citation_data.get('year', '')),
                    url=citation_data.get('url', ''),
                    doi=citation_data.get('doi', ''),
                    journal=citation_data.get('journal', ''),
                    volume=citation_data.get('volume', ''),
                    pages=citation_data.get('pages', '')
                )
                citations.append(citation)
        
        return citations
    
    def _create_pdf_config(self, options: Dict[str, Any]) -> PDFConfig:
        """Create PDF configuration from export options."""
        # Start with default config
        config = PDFConfig()
        
        # Apply format
        format_type = options.get('format', 'presentation')
        if format_type in self.supported_formats:
            config.format = self.supported_formats[format_type]
        
        # Apply quality
        quality = options.get('quality', 'standard')
        if quality in self.quality_levels:
            config.quality = self.quality_levels[quality]
        
        # Apply academic template
        template = options.get('template')
        if template in self.academic_templates:
            config = self.academic_templates[template]()
            # Override format if specified
            if format_type in self.supported_formats:
                config.format = self.supported_formats[format_type]
        
        # Apply page settings
        page_size = options.get('page_size', 'A4')
        if hasattr(PageSize, page_size.upper()):
            config.page_size = getattr(PageSize, page_size.upper())
        
        orientation = options.get('orientation', 'portrait')
        if hasattr(PageOrientation, orientation.upper()):
            config.orientation = getattr(PageOrientation, orientation.upper())
        
        # Apply handout layout
        if config.format == PDFFormat.HANDOUT:
            layout = options.get('handout_layout', 'LAYOUT_2x3')
            if hasattr(HandoutLayout, layout):
                config.handout_layout = getattr(HandoutLayout, layout)
        
        # Apply custom settings
        if 'watermark' in options:
            config.watermark_text = options['watermark']
            config.watermark_opacity = options.get('watermark_opacity', 0.1)
        
        if 'margins' in options:
            margins = options['margins']
            config.margin_top = margins.get('top', config.margin_top)
            config.margin_bottom = margins.get('bottom', config.margin_bottom)
            config.margin_left = margins.get('left', config.margin_left)
            config.margin_right = margins.get('right', config.margin_right)
        
        # Apply styling options
        if 'colors' in options:
            colors = options['colors']
            config.primary_color = colors.get('primary', config.primary_color)
            config.accent_color = colors.get('accent', config.accent_color)
            config.text_color = colors.get('text', config.text_color)
            config.background_color = colors.get('background', config.background_color)
        
        # Apply feature toggles
        config.include_toc = options.get('include_toc', config.include_toc)
        config.include_bookmarks = options.get('include_bookmarks', config.include_bookmarks)
        config.include_page_numbers = options.get('include_page_numbers', config.include_page_numbers)
        config.show_citations = options.get('show_citations', config.show_citations)
        
        return config
    
    def _extract_metadata(self, presentation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract PDF metadata from presentation data."""
        metadata = {
            'Title': presentation_data.get('title', 'SlideGenie Presentation'),
            'Author': presentation_data.get('author', 'SlideGenie User'),
            'Subject': presentation_data.get('description', 'Academic Presentation'),
            'Creator': 'SlideGenie PDF Generator',
            'Producer': 'SlideGenie Academic Presentation Platform'
        }
        
        # Add custom metadata if available
        if 'metadata' in presentation_data:
            custom_metadata = presentation_data['metadata']
            metadata.update({
                'Keywords': custom_metadata.get('tags', ''),
                'Conference': custom_metadata.get('conference', ''),
                'Course': custom_metadata.get('course', ''),
                'Institution': custom_metadata.get('institution', '')
            })
        
        return metadata
    
    def get_export_options_schema(self) -> Dict[str, Any]:
        """Get the schema for export options."""
        return {
            'format': {
                'type': 'string',
                'enum': list(self.supported_formats.keys()),
                'default': 'presentation',
                'description': 'PDF output format'
            },
            'quality': {
                'type': 'string',
                'enum': list(self.quality_levels.keys()),
                'default': 'standard',
                'description': 'PDF quality level'
            },
            'template': {
                'type': 'string',
                'enum': list(self.academic_templates.keys()),
                'description': 'Academic template style'
            },
            'page_size': {
                'type': 'string',
                'enum': ['A4', 'A3', 'A5', 'LETTER', 'LEGAL'],
                'default': 'A4',
                'description': 'Page size'
            },
            'orientation': {
                'type': 'string',
                'enum': ['portrait', 'landscape'],
                'default': 'portrait',
                'description': 'Page orientation'
            },
            'handout_layout': {
                'type': 'string',
                'enum': [layout.name for layout in HandoutLayout],
                'default': 'LAYOUT_2x3',
                'description': 'Handout grid layout (when format=handout)'
            },
            'watermark': {
                'type': 'string',
                'description': 'Watermark text'
            },
            'watermark_opacity': {
                'type': 'number',
                'minimum': 0.0,
                'maximum': 1.0,
                'default': 0.1,
                'description': 'Watermark opacity'
            },
            'include_toc': {
                'type': 'boolean',
                'default': True,
                'description': 'Include table of contents'
            },
            'include_bookmarks': {
                'type': 'boolean',
                'default': True,
                'description': 'Include PDF bookmarks'
            },
            'include_page_numbers': {
                'type': 'boolean',
                'default': True,
                'description': 'Include page numbers'
            },
            'show_citations': {
                'type': 'boolean',
                'default': True,
                'description': 'Show citations in PDF'
            },
            'margins': {
                'type': 'object',
                'properties': {
                    'top': {'type': 'number'},
                    'bottom': {'type': 'number'},
                    'left': {'type': 'number'},
                    'right': {'type': 'number'}
                },
                'description': 'Page margins in points'
            },
            'colors': {
                'type': 'object',
                'properties': {
                    'primary': {'type': 'string', 'pattern': '^#[0-9A-Fa-f]{6}$'},
                    'accent': {'type': 'string', 'pattern': '^#[0-9A-Fa-f]{6}$'},
                    'text': {'type': 'string', 'pattern': '^#[0-9A-Fa-f]{6}$'},
                    'background': {'type': 'string', 'pattern': '^#[0-9A-Fa-f]{6}$'}
                },
                'description': 'Color scheme customization'
            }
        }


# Example usage and testing
def demo_slidegenie_integration():
    """Demonstrate SlideGenie PDF integration."""
    
    # Sample SlideGenie presentation data
    sample_presentation = {
        'title': 'Machine Learning Fundamentals',
        'author': 'Dr. AI Researcher',
        'description': 'Introduction to machine learning concepts',
        'metadata': {
            'tags': 'machine learning, AI, algorithms',
            'course': 'CS 4641',
            'institution': 'Georgia Institute of Technology'
        },
        'slides': [
            {
                'title': 'What is Machine Learning?',
                'content': {
                    'sections': [
                        {
                            'type': 'text',
                            'content': 'Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.'
                        },
                        {
                            'type': 'bullet_points',
                            'items': [
                                'Supervised learning: Learning with labeled data',
                                'Unsupervised learning: Finding patterns in unlabeled data',
                                'Reinforcement learning: Learning through interaction and rewards'
                            ]
                        }
                    ]
                },
                'speaker_notes': 'Start with a broad definition and then break down the main categories. Ask students if they can think of examples.',
                'images': [
                    {
                        'url': 'https://via.placeholder.com/500x300/4472C4/FFFFFF?text=ML+Overview',
                        'alt_text': 'Machine learning overview diagram',
                        'caption': 'Figure 1: Overview of machine learning approaches'
                    }
                ],
                'citations': [
                    {
                        'title': 'Pattern Recognition and Machine Learning',
                        'authors': 'Christopher M. Bishop',
                        'year': 2006,
                        'url': 'https://www.microsoft.com/en-us/research/publication/pattern-recognition-machine-learning/'
                    }
                ]
            },
            {
                'title': 'Linear Regression',
                'content': {
                    'sections': [
                        {
                            'type': 'text',
                            'content': 'Linear regression is one of the simplest and most widely used machine learning algorithms.'
                        },
                        {
                            'type': 'numbered_list',
                            'items': [
                                'Define the hypothesis function: h(x) = θ₀ + θ₁x',
                                'Choose a cost function: J(θ) = ½m Σ(h(x⁽ⁱ⁾) - y⁽ⁱ⁾)²',
                                'Minimize the cost function using gradient descent',
                                'Update parameters: θⱼ := θⱼ - α ∂J/∂θⱼ'
                            ]
                        }
                    ]
                },
                'speaker_notes': 'Draw the regression line on the board. Explain the intuition behind gradient descent.',
                'layout': 'title_and_content'
            }
        ]
    }
    
    # Initialize the exporter
    exporter = SlideGeniePDFExporter()
    
    # Test different export formats
    export_configs = [
        {
            'format': 'presentation',
            'quality': 'standard',
            'template': 'ieee',
            'include_toc': True
        },
        {
            'format': 'handout',
            'handout_layout': 'LAYOUT_2x2',
            'quality': 'high',
            'watermark': 'COURSE MATERIAL'
        },
        {
            'format': 'notes',
            'quality': 'standard',
            'include_page_numbers': True,
            'margins': {
                'left': 100,
                'right': 50
            }
        },
        {
            'format': 'print',
            'quality': 'print_ready',
            'page_size': 'A4',
            'orientation': 'portrait'
        }
    ]
    
    print("SlideGenie PDF Integration Demo")
    print("=" * 40)
    
    for i, config in enumerate(export_configs, 1):
        output_path = f"demo_output_{config['format']}.pdf"
        
        print(f"\n{i}. Generating {config['format']} PDF...")
        result = exporter.export_presentation(sample_presentation, output_path, config)
        
        if result['success']:
            print(f"   ✓ Success: {output_path}")
            print(f"   Format: {result['format']}")
            print(f"   Quality: {result['quality']}")
            print(f"   File size: {result['file_size']:,} bytes")
            print(f"   Slides: {result['slide_count']}")
        else:
            print(f"   ✗ Failed: {result['error']}")
    
    # Show export options schema
    print(f"\n\nExport Options Schema:")
    print("=" * 40)
    schema = exporter.get_export_options_schema()
    for option, details in schema.items():
        print(f"{option}: {details['description']}")
        if 'enum' in details:
            print(f"  Options: {', '.join(details['enum'])}")
        if 'default' in details:
            print(f"  Default: {details['default']}")
        print()


if __name__ == "__main__":
    demo_slidegenie_integration()