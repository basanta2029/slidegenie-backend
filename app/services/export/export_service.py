"""
Export service for various presentation formats.

This service integrates the PPTX generator with the SlideGenie architecture,
providing a unified interface for exporting presentations in different formats.
"""

import io
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.logging import get_logger
from app.domain.schemas.generation import Citation, SlideContent
from app.services.export.generators.pptx_generator import (
    AcademicTemplate,
    PPTXGenerator,
    TemplateConfig,
    create_academic_template_config,
)

logger = get_logger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    PPTX = "pptx"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"


class ExportService:
    """
    Service for exporting presentations in various formats.
    
    Integrates with the SlideGenie architecture to provide
    comprehensive export capabilities.
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._generators = {}
        self._initialize_generators()
    
    def _initialize_generators(self) -> None:
        """Initialize format-specific generators."""
        # PPTX generator is always available
        self._generators[ExportFormat.PPTX] = self._create_pptx_generator
        
        # Add other generators as they become available
        # self._generators[ExportFormat.PDF] = self._create_pdf_generator
        # self._generators[ExportFormat.HTML] = self._create_html_generator
    
    def export_presentation(
        self,
        slides: List[SlideContent],
        format: ExportFormat,
        template_config: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Citation]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        output_path: Optional[Union[str, Path]] = None
    ) -> Union[io.BytesIO, str]:
        """
        Export presentation in the specified format.
        
        Args:
            slides: List of slide content to export
            format: Target export format
            template_config: Template configuration options
            citations: List of citations to include
            metadata: Presentation metadata
            output_path: Optional output file path
            
        Returns:
            BytesIO buffer if no output_path, otherwise file path
            
        Raises:
            ValueError: If format not supported or slides empty
            Exception: If export fails
        """
        if not slides:
            raise ValueError("No slides provided for export")
        
        if format not in self._generators:
            raise ValueError(f"Export format {format.value} not supported")
        
        try:
            self.logger.info(f"Exporting presentation in {format.value} format")
            
            # Get generator function
            generator_func = self._generators[format]
            
            # Create generator
            generator = generator_func(template_config or {})
            
            # Export presentation
            if output_path:
                generator.export_to_file(
                    slides=slides,
                    output_path=str(output_path),
                    citations=citations,
                    metadata=metadata
                )
                self.logger.info(f"Presentation exported to {output_path}")
                return str(output_path)
            else:
                buffer = generator.export_to_buffer(
                    slides=slides,
                    citations=citations,
                    metadata=metadata
                )
                self.logger.info("Presentation exported to buffer")
                return buffer
                
        except Exception as e:
            self.logger.error(f"Failed to export presentation: {e}")
            raise
    
    def _create_pptx_generator(self, template_config: Dict[str, Any]) -> PPTXGenerator:
        """Create PPTX generator with configuration."""
        # Parse template configuration
        config = self._parse_pptx_template_config(template_config)
        return PPTXGenerator(config)
    
    def _parse_pptx_template_config(self, config: Dict[str, Any]) -> TemplateConfig:
        """Parse template configuration for PPTX generator."""
        # Get template type
        template_name = config.get('template', 'ieee').lower()
        template = AcademicTemplate.IEEE  # Default
        
        try:
            template = AcademicTemplate(template_name)
        except ValueError:
            self.logger.warning(f"Unknown template {template_name}, using IEEE")
        
        # Create base configuration
        template_config = create_academic_template_config(
            template=template,
            university_name=config.get('university_name'),
            logo_path=config.get('logo_path'),
            custom_colors=config.get('custom_colors')
        )
        
        # Apply additional customizations
        if 'branding' in config:
            branding = config['branding']
            if 'show_slide_numbers' in branding:
                template_config.branding.show_slide_numbers = branding['show_slide_numbers']
            if 'show_date' in branding:
                template_config.branding.show_date = branding['show_date']
            if 'custom_footer' in branding:
                template_config.branding.custom_footer = branding['custom_footer']
            if 'logo_position' in branding:
                template_config.branding.logo_position = branding['logo_position']
        
        if 'typography' in config:
            typography = config['typography']
            if 'title_size' in typography:
                template_config.typography.title_size = typography['title_size']
            if 'body_size' in typography:
                template_config.typography.body_size = typography['body_size']
            if 'title_font' in typography:
                template_config.typography.title_font = typography['title_font']
            if 'body_font' in typography:
                template_config.typography.body_font = typography['body_font']
        
        return template_config
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return [format.value for format in self._generators.keys()]
    
    def get_template_options(self, format: ExportFormat) -> Dict[str, Any]:
        """
        Get available template options for a format.
        
        Args:
            format: Export format
            
        Returns:
            Dictionary of template options
        """
        if format == ExportFormat.PPTX:
            return {
                'templates': [template.value for template in AcademicTemplate],
                'color_schemes': {
                    'ieee': {
                        'primary': '#003f7f',
                        'secondary': '#0066cc',
                        'accent': '#ff6600'
                    },
                    'nature': {
                        'primary': '#006633',
                        'secondary': '#009966', 
                        'accent': '#cc3300'
                    },
                    'mit': {
                        'primary': '#8c1515',
                        'secondary': '#b83a4b',
                        'accent': '#009639'
                    }
                },
                'fonts': ['Arial', 'Calibri', 'Times New Roman', 'Helvetica', 'Georgia'],
                'sizes': {
                    'slides': ['16:9', '4:3', '16:10'],
                    'fonts': {
                        'title': [36, 40, 44, 48, 52],
                        'body': [18, 20, 22, 24, 26, 28]
                    }
                },
                'branding_options': {
                    'logo_positions': ['top_left', 'top_right', 'bottom_left', 'bottom_right'],
                    'footer_options': ['slide_numbers', 'date', 'custom_text', 'university_name']
                }
            }
        
        return {}
    
    def validate_export_request(
        self,
        slides: List[SlideContent],
        format: ExportFormat,
        template_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate export request parameters.
        
        Args:
            slides: Slide content to validate
            format: Export format
            template_config: Template configuration
            
        Returns:
            True if valid, raises ValueError if not
        """
        if not slides:
            raise ValueError("No slides provided")
        
        if format not in self._generators:
            raise ValueError(f"Unsupported format: {format.value}")
        
        # Validate slide content
        for i, slide in enumerate(slides):
            if not slide.title and not slide.body:
                raise ValueError(f"Slide {i+1} has no title or content")
            
            # Validate body content structure
            for j, item in enumerate(slide.body):
                if not isinstance(item, dict) or 'type' not in item:
                    raise ValueError(f"Invalid content item {j+1} in slide {i+1}")
        
        # Format-specific validation
        if format == ExportFormat.PPTX:
            self._validate_pptx_config(template_config or {})
        
        return True
    
    def _validate_pptx_config(self, config: Dict[str, Any]) -> None:
        """Validate PPTX-specific configuration."""
        if 'template' in config:
            template_name = config['template']
            valid_templates = [t.value for t in AcademicTemplate]
            if template_name not in valid_templates:
                raise ValueError(f"Invalid template: {template_name}")
        
        if 'logo_path' in config:
            logo_path = Path(config['logo_path'])
            if not logo_path.exists():
                self.logger.warning(f"Logo file not found: {logo_path}")
    
    def estimate_export_time(
        self,
        slides: List[SlideContent],
        format: ExportFormat
    ) -> float:
        """
        Estimate export time in seconds.
        
        Args:
            slides: Slide content
            format: Export format
            
        Returns:
            Estimated time in seconds
        """
        base_time = 2.0  # Base processing time
        
        if format == ExportFormat.PPTX:
            # Estimate based on slide count and content complexity
            slide_time = len(slides) * 0.5  # 0.5 seconds per slide
            
            # Add time for complex content
            for slide in slides:
                for item in slide.body:
                    if item.get('type') == 'image':
                        slide_time += 1.0  # Image processing
                    elif item.get('type') == 'chart':
                        slide_time += 0.5  # Chart generation
                    elif item.get('type') == 'equation':
                        slide_time += 0.3  # Equation rendering
            
            return base_time + slide_time
        
        return base_time
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """Get export service statistics."""
        return {
            'supported_formats': self.get_supported_formats(),
            'available_generators': len(self._generators),
            'pptx_templates': len(AcademicTemplate),
        }


# Convenience functions for common export operations

def export_to_pptx(
    slides: List[SlideContent],
    template: str = 'ieee',
    university_name: Optional[str] = None,
    logo_path: Optional[str] = None,
    citations: Optional[List[Citation]] = None,
    output_path: Optional[str] = None
) -> Union[io.BytesIO, str]:
    """
    Convenience function to export slides to PPTX.
    
    Args:
        slides: Slide content
        template: Template name (ieee, acm, nature, etc.)
        university_name: University name for branding
        logo_path: Path to logo file
        citations: Citations to include
        output_path: Optional output file path
        
    Returns:
        BytesIO buffer or file path
    """
    service = ExportService()
    
    template_config = {
        'template': template,
        'university_name': university_name,
        'logo_path': logo_path
    }
    
    return service.export_presentation(
        slides=slides,
        format=ExportFormat.PPTX,
        template_config=template_config,
        citations=citations,
        output_path=output_path
    )


def export_academic_presentation(
    slides: List[SlideContent],
    conference_name: str,
    author_name: str,
    institution: str,
    template: str = 'ieee',
    citations: Optional[List[Citation]] = None,
    output_path: Optional[str] = None
) -> Union[io.BytesIO, str]:
    """
    Export an academic presentation with standard formatting.
    
    Args:
        slides: Slide content
        conference_name: Name of conference/venue
        author_name: Presenter name
        institution: Institution name
        template: Academic template to use
        citations: Research citations
        output_path: Optional output file path
        
    Returns:
        BytesIO buffer or file path
    """
    service = ExportService()
    
    # Create metadata
    metadata = {
        'title': slides[0].title if slides else "Academic Presentation",
        'author': author_name,
        'subject': conference_name,
        'description': f"Academic presentation for {conference_name}",
        'keywords': "academic, research, presentation",
        'category': "Research"
    }
    
    # Template configuration
    template_config = {
        'template': template,
        'university_name': institution,
        'branding': {
            'custom_footer': f"{conference_name} • {institution}",
            'show_slide_numbers': True,
            'show_date': True
        }
    }
    
    return service.export_presentation(
        slides=slides,
        format=ExportFormat.PPTX,
        template_config=template_config,
        citations=citations,
        metadata=metadata,
        output_path=output_path
    )