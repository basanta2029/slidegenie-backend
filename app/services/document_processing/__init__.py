"""
Document processing services for SlideGenie.

This module provides comprehensive document processing capabilities,
including PDF text extraction, figure/table detection, citation parsing,
and academic document structure analysis.
"""

from .processors.pdf_processor import PDFProcessor
from .utils.text_analysis import TextAnalyzer
from .utils.layout_detector import LayoutDetector

__all__ = [
    "PDFProcessor",
    "TextAnalyzer", 
    "LayoutDetector",
]