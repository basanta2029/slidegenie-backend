"""
Slide Layout Templates

Comprehensive collection of layout templates for different slide types,
each optimized for specific content patterns and academic needs.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from .base import (
    BaseLayout, LayoutConfig, ElementPosition, LayoutElement, 
    ElementType, AspectRatio
)
from .grid import GridSystem, GridCell, GridAlignment
from .positioning import PositioningEngine, PositioningStrategy
from .academic_patterns import AcademicDesignPatterns


class TitleSlideLayout(BaseLayout):
    """
    Layout for title slides
    
    Supports:
    - Main title
    - Subtitle
    - Author information (with affiliations)
    - Date/venue
    - Institutional logos
    """
    
    def get_layout_type(self) -> str:
        return "title_slide"
    
    def get_default_positions(self) -> Dict[ElementType, ElementPosition]:
        return {
            ElementType.TITLE: ElementPosition(x=0.1, y=0.25, width=0.8, height=0.15),
            ElementType.SUBTITLE: ElementPosition(x=0.1, y=0.42, width=0.8, height=0.08),
            ElementType.AUTHOR_INFO: ElementPosition(x=0.1, y=0.55, width=0.8, height=0.20),
            ElementType.TEXT: ElementPosition(x=0.1, y=0.78, width=0.8, height=0.05),  # Date/venue
            ElementType.LOGO: ElementPosition(x=0.05, y=0.88, width=0.90, height=0.10)
        }
    
    def arrange_elements(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Arrange elements for title slide"""
        defaults = self.get_default_positions()
        grid = GridSystem()
        
        # Group elements by type
        title = None
        subtitle = None
        authors = []
        other_text = []
        logos = []
        
        for elem in elements:
            if elem.type == ElementType.TITLE and not title:
                title = elem
            elif elem.type == ElementType.SUBTITLE and not subtitle:
                subtitle = elem
            elif elem.type == ElementType.AUTHOR_INFO:
                authors.append(elem)
            elif elem.type == ElementType.LOGO:
                logos.append(elem)
            elif elem.type == ElementType.TEXT:
                other_text.append(elem)
        
        positioned = []
        
        # Position title
        if title:
            title.position = defaults[ElementType.TITLE]
            positioned.append(title)
        
        # Position subtitle
        if subtitle:
            if not title:
                # Move subtitle up if no title
                subtitle.position = defaults[ElementType.TITLE]
            else:
                subtitle.position = defaults[ElementType.SUBTITLE]
            positioned.append(subtitle)
        
        # Position authors
        if authors:
            # Use academic patterns for author layout
            academic = AcademicDesignPatterns()
            if len(authors) <= 3:
                # Single row
                cells = grid.create_equal_columns(len(authors), row=4, row_span=2)
            else:
                # Multiple rows
                cells = []
                cols_per_row = 3
                for i in range(0, len(authors), cols_per_row):
                    row_cells = grid.create_equal_columns(
                        min(cols_per_row, len(authors) - i),
                        row=4 + (i // cols_per_row) * 2,
                        row_span=2
                    )
                    cells.extend(row_cells)
            
            for author, cell in zip(authors, cells[:len(authors)]):
                author.position = grid.get_cell_position(cell)
                positioned.append(author)
        
        # Position other text (date, venue, etc.)
        if other_text:
            y_pos = 0.78
            for text in other_text:
                text.position = ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.04)
                y_pos += 0.05
                positioned.append(text)
        
        # Position logos
        if logos:
            if len(logos) == 1:
                logos[0].position = ElementPosition(x=0.35, y=0.88, width=0.30, height=0.10)
            else:
                # Distribute logos horizontally
                logo_width = min(0.20, 0.80 / len(logos))
                spacing = (0.90 - logo_width * len(logos)) / (len(logos) + 1)
                
                for i, logo in enumerate(logos):
                    x_pos = spacing + i * (logo_width + spacing)
                    logo.position = ElementPosition(x=x_pos, y=0.88, width=logo_width, height=0.10)
            
            positioned.extend(logos)
        
        return positioned


class ContentSlideLayout(BaseLayout):
    """
    Layout for standard content slides
    
    Supports:
    - Title
    - Bullet points
    - Text blocks
    - Single image/diagram
    - Mixed content
    """
    
    def get_layout_type(self) -> str:
        return "content_slide"
    
    def get_default_positions(self) -> Dict[ElementType, ElementPosition]:
        return {
            ElementType.TITLE: ElementPosition(x=0.05, y=0.05, width=0.90, height=0.10),
            ElementType.BULLET_LIST: ElementPosition(x=0.05, y=0.18, width=0.50, height=0.72),
            ElementType.IMAGE: ElementPosition(x=0.58, y=0.18, width=0.37, height=0.72),
            ElementType.TEXT: ElementPosition(x=0.05, y=0.18, width=0.90, height=0.72),
            ElementType.FOOTER: ElementPosition(x=0.05, y=0.92, width=0.90, height=0.06)
        }
    
    def arrange_elements(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Arrange elements for content slide"""
        positioning = PositioningEngine()
        positioned = []
        
        # Separate elements by type
        title = None
        bullets = []
        text_blocks = []
        visuals = []
        footer = None
        
        for elem in elements:
            if elem.type == ElementType.TITLE and not title:
                title = elem
            elif elem.type == ElementType.BULLET_LIST:
                bullets.append(elem)
            elif elem.type == ElementType.TEXT:
                text_blocks.append(elem)
            elif elem.type in [ElementType.IMAGE, ElementType.CHART, ElementType.DIAGRAM]:
                visuals.append(elem)
            elif elem.type == ElementType.FOOTER and not footer:
                footer = elem
        
        # Position title
        if title:
            title.position = self.get_default_positions()[ElementType.TITLE]
            positioned.append(title)
        
        # Determine layout based on content mix
        content_area = ElementPosition(x=0.05, y=0.18, width=0.90, height=0.72)
        
        if visuals and (bullets or text_blocks):
            # Two-column layout
            left_area = ElementPosition(x=0.05, y=0.18, width=0.48, height=0.72)
            right_area = ElementPosition(x=0.55, y=0.18, width=0.40, height=0.72)
            
            # Text content on left
            text_content = bullets + text_blocks
            left_positioned = positioning.position_elements(
                text_content,
                PositioningStrategy.FLOW_VERTICAL,
                left_area
            )
            positioned.extend(left_positioned)
            
            # Visuals on right
            right_positioned = positioning.position_elements(
                visuals,
                PositioningStrategy.CENTERED,
                right_area
            )
            positioned.extend(right_positioned)
            
        elif bullets or text_blocks:
            # Text only - full width
            text_content = bullets + text_blocks
            content_positioned = positioning.position_elements(
                text_content,
                PositioningStrategy.FLOW_VERTICAL,
                content_area
            )
            positioned.extend(content_positioned)
            
        elif visuals:
            # Visuals only - centered
            visual_positioned = positioning.position_elements(
                visuals,
                PositioningStrategy.CENTERED,
                content_area
            )
            positioned.extend(visual_positioned)
        
        # Position footer
        if footer:
            footer.position = self.get_default_positions()[ElementType.FOOTER]
            positioned.append(footer)
        
        return positioned


class ComparisonSlideLayout(BaseLayout):
    """
    Layout for comparison/contrast slides
    
    Supports:
    - Side-by-side comparisons
    - Versus layouts
    - Pro/con lists
    - Before/after
    """
    
    def get_layout_type(self) -> str:
        return "comparison_slide"
    
    def get_default_positions(self) -> Dict[ElementType, ElementPosition]:
        return {
            ElementType.TITLE: ElementPosition(x=0.05, y=0.05, width=0.90, height=0.10),
            ElementType.SUBTITLE: ElementPosition(x=0.05, y=0.92, width=0.90, height=0.06)
        }
    
    def arrange_elements(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Arrange elements for comparison"""
        grid = GridSystem()
        positioned = []
        
        # Extract title
        title = None
        comparison_items = []
        
        for elem in elements:
            if elem.type == ElementType.TITLE and not title:
                title = elem
            else:
                comparison_items.append(elem)
        
        # Position title
        if title:
            title.position = self.get_default_positions()[ElementType.TITLE]
            positioned.append(title)
        
        # Create two-column layout
        left_cell = GridCell(row=2, col=0, row_span=5, col_span=6)
        right_cell = GridCell(row=2, col=6, row_span=5, col_span=6)
        
        left_area = grid.get_cell_position(left_cell)
        right_area = grid.get_cell_position(right_cell)
        
        # Add column headers if needed
        if len(comparison_items) >= 2:
            # Assume first two items are headers
            header_height = 0.08
            
            # Left header
            comparison_items[0].position = ElementPosition(
                x=left_area.x,
                y=left_area.y,
                width=left_area.width,
                height=header_height
            )
            positioned.append(comparison_items[0])
            
            # Right header
            comparison_items[1].position = ElementPosition(
                x=right_area.x,
                y=right_area.y,
                width=right_area.width,
                height=header_height
            )
            positioned.append(comparison_items[1])
            
            # Adjust content areas
            left_area.y += header_height + 0.02
            left_area.height -= header_height + 0.02
            right_area.y += header_height + 0.02
            right_area.height -= header_height + 0.02
            
            # Distribute remaining items
            remaining = comparison_items[2:]
            left_items = remaining[::2]  # Even indices
            right_items = remaining[1::2]  # Odd indices
            
            # Position left items
            positioning = PositioningEngine()
            left_positioned = positioning.position_elements(
                left_items,
                PositioningStrategy.FLOW_VERTICAL,
                left_area
            )
            positioned.extend(left_positioned)
            
            # Position right items
            right_positioned = positioning.position_elements(
                right_items,
                PositioningStrategy.FLOW_VERTICAL,
                right_area
            )
            positioned.extend(right_positioned)
        
        return positioned


class ImageFocusedLayout(BaseLayout):
    """
    Layout for image-centric slides
    
    Supports:
    - Full-bleed images
    - Image with caption
    - Multiple images grid
    - Image with minimal text
    """
    
    def get_layout_type(self) -> str:
        return "image_focused"
    
    def get_default_positions(self) -> Dict[ElementType, ElementPosition]:
        return {
            ElementType.TITLE: ElementPosition(x=0.05, y=0.05, width=0.90, height=0.08),
            ElementType.IMAGE: ElementPosition(x=0.05, y=0.15, width=0.90, height=0.75),
            ElementType.TEXT: ElementPosition(x=0.05, y=0.91, width=0.90, height=0.06)  # Caption
        }
    
    def arrange_elements(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Arrange elements for image-focused slide"""
        positioned = []
        
        # Categorize elements
        title = None
        images = []
        captions = []
        other = []
        
        for elem in elements:
            if elem.type == ElementType.TITLE and not title:
                title = elem
            elif elem.type == ElementType.IMAGE:
                images.append(elem)
            elif elem.type == ElementType.TEXT and len(elem.content) < 100:
                captions.append(elem)
            else:
                other.append(elem)
        
        # Position title if present
        if title:
            title.position = self.get_default_positions()[ElementType.TITLE]
            positioned.append(title)
            image_top = 0.15
        else:
            image_top = 0.05
        
        # Handle images
        if len(images) == 1:
            # Single large image
            images[0].position = ElementPosition(
                x=0.05,
                y=image_top,
                width=0.90,
                height=0.90 - image_top - (0.08 if captions else 0.02)
            )
            positioned.append(images[0])
            
            # Add caption if available
            if captions:
                captions[0].position = ElementPosition(
                    x=0.05,
                    y=0.92 - 0.06,
                    width=0.90,
                    height=0.06
                )
                positioned.append(captions[0])
                
        elif len(images) > 1:
            # Multiple images - create grid
            grid = GridSystem()
            
            # Determine grid layout
            if len(images) == 2:
                cells = grid.create_equal_columns(2, row=2, row_span=5)
            elif len(images) <= 4:
                cells = [
                    GridCell(row=2, col=0, row_span=3, col_span=6),
                    GridCell(row=2, col=6, row_span=3, col_span=6),
                    GridCell(row=5, col=0, row_span=3, col_span=6),
                    GridCell(row=5, col=6, row_span=3, col_span=6)
                ]
            else:
                # 3x2 grid for up to 6 images
                cells = []
                for row in range(2):
                    for col in range(3):
                        cells.append(GridCell(
                            row=2 + row * 3,
                            col=col * 4,
                            row_span=3,
                            col_span=4
                        ))
            
            # Position images in grid
            for img, cell in zip(images[:len(cells)], cells):
                pos = grid.get_cell_position(cell)
                img.position = pos.with_margin(0.01)  # Small margin between images
                positioned.append(img)
        
        return positioned


class DataVisualizationLayout(BaseLayout):
    """
    Layout for data-heavy slides
    
    Supports:
    - Charts and graphs
    - Data tables
    - Statistical results
    - Mixed data displays
    """
    
    def get_layout_type(self) -> str:
        return "data_visualization"
    
    def get_default_positions(self) -> Dict[ElementType, ElementPosition]:
        return {
            ElementType.TITLE: ElementPosition(x=0.05, y=0.05, width=0.90, height=0.08),
            ElementType.CHART: ElementPosition(x=0.05, y=0.15, width=0.90, height=0.65),
            ElementType.TEXT: ElementPosition(x=0.05, y=0.82, width=0.90, height=0.10)
        }
    
    def arrange_elements(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Arrange elements for data visualization"""
        positioning = PositioningEngine()
        positioned = []
        
        # Categorize elements
        title = None
        charts = []
        tables = []
        text_elements = []
        
        for elem in elements:
            if elem.type == ElementType.TITLE and not title:
                title = elem
            elif elem.type == ElementType.CHART:
                charts.append(elem)
            elif elem.type == ElementType.DIAGRAM and 'table' in str(elem.content).lower():
                tables.append(elem)
            elif elem.type == ElementType.TEXT:
                text_elements.append(elem)
        
        # Position title
        if title:
            title.position = self.get_default_positions()[ElementType.TITLE]
            positioned.append(title)
            content_top = 0.15
        else:
            content_top = 0.05
        
        # Determine layout based on content
        data_elements = charts + tables
        
        if len(data_elements) == 1:
            # Single visualization - large and centered
            data_elements[0].position = ElementPosition(
                x=0.05,
                y=content_top,
                width=0.90,
                height=0.75 - content_top
            )
            positioned.append(data_elements[0])
            
            # Add supporting text below
            if text_elements:
                text_area = ElementPosition(x=0.05, y=0.78, width=0.90, height=0.15)
                text_positioned = positioning.position_elements(
                    text_elements,
                    PositioningStrategy.FLOW_VERTICAL,
                    text_area
                )
                positioned.extend(text_positioned)
                
        elif len(data_elements) == 2:
            # Side-by-side layout
            data_elements[0].position = ElementPosition(
                x=0.05,
                y=content_top,
                width=0.43,
                height=0.75 - content_top
            )
            data_elements[1].position = ElementPosition(
                x=0.52,
                y=content_top,
                width=0.43,
                height=0.75 - content_top
            )
            positioned.extend(data_elements[:2])
            
        else:
            # Grid layout for multiple visualizations
            grid = GridSystem()
            cells = grid.create_equal_columns(2, row=2, row_span=4)
            
            for viz, cell in zip(data_elements[:4], cells):
                viz.position = grid.get_cell_position(cell).with_margin(0.02)
                positioned.append(viz)
        
        return positioned


class QuoteHighlightLayout(BaseLayout):
    """
    Layout for quote or highlight slides
    
    Supports:
    - Centered quotes
    - Pull quotes
    - Key takeaways
    - Callout boxes
    """
    
    def get_layout_type(self) -> str:
        return "quote_highlight"
    
    def get_default_positions(self) -> Dict[ElementType, ElementPosition]:
        return {
            ElementType.QUOTE: ElementPosition(x=0.15, y=0.35, width=0.70, height=0.30),
            ElementType.TEXT: ElementPosition(x=0.25, y=0.68, width=0.50, height=0.05)  # Attribution
        }
    
    def arrange_elements(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Arrange elements for quote/highlight"""
        positioned = []
        
        # Find quote and attribution
        quote = None
        attribution = None
        supporting = []
        
        for elem in elements:
            if elem.type == ElementType.QUOTE and not quote:
                quote = elem
            elif elem.type == ElementType.TEXT and not attribution and quote:
                attribution = elem
            else:
                supporting.append(elem)
        
        # Center the quote
        if quote:
            # Calculate size based on content length
            content_length = len(str(quote.content))
            
            if content_length < 50:
                # Short quote - smaller area, larger font
                quote.position = ElementPosition(x=0.20, y=0.40, width=0.60, height=0.20)
            elif content_length < 150:
                # Medium quote
                quote.position = ElementPosition(x=0.15, y=0.35, width=0.70, height=0.30)
            else:
                # Long quote
                quote.position = ElementPosition(x=0.10, y=0.30, width=0.80, height=0.40)
            
            quote.style.update({
                'text_align': 'center',
                'font_size': 'x-large',
                'font_style': 'italic',
                'line_height': '1.5'
            })
            positioned.append(quote)
            
            # Position attribution
            if attribution:
                attribution.position = ElementPosition(
                    x=quote.position.x + quote.position.width * 0.25,
                    y=quote.position.y + quote.position.height + 0.03,
                    width=quote.position.width * 0.5,
                    height=0.05
                )
                attribution.style.update({
                    'text_align': 'right',
                    'font_size': 'medium'
                })
                positioned.append(attribution)
        
        return positioned


class SectionDividerLayout(BaseLayout):
    """
    Layout for section divider slides
    
    Supports:
    - Chapter/section titles
    - Progress indicators
    - Transition slides
    - Agenda highlights
    """
    
    def get_layout_type(self) -> str:
        return "section_divider"
    
    def get_default_positions(self) -> Dict[ElementType, ElementPosition]:
        return {
            ElementType.TITLE: ElementPosition(x=0.10, y=0.40, width=0.80, height=0.15),
            ElementType.SUBTITLE: ElementPosition(x=0.15, y=0.57, width=0.70, height=0.08),
            ElementType.TEXT: ElementPosition(x=0.20, y=0.70, width=0.60, height=0.10)
        }
    
    def arrange_elements(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Arrange elements for section divider"""
        positioned = []
        
        # Extract main elements
        section_title = None
        section_number = None
        description = None
        progress = None
        
        for elem in elements:
            if elem.type == ElementType.TITLE and not section_title:
                section_title = elem
            elif elem.type == ElementType.SUBTITLE and not section_number:
                section_number = elem
            elif elem.type == ElementType.TEXT and not description:
                description = elem
            elif elem.type == ElementType.DIAGRAM and 'progress' in str(elem.content).lower():
                progress = elem
        
        # Center section title
        if section_title:
            section_title.position = ElementPosition(x=0.10, y=0.38, width=0.80, height=0.15)
            section_title.style.update({
                'text_align': 'center',
                'font_size': 'xx-large',
                'font_weight': 'bold'
            })
            positioned.append(section_title)
        
        # Add section number above if present
        if section_number:
            section_number.position = ElementPosition(x=0.20, y=0.30, width=0.60, height=0.06)
            section_number.style.update({
                'text_align': 'center',
                'font_size': 'large',
                'color': 'secondary'
            })
            positioned.append(section_number)
        
        # Add description below
        if description:
            description.position = ElementPosition(x=0.15, y=0.56, width=0.70, height=0.10)
            description.style.update({
                'text_align': 'center',
                'font_style': 'italic'
            })
            positioned.append(description)
        
        # Add progress indicator at bottom
        if progress:
            progress.position = ElementPosition(x=0.10, y=0.85, width=0.80, height=0.08)
            positioned.append(progress)
        
        return positioned


def get_layout_by_type(layout_type: str, config: Optional[LayoutConfig] = None) -> BaseLayout:
    """
    Factory function to get layout by type
    
    Args:
        layout_type: Type of layout
        config: Optional layout configuration
        
    Returns:
        Layout instance
    """
    layouts = {
        'title_slide': TitleSlideLayout,
        'content_slide': ContentSlideLayout,
        'comparison_slide': ComparisonSlideLayout,
        'image_focused': ImageFocusedLayout,
        'data_visualization': DataVisualizationLayout,
        'quote_highlight': QuoteHighlightLayout,
        'section_divider': SectionDividerLayout
    }
    
    layout_class = layouts.get(layout_type)
    if not layout_class:
        # Default to content slide
        layout_class = ContentSlideLayout
    
    return layout_class(config)