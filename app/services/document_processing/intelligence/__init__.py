"""
Document Intelligence Layer.

This module provides advanced document analysis capabilities including:
- Language detection with confidence scoring
- Content quality assessment with academic standards  
- Missing section identification and recommendations
- Academic writing style analysis
- Content coherence and flow analysis
- Citation quality assessment
- Document readiness scoring
"""

from .analyzer import IntelligenceEngine, DocumentIntelligenceResult

__all__ = [
    "IntelligenceEngine",
    "DocumentIntelligenceResult",
]