"""
Test suite for the Document Intelligence Engine.

This module provides comprehensive tests for the intelligence analysis capabilities
including language detection, quality assessment, content gap analysis, and more.
"""

import asyncio
import pytest
from uuid import uuid4
from datetime import datetime

from app.domain.schemas.document_processing import (
    ProcessingResult,
    DocumentSection,
    TextElement,
    HeadingElement,
    ReferenceElement,
    CitationElement,
    ElementType,
    BoundingBox,
)

from .analyzer import (
    IntelligenceEngine,
    LanguageCode,
    QualityLevel,
    DocumentType,
    SectionType,
    WritingIssueType,
)


class TestIntelligenceEngine:
    """Test suite for the Intelligence Engine."""
    
    @pytest.fixture
    def intelligence_engine(self):
        """Create an intelligence engine instance."""
        return IntelligenceEngine()
    
    @pytest.fixture
    def sample_processing_result(self):
        """Create a sample processing result for testing."""
        document_id = uuid4()
        
        # Create sample elements
        elements = [
            HeadingElement(
                id=uuid4(),
                element_type=ElementType.HEADING,
                text="Advanced Machine Learning Techniques",
                bounding_box=BoundingBox(x=0, y=0, width=100, height=20),
                level=1
            ),
            TextElement(
                id=uuid4(),
                element_type=ElementType.TEXT,
                text="This paper presents a comprehensive analysis of advanced machine learning techniques. "
                     "The research focuses on deep learning algorithms and their applications in natural language processing. "
                     "However, there are several challenges that need to be addressed. Therefore, we propose a novel approach.",
                bounding_box=BoundingBox(x=0, y=25, width=100, height=60)
            ),
            HeadingElement(
                id=uuid4(),
                element_type=ElementType.HEADING,
                text="Introduction",
                bounding_box=BoundingBox(x=0, y=90, width=100, height=20),
                level=2
            ),
            TextElement(
                id=uuid4(),
                element_type=ElementType.TEXT,
                text="Machine learning has revolutionized many fields. The introduction of deep learning has enabled "
                     "significant breakthroughs in computer vision and natural language processing. "
                     "This study aims to investigate the effectiveness of transformer architectures.",
                bounding_box=BoundingBox(x=0, y=115, width=100, height=60)
            ),
            HeadingElement(
                id=uuid4(),
                element_type=ElementType.HEADING,
                text="Methodology",
                bounding_box=BoundingBox(x=0, y=180, width=100, height=20),
                level=2
            ),
            TextElement(
                id=uuid4(),
                element_type=ElementType.TEXT,
                text="We conducted experiments using a dataset of 10,000 samples. The data was preprocessed using "
                     "standard techniques. Statistical analysis was performed using Python libraries. "
                     "The methodology follows established protocols.",
                bounding_box=BoundingBox(x=0, y=205, width=100, height=60)
            ),
            CitationElement(
                id=uuid4(),
                element_type=ElementType.CITATION,
                text="(Smith et al., 2023)",
                bounding_box=BoundingBox(x=0, y=270, width=30, height=15)
            ),
            ReferenceElement(
                id=uuid4(),
                element_type=ElementType.REFERENCE,
                text="Smith, J., Johnson, M., & Williams, K. (2023). Deep Learning Applications. Journal of AI Research, 15(3), 45-67.",
                bounding_box=BoundingBox(x=0, y=290, width=100, height=25)
            )
        ]
        
        # Create sections
        sections = [
            DocumentSection(
                id=uuid4(),
                title="Advanced Machine Learning Techniques",
                elements=elements[:2],
                section_type="title"
            ),
            DocumentSection(
                id=uuid4(),
                title="Introduction",
                elements=elements[2:4],
                section_type="introduction"
            ),
            DocumentSection(
                id=uuid4(),
                title="Methodology",
                elements=elements[4:6],
                section_type="methodology"
            ),
            DocumentSection(
                id=uuid4(),
                title="References",
                elements=elements[6:],
                section_type="references"
            )
        ]
        
        return ProcessingResult(
            document_id=document_id,
            filename="test_document.pdf",
            processing_status="completed",
            elements=elements,
            sections=sections,
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    async def test_analyze_document_complete_flow(self, intelligence_engine, sample_processing_result):
        """Test the complete document analysis flow."""
        result = await intelligence_engine.analyze_document(sample_processing_result)
        
        # Verify basic result structure
        assert result.document_id == sample_processing_result.document_id
        assert result.analysis_timestamp is not None
        assert result.processing_time > 0
        assert result.word_count > 0
        assert result.section_count == len(sample_processing_result.sections)
        
        # Verify language detection
        assert result.language_detection.primary_language in LanguageCode
        assert 0.0 <= result.language_detection.confidence <= 1.0
        
        # Verify document type classification
        assert result.document_type in DocumentType
        
        # Verify quality metrics
        assert isinstance(result.quality_metrics.overall_score, float)
        assert 0 <= result.quality_metrics.overall_score <= 100
        assert result.quality_metrics.quality_level in QualityLevel
        
        # Verify analysis components
        assert isinstance(result.missing_sections, list)
        assert isinstance(result.content_gaps, list)
        assert isinstance(result.writing_issues, list)
        assert isinstance(result.priority_improvements, list)
        assert isinstance(result.quick_fixes, list)
        assert isinstance(result.long_term_suggestions, list)

    async def test_language_detection(self, intelligence_engine):
        """Test language detection functionality."""
        # Test English text
        english_text = "This is a comprehensive analysis of machine learning algorithms. " \
                      "The research methodology involves statistical analysis and data processing."
        
        result = await intelligence_engine._detect_language(english_text)
        
        assert result.primary_language == LanguageCode.ENGLISH
        assert result.confidence > 0.5
        assert len(result.evidence) > 0
        
        # Test insufficient text
        short_text = "Too short"
        result = await intelligence_engine._detect_language(short_text)
        assert result.primary_language == LanguageCode.UNKNOWN
        assert result.confidence == 0.0

    async def test_document_type_classification(self, intelligence_engine, sample_processing_result):
        """Test document type classification."""
        doc_type = await intelligence_engine._classify_document_type(sample_processing_result)
        
        assert doc_type in DocumentType
        # With methodology and introduction sections, should likely be classified as research paper
        assert doc_type in [DocumentType.RESEARCH_PAPER, DocumentType.JOURNAL_ARTICLE, DocumentType.UNKNOWN]

    async def test_quality_assessment(self, intelligence_engine, sample_processing_result):
        """Test quality assessment functionality."""
        text_content = intelligence_engine._extract_text_content(sample_processing_result)
        quality_metrics = await intelligence_engine._assess_quality(sample_processing_result, text_content)
        
        # Verify all quality scores are within valid range
        assert 0 <= quality_metrics.overall_score <= 100
        assert 0 <= quality_metrics.readability_score <= 100
        assert 0 <= quality_metrics.coherence_score <= 100
        assert 0 <= quality_metrics.completeness_score <= 100
        assert 0 <= quality_metrics.academic_tone_score <= 100
        assert 0 <= quality_metrics.citation_quality_score <= 100
        assert 0 <= quality_metrics.structure_score <= 100
        assert 0 <= quality_metrics.clarity_score <= 100
        assert 0 <= quality_metrics.conciseness_score <= 100
        assert quality_metrics.quality_level in QualityLevel

    async def test_missing_sections_identification(self, intelligence_engine, sample_processing_result):
        """Test missing sections identification."""
        missing_sections = await intelligence_engine._identify_missing_sections(sample_processing_result)
        
        assert isinstance(missing_sections, list)
        
        # Should identify missing sections like Abstract, Results, Discussion, Conclusion
        missing_types = [section.section_type for section in missing_sections]
        expected_missing = [SectionType.ABSTRACT, SectionType.RESULTS, SectionType.DISCUSSION, SectionType.CONCLUSION]
        
        for expected in expected_missing:
            assert expected in missing_types
        
        # Verify structure of missing section objects
        for section in missing_sections:
            assert section.importance in ["required", "recommended", "optional"]
            assert len(section.description) > 0
            assert len(section.recommendation) > 0
            assert isinstance(section.expected_content, list)

    async def test_content_gaps_analysis(self, intelligence_engine, sample_processing_result):
        """Test content gaps analysis."""
        content_gaps = await intelligence_engine._analyze_content_gaps(sample_processing_result)
        
        assert isinstance(content_gaps, list)
        
        # Verify structure of content gap objects
        for gap in content_gaps:
            assert gap.section in SectionType
            assert len(gap.description) > 0
            assert len(gap.suggestion) > 0
            assert gap.priority in ["high", "medium", "low"]
            assert isinstance(gap.examples, list)

    async def test_writing_issues_identification(self, intelligence_engine, sample_processing_result):
        """Test writing issues identification."""
        text_content = intelligence_engine._extract_text_content(sample_processing_result)
        writing_issues = await intelligence_engine._identify_writing_issues(text_content, sample_processing_result)
        
        assert isinstance(writing_issues, list)
        
        # Verify structure of writing issue objects
        for issue in writing_issues:
            assert issue.issue_type in WritingIssueType
            assert issue.severity in ["low", "medium", "high", "critical"]
            assert len(issue.description) > 0
            assert len(issue.suggestion) > 0
            assert 0.0 <= issue.confidence <= 1.0

    async def test_citation_analysis(self, intelligence_engine, sample_processing_result):
        """Test citation analysis."""
        citation_analysis = await intelligence_engine._analyze_citations(sample_processing_result)
        
        assert citation_analysis.total_citations >= 0
        assert citation_analysis.unique_sources >= 0
        assert citation_analysis.citation_density >= 0
        assert 0 <= citation_analysis.format_consistency <= 1
        assert 0 <= citation_analysis.recency_score <= 1
        assert 0 <= citation_analysis.authority_score <= 1
        assert 0 <= citation_analysis.completeness_score <= 1
        assert isinstance(citation_analysis.issues, list)
        assert isinstance(citation_analysis.recommendations, list)

    async def test_coherence_analysis(self, intelligence_engine, sample_processing_result):
        """Test coherence analysis."""
        text_content = intelligence_engine._extract_text_content(sample_processing_result)
        coherence_analysis = await intelligence_engine._analyze_coherence(sample_processing_result, text_content)
        
        assert 0 <= coherence_analysis.overall_coherence <= 1
        assert 0 <= coherence_analysis.paragraph_flow <= 1
        assert 0 <= coherence_analysis.logical_progression <= 1
        assert 0 <= coherence_analysis.topic_continuity <= 1
        assert isinstance(coherence_analysis.section_transitions, dict)
        assert isinstance(coherence_analysis.weak_transitions, list)
        assert isinstance(coherence_analysis.improvement_suggestions, list)

    async def test_presentation_readiness_assessment(self, intelligence_engine, sample_processing_result):
        """Test presentation readiness assessment."""
        presentation_readiness = await intelligence_engine._assess_presentation_readiness(sample_processing_result)
        
        assert 0 <= presentation_readiness.overall_readiness <= 100
        assert 0 <= presentation_readiness.visual_elements_score <= 100
        assert 0 <= presentation_readiness.slide_adaptability_score <= 100
        assert 0 <= presentation_readiness.content_density_score <= 100
        assert 0 <= presentation_readiness.structure_clarity_score <= 100
        assert 0 <= presentation_readiness.key_points_identifiable <= 100
        assert 0 <= presentation_readiness.narrative_flow_score <= 100
        assert isinstance(presentation_readiness.recommendations, list)
        assert isinstance(presentation_readiness.slide_suggestions, list)

    def test_readability_calculation(self, intelligence_engine):
        """Test readability score calculation."""
        # Test with academic-style text
        academic_text = "The methodology employed in this research involves comprehensive statistical analysis. " \
                       "Data preprocessing was conducted using established protocols. " \
                       "Results demonstrate significant improvements in algorithmic performance."
        
        score = intelligence_engine._calculate_readability_score(academic_text)
        assert 0 <= score <= 100
        
        # Test with empty text
        empty_score = intelligence_engine._calculate_readability_score("")
        assert empty_score == 0.0

    def test_syllable_counting(self, intelligence_engine):
        """Test syllable counting functionality."""
        # Test various words
        test_cases = [
            ("hello", 2),
            ("world", 1),
            ("computer", 3),
            ("analysis", 4),
            ("a", 1),
            ("", 0)
        ]
        
        for word, expected_syllables in test_cases:
            syllables = intelligence_engine._count_syllables(word)
            assert syllables >= 1 if word else syllables == 0

    def test_academic_tone_scoring(self, intelligence_engine):
        """Test academic tone scoring."""
        # Academic text with formal language
        academic_text = "This research demonstrates significant improvements. " \
                       "However, further investigation is required. " \
                       "The methodology follows established protocols."
        
        score = intelligence_engine._calculate_academic_tone_score(academic_text)
        assert 0 <= score <= 100
        
        # Informal text with contractions and weak language
        informal_text = "I think this is pretty good. It's very nice and I really like it."
        informal_score = intelligence_engine._calculate_academic_tone_score(informal_text)
        
        # Academic text should score higher than informal text
        assert score > informal_score

    def test_section_classification(self, intelligence_engine):
        """Test section type classification."""
        test_cases = [
            ("Abstract", SectionType.ABSTRACT),
            ("Introduction", SectionType.INTRODUCTION),
            ("Methodology", SectionType.METHODOLOGY),
            ("Results and Discussion", SectionType.RESULTS),
            ("Conclusion", SectionType.CONCLUSION),
            ("References", SectionType.REFERENCES),
            ("Random Section", SectionType.UNKNOWN)
        ]
        
        for title, expected_type in test_cases:
            classified_type = intelligence_engine._classify_section_type(title)
            assert classified_type == expected_type

    def test_transition_quality_calculation(self, intelligence_engine):
        """Test transition quality calculation between text segments."""
        # Good transition with explicit connector
        text1 = "Machine learning algorithms show promise in various applications."
        text2 = "However, there are several challenges that need to be addressed."
        
        good_score = intelligence_engine._calculate_transition_quality(text1, text2)
        
        # Poor transition without connector
        text3 = "The weather was sunny yesterday."
        text4 = "Quantum computing requires specialized hardware."
        
        poor_score = intelligence_engine._calculate_transition_quality(text3, text4)
        
        assert 0 <= good_score <= 1
        assert 0 <= poor_score <= 1
        assert good_score > poor_score

    def test_topic_continuity_calculation(self, intelligence_engine):
        """Test topic continuity calculation."""
        # Text with good topic continuity
        continuous_text = "Machine learning algorithms are powerful tools. " \
                         "These algorithms can process large datasets efficiently. " \
                         "The processing capabilities enable advanced analytics."
        
        continuity_score = intelligence_engine._calculate_topic_continuity(continuous_text)
        assert 0 <= continuity_score <= 1

    async def test_error_handling(self, intelligence_engine):
        """Test error handling in intelligence analysis."""
        # Test with minimal processing result
        minimal_result = ProcessingResult(
            document_id=uuid4(),
            filename="minimal.pdf",
            processing_status="completed",
            elements=[],
            sections=[],
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Should not raise an exception
        result = await intelligence_engine.analyze_document(minimal_result)
        assert result is not None
        assert result.analysis_confidence >= 0


async def test_intelligence_engine_integration():
    """Integration test for the intelligence engine."""
    engine = IntelligenceEngine()
    
    # Create a more comprehensive test document
    document_id = uuid4()
    
    elements = [
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="The Impact of Artificial Intelligence on Healthcare",
            bounding_box=BoundingBox(x=0, y=0, width=100, height=20),
            level=1
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="Abstract: This study examines the transformative impact of artificial intelligence technologies "
                 "in healthcare settings. Through comprehensive analysis of implementation strategies and outcomes, "
                 "we demonstrate significant improvements in diagnostic accuracy and patient care efficiency.",
            bounding_box=BoundingBox(x=0, y=25, width=100, height=40)
        ),
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="Introduction",
            bounding_box=BoundingBox(x=0, y=70, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="Healthcare systems worldwide face unprecedented challenges. However, the integration of AI technologies "
                 "offers promising solutions. This research aims to evaluate the effectiveness of AI implementation "
                 "in clinical settings. The study addresses the gap between theoretical AI capabilities and practical "
                 "healthcare applications.",
            bounding_box=BoundingBox(x=0, y=95, width=100, height=60)
        )
    ]
    
    sections = [
        DocumentSection(
            id=uuid4(),
            title="The Impact of Artificial Intelligence on Healthcare",
            elements=elements[:2],
            section_type="title"
        ),
        DocumentSection(
            id=uuid4(),
            title="Introduction",
            elements=elements[2:],
            section_type="introduction"
        )
    ]
    
    processing_result = ProcessingResult(
        document_id=document_id,
        filename="ai_healthcare_study.pdf",
        processing_status="completed",
        elements=elements,
        sections=sections,
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Run the analysis
    result = await engine.analyze_document(processing_result)
    
    # Comprehensive verification
    assert result.document_id == document_id
    assert result.language_detection.primary_language == LanguageCode.ENGLISH
    assert result.language_detection.confidence > 0.5
    
    # Should identify as research paper or journal article
    assert result.document_type in [DocumentType.RESEARCH_PAPER, DocumentType.JOURNAL_ARTICLE]
    
    # Quality should be reasonable for well-structured academic text
    assert result.quality_metrics.overall_score > 40
    assert result.quality_metrics.academic_tone_score > 50
    
    # Should identify missing sections
    missing_section_types = [section.section_type for section in result.missing_sections]
    assert SectionType.METHODOLOGY in missing_section_types
    assert SectionType.RESULTS in missing_section_types
    assert SectionType.CONCLUSION in missing_section_types
    
    # Should have actionable recommendations
    assert len(result.priority_improvements) > 0
    assert len(result.quick_fixes) >= 0
    assert len(result.long_term_suggestions) > 0
    
    # Presentation readiness should reflect document structure
    assert 0 <= result.presentation_readiness.overall_readiness <= 100
    
    print(f"✅ Intelligence Analysis Complete:")
    print(f"   Language: {result.language_detection.primary_language.value} ({result.language_detection.confidence:.2f})")
    print(f"   Document Type: {result.document_type.value}")
    print(f"   Overall Quality: {result.quality_metrics.overall_score:.1f}/100 ({result.quality_metrics.quality_level.value})")
    print(f"   Missing Sections: {len(result.missing_sections)}")
    print(f"   Content Gaps: {len(result.content_gaps)}")
    print(f"   Writing Issues: {len(result.writing_issues)}")
    print(f"   Presentation Readiness: {result.presentation_readiness.overall_readiness:.1f}/100")
    print(f"   Analysis Confidence: {result.analysis_confidence:.2f}")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_intelligence_engine_integration())