"""
Responsive Content Adaptation System

Handles dynamic content adaptation based on content volume,
complexity, and display constraints.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import math

from .base import ElementPosition, LayoutElement, ElementType, AspectRatio
from .positioning import PositioningEngine, PositioningStrategy


class ContentDensity(Enum):
    """Content density levels"""
    MINIMAL = "minimal"      # < 25% of slide
    LIGHT = "light"         # 25-50% of slide
    MODERATE = "moderate"   # 50-75% of slide
    DENSE = "dense"        # > 75% of slide
    OVERFLOW = "overflow"   # Exceeds slide capacity


class AdaptationStrategy(Enum):
    """Strategies for content adaptation"""
    SCALE_DOWN = "scale_down"           # Reduce element sizes
    REFLOW = "reflow"                   # Rearrange layout
    PAGINATE = "paginate"               # Split across slides
    SUMMARIZE = "summarize"             # Condense content
    PRIORITIZE = "prioritize"           # Show only key elements
    RESPONSIVE_COLUMNS = "responsive_columns"  # Adjust column count


@dataclass
class ContentMetrics:
    """Metrics for content analysis"""
    text_length: int = 0
    element_count: int = 0
    visual_elements: int = 0
    complexity_score: float = 0.0
    estimated_area: float = 0.0
    
    @property
    def density(self) -> ContentDensity:
        """Calculate content density"""
        if self.estimated_area < 0.25:
            return ContentDensity.MINIMAL
        elif self.estimated_area < 0.50:
            return ContentDensity.LIGHT
        elif self.estimated_area < 0.75:
            return ContentDensity.MODERATE
        elif self.estimated_area <= 1.0:
            return ContentDensity.DENSE
        else:
            return ContentDensity.OVERFLOW


class ResponsiveAdapter:
    """
    Handles responsive content adaptation for slides
    
    Features:
    - Content-aware scaling
    - Dynamic layout adjustment
    - Overflow handling
    - Multi-device optimization
    """
    
    def __init__(self):
        self.positioning_engine = PositioningEngine()
        self.adaptation_rules = self._init_adaptation_rules()
    
    def _init_adaptation_rules(self) -> Dict[ContentDensity, List[AdaptationStrategy]]:
        """Initialize adaptation rules by density"""
        return {
            ContentDensity.MINIMAL: [AdaptationStrategy.SCALE_DOWN],
            ContentDensity.LIGHT: [AdaptationStrategy.REFLOW],
            ContentDensity.MODERATE: [AdaptationStrategy.RESPONSIVE_COLUMNS],
            ContentDensity.DENSE: [AdaptationStrategy.SCALE_DOWN, AdaptationStrategy.REFLOW],
            ContentDensity.OVERFLOW: [AdaptationStrategy.PAGINATE, AdaptationStrategy.PRIORITIZE]
        }
    
    def analyze_content(self, elements: List[LayoutElement]) -> ContentMetrics:
        """
        Analyze content to determine metrics
        
        Args:
            elements: List of layout elements
            
        Returns:
            ContentMetrics object
        """
        metrics = ContentMetrics()
        
        for element in elements:
            metrics.element_count += 1
            
            # Count text length
            if element.type in [ElementType.TEXT, ElementType.TITLE, 
                               ElementType.SUBTITLE, ElementType.BULLET_LIST]:
                if isinstance(element.content, str):
                    metrics.text_length += len(element.content)
                elif isinstance(element.content, list):
                    metrics.text_length += sum(len(str(item)) for item in element.content)
            
            # Count visual elements
            if element.type in [ElementType.IMAGE, ElementType.CHART, 
                               ElementType.DIAGRAM]:
                metrics.visual_elements += 1
            
            # Estimate area needed
            metrics.estimated_area += self._estimate_element_area(element)
        
        # Calculate complexity score
        metrics.complexity_score = self._calculate_complexity(metrics)
        
        return metrics
    
    def _estimate_element_area(self, element: LayoutElement) -> float:
        """Estimate the area an element will need"""
        # Base areas by element type
        base_areas = {
            ElementType.TITLE: 0.15,
            ElementType.SUBTITLE: 0.10,
            ElementType.TEXT: 0.20,
            ElementType.BULLET_LIST: 0.25,
            ElementType.IMAGE: 0.35,
            ElementType.CHART: 0.40,
            ElementType.DIAGRAM: 0.40,
            ElementType.QUOTE: 0.20,
            ElementType.FOOTER: 0.05,
            ElementType.HEADER: 0.05
        }
        
        base_area = base_areas.get(element.type, 0.15)
        
        # Adjust for content length
        if hasattr(element, 'content') and isinstance(element.content, str):
            length_factor = min(2.0, len(element.content) / 100)
            base_area *= (1 + length_factor * 0.5)
        
        return base_area
    
    def _calculate_complexity(self, metrics: ContentMetrics) -> float:
        """Calculate content complexity score (0-1)"""
        # Factors: text density, element diversity, visual complexity
        text_factor = min(1.0, metrics.text_length / 500)
        element_factor = min(1.0, metrics.element_count / 10)
        visual_factor = min(1.0, metrics.visual_elements / 3)
        
        return (text_factor * 0.4 + element_factor * 0.3 + visual_factor * 0.3)
    
    def adapt_layout(self, 
                    elements: List[LayoutElement],
                    aspect_ratio: AspectRatio,
                    target_device: Optional[str] = None) -> List[List[LayoutElement]]:
        """
        Adapt layout based on content and constraints
        
        Args:
            elements: Elements to layout
            aspect_ratio: Target aspect ratio
            target_device: Optional device type (desktop, tablet, mobile)
            
        Returns:
            List of element groups (one per slide if paginated)
        """
        # Analyze content
        metrics = self.analyze_content(elements)
        
        # Determine adaptation strategies
        strategies = self.adaptation_rules.get(metrics.density, [])
        
        # Apply device-specific adjustments
        if target_device:
            strategies = self._adjust_for_device(strategies, target_device)
        
        # Apply adaptation strategies
        adapted_elements = elements
        slides = []
        
        for strategy in strategies:
            if strategy == AdaptationStrategy.SCALE_DOWN:
                adapted_elements = self._scale_down_elements(adapted_elements, metrics)
            
            elif strategy == AdaptationStrategy.REFLOW:
                adapted_elements = self._reflow_layout(adapted_elements, aspect_ratio)
            
            elif strategy == AdaptationStrategy.RESPONSIVE_COLUMNS:
                adapted_elements = self._adjust_columns(adapted_elements, metrics)
            
            elif strategy == AdaptationStrategy.PAGINATE:
                slides = self._paginate_content(adapted_elements, metrics)
                break  # Pagination is final
            
            elif strategy == AdaptationStrategy.PRIORITIZE:
                adapted_elements = self._prioritize_content(adapted_elements)
        
        # If not paginated, return single slide
        if not slides:
            slides = [adapted_elements]
        
        return slides
    
    def _scale_down_elements(self, elements: List[LayoutElement], 
                           metrics: ContentMetrics) -> List[LayoutElement]:
        """Scale down element sizes to fit"""
        scale_factor = min(1.0, 1.0 / metrics.estimated_area)
        
        for element in elements:
            if element.position:
                element.position.width *= scale_factor
                element.position.height *= scale_factor
            
            # Adjust font sizes in style
            if 'font_size' in element.style:
                # Implement font size scaling logic
                pass
        
        return elements
    
    def _reflow_layout(self, elements: List[LayoutElement], 
                      aspect_ratio: AspectRatio) -> List[LayoutElement]:
        """Reflow layout for better fit"""
        # Separate elements by type
        titles = []
        content = []
        visuals = []
        footer = []
        
        for elem in elements:
            if elem.type in [ElementType.TITLE, ElementType.SUBTITLE]:
                titles.append(elem)
            elif elem.type in [ElementType.IMAGE, ElementType.CHART, ElementType.DIAGRAM]:
                visuals.append(elem)
            elif elem.type in [ElementType.FOOTER, ElementType.PAGE_NUMBER]:
                footer.append(elem)
            else:
                content.append(elem)
        
        # Determine optimal layout based on aspect ratio
        if aspect_ratio == AspectRatio.RATIO_16_9:
            # Wide format - side-by-side layout preferred
            if visuals and content:
                # Position visuals on right, content on left
                available_area = ElementPosition(0.05, 0.15, 0.45, 0.70)
                positioned_content = self.positioning_engine.position_elements(
                    content, PositioningStrategy.FLOW_VERTICAL, available_area
                )
                
                available_area = ElementPosition(0.55, 0.15, 0.40, 0.70)
                positioned_visuals = self.positioning_engine.position_elements(
                    visuals, PositioningStrategy.CENTERED, available_area
                )
                
                elements = titles + positioned_content + positioned_visuals + footer
        
        return elements
    
    def _adjust_columns(self, elements: List[LayoutElement], 
                       metrics: ContentMetrics) -> List[LayoutElement]:
        """Adjust column count based on content"""
        # Determine optimal column count
        if metrics.density == ContentDensity.MINIMAL:
            columns = 1
        elif metrics.density == ContentDensity.LIGHT:
            columns = 1
        elif metrics.density == ContentDensity.MODERATE:
            columns = 2
        else:
            columns = 2 if metrics.visual_elements > 0 else 3
        
        # Reposition elements in columns
        # Implementation depends on specific column layout algorithm
        
        return elements
    
    def _paginate_content(self, elements: List[LayoutElement], 
                         metrics: ContentMetrics) -> List[List[LayoutElement]]:
        """Split content across multiple slides"""
        slides = []
        
        # Separate must-keep-together elements
        titles = [e for e in elements if e.type == ElementType.TITLE]
        
        # Calculate elements per slide
        elements_per_slide = 5  # Reasonable default
        
        # Keep related elements together
        current_slide = titles.copy()
        
        for element in elements:
            if element.type == ElementType.TITLE:
                continue
            
            current_slide.append(element)
            
            # Check if slide is full
            if len(current_slide) >= elements_per_slide:
                slides.append(current_slide)
                current_slide = []
        
        # Add remaining elements
        if current_slide:
            slides.append(current_slide)
        
        return slides
    
    def _prioritize_content(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Prioritize most important content"""
        # Priority order
        priority_order = [
            ElementType.TITLE,
            ElementType.SUBTITLE,
            ElementType.IMAGE,
            ElementType.CHART,
            ElementType.BULLET_LIST,
            ElementType.TEXT,
            ElementType.QUOTE,
            ElementType.FOOTER
        ]
        
        # Sort by priority
        prioritized = []
        for element_type in priority_order:
            prioritized.extend([e for e in elements if e.type == element_type])
        
        # Keep only top elements that fit
        max_elements = 6
        return prioritized[:max_elements]
    
    def _adjust_for_device(self, strategies: List[AdaptationStrategy], 
                          device: str) -> List[AdaptationStrategy]:
        """Adjust strategies based on target device"""
        device_adjustments = {
            'mobile': [AdaptationStrategy.SCALE_DOWN, AdaptationStrategy.PRIORITIZE],
            'tablet': [AdaptationStrategy.RESPONSIVE_COLUMNS],
            'desktop': []  # No special adjustments
        }
        
        additional = device_adjustments.get(device, [])
        return list(set(strategies + additional))
    
    def calculate_readability_score(self, elements: List[LayoutElement], 
                                  viewport_size: Tuple[int, int]) -> float:
        """
        Calculate readability score for adapted layout
        
        Args:
            elements: Positioned elements
            viewport_size: (width, height) in pixels
            
        Returns:
            Readability score (0-1)
        """
        score = 1.0
        
        for element in elements:
            if not element.position:
                continue
            
            # Check minimum sizes
            if element.type in [ElementType.TEXT, ElementType.BULLET_LIST]:
                # Calculate actual pixel size
                width_px = element.position.width * viewport_size[0]
                height_px = element.position.height * viewport_size[1]
                
                # Minimum readable text area
                if width_px < 200 or height_px < 50:
                    score *= 0.8
            
            # Check spacing
            # Implementation would check distances between elements
        
        return max(0.0, min(1.0, score))
    
    def suggest_improvements(self, elements: List[LayoutElement], 
                           metrics: ContentMetrics) -> List[str]:
        """
        Suggest improvements for better adaptation
        
        Args:
            elements: Current elements
            metrics: Content metrics
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        if metrics.density == ContentDensity.OVERFLOW:
            suggestions.append("Consider splitting content across multiple slides")
        
        if metrics.text_length > 300:
            suggestions.append("Reduce text content or use bullet points")
        
        if metrics.visual_elements > 3:
            suggestions.append("Limit visual elements to 2-3 per slide")
        
        if metrics.complexity_score > 0.8:
            suggestions.append("Simplify content for better clarity")
        
        return suggestions