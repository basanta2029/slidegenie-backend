"""
Base Layout Classes and Configuration

Provides the foundation for all slide layout templates with
support for multiple aspect ratios and theme awareness.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class AspectRatio(Enum):
    """Supported slide aspect ratios"""
    RATIO_16_9 = (16, 9)
    RATIO_4_3 = (4, 3)
    RATIO_SQUARE = (1, 1)
    
    @property
    def width_ratio(self) -> int:
        return self.value[0]
    
    @property
    def height_ratio(self) -> int:
        return self.value[1]
    
    def get_dimensions(self, width: int = 1920) -> Tuple[int, int]:
        """Calculate dimensions for given width"""
        height = int(width * self.height_ratio / self.width_ratio)
        return (width, height)


class ElementType(Enum):
    """Types of elements that can be positioned on a slide"""
    TITLE = "title"
    SUBTITLE = "subtitle"
    TEXT = "text"
    BULLET_LIST = "bullet_list"
    IMAGE = "image"
    CHART = "chart"
    DIAGRAM = "diagram"
    QUOTE = "quote"
    FOOTER = "footer"
    HEADER = "header"
    LOGO = "logo"
    AUTHOR_INFO = "author_info"
    PAGE_NUMBER = "page_number"
    CITATION = "citation"
    SHAPE = "shape"
    ICON = "icon"


@dataclass
class ElementPosition:
    """Represents the position and dimensions of an element"""
    x: float  # X coordinate (0-1 normalized)
    y: float  # Y coordinate (0-1 normalized)
    width: float  # Width (0-1 normalized)
    height: float  # Height (0-1 normalized)
    z_index: int = 0  # Layer order
    rotation: float = 0  # Rotation in degrees
    
    def to_pixels(self, slide_width: int, slide_height: int) -> Dict[str, int]:
        """Convert normalized coordinates to pixels"""
        return {
            'x': int(self.x * slide_width),
            'y': int(self.y * slide_height),
            'width': int(self.width * slide_width),
            'height': int(self.height * slide_height),
            'z_index': self.z_index,
            'rotation': self.rotation
        }
    
    def with_margin(self, margin: float) -> 'ElementPosition':
        """Return new position with margin applied"""
        return ElementPosition(
            x=self.x + margin,
            y=self.y + margin,
            width=self.width - (2 * margin),
            height=self.height - (2 * margin),
            z_index=self.z_index,
            rotation=self.rotation
        )


@dataclass
class LayoutConfig:
    """Configuration for a slide layout"""
    aspect_ratio: AspectRatio = AspectRatio.RATIO_16_9
    margin_top: float = 0.05  # 5% margin
    margin_bottom: float = 0.05
    margin_left: float = 0.05
    margin_right: float = 0.05
    spacing: float = 0.02  # 2% spacing between elements
    theme_aware: bool = True
    max_content_width: float = 0.9  # Maximum content width
    max_content_height: float = 0.9  # Maximum content height
    
    @property
    def content_area(self) -> ElementPosition:
        """Calculate the available content area"""
        return ElementPosition(
            x=self.margin_left,
            y=self.margin_top,
            width=1.0 - self.margin_left - self.margin_right,
            height=1.0 - self.margin_top - self.margin_bottom
        )


@dataclass
class LayoutElement:
    """Represents an element to be positioned in a layout"""
    type: ElementType
    content: Any
    position: Optional[ElementPosition] = None
    style: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def set_position(self, position: ElementPosition):
        """Set the element's position"""
        self.position = position
        return self


class BaseLayout(ABC):
    """
    Abstract base class for all slide layouts
    
    Provides common functionality for positioning elements,
    handling overflow, and maintaining visual hierarchy.
    """
    
    def __init__(self, config: Optional[LayoutConfig] = None):
        self.config = config or LayoutConfig()
        self.elements: List[LayoutElement] = []
        self._grid_system = None  # Lazy loaded
    
    @abstractmethod
    def get_layout_type(self) -> str:
        """Return the type identifier for this layout"""
        pass
    
    @abstractmethod
    def get_default_positions(self) -> Dict[ElementType, ElementPosition]:
        """Return default positions for common elements"""
        pass
    
    @abstractmethod
    def arrange_elements(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """
        Arrange elements according to the layout rules
        
        Args:
            elements: List of elements to position
            
        Returns:
            List of elements with positions set
        """
        pass
    
    def add_element(self, element: LayoutElement) -> 'BaseLayout':
        """Add an element to the layout"""
        self.elements.append(element)
        return self
    
    def clear_elements(self) -> 'BaseLayout':
        """Clear all elements from the layout"""
        self.elements.clear()
        return self
    
    def validate_layout(self) -> Tuple[bool, List[str]]:
        """
        Validate the current layout
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for overlapping elements
        for i, elem1 in enumerate(self.elements):
            if not elem1.position:
                issues.append(f"Element {i} has no position")
                continue
                
            for j, elem2 in enumerate(self.elements[i+1:], i+1):
                if not elem2.position:
                    continue
                    
                if self._elements_overlap(elem1.position, elem2.position):
                    issues.append(f"Elements {i} and {j} overlap")
        
        # Check for out-of-bounds elements
        for i, elem in enumerate(self.elements):
            if not elem.position:
                continue
                
            if (elem.position.x < 0 or elem.position.y < 0 or
                elem.position.x + elem.position.width > 1.0 or
                elem.position.y + elem.position.height > 1.0):
                issues.append(f"Element {i} is out of bounds")
        
        return len(issues) == 0, issues
    
    def _elements_overlap(self, pos1: ElementPosition, pos2: ElementPosition) -> bool:
        """Check if two element positions overlap"""
        # Check if one element is to the left of the other
        if (pos1.x + pos1.width <= pos2.x or 
            pos2.x + pos2.width <= pos1.x):
            return False
        
        # Check if one element is above the other
        if (pos1.y + pos1.height <= pos2.y or 
            pos2.y + pos2.height <= pos1.y):
            return False
        
        return True
    
    def handle_overflow(self, elements: List[LayoutElement]) -> List[List[LayoutElement]]:
        """
        Handle content overflow by splitting into multiple slides
        
        Args:
            elements: List of elements that may overflow
            
        Returns:
            List of element groups, one per slide
        """
        # Simple implementation - override in subclasses for sophisticated handling
        max_elements = 10  # Reasonable default
        
        if len(elements) <= max_elements:
            return [elements]
        
        # Split into chunks
        chunks = []
        for i in range(0, len(elements), max_elements):
            chunks.append(elements[i:i + max_elements])
        
        return chunks
    
    def apply_theme(self, theme: Dict[str, Any]) -> 'BaseLayout':
        """
        Apply theme settings to the layout
        
        Args:
            theme: Theme configuration dictionary
            
        Returns:
            Self for chaining
        """
        if not self.config.theme_aware:
            return self
        
        # Apply theme margins if specified
        if 'margins' in theme:
            margins = theme['margins']
            self.config.margin_top = margins.get('top', self.config.margin_top)
            self.config.margin_bottom = margins.get('bottom', self.config.margin_bottom)
            self.config.margin_left = margins.get('left', self.config.margin_left)
            self.config.margin_right = margins.get('right', self.config.margin_right)
        
        # Apply theme spacing
        if 'spacing' in theme:
            self.config.spacing = theme['spacing']
        
        return self
    
    def get_safe_area(self) -> ElementPosition:
        """Get the safe area for content placement"""
        return self.config.content_area
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert layout to dictionary representation"""
        return {
            'type': self.get_layout_type(),
            'config': {
                'aspect_ratio': self.config.aspect_ratio.name,
                'margins': {
                    'top': self.config.margin_top,
                    'bottom': self.config.margin_bottom,
                    'left': self.config.margin_left,
                    'right': self.config.margin_right
                },
                'spacing': self.config.spacing
            },
            'elements': [
                {
                    'type': elem.type.value,
                    'position': {
                        'x': elem.position.x,
                        'y': elem.position.y,
                        'width': elem.position.width,
                        'height': elem.position.height,
                        'z_index': elem.position.z_index,
                        'rotation': elem.position.rotation
                    } if elem.position else None,
                    'style': elem.style,
                    'content': elem.content
                }
                for elem in self.elements
            ]
        }