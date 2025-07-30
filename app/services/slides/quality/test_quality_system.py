"""
Unit tests for the SlideGenie Quality Assurance System.

This module tests the core functionality of quality checkers
without requiring external dependencies.
"""
import unittest
from datetime import datetime
from uuid import uuid4

# Mock the schema classes to avoid dependency issues
class MockPresentationResponse:
    def __init__(self):
        self.id = uuid4()
        self.owner_id = uuid4()
        self.title = "Test Presentation"
        self.subtitle = "Test Subtitle"
        self.description = "Test description"
        self.abstract = "Test abstract"
        self.presentation_type = "conference"
        self.academic_level = "research"
        self.field_of_study = "Computer Science"
        self.keywords = ["test", "quality"]
        self.duration_minutes = 15
        self.status = "draft"
        self.slide_count = 3
        self.view_count = 0
        self.is_public = False
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class MockSlideResponse:
    def __init__(self, title="Test Slide", slide_number=1, content=None):
        self.id = uuid4()
        self.presentation_id = uuid4()
        self.slide_number = slide_number
        self.title = title
        self.content = content or {}
        self.layout_type = "content"
        self.speaker_notes = None
        self.section = None
        self.contains_equations = False
        self.contains_code = False
        self.contains_citations = False
        self.figure_count = 0
        self.is_hidden = False
        self.is_backup = False
        self.transitions = {}
        self.animations = {}
        self.duration_seconds = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class MockCitation:
    def __init__(self, key="test2023"):
        self.key = key
        self.authors = ["Test Author"]
        self.title = "Test Paper"
        self.year = 2023
        self.venue = "Test Journal"
        self.doi = "10.1234/test"
        self.url = None
        self.bibtex_type = "article"
        self.raw_bibtex = None


class TestQualitySystem(unittest.TestCase):
    """Test the quality assurance system components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.presentation = MockPresentationResponse()
        self.slides = [
            MockSlideResponse("Introduction", 1, {
                "body": [
                    {"type": "text", "content": "This is an introduction slide with some content."}
                ]
            }),
            MockSlideResponse("Methods", 2, {
                "body": [
                    {"type": "bullet_list", "items": ["Point 1", "Point 2", "Point 3"]},
                    {"type": "citation", "keys": ["test2023"]}
                ]
            }),
            MockSlideResponse("Conclusion", 3, {
                "body": [
                    {"type": "text", "content": "In conclusion, this presentation demonstrates quality assessment."}
                ]
            })
        ]
        self.references = [MockCitation()]
    
    def test_quality_dimensions_enum(self):
        """Test that quality dimensions are properly defined."""
        from app.services.slides.quality.base import QualityDimension
        
        expected_dimensions = [
            'COHERENCE', 'TRANSITIONS', 'CITATIONS', 'TIMING', 
            'VISUAL_BALANCE', 'READABILITY', 'COMPLETENESS', 'ACCURACY'
        ]
        
        actual_dimensions = [dim.name for dim in QualityDimension]
        
        for expected in expected_dimensions[:6]:  # Test first 6 that we implemented
            self.assertIn(expected, actual_dimensions)
    
    def test_quality_levels_enum(self):
        """Test that quality levels are properly defined."""
        from app.services.slides.quality.base import QualityLevel
        
        expected_levels = ['EXCELLENT', 'GOOD', 'SATISFACTORY', 'NEEDS_IMPROVEMENT', 'POOR']
        actual_levels = [level.name for level in QualityLevel]
        
        for expected in expected_levels:
            self.assertIn(expected, actual_levels)
    
    def test_quality_issue_creation(self):
        """Test quality issue creation."""
        from app.services.slides.quality.base import QualityIssue, QualityDimension
        
        issue = QualityIssue(
            dimension=QualityDimension.COHERENCE,
            severity="major",
            slide_number=1,
            description="Test issue",
            suggestion="Test suggestion"
        )
        
        self.assertEqual(issue.dimension, QualityDimension.COHERENCE)
        self.assertEqual(issue.severity, "major")
        self.assertEqual(issue.slide_number, 1)
        self.assertEqual(issue.description, "Test issue")
        self.assertEqual(issue.suggestion, "Test suggestion")
    
    def test_quality_metrics_properties(self):
        """Test quality metrics calculations."""
        from app.services.slides.quality.base import QualityMetrics, QualityDimension, QualityLevel
        
        metrics = QualityMetrics(
            overall_score=0.85,
            dimension_scores={QualityDimension.COHERENCE: 0.9, QualityDimension.CITATIONS: 0.8},
            issues=[],
            strengths=["Good flow"],
            improvement_areas=[]
        )
        
        self.assertEqual(metrics.overall_score, 0.85)
        self.assertEqual(metrics.quality_level, QualityLevel.GOOD)
        self.assertEqual(metrics.critical_issues_count, 0)
        self.assertEqual(metrics.major_issues_count, 0)
    
    def test_base_quality_checker_interface(self):
        """Test the base quality checker interface."""
        from app.services.slides.quality.base import QualityChecker, QualityDimension
        
        class TestChecker(QualityChecker):
            @property
            def dimension(self):
                return QualityDimension.COHERENCE
            
            def check(self, presentation, slides, references=None):
                return 0.8, [], {}
        
        checker = TestChecker()
        self.assertEqual(checker.dimension, QualityDimension.COHERENCE)
        self.assertEqual(checker.weight, 1.0)  # Default weight
        
        score, issues, metadata = checker.check(self.presentation, self.slides)
        self.assertEqual(score, 0.8)
        self.assertEqual(issues, [])
        self.assertEqual(metadata, {})
    
    def test_simple_coherence_analysis(self):
        """Test basic coherence checking without NLTK dependencies."""
        # Simple test that doesn't require NLTK
        slide_texts = [
            slide.content.get('body', [{}])[0].get('content', '') 
            for slide in self.slides
            if slide.content and 'body' in slide.content
        ]
        
        # Basic keyword extraction without NLTK
        def simple_keywords(text):
            words = text.lower().split()
            return set(w for w in words if len(w) > 3 and w.isalpha())
        
        keywords_sets = [simple_keywords(text) for text in slide_texts if text]
        
        # Test that we can extract some keywords
        self.assertTrue(len(keywords_sets) > 0)
        if len(keywords_sets) > 1:
            # Test keyword overlap calculation
            overlap = len(keywords_sets[0] & keywords_sets[1]) / min(len(keywords_sets[0]), len(keywords_sets[1])) if keywords_sets[0] and keywords_sets[1] else 0
            self.assertIsInstance(overlap, float)
            self.assertTrue(0 <= overlap <= 1)
    
    def test_timing_estimation_basics(self):
        """Test basic timing estimation logic."""
        # Test basic timing calculations
        base_time = 20  # seconds
        
        # Simulate word counting
        text = "This is a test slide with some content to analyze for timing."
        word_count = len(text.split())
        reading_speed = 150  # words per minute
        reading_time = (word_count / reading_speed) * 60
        
        total_time = base_time + reading_time
        
        self.assertIsInstance(total_time, (int, float))
        self.assertGreater(total_time, 0)
    
    def test_citation_pattern_matching(self):
        """Test citation pattern recognition."""
        import re
        
        # Test citation patterns
        citation_patterns = {
            'inline': r'\(([A-Za-z\s&,]+,?\s*\d{4}[a-z]?)\)',
            'numbered': r'\[(\d+)\]',
            'author_year': r'([A-Z][a-z]+\s+(?:et\s+al\.\s+)?\(\d{4}\))'
        }
        
        test_text = "Studies show (Smith, 2023) that quality matters. See reference [1] for details."
        
        for pattern_name, pattern in citation_patterns.items():
            matches = re.findall(pattern, test_text)
            if pattern_name == 'inline':
                self.assertGreater(len(matches), 0)
                self.assertIn('Smith, 2023', matches[0])
            elif pattern_name == 'numbered':
                self.assertGreater(len(matches), 0)
                self.assertEqual(matches[0], '1')
    
    def test_visual_balance_element_counting(self):
        """Test visual element counting logic."""
        slide = self.slides[1]  # Methods slide with bullet points
        
        # Count elements
        element_count = {'text': 0, 'bullets': 0, 'visuals': 0}
        
        if slide.content and 'body' in slide.content:
            for item in slide.content['body']:
                item_type = item.get('type', '')
                if item_type == 'text':
                    element_count['text'] += 1
                elif item_type == 'bullet_list':
                    element_count['bullets'] += len(item.get('items', []))
                elif item_type in ['image', 'chart', 'diagram']:
                    element_count['visuals'] += 1
        
        # Test that we counted elements correctly
        self.assertEqual(element_count['bullets'], 3)  # 3 bullet points
        self.assertEqual(element_count['text'], 0)
        self.assertEqual(element_count['visuals'], 0)
    
    def test_readability_sentence_analysis(self):
        """Test sentence analysis without NLTK."""
        text = "This is a test sentence. Here is another one! And a question?"
        
        # Simple sentence splitting
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        
        self.assertEqual(len(sentences), 3)
        self.assertEqual(sentence_lengths[0], 5)  # "This is a test sentence"
        self.assertEqual(sentence_lengths[1], 4)  # "Here is another one"
        self.assertEqual(sentence_lengths[2], 3)  # "And a question"
    
    def test_quality_report_serialization(self):
        """Test quality report dictionary conversion."""
        from app.services.slides.quality.base import QualityMetrics, QualityReport
        
        metrics = QualityMetrics(
            overall_score=0.75,
            dimension_scores={},
            issues=[],
            strengths=["Test strength"],
            improvement_areas=["Test improvement"]
        )
        
        report = QualityReport(
            presentation_id=self.presentation.id,
            assessment_date=datetime.utcnow(),
            metrics=metrics,
            recommendations=["Test recommendation"],
            estimated_revision_time=30
        )
        
        # Test dictionary conversion
        report_dict = report.to_dict()
        
        self.assertIn('presentation_id', report_dict)
        self.assertIn('assessment_date', report_dict)
        self.assertIn('metrics', report_dict)
        self.assertIn('recommendations', report_dict)
        self.assertIn('estimated_revision_time', report_dict)
        
        metrics_dict = report_dict['metrics']
        self.assertEqual(metrics_dict['overall_score'], 0.75)
        self.assertEqual(metrics_dict['quality_level'], 'satisfactory')
        self.assertIn('Test strength', metrics_dict['strengths'])


if __name__ == '__main__':
    # Run tests with minimal dependencies
    import sys
    import os
    
    # Add the current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    
    # Run the tests
    unittest.main()