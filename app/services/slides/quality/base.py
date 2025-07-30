"""
Base Quality Assurance System for SlideGenie presentations.

This module provides the foundation for comprehensive quality checking
of generated presentations, ensuring they meet academic standards.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation


class QualityLevel(Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    SATISFACTORY = "satisfactory"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class QualityDimension(Enum):
    """Dimensions of quality assessment."""
    COHERENCE = "coherence"
    TRANSITIONS = "transitions"
    CITATIONS = "citations"
    TIMING = "timing"
    VISUAL_BALANCE = "visual_balance"
    READABILITY = "readability"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"


@dataclass
class QualityIssue:
    """Represents a quality issue found during assessment."""
    dimension: QualityDimension
    severity: str  # "critical", "major", "minor", "suggestion"
    slide_number: Optional[int] = None
    description: str = ""
    suggestion: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityMetrics:
    """Quality metrics for a presentation."""
    overall_score: float  # 0.0 to 1.0
    dimension_scores: Dict[QualityDimension, float] = field(default_factory=dict)
    issues: List[QualityIssue] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def quality_level(self) -> QualityLevel:
        """Determine overall quality level based on score."""
        if self.overall_score >= 0.9:
            return QualityLevel.EXCELLENT
        elif self.overall_score >= 0.8:
            return QualityLevel.GOOD
        elif self.overall_score >= 0.6:
            return QualityLevel.SATISFACTORY
        elif self.overall_score >= 0.4:
            return QualityLevel.NEEDS_IMPROVEMENT
        else:
            return QualityLevel.POOR
    
    @property
    def critical_issues_count(self) -> int:
        """Count of critical issues."""
        return sum(1 for issue in self.issues if issue.severity == "critical")
    
    @property
    def major_issues_count(self) -> int:
        """Count of major issues."""
        return sum(1 for issue in self.issues if issue.severity == "major")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "overall_score": self.overall_score,
            "quality_level": self.quality_level.value,
            "dimension_scores": {
                dim.value: score for dim, score in self.dimension_scores.items()
            },
            "issues": [
                {
                    "dimension": issue.dimension.value,
                    "severity": issue.severity,
                    "slide_number": issue.slide_number,
                    "description": issue.description,
                    "suggestion": issue.suggestion,
                    "metadata": issue.metadata
                }
                for issue in self.issues
            ],
            "strengths": self.strengths,
            "improvement_areas": self.improvement_areas,
            "critical_issues_count": self.critical_issues_count,
            "major_issues_count": self.major_issues_count,
            "metadata": self.metadata
        }


@dataclass
class QualityReport:
    """Comprehensive quality assessment report."""
    presentation_id: UUID
    assessment_date: datetime
    metrics: QualityMetrics
    detailed_analysis: Dict[QualityDimension, Dict[str, Any]] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    estimated_revision_time: int = 0  # in minutes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "presentation_id": str(self.presentation_id),
            "assessment_date": self.assessment_date.isoformat(),
            "metrics": self.metrics.to_dict(),
            "detailed_analysis": {
                dim.value: analysis for dim, analysis in self.detailed_analysis.items()
            },
            "recommendations": self.recommendations,
            "estimated_revision_time": self.estimated_revision_time
        }


class QualityChecker(ABC):
    """Abstract base class for quality checkers."""
    
    @abstractmethod
    def check(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """
        Perform quality check on presentation.
        
        Args:
            presentation: The presentation metadata
            slides: List of slides in the presentation
            references: Optional list of citations
            
        Returns:
            Tuple of (score, issues, metadata)
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> QualityDimension:
        """The quality dimension this checker assesses."""
        pass
    
    @property
    def weight(self) -> float:
        """Weight of this dimension in overall quality score."""
        return 1.0


class BaseQualityAssurance:
    """
    Base quality assurance system that orchestrates multiple quality checkers.
    """
    
    def __init__(self, checkers: Optional[List[QualityChecker]] = None):
        """
        Initialize quality assurance system.
        
        Args:
            checkers: List of quality checkers to use
        """
        self.checkers: Dict[QualityDimension, QualityChecker] = {}
        if checkers:
            for checker in checkers:
                self.register_checker(checker)
    
    def register_checker(self, checker: QualityChecker) -> None:
        """Register a quality checker."""
        self.checkers[checker.dimension] = checker
    
    def assess_quality(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None,
        custom_rules: Optional[Dict[str, Any]] = None
    ) -> QualityReport:
        """
        Perform comprehensive quality assessment.
        
        Args:
            presentation: The presentation to assess
            slides: List of slides in the presentation
            references: Optional list of citations
            custom_rules: Optional custom quality rules
            
        Returns:
            QualityReport with detailed assessment
        """
        # Initialize metrics
        dimension_scores = {}
        all_issues = []
        detailed_analysis = {}
        
        # Run each quality checker
        for dimension, checker in self.checkers.items():
            score, issues, metadata = checker.check(presentation, slides, references)
            dimension_scores[dimension] = score
            all_issues.extend(issues)
            detailed_analysis[dimension] = metadata
        
        # Calculate weighted overall score
        overall_score = self._calculate_overall_score(dimension_scores)
        
        # Identify strengths and improvement areas
        strengths = self._identify_strengths(dimension_scores, detailed_analysis)
        improvement_areas = self._identify_improvement_areas(dimension_scores, all_issues)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_issues, dimension_scores)
        
        # Estimate revision time
        revision_time = self._estimate_revision_time(all_issues)
        
        # Create metrics
        metrics = QualityMetrics(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=all_issues,
            strengths=strengths,
            improvement_areas=improvement_areas,
            metadata={
                "slide_count": len(slides),
                "reference_count": len(references) if references else 0,
                "custom_rules_applied": bool(custom_rules)
            }
        )
        
        # Create and return report
        return QualityReport(
            presentation_id=presentation.id,
            assessment_date=datetime.utcnow(),
            metrics=metrics,
            detailed_analysis=detailed_analysis,
            recommendations=recommendations,
            estimated_revision_time=revision_time
        )
    
    def _calculate_overall_score(self, dimension_scores: Dict[QualityDimension, float]) -> float:
        """Calculate weighted overall quality score."""
        if not dimension_scores:
            return 0.0
        
        total_weight = sum(self.checkers[dim].weight for dim in dimension_scores)
        weighted_sum = sum(
            score * self.checkers[dim].weight 
            for dim, score in dimension_scores.items()
        )
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _identify_strengths(
        self,
        dimension_scores: Dict[QualityDimension, float],
        detailed_analysis: Dict[QualityDimension, Dict[str, Any]]
    ) -> List[str]:
        """Identify presentation strengths."""
        strengths = []
        
        # High-scoring dimensions
        for dimension, score in dimension_scores.items():
            if score >= 0.8:
                if dimension == QualityDimension.COHERENCE:
                    strengths.append("Strong logical flow and content coherence")
                elif dimension == QualityDimension.CITATIONS:
                    strengths.append("Comprehensive and properly formatted citations")
                elif dimension == QualityDimension.VISUAL_BALANCE:
                    strengths.append("Well-balanced visual design and layout")
                elif dimension == QualityDimension.READABILITY:
                    strengths.append("Excellent readability and clarity")
        
        # Add specific strengths from detailed analysis
        for dimension, analysis in detailed_analysis.items():
            if "strengths" in analysis:
                strengths.extend(analysis["strengths"])
        
        return list(set(strengths))  # Remove duplicates
    
    def _identify_improvement_areas(
        self,
        dimension_scores: Dict[QualityDimension, float],
        issues: List[QualityIssue]
    ) -> List[str]:
        """Identify areas needing improvement."""
        areas = []
        
        # Low-scoring dimensions
        for dimension, score in dimension_scores.items():
            if score < 0.6:
                if dimension == QualityDimension.COHERENCE:
                    areas.append("Improve logical flow between slides")
                elif dimension == QualityDimension.TRANSITIONS:
                    areas.append("Enhance slide transitions")
                elif dimension == QualityDimension.TIMING:
                    areas.append("Adjust content density for better timing")
        
        # Critical and major issues
        critical_dimensions = set()
        for issue in issues:
            if issue.severity in ["critical", "major"]:
                critical_dimensions.add(issue.dimension)
        
        for dimension in critical_dimensions:
            if dimension == QualityDimension.CITATIONS:
                areas.append("Fix citation completeness and accuracy")
            elif dimension == QualityDimension.VISUAL_BALANCE:
                areas.append("Rebalance visual elements across slides")
        
        return list(set(areas))  # Remove duplicates
    
    def _generate_recommendations(
        self,
        issues: List[QualityIssue],
        dimension_scores: Dict[QualityDimension, float]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Priority recommendations based on critical issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            recommendations.append(
                f"Address {len(critical_issues)} critical issues immediately"
            )
            
            # Group critical issues by type
            issue_types = {}
            for issue in critical_issues:
                if issue.dimension not in issue_types:
                    issue_types[issue.dimension] = []
                issue_types[issue.dimension].append(issue)
            
            for dimension, dim_issues in issue_types.items():
                if dimension == QualityDimension.CITATIONS:
                    recommendations.append(
                        f"Add missing citations for {len(dim_issues)} claims"
                    )
                elif dimension == QualityDimension.COHERENCE:
                    recommendations.append(
                        "Restructure content flow to improve logical progression"
                    )
        
        # General recommendations based on scores
        low_scores = {
            dim: score for dim, score in dimension_scores.items()
            if score < 0.7
        }
        
        for dimension, score in sorted(low_scores.items(), key=lambda x: x[1]):
            if dimension == QualityDimension.TIMING:
                recommendations.append(
                    "Review slide content density and adjust for target duration"
                )
            elif dimension == QualityDimension.READABILITY:
                recommendations.append(
                    "Simplify complex text and improve visual hierarchy"
                )
        
        # Limit to top 5 recommendations
        return recommendations[:5]
    
    def _estimate_revision_time(self, issues: List[QualityIssue]) -> int:
        """Estimate time needed to address issues (in minutes)."""
        time_estimate = 0
        
        for issue in issues:
            if issue.severity == "critical":
                time_estimate += 10
            elif issue.severity == "major":
                time_estimate += 5
            elif issue.severity == "minor":
                time_estimate += 2
            else:  # suggestion
                time_estimate += 1
        
        # Add base time for review
        time_estimate += 10
        
        return min(time_estimate, 120)  # Cap at 2 hours