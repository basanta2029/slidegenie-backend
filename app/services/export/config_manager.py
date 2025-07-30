"""
Configuration management system for export preferences and settings.

This module provides:
- User-specific export preferences
- Template configuration management
- Format-specific settings
- Default configurations and validation
- Configuration inheritance and overrides
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from app.core.logging import get_logger
from app.services.export.export_coordinator import ExportFormat, ExportQuality, ExportPriority

logger = get_logger(__name__)


class ConfigScope(Enum):
    """Configuration scope levels."""
    SYSTEM = "system"      # System-wide defaults
    ORGANIZATION = "org"   # Organization-wide settings
    USER = "user"         # User-specific preferences
    PROJECT = "project"   # Project-specific overrides
    JOB = "job"          # Job-specific overrides


@dataclass
class BrandingConfig:
    """Branding configuration."""
    logo_url: Optional[str] = None
    logo_position: str = "top_right"  # top_left, top_right, bottom_left, bottom_right
    show_logo: bool = True
    university_name: Optional[str] = None
    department: Optional[str] = None
    custom_footer: Optional[str] = None
    show_slide_numbers: bool = True
    show_date: bool = False
    color_scheme: Dict[str, str] = field(default_factory=lambda: {
        "primary": "#003f7f",
        "secondary": "#0066cc", 
        "accent": "#ff6600",
        "background": "#ffffff",
        "text": "#000000"
    })


@dataclass
class TypographyConfig:
    """Typography configuration."""
    title_font: str = "Arial"
    body_font: str = "Arial"
    code_font: str = "Courier New"
    title_size: int = 44
    heading_size: int = 32
    body_size: int = 24
    caption_size: int = 16
    line_height: float = 1.2
    font_weights: Dict[str, str] = field(default_factory=lambda: {
        "title": "bold",
        "heading": "bold",
        "body": "normal",
        "emphasis": "italic"
    })


@dataclass
class LayoutConfig:
    """Layout configuration."""
    slide_size: str = "16:9"  # 16:9, 4:3, 16:10
    margins: Dict[str, float] = field(default_factory=lambda: {
        "top": 0.5,
        "bottom": 0.5,
        "left": 0.5,
        "right": 0.5
    })
    content_spacing: float = 0.25
    max_bullet_depth: int = 3
    image_max_width: float = 0.8
    image_max_height: float = 0.6
    table_style: str = "professional"  # minimal, professional, academic
    chart_style: str = "clean"  # minimal, clean, colorful


@dataclass
class QualityConfig:
    """Quality and output configuration."""
    image_dpi: int = 300
    image_quality: int = 95  # JPEG quality 1-100
    compression_level: str = "moderate"  # none, low, moderate, high
    include_metadata: bool = True
    include_notes: bool = False
    include_hidden_slides: bool = False
    optimize_for_web: bool = False
    embed_fonts: bool = True


@dataclass
class FormatSpecificConfig:
    """Format-specific configuration."""
    pptx: Dict[str, Any] = field(default_factory=lambda: {
        "animation_enabled": True,
        "transition_type": "fade",
        "slide_master": "default",
        "handout_master": "default"
    })
    beamer: Dict[str, Any] = field(default_factory=lambda: {
        "theme": "Berlin",
        "color_theme": "default",
        "font_theme": "default",
        "navigation_symbols": False,
        "frame_numbering": True,
        "bibliography_style": "ieee"
    })
    pdf: Dict[str, Any] = field(default_factory=lambda: {
        "page_layout": "slides",  # slides, handout, notes
        "bookmarks": True,
        "hyperlinks": True,
        "form_fields": False,
        "security": {
            "allow_printing": True,
            "allow_copying": True,
            "allow_modifications": False
        }
    })
    google_slides: Dict[str, Any] = field(default_factory=lambda: {
        "sharing_permissions": "view",  # view, comment, edit
        "folder_id": None,
        "auto_save": True,
        "version_history": True
    })


@dataclass
class ExportPreferences:
    """Complete export preferences configuration."""
    user_id: Optional[str] = None
    scope: ConfigScope = ConfigScope.USER
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Main configuration sections
    branding: BrandingConfig = field(default_factory=BrandingConfig)
    typography: TypographyConfig = field(default_factory=TypographyConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    format_specific: FormatSpecificConfig = field(default_factory=FormatSpecificConfig)
    
    # Default settings per format
    default_templates: Dict[str, str] = field(default_factory=lambda: {
        "pptx": "ieee",
        "beamer": "berlin",
        "pdf": "standard",
        "google_slides": "academic"
    })
    default_quality: ExportQuality = ExportQuality.STANDARD
    default_priority: ExportPriority = ExportPriority.NORMAL
    
    # Advanced options
    custom_css: Optional[str] = None
    custom_templates: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    post_processing: Dict[str, Any] = field(default_factory=dict)


class ConfigurationValidator:
    """Validates export configuration."""
    
    @staticmethod
    def validate_preferences(preferences: ExportPreferences) -> Dict[str, Any]:
        """
        Validate export preferences.
        
        Returns:
            Validation result with errors and warnings
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate branding
        branding_validation = ConfigurationValidator._validate_branding(preferences.branding)
        result["errors"].extend(branding_validation.get("errors", []))
        result["warnings"].extend(branding_validation.get("warnings", []))
        
        # Validate typography
        typography_validation = ConfigurationValidator._validate_typography(preferences.typography)
        result["errors"].extend(typography_validation.get("errors", []))
        result["warnings"].extend(typography_validation.get("warnings", []))
        
        # Validate layout
        layout_validation = ConfigurationValidator._validate_layout(preferences.layout)
        result["errors"].extend(layout_validation.get("errors", []))
        result["warnings"].extend(layout_validation.get("warnings", []))
        
        # Validate quality
        quality_validation = ConfigurationValidator._validate_quality(preferences.quality)
        result["errors"].extend(quality_validation.get("errors", []))
        result["warnings"].extend(quality_validation.get("warnings", []))
        
        result["valid"] = len(result["errors"]) == 0
        return result
    
    @staticmethod
    def _validate_branding(branding: BrandingConfig) -> Dict[str, List[str]]:
        """Validate branding configuration."""
        result = {"errors": [], "warnings": []}
        
        # Logo position validation
        valid_positions = ["top_left", "top_right", "bottom_left", "bottom_right"]
        if branding.logo_position not in valid_positions:
            result["errors"].append(f"Invalid logo position: {branding.logo_position}")
        
        # Color validation
        for color_name, color_value in branding.color_scheme.items():
            if not color_value.startswith("#") or len(color_value) not in [4, 7]:
                result["errors"].append(f"Invalid color format for {color_name}: {color_value}")
        
        # Logo URL validation
        if branding.logo_url and not (branding.logo_url.startswith("http") or Path(branding.logo_url).exists()):
            result["warnings"].append(f"Logo URL may not be accessible: {branding.logo_url}")
        
        return result
    
    @staticmethod
    def _validate_typography(typography: TypographyConfig) -> Dict[str, List[str]]:
        """Validate typography configuration."""
        result = {"errors": [], "warnings": []}
        
        # Font size validation
        if typography.title_size < 20 or typography.title_size > 72:
            result["warnings"].append(f"Title size {typography.title_size} may not be optimal")
        
        if typography.body_size < 12 or typography.body_size > 36:
            result["warnings"].append(f"Body size {typography.body_size} may not be optimal")
        
        # Line height validation
        if typography.line_height < 0.8 or typography.line_height > 2.0:
            result["warnings"].append(f"Line height {typography.line_height} may cause readability issues")
        
        return result
    
    @staticmethod
    def _validate_layout(layout: LayoutConfig) -> Dict[str, List[str]]:
        """Validate layout configuration."""
        result = {"errors": [], "warnings": []}
        
        # Slide size validation
        valid_sizes = ["16:9", "4:3", "16:10"]
        if layout.slide_size not in valid_sizes:
            result["errors"].append(f"Invalid slide size: {layout.slide_size}")
        
        # Margin validation
        for margin_name, margin_value in layout.margins.items():
            if margin_value < 0 or margin_value > 2:
                result["warnings"].append(f"Margin {margin_name} = {margin_value} may be too large/small")
        
        # Image size validation
        if layout.image_max_width > 1.0 or layout.image_max_height > 1.0:
            result["errors"].append("Image max dimensions cannot exceed 1.0 (100%)")
        
        return result
    
    @staticmethod
    def _validate_quality(quality: QualityConfig) -> Dict[str, List[str]]:
        """Validate quality configuration."""
        result = {"errors": [], "warnings": []}
        
        # DPI validation
        if quality.image_dpi < 72:
            result["warnings"].append(f"Low DPI {quality.image_dpi} may result in poor image quality")
        elif quality.image_dpi > 600:
            result["warnings"].append(f"High DPI {quality.image_dpi} may result in large file sizes")
        
        # JPEG quality validation
        if quality.image_quality < 1 or quality.image_quality > 100:
            result["errors"].append(f"Invalid image quality: {quality.image_quality}")
        
        # Compression level validation
        valid_levels = ["none", "low", "moderate", "high"]
        if quality.compression_level not in valid_levels:
            result["errors"].append(f"Invalid compression level: {quality.compression_level}")
        
        return result


class ConfigManager:
    """
    Manages export configurations and preferences.
    
    Provides hierarchical configuration management with inheritance,
    validation, and persistence.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.config_dir = config_dir or Path("config/export")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.validator = ConfigurationValidator()
        
        # In-memory cache
        self._config_cache: Dict[str, ExportPreferences] = {}
        self._system_defaults: Optional[ExportPreferences] = None
        
        # Load system defaults
        self._load_system_defaults()
    
    def _load_system_defaults(self):
        """Load system default configuration."""
        defaults_file = self.config_dir / "system_defaults.json"
        
        if defaults_file.exists():
            try:
                with open(defaults_file, 'r') as f:
                    data = json.load(f)
                    self._system_defaults = self._dict_to_preferences(data)
            except Exception as e:
                self.logger.error(f"Failed to load system defaults: {e}")
        
        if not self._system_defaults:
            self._system_defaults = ExportPreferences(scope=ConfigScope.SYSTEM)
            self._save_system_defaults()
    
    def _save_system_defaults(self):
        """Save system default configuration."""
        defaults_file = self.config_dir / "system_defaults.json"
        
        try:
            with open(defaults_file, 'w') as f:
                data = self._preferences_to_dict(self._system_defaults)
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save system defaults: {e}")
    
    def get_user_preferences(self, user_id: str) -> ExportPreferences:
        """
        Get user-specific export preferences.
        
        Returns merged preferences with inheritance from system defaults.
        """
        cache_key = f"user_{user_id}"
        
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # Try to load from file
        user_file = self.config_dir / f"user_{user_id}.json"
        user_prefs = None
        
        if user_file.exists():
            try:
                with open(user_file, 'r') as f:
                    data = json.load(f)
                    user_prefs = self._dict_to_preferences(data)
                    user_prefs.user_id = user_id
            except Exception as e:
                self.logger.error(f"Failed to load user preferences: {e}")
        
        if not user_prefs:
            # Create new user preferences based on system defaults
            user_prefs = self._create_user_preferences(user_id)
        
        # Merge with system defaults
        merged_prefs = self._merge_preferences(self._system_defaults, user_prefs)
        merged_prefs.user_id = user_id
        merged_prefs.scope = ConfigScope.USER
        
        # Cache the result
        self._config_cache[cache_key] = merged_prefs
        
        return merged_prefs
    
    def save_user_preferences(self, user_id: str, preferences: ExportPreferences) -> bool:
        """Save user-specific export preferences."""
        try:
            # Validate preferences
            validation_result = self.validator.validate_preferences(preferences)
            if not validation_result["valid"]:
                self.logger.error(f"Invalid preferences: {validation_result['errors']}")
                return False
            
            # Update timestamps
            preferences.user_id = user_id
            preferences.updated_at = datetime.now()
            preferences.scope = ConfigScope.USER
            
            # Save to file
            user_file = self.config_dir / f"user_{user_id}.json"
            with open(user_file, 'w') as f:
                data = self._preferences_to_dict(preferences)
                json.dump(data, f, indent=2, default=str)
            
            # Update cache
            cache_key = f"user_{user_id}"
            self._config_cache[cache_key] = preferences
            
            self.logger.info(f"Saved preferences for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save user preferences: {e}")
            return False
    
    def get_format_config(
        self, 
        user_id: str, 
        format: ExportFormat,
        template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get format-specific configuration for a user.
        
        Returns merged configuration with template overrides.
        """
        user_prefs = self.get_user_preferences(user_id)
        
        # Base format configuration
        format_key = format.name.lower()
        base_config = getattr(user_prefs.format_specific, format_key, {})
        
        # Merge with template-specific settings
        if template_name and template_name in user_prefs.custom_templates:
            template_config = user_prefs.custom_templates[template_name]
            base_config = {**base_config, **template_config}
        
        # Add common settings
        config = {
            **base_config,
            "branding": asdict(user_prefs.branding),
            "typography": asdict(user_prefs.typography),
            "layout": asdict(user_prefs.layout),
            "quality": asdict(user_prefs.quality)
        }
        
        return config
    
    def create_job_config(
        self,
        user_id: str,
        format: ExportFormat,
        template_name: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create job-specific configuration.
        
        Merges user preferences with job-specific overrides.
        """
        # Get base format config
        config = self.get_format_config(user_id, format, template_name)
        
        # Apply overrides
        if overrides:
            config = self._deep_merge(config, overrides)
        
        return config
    
    def get_template_list(self, format: ExportFormat) -> List[Dict[str, Any]]:
        """Get available templates for a format."""
        # This would typically query a template database
        # For now, return predefined templates
        
        templates = {
            ExportFormat.PPTX: [
                {
                    "name": "ieee",
                    "display_name": "IEEE Academic",
                    "description": "IEEE conference presentation template",
                    "category": "academic",
                    "preview_url": "/static/previews/pptx_ieee.png"
                },
                {
                    "name": "acm",
                    "display_name": "ACM Conference",
                    "description": "ACM conference presentation template",
                    "category": "academic",
                    "preview_url": "/static/previews/pptx_acm.png"
                },
                {
                    "name": "nature",
                    "display_name": "Nature Journal",
                    "description": "Nature journal presentation template",
                    "category": "academic",
                    "preview_url": "/static/previews/pptx_nature.png"
                }
            ],
            ExportFormat.BEAMER: [
                {
                    "name": "berlin",
                    "display_name": "Berlin Theme",
                    "description": "Clean Berlin Beamer theme",
                    "category": "academic",
                    "preview_url": "/static/previews/beamer_berlin.png"
                },
                {
                    "name": "madrid",
                    "display_name": "Madrid Theme",
                    "description": "Professional Madrid Beamer theme",
                    "category": "academic",
                    "preview_url": "/static/previews/beamer_madrid.png"
                }
            ],
            ExportFormat.PDF: [
                {
                    "name": "standard",
                    "display_name": "Standard PDF",
                    "description": "Standard PDF presentation format",
                    "category": "general",
                    "preview_url": "/static/previews/pdf_standard.png"
                },
                {
                    "name": "handout",
                    "display_name": "Handout Format",
                    "description": "Multi-slide per page handout format",
                    "category": "handout",
                    "preview_url": "/static/previews/pdf_handout.png"
                }
            ],
            ExportFormat.GOOGLE_SLIDES: [
                {
                    "name": "academic",
                    "display_name": "Academic Theme",
                    "description": "Clean academic Google Slides theme",
                    "category": "academic",
                    "preview_url": "/static/previews/gslides_academic.png"
                },
                {
                    "name": "corporate",
                    "display_name": "Corporate Theme",
                    "description": "Professional corporate theme",
                    "category": "business",
                    "preview_url": "/static/previews/gslides_corporate.png"
                }
            ]
        }
        
        return templates.get(format, [])
    
    def save_custom_template(
        self,
        user_id: str,
        template_name: str,
        template_config: Dict[str, Any],
        format: ExportFormat
    ) -> bool:
        """Save a custom template for a user."""
        try:
            user_prefs = self.get_user_preferences(user_id)
            
            # Add format prefix to template name
            full_template_name = f"{format.name.lower()}_{template_name}"
            user_prefs.custom_templates[full_template_name] = template_config
            
            # Save updated preferences
            return self.save_user_preferences(user_id, user_prefs)
            
        except Exception as e:
            self.logger.error(f"Failed to save custom template: {e}")
            return False
    
    def delete_custom_template(self, user_id: str, template_name: str) -> bool:
        """Delete a custom template for a user."""
        try:
            user_prefs = self.get_user_preferences(user_id)
            
            if template_name in user_prefs.custom_templates:
                del user_prefs.custom_templates[template_name]
                return self.save_user_preferences(user_id, user_prefs)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete custom template: {e}")
            return False
    
    def _create_user_preferences(self, user_id: str) -> ExportPreferences:
        """Create new user preferences with defaults."""
        prefs = ExportPreferences(
            user_id=user_id,
            scope=ConfigScope.USER
        )
        return prefs
    
    def _merge_preferences(
        self, 
        base: ExportPreferences, 
        override: ExportPreferences
    ) -> ExportPreferences:
        """Merge two preference objects with override taking precedence."""
        # Convert to dictionaries for easier merging
        base_dict = self._preferences_to_dict(base)
        override_dict = self._preferences_to_dict(override)
        
        # Deep merge
        merged_dict = self._deep_merge(base_dict, override_dict)
        
        # Convert back to preferences object
        return self._dict_to_preferences(merged_dict)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _preferences_to_dict(self, preferences: ExportPreferences) -> Dict[str, Any]:
        """Convert preferences object to dictionary."""
        return asdict(preferences)
    
    def _dict_to_preferences(self, data: Dict[str, Any]) -> ExportPreferences:
        """Convert dictionary to preferences object."""
        # Handle nested objects
        if "branding" in data and isinstance(data["branding"], dict):
            data["branding"] = BrandingConfig(**data["branding"])
        
        if "typography" in data and isinstance(data["typography"], dict):
            data["typography"] = TypographyConfig(**data["typography"])
        
        if "layout" in data and isinstance(data["layout"], dict):
            data["layout"] = LayoutConfig(**data["layout"])
        
        if "quality" in data and isinstance(data["quality"], dict):
            data["quality"] = QualityConfig(**data["quality"])
        
        if "format_specific" in data and isinstance(data["format_specific"], dict):
            data["format_specific"] = FormatSpecificConfig(**data["format_specific"])
        
        # Handle enums
        if "default_quality" in data and isinstance(data["default_quality"], str):
            data["default_quality"] = ExportQuality(data["default_quality"])
        
        if "default_priority" in data and isinstance(data["default_priority"], str):
            data["default_priority"] = ExportPriority[data["default_priority"].upper()]
        
        if "scope" in data and isinstance(data["scope"], str):
            data["scope"] = ConfigScope(data["scope"])
        
        # Handle datetime strings
        for field in ["created_at", "updated_at"]:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        
        return ExportPreferences(**data)
    
    def cleanup_cache(self):
        """Clear configuration cache."""
        self._config_cache.clear()
        self.logger.info("Configuration cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_configs": len(self._config_cache),
            "cache_keys": list(self._config_cache.keys()),
            "system_defaults_loaded": self._system_defaults is not None
        }


# Factory function
def create_config_manager(config_dir: Optional[Path] = None) -> ConfigManager:
    """Create a configuration manager instance."""
    return ConfigManager(config_dir)