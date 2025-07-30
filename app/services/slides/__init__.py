"""Slide generation service package.

This package provides the main interface for generating presentations
with various formats, layouts, and quality controls.
"""

from .service import SlideGenerationService
from .config import SlideGenerationConfig
from .extensions import ExtensionRegistry

__all__ = [
    "SlideGenerationService",
    "SlideGenerationConfig",
    "ExtensionRegistry",
]