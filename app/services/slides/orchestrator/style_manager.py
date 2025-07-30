"""Style manager for consistent styling across slides."""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import logging
from copy import deepcopy
import re

logger = logging.getLogger(__name__)


@dataclass
class StyleRule:
    """Defines a style rule."""
    property: str
    value: Any
    scope: str  # global, slide_type, specific
    priority: int = 0
    cascade: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StyleTheme:
    """Represents a complete style theme."""
    id: str
    name: str
    colors: Dict[str, str] = field(default_factory=dict)
    fonts: Dict[str, str] = field(default_factory=dict)
    spacing: Dict[str, float] = field(default_factory=dict)
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    animations: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class StyleManager:
    """Manages style application and consistency."""
    
    def __init__(self):
        """Initialize the style manager."""
        self.themes: Dict[str, StyleTheme] = {}
        self.global_styles: Dict[str, Any] = {}
        self.slide_type_styles: Dict[str, Dict[str, Any]] = {}
        self.custom_rules: List[StyleRule] = []
        self._style_cache: Dict[str, Dict[str, Any]] = {}
        self._init_default_themes()
        
    def _init_default_themes(self):
        """Initialize default themes."""
        # Professional theme
        professional = StyleTheme(
            id="professional",
            name="Professional",
            colors={
                "primary": "#1e3a8a",
                "secondary": "#3b82f6",
                "accent": "#60a5fa",
                "background": "#ffffff",
                "text": "#1f2937",
                "muted": "#6b7280"
            },
            fonts={
                "heading": "Inter, sans-serif",
                "body": "Inter, sans-serif",
                "code": "Fira Code, monospace"
            },
            spacing={
                "xs": 0.25,
                "sm": 0.5,
                "md": 1.0,
                "lg": 1.5,
                "xl": 2.0
            },
            components={
                "title_slide": {
                    "title": {
                        "fontSize": "48px",
                        "fontWeight": "bold",
                        "color": "$primary",
                        "marginBottom": "$spacing.lg"
                    },
                    "subtitle": {
                        "fontSize": "24px",
                        "color": "$text",
                        "marginBottom": "$spacing.md"
                    }
                },
                "content_slide": {
                    "heading": {
                        "fontSize": "36px",
                        "fontWeight": "600",
                        "color": "$primary",
                        "marginBottom": "$spacing.md"
                    },
                    "body": {
                        "fontSize": "18px",
                        "lineHeight": "1.6",
                        "color": "$text"
                    },
                    "bullet": {
                        "fontSize": "18px",
                        "lineHeight": "1.8",
                        "color": "$text",
                        "marginLeft": "$spacing.lg"
                    }
                }
            }
        )
        
        # Modern theme
        modern = StyleTheme(
            id="modern",
            name="Modern",
            colors={
                "primary": "#8b5cf6",
                "secondary": "#a78bfa",
                "accent": "#c4b5fd",
                "background": "#fafafa",
                "text": "#111827",
                "muted": "#9ca3af"
            },
            fonts={
                "heading": "Poppins, sans-serif",
                "body": "Open Sans, sans-serif",
                "code": "JetBrains Mono, monospace"
            },
            spacing={
                "xs": 0.375,
                "sm": 0.75,
                "md": 1.25,
                "lg": 2.0,
                "xl": 3.0
            },
            components={
                "title_slide": {
                    "title": {
                        "fontSize": "56px",
                        "fontWeight": "700",
                        "color": "$primary",
                        "marginBottom": "$spacing.xl"
                    },
                    "subtitle": {
                        "fontSize": "28px",
                        "fontWeight": "300",
                        "color": "$text",
                        "marginBottom": "$spacing.lg"
                    }
                },
                "content_slide": {
                    "heading": {
                        "fontSize": "40px",
                        "fontWeight": "600",
                        "color": "$primary",
                        "marginBottom": "$spacing.lg"
                    },
                    "body": {
                        "fontSize": "20px",
                        "lineHeight": "1.7",
                        "color": "$text"
                    }
                }
            },
            animations={
                "fadeIn": {
                    "duration": "0.5s",
                    "easing": "ease-out"
                },
                "slideUp": {
                    "duration": "0.6s",
                    "easing": "cubic-bezier(0.4, 0, 0.2, 1)"
                }
            }
        )
        
        self.themes["professional"] = professional
        self.themes["modern"] = modern
        
    def add_theme(self, theme: StyleTheme) -> None:
        """Add a custom theme."""
        self.themes[theme.id] = theme
        logger.info(f"Added theme: {theme.name}")
        
    def set_global_styles(self, styles: Dict[str, Any]) -> None:
        """Set global styles that apply to all slides."""
        self.global_styles = deepcopy(styles)
        self._invalidate_cache()
        
    def set_slide_type_styles(self, slide_type: str, styles: Dict[str, Any]) -> None:
        """Set styles for a specific slide type."""
        self.slide_type_styles[slide_type] = deepcopy(styles)
        self._invalidate_cache()
        
    def add_style_rule(self, rule: StyleRule) -> None:
        """Add a custom style rule."""
        self.custom_rules.append(rule)
        self._invalidate_cache()
        
    async def apply_theme(
        self, 
        slide: Dict[str, Any], 
        theme_id: str,
        override_styles: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Apply a theme to a slide."""
        theme = self.themes.get(theme_id)
        if not theme:
            logger.warning(f"Theme {theme_id} not found")
            return slide
            
        # Start with theme base styles
        styled_slide = deepcopy(slide)
        slide_type = slide.get("type", "content")
        
        # Apply theme component styles
        component_styles = theme.components.get(f"{slide_type}_slide", {})
        
        # Process slide content with theme styles
        styled_slide["style"] = self._merge_styles(
            theme_styles=self._resolve_theme_variables(component_styles, theme),
            global_styles=self.global_styles,
            type_styles=self.slide_type_styles.get(slide_type, {}),
            slide_styles=slide.get("style", {}),
            override_styles=override_styles or {}
        )
        
        # Apply theme to content elements
        styled_slide["content"] = await self._style_content_elements(
            slide.get("content", {}),
            theme,
            component_styles
        )
        
        # Add animation styles if defined
        if theme.animations:
            styled_slide["animations"] = self._prepare_animations(theme.animations, slide_type)
            
        return styled_slide
        
    async def finalize_slide_style(
        self,
        slide: Dict[str, Any],
        global_style: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Finalize slide styling with all applied rules."""
        slide_type = slide.get("type", "content")
        cache_key = f"{slide.get('slide_index')}_{slide_type}_{hash(str(theme))}"
        
        # Check cache
        if cache_key in self._style_cache:
            cached_style = self._style_cache[cache_key]
            slide["style"] = deepcopy(cached_style)
            return slide
            
        # Apply cascading styles
        final_style = self._cascade_styles(
            base=theme,
            global_style=global_style,
            type_style=self.slide_type_styles.get(slide_type, {}),
            slide_style=slide.get("style", {})
        )
        
        # Apply custom rules
        for rule in self.custom_rules:
            if self._should_apply_rule(rule, slide):
                final_style = self._apply_style_rule(final_style, rule)
                
        # Process responsive styles
        final_style = self._process_responsive_styles(final_style)
        
        # Optimize and clean styles
        final_style = self._optimize_styles(final_style)
        
        slide["style"] = final_style
        self._style_cache[cache_key] = deepcopy(final_style)
        
        return slide
        
    def _merge_styles(self, **style_sources) -> Dict[str, Any]:
        """Merge multiple style sources with proper precedence."""
        merged = {}
        
        # Order matters: later sources override earlier ones
        for source in ["theme_styles", "global_styles", "type_styles", "slide_styles", "override_styles"]:
            if source in style_sources and style_sources[source]:
                merged = self._deep_merge(merged, style_sources[source])
                
        return merged
        
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = deepcopy(base)
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
                
        return result
        
    def _resolve_theme_variables(self, styles: Dict[str, Any], theme: StyleTheme) -> Dict[str, Any]:
        """Resolve theme variables in styles."""
        resolved = {}
        
        for key, value in styles.items():
            if isinstance(value, str):
                # Replace color variables
                for color_name, color_value in theme.colors.items():
                    value = value.replace(f"$primary", theme.colors.get("primary", ""))
                    value = value.replace(f"$secondary", theme.colors.get("secondary", ""))
                    value = value.replace(f"${color_name}", color_value)
                    
                # Replace spacing variables
                for spacing_name, spacing_value in theme.spacing.items():
                    value = value.replace(f"$spacing.{spacing_name}", f"{spacing_value}rem")
                    
                resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self._resolve_theme_variables(value, theme)
            else:
                resolved[key] = value
                
        return resolved
        
    async def _style_content_elements(
        self,
        content: Dict[str, Any],
        theme: StyleTheme,
        component_styles: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply styling to content elements."""
        styled_content = deepcopy(content)
        
        # Style title
        if "title" in styled_content and "title" in component_styles:
            styled_content["title_style"] = self._resolve_theme_variables(
                component_styles["title"], 
                theme
            )
            
        # Style headings
        if "headings" in styled_content:
            heading_style = component_styles.get("heading", {})
            for i, heading in enumerate(styled_content["headings"]):
                if isinstance(heading, dict):
                    heading["style"] = self._resolve_theme_variables(heading_style, theme)
                    
        # Style bullets
        if "bullets" in styled_content:
            bullet_style = component_styles.get("bullet", {})
            for bullet in styled_content["bullets"]:
                if isinstance(bullet, dict):
                    bullet["style"] = self._resolve_theme_variables(bullet_style, theme)
                    
        # Style body text
        if "body" in styled_content:
            body_style = component_styles.get("body", {})
            styled_content["body_style"] = self._resolve_theme_variables(body_style, theme)
            
        return styled_content
        
    def _cascade_styles(
        self,
        base: Dict[str, Any],
        global_style: Dict[str, Any],
        type_style: Dict[str, Any],
        slide_style: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply cascading style rules."""
        # Start with base
        cascaded = deepcopy(base)
        
        # Apply in order of increasing specificity
        for styles in [global_style, type_style, slide_style]:
            if styles:
                cascaded = self._deep_merge(cascaded, styles)
                
        return cascaded
        
    def _should_apply_rule(self, rule: StyleRule, slide: Dict[str, Any]) -> bool:
        """Check if a rule should be applied to a slide."""
        # Check scope
        if rule.scope == "global":
            return True
        elif rule.scope == "slide_type":
            return slide.get("type") in rule.conditions.get("types", [])
        elif rule.scope == "specific":
            # Check specific conditions
            for condition, value in rule.conditions.items():
                if slide.get(condition) != value:
                    return False
            return True
            
        return False
        
    def _apply_style_rule(self, styles: Dict[str, Any], rule: StyleRule) -> Dict[str, Any]:
        """Apply a style rule to existing styles."""
        result = deepcopy(styles)
        
        # Navigate to the property path
        path_parts = rule.property.split(".")
        current = result
        
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
            
        # Apply the rule value
        current[path_parts[-1]] = rule.value
        
        return result
        
    def _prepare_animations(self, animations: Dict[str, Any], slide_type: str) -> Dict[str, Any]:
        """Prepare animation definitions for a slide."""
        slide_animations = {}
        
        # Default animations by slide type
        default_animations = {
            "title": ["fadeIn"],
            "content": ["fadeIn", "slideUp"],
            "section": ["fadeIn"],
            "conclusion": ["fadeIn"]
        }
        
        animation_names = default_animations.get(slide_type, ["fadeIn"])
        
        for name in animation_names:
            if name in animations:
                slide_animations[name] = animations[name]
                
        return slide_animations
        
    def _process_responsive_styles(self, styles: Dict[str, Any]) -> Dict[str, Any]:
        """Process responsive style definitions."""
        processed = deepcopy(styles)
        
        # Define breakpoints
        breakpoints = {
            "sm": "640px",
            "md": "768px",
            "lg": "1024px",
            "xl": "1280px"
        }
        
        # Process responsive properties
        if "responsive" in processed:
            responsive_styles = processed.pop("responsive")
            processed["@media"] = {}
            
            for breakpoint, bp_styles in responsive_styles.items():
                if breakpoint in breakpoints:
                    media_query = f"(min-width: {breakpoints[breakpoint]})"
                    processed["@media"][media_query] = bp_styles
                    
        return processed
        
    def _optimize_styles(self, styles: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize and clean style definitions."""
        optimized = {}
        
        for key, value in styles.items():
            # Remove empty values
            if value is None or value == "":
                continue
                
            # Optimize nested objects
            if isinstance(value, dict):
                nested_optimized = self._optimize_styles(value)
                if nested_optimized:  # Only include non-empty objects
                    optimized[key] = nested_optimized
            else:
                optimized[key] = value
                
        # Combine similar properties
        optimized = self._combine_similar_properties(optimized)
        
        return optimized
        
    def _combine_similar_properties(self, styles: Dict[str, Any]) -> Dict[str, Any]:
        """Combine similar CSS properties for efficiency."""
        combined = deepcopy(styles)
        
        # Combine margin/padding properties
        for prop in ["margin", "padding"]:
            sides = ["Top", "Right", "Bottom", "Left"]
            values = []
            
            for side in sides:
                key = f"{prop}{side}"
                if key in combined:
                    values.append(combined.pop(key))
                else:
                    values.append(None)
                    
            # If all sides are defined and can be combined
            if all(v is not None for v in values):
                if len(set(values)) == 1:
                    combined[prop] = values[0]
                elif values[0] == values[2] and values[1] == values[3]:
                    combined[prop] = f"{values[0]} {values[1]}"
                else:
                    combined[prop] = " ".join(str(v) for v in values)
                    
        return combined
        
    def _invalidate_cache(self):
        """Invalidate the style cache."""
        self._style_cache.clear()
        
    def get_theme_preview(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Get a preview of a theme."""
        theme = self.themes.get(theme_id)
        if not theme:
            return None
            
        return {
            "id": theme.id,
            "name": theme.name,
            "colors": theme.colors,
            "fonts": theme.fonts,
            "preview_styles": {
                "title": theme.components.get("title_slide", {}).get("title", {}),
                "heading": theme.components.get("content_slide", {}).get("heading", {}),
                "body": theme.components.get("content_slide", {}).get("body", {})
            }
        }