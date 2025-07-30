"""
Document analyzers for advanced content analysis.

This module provides specialized analyzers for different types of content analysis,
including academic document structure detection, IMRAD classification, and content quality assessment.
"""

from .academic_analyzer import AcademicAnalyzer

__all__ = [
    "AcademicAnalyzer",
]