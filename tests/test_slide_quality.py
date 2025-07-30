"""Tests for slide quality assurance system."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from typing import Tuple

from app.services.slides.interfaces import (
    IQualityChecker, PresentationContent, SlideContent,
    QualityReport
)
from app.services.slides.config import QualityLevel


class MockQualityChecker(IQualityChecker):
    """Mock implementation of quality checker."""
    
    def __init__(self):
        self.check_quality_calls = 0
        self.improve_quality_calls = 0
        self.quality_metrics = [
            "readability",
            "consistency", 
            "accessibility",
            "spelling",
            "grammar",
            "visual_balance",
            "citations"
        ]
    
    async def check_quality(
        self,
        presentation: PresentationContent,
        quality_level: str = "standard"
    ) -> QualityReport:
        self.check_quality_calls += 1
        
        # Simulate quality scoring based on content
        base_score = 0.7
        
        # Adjust score based on quality level
        if quality_level == "premium":
            base_score -= 0.1  # Higher standards
        elif quality_level == "draft":
            base_score += 0.1  # Lower standards
        
        # Calculate sub-scores
        readability = self._calculate_readability(presentation)
        consistency = self._calculate_consistency(presentation)
        accessibility = self._calculate_accessibility(presentation)
        
        overall_score = (readability + consistency + accessibility) / 3
        
        # Identify issues
        issues = []
        if readability < 0.7:
            issues.append({
                "type": "readability",
                "severity": "medium",
                "description": "Text is too complex",
                "slides_affected": [0, 2]
            })
        
        if consistency < 0.8:
            issues.append({
                "type": "consistency",
                "severity": "low",
                "description": "Inconsistent formatting",
                "slides_affected": [1]
            })
        
        # Generate recommendations
        recommendations = []
        if overall_score < 0.8:
            recommendations.append("Simplify complex sentences")
            recommendations.append("Ensure consistent bullet point formatting")
        
        return QualityReport(
            overall_score=overall_score,
            readability_score=readability,
            consistency_score=consistency,
            accessibility_score=accessibility,
            issues=issues if issues else None,
            recommendations=recommendations if recommendations else None
        )
    
    async def improve_quality(
        self,
        presentation: PresentationContent,
        target_score: float = 0.8
    ) -> Tuple[PresentationContent, QualityReport]:
        self.improve_quality_calls += 1
        
        # Simulate quality improvement
        improved_presentation = PresentationContent(
            title=presentation.title,
            subtitle=presentation.subtitle,
            author=presentation.author,
            date=presentation.date,
            slides=[self._improve_slide(slide) for slide in presentation.slides],
            theme=presentation.theme,
            metadata=presentation.metadata
        )
        
        # Generate improved report
        improved_report = QualityReport(
            overall_score=target_score + 0.05,  # Slightly exceed target
            readability_score=target_score + 0.1,
            consistency_score=target_score + 0.05,
            accessibility_score=target_score,
            issues=None,  # Issues resolved
            recommendations=["Continue monitoring quality metrics"]
        )
        
        return improved_presentation, improved_report
    
    def get_quality_metrics(self) -> list[str]:
        return self.quality_metrics
    
    def _calculate_readability(self, presentation: PresentationContent) -> float:
        """Calculate readability score."""
        total_length = 0
        for slide in presentation.slides:
            if slide.content:
                total_length += len(slide.content)
        
        # Simple heuristic: shorter is more readable
        if total_length < 500:
            return 0.9
        elif total_length < 1000:
            return 0.7
        else:
            return 0.5
    
    def _calculate_consistency(self, presentation: PresentationContent) -> float:
        """Calculate consistency score."""
        # Check if all slides have titles
        slides_with_titles = sum(1 for slide in presentation.slides if slide.title)
        return slides_with_titles / len(presentation.slides) if presentation.slides else 1.0
    
    def _calculate_accessibility(self, presentation: PresentationContent) -> float:
        """Calculate accessibility score."""
        # Check for visual elements with alt text
        total_visuals = 0
        visuals_with_alt = 0
        
        for slide in presentation.slides:
            if slide.visual_elements:
                for element in slide.visual_elements:
                    total_visuals += 1
                    if element.get("alt_text"):
                        visuals_with_alt += 1
        
        if total_visuals == 0:
            return 1.0  # No visuals, so accessible by default
        
        return visuals_with_alt / total_visuals
    
    def _improve_slide(self, slide: SlideContent) -> SlideContent:
        """Improve individual slide quality."""
        # Simplify content
        if slide.content and len(slide.content) > 150:
            slide.content = slide.content[:147] + "..."
        
        # Ensure title exists
        if not slide.title and slide.content:
            slide.title = "Slide Title"
        
        # Add alt text to images
        if slide.visual_elements:
            for element in slide.visual_elements:
                if element.get("type") == "image" and not element.get("alt_text"):
                    element["alt_text"] = "Image description"
        
        return slide


class TestQualityChecker:
    """Test suite for quality checker."""
    
    @pytest.fixture
    def checker(self):
        """Create quality checker instance."""
        return MockQualityChecker()
    
    @pytest.fixture
    def sample_presentation(self):
        """Create sample presentation."""
        return PresentationContent(
            title="Quality Test Presentation",
            author="Test Author",
            slides=[
                SlideContent(
                    title="Introduction",
                    content="Welcome to this presentation about quality."
                ),
                SlideContent(
                    title="Main Points",
                    content="Here are the main points to discuss.",
                    bullet_points=["Point 1", "Point 2", "Point 3"]
                ),
                SlideContent(
                    title="Complex Slide",
                    content="x" * 200,  # Long content
                    visual_elements=[
                        {"type": "image", "src": "img.jpg"}  # Missing alt text
                    ]
                )
            ]
        )
    
    @pytest.mark.asyncio
    async def test_basic_quality_check(self, checker, sample_presentation):
        """Test basic quality checking."""
        report = await checker.check_quality(sample_presentation)
        
        assert checker.check_quality_calls == 1
        assert 0 <= report.overall_score <= 1.0
        assert 0 <= report.readability_score <= 1.0
        assert 0 <= report.consistency_score <= 1.0
        assert 0 <= report.accessibility_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_quality_levels(self, checker, sample_presentation):
        """Test different quality levels."""
        # Test draft level
        draft_report = await checker.check_quality(sample_presentation, "draft")
        
        # Test standard level
        standard_report = await checker.check_quality(sample_presentation, "standard")
        
        # Test premium level
        premium_report = await checker.check_quality(sample_presentation, "premium")
        
        # Premium should have stricter scoring than draft
        assert draft_report.overall_score > premium_report.overall_score
    
    @pytest.mark.asyncio
    async def test_quality_issues_detection(self, checker, sample_presentation):
        """Test detection of quality issues."""
        report = await checker.check_quality(sample_presentation)
        
        # Should detect issues
        assert report.issues is not None
        assert len(report.issues) > 0
        
        # Check issue structure
        issue = report.issues[0]
        assert "type" in issue
        assert "severity" in issue
        assert "description" in issue
        assert "slides_affected" in issue
    
    @pytest.mark.asyncio
    async def test_quality_recommendations(self, checker, sample_presentation):
        """Test generation of recommendations."""
        report = await checker.check_quality(sample_presentation)
        
        if report.overall_score < 0.8:
            assert report.recommendations is not None
            assert len(report.recommendations) > 0
            assert all(isinstance(rec, str) for rec in report.recommendations)
    
    @pytest.mark.asyncio
    async def test_improve_quality(self, checker, sample_presentation):
        """Test quality improvement functionality."""
        improved_pres, improved_report = await checker.improve_quality(
            sample_presentation,
            target_score=0.85
        )
        
        assert checker.improve_quality_calls == 1
        
        # Check improved presentation
        assert improved_pres.title == sample_presentation.title
        assert len(improved_pres.slides) == len(sample_presentation.slides)
        
        # Check improved scores
        assert improved_report.overall_score >= 0.85
        assert improved_report.issues is None  # Issues should be resolved
    
    @pytest.mark.asyncio
    async def test_improve_quality_content_changes(self, checker, sample_presentation):
        """Test that quality improvement modifies content."""
        improved_pres, _ = await checker.improve_quality(sample_presentation)
        
        # Check that long content was shortened
        long_slide = sample_presentation.slides[2]
        improved_slide = improved_pres.slides[2]
        
        assert len(improved_slide.content) < len(long_slide.content)
        assert improved_slide.content.endswith("...")
        
        # Check that alt text was added
        assert improved_slide.visual_elements[0].get("alt_text") == "Image description"
    
    def test_get_quality_metrics(self, checker):
        """Test getting available quality metrics."""
        metrics = checker.get_quality_metrics()
        
        assert "readability" in metrics
        assert "consistency" in metrics
        assert "accessibility" in metrics
        assert "spelling" in metrics
        assert "grammar" in metrics
        assert len(metrics) > 5


class TestQualityScoring:
    """Test quality scoring algorithms."""
    
    @pytest.fixture
    def checker(self):
        return MockQualityChecker()
    
    @pytest.mark.asyncio
    async def test_readability_scoring(self, checker):
        """Test readability score calculation."""
        # Short presentation - high readability
        short_pres = PresentationContent(
            title="Short",
            slides=[
                SlideContent(content="Brief content"),
                SlideContent(content="Another brief slide")
            ]
        )
        
        report = await checker.check_quality(short_pres)
        assert report.readability_score >= 0.8
        
        # Long presentation - lower readability
        long_pres = PresentationContent(
            title="Long",
            slides=[
                SlideContent(content="x" * 500),
                SlideContent(content="y" * 500)
            ]
        )
        
        report = await checker.check_quality(long_pres)
        assert report.readability_score <= 0.6
    
    @pytest.mark.asyncio
    async def test_consistency_scoring(self, checker):
        """Test consistency score calculation."""
        # Consistent presentation - all slides have titles
        consistent_pres = PresentationContent(
            title="Consistent",
            slides=[
                SlideContent(title="Slide 1", content="Content 1"),
                SlideContent(title="Slide 2", content="Content 2"),
                SlideContent(title="Slide 3", content="Content 3")
            ]
        )
        
        report = await checker.check_quality(consistent_pres)
        assert report.consistency_score == 1.0
        
        # Inconsistent presentation - missing titles
        inconsistent_pres = PresentationContent(
            title="Inconsistent",
            slides=[
                SlideContent(title="Slide 1", content="Content 1"),
                SlideContent(content="Content 2"),  # No title
                SlideContent(title="Slide 3", content="Content 3")
            ]
        )
        
        report = await checker.check_quality(inconsistent_pres)
        assert report.consistency_score < 1.0
    
    @pytest.mark.asyncio
    async def test_accessibility_scoring(self, checker):
        """Test accessibility score calculation."""
        # Accessible presentation - all images have alt text
        accessible_pres = PresentationContent(
            title="Accessible",
            slides=[
                SlideContent(
                    title="Images",
                    visual_elements=[
                        {"type": "image", "src": "1.jpg", "alt_text": "Description 1"},
                        {"type": "image", "src": "2.jpg", "alt_text": "Description 2"}
                    ]
                )
            ]
        )
        
        report = await checker.check_quality(accessible_pres)
        assert report.accessibility_score == 1.0
        
        # Inaccessible presentation - missing alt text
        inaccessible_pres = PresentationContent(
            title="Inaccessible",
            slides=[
                SlideContent(
                    title="Images",
                    visual_elements=[
                        {"type": "image", "src": "1.jpg", "alt_text": "Description"},
                        {"type": "image", "src": "2.jpg"},  # Missing alt text
                        {"type": "image", "src": "3.jpg"}   # Missing alt text
                    ]
                )
            ]
        )
        
        report = await checker.check_quality(inaccessible_pres)
        assert report.accessibility_score < 0.5


class TestQualityEdgeCases:
    """Test edge cases for quality system."""
    
    @pytest.fixture
    def checker(self):
        return MockQualityChecker()
    
    @pytest.mark.asyncio
    async def test_empty_presentation(self, checker):
        """Test quality check on empty presentation."""
        empty_pres = PresentationContent(
            title="Empty",
            slides=[]
        )
        
        report = await checker.check_quality(empty_pres)
        
        # Should handle gracefully
        assert report.overall_score >= 0
        assert report.consistency_score == 1.0  # No slides to be inconsistent
    
    @pytest.mark.asyncio
    async def test_presentation_without_content(self, checker):
        """Test presentation with slides but no content."""
        no_content_pres = PresentationContent(
            title="No Content",
            slides=[
                SlideContent(),
                SlideContent(),
                SlideContent()
            ]
        )
        
        report = await checker.check_quality(no_content_pres)
        
        # Should still generate report
        assert report is not None
        assert report.readability_score >= 0
    
    @pytest.mark.asyncio
    async def test_improve_already_good_presentation(self, checker):
        """Test improving presentation that already meets target."""
        good_pres = PresentationContent(
            title="Good Presentation",
            slides=[
                SlideContent(title="Good Slide", content="Perfect content")
            ]
        )
        
        # Mock to return high initial score
        with patch.object(checker, 'check_quality', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = QualityReport(
                overall_score=0.95,
                readability_score=0.95,
                consistency_score=0.95,
                accessibility_score=0.95
            )
            
            improved_pres, improved_report = await checker.improve_quality(
                good_pres,
                target_score=0.8
            )
            
            # Should still exceed target
            assert improved_report.overall_score > 0.8


class TestQualityIntegration:
    """Integration tests for quality system."""
    
    @pytest.mark.asyncio
    async def test_quality_workflow(self):
        """Test complete quality workflow."""
        checker = MockQualityChecker()
        
        # Create presentation with various quality issues
        problematic_pres = PresentationContent(
            title="Problematic Presentation",
            slides=[
                SlideContent(content="No title here"),  # Missing title
                SlideContent(
                    title="Long Content",
                    content="x" * 300  # Too long
                ),
                SlideContent(
                    title="Images",
                    visual_elements=[
                        {"type": "image", "src": "img.jpg"}  # No alt text
                    ]
                )
            ]
        )
        
        # Initial quality check
        initial_report = await checker.check_quality(problematic_pres)
        assert initial_report.overall_score < 0.8
        assert initial_report.issues is not None
        
        # Improve quality
        improved_pres, improved_report = await checker.improve_quality(
            problematic_pres,
            target_score=0.85
        )
        
        # Verify improvements
        assert improved_report.overall_score >= 0.85
        assert improved_report.issues is None
        
        # Verify specific improvements
        assert improved_pres.slides[0].title is not None  # Title added
        assert len(improved_pres.slides[1].content) < 300  # Content shortened
        assert improved_pres.slides[2].visual_elements[0].get("alt_text")  # Alt text added
    
    def test_quality_level_enum(self):
        """Test QualityLevel enum values."""
        assert QualityLevel.DRAFT.value == "draft"
        assert QualityLevel.STANDARD.value == "standard"
        assert QualityLevel.PREMIUM.value == "premium"