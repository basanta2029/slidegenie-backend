"""
Slide Layout System Package

This package provides comprehensive layout templates and positioning
algorithms for academic presentations.
"""

from .base import BaseLayout, LayoutConfig, ElementPosition
from .templates import (
    TitleSlideLayout,
    ContentSlideLayout,
    ComparisonSlideLayout,
    ImageFocusedLayout,
    DataVisualizationLayout,
    QuoteHighlightLayout,
    SectionDividerLayout,
    get_layout_by_type
)
from .positioning import PositioningEngine, PositioningStrategy
from .academic_patterns import AcademicDesignPatterns
from .responsive import ResponsiveAdapter
from .grid import GridSystem, GridConfig

__all__ = [
    # Base classes
    'BaseLayout',
    'LayoutConfig',
    'ElementPosition',
    
    # Layout templates
    'TitleSlideLayout',
    'ContentSlideLayout',
    'ComparisonSlideLayout',
    'ImageFocusedLayout',
    'DataVisualizationLayout',
    'QuoteHighlightLayout',
    'SectionDividerLayout',
    'get_layout_by_type',
    
    # Positioning system
    'PositioningEngine',
    'PositioningStrategy',
    
    # Design patterns
    'AcademicDesignPatterns',
    
    # Responsive system
    'ResponsiveAdapter',
    
    # Grid system
    'GridSystem',
    'GridConfig'
]