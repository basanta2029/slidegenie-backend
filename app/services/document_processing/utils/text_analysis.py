"""
Text analysis utilities for document processing.

Provides advanced text analysis capabilities including layout analysis,
reading order detection, and text classification for academic documents.
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

import structlog
from pydantic import BaseModel

from app.domain.schemas.document_processing import (
    BoundingBox, 
    TextElement, 
    TextStyle,
    ElementType
)

logger = structlog.get_logger(__name__)


class TextCategory(str, Enum):
    """Categories for text classification."""
    TITLE = "title"
    AUTHOR = "author"
    AFFILIATION = "affiliation"
    ABSTRACT = "abstract"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CAPTION = "caption"
    REFERENCE = "reference"
    FOOTER = "footer"
    HEADER = "header"
    PAGE_NUMBER = "page_number"
    EQUATION = "equation"
    TABLE_CELL = "table_cell"
    UNKNOWN = "unknown"


@dataclass
class ReadingOrderGroup:
    """Group of text elements with similar reading order."""
    elements: List[TextElement]
    column_index: int
    y_position: float
    confidence: float


@dataclass 
class TextCluster:
    """Cluster of text elements with similar properties."""
    elements: List[TextElement]
    category: TextCategory
    confidence: float
    representative_style: Optional[TextStyle] = None


class TextAnalyzer:
    """
    Advanced text analysis for academic documents.
    
    Provides methods for text classification, reading order detection,
    layout analysis, and content structure recognition.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = structlog.get_logger(__name__)
        
        # Regex patterns for academic content
        self._patterns = {
            'title': [
                r'^[A-Z][^.!?]*(?:[:.][^.!?]*)*$',  # Title case without sentence ending
                r'^(?:[A-Z][a-z]*\s*){2,}[A-Z][a-z]*(?:\s*[:\-]\s*[A-Z].*)?$',  # Multi-word title
            ],
            'author': [
                r'^[A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)*$',
                r'^[A-Z]\.\s*[A-Z][a-z]+(?:\s*,\s*[A-Z]\.\s*[A-Z][a-z]+)*$',
            ],
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'doi': r'(?:doi:?\s*)?10\.[0-9]+\/[^\s]+',
            'reference_number': r'^\s*\[?\d+\]?\s*$',
            'page_number': r'^\s*\d+\s*$',
            'section_number': r'^\s*(?:\d+\.)*\d+\s+[A-Z]',
            'figure_caption': r'^(?:Fig(?:ure)?\.?\s*\d+|Figure\s+\d+)[:\-\.]?\s*',
            'table_caption': r'^(?:Tab(?:le)?\.?\s*\d+|Table\s+\d+)[:\-\.]?\s*',
            'equation': r'^\s*\([0-9]+\)\s*$|[=<>≤≥±∫∑∏√]',
        }
        
        # Font size thresholds (relative to document average)
        self.title_font_threshold = 1.5
        self.heading_font_threshold = 1.2
        self.small_font_threshold = 0.8
        
    def classify_text_elements(self, elements: List[TextElement]) -> List[TextCluster]:
        """
        Classify text elements into semantic categories.
        
        Args:
            elements: List of text elements to classify
            
        Returns:
            List of text clusters with categories
        """
        clusters = []
        
        # Calculate document statistics
        font_sizes = [elem.style.font_size for elem in elements 
                     if elem.style and elem.style.font_size]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12.0
        
        # Group elements by category
        categorized = {}
        for element in elements:
            category = self._classify_single_element(element, avg_font_size)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(element)
            
        # Create clusters
        for category, elems in categorized.items():
            if elems:
                cluster = TextCluster(
                    elements=elems,
                    category=category,
                    confidence=self._calculate_category_confidence(elems, category),
                    representative_style=self._get_representative_style(elems)
                )
                clusters.append(cluster)
                
        return clusters
        
    def detect_reading_order(self, elements: List[TextElement]) -> List[TextElement]:
        """
        Detect and assign reading order to text elements.
        
        Args:
            elements: List of text elements
            
        Returns:
            List of elements with reading_order assigned
        """
        if not elements:
            return elements
            
        # Group elements by column
        column_groups = self._group_by_columns(elements)
        
        # Sort within each column by y-coordinate (top to bottom)
        ordered_elements = []
        reading_order = 0
        
        for column_idx, column_elements in enumerate(column_groups):
            # Sort by y-coordinate (descending for top-to-bottom reading)
            sorted_column = sorted(column_elements, 
                                 key=lambda e: e.bbox.y1 if e.bbox else 0, 
                                 reverse=True)
            
            for element in sorted_column:
                element.reading_order = reading_order
                element.column_index = column_idx
                ordered_elements.append(element)
                reading_order += 1
                
        return ordered_elements
        
    def detect_multi_column_layout(self, elements: List[TextElement]) -> Dict:
        """
        Detect multi-column layout in text elements.
        
        Args:
            elements: List of text elements
            
        Returns:
            Dictionary with column information
        """
        if not elements:
            return {'columns': 1, 'boundaries': []}
            
        # Get x-coordinates of all elements
        x_coords = []
        for element in elements:
            if element.bbox:
                x_coords.append(element.bbox.x0)
                x_coords.append(element.bbox.x1)
                
        if not x_coords:
            return {'columns': 1, 'boundaries': []}
            
        # Find column boundaries using clustering
        x_coords.sort()
        min_x, max_x = min(x_coords), max(x_coords)
        
        # Simple column detection: look for gaps in x-coordinates
        gaps = []
        threshold = (max_x - min_x) * 0.05  # 5% of page width
        
        for i in range(1, len(x_coords)):
            if x_coords[i] - x_coords[i-1] > threshold:
                gaps.append((x_coords[i-1], x_coords[i]))
                
        # Determine column boundaries
        if not gaps:
            return {'columns': 1, 'boundaries': [(min_x, max_x)]}
            
        # Find the largest gap (likely column separator)
        largest_gap = max(gaps, key=lambda g: g[1] - g[0])
        gap_center = (largest_gap[0] + largest_gap[1]) / 2
        
        return {
            'columns': 2,
            'boundaries': [(min_x, gap_center), (gap_center, max_x)],
            'gap': largest_gap
        }
        
    def extract_text_statistics(self, elements: List[TextElement]) -> Dict:
        """
        Extract statistical information about text elements.
        
        Args:
            elements: List of text elements
            
        Returns:
            Dictionary with text statistics
        """
        if not elements:
            return {}
            
        stats = {
            'total_elements': len(elements),
            'total_characters': sum(len(elem.content) for elem in elements),
            'total_words': sum(len(elem.content.split()) for elem in elements),
            'font_sizes': [],
            'line_heights': [],
            'element_heights': [],
            'element_widths': [],
        }
        
        for element in elements:
            if element.style and element.style.font_size:
                stats['font_sizes'].append(element.style.font_size)
                
            if element.line_height:
                stats['line_heights'].append(element.line_height)
                
            if element.bbox:
                stats['element_heights'].append(element.bbox.height)
                stats['element_widths'].append(element.bbox.width)
                
        # Calculate averages and distributions
        for key in ['font_sizes', 'line_heights', 'element_heights', 'element_widths']:
            values = stats[key]
            if values:
                stats[f'avg_{key[:-1]}'] = sum(values) / len(values)
                stats[f'min_{key[:-1]}'] = min(values)
                stats[f'max_{key[:-1]}'] = max(values)
                
        return stats
        
    def merge_text_elements(self, elements: List[TextElement], 
                           merge_threshold: float = 5.0) -> List[TextElement]:
        """
        Merge nearby text elements that likely belong together.
        
        Args:
            elements: List of text elements
            merge_threshold: Distance threshold for merging
            
        Returns:
            List of merged text elements
        """
        if not elements:
            return elements
            
        # Sort elements by reading order
        sorted_elements = sorted(elements, 
                               key=lambda e: e.reading_order or 0)
        
        merged = []
        current_group = [sorted_elements[0]]
        
        for i in range(1, len(sorted_elements)):
            current = sorted_elements[i]
            previous = sorted_elements[i-1]
            
            # Check if elements should be merged
            if self._should_merge_elements(previous, current, merge_threshold):
                current_group.append(current)
            else:
                # Merge current group and start new one
                if len(current_group) > 1:
                    merged_element = self._merge_element_group(current_group)
                    merged.append(merged_element)
                else:
                    merged.extend(current_group)
                current_group = [current]
                
        # Handle last group
        if len(current_group) > 1:
            merged_element = self._merge_element_group(current_group)
            merged.append(merged_element)
        else:
            merged.extend(current_group)
            
        return merged
        
    def _classify_single_element(self, element: TextElement, avg_font_size: float) -> TextCategory:
        """Classify a single text element."""
        content = element.content.strip()
        
        if not content:
            return TextCategory.UNKNOWN
            
        # Check for page numbers
        if re.match(self._patterns['page_number'], content):
            return TextCategory.PAGE_NUMBER
            
        # Check for reference numbers
        if re.match(self._patterns['reference_number'], content):
            return TextCategory.REFERENCE
            
        # Check for equations
        if re.search(self._patterns['equation'], content):
            return TextCategory.EQUATION
            
        # Check for captions
        if re.match(self._patterns['figure_caption'], content, re.IGNORECASE):
            return TextCategory.CAPTION
        if re.match(self._patterns['table_caption'], content, re.IGNORECASE):
            return TextCategory.CAPTION
            
        # Check font size for classification
        font_size = element.style.font_size if element.style else avg_font_size
        
        # Large font might be title or heading
        if font_size > avg_font_size * self.title_font_threshold:
            if any(re.match(pattern, content) for pattern in self._patterns['title']):
                return TextCategory.TITLE
            return TextCategory.HEADING
            
        # Medium-large font might be heading
        if font_size > avg_font_size * self.heading_font_threshold:
            if re.match(self._patterns['section_number'], content):
                return TextCategory.HEADING
            return TextCategory.HEADING
            
        # Check for author patterns
        if any(re.match(pattern, content) for pattern in self._patterns['author']):
            return TextCategory.AUTHOR
            
        # Check for email (likely affiliation)
        if re.search(self._patterns['email'], content):
            return TextCategory.AFFILIATION
            
        # Small font might be footer/header
        if font_size < avg_font_size * self.small_font_threshold:
            # Check position to determine if header or footer
            if element.bbox and element.bbox.y1 > 700:  # Approximate header position
                return TextCategory.HEADER
            else:
                return TextCategory.FOOTER
                
        # Default to paragraph for regular text
        return TextCategory.PARAGRAPH
        
    def _group_by_columns(self, elements: List[TextElement]) -> List[List[TextElement]]:
        """Group elements by columns."""
        if not elements:
            return []
            
        layout_info = self.detect_multi_column_layout(elements)
        boundaries = layout_info['boundaries']
        
        if len(boundaries) == 1:
            return [elements]
            
        # Assign elements to columns
        columns = [[] for _ in boundaries]
        
        for element in elements:
            if not element.bbox:
                columns[0].append(element)  # Default to first column
                continue
                
            element_center_x = (element.bbox.x0 + element.bbox.x1) / 2
            
            # Find which column this element belongs to
            for i, (left, right) in enumerate(boundaries):
                if left <= element_center_x <= right:
                    columns[i].append(element)
                    break
            else:
                # Element doesn't fit in any column, add to nearest
                distances = [min(abs(element_center_x - left), abs(element_center_x - right))
                           for left, right in boundaries]
                nearest_column = distances.index(min(distances))
                columns[nearest_column].append(element)
                
        return [col for col in columns if col]  # Remove empty columns
        
    def _calculate_category_confidence(self, elements: List[TextElement], 
                                     category: TextCategory) -> float:
        """Calculate confidence score for category classification."""
        if not elements:
            return 0.0
            
        # Simple confidence based on pattern matches and consistency
        pattern_matches = 0
        style_consistency = 0
        
        for element in elements:
            content = element.content.strip()
            
            # Check pattern matches for specific categories
            if category == TextCategory.TITLE:
                if any(re.match(pattern, content) for pattern in self._patterns['title']):
                    pattern_matches += 1
            elif category == TextCategory.AUTHOR:
                if any(re.match(pattern, content) for pattern in self._patterns['author']):
                    pattern_matches += 1
                    
        # Calculate confidence based on matches
        pattern_confidence = pattern_matches / len(elements) if elements else 0
        
        # Add style consistency check
        if len(elements) > 1:
            font_sizes = [elem.style.font_size for elem in elements 
                         if elem.style and elem.style.font_size]
            if font_sizes:
                avg_size = sum(font_sizes) / len(font_sizes)
                variance = sum((size - avg_size) ** 2 for size in font_sizes) / len(font_sizes)
                style_consistency = max(0, 1 - (variance / avg_size))
                
        return min(1.0, (pattern_confidence + style_consistency) / 2)
        
    def _get_representative_style(self, elements: List[TextElement]) -> Optional[TextStyle]:
        """Get representative style for a group of elements."""
        if not elements:
            return None
            
        styles = [elem.style for elem in elements if elem.style]
        if not styles:
            return None
            
        # Find most common font properties
        font_names = [s.font_name for s in styles if s.font_name]
        font_sizes = [s.font_size for s in styles if s.font_size]
        
        return TextStyle(
            font_name=max(set(font_names), key=font_names.count) if font_names else None,
            font_size=sum(font_sizes) / len(font_sizes) if font_sizes else None,
            is_bold=sum(s.is_bold for s in styles) > len(styles) / 2,
            is_italic=sum(s.is_italic for s in styles) > len(styles) / 2,
        )
        
    def _should_merge_elements(self, elem1: TextElement, elem2: TextElement, 
                             threshold: float) -> bool:
        """Check if two elements should be merged."""
        if not elem1.bbox or not elem2.bbox:
            return False
            
        # Check if elements are on same line (similar y-coordinates)
        y_diff = abs(elem1.bbox.y0 - elem2.bbox.y0)
        if y_diff > threshold:
            return False
            
        # Check horizontal distance
        x_gap = elem2.bbox.x0 - elem1.bbox.x1
        if x_gap > threshold * 2:  # Allow larger horizontal gaps
            return False
            
        # Check if styles are similar
        if elem1.style and elem2.style:
            if (elem1.style.font_size and elem2.style.font_size and
                abs(elem1.style.font_size - elem2.style.font_size) > 2):
                return False
                
        return True
        
    def _merge_element_group(self, elements: List[TextElement]) -> TextElement:
        """Merge a group of elements into one."""
        if len(elements) == 1:
            return elements[0]
            
        # Combine content
        content = ' '.join(elem.content for elem in elements)
        
        # Create combined bounding box
        min_x0 = min(elem.bbox.x0 for elem in elements if elem.bbox)
        min_y0 = min(elem.bbox.y0 for elem in elements if elem.bbox)
        max_x1 = max(elem.bbox.x1 for elem in elements if elem.bbox)
        max_y1 = max(elem.bbox.y1 for elem in elements if elem.bbox)
        
        combined_bbox = BoundingBox(
            x0=min_x0, y0=min_y0, x1=max_x1, y1=max_y1,
            page=elements[0].bbox.page if elements[0].bbox else 0
        )
        
        # Use style from first element
        return TextElement(
            content=content,
            bbox=combined_bbox,
            style=elements[0].style,
            reading_order=elements[0].reading_order,
            column_index=elements[0].column_index
        )