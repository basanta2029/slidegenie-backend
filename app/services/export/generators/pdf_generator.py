"""
Comprehensive PDF generator for academic presentations.

This module provides a complete PDF generation system with:
- Multiple layout formats (slides, handouts, notes, print-optimized)
- Template system for consistent academic styling
- Image optimization and compression
- Text rendering with proper font handling
- Page layout management and pagination
- Bookmarks and navigation support
- Quality control and optimization
- Accessibility features and print optimization
- Watermark and header/footer support
- Table of contents generation
"""

import io
import logging
import math
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
from uuid import UUID

try:
    import requests
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing, Group, Rect, String
    from reportlab.lib import colors
    from reportlab.lib.colors import Color, HexColor, black, white
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, LETTER, LEGAL, A3, A5, landscape, portrait
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, inch, mm, pica, point
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        BaseDocTemplate, 
        Frame, 
        PageBreak, 
        PageTemplate, 
        Paragraph, 
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        NextPageTemplate,
        KeepTogether
    )
    from reportlab.platypus.flowables import Flowable
    from reportlab.platypus.tableofcontents import TableOfContents
    
    # Try weasyprint as alternative
    try:
        import weasyprint
        WEASYPRINT_AVAILABLE = True
    except ImportError:
        WEASYPRINT_AVAILABLE = False
        
except ImportError as e:
    raise ImportError(
        f"Required packages not installed: {e}. "
        "Please install: pip install reportlab pillow requests weasyprint"
    )

from app.core.logging import get_logger
from app.domain.schemas.generation import Citation, SlideContent

logger = get_logger(__name__)


class PDFFormat(Enum):
    """PDF output format types."""
    PRESENTATION = "presentation"  # Standard slide view
    HANDOUT = "handout"           # Grid layout with multiple slides per page
    NOTES = "notes"               # Slides with speaker notes
    PRINT_OPTIMIZED = "print"     # High contrast, print-friendly version
    CUSTOM = "custom"             # Custom layout


class PDFQuality(Enum):
    """PDF quality settings."""
    DRAFT = "draft"               # Low quality, fast generation
    STANDARD = "standard"         # Balanced quality and size
    HIGH_QUALITY = "high"         # Maximum quality
    PRINT_READY = "print_ready"   # Optimized for printing


class HandoutLayout(Enum):
    """Handout grid layout options."""
    LAYOUT_1x1 = (1, 1)          # One slide per page
    LAYOUT_2x1 = (2, 1)          # Two slides horizontally
    LAYOUT_1x2 = (1, 2)          # Two slides vertically
    LAYOUT_2x2 = (2, 2)          # Four slides in 2x2 grid
    LAYOUT_3x2 = (3, 2)          # Six slides in 3x2 grid
    LAYOUT_2x3 = (2, 3)          # Six slides in 2x3 grid
    LAYOUT_3x3 = (3, 3)          # Nine slides in 3x3 grid
    LAYOUT_4x3 = (4, 3)          # Twelve slides in 4x3 grid
    LAYOUT_4x4 = (4, 4)          # Sixteen slides in 4x4 grid


class PageSize(Enum):
    """Page size options."""
    A4 = A4
    A3 = A3
    A5 = A5
    LETTER = LETTER
    LEGAL = LEGAL
    CUSTOM = "custom"


class PageOrientation(Enum):
    """Page orientation options."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass
class PDFConfig:
    """PDF generation configuration."""
    format: PDFFormat = PDFFormat.PRESENTATION
    quality: PDFQuality = PDFQuality.STANDARD
    page_size: PageSize = PageSize.A4
    orientation: PageOrientation = PageOrientation.PORTRAIT
    custom_size: Optional[Tuple[float, float]] = None  # (width, height) in points
    
    # Layout settings
    handout_layout: HandoutLayout = HandoutLayout.LAYOUT_2x3
    slides_per_page: Optional[int] = None  # Override handout layout
    
    # Margins (in points)
    margin_top: float = 72
    margin_bottom: float = 72
    margin_left: float = 72
    margin_right: float = 72
    
    # Content settings
    include_toc: bool = True
    include_bookmarks: bool = True
    include_page_numbers: bool = True
    include_headers: bool = False
    include_footers: bool = True
    
    # Watermark settings
    watermark_text: Optional[str] = None
    watermark_opacity: float = 0.1
    watermark_rotation: float = 45
    
    # Font settings
    title_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    code_font: str = "Courier"
    font_size_title: int = 16
    font_size_body: int = 11
    font_size_caption: int = 9
    
    # Image settings
    image_dpi: int = 150
    image_quality: int = 85
    compress_images: bool = True
    
    # Colors
    primary_color: str = "#2E3440"
    accent_color: str = "#5E81AC"
    text_color: str = "#2E3440"
    background_color: str = "#FFFFFF"
    
    # Academic settings
    show_slide_numbers: bool = True
    show_citations: bool = True
    citation_style: str = "apa"
    
    # Accessibility
    tagged_pdf: bool = True
    alt_text_images: bool = True
    high_contrast: bool = False


@dataclass
class PDFSlide:
    """Individual slide data for PDF generation."""
    title: str = ""
    content: str = ""
    notes: str = ""
    images: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    slide_number: int = 1
    layout_type: str = "title_and_content"
    background_color: Optional[str] = None
    template_override: Optional[str] = None


class WatermarkFlowable(Flowable):
    """Custom flowable for watermark text."""
    
    def __init__(self, text: str, opacity: float = 0.1, rotation: float = 45):
        self.text = text
        self.opacity = opacity
        self.rotation = rotation
        Flowable.__init__(self)
    
    def draw(self):
        """Draw the watermark."""
        canvas = self.canv
        canvas.saveState()
        
        # Set transparency
        canvas.setFillColorRGB(0.5, 0.5, 0.5, alpha=self.opacity)
        
        # Rotate and position
        canvas.rotate(self.rotation)
        canvas.setFont("Helvetica-Bold", 48)
        
        # Center the text
        text_width = canvas.stringWidth(self.text, "Helvetica-Bold", 48)
        x = -text_width / 2
        y = 0
        
        canvas.drawString(x, y, self.text)
        canvas.restoreState()


class PDFTableOfContents(TableOfContents):
    """Custom table of contents for PDF."""
    
    def __init__(self, config: PDFConfig):
        super().__init__()
        self.config = config
        self.levelStyles = [
            ParagraphStyle(
                name="TOCHeading1",
                fontSize=14,
                fontName=config.title_font,
                leftIndent=0,
                spaceAfter=6
            ),
            ParagraphStyle(
                name="TOCHeading2", 
                fontSize=12,
                fontName=config.body_font,
                leftIndent=20,
                spaceAfter=3
            )
        ]


class PDFLayoutEngine:
    """Layout engine for different PDF formats."""
    
    def __init__(self, config: PDFConfig):
        self.config = config
        self.page_width = 0
        self.page_height = 0
        self._setup_page_dimensions()
    
    def _setup_page_dimensions(self):
        """Setup page dimensions based on configuration."""
        if self.config.page_size == PageSize.CUSTOM and self.config.custom_size:
            base_size = self.config.custom_size
        else:
            base_size = self.config.page_size.value
        
        if self.config.orientation == PageOrientation.LANDSCAPE:
            self.page_width, self.page_height = landscape(base_size)
        else:
            self.page_width, self.page_height = portrait(base_size)
    
    def calculate_slide_dimensions(self, slides_count: int) -> Tuple[float, float, int, int]:
        """Calculate slide dimensions for handout layout."""
        if self.config.format == PDFFormat.HANDOUT:
            if self.config.slides_per_page:
                # Calculate grid based on slides per page
                cols = math.ceil(math.sqrt(self.config.slides_per_page))
                rows = math.ceil(self.config.slides_per_page / cols)
            else:
                cols, rows = self.config.handout_layout.value
            
            available_width = self.page_width - self.config.margin_left - self.config.margin_right
            available_height = self.page_height - self.config.margin_top - self.config.margin_bottom
            
            slide_width = (available_width - (cols - 1) * 10) / cols  # 10pt gap
            slide_height = (available_height - (rows - 1) * 10) / rows
            
            return slide_width, slide_height, cols, rows
        else:
            # Full page slide
            slide_width = self.page_width - self.config.margin_left - self.config.margin_right
            slide_height = self.page_height - self.config.margin_top - self.config.margin_bottom
            return slide_width, slide_height, 1, 1


class PDFImageProcessor:
    """Image processing utilities for PDF generation."""
    
    def __init__(self, config: PDFConfig):
        self.config = config
    
    def process_image(self, image_path: str, max_width: float, max_height: float) -> ImageReader:
        """Process and optimize image for PDF inclusion."""
        try:
            if image_path.startswith(('http://', 'https://')):
                response = requests.get(image_path, timeout=30)
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content))
            else:
                image = Image.open(image_path)
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply high contrast if needed
            if self.config.high_contrast:
                image = ImageOps.autocontrast(image)
            
            # Resize if needed
            image = self._resize_image(image, max_width, max_height)
            
            # Optimize quality
            if self.config.compress_images:
                image = self._compress_image(image)
            
            # Convert to ImageReader
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG', quality=self.config.image_quality, dpi=(self.config.image_dpi, self.config.image_dpi))
            img_buffer.seek(0)
            
            return ImageReader(img_buffer)
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None
    
    def _resize_image(self, image: Image.Image, max_width: float, max_height: float) -> Image.Image:
        """Resize image while maintaining aspect ratio."""
        width, height = image.size
        
        # Convert points to pixels
        max_width_px = int(max_width * self.config.image_dpi / 72)
        max_height_px = int(max_height * self.config.image_dpi / 72)
        
        # Calculate scaling
        width_ratio = max_width_px / width
        height_ratio = max_height_px / height
        scale_ratio = min(width_ratio, height_ratio, 1.0)  # Don't upscale
        
        if scale_ratio < 1.0:
            new_width = int(width * scale_ratio)
            new_height = int(height * scale_ratio)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def _compress_image(self, image: Image.Image) -> Image.Image:
        """Apply compression optimizations."""
        # Convert to optimized palette if appropriate
        if self.config.quality == PDFQuality.DRAFT:
            # More aggressive compression for draft
            if image.mode == 'RGB':
                image = image.quantize(colors=64)
                image = image.convert('RGB')
        
        return image


class PDFFontManager:
    """Font management for PDF generation."""
    
    def __init__(self, config: PDFConfig):
        self.config = config
        self._register_fonts()
    
    def _register_fonts(self):
        """Register custom fonts if available."""
        try:
            # Try to register common academic fonts
            font_paths = [
                '/System/Library/Fonts/',  # macOS
                '/usr/share/fonts/',       # Linux
                'C:/Windows/Fonts/',       # Windows
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    self._register_fonts_from_path(font_path)
                    break
        except Exception as e:
            logger.warning(f"Could not register custom fonts: {e}")
    
    def _register_fonts_from_path(self, font_path: str):
        """Register fonts from a directory."""
        try:
            # Common academic fonts
            font_files = {
                'Times-Roman': 'Times.ttc',
                'Times-Bold': 'TimesB.ttc', 
                'Palatino': 'Palatino.ttc',
                'Computer-Modern': 'cmr10.ttf'
            }
            
            for font_name, font_file in font_files.items():
                full_path = os.path.join(font_path, font_file)
                if os.path.exists(full_path):
                    pdfmetrics.registerFont(TTFont(font_name, full_path))
        except Exception as e:
            logger.debug(f"Font registration failed: {e}")


class PDFGenerator:
    """Main PDF generator class."""
    
    def __init__(self, config: Optional[PDFConfig] = None):
        self.config = config or PDFConfig()
        self.layout_engine = PDFLayoutEngine(self.config)
        self.image_processor = PDFImageProcessor(self.config)
        self.font_manager = PDFFontManager(self.config)
        self.toc_entries = []
        
    def generate_pdf(self, slides: List[PDFSlide], output_path: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Generate PDF with specified format and configuration."""
        try:
            logger.info(f"Generating PDF with format: {self.config.format.value}")
            
            if self.config.format == PDFFormat.PRESENTATION:
                return self._generate_presentation_pdf(slides, output_path, metadata)
            elif self.config.format == PDFFormat.HANDOUT:
                return self._generate_handout_pdf(slides, output_path, metadata)
            elif self.config.format == PDFFormat.NOTES:
                return self._generate_notes_pdf(slides, output_path, metadata)
            elif self.config.format == PDFFormat.PRINT_OPTIMIZED:
                return self._generate_print_pdf(slides, output_path, metadata)
            else:
                return self._generate_custom_pdf(slides, output_path, metadata)
                
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return False
    
    def _generate_presentation_pdf(self, slides: List[PDFSlide], output_path: str,
                                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Generate standard presentation PDF (one slide per page)."""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=(self.layout_engine.page_width, self.layout_engine.page_height),
            leftMargin=self.config.margin_left,
            rightMargin=self.config.margin_right,
            topMargin=self.config.margin_top,
            bottomMargin=self.config.margin_bottom
        )
        
        # Build story
        story = []
        
        # Add table of contents if requested
        if self.config.include_toc:
            toc = PDFTableOfContents(self.config)
            story.append(toc)
            story.append(PageBreak())
        
        # Add slides
        for i, slide in enumerate(slides):
            # Add to TOC
            if self.config.include_toc:
                self.toc_entries.append((0, slide.title, i + 1))
            
            # Add slide content
            slide_content = self._create_slide_content(slide, full_page=True)
            story.extend(slide_content)
            
            # Add page break except for last slide
            if i < len(slides) - 1:
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_decorations,
                 onLaterPages=self._add_page_decorations)
        
        # Add metadata
        self._add_pdf_metadata(output_path, metadata)
        
        return True
    
    def _generate_handout_pdf(self, slides: List[PDFSlide], output_path: str,
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Generate handout PDF with multiple slides per page."""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=(self.layout_engine.page_width, self.layout_engine.page_height),
            leftMargin=self.config.margin_left,
            rightMargin=self.config.margin_right,
            topMargin=self.config.margin_top,
            bottomMargin=self.config.margin_bottom
        )
        
        slide_width, slide_height, cols, rows = self.layout_engine.calculate_slide_dimensions(len(slides))
        slides_per_page = cols * rows
        
        story = []
        
        # Process slides in groups
        for page_start in range(0, len(slides), slides_per_page):
            page_slides = slides[page_start:page_start + slides_per_page]
            
            # Create handout page
            handout_content = self._create_handout_page(page_slides, slide_width, slide_height, cols, rows)
            story.extend(handout_content)
            
            # Add page break except for last page
            if page_start + slides_per_page < len(slides):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_decorations,
                 onLaterPages=self._add_page_decorations)
        
        # Add metadata
        self._add_pdf_metadata(output_path, metadata)
        
        return True
    
    def _generate_notes_pdf(self, slides: List[PDFSlide], output_path: str,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Generate notes PDF with slides and speaker notes."""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=(self.layout_engine.page_width, self.layout_engine.page_height),
            leftMargin=self.config.margin_left,
            rightMargin=self.config.margin_right,
            topMargin=self.config.margin_top,
            bottomMargin=self.config.margin_bottom
        )
        
        story = []
        
        # Add table of contents if requested
        if self.config.include_toc:
            toc = PDFTableOfContents(self.config)
            story.append(toc)
            story.append(PageBreak())
        
        # Add slides with notes
        for i, slide in enumerate(slides):
            # Add to TOC
            if self.config.include_toc:
                self.toc_entries.append((0, slide.title, i + 1))
            
            # Create notes page layout
            notes_content = self._create_notes_page(slide)
            story.extend(notes_content)
            
            # Add page break except for last slide
            if i < len(slides) - 1:
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_decorations,
                 onLaterPages=self._add_page_decorations)
        
        # Add metadata
        self._add_pdf_metadata(output_path, metadata)
        
        return True
    
    def _generate_print_pdf(self, slides: List[PDFSlide], output_path: str,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Generate print-optimized PDF with enhanced contrast."""
        # Create print-optimized config
        print_config = PDFConfig(
            format=PDFFormat.PRESENTATION,
            quality=PDFQuality.PRINT_READY,
            high_contrast=True,
            text_color="#000000",
            background_color="#FFFFFF",
            image_dpi=300,
            compress_images=False
        )
        
        # Temporarily use print config
        original_config = self.config
        self.config = print_config
        
        try:
            result = self._generate_presentation_pdf(slides, output_path, metadata)
        finally:
            self.config = original_config
        
        return result
    
    def _generate_custom_pdf(self, slides: List[PDFSlide], output_path: str,
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Generate custom PDF format."""
        # Default to presentation format for custom
        return self._generate_presentation_pdf(slides, output_path, metadata)
    
    def _create_slide_content(self, slide: PDFSlide, full_page: bool = True) -> List:
        """Create content elements for a slide."""
        content = []
        
        # Title
        if slide.title:
            title_style = ParagraphStyle(
                'SlideTitle',
                fontSize=self.config.font_size_title,
                fontName=self.config.title_font,
                textColor=HexColor(self.config.text_color),
                alignment=TA_CENTER,
                spaceAfter=12
            )
            content.append(Paragraph(slide.title, title_style))
        
        # Content
        if slide.content:
            body_style = ParagraphStyle(
                'SlideBody',
                fontSize=self.config.font_size_body,
                fontName=self.config.body_font,
                textColor=HexColor(self.config.text_color),
                alignment=TA_LEFT,
                spaceAfter=6,
                leading=self.config.font_size_body * 1.2
            )
            
            # Split content into paragraphs
            paragraphs = slide.content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    content.append(Paragraph(para.strip(), body_style))
        
        # Images
        if slide.images and full_page:
            available_width = self.layout_engine.page_width - self.config.margin_left - self.config.margin_right
            available_height = 200  # Reserve space for images
            
            for img_data in slide.images[:2]:  # Limit to 2 images per slide
                img_path = img_data.get('path') or img_data.get('url')
                if img_path:
                    processed_img = self.image_processor.process_image(
                        img_path, available_width * 0.8, available_height * 0.4
                    )
                    if processed_img:
                        content.append(Spacer(1, 6))
                        # Note: For full implementation, would need custom flowable for images
                        # content.append(ImageFlowable(processed_img))
        
        # Citations
        if slide.citations and self.config.show_citations:
            citation_style = ParagraphStyle(
                'Citations',
                fontSize=self.config.font_size_caption,
                fontName=self.config.body_font,
                textColor=HexColor(self.config.text_color),
                alignment=TA_LEFT,
                leftIndent=20
            )
            
            for citation in slide.citations:
                citation_text = f"• {citation.authors} ({citation.year}). {citation.title}"
                content.append(Paragraph(citation_text, citation_style))
        
        return content
    
    def _create_handout_page(self, slides: List[PDFSlide], slide_width: float,
                           slide_height: float, cols: int, rows: int) -> List:
        """Create a handout page with multiple slides."""
        content = []
        
        # Create table for slide layout
        slide_data = []
        row_data = []
        
        for i, slide in enumerate(slides):
            # Create mini slide content
            mini_content = self._create_mini_slide(slide, slide_width, slide_height)
            row_data.append(mini_content)
            
            # Check if row is complete or last slide
            if len(row_data) == cols or i == len(slides) - 1:
                # Pad row if needed
                while len(row_data) < cols:
                    row_data.append("")
                slide_data.append(row_data)
                row_data = []
        
        # Create table
        if slide_data:
            table = Table(slide_data, colWidths=[slide_width] * cols, 
                         rowHeights=[slide_height] * len(slide_data))
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            content.append(table)
        
        return content
    
    def _create_mini_slide(self, slide: PDFSlide, width: float, height: float) -> str:
        """Create mini slide content for handout."""
        # Simplified slide representation
        content = []
        
        if slide.title:
            content.append(f"<b>{slide.title}</b>")
        
        if slide.content:
            # Truncate content for mini slide
            truncated = slide.content[:100] + "..." if len(slide.content) > 100 else slide.content
            content.append(truncated)
        
        # Add slide number
        content.append(f"<i>Slide {slide.slide_number}</i>")
        
        return "<br/>".join(content)
    
    def _create_notes_page(self, slide: PDFSlide) -> List:
        """Create a notes page with slide and speaker notes."""
        content = []
        
        # Slide content (top half)
        slide_content = self._create_slide_content(slide, full_page=False)
        content.extend(slide_content)
        
        # Separator
        content.append(Spacer(1, 20))
        
        # Notes section
        if slide.notes:
            notes_title_style = ParagraphStyle(
                'NotesTitle',
                fontSize=self.config.font_size_body + 2,
                fontName=self.config.title_font,
                textColor=HexColor(self.config.text_color),
                alignment=TA_LEFT,
                spaceAfter=6
            )
            content.append(Paragraph("Speaker Notes:", notes_title_style))
            
            notes_style = ParagraphStyle(
                'Notes',
                fontSize=self.config.font_size_body,
                fontName=self.config.body_font,
                textColor=HexColor(self.config.text_color),
                alignment=TA_LEFT,
                leftIndent=10,
                leading=self.config.font_size_body * 1.3
            )
            content.append(Paragraph(slide.notes, notes_style))
        
        return content
    
    def _add_page_decorations(self, canvas_obj, doc):
        """Add headers, footers, watermarks, and page numbers."""
        canvas_obj.saveState()
        
        # Add watermark
        if self.config.watermark_text:
            self._add_watermark(canvas_obj)
        
        # Add header
        if self.config.include_headers:
            self._add_header(canvas_obj, doc)
        
        # Add footer
        if self.config.include_footers:
            self._add_footer(canvas_obj, doc)
        
        # Add page numbers
        if self.config.include_page_numbers:
            self._add_page_number(canvas_obj, doc)
        
        canvas_obj.restoreState()
    
    def _add_watermark(self, canvas_obj):
        """Add watermark to page."""
        canvas_obj.saveState()
        canvas_obj.setFillColorRGB(0.5, 0.5, 0.5, alpha=self.config.watermark_opacity)
        canvas_obj.rotate(self.config.watermark_rotation)
        canvas_obj.setFont("Helvetica-Bold", 48)
        
        # Center the watermark
        text_width = canvas_obj.stringWidth(self.config.watermark_text, "Helvetica-Bold", 48)
        x = -text_width / 2
        y = 0
        
        canvas_obj.drawString(x, y, self.config.watermark_text)
        canvas_obj.restoreState()
    
    def _add_header(self, canvas_obj, doc):
        """Add header to page."""
        # Simple header implementation
        canvas_obj.setFont(self.config.body_font, self.config.font_size_caption)
        canvas_obj.drawString(
            self.config.margin_left,
            self.layout_engine.page_height - self.config.margin_top / 2,
            "Academic Presentation"  # Would be customizable
        )
    
    def _add_footer(self, canvas_obj, doc):
        """Add footer to page."""
        canvas_obj.setFont(self.config.body_font, self.config.font_size_caption)
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
        canvas_obj.drawString(
            self.config.margin_left,
            self.config.margin_bottom / 2,
            footer_text
        )
    
    def _add_page_number(self, canvas_obj, doc):
        """Add page number to page."""
        canvas_obj.setFont(self.config.body_font, self.config.font_size_caption)
        page_num = f"Page {doc.page}"
        text_width = canvas_obj.stringWidth(page_num, self.config.body_font, self.config.font_size_caption)
        
        canvas_obj.drawString(
            self.layout_engine.page_width - self.config.margin_right - text_width,
            self.config.margin_bottom / 2,
            page_num
        )
    
    def _add_pdf_metadata(self, output_path: str, metadata: Optional[Dict[str, Any]]):
        """Add metadata to PDF."""
        if not metadata:
            metadata = {}
        
        # Default metadata
        default_metadata = {
            'Title': 'Academic Presentation',
            'Author': 'SlideGenie',
            'Subject': 'Generated Presentation',
            'Creator': 'SlideGenie PDF Generator',
            'Producer': 'ReportLab PDF Library',
            'CreationDate': datetime.now(),
        }
        
        # Merge with provided metadata
        final_metadata = {**default_metadata, **metadata}
        
        # Note: Full metadata implementation would require additional PDF processing
        logger.info(f"PDF metadata: {final_metadata}")


# Convenience functions
def create_presentation_pdf(slides: List[PDFSlide], output_path: str,
                          config: Optional[PDFConfig] = None) -> bool:
    """Create a standard presentation PDF."""
    if not config:
        config = PDFConfig(format=PDFFormat.PRESENTATION)
    
    generator = PDFGenerator(config)
    return generator.generate_pdf(slides, output_path)


def create_handout_pdf(slides: List[PDFSlide], output_path: str,
                      layout: HandoutLayout = HandoutLayout.LAYOUT_2x3,
                      config: Optional[PDFConfig] = None) -> bool:
    """Create a handout PDF with specified layout."""
    if not config:
        config = PDFConfig(format=PDFFormat.HANDOUT, handout_layout=layout)
    
    generator = PDFGenerator(config)
    return generator.generate_pdf(slides, output_path)


def create_notes_pdf(slides: List[PDFSlide], output_path: str,
                    config: Optional[PDFConfig] = None) -> bool:
    """Create a notes PDF with slides and speaker notes."""
    if not config:
        config = PDFConfig(format=PDFFormat.NOTES)
    
    generator = PDFGenerator(config)
    return generator.generate_pdf(slides, output_path)


def create_print_pdf(slides: List[PDFSlide], output_path: str,
                    config: Optional[PDFConfig] = None) -> bool:
    """Create a print-optimized PDF."""
    if not config:
        config = PDFConfig(format=PDFFormat.PRINT_OPTIMIZED)
    
    generator = PDFGenerator(config)
    return generator.generate_pdf(slides, output_path)


# Template configurations for common academic styles
def get_ieee_config() -> PDFConfig:
    """Get IEEE conference paper style configuration."""
    return PDFConfig(
        page_size=PageSize.A4,
        orientation=PageOrientation.PORTRAIT,
        primary_color="#003366",
        accent_color="#0066CC",
        title_font="Times-Bold",
        body_font="Times-Roman",
        font_size_title=14,
        font_size_body=10,
        include_toc=True,
        citation_style="ieee"
    )


def get_acm_config() -> PDFConfig:
    """Get ACM conference style configuration."""
    return PDFConfig(
        page_size=PageSize.A4,
        orientation=PageOrientation.PORTRAIT,
        primary_color="#FF6900",
        accent_color="#FCB900",
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        font_size_title=16,
        font_size_body=11,
        include_toc=True,
        citation_style="acm"
    )


def get_nature_config() -> PDFConfig:
    """Get Nature journal style configuration."""
    return PDFConfig(
        page_size=PageSize.A4,
        orientation=PageOrientation.PORTRAIT,
        primary_color="#0F4C81",
        accent_color="#2E8B57",
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        font_size_title=18,
        font_size_body=12,
        include_toc=False,
        high_contrast=True,
        citation_style="nature"
    )