"""
Grid System Implementation

Provides a flexible grid system for precise element positioning
and alignment in slide layouts.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum

from .base import ElementPosition


class GridAlignment(Enum):
    """Grid alignment options"""
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


@dataclass
class GridConfig:
    """Configuration for the grid system"""
    columns: int = 12  # Number of columns
    rows: int = 8  # Number of rows
    gutter_x: float = 0.01  # Horizontal gutter (1% of width)
    gutter_y: float = 0.01  # Vertical gutter (1% of height)
    margin_x: float = 0.05  # Horizontal margin
    margin_y: float = 0.05  # Vertical margin


@dataclass
class GridCell:
    """Represents a cell in the grid"""
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    alignment: GridAlignment = GridAlignment.TOP_LEFT
    
    def validate(self, grid_config: GridConfig) -> bool:
        """Validate cell against grid configuration"""
        return (0 <= self.row < grid_config.rows and
                0 <= self.col < grid_config.columns and
                self.row + self.row_span <= grid_config.rows and
                self.col + self.col_span <= grid_config.columns)


class GridSystem:
    """
    Flexible grid system for slide layouts
    
    Provides methods for:
    - Converting grid positions to normalized coordinates
    - Aligning elements within grid cells
    - Creating responsive grid layouts
    - Managing grid-based spacing
    """
    
    def __init__(self, config: Optional[GridConfig] = None):
        self.config = config or GridConfig()
        self._cell_cache: Dict[str, ElementPosition] = {}
    
    def get_cell_position(self, cell: GridCell) -> ElementPosition:
        """
        Get the position for a grid cell
        
        Args:
            cell: Grid cell specification
            
        Returns:
            ElementPosition in normalized coordinates
        """
        # Check cache
        cache_key = f"{cell.row},{cell.col},{cell.row_span},{cell.col_span}"
        if cache_key in self._cell_cache:
            return self._cell_cache[cache_key]
        
        # Calculate cell dimensions
        cell_width = (1.0 - 2 * self.config.margin_x - 
                     (self.config.columns - 1) * self.config.gutter_x) / self.config.columns
        cell_height = (1.0 - 2 * self.config.margin_y - 
                      (self.config.rows - 1) * self.config.gutter_y) / self.config.rows
        
        # Calculate position
        x = self.config.margin_x + cell.col * (cell_width + self.config.gutter_x)
        y = self.config.margin_y + cell.row * (cell_height + self.config.gutter_y)
        
        # Calculate size with spans
        width = (cell.col_span * cell_width + 
                (cell.col_span - 1) * self.config.gutter_x)
        height = (cell.row_span * cell_height + 
                 (cell.row_span - 1) * self.config.gutter_y)
        
        position = ElementPosition(x=x, y=y, width=width, height=height)
        
        # Cache the result
        self._cell_cache[cache_key] = position
        
        return position
    
    def align_in_cell(self, content_size: Tuple[float, float], 
                     cell: GridCell) -> ElementPosition:
        """
        Align content within a grid cell
        
        Args:
            content_size: (width, height) of content in normalized units
            cell: Grid cell to align within
            
        Returns:
            ElementPosition for the aligned content
        """
        cell_pos = self.get_cell_position(cell)
        content_width, content_height = content_size
        
        # Calculate offsets based on alignment
        x_offset = 0.0
        y_offset = 0.0
        
        # Horizontal alignment
        if cell.alignment in [GridAlignment.TOP_CENTER, GridAlignment.CENTER, 
                             GridAlignment.BOTTOM_CENTER]:
            x_offset = (cell_pos.width - content_width) / 2
        elif cell.alignment in [GridAlignment.TOP_RIGHT, GridAlignment.CENTER_RIGHT,
                               GridAlignment.BOTTOM_RIGHT]:
            x_offset = cell_pos.width - content_width
        
        # Vertical alignment
        if cell.alignment in [GridAlignment.CENTER_LEFT, GridAlignment.CENTER,
                             GridAlignment.CENTER_RIGHT]:
            y_offset = (cell_pos.height - content_height) / 2
        elif cell.alignment in [GridAlignment.BOTTOM_LEFT, GridAlignment.BOTTOM_CENTER,
                               GridAlignment.BOTTOM_RIGHT]:
            y_offset = cell_pos.height - content_height
        
        return ElementPosition(
            x=cell_pos.x + x_offset,
            y=cell_pos.y + y_offset,
            width=content_width,
            height=content_height
        )
    
    def create_equal_columns(self, num_columns: int, 
                           row: int = 0, 
                           row_span: int = None) -> List[GridCell]:
        """
        Create equal-width columns
        
        Args:
            num_columns: Number of columns to create
            row: Starting row
            row_span: Height in rows (default: full height)
            
        Returns:
            List of GridCell objects
        """
        if row_span is None:
            row_span = self.config.rows - row
        
        col_span = self.config.columns // num_columns
        remainder = self.config.columns % num_columns
        
        cells = []
        current_col = 0
        
        for i in range(num_columns):
            # Distribute remainder columns
            span = col_span + (1 if i < remainder else 0)
            
            cells.append(GridCell(
                row=row,
                col=current_col,
                row_span=row_span,
                col_span=span
            ))
            
            current_col += span
        
        return cells
    
    def create_golden_ratio_split(self, vertical: bool = False) -> Tuple[GridCell, GridCell]:
        """
        Create a golden ratio split (1.618:1)
        
        Args:
            vertical: If True, split vertically; otherwise horizontally
            
        Returns:
            Tuple of (larger_cell, smaller_cell)
        """
        golden_ratio = 1.618
        
        if vertical:
            # Vertical split
            total_rows = self.config.rows
            larger_rows = int(total_rows * golden_ratio / (golden_ratio + 1))
            smaller_rows = total_rows - larger_rows
            
            larger_cell = GridCell(row=0, col=0, 
                                 row_span=larger_rows, 
                                 col_span=self.config.columns)
            smaller_cell = GridCell(row=larger_rows, col=0,
                                  row_span=smaller_rows,
                                  col_span=self.config.columns)
        else:
            # Horizontal split
            total_cols = self.config.columns
            larger_cols = int(total_cols * golden_ratio / (golden_ratio + 1))
            smaller_cols = total_cols - larger_cols
            
            larger_cell = GridCell(row=0, col=0,
                                 row_span=self.config.rows,
                                 col_span=larger_cols)
            smaller_cell = GridCell(row=0, col=larger_cols,
                                  row_span=self.config.rows,
                                  col_span=smaller_cols)
        
        return larger_cell, smaller_cell
    
    def create_thirds_layout(self) -> List[GridCell]:
        """Create a rule-of-thirds layout"""
        cells = []
        
        rows_per_third = self.config.rows // 3
        cols_per_third = self.config.columns // 3
        
        for row in range(3):
            for col in range(3):
                cells.append(GridCell(
                    row=row * rows_per_third,
                    col=col * cols_per_third,
                    row_span=rows_per_third,
                    col_span=cols_per_third
                ))
        
        return cells
    
    def get_center_cell(self, width_ratio: float = 0.8, 
                       height_ratio: float = 0.8) -> GridCell:
        """
        Get a centered cell with specified size ratio
        
        Args:
            width_ratio: Width as ratio of total columns
            height_ratio: Height as ratio of total rows
            
        Returns:
            GridCell positioned at center
        """
        col_span = int(self.config.columns * width_ratio)
        row_span = int(self.config.rows * height_ratio)
        
        start_col = (self.config.columns - col_span) // 2
        start_row = (self.config.rows - row_span) // 2
        
        return GridCell(
            row=start_row,
            col=start_col,
            row_span=row_span,
            col_span=col_span,
            alignment=GridAlignment.CENTER
        )
    
    def create_responsive_grid(self, aspect_ratio: Tuple[int, int]) -> 'GridSystem':
        """
        Create a responsive grid based on aspect ratio
        
        Args:
            aspect_ratio: (width, height) ratio
            
        Returns:
            New GridSystem configured for the aspect ratio
        """
        width_ratio, height_ratio = aspect_ratio
        
        # Adjust grid dimensions based on aspect ratio
        if width_ratio > height_ratio:
            # Wide format - more columns
            columns = 16
            rows = int(16 * height_ratio / width_ratio)
        else:
            # Tall format - more rows
            columns = int(12 * width_ratio / height_ratio)
            rows = 12
        
        config = GridConfig(
            columns=columns,
            rows=rows,
            gutter_x=self.config.gutter_x,
            gutter_y=self.config.gutter_y,
            margin_x=self.config.margin_x,
            margin_y=self.config.margin_y
        )
        
        return GridSystem(config)
    
    def get_safe_text_area(self, cell: GridCell, 
                          padding: float = 0.02) -> ElementPosition:
        """
        Get safe area for text within a cell
        
        Args:
            cell: Grid cell
            padding: Internal padding
            
        Returns:
            ElementPosition with padding applied
        """
        pos = self.get_cell_position(cell)
        return pos.with_margin(padding)
    
    def clear_cache(self):
        """Clear the position cache"""
        self._cell_cache.clear()