"""Configuration management for slide generation service."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class OutputFormat(str, Enum):
    """Supported presentation output formats."""
    PPTX = "pptx"
    PDF = "pdf"
    GOOGLE_SLIDES = "google_slides"
    REVEAL_JS = "reveal_js"
    MARKDOWN = "markdown"


class LayoutStyle(str, Enum):
    """Available layout styles."""
    MINIMAL = "minimal"
    MODERN = "modern"
    ACADEMIC = "academic"
    BUSINESS = "business"
    CREATIVE = "creative"


class QualityLevel(str, Enum):
    """Quality control levels."""
    DRAFT = "draft"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class GeneratorConfig:
    """Configuration for slide generators."""
    format: OutputFormat = OutputFormat.PPTX
    enable_smart_content: bool = True
    enable_visual_suggestions: bool = True
    max_slides: int = 50
    min_slides: int = 5
    slide_transition_duration: float = 1.0
    enable_animations: bool = True
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayoutConfig:
    """Configuration for layout system."""
    style: LayoutStyle = LayoutStyle.MODERN
    enable_responsive_design: bool = True
    enable_accessibility: bool = True
    color_scheme: Optional[Dict[str, str]] = None
    font_family: Optional[str] = None
    font_size_base: int = 14
    spacing_unit: int = 8
    enable_grid_system: bool = True
    custom_css: Optional[str] = None


@dataclass
class RulesConfig:
    """Configuration for rules engine."""
    enable_content_rules: bool = True
    enable_design_rules: bool = True
    enable_accessibility_rules: bool = True
    enable_citation_rules: bool = True
    max_text_per_slide: int = 150
    min_text_per_slide: int = 20
    max_bullet_points: int = 6
    enable_custom_rules: bool = True
    custom_rules_path: Optional[str] = None


@dataclass
class QualityConfig:
    """Configuration for quality assurance."""
    quality_level: QualityLevel = QualityLevel.STANDARD
    enable_spell_check: bool = True
    enable_grammar_check: bool = True
    enable_readability_check: bool = True
    enable_consistency_check: bool = True
    enable_accessibility_check: bool = True
    readability_target: str = "college"
    enable_image_quality_check: bool = True
    min_image_resolution: int = 300


@dataclass
class OrchestratorConfig:
    """Configuration for orchestration system."""
    enable_parallel_processing: bool = True
    max_workers: int = 4
    enable_caching: bool = True
    cache_ttl: int = 3600
    enable_progress_tracking: bool = True
    enable_error_recovery: bool = True
    retry_attempts: int = 3
    timeout_seconds: int = 300


@dataclass
class PerformanceConfig:
    """Performance optimization settings."""
    enable_lazy_loading: bool = True
    enable_streaming: bool = True
    chunk_size: int = 1024 * 1024  # 1MB
    enable_compression: bool = True
    compression_level: int = 6
    enable_memory_optimization: bool = True
    max_memory_usage_mb: int = 512


@dataclass
class SlideGenerationConfig:
    """Main configuration for slide generation service."""
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    orchestrator: OrchestratorConfig = field(default_factory=OrchestratorConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Global settings
    enable_telemetry: bool = True
    enable_debugging: bool = False
    log_level: str = "INFO"
    temp_directory: str = "/tmp/slidegenie"
    
    # Extension settings
    enabled_extensions: List[str] = field(default_factory=list)
    extension_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlideGenerationConfig":
        """Create configuration from dictionary."""
        generator_data = data.get("generator", {})
        if "format" in generator_data and isinstance(generator_data["format"], str):
            generator_data["format"] = OutputFormat(generator_data["format"])
        
        layout_data = data.get("layout", {})
        if "style" in layout_data and isinstance(layout_data["style"], str):
            layout_data["style"] = LayoutStyle(layout_data["style"])
        
        quality_data = data.get("quality", {})
        if "quality_level" in quality_data and isinstance(quality_data["quality_level"], str):
            quality_data["quality_level"] = QualityLevel(quality_data["quality_level"])
        
        return cls(
            generator=GeneratorConfig(**generator_data),
            layout=LayoutConfig(**layout_data),
            rules=RulesConfig(**data.get("rules", {})),
            quality=QualityConfig(**quality_data),
            orchestrator=OrchestratorConfig(**data.get("orchestrator", {})),
            performance=PerformanceConfig(**data.get("performance", {})),
            enable_telemetry=data.get("enable_telemetry", True),
            enable_debugging=data.get("enable_debugging", False),
            log_level=data.get("log_level", "INFO"),
            temp_directory=data.get("temp_directory", "/tmp/slidegenie"),
            enabled_extensions=data.get("enabled_extensions", []),
            extension_config=data.get("extension_config", {})
        )
    
    @classmethod
    def from_file(cls, path: str) -> "SlideGenerationConfig":
        """Load configuration from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "generator": {
                "format": self.generator.format.value,
                "enable_smart_content": self.generator.enable_smart_content,
                "enable_visual_suggestions": self.generator.enable_visual_suggestions,
                "max_slides": self.generator.max_slides,
                "min_slides": self.generator.min_slides,
                "slide_transition_duration": self.generator.slide_transition_duration,
                "enable_animations": self.generator.enable_animations,
                "custom_settings": self.generator.custom_settings
            },
            "layout": {
                "style": self.layout.style.value,
                "enable_responsive_design": self.layout.enable_responsive_design,
                "enable_accessibility": self.layout.enable_accessibility,
                "color_scheme": self.layout.color_scheme,
                "font_family": self.layout.font_family,
                "font_size_base": self.layout.font_size_base,
                "spacing_unit": self.layout.spacing_unit,
                "enable_grid_system": self.layout.enable_grid_system,
                "custom_css": self.layout.custom_css
            },
            "rules": {
                "enable_content_rules": self.rules.enable_content_rules,
                "enable_design_rules": self.rules.enable_design_rules,
                "enable_accessibility_rules": self.rules.enable_accessibility_rules,
                "enable_citation_rules": self.rules.enable_citation_rules,
                "max_text_per_slide": self.rules.max_text_per_slide,
                "min_text_per_slide": self.rules.min_text_per_slide,
                "max_bullet_points": self.rules.max_bullet_points,
                "enable_custom_rules": self.rules.enable_custom_rules,
                "custom_rules_path": self.rules.custom_rules_path
            },
            "quality": {
                "quality_level": self.quality.quality_level.value,
                "enable_spell_check": self.quality.enable_spell_check,
                "enable_grammar_check": self.quality.enable_grammar_check,
                "enable_readability_check": self.quality.enable_readability_check,
                "enable_consistency_check": self.quality.enable_consistency_check,
                "enable_accessibility_check": self.quality.enable_accessibility_check,
                "readability_target": self.quality.readability_target,
                "enable_image_quality_check": self.quality.enable_image_quality_check,
                "min_image_resolution": self.quality.min_image_resolution
            },
            "orchestrator": {
                "enable_parallel_processing": self.orchestrator.enable_parallel_processing,
                "max_workers": self.orchestrator.max_workers,
                "enable_caching": self.orchestrator.enable_caching,
                "cache_ttl": self.orchestrator.cache_ttl,
                "enable_progress_tracking": self.orchestrator.enable_progress_tracking,
                "enable_error_recovery": self.orchestrator.enable_error_recovery,
                "retry_attempts": self.orchestrator.retry_attempts,
                "timeout_seconds": self.orchestrator.timeout_seconds
            },
            "performance": {
                "enable_lazy_loading": self.performance.enable_lazy_loading,
                "enable_streaming": self.performance.enable_streaming,
                "chunk_size": self.performance.chunk_size,
                "enable_compression": self.performance.enable_compression,
                "compression_level": self.performance.compression_level,
                "enable_memory_optimization": self.performance.enable_memory_optimization,
                "max_memory_usage_mb": self.performance.max_memory_usage_mb
            },
            "enable_telemetry": self.enable_telemetry,
            "enable_debugging": self.enable_debugging,
            "log_level": self.log_level,
            "temp_directory": self.temp_directory,
            "enabled_extensions": self.enabled_extensions,
            "extension_config": self.extension_config
        }
    
    def save(self, path: str) -> None:
        """Save configuration to JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def merge_with(self, overrides: Dict[str, Any]) -> "SlideGenerationConfig":
        """Create new configuration with overrides applied."""
        base_dict = self.to_dict()
        
        # Deep merge the dictionaries
        def deep_merge(base: Dict, override: Dict) -> Dict:
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        
        merged = deep_merge(base_dict, overrides)
        return SlideGenerationConfig.from_dict(merged)


# Preset configurations
PRESETS = {
    "quick_draft": SlideGenerationConfig(
        generator=GeneratorConfig(
            enable_smart_content=False,
            enable_visual_suggestions=False,
            enable_animations=False
        ),
        quality=QualityConfig(
            quality_level=QualityLevel.DRAFT,
            enable_spell_check=False,
            enable_grammar_check=False
        ),
        orchestrator=OrchestratorConfig(
            enable_parallel_processing=False,
            enable_caching=False
        )
    ),
    "academic_presentation": SlideGenerationConfig(
        generator=GeneratorConfig(
            format=OutputFormat.PDF,
            enable_animations=False
        ),
        layout=LayoutConfig(
            style=LayoutStyle.ACADEMIC,
            enable_accessibility=True
        ),
        rules=RulesConfig(
            enable_citation_rules=True,
            max_text_per_slide=200
        ),
        quality=QualityConfig(
            quality_level=QualityLevel.PREMIUM,
            readability_target="graduate"
        )
    ),
    "business_pitch": SlideGenerationConfig(
        generator=GeneratorConfig(
            format=OutputFormat.PPTX,
            enable_animations=True,
            max_slides=20
        ),
        layout=LayoutConfig(
            style=LayoutStyle.BUSINESS,
            enable_responsive_design=True
        ),
        rules=RulesConfig(
            max_text_per_slide=100,
            max_bullet_points=4
        ),
        quality=QualityConfig(
            quality_level=QualityLevel.PREMIUM
        )
    )
}


def get_preset(name: str) -> SlideGenerationConfig:
    """Get a preset configuration by name."""
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")
    return PRESETS[name]