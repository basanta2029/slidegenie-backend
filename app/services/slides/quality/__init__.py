"""
Quality Assurance System for SlideGenie presentations.

This package provides comprehensive quality checking for generated presentations,
ensuring they meet academic standards and provide excellent user experience.
"""

from .base import (
    BaseQualityAssurance,
    QualityChecker,
    QualityDimension,
    QualityIssue,
    QualityLevel,
    QualityMetrics,
    QualityReport
)
from .citations import CitationChecker
from .coherence import CoherenceChecker
from .metrics import QualityMetricsCalculator
from .readability import ReadabilityScorer
from .timing import TimingValidator
from .transitions import TransitionValidator
from .visual_balance import VisualBalanceAssessor

# Convenience function to create a fully configured QA system
def create_quality_assurance_system() -> BaseQualityAssurance:
    """
    Create a quality assurance system with all default checkers.
    
    Returns:
        Configured BaseQualityAssurance instance
    """
    qa_system = BaseQualityAssurance()
    
    # Register all quality checkers
    qa_system.register_checker(CoherenceChecker())
    qa_system.register_checker(TransitionValidator())
    qa_system.register_checker(CitationChecker())
    qa_system.register_checker(TimingValidator())
    qa_system.register_checker(VisualBalanceAssessor())
    qa_system.register_checker(ReadabilityScorer())
    
    return qa_system


# Export all public components
__all__ = [
    # Base classes
    'BaseQualityAssurance',
    'QualityChecker',
    'QualityDimension',
    'QualityIssue',
    'QualityLevel',
    'QualityMetrics',
    'QualityReport',
    
    # Quality checkers
    'CoherenceChecker',
    'TransitionValidator',
    'CitationChecker',
    'TimingValidator',
    'VisualBalanceAssessor',
    'ReadabilityScorer',
    
    # Metrics and utilities
    'QualityMetricsCalculator',
    
    # Factory function
    'create_quality_assurance_system'
]