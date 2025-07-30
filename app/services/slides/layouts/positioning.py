"""
Element Positioning System

Provides intelligent positioning algorithms for slide elements
with support for various strategies and constraints.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import math

from .base import ElementPosition, LayoutElement, ElementType
from .grid import GridSystem, GridCell, GridAlignment


class PositioningStrategy(Enum):
    """Available positioning strategies"""
    GRID_BASED = "grid_based"
    FLOW_VERTICAL = "flow_vertical"
    FLOW_HORIZONTAL = "flow_horizontal"
    CENTERED = "centered"
    DISTRIBUTED = "distributed"
    HIERARCHICAL = "hierarchical"
    RADIAL = "radial"
    MASONRY = "masonry"


@dataclass
class PositioningConstraint:
    """Constraints for element positioning"""
    min_width: Optional[float] = None
    max_width: Optional[float] = None
    min_height: Optional[float] = None
    max_height: Optional[float] = None
    aspect_ratio: Optional[float] = None
    anchor_to: Optional[str] = None  # Element ID to anchor to
    anchor_position: Optional[str] = None  # e.g., "below", "right", "center"
    maintain_distance: Optional[float] = None
    avoid_overlap: bool = True
    lock_position: bool = False


class PositioningAlgorithm(ABC):
    """Abstract base class for positioning algorithms"""
    
    @abstractmethod
    def position_elements(self, elements: List[LayoutElement], 
                         available_area: ElementPosition) -> List[LayoutElement]:
        """Position elements within the available area"""
        pass


class GridBasedPositioning(PositioningAlgorithm):
    """Position elements using a grid system"""
    
    def __init__(self, grid_system: GridSystem):
        self.grid = grid_system
    
    def position_elements(self, elements: List[LayoutElement], 
                         available_area: ElementPosition) -> List[LayoutElement]:
        """Position elements using grid cells"""
        positioned_elements = []
        
        # Define default grid positions for element types
        type_positions = {
            ElementType.TITLE: GridCell(0, 0, 1, 12, GridAlignment.CENTER),
            ElementType.SUBTITLE: GridCell(1, 0, 1, 12, GridAlignment.CENTER),
            ElementType.TEXT: GridCell(2, 0, 4, 12),
            ElementType.BULLET_LIST: GridCell(2, 0, 4, 6),
            ElementType.IMAGE: GridCell(2, 6, 4, 6),
            ElementType.FOOTER: GridCell(7, 0, 1, 12, GridAlignment.CENTER)
        }
        
        for element in elements:
            if element.type in type_positions:
                cell = type_positions[element.type]
                position = self.grid.get_cell_position(cell)
                element.position = position
            positioned_elements.append(element)
        
        return positioned_elements


class FlowPositioning(PositioningAlgorithm):
    """Position elements in a flow layout"""
    
    def __init__(self, direction: str = "vertical", spacing: float = 0.02):
        self.direction = direction
        self.spacing = spacing
    
    def position_elements(self, elements: List[LayoutElement], 
                         available_area: ElementPosition) -> List[LayoutElement]:
        """Position elements in a flow"""
        positioned_elements = []
        
        if self.direction == "vertical":
            current_y = available_area.y
            
            for element in elements:
                # Calculate element height based on content
                height = self._calculate_element_height(element)
                
                element.position = ElementPosition(
                    x=available_area.x,
                    y=current_y,
                    width=available_area.width,
                    height=height
                )
                
                current_y += height + self.spacing
                positioned_elements.append(element)
        
        else:  # horizontal
            current_x = available_area.x
            
            for element in elements:
                # Calculate element width based on content
                width = self._calculate_element_width(element)
                
                element.position = ElementPosition(
                    x=current_x,
                    y=available_area.y,
                    width=width,
                    height=available_area.height
                )
                
                current_x += width + self.spacing
                positioned_elements.append(element)
        
        return positioned_elements
    
    def _calculate_element_height(self, element: LayoutElement) -> float:
        """Calculate appropriate height for element"""
        # Default heights by type
        default_heights = {
            ElementType.TITLE: 0.15,
            ElementType.SUBTITLE: 0.10,
            ElementType.TEXT: 0.20,
            ElementType.BULLET_LIST: 0.30,
            ElementType.IMAGE: 0.40,
            ElementType.QUOTE: 0.25
        }
        return default_heights.get(element.type, 0.20)
    
    def _calculate_element_width(self, element: LayoutElement) -> float:
        """Calculate appropriate width for element"""
        # Default widths by type
        default_widths = {
            ElementType.IMAGE: 0.40,
            ElementType.CHART: 0.45,
            ElementType.TEXT: 0.30,
            ElementType.BULLET_LIST: 0.35
        }
        return default_widths.get(element.type, 0.30)


class CenteredPositioning(PositioningAlgorithm):
    """Center elements within available area"""
    
    def position_elements(self, elements: List[LayoutElement], 
                         available_area: ElementPosition) -> List[LayoutElement]:
        """Center all elements"""
        positioned_elements = []
        
        # Calculate total height needed
        total_height = sum(self._get_element_height(e) for e in elements)
        total_height += (len(elements) - 1) * 0.02  # spacing
        
        # Start position for vertical centering
        start_y = available_area.y + (available_area.height - total_height) / 2
        current_y = start_y
        
        for element in elements:
            height = self._get_element_height(element)
            width = self._get_element_width(element)
            
            # Center horizontally
            x = available_area.x + (available_area.width - width) / 2
            
            element.position = ElementPosition(
                x=x,
                y=current_y,
                width=width,
                height=height
            )
            
            current_y += height + 0.02
            positioned_elements.append(element)
        
        return positioned_elements
    
    def _get_element_height(self, element: LayoutElement) -> float:
        """Get element height"""
        return element.constraints.get('height', 0.15) if hasattr(element, 'constraints') else 0.15
    
    def _get_element_width(self, element: LayoutElement) -> float:
        """Get element width"""
        return element.constraints.get('width', 0.80) if hasattr(element, 'constraints') else 0.80


class PositioningEngine:
    """
    Main positioning engine that coordinates different positioning strategies
    """
    
    def __init__(self):
        self.strategies: Dict[PositioningStrategy, PositioningAlgorithm] = {}
        self._init_default_strategies()
    
    def _init_default_strategies(self):
        """Initialize default positioning strategies"""
        self.strategies[PositioningStrategy.GRID_BASED] = GridBasedPositioning(GridSystem())
        self.strategies[PositioningStrategy.FLOW_VERTICAL] = FlowPositioning("vertical")
        self.strategies[PositioningStrategy.FLOW_HORIZONTAL] = FlowPositioning("horizontal")
        self.strategies[PositioningStrategy.CENTERED] = CenteredPositioning()
    
    def register_strategy(self, strategy: PositioningStrategy, 
                         algorithm: PositioningAlgorithm):
        """Register a custom positioning strategy"""
        self.strategies[strategy] = algorithm
    
    def position_elements(self, elements: List[LayoutElement],
                         strategy: PositioningStrategy,
                         available_area: ElementPosition,
                         constraints: Optional[Dict[str, Any]] = None) -> List[LayoutElement]:
        """
        Position elements using specified strategy
        
        Args:
            elements: Elements to position
            strategy: Positioning strategy to use
            available_area: Available area for positioning
            constraints: Additional constraints
            
        Returns:
            List of positioned elements
        """
        if strategy not in self.strategies:
            raise ValueError(f"Unknown positioning strategy: {strategy}")
        
        algorithm = self.strategies[strategy]
        
        # Apply pre-positioning constraints
        elements = self._apply_constraints(elements, constraints)
        
        # Position elements
        positioned = algorithm.position_elements(elements, available_area)
        
        # Apply post-positioning adjustments
        positioned = self._adjust_positions(positioned, available_area)
        
        return positioned
    
    def _apply_constraints(self, elements: List[LayoutElement],
                          constraints: Optional[Dict[str, Any]]) -> List[LayoutElement]:
        """Apply positioning constraints to elements"""
        if not constraints:
            return elements
        
        # Apply global constraints
        for element in elements:
            if 'min_spacing' in constraints:
                element.constraints['min_spacing'] = constraints['min_spacing']
        
        return elements
    
    def _adjust_positions(self, elements: List[LayoutElement],
                         available_area: ElementPosition) -> List[LayoutElement]:
        """Adjust positions to ensure they fit within available area"""
        for element in elements:
            if not element.position:
                continue
            
            # Ensure element fits within bounds
            if element.position.x < available_area.x:
                element.position.x = available_area.x
            
            if element.position.y < available_area.y:
                element.position.y = available_area.y
            
            if element.position.x + element.position.width > available_area.x + available_area.width:
                element.position.width = (available_area.x + available_area.width) - element.position.x
            
            if element.position.y + element.position.height > available_area.y + available_area.height:
                element.position.height = (available_area.y + available_area.height) - element.position.y
        
        return elements
    
    def calculate_visual_balance(self, elements: List[LayoutElement]) -> float:
        """
        Calculate visual balance score for positioned elements
        
        Returns:
            Balance score (0-1, where 1 is perfectly balanced)
        """
        if not elements:
            return 1.0
        
        # Calculate center of mass
        total_area = 0
        weighted_x = 0
        weighted_y = 0
        
        for element in elements:
            if not element.position:
                continue
            
            area = element.position.width * element.position.height
            center_x = element.position.x + element.position.width / 2
            center_y = element.position.y + element.position.height / 2
            
            weighted_x += center_x * area
            weighted_y += center_y * area
            total_area += area
        
        if total_area == 0:
            return 0.0
        
        center_of_mass_x = weighted_x / total_area
        center_of_mass_y = weighted_y / total_area
        
        # Calculate distance from ideal center (0.5, 0.5)
        distance = math.sqrt((center_of_mass_x - 0.5) ** 2 + 
                           (center_of_mass_y - 0.5) ** 2)
        
        # Normalize to 0-1 scale (max distance is ~0.707)
        balance_score = 1.0 - (distance / 0.707)
        
        return max(0.0, min(1.0, balance_score))
    
    def optimize_positions(self, elements: List[LayoutElement],
                          iterations: int = 10) -> List[LayoutElement]:
        """
        Optimize element positions for better visual balance
        
        Args:
            elements: Elements to optimize
            iterations: Number of optimization iterations
            
        Returns:
            Optimized elements
        """
        best_score = self.calculate_visual_balance(elements)
        best_positions = [(e.position.x, e.position.y) if e.position else (0, 0) 
                         for e in elements]
        
        for _ in range(iterations):
            # Try small adjustments
            for i, element in enumerate(elements):
                if not element.position:
                    continue
                
                # Try different positions
                for dx in [-0.02, 0, 0.02]:
                    for dy in [-0.02, 0, 0.02]:
                        if dx == 0 and dy == 0:
                            continue
                        
                        # Temporarily adjust position
                        original_x = element.position.x
                        original_y = element.position.y
                        
                        element.position.x += dx
                        element.position.y += dy
                        
                        # Check if still valid
                        if (0 <= element.position.x <= 1 - element.position.width and
                            0 <= element.position.y <= 1 - element.position.height):
                            
                            score = self.calculate_visual_balance(elements)
                            
                            if score > best_score:
                                best_score = score
                                best_positions[i] = (element.position.x, element.position.y)
                        
                        # Restore position
                        element.position.x = original_x
                        element.position.y = original_y
        
        # Apply best positions
        for i, element in enumerate(elements):
            if element.position:
                element.position.x, element.position.y = best_positions[i]
        
        return elements