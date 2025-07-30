"""
Layout detection utilities for document processing.

Provides advanced layout analysis capabilities including column detection,
figure/table region identification, and document structure analysis.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import math

import structlog
import numpy as np

from app.domain.schemas.document_processing import (
    BoundingBox,
    LayoutInfo,
    DocumentElement,
    ElementType
)

logger = structlog.get_logger(__name__)


class RegionType(str, Enum):
    """Types of document regions."""
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    HEADER = "header"
    FOOTER = "footer"
    MARGIN = "margin"
    WHITESPACE = "whitespace"


@dataclass
class DocumentRegion:
    """A region within a document page."""
    bbox: BoundingBox
    region_type: RegionType
    confidence: float
    elements: List[DocumentElement]
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ColumnInfo:
    """Information about a column in the document."""
    index: int
    left_boundary: float
    right_boundary: float
    top: float
    bottom: float
    width: float
    elements: List[DocumentElement]
    
    @property
    def center(self) -> float:
        """Center x-coordinate of the column."""
        return (self.left_boundary + self.right_boundary) / 2


class LayoutDetector:
    """
    Advanced layout detection for academic documents.
    
    Detects columns, figures, tables, headers, footers, and other
    structural elements in document pages.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = structlog.get_logger(__name__)
        
        # Configuration parameters
        self.column_gap_threshold = self.config.get('column_gap_threshold', 20.0)
        self.margin_threshold = self.config.get('margin_threshold', 50.0)
        self.header_height_ratio = self.config.get('header_height_ratio', 0.1)
        self.footer_height_ratio = self.config.get('footer_height_ratio', 0.1)
        self.figure_min_size = self.config.get('figure_min_size', 50.0)
        self.table_min_size = self.config.get('table_min_size', 30.0)
    
    def analyze_page_layout(self, elements: List[DocumentElement], 
                           page_width: float, page_height: float) -> LayoutInfo:
        """
        Analyze the layout of a document page.
        
        Args:
            elements: List of document elements on the page
            page_width: Page width in points
            page_height: Page height in points
            
        Returns:
            LayoutInfo object with detected layout information
        """
        page_number = elements[0].bbox.page if elements and elements[0].bbox else 0
        
        # Detect columns
        columns = self.detect_columns(elements, page_width)
        
        # Detect regions
        regions = self.detect_regions(elements, page_width, page_height)
        
        # Separate regions by type
        text_regions = [r.bbox for r in regions if r.region_type == RegionType.TEXT]
        figure_regions = [r.bbox for r in regions if r.region_type == RegionType.FIGURE]
        table_regions = [r.bbox for r in regions if r.region_type == RegionType.TABLE]
        header_region = next((r.bbox for r in regions if r.region_type == RegionType.HEADER), None)
        footer_region = next((r.bbox for r in regions if r.region_type == RegionType.FOOTER), None)
        
        # Calculate margins
        margins = self.calculate_margins(elements, page_width, page_height)
        
        # Create column boundaries
        column_boundaries = [(col.left_boundary, col.right_boundary) for col in columns]
        
        return LayoutInfo(
            page_number=page_number,
            page_width=page_width,
            page_height=page_height,
            columns=len(columns),
            column_boundaries=column_boundaries,
            text_regions=text_regions,
            figure_regions=figure_regions,
            table_regions=table_regions,
            header_region=header_region,
            footer_region=footer_region,
            margins=margins
        )
    
    def detect_columns(self, elements: List[DocumentElement], 
                      page_width: float) -> List[ColumnInfo]:
        """
        Detect columns in the document page.
        
        Args:
            elements: List of document elements
            page_width: Page width in points
            
        Returns:
            List of ColumnInfo objects
        """
        if not elements:
            return []
        
        # Get elements with bounding boxes
        text_elements = [elem for elem in elements 
                        if elem.bbox and elem.element_type in [ElementType.TEXT, ElementType.PARAGRAPH]]
        
        if not text_elements:
            return []
        
        # Extract x-coordinates
        x_coords = []
        for elem in text_elements:
            x_coords.extend([elem.bbox.x0, elem.bbox.x1])
        
        x_coords.sort()
        
        # Find column gaps using density analysis
        column_boundaries = self._find_column_boundaries(x_coords, page_width)
        
        # Create column info objects
        columns = []
        for i, (left, right) in enumerate(column_boundaries):
            # Find elements in this column
            column_elements = []
            for elem in text_elements:
                elem_center = (elem.bbox.x0 + elem.bbox.x1) / 2
                if left <= elem_center <= right:
                    column_elements.append(elem)
            
            if column_elements:
                # Calculate column bounds
                top = max(elem.bbox.y1 for elem in column_elements)
                bottom = min(elem.bbox.y0 for elem in column_elements)
                
                column = ColumnInfo(
                    index=i,
                    left_boundary=left,
                    right_boundary=right,
                    top=top,
                    bottom=bottom,
                    width=right - left,
                    elements=column_elements
                )
                columns.append(column)
        
        return columns
    
    def detect_regions(self, elements: List[DocumentElement], 
                      page_width: float, page_height: float) -> List[DocumentRegion]:
        """
        Detect different types of regions on the page.
        
        Args:
            elements: List of document elements
            page_width: Page width in points
            page_height: Page height in points
            
        Returns:
            List of DocumentRegion objects
        """
        regions = []
        
        if not elements:
            return regions
        
        # Detect header region
        header_region = self._detect_header_region(elements, page_width, page_height)
        if header_region:
            regions.append(header_region)
        
        # Detect footer region
        footer_region = self._detect_footer_region(elements, page_width, page_height)
        if footer_region:
            regions.append(footer_region)
        
        # Detect figure regions
        figure_regions = self._detect_figure_regions(elements)
        regions.extend(figure_regions)
        
        # Detect table regions
        table_regions = self._detect_table_regions(elements)
        regions.extend(table_regions)
        
        # Detect text regions (remaining areas)
        text_regions = self._detect_text_regions(elements, regions)
        regions.extend(text_regions)
        
        return regions
    
    def calculate_margins(self, elements: List[DocumentElement], 
                         page_width: float, page_height: float) -> Dict[str, float]:
        """
        Calculate page margins based on element positions.
        
        Args:
            elements: List of document elements
            page_width: Page width in points
            page_height: Page height in points
            
        Returns:
            Dictionary with margin measurements
        """
        if not elements:
            return {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}
        
        # Get elements with bounding boxes
        bounded_elements = [elem for elem in elements if elem.bbox]
        
        if not bounded_elements:
            return {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}
        
        # Calculate content bounds
        min_x = min(elem.bbox.x0 for elem in bounded_elements)
        max_x = max(elem.bbox.x1 for elem in bounded_elements)
        min_y = min(elem.bbox.y0 for elem in bounded_elements)
        max_y = max(elem.bbox.y1 for elem in bounded_elements)
        
        return {
            'left': min_x,
            'right': page_width - max_x,
            'bottom': min_y,
            'top': page_height - max_y
        }
    
    def detect_reading_flow(self, elements: List[DocumentElement]) -> List[DocumentElement]:
        """
        Detect the natural reading flow of elements.
        
        Args:
            elements: List of document elements
            
        Returns:
            List of elements sorted by reading order
        """
        if not elements:
            return elements
        
        # Detect columns first
        page_width = max(elem.bbox.x1 for elem in elements if elem.bbox) if elements else 1000
        columns = self.detect_columns(elements, page_width)
        
        # Sort elements within each column
        sorted_elements = []
        
        for column in columns:
            # Sort by y-coordinate (top to bottom)
            column_sorted = sorted(column.elements, 
                                 key=lambda e: -e.bbox.y1 if e.bbox else 0)
            sorted_elements.extend(column_sorted)
        
        # Handle elements not in any column
        unassigned = [elem for elem in elements 
                     if not any(elem in col.elements for col in columns)]
        
        if unassigned:
            unassigned_sorted = sorted(unassigned,
                                     key=lambda e: (-e.bbox.y1, e.bbox.x0) if e.bbox else (0, 0))
            sorted_elements.extend(unassigned_sorted)
        
        return sorted_elements
    
    def _find_column_boundaries(self, x_coords: List[float], 
                               page_width: float) -> List[Tuple[float, float]]:
        """Find column boundaries using coordinate analysis."""
        if not x_coords:
            return [(0, page_width)]
        
        # Create histogram of x-coordinates
        hist, bin_edges = np.histogram(x_coords, bins=50)
        
        # Find gaps in the histogram (potential column separators)
        gap_threshold = max(hist) * 0.1  # 10% of max frequency
        gap_indices = np.where(hist < gap_threshold)[0]
        
        # Find continuous gap regions
        gap_regions = []
        if len(gap_indices) > 0:
            start = gap_indices[0]
            for i in range(1, len(gap_indices)):
                if gap_indices[i] - gap_indices[i-1] > 1:
                    # End of current gap region
                    end = gap_indices[i-1]
                    gap_center = (bin_edges[start] + bin_edges[end + 1]) / 2
                    gap_regions.append(gap_center)
                    start = gap_indices[i]
            
            # Handle last gap region
            end = gap_indices[-1]
            gap_center = (bin_edges[start] + bin_edges[end + 1]) / 2
            gap_regions.append(gap_center)
        
        # Create column boundaries
        if not gap_regions:
            return [(min(x_coords), max(x_coords))]
        
        # Filter gaps that are too close to page edges
        significant_gaps = [gap for gap in gap_regions 
                           if gap > page_width * 0.1 and gap < page_width * 0.9]
        
        if not significant_gaps:
            return [(min(x_coords), max(x_coords))]
        
        # Create column boundaries
        boundaries = []
        left = min(x_coords)
        
        for gap in sorted(significant_gaps):
            boundaries.append((left, gap))
            left = gap
        
        # Add final column
        boundaries.append((left, max(x_coords)))
        
        # Filter out very narrow columns
        min_column_width = page_width * 0.15  # 15% of page width
        filtered_boundaries = [b for b in boundaries if b[1] - b[0] > min_column_width]
        
        return filtered_boundaries if filtered_boundaries else [(min(x_coords), max(x_coords))]
    
    def _detect_header_region(self, elements: List[DocumentElement], 
                             page_width: float, page_height: float) -> Optional[DocumentRegion]:
        """Detect header region."""
        header_threshold = page_height * (1 - self.header_height_ratio)
        
        header_elements = [elem for elem in elements 
                          if elem.bbox and elem.bbox.y0 > header_threshold]
        
        if not header_elements:
            return None
        
        # Create bounding box for header region
        min_x = min(elem.bbox.x0 for elem in header_elements)
        max_x = max(elem.bbox.x1 for elem in header_elements)
        min_y = min(elem.bbox.y0 for elem in header_elements)
        max_y = max(elem.bbox.y1 for elem in header_elements)
        
        bbox = BoundingBox(
            x0=min_x, y0=min_y, x1=max_x, y1=max_y,
            page=header_elements[0].bbox.page
        )
        
        return DocumentRegion(
            bbox=bbox,
            region_type=RegionType.HEADER,
            confidence=0.8,
            elements=header_elements
        )
    
    def _detect_footer_region(self, elements: List[DocumentElement], 
                             page_width: float, page_height: float) -> Optional[DocumentRegion]:
        """Detect footer region."""
        footer_threshold = page_height * self.footer_height_ratio
        
        footer_elements = [elem for elem in elements 
                          if elem.bbox and elem.bbox.y1 < footer_threshold]
        
        if not footer_elements:
            return None
        
        # Create bounding box for footer region
        min_x = min(elem.bbox.x0 for elem in footer_elements)
        max_x = max(elem.bbox.x1 for elem in footer_elements)
        min_y = min(elem.bbox.y0 for elem in footer_elements)
        max_y = max(elem.bbox.y1 for elem in footer_elements)
        
        bbox = BoundingBox(
            x0=min_x, y0=min_y, x1=max_x, y1=max_y,
            page=footer_elements[0].bbox.page
        )
        
        return DocumentRegion(
            bbox=bbox,
            region_type=RegionType.FOOTER,
            confidence=0.8,
            elements=footer_elements
        )
    
    def _detect_figure_regions(self, elements: List[DocumentElement]) -> List[DocumentRegion]:
        """Detect figure regions."""
        figure_regions = []
        
        # Look for elements marked as figures
        figure_elements = [elem for elem in elements 
                          if elem.element_type == ElementType.FIGURE]
        
        for elem in figure_elements:
            if elem.bbox and elem.bbox.width > self.figure_min_size and elem.bbox.height > self.figure_min_size:
                region = DocumentRegion(
                    bbox=elem.bbox,
                    region_type=RegionType.FIGURE,
                    confidence=0.9,
                    elements=[elem]
                )
                figure_regions.append(region)
        
        return figure_regions
    
    def _detect_table_regions(self, elements: List[DocumentElement]) -> List[DocumentRegion]:
        """Detect table regions."""
        table_regions = []
        
        # Look for elements marked as tables
        table_elements = [elem for elem in elements 
                         if elem.element_type == ElementType.TABLE]
        
        for elem in table_elements:
            if elem.bbox and elem.bbox.width > self.table_min_size and elem.bbox.height > self.table_min_size:
                region = DocumentRegion(
                    bbox=elem.bbox,
                    region_type=RegionType.TABLE,
                    confidence=0.9,
                    elements=[elem]
                )
                table_regions.append(region)
        
        return table_regions
    
    def _detect_text_regions(self, elements: List[DocumentElement], 
                            existing_regions: List[DocumentRegion]) -> List[DocumentRegion]:
        """Detect text regions not covered by other regions."""
        text_regions = []
        
        # Get text elements
        text_elements = [elem for elem in elements 
                        if elem.element_type in [ElementType.TEXT, ElementType.PARAGRAPH, ElementType.HEADING]
                        and elem.bbox]
        
        if not text_elements:
            return text_regions
        
        # Remove elements that are already in other regions
        existing_bboxes = [region.bbox for region in existing_regions]
        unassigned_elements = []
        
        for elem in text_elements:
            # Check if element overlaps with existing regions
            overlaps = any(elem.bbox.overlaps(bbox) for bbox in existing_bboxes)
            if not overlaps:
                unassigned_elements.append(elem)
        
        if unassigned_elements:
            # Group nearby text elements
            text_groups = self._group_nearby_elements(unassigned_elements)
            
            for group in text_groups:
                if len(group) > 0:
                    # Create bounding box for text region
                    min_x = min(elem.bbox.x0 for elem in group)
                    max_x = max(elem.bbox.x1 for elem in group)
                    min_y = min(elem.bbox.y0 for elem in group)
                    max_y = max(elem.bbox.y1 for elem in group)
                    
                    bbox = BoundingBox(
                        x0=min_x, y0=min_y, x1=max_x, y1=max_y,
                        page=group[0].bbox.page
                    )
                    
                    region = DocumentRegion(
                        bbox=bbox,
                        region_type=RegionType.TEXT,
                        confidence=0.7,
                        elements=group
                    )
                    text_regions.append(region)
        
        return text_regions
    
    def _group_nearby_elements(self, elements: List[DocumentElement], 
                              distance_threshold: float = 50.0) -> List[List[DocumentElement]]:
        """Group nearby elements together."""
        if not elements:
            return []
        
        groups = []
        used = set()
        
        for i, elem in enumerate(elements):
            if i in used:
                continue
            
            group = [elem]
            used.add(i)
            
            # Find nearby elements
            for j, other_elem in enumerate(elements):
                if j in used or i == j:
                    continue
                
                # Calculate distance between elements
                if elem.bbox and other_elem.bbox:
                    center1 = elem.bbox.center
                    center2 = other_elem.bbox.center
                    distance = math.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
                    
                    if distance < distance_threshold:
                        group.append(other_elem)
                        used.add(j)
            
            groups.append(group)
        
        return groups