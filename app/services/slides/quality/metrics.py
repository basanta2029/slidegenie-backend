"""
Quality Metrics Calculator for SlideGenie presentations.

This module calculates comprehensive quality metrics and tracks
quality trends over time.
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation
from .base import (
    BaseQualityAssurance,
    QualityDimension,
    QualityLevel,
    QualityMetrics,
    QualityReport
)


class QualityMetricsCalculator:
    """
    Calculates and tracks quality metrics for presentations.
    """
    
    def __init__(self, quality_assurance: BaseQualityAssurance):
        """
        Initialize metrics calculator.
        
        Args:
            quality_assurance: Quality assurance system to use
        """
        self.qa_system = quality_assurance
        self.metrics_history: Dict[UUID, List[QualityReport]] = {}
    
    def calculate_metrics(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None,
        custom_rules: Optional[Dict[str, Any]] = None
    ) -> QualityReport:
        """
        Calculate quality metrics for a presentation.
        
        Args:
            presentation: The presentation to analyze
            slides: List of slides
            references: Optional citations
            custom_rules: Optional custom quality rules
            
        Returns:
            QualityReport with metrics
        """
        # Run quality assessment
        report = self.qa_system.assess_quality(
            presentation, slides, references, custom_rules
        )
        
        # Store in history
        if presentation.id not in self.metrics_history:
            self.metrics_history[presentation.id] = []
        self.metrics_history[presentation.id].append(report)
        
        # Add trend analysis if history exists
        if len(self.metrics_history[presentation.id]) > 1:
            report.metrics.metadata['trend'] = self._calculate_trend(
                presentation.id
            )
        
        return report
    
    def get_aggregated_metrics(
        self,
        presentation_ids: Optional[List[UUID]] = None,
        time_period: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics across presentations.
        
        Args:
            presentation_ids: Specific presentations to include
            time_period: Time period to analyze
            
        Returns:
            Aggregated metrics dictionary
        """
        # Filter presentations
        if presentation_ids:
            reports = [
                report
                for pid in presentation_ids
                if pid in self.metrics_history
                for report in self.metrics_history[pid]
            ]
        else:
            reports = [
                report
                for reports_list in self.metrics_history.values()
                for report in reports_list
            ]
        
        # Filter by time period
        if time_period:
            cutoff_date = datetime.utcnow() - time_period
            reports = [
                r for r in reports
                if r.assessment_date >= cutoff_date
            ]
        
        if not reports:
            return {
                'total_assessments': 0,
                'avg_overall_score': 0,
                'dimension_averages': {},
                'quality_distribution': {},
                'common_issues': []
            }
        
        # Calculate aggregated metrics
        return {
            'total_assessments': len(reports),
            'avg_overall_score': self._calculate_average_score(reports),
            'dimension_averages': self._calculate_dimension_averages(reports),
            'quality_distribution': self._calculate_quality_distribution(reports),
            'common_issues': self._identify_common_issues(reports),
            'improvement_rate': self._calculate_improvement_rate(reports),
            'best_practices': self._identify_best_practices(reports)
        }
    
    def get_presentation_metrics_history(
        self,
        presentation_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get metrics history for a specific presentation.
        
        Args:
            presentation_id: The presentation ID
            
        Returns:
            List of historical metrics
        """
        if presentation_id not in self.metrics_history:
            return []
        
        return [
            {
                'date': report.assessment_date.isoformat(),
                'overall_score': report.metrics.overall_score,
                'quality_level': report.metrics.quality_level.value,
                'dimension_scores': {
                    dim.value: score
                    for dim, score in report.metrics.dimension_scores.items()
                },
                'issue_counts': {
                    'critical': report.metrics.critical_issues_count,
                    'major': report.metrics.major_issues_count,
                    'total': len(report.metrics.issues)
                }
            }
            for report in self.metrics_history[presentation_id]
        ]
    
    def compare_presentations(
        self,
        presentation_id1: UUID,
        presentation_id2: UUID
    ) -> Dict[str, Any]:
        """
        Compare quality metrics between two presentations.
        
        Args:
            presentation_id1: First presentation ID
            presentation_id2: Second presentation ID
            
        Returns:
            Comparison results
        """
        # Get latest reports for each
        report1 = self._get_latest_report(presentation_id1)
        report2 = self._get_latest_report(presentation_id2)
        
        if not report1 or not report2:
            return {'error': 'One or both presentations have no metrics'}
        
        # Compare metrics
        comparison = {
            'presentation1': {
                'id': str(presentation_id1),
                'overall_score': report1.metrics.overall_score,
                'quality_level': report1.metrics.quality_level.value
            },
            'presentation2': {
                'id': str(presentation_id2),
                'overall_score': report2.metrics.overall_score,
                'quality_level': report2.metrics.quality_level.value
            },
            'score_difference': report1.metrics.overall_score - report2.metrics.overall_score,
            'dimension_comparison': {}
        }
        
        # Compare dimensions
        for dimension in QualityDimension:
            score1 = report1.metrics.dimension_scores.get(dimension, 0)
            score2 = report2.metrics.dimension_scores.get(dimension, 0)
            comparison['dimension_comparison'][dimension.value] = {
                'score1': score1,
                'score2': score2,
                'difference': score1 - score2
            }
        
        # Identify relative strengths
        comparison['relative_strengths'] = {
            'presentation1': [
                dim.value for dim, scores in comparison['dimension_comparison'].items()
                if scores['difference'] > 0.1
            ],
            'presentation2': [
                dim.value for dim, scores in comparison['dimension_comparison'].items()
                if scores['difference'] < -0.1
            ]
        }
        
        return comparison
    
    def generate_quality_insights(
        self,
        presentation_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate actionable insights from quality metrics.
        
        Args:
            presentation_id: The presentation ID
            
        Returns:
            Quality insights and recommendations
        """
        report = self._get_latest_report(presentation_id)
        if not report:
            return {'error': 'No quality metrics available'}
        
        insights = {
            'summary': self._generate_summary(report),
            'priority_actions': self._identify_priority_actions(report),
            'quick_wins': self._identify_quick_wins(report),
            'long_term_improvements': self._identify_long_term_improvements(report),
            'benchmarks': self._compare_to_benchmarks(report)
        }
        
        return insights
    
    def export_metrics(
        self,
        presentation_id: Optional[UUID] = None,
        format: str = 'json'
    ) -> str:
        """
        Export metrics in specified format.
        
        Args:
            presentation_id: Specific presentation or all
            format: Export format (json, csv)
            
        Returns:
            Exported metrics string
        """
        if presentation_id:
            data = {
                'presentation_id': str(presentation_id),
                'metrics_history': self.get_presentation_metrics_history(presentation_id)
            }
        else:
            data = {
                'aggregated_metrics': self.get_aggregated_metrics(),
                'all_presentations': {
                    str(pid): self.get_presentation_metrics_history(pid)
                    for pid in self.metrics_history.keys()
                }
            }
        
        if format == 'json':
            return json.dumps(data, indent=2, default=str)
        elif format == 'csv':
            # Simplified CSV export
            lines = ['presentation_id,date,overall_score,quality_level']
            for pid, reports in self.metrics_history.items():
                for report in reports:
                    lines.append(
                        f"{pid},{report.assessment_date.isoformat()},"
                        f"{report.metrics.overall_score:.2f},"
                        f"{report.metrics.quality_level.value}"
                    )
            return '\n'.join(lines)
        else:
            return json.dumps(data, default=str)
    
    # Private helper methods
    
    def _calculate_trend(self, presentation_id: UUID) -> Dict[str, Any]:
        """Calculate quality trend for a presentation."""
        reports = self.metrics_history[presentation_id]
        if len(reports) < 2:
            return {}
        
        # Compare last two assessments
        current = reports[-1]
        previous = reports[-2]
        
        trend = {
            'overall_change': current.metrics.overall_score - previous.metrics.overall_score,
            'dimension_changes': {},
            'issues_change': len(current.metrics.issues) - len(previous.metrics.issues)
        }
        
        # Dimension changes
        for dim in QualityDimension:
            current_score = current.metrics.dimension_scores.get(dim, 0)
            previous_score = previous.metrics.dimension_scores.get(dim, 0)
            trend['dimension_changes'][dim.value] = current_score - previous_score
        
        return trend
    
    def _calculate_average_score(self, reports: List[QualityReport]) -> float:
        """Calculate average overall score."""
        if not reports:
            return 0.0
        return sum(r.metrics.overall_score for r in reports) / len(reports)
    
    def _calculate_dimension_averages(
        self,
        reports: List[QualityReport]
    ) -> Dict[str, float]:
        """Calculate average scores per dimension."""
        dimension_totals = {dim: 0.0 for dim in QualityDimension}
        dimension_counts = {dim: 0 for dim in QualityDimension}
        
        for report in reports:
            for dim, score in report.metrics.dimension_scores.items():
                dimension_totals[dim] += score
                dimension_counts[dim] += 1
        
        return {
            dim.value: (
                dimension_totals[dim] / dimension_counts[dim]
                if dimension_counts[dim] > 0 else 0.0
            )
            for dim in QualityDimension
        }
    
    def _calculate_quality_distribution(
        self,
        reports: List[QualityReport]
    ) -> Dict[str, int]:
        """Calculate distribution of quality levels."""
        distribution = {level.value: 0 for level in QualityLevel}
        
        for report in reports:
            distribution[report.metrics.quality_level.value] += 1
        
        return distribution
    
    def _identify_common_issues(
        self,
        reports: List[QualityReport]
    ) -> List[Dict[str, Any]]:
        """Identify most common quality issues."""
        issue_counter = {}
        
        for report in reports:
            for issue in report.metrics.issues:
                key = (issue.dimension.value, issue.description)
                if key not in issue_counter:
                    issue_counter[key] = {
                        'dimension': issue.dimension.value,
                        'description': issue.description,
                        'count': 0,
                        'severity': issue.severity
                    }
                issue_counter[key]['count'] += 1
        
        # Sort by frequency
        common_issues = sorted(
            issue_counter.values(),
            key=lambda x: x['count'],
            reverse=True
        )
        
        return common_issues[:10]  # Top 10 issues
    
    def _calculate_improvement_rate(
        self,
        reports: List[QualityReport]
    ) -> float:
        """Calculate rate of quality improvement."""
        if len(reports) < 2:
            return 0.0
        
        # Group by presentation
        presentation_trends = {}
        for report in reports:
            pid = report.presentation_id
            if pid not in presentation_trends:
                presentation_trends[pid] = []
            presentation_trends[pid].append(report.metrics.overall_score)
        
        # Calculate improvement for each presentation
        improvements = []
        for pid, scores in presentation_trends.items():
            if len(scores) >= 2:
                improvement = scores[-1] - scores[0]
                improvements.append(improvement)
        
        if not improvements:
            return 0.0
        
        # Average improvement rate
        avg_improvement = sum(improvements) / len(improvements)
        return avg_improvement
    
    def _identify_best_practices(
        self,
        reports: List[QualityReport]
    ) -> List[str]:
        """Identify best practices from high-scoring presentations."""
        high_quality_reports = [
            r for r in reports
            if r.metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
        ]
        
        if not high_quality_reports:
            return []
        
        # Collect strengths from high-quality presentations
        all_strengths = []
        for report in high_quality_reports:
            all_strengths.extend(report.metrics.strengths)
        
        # Count occurrences
        strength_counts = {}
        for strength in all_strengths:
            strength_counts[strength] = strength_counts.get(strength, 0) + 1
        
        # Sort by frequency
        best_practices = sorted(
            strength_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [practice for practice, _ in best_practices[:5]]
    
    def _get_latest_report(self, presentation_id: UUID) -> Optional[QualityReport]:
        """Get the latest quality report for a presentation."""
        if presentation_id not in self.metrics_history:
            return None
        reports = self.metrics_history[presentation_id]
        return reports[-1] if reports else None
    
    def _generate_summary(self, report: QualityReport) -> str:
        """Generate a summary of the quality assessment."""
        level = report.metrics.quality_level.value
        score = report.metrics.overall_score
        
        if level == QualityLevel.EXCELLENT.value:
            summary = f"Excellent presentation quality (score: {score:.2f}). "
            summary += "The presentation demonstrates strong coherence, proper citations, and balanced visuals."
        elif level == QualityLevel.GOOD.value:
            summary = f"Good presentation quality (score: {score:.2f}). "
            summary += "Minor improvements would enhance the overall effectiveness."
        elif level == QualityLevel.SATISFACTORY.value:
            summary = f"Satisfactory presentation quality (score: {score:.2f}). "
            summary += "Several areas need attention for better academic standards."
        else:
            summary = f"The presentation needs significant improvement (score: {score:.2f}). "
            summary += "Focus on addressing critical issues first."
        
        return summary
    
    def _identify_priority_actions(
        self,
        report: QualityReport
    ) -> List[Dict[str, Any]]:
        """Identify priority actions based on critical issues."""
        priority_actions = []
        
        # Group critical issues by dimension
        critical_by_dimension = {}
        for issue in report.metrics.issues:
            if issue.severity == "critical":
                dim = issue.dimension.value
                if dim not in critical_by_dimension:
                    critical_by_dimension[dim] = []
                critical_by_dimension[dim].append(issue)
        
        # Create priority actions
        for dimension, issues in critical_by_dimension.items():
            action = {
                'dimension': dimension,
                'action': f"Fix {len(issues)} critical issues in {dimension}",
                'impact': 'high',
                'estimated_time': len(issues) * 10,
                'specific_fixes': [issue.suggestion for issue in issues[:3]]
            }
            priority_actions.append(action)
        
        return sorted(priority_actions, key=lambda x: x['estimated_time'])
    
    def _identify_quick_wins(self, report: QualityReport) -> List[Dict[str, Any]]:
        """Identify quick improvements that can be made."""
        quick_wins = []
        
        # Find minor issues that are easy to fix
        for issue in report.metrics.issues:
            if issue.severity == "minor" and issue.suggestion:
                quick_wins.append({
                    'issue': issue.description,
                    'fix': issue.suggestion,
                    'dimension': issue.dimension.value,
                    'slide': issue.slide_number,
                    'estimated_time': 2
                })
        
        # Limit to top 5 quick wins
        return quick_wins[:5]
    
    def _identify_long_term_improvements(
        self,
        report: QualityReport
    ) -> List[str]:
        """Identify long-term improvements."""
        improvements = []
        
        # Based on dimension scores
        for dim, score in report.metrics.dimension_scores.items():
            if score < 0.6:
                if dim == QualityDimension.COHERENCE:
                    improvements.append(
                        "Restructure presentation flow for better logical progression"
                    )
                elif dim == QualityDimension.CITATIONS:
                    improvements.append(
                        "Conduct thorough literature review and add comprehensive citations"
                    )
                elif dim == QualityDimension.VISUAL_BALANCE:
                    improvements.append(
                        "Redesign slides with professional visual elements and layouts"
                    )
        
        return improvements
    
    def _compare_to_benchmarks(self, report: QualityReport) -> Dict[str, Any]:
        """Compare metrics to benchmark standards."""
        benchmarks = {
            'academic_conference': {
                'overall': 0.8,
                'coherence': 0.85,
                'citations': 0.9,
                'visual_balance': 0.75
            },
            'lecture': {
                'overall': 0.75,
                'coherence': 0.8,
                'citations': 0.7,
                'visual_balance': 0.7
            }
        }
        
        # Use academic conference as default benchmark
        benchmark = benchmarks['academic_conference']
        
        comparison = {
            'meets_standards': report.metrics.overall_score >= benchmark['overall'],
            'overall_gap': report.metrics.overall_score - benchmark['overall'],
            'dimension_gaps': {}
        }
        
        for dim in [QualityDimension.COHERENCE, QualityDimension.CITATIONS, 
                   QualityDimension.VISUAL_BALANCE]:
            score = report.metrics.dimension_scores.get(dim, 0)
            benchmark_score = benchmark.get(dim.value, 0.75)
            comparison['dimension_gaps'][dim.value] = score - benchmark_score
        
        return comparison