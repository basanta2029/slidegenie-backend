"""
Visual element rules for slide content validation.
"""
from typing import Any, Dict, List, Set

from app.services.slides.rules.base import (
    Rule,
    RuleCategory,
    RuleContext,
    RuleSeverity,
    RuleViolation,
    get_rule_engine
)


class VisualElementCountRule(Rule):
    """Limits the number of visual elements per slide."""
    
    def __init__(self, max_visuals: int = 2):
        super().__init__(
            rule_id="visual.element_count",
            name="Visual Element Limit",
            description=f"Slides should have no more than {max_visuals} visual elements",
            category=RuleCategory.VISUAL,
            severity=RuleSeverity.WARNING,
            config={"max_visuals": max_visuals}
        )
        self.max_visuals = max_visuals
        self.visual_types = {"image", "chart", "table", "diagram", "video", "equation", "code"}
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            visual_count = 0
            visual_elements = []
            
            for idx, element in enumerate(slide_content.get("body", [])):
                if element.get("type") in self.visual_types:
                    visual_count += 1
                    visual_elements.append({
                        "type": element.get("type"),
                        "index": idx
                    })
            
            if visual_count > self.max_visuals:
                violations.append(self.create_violation(
                    message=f"Slide has {visual_count} visual elements, exceeding limit of {self.max_visuals}",
                    suggestion="Reduce visual elements or split across multiple slides",
                    context={
                        "visual_count": visual_count,
                        "visual_elements": visual_elements
                    },
                    location={"slide_number": content.get("slide_number")}
                ))
        
        return violations


class ImageQualityRule(Rule):
    """Ensures images meet quality requirements."""
    
    def __init__(self, min_resolution: int = 300, require_attribution: bool = True):
        super().__init__(
            rule_id="visual.image_quality",
            name="Image Quality Requirements",
            description="Ensures images meet resolution and attribution standards",
            category=RuleCategory.VISUAL,
            severity=RuleSeverity.WARNING,
            config={
                "min_resolution": min_resolution,
                "require_attribution": require_attribution
            }
        )
        self.min_resolution = min_resolution
        self.require_attribution = require_attribution
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            
            for idx, element in enumerate(slide_content.get("body", [])):
                if element.get("type") == "image":
                    # Check resolution if provided
                    resolution = element.get("resolution")
                    if resolution and resolution < self.min_resolution:
                        violations.append(self.create_violation(
                            message=f"Image resolution ({resolution} dpi) below minimum ({self.min_resolution} dpi)",
                            suggestion="Use higher resolution images for better print/projection quality",
                            context={"resolution": resolution},
                            location={
                                "slide_number": content.get("slide_number"),
                                "element_index": idx
                            }
                        ))
                    
                    # Check attribution for academic presentations
                    if self.require_attribution and context.presentation_type in ["conference", "defense", "research"]:
                        attribution = element.get("attribution", "").strip()
                        if not attribution:
                            violations.append(self.create_violation(
                                message="Image missing attribution/source",
                                suggestion="Add image source or attribution",
                                location={
                                    "slide_number": content.get("slide_number"),
                                    "element_index": idx
                                }
                            ))
                    
                    # Check alt text for accessibility
                    alt_text = element.get("alt_text", "").strip()
                    if not alt_text:
                        violations.append(self.create_violation(
                            message="Image missing alt text for accessibility",
                            suggestion="Add descriptive alt text for the image",
                            location={
                                "slide_number": content.get("slide_number"),
                                "element_index": idx
                            },
                            severity=RuleSeverity.INFO
                        ))
        
        return violations


class ChartComplexityRule(Rule):
    """Ensures charts and graphs are not too complex."""
    
    def __init__(self, max_data_series: int = 5, max_data_points: int = 10):
        super().__init__(
            rule_id="visual.chart_complexity",
            name="Chart Complexity Limit",
            description="Ensures charts are not too complex for presentation",
            category=RuleCategory.VISUAL,
            severity=RuleSeverity.WARNING,
            config={
                "max_data_series": max_data_series,
                "max_data_points": max_data_points
            }
        )
        self.max_data_series = max_data_series
        self.max_data_points = max_data_points
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            
            for idx, element in enumerate(slide_content.get("body", [])):
                if element.get("type") == "chart":
                    chart_data = element.get("data", {})
                    
                    # Check number of data series
                    series_count = len(chart_data.get("series", []))
                    if series_count > self.max_data_series:
                        violations.append(self.create_violation(
                            message=f"Chart has {series_count} data series, exceeding limit of {self.max_data_series}",
                            suggestion="Simplify chart or focus on key data series",
                            context={"series_count": series_count},
                            location={
                                "slide_number": content.get("slide_number"),
                                "element_index": idx
                            }
                        ))
                    
                    # Check data points per series
                    for series_idx, series in enumerate(chart_data.get("series", [])):
                        point_count = len(series.get("data", []))
                        if point_count > self.max_data_points:
                            violations.append(self.create_violation(
                                message=f"Chart series has {point_count} data points, exceeding limit of {self.max_data_points}",
                                suggestion="Reduce data points or use summary statistics",
                                context={
                                    "series_index": series_idx,
                                    "point_count": point_count
                                },
                                location={
                                    "slide_number": content.get("slide_number"),
                                    "element_index": idx
                                }
                            ))
                    
                    # Check for proper labels
                    if not chart_data.get("x_label") or not chart_data.get("y_label"):
                        violations.append(self.create_violation(
                            message="Chart missing axis labels",
                            suggestion="Add descriptive labels to both axes",
                            location={
                                "slide_number": content.get("slide_number"),
                                "element_index": idx
                            },
                            severity=RuleSeverity.WARNING
                        ))
        
        return violations


class TableSizeRule(Rule):
    """Ensures tables are readable and not too large."""
    
    def __init__(self, max_rows: int = 6, max_columns: int = 5):
        super().__init__(
            rule_id="visual.table_size",
            name="Table Size Limit",
            description="Ensures tables are readable on slides",
            category=RuleCategory.VISUAL,
            severity=RuleSeverity.WARNING,
            config={
                "max_rows": max_rows,
                "max_columns": max_columns
            }
        )
        self.max_rows = max_rows
        self.max_columns = max_columns
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            
            for idx, element in enumerate(slide_content.get("body", [])):
                if element.get("type") == "table":
                    headers = element.get("headers", [])
                    rows = element.get("rows", [])
                    
                    # Check column count
                    col_count = len(headers)
                    if col_count > self.max_columns:
                        violations.append(self.create_violation(
                            message=f"Table has {col_count} columns, exceeding limit of {self.max_columns}",
                            suggestion="Reduce columns or split into multiple tables",
                            context={"column_count": col_count},
                            location={
                                "slide_number": content.get("slide_number"),
                                "element_index": idx
                            }
                        ))
                    
                    # Check row count
                    row_count = len(rows)
                    if row_count > self.max_rows:
                        violations.append(self.create_violation(
                            message=f"Table has {row_count} rows, exceeding limit of {self.max_rows}",
                            suggestion="Show only key data or use a summary table",
                            context={"row_count": row_count},
                            location={
                                "slide_number": content.get("slide_number"),
                                "element_index": idx
                            }
                        ))
                    
                    # Check for caption
                    if not element.get("caption"):
                        violations.append(self.create_violation(
                            message="Table missing caption",
                            suggestion="Add a descriptive caption to the table",
                            location={
                                "slide_number": content.get("slide_number"),
                                "element_index": idx
                            },
                            severity=RuleSeverity.INFO
                        ))
        
        return violations


class ColorContrastRule(Rule):
    """Ensures sufficient color contrast for readability."""
    
    def __init__(self):
        super().__init__(
            rule_id="visual.color_contrast",
            name="Color Contrast Check",
            description="Ensures text has sufficient contrast against background",
            category=RuleCategory.VISUAL,
            severity=RuleSeverity.WARNING
        )
        
        # WCAG AA standard contrast ratios
        self.min_contrast_normal = 4.5
        self.min_contrast_large = 3.0
    
    def _calculate_luminance(self, rgb: List[int]) -> float:
        """Calculate relative luminance of a color."""
        def adjust(val):
            val = val / 255.0
            if val <= 0.03928:
                return val / 12.92
            return ((val + 0.055) / 1.055) ** 2.4
        
        r, g, b = [adjust(c) for c in rgb]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    def _calculate_contrast_ratio(self, color1: List[int], color2: List[int]) -> float:
        """Calculate contrast ratio between two colors."""
        lum1 = self._calculate_luminance(color1)
        lum2 = self._calculate_luminance(color2)
        
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            
            # Check if color information is provided
            theme = slide_content.get("theme", {})
            if theme.get("text_color") and theme.get("background_color"):
                text_rgb = theme.get("text_color")
                bg_rgb = theme.get("background_color")
                
                if isinstance(text_rgb, list) and isinstance(bg_rgb, list):
                    contrast_ratio = self._calculate_contrast_ratio(text_rgb, bg_rgb)
                    
                    if contrast_ratio < self.min_contrast_normal:
                        violations.append(self.create_violation(
                            message=f"Insufficient color contrast ({contrast_ratio:.2f}:1)",
                            suggestion=f"Increase contrast to at least {self.min_contrast_normal}:1",
                            context={
                                "contrast_ratio": contrast_ratio,
                                "text_color": text_rgb,
                                "background_color": bg_rgb
                            },
                            location={"slide_number": content.get("slide_number")}
                        ))
        
        return violations


class AnimationUseRule(Rule):
    """Ensures appropriate use of animations and transitions."""
    
    def __init__(self, max_animations_per_slide: int = 3):
        super().__init__(
            rule_id="visual.animation_use",
            name="Animation Usage Limit",
            description="Ensures animations don't distract from content",
            category=RuleCategory.VISUAL,
            severity=RuleSeverity.INFO,
            config={"max_animations_per_slide": max_animations_per_slide}
        )
        self.max_animations = max_animations_per_slide
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            animations = slide_content.get("animations", [])
            
            # Count animations
            animation_count = len(animations)
            if animation_count > self.max_animations:
                violations.append(self.create_violation(
                    message=f"Slide has {animation_count} animations, which may be distracting",
                    suggestion="Reduce animations to focus on content",
                    context={"animation_count": animation_count},
                    location={"slide_number": content.get("slide_number")}
                ))
            
            # Check for appropriate animation types in academic context
            if context.presentation_type in ["conference", "defense", "research"]:
                flashy_animations = ["bounce", "spin", "zoom", "fly", "swivel", "pulse"]
                used_flashy = [a for a in animations if any(f in a.get("type", "").lower() for f in flashy_animations)]
                
                if used_flashy:
                    violations.append(self.create_violation(
                        message="Flashy animations may be inappropriate for academic presentation",
                        suggestion="Use subtle transitions like fade or appear",
                        context={"flashy_animations": used_flashy},
                        location={"slide_number": content.get("slide_number")},
                        severity=RuleSeverity.INFO
                    ))
        
        return violations


class VisualBalanceRule(Rule):
    """Ensures visual elements are balanced with text content."""
    
    def __init__(self):
        super().__init__(
            rule_id="visual.balance",
            name="Visual-Text Balance",
            description="Ensures proper balance between visual and text content",
            category=RuleCategory.VISUAL,
            severity=RuleSeverity.INFO
        )
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            
            # Count text and visual elements
            text_elements = 0
            visual_elements = 0
            visual_types = {"image", "chart", "table", "diagram", "video"}
            
            for element in slide_content.get("body", []):
                if element.get("type") in ["text", "bullet_list"]:
                    text_elements += 1
                elif element.get("type") in visual_types:
                    visual_elements += 1
            
            total_elements = text_elements + visual_elements
            
            if total_elements > 0:
                visual_ratio = visual_elements / total_elements
                
                # Check for slides that are too text-heavy
                if visual_elements == 0 and text_elements > 2:
                    violations.append(self.create_violation(
                        message="Slide contains only text with no visual elements",
                        suggestion="Consider adding a diagram, chart, or image to enhance understanding",
                        context={"text_elements": text_elements},
                        location={"slide_number": content.get("slide_number")},
                        severity=RuleSeverity.INFO
                    ))
                
                # Check for slides that are too visual-heavy
                elif visual_ratio > 0.8 and visual_elements > 1:
                    violations.append(self.create_violation(
                        message="Slide is dominated by visual elements with minimal text",
                        suggestion="Add explanatory text to provide context",
                        context={
                            "visual_elements": visual_elements,
                            "text_elements": text_elements
                        },
                        location={"slide_number": content.get("slide_number")},
                        severity=RuleSeverity.INFO
                    ))
        
        return violations


def register_visual_rules(engine=None):
    """Register all visual rules with the rule engine."""
    if engine is None:
        engine = get_rule_engine()
    
    # Register rules with appropriate rule sets
    rules = [
        (VisualElementCountRule(), ["conference", "lecture", "defense", "seminar", "workshop"]),
        (ImageQualityRule(), ["conference", "defense", "research"]),
        (ChartComplexityRule(), ["conference", "lecture", "defense", "seminar"]),
        (TableSizeRule(), ["conference", "lecture", "defense", "seminar", "workshop"]),
        (ColorContrastRule(), ["conference", "lecture", "defense", "seminar", "workshop"]),
        (AnimationUseRule(), ["conference", "defense", "research"]),
        (VisualBalanceRule(), ["lecture", "workshop", "seminar"])
    ]
    
    for rule, rule_sets in rules:
        engine.register_rule(rule, rule_sets)