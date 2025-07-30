"""
Advanced Document Intelligence Engine with ML-based Analysis.

This module provides comprehensive document analysis capabilities including:
- Automatic language detection with confidence scoring
- Content quality assessment with academic standards
- Missing section identification and recommendations
- Suggestion engine for document improvements
- Academic writing style analysis and recommendations
- Content coherence and flow analysis
- Citation quality and completeness assessment
- Document readiness scoring for presentations
"""

import re
import math
import string
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from uuid import UUID

import structlog
import numpy as np
from pydantic import BaseModel, Field

from app.domain.schemas.document_processing import (
    DocumentElement,
    DocumentSection,
    DocumentMetadata,
    TextElement,
    HeadingElement,
    ReferenceElement,
    CitationElement, 
    EquationElement,
    ProcessingResult,
    ElementType,
    BoundingBox,
)

logger = structlog.get_logger(__name__)


class LanguageCode(str, Enum):
    """Supported language codes for detection."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    RUSSIAN = "ru"
    UNKNOWN = "unknown"


class QualityLevel(str, Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 70-89%
    FAIR = "fair"           # 50-69%
    POOR = "poor"           # 30-49%
    CRITICAL = "critical"   # 0-29%


class DocumentType(str, Enum):
    """Document type classification."""
    RESEARCH_PAPER = "research_paper"
    THESIS = "thesis"
    DISSERTATION = "dissertation"
    CONFERENCE_PAPER = "conference_paper"
    JOURNAL_ARTICLE = "journal_article"
    TECHNICAL_REPORT = "technical_report"
    REVIEW_PAPER = "review_paper"
    CASE_STUDY = "case_study"
    WHITE_PAPER = "white_paper"
    UNKNOWN = "unknown"


class SectionType(str, Enum):
    """Academic section types."""
    TITLE = "title"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    LITERATURE_REVIEW = "literature_review"
    METHODOLOGY = "methodology"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    ACKNOWLEDGMENTS = "acknowledgments"
    APPENDIX = "appendix"
    UNKNOWN = "unknown"


class WritingIssueType(str, Enum):
    """Types of writing issues."""
    GRAMMAR = "grammar"
    STYLE = "style"
    CLARITY = "clarity"
    COHERENCE = "coherence"
    CONCISENESS = "conciseness"
    ACADEMIC_TONE = "academic_tone"
    CITATION_FORMAT = "citation_format"
    STRUCTURE = "structure"
    COMPLETENESS = "completeness"


@dataclass
class LanguageDetectionResult:
    """Result of language detection analysis."""
    primary_language: LanguageCode
    confidence: float  # 0.0 to 1.0
    secondary_languages: List[Tuple[LanguageCode, float]] = field(default_factory=list)
    mixed_language_score: float = 0.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class QualityMetrics:
    """Comprehensive quality assessment metrics."""
    overall_score: float  # 0-100
    readability_score: float
    coherence_score: float
    completeness_score: float
    academic_tone_score: float
    citation_quality_score: float
    structure_score: float
    clarity_score: float
    conciseness_score: float
    quality_level: QualityLevel
    
    
@dataclass
class WritingIssue:
    """Individual writing issue identified."""
    issue_type: WritingIssueType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    suggestion: str
    location: Optional[str] = None
    element_id: Optional[UUID] = None
    confidence: float = 1.0


@dataclass
class MissingSection:
    """Information about missing academic sections."""
    section_type: SectionType
    importance: str  # "required", "recommended", "optional"
    description: str
    recommendation: str
    expected_content: List[str] = field(default_factory=list)


@dataclass
class ContentGap:
    """Identified gap in document content."""
    section: SectionType
    gap_type: str
    description: str
    suggestion: str
    priority: str  # "high", "medium", "low"
    examples: List[str] = field(default_factory=list)


@dataclass
class CitationAnalysis:
    """Analysis of citation quality and completeness."""
    total_citations: int
    unique_sources: int
    citation_density: float  # citations per page
    format_consistency: float  # 0-1
    recency_score: float  # 0-1 based on publication dates
    authority_score: float  # 0-1 based on source quality
    completeness_score: float  # 0-1 based on required fields
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class CoherenceAnalysis:
    """Analysis of document coherence and flow."""
    overall_coherence: float  # 0-1
    section_transitions: Dict[str, float] = field(default_factory=dict)
    paragraph_flow: float = 0.0
    logical_progression: float = 0.0
    topic_continuity: float = 0.0
    weak_transitions: List[Dict[str, Any]] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class PresentationReadiness:
    """Assessment of document readiness for presentation conversion."""
    overall_readiness: float  # 0-100
    visual_elements_score: float
    slide_adaptability_score: float
    content_density_score: float
    structure_clarity_score: float
    key_points_identifiable: float
    narrative_flow_score: float
    recommendations: List[str] = field(default_factory=list)
    slide_suggestions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DocumentIntelligenceResult:
    """Complete intelligence analysis result."""
    document_id: UUID
    analysis_timestamp: str
    
    # Core analysis results
    language_detection: LanguageDetectionResult
    document_type: DocumentType
    quality_metrics: QualityMetrics
    
    # Content analysis
    missing_sections: List[MissingSection]
    content_gaps: List[ContentGap]
    writing_issues: List[WritingIssue]
    
    # Specialized analysis
    citation_analysis: CitationAnalysis
    coherence_analysis: CoherenceAnalysis
    presentation_readiness: PresentationReadiness
    
    # Recommendations
    priority_improvements: List[str]
    quick_fixes: List[str]
    long_term_suggestions: List[str]
    
    # Metadata
    analysis_confidence: float  # 0-1
    processing_time: float
    word_count: int
    section_count: int


class IntelligenceEngine:
    """
    Advanced document intelligence engine with ML-based analysis capabilities.
    
    Provides comprehensive document analysis including language detection,
    quality assessment, content gap analysis, and presentation readiness evaluation.
    """
    
    def __init__(self):
        """Initialize the intelligence engine."""
        self.logger = structlog.get_logger(__name__)
        self._initialize_language_models()
        self._initialize_quality_models()
        self._initialize_style_patterns()
        
    def _initialize_language_models(self) -> None:
        """Initialize language detection models and patterns."""
        # Common words for different languages (simplified approach)
        self.language_patterns = {
            LanguageCode.ENGLISH: {
                'common_words': {'the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'you', 'that'},
                'patterns': [r'\bthe\b', r'\band\b', r'\bof\b', r'\bto\b', r'\ba\b'],
                'stopwords': {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i'}
            },
            LanguageCode.SPANISH: {
                'common_words': {'el', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no'},
                'patterns': [r'\bel\b', r'\bde\b', r'\bque\b', r'\by\b', r'\ba\b'],
                'stopwords': {'el', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no'}
            },
            LanguageCode.FRENCH: {
                'common_words': {'le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir'},
                'patterns': [r'\ble\b', r'\bde\b', r'\bet\b', r'\bà\b', r'\bun\b'],
                'stopwords': {'le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir'}
            },
            LanguageCode.GERMAN: {
                'common_words': {'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'},
                'patterns': [r'\bder\b', r'\bdie\b', r'\bund\b', r'\bin\b', r'\bden\b'],
                'stopwords': {'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'}
            }
        }
        
    def _initialize_quality_models(self) -> None:
        """Initialize quality assessment models and thresholds."""
        self.quality_thresholds = {
            'readability': {'excellent': 80, 'good': 60, 'fair': 40, 'poor': 20},
            'coherence': {'excellent': 85, 'good': 70, 'fair': 50, 'poor': 30},
            'academic_tone': {'excellent': 90, 'good': 75, 'fair': 55, 'poor': 35},
            'citation_quality': {'excellent': 85, 'good': 70, 'fair': 50, 'poor': 30},
            'completeness': {'excellent': 95, 'good': 80, 'fair': 60, 'poor': 40}
        }
        
    def _initialize_style_patterns(self) -> None:
        """Initialize academic writing style patterns."""
        self.academic_patterns = {
            'passive_voice': [
                r'\b(?:is|are|was|were|been|being)\s+\w*ed\b',
                r'\b(?:is|are|was|were)\s+(?:being\s+)?\w*ed\b'
            ],
            'hedging_language': [
                r'\b(?:may|might|could|would|should|possibly|potentially|likely)\b',
                r'\b(?:suggest|indicate|appear|seem|tend)\b'
            ],
            'formal_connectors': [
                r'\b(?:however|therefore|furthermore|moreover|nevertheless|consequently)\b',
                r'\b(?:in addition|on the other hand|in contrast|as a result)\b'
            ],
            'weak_language': [
                r'\b(?:very|really|quite|rather|pretty|somewhat|fairly)\b',
                r'\b(?:I think|I believe|I feel|in my opinion)\b'
            ],
            'nominalizations': [
                r'\b\w+(?:tion|sion|ment|ance|ence|ity|ness)\b'
            ]
        }
        
        self.section_keywords = {
            SectionType.ABSTRACT: ['abstract', 'summary', 'overview'],
            SectionType.INTRODUCTION: ['introduction', 'background', 'motivation'],
            SectionType.LITERATURE_REVIEW: ['literature review', 'related work', 'previous work'],
            SectionType.METHODOLOGY: ['methodology', 'methods', 'approach', 'experimental design'],
            SectionType.RESULTS: ['results', 'findings', 'outcomes', 'analysis'],
            SectionType.DISCUSSION: ['discussion', 'interpretation', 'implications'],
            SectionType.CONCLUSION: ['conclusion', 'conclusions', 'summary', 'final remarks'],
            SectionType.REFERENCES: ['references', 'bibliography', 'works cited']
        }

    async def analyze_document(
        self, 
        processing_result: ProcessingResult,
        document_metadata: Optional[DocumentMetadata] = None
    ) -> DocumentIntelligenceResult:
        """
        Perform comprehensive intelligence analysis on a document.
        
        Args:
            processing_result: The processed document result
            document_metadata: Optional document metadata
            
        Returns:
            Complete intelligence analysis result
        """
        start_time = time.time()
        
        try:
            self.logger.info("Starting document intelligence analysis", 
                           document_id=processing_result.document_id)
            
            # Extract text content for analysis
            text_content = self._extract_text_content(processing_result)
            
            # Perform core analysis
            language_detection = await self._detect_language(text_content)
            document_type = await self._classify_document_type(processing_result)
            quality_metrics = await self._assess_quality(processing_result, text_content)
            
            # Content analysis
            missing_sections = await self._identify_missing_sections(processing_result)
            content_gaps = await self._analyze_content_gaps(processing_result)
            writing_issues = await self._identify_writing_issues(text_content, processing_result)
            
            # Specialized analysis
            citation_analysis = await self._analyze_citations(processing_result)
            coherence_analysis = await self._analyze_coherence(processing_result, text_content)
            presentation_readiness = await self._assess_presentation_readiness(processing_result)
            
            # Generate recommendations
            priority_improvements = self._generate_priority_improvements(
                quality_metrics, missing_sections, writing_issues
            )
            quick_fixes = self._generate_quick_fixes(writing_issues)
            long_term_suggestions = self._generate_long_term_suggestions(
                content_gaps, quality_metrics
            )
            
            processing_time = time.time() - start_time
            
            result = DocumentIntelligenceResult(
                document_id=processing_result.document_id,
                analysis_timestamp=datetime.utcnow().isoformat(),
                language_detection=language_detection,
                document_type=document_type,
                quality_metrics=quality_metrics,
                missing_sections=missing_sections,
                content_gaps=content_gaps,
                writing_issues=writing_issues,
                citation_analysis=citation_analysis,
                coherence_analysis=coherence_analysis,
                presentation_readiness=presentation_readiness,
                priority_improvements=priority_improvements,
                quick_fixes=quick_fixes,
                long_term_suggestions=long_term_suggestions,
                analysis_confidence=self._calculate_analysis_confidence(processing_result),
                processing_time=processing_time,
                word_count=len(text_content.split()),
                section_count=len(processing_result.sections)
            )
            
            self.logger.info("Document intelligence analysis completed",
                           document_id=processing_result.document_id,
                           processing_time=processing_time)
            
            return result
            
        except Exception as e:
            self.logger.error("Error in document intelligence analysis",
                            document_id=processing_result.document_id,
                            error=str(e))
            raise

    async def _detect_language(self, text_content: str) -> LanguageDetectionResult:
        """
        Detect the primary language of the document with confidence scoring.
        
        Args:
            text_content: Text content to analyze
            
        Returns:
            Language detection result with confidence scores
        """
        if not text_content or len(text_content.strip()) < 50:
            return LanguageDetectionResult(
                primary_language=LanguageCode.UNKNOWN,
                confidence=0.0,
                evidence=["Insufficient text for reliable detection"]
            )
        
        # Clean and prepare text
        clean_text = re.sub(r'[^\w\s]', ' ', text_content.lower())
        words = clean_text.split()
        
        if len(words) < 10:
            return LanguageDetectionResult(
                primary_language=LanguageCode.UNKNOWN,
                confidence=0.0,
                evidence=["Too few words for reliable detection"]
            )
        
        # Calculate language scores
        language_scores = {}
        total_words = len(words)
        
        for lang_code, lang_data in self.language_patterns.items():
            if lang_code == LanguageCode.UNKNOWN:
                continue
                
            # Count common words
            common_word_matches = sum(1 for word in words if word in lang_data['common_words'])
            common_word_score = common_word_matches / total_words
            
            # Count pattern matches
            pattern_matches = 0
            for pattern in lang_data['patterns']:
                pattern_matches += len(re.findall(pattern, clean_text))
            pattern_score = min(pattern_matches / total_words, 1.0)
            
            # Calculate stopword ratio
            stopword_matches = sum(1 for word in words if word in lang_data['stopwords'])
            stopword_score = stopword_matches / total_words
            
            # Combined score
            combined_score = (common_word_score * 0.4 + pattern_score * 0.3 + stopword_score * 0.3)
            language_scores[lang_code] = combined_score
        
        # Find primary language
        if not language_scores:
            primary_language = LanguageCode.UNKNOWN
            confidence = 0.0
        else:
            primary_language = max(language_scores.items(), key=lambda x: x[1])[0]
            confidence = language_scores[primary_language]
        
        # Calculate secondary languages
        secondary_languages = [
            (lang, score) for lang, score in sorted(language_scores.items(), 
                                                  key=lambda x: x[1], reverse=True)[1:3]
            if score > 0.1
        ]
        
        # Calculate mixed language score
        sorted_scores = sorted(language_scores.values(), reverse=True)
        mixed_language_score = 0.0
        if len(sorted_scores) > 1 and sorted_scores[0] > 0:
            mixed_language_score = sorted_scores[1] / sorted_scores[0]
        
        # Generate evidence
        evidence = []
        if confidence > 0.7:
            evidence.append(f"Strong {primary_language.value} language indicators")
        elif confidence > 0.4:
            evidence.append(f"Moderate {primary_language.value} language indicators")
        else:
            evidence.append("Weak language indicators")
            
        if mixed_language_score > 0.3:
            evidence.append("Mixed language content detected")
        
        return LanguageDetectionResult(
            primary_language=primary_language,
            confidence=confidence,
            secondary_languages=secondary_languages,
            mixed_language_score=mixed_language_score,
            evidence=evidence
        )

    async def _classify_document_type(self, processing_result: ProcessingResult) -> DocumentType:
        """
        Classify the document type based on structure and content.
        
        Args:
            processing_result: The processed document result
            
        Returns:
            Classified document type
        """
        # Extract section titles for analysis
        section_titles = []
        for section in processing_result.sections:
            if section.title:
                section_titles.append(section.title.lower())
        
        # Extract heading text
        heading_text = []
        for element in processing_result.elements:
            if isinstance(element, HeadingElement):
                heading_text.append(element.text.lower())
        
        all_titles = section_titles + heading_text
        title_text = " ".join(all_titles)
        
        # Classification patterns
        classification_patterns = {
            DocumentType.THESIS: [
                r'\bthesis\b', r'\bdissertation\b', r'\bchapter\b',
                r'\bcommittee\b', r'\badvisor\b', r'\bdefense\b'
            ],
            DocumentType.JOURNAL_ARTICLE: [
                r'\babstract\b', r'\bintroduction\b', r'\bmethodology\b',
                r'\bresults\b', r'\bdiscussion\b', r'\bconclusion\b'
            ],
            DocumentType.CONFERENCE_PAPER: [
                r'\bconference\b', r'\bproceedings\b', r'\bworkshop\b',
                r'\bsymposium\b', r'\bacm\b', r'\bieee\b'
            ],
            DocumentType.TECHNICAL_REPORT: [
                r'\breport\b', r'\btechnical\b', r'\bspecification\b',
                r'\banalysis\b', r'\bevaluation\b'
            ],
            DocumentType.REVIEW_PAPER: [
                r'\breview\b', r'\bsurvey\b', r'\bstate.of.the.art\b',
                r'\bliterature.review\b', r'\bsystematic.review\b'
            ]
        }
        
        # Score each document type
        type_scores = {}
        for doc_type, patterns in classification_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, title_text))
                score += matches
            type_scores[doc_type] = score
        
        # Additional heuristics based on document structure
        section_count = len(processing_result.sections)
        element_count = len(processing_result.elements)
        
        # Adjust scores based on structure
        if section_count > 10:  # Likely thesis/dissertation
            type_scores[DocumentType.THESIS] += 2
        
        if any('imrad' in title.lower() or 'abstract' in title.lower() for title in all_titles):
            type_scores[DocumentType.JOURNAL_ARTICLE] += 3
            type_scores[DocumentType.CONFERENCE_PAPER] += 2
        
        # Determine final classification
        if not type_scores or max(type_scores.values()) == 0:
            return DocumentType.UNKNOWN
        
        return max(type_scores.items(), key=lambda x: x[1])[0]

    async def _assess_quality(
        self, 
        processing_result: ProcessingResult, 
        text_content: str
    ) -> QualityMetrics:
        """
        Assess overall document quality with multiple metrics.
        
        Args:
            processing_result: The processed document result
            text_content: Raw text content
            
        Returns:
            Comprehensive quality metrics
        """
        # Calculate individual quality scores
        readability_score = self._calculate_readability_score(text_content)
        coherence_score = self._calculate_coherence_score(processing_result, text_content)
        completeness_score = self._calculate_completeness_score(processing_result)
        academic_tone_score = self._calculate_academic_tone_score(text_content)
        citation_quality_score = self._calculate_citation_quality_score(processing_result)
        structure_score = self._calculate_structure_score(processing_result)
        clarity_score = self._calculate_clarity_score(text_content)
        conciseness_score = self._calculate_conciseness_score(text_content)
        
        # Calculate overall score (weighted average)
        weights = {
            'readability': 0.15,
            'coherence': 0.20,
            'completeness': 0.15,
            'academic_tone': 0.15,
            'citation_quality': 0.10,
            'structure': 0.10,
            'clarity': 0.10,
            'conciseness': 0.05
        }
        
        overall_score = (
            readability_score * weights['readability'] +
            coherence_score * weights['coherence'] +
            completeness_score * weights['completeness'] +
            academic_tone_score * weights['academic_tone'] +
            citation_quality_score * weights['citation_quality'] +
            structure_score * weights['structure'] +
            clarity_score * weights['clarity'] +
            conciseness_score * weights['conciseness']
        )
        
        # Determine quality level
        if overall_score >= 90:
            quality_level = QualityLevel.EXCELLENT
        elif overall_score >= 70:
            quality_level = QualityLevel.GOOD
        elif overall_score >= 50:
            quality_level = QualityLevel.FAIR
        elif overall_score >= 30:
            quality_level = QualityLevel.POOR
        else:
            quality_level = QualityLevel.CRITICAL
        
        return QualityMetrics(
            overall_score=overall_score,
            readability_score=readability_score,
            coherence_score=coherence_score,
            completeness_score=completeness_score,
            academic_tone_score=academic_tone_score,
            citation_quality_score=citation_quality_score,
            structure_score=structure_score,
            clarity_score=clarity_score,
            conciseness_score=conciseness_score,
            quality_level=quality_level
        )

    def _calculate_readability_score(self, text_content: str) -> float:
        """Calculate readability score using multiple metrics."""
        if not text_content or len(text_content.strip()) < 100:
            return 0.0
        
        # Basic text statistics
        sentences = re.split(r'[.!?]+', text_content)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = text_content.split()
        syllables = sum(self._count_syllables(word) for word in words)
        
        if not sentences or not words:
            return 0.0
        
        # Calculate metrics
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = syllables / len(words)
        
        # Flesch Reading Ease (adapted for academic content)
        flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        flesch_score = max(0, min(100, flesch_score))
        
        # Academic readability adjustments
        # Academic texts typically have lower Flesch scores, so we adjust the scale
        if flesch_score >= 30:  # Good for academic content
            readability_score = 80 + (flesch_score - 30) * 0.5
        elif flesch_score >= 10:  # Acceptable for academic content
            readability_score = 50 + (flesch_score - 10) * 1.5
        else:  # Too complex even for academic content
            readability_score = flesch_score * 5
        
        return min(100, max(0, readability_score))

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified approach)."""
        word = word.lower().strip(string.punctuation)
        if not word:
            return 0
        
        # Count vowel groups
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent 'e'
        if word.endswith('e'):
            syllable_count -= 1
        
        # Every word has at least one syllable
        return max(1, syllable_count)

    def _calculate_coherence_score(
        self, 
        processing_result: ProcessingResult, 
        text_content: str
    ) -> float:
        """Calculate document coherence score."""
        # Extract paragraphs from sections
        paragraphs = []
        for section in processing_result.sections:
            section_text = ""
            for element in section.elements:
                if isinstance(element, TextElement):
                    section_text += element.text + " "
            
            # Split into paragraphs
            section_paragraphs = [p.strip() for p in section_text.split('\n\n') if p.strip()]
            paragraphs.extend(section_paragraphs)
        
        if len(paragraphs) < 2:
            return 50.0  # Neutral score for insufficient content
        
        # Calculate transition quality
        transition_words = [
            'however', 'therefore', 'furthermore', 'moreover', 'nevertheless',
            'consequently', 'additionally', 'similarly', 'in contrast',
            'on the other hand', 'as a result', 'in addition', 'finally'
        ]
        
        transition_count = 0
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            for transition in transition_words:
                if transition in paragraph_lower:
                    transition_count += 1
                    break
        
        transition_ratio = transition_count / len(paragraphs)
        
        # Calculate topic consistency (simplified)
        # Look for repeated key terms across paragraphs
        all_words = []
        for paragraph in paragraphs:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', paragraph.lower())
            all_words.extend(words)
        
        word_freq = Counter(all_words)
        common_words = [word for word, freq in word_freq.most_common(20) if freq > 1]
        
        topic_consistency = 0.0
        if common_words:
            consistency_scores = []
            for paragraph in paragraphs:
                paragraph_lower = paragraph.lower()
                common_in_paragraph = sum(1 for word in common_words if word in paragraph_lower)
                consistency_scores.append(common_in_paragraph / len(common_words))
            topic_consistency = statistics.mean(consistency_scores)
        
        # Combine scores
        coherence_score = (transition_ratio * 0.4 + topic_consistency * 0.6) * 100
        return min(100, max(0, coherence_score))

    def _calculate_completeness_score(self, processing_result: ProcessingResult) -> float:
        """Calculate document completeness based on expected sections."""
        expected_sections = {
            SectionType.TITLE: 10,
            SectionType.ABSTRACT: 15,
            SectionType.INTRODUCTION: 20,
            SectionType.METHODOLOGY: 20,
            SectionType.RESULTS: 15,
            SectionType.DISCUSSION: 10,
            SectionType.CONCLUSION: 5,
            SectionType.REFERENCES: 5
        }
        
        # Identify present sections
        present_sections = set()
        for section in processing_result.sections:
            section_type = self._classify_section_type(section.title or "")
            present_sections.add(section_type)
        
        # Calculate completeness score
        total_weight = sum(expected_sections.values())
        achieved_weight = sum(
            weight for section_type, weight in expected_sections.items()
            if section_type in present_sections
        )
        
        completeness_score = (achieved_weight / total_weight) * 100
        return completeness_score

    def _classify_section_type(self, section_title: str) -> SectionType:
        """Classify section type based on title."""
        if not section_title:
            return SectionType.UNKNOWN
        
        title_lower = section_title.lower()
        
        for section_type, keywords in self.section_keywords.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return section_type
        
        return SectionType.UNKNOWN

    def _calculate_academic_tone_score(self, text_content: str) -> float:
        """Calculate academic tone score."""
        if not text_content:
            return 0.0
        
        text_lower = text_content.lower()
        word_count = len(text_content.split())
        
        # Positive academic indicators
        formal_connectors = sum(
            len(re.findall(pattern, text_lower))
            for pattern in self.academic_patterns['formal_connectors']
        )
        
        hedging_language = sum(
            len(re.findall(pattern, text_lower))
            for pattern in self.academic_patterns['hedging_language']
        )
        
        nominalizations = len(re.findall(
            self.academic_patterns['nominalizations'][0], text_lower
        ))
        
        # Negative indicators (informal language)
        weak_language = sum(
            len(re.findall(pattern, text_lower))
            for pattern in self.academic_patterns['weak_language']
        )
        
        contractions = len(re.findall(r"\b\w+'\w+\b", text_content))
        
        # Calculate scores
        positive_score = (formal_connectors + hedging_language + nominalizations) / word_count
        negative_score = (weak_language + contractions) / word_count
        
        # Academic tone score (0-100)
        tone_score = min(100, max(0, (positive_score * 100) - (negative_score * 50)))
        return tone_score

    def _calculate_citation_quality_score(self, processing_result: ProcessingResult) -> float:
        """Calculate citation quality score."""
        citations = [
            element for element in processing_result.elements
            if isinstance(element, CitationElement)
        ]
        
        references = [
            element for element in processing_result.elements
            if isinstance(element, ReferenceElement)
        ]
        
        if not citations and not references:
            return 30.0  # Low score for no citations
        
        # Basic citation metrics
        total_citations = len(citations)
        total_references = len(references)
        
        # Citation density (citations per 1000 words)
        total_words = sum(
            len(element.text.split()) for element in processing_result.elements
            if isinstance(element, TextElement)
        )
        
        citation_density = (total_citations / max(total_words, 1)) * 1000
        
        # Quality indicators
        format_consistency = 0.8  # Assume good formatting (would need detailed analysis)
        recency_score = 0.7  # Assume reasonable recency (would need date analysis)
        authority_score = 0.6  # Assume decent authority (would need source analysis)
        
        # Calculate overall citation quality
        base_score = min(80, citation_density * 10)  # Up to 80 points for density
        quality_bonus = (format_consistency + recency_score + authority_score) / 3 * 20
        
        citation_quality_score = base_score + quality_bonus
        return min(100, citation_quality_score)

    def _calculate_structure_score(self, processing_result: ProcessingResult) -> float:
        """Calculate document structure score."""
        sections = processing_result.sections
        
        if not sections:
            return 0.0
        
        # Check for logical section order
        section_types = []
        for section in sections:
            section_type = self._classify_section_type(section.title or "")
            section_types.append(section_type)
        
        # Expected order for academic papers
        expected_order = [
            SectionType.TITLE,
            SectionType.ABSTRACT,
            SectionType.INTRODUCTION,
            SectionType.LITERATURE_REVIEW,
            SectionType.METHODOLOGY,
            SectionType.RESULTS,
            SectionType.DISCUSSION,
            SectionType.CONCLUSION,
            SectionType.REFERENCES
        ]
        
        # Calculate order score
        order_score = 0.0
        last_expected_index = -1
        
        for section_type in section_types:
            if section_type in expected_order:
                current_index = expected_order.index(section_type)
                if current_index > last_expected_index:
                    order_score += 1
                    last_expected_index = current_index
        
        order_score = (order_score / len(section_types)) * 100
        
        # Check section balance
        section_lengths = [
            sum(len(element.text.split()) for element in section.elements
                if isinstance(element, TextElement))
            for section in sections
        ]
        
        if section_lengths:
            length_variance = statistics.variance(section_lengths) if len(section_lengths) > 1 else 0
            avg_length = statistics.mean(section_lengths)
            balance_score = max(0, 100 - (length_variance / max(avg_length, 1)) * 10)
        else:
            balance_score = 50.0
        
        # Combine scores
        structure_score = (order_score * 0.7 + balance_score * 0.3)
        return min(100, max(0, structure_score))

    def _calculate_clarity_score(self, text_content: str) -> float:
        """Calculate text clarity score."""
        if not text_content:
            return 0.0
        
        # Sentence length analysis
        sentences = re.split(r'[.!?]+', text_content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        avg_sentence_length = statistics.mean(sentence_lengths)
        
        # Ideal academic sentence length is 15-25 words
        if 15 <= avg_sentence_length <= 25:
            length_score = 100
        elif 10 <= avg_sentence_length < 15 or 25 < avg_sentence_length <= 35:
            length_score = 80
        else:
            length_score = max(0, 100 - abs(avg_sentence_length - 20) * 2)
        
        # Vocabulary complexity
        words = text_content.split()
        complex_words = [word for word in words if len(word) > 6]
        complexity_ratio = len(complex_words) / len(words) if words else 0
        
        # Academic writing should have moderate complexity (30-50%)
        if 0.3 <= complexity_ratio <= 0.5:
            complexity_score = 100
        else:
            complexity_score = max(0, 100 - abs(complexity_ratio - 0.4) * 200)
        
        # Combine scores
        clarity_score = (length_score * 0.6 + complexity_score * 0.4)
        return clarity_score

    def _calculate_conciseness_score(self, text_content: str) -> float:
        """Calculate conciseness score."""
        if not text_content:
            return 0.0
        
        # Look for redundant phrases and wordy constructions
        wordy_patterns = [
            r'\bin order to\b',
            r'\bdue to the fact that\b',
            r'\bit is important to note that\b',
            r'\bit should be mentioned that\b',
            r'\bit is worth noting that\b',
            r'\bthe fact that\b',
            r'\bin the event that\b',
            r'\bfor the purpose of\b'
        ]
        
        words = text_content.split()
        word_count = len(words)
        
        # Count wordy constructions
        wordy_count = sum(
            len(re.findall(pattern, text_content.lower()))
            for pattern in wordy_patterns
        )
        
        # Calculate redundancy ratio
        redundancy_ratio = wordy_count / max(word_count / 100, 1)  # Per 100 words
        
        # Conciseness score (lower redundancy = higher score)
        conciseness_score = max(0, 100 - redundancy_ratio * 10)
        return conciseness_score

    async def _identify_missing_sections(
        self, 
        processing_result: ProcessingResult
    ) -> List[MissingSection]:
        """Identify missing academic sections."""
        present_sections = set()
        for section in processing_result.sections:
            section_type = self._classify_section_type(section.title or "")
            present_sections.add(section_type)
        
        # Define required and recommended sections
        required_sections = {
            SectionType.TITLE: "Document title page",
            SectionType.ABSTRACT: "Abstract or executive summary",
            SectionType.INTRODUCTION: "Introduction section",
            SectionType.CONCLUSION: "Conclusion section"
        }
        
        recommended_sections = {
            SectionType.METHODOLOGY: "Methodology or approach section",
            SectionType.RESULTS: "Results or findings section",
            SectionType.DISCUSSION: "Discussion or analysis section",
            SectionType.REFERENCES: "References or bibliography"
        }
        
        missing_sections = []
        
        # Check required sections
        for section_type, description in required_sections.items():
            if section_type not in present_sections:
                missing_sections.append(MissingSection(
                    section_type=section_type,
                    importance="required",
                    description=f"Missing {description}",
                    recommendation=f"Add a {section_type.value} section to provide {description.lower()}",
                    expected_content=self._get_expected_content(section_type)
                ))
        
        # Check recommended sections
        for section_type, description in recommended_sections.items():
            if section_type not in present_sections:
                missing_sections.append(MissingSection(
                    section_type=section_type,
                    importance="recommended",
                    description=f"Missing {description}",
                    recommendation=f"Consider adding a {section_type.value} section to include {description.lower()}",
                    expected_content=self._get_expected_content(section_type)
                ))
        
        return missing_sections

    def _get_expected_content(self, section_type: SectionType) -> List[str]:
        """Get expected content for a section type."""
        content_expectations = {
            SectionType.TITLE: [
                "Document title",
                "Author names and affiliations",
                "Date of publication",
                "Institution or organization"
            ],
            SectionType.ABSTRACT: [
                "Background and motivation",
                "Research objectives",
                "Methodology overview",
                "Key findings",
                "Conclusions and implications"
            ],
            SectionType.INTRODUCTION: [
                "Problem statement",
                "Research context",
                "Literature background",
                "Research objectives",
                "Document structure overview"
            ],
            SectionType.METHODOLOGY: [
                "Research approach",
                "Data collection methods",
                "Analysis procedures",
                "Tools and instruments",
                "Validation methods"
            ],
            SectionType.RESULTS: [
                "Key findings",
                "Data presentation",
                "Statistical analysis",
                "Visual representations",
                "Result interpretation"
            ],
            SectionType.DISCUSSION: [
                "Result interpretation",
                "Comparison with literature",
                "Implications",
                "Limitations",
                "Future work suggestions"
            ],
            SectionType.CONCLUSION: [
                "Summary of findings",
                "Research contributions",
                "Practical implications",
                "Recommendations",
                "Final remarks"
            ],
            SectionType.REFERENCES: [
                "Cited sources",
                "Consistent citation format",
                "Comprehensive bibliography",
                "Recent and relevant sources"
            ]
        }
        
        return content_expectations.get(section_type, [])

    async def _analyze_content_gaps(
        self, 
        processing_result: ProcessingResult
    ) -> List[ContentGap]:
        """Analyze content gaps within existing sections."""
        content_gaps = []
        
        for section in processing_result.sections:
            section_type = self._classify_section_type(section.title or "")
            section_text = ""
            
            # Extract section text
            for element in section.elements:
                if isinstance(element, TextElement):
                    section_text += element.text + " "
            
            # Analyze gaps based on section type
            section_gaps = self._identify_section_gaps(section_type, section_text)
            content_gaps.extend(section_gaps)
        
        return content_gaps

    def _identify_section_gaps(self, section_type: SectionType, section_text: str) -> List[ContentGap]:
        """Identify gaps in a specific section."""
        gaps = []
        text_lower = section_text.lower()
        word_count = len(section_text.split())
        
        if section_type == SectionType.INTRODUCTION:
            # Check for problem statement
            problem_indicators = ['problem', 'issue', 'challenge', 'gap', 'need']
            if not any(indicator in text_lower for indicator in problem_indicators):
                gaps.append(ContentGap(
                    section=section_type,
                    gap_type="missing_problem_statement",
                    description="Introduction lacks clear problem statement",
                    suggestion="Add a clear statement of the problem or research gap",
                    priority="high",
                    examples=["The main problem addressed in this research is...", 
                             "This study addresses the gap in..."]
                ))
            
            # Check for objectives
            objective_indicators = ['objective', 'goal', 'aim', 'purpose', 'research question']
            if not any(indicator in text_lower for indicator in objective_indicators):
                gaps.append(ContentGap(
                    section=section_type,
                    gap_type="missing_objectives",
                    description="Introduction lacks clear research objectives",
                    suggestion="Include specific research objectives or questions",
                    priority="high",
                    examples=["The objectives of this study are...", 
                             "This research aims to..."]
                ))
        
        elif section_type == SectionType.METHODOLOGY:
            # Check for data collection methods
            data_indicators = ['data', 'sample', 'participant', 'measurement', 'collection']
            if not any(indicator in text_lower for indicator in data_indicators):
                gaps.append(ContentGap(
                    section=section_type,
                    gap_type="missing_data_description",
                    description="Methodology lacks data collection details",
                    suggestion="Describe data sources, collection methods, and sample characteristics",
                    priority="high",
                    examples=["Data was collected through...", 
                             "The sample consisted of..."]
                ))
            
            # Check for analysis methods
            analysis_indicators = ['analysis', 'statistical', 'procedure', 'method', 'technique']
            if not any(indicator in text_lower for indicator in analysis_indicators):
                gaps.append(ContentGap(
                    section=section_type,
                    gap_type="missing_analysis_methods",
                    description="Methodology lacks analysis procedures",
                    suggestion="Describe analytical methods and procedures used",
                    priority="medium",
                    examples=["Analysis was conducted using...", 
                             "Statistical procedures included..."]
                ))
        
        elif section_type == SectionType.RESULTS:
            # Check for quantitative results
            if word_count > 200:  # Only for substantial results sections
                number_pattern = r'\b\d+\.?\d*\b'
                numbers = re.findall(number_pattern, section_text)
                if len(numbers) < 5:
                    gaps.append(ContentGap(
                        section=section_type,
                        gap_type="insufficient_quantitative_data",
                        description="Results section lacks sufficient quantitative data",
                        suggestion="Include more specific numerical results and statistics",
                        priority="medium",
                        examples=["The results showed 85% improvement...", 
                                 "Statistical analysis revealed p < 0.05..."]
                    ))
        
        elif section_type == SectionType.DISCUSSION:
            # Check for limitation discussion
            limitation_indicators = ['limitation', 'constraint', 'weakness', 'shortcoming']
            if not any(indicator in text_lower for indicator in limitation_indicators):
                gaps.append(ContentGap(
                    section=section_type,
                    gap_type="missing_limitations",
                    description="Discussion lacks acknowledgment of limitations",
                    suggestion="Include a discussion of study limitations and constraints",
                    priority="medium",
                    examples=["This study has several limitations...", 
                             "The main constraints include..."]
                ))
            
            # Check for future work
            future_indicators = ['future', 'further research', 'next step', 'recommendation']
            if not any(indicator in text_lower for indicator in future_indicators):
                gaps.append(ContentGap(
                    section=section_type,
                    gap_type="missing_future_work",
                    description="Discussion lacks suggestions for future work",
                    suggestion="Include recommendations for future research directions",
                    priority="low",
                    examples=["Future research should focus on...", 
                             "Further investigation is needed..."]
                ))
        
        return gaps

    async def _identify_writing_issues(
        self, 
        text_content: str, 
        processing_result: ProcessingResult
    ) -> List[WritingIssue]:
        """Identify writing issues and provide suggestions."""
        issues = []
        
        # Grammar and style issues
        issues.extend(self._check_grammar_issues(text_content))
        issues.extend(self._check_style_issues(text_content))
        issues.extend(self._check_clarity_issues(text_content))
        issues.extend(self._check_coherence_issues(processing_result))
        issues.extend(self._check_academic_tone_issues(text_content))
        
        return issues

    def _check_grammar_issues(self, text_content: str) -> List[WritingIssue]:
        """Check for common grammar issues."""
        issues = []
        
        # Check for sentence fragments (very basic check)
        sentences = re.split(r'[.!?]+', text_content)
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence and len(sentence.split()) < 3:
                # Possible sentence fragment
                issues.append(WritingIssue(
                    issue_type=WritingIssueType.GRAMMAR,
                    severity="medium",
                    description=f"Possible sentence fragment: '{sentence[:50]}...'",
                    suggestion="Ensure all sentences are complete with subject and predicate",
                    confidence=0.6
                ))
        
        # Check for run-on sentences
        for sentence in sentences:
            if len(sentence.split()) > 40:
                issues.append(WritingIssue(
                    issue_type=WritingIssueType.GRAMMAR,
                    severity="medium",
                    description=f"Very long sentence detected ({len(sentence.split())} words)",
                    suggestion="Consider breaking this sentence into shorter, clearer sentences",
                    confidence=0.8
                ))
        
        return issues

    def _check_style_issues(self, text_content: str) -> List[WritingIssue]:
        """Check for style issues."""
        issues = []
        
        # Check for excessive passive voice
        passive_patterns = self.academic_patterns['passive_voice']
        passive_count = sum(
            len(re.findall(pattern, text_content.lower()))
            for pattern in passive_patterns
        )
        
        total_sentences = len(re.split(r'[.!?]+', text_content))
        if total_sentences > 0:
            passive_ratio = passive_count / total_sentences
            if passive_ratio > 0.4:  # More than 40% passive voice
                issues.append(WritingIssue(
                    issue_type=WritingIssueType.STYLE,
                    severity="medium",
                    description=f"High passive voice usage ({passive_ratio:.1%})",
                    suggestion="Consider using more active voice for clarity and engagement",
                    confidence=0.8
                ))
        
        # Check for weak language
        weak_patterns = self.academic_patterns['weak_language']
        weak_count = sum(
            len(re.findall(pattern, text_content.lower()))
            for pattern in weak_patterns
        )
        
        if weak_count > 0:
            issues.append(WritingIssue(
                issue_type=WritingIssueType.ACADEMIC_TONE,
                severity="low",
                description=f"Use of weak or informal language ({weak_count} instances)",
                suggestion="Replace weak language with more precise, academic terminology",
                confidence=0.7
            ))
        
        return issues

    def _check_clarity_issues(self, text_content: str) -> List[WritingIssue]:
        """Check for clarity issues."""
        issues = []
        
        # Check for overly complex words
        words = re.findall(r'\b[a-zA-Z]+\b', text_content)
        very_long_words = [word for word in words if len(word) > 12]
        
        if len(very_long_words) > len(words) * 0.05:  # More than 5% very long words
            issues.append(WritingIssue(
                issue_type=WritingIssueType.CLARITY,
                severity="low",
                description="High usage of very long words may affect readability",
                suggestion="Consider using shorter, clearer alternatives where appropriate",
                confidence=0.6
            ))
        
        # Check for jargon overuse (simplified check)
        technical_suffixes = ['tion', 'sion', 'ment', 'ance', 'ence', 'ity', 'ness']
        jargon_count = sum(
            len([word for word in words if word.lower().endswith(suffix)])
            for suffix in technical_suffixes
        )
        
        if jargon_count > len(words) * 0.15:  # More than 15% technical terms
            issues.append(WritingIssue(
                issue_type=WritingIssueType.CLARITY,
                severity="low",
                description="High density of technical terminology",
                suggestion="Consider defining technical terms or using simpler alternatives",
                confidence=0.5
            ))
        
        return issues

    def _check_coherence_issues(self, processing_result: ProcessingResult) -> List[WritingIssue]:
        """Check for coherence issues."""
        issues = []
        
        # Check for missing transitions between sections
        for i in range(len(processing_result.sections) - 1):
            current_section = processing_result.sections[i]
            next_section = processing_result.sections[i + 1]
            
            # Get last paragraph of current section
            current_text = ""
            for element in reversed(current_section.elements):
                if isinstance(element, TextElement):
                    current_text = element.text
                    break
            
            # Get first paragraph of next section
            next_text = ""
            for element in next_section.elements:
                if isinstance(element, TextElement):
                    next_text = element.text
                    break
            
            # Check for transition words
            transition_words = [
                'however', 'therefore', 'furthermore', 'moreover', 'nevertheless',
                'consequently', 'additionally', 'similarly', 'in contrast',
                'on the other hand', 'as a result', 'in addition', 'finally'
            ]
            
            has_transition = any(
                word in next_text.lower() for word in transition_words
            )
            
            if not has_transition and len(next_text.split()) > 10:
                issues.append(WritingIssue(
                    issue_type=WritingIssueType.COHERENCE,
                    severity="low",
                    description=f"Abrupt transition between sections",
                    suggestion="Add transitional phrases to improve flow between sections",
                    confidence=0.6
                ))
        
        return issues

    def _check_academic_tone_issues(self, text_content: str) -> List[WritingIssue]:
        """Check for academic tone issues."""
        issues = []
        
        # Check for contractions
        contractions = re.findall(r"\b\w+'\w+\b", text_content)
        if contractions:
            issues.append(WritingIssue(
                issue_type=WritingIssueType.ACADEMIC_TONE,
                severity="medium",
                description=f"Use of contractions in academic text ({len(contractions)} found)",
                suggestion="Expand contractions for formal academic writing",
                confidence=0.9,
                location=f"Examples: {', '.join(contractions[:3])}"
            ))
        
        # Check for first person overuse
        first_person = re.findall(r'\b(I|me|my|we|us|our)\b', text_content, re.IGNORECASE)
        word_count = len(text_content.split())
        
        if len(first_person) > word_count * 0.02:  # More than 2% first person
            issues.append(WritingIssue(
                issue_type=WritingIssueType.ACADEMIC_TONE,
                severity="low",
                description="High usage of first-person pronouns",
                suggestion="Consider using third person or passive voice for more formal tone",
                confidence=0.7
            ))
        
        return issues

    async def _analyze_citations(self, processing_result: ProcessingResult) -> CitationAnalysis:
        """Analyze citation quality and completeness."""
        citations = [
            element for element in processing_result.elements
            if isinstance(element, CitationElement)
        ]
        
        references = [
            element for element in processing_result.elements
            if isinstance(element, ReferenceElement)
        ]
        
        # Basic metrics
        total_citations = len(citations)
        unique_sources = len(set(citation.text for citation in citations)) if citations else 0
        
        # Calculate citation density (citations per page, assuming ~250 words per page)
        total_words = sum(
            len(element.text.split()) for element in processing_result.elements
            if isinstance(element, TextElement)
        )
        estimated_pages = max(1, total_words / 250)
        citation_density = total_citations / estimated_pages
        
        # Assess format consistency (simplified)
        format_consistency = 0.8  # Placeholder - would need detailed format analysis
        
        # Assess recency and authority (simplified)
        recency_score = 0.7  # Placeholder - would need publication date analysis
        authority_score = 0.6  # Placeholder - would need source quality analysis
        completeness_score = 0.75  # Placeholder - would need field completeness analysis
        
        # Generate issues and recommendations
        issues = []
        recommendations = []
        
        if total_citations < 10:
            issues.append("Low number of citations for academic document")
            recommendations.append("Consider adding more supporting citations")
        
        if citation_density < 1:
            issues.append("Low citation density")
            recommendations.append("Increase citation frequency to support claims")
        
        if unique_sources < total_citations * 0.7:
            issues.append("High repetition of sources")
            recommendations.append("Diversify citation sources")
        
        return CitationAnalysis(
            total_citations=total_citations,
            unique_sources=unique_sources,
            citation_density=citation_density,
            format_consistency=format_consistency,
            recency_score=recency_score,
            authority_score=authority_score,
            completeness_score=completeness_score,
            issues=issues,
            recommendations=recommendations
        )

    async def _analyze_coherence(
        self, 
        processing_result: ProcessingResult, 
        text_content: str
    ) -> CoherenceAnalysis:
        """Analyze document coherence and flow."""
        # Extract section texts
        section_texts = {}
        for section in processing_result.sections:
            section_text = ""
            for element in section.elements:
                if isinstance(element, TextElement):
                    section_text += element.text + " "
            section_texts[section.title or f"Section_{len(section_texts)}"] = section_text.strip()
        
        # Analyze transitions between sections
        section_transitions = {}
        section_names = list(section_texts.keys())
        
        for i in range(len(section_names) - 1):
            current_section = section_names[i]
            next_section = section_names[i + 1]
            
            current_text = section_texts[current_section]
            next_text = section_texts[next_section]
            
            # Simple transition quality score
            transition_score = self._calculate_transition_quality(current_text, next_text)
            section_transitions[f"{current_section} -> {next_section}"] = transition_score
        
        # Calculate overall coherence metrics
        overall_coherence = statistics.mean(section_transitions.values()) if section_transitions else 0.5
        
        # Paragraph flow analysis (simplified)
        paragraphs = text_content.split('\n\n')
        paragraph_scores = []
        
        for i in range(len(paragraphs) - 1):
            if i < len(paragraphs) - 1:
                score = self._calculate_transition_quality(paragraphs[i], paragraphs[i + 1])
                paragraph_scores.append(score)
        
        paragraph_flow = statistics.mean(paragraph_scores) if paragraph_scores else 0.5
        
        # Logical progression and topic continuity (simplified)
        logical_progression = min(overall_coherence + 0.1, 1.0)
        topic_continuity = self._calculate_topic_continuity(text_content)
        
        # Identify weak transitions
        weak_transitions = [
            {"transition": trans, "score": score}
            for trans, score in section_transitions.items()
            if score < 0.4
        ]
        
        # Generate improvement suggestions
        improvement_suggestions = []
        if overall_coherence < 0.6:
            improvement_suggestions.append("Improve transitions between major sections")
        if paragraph_flow < 0.5:
            improvement_suggestions.append("Enhance paragraph-to-paragraph flow with better connectors")
        if topic_continuity < 0.6:
            improvement_suggestions.append("Maintain more consistent topic focus throughout sections")
        
        return CoherenceAnalysis(
            overall_coherence=overall_coherence,
            section_transitions=section_transitions,
            paragraph_flow=paragraph_flow,
            logical_progression=logical_progression,
            topic_continuity=topic_continuity,
            weak_transitions=weak_transitions,
            improvement_suggestions=improvement_suggestions
        )

    def _calculate_transition_quality(self, text1: str, text2: str) -> float:
        """Calculate quality of transition between two text segments."""
        if not text1 or not text2:
            return 0.0
        
        # Check for explicit transition words at the beginning of text2
        transition_words = [
            'however', 'therefore', 'furthermore', 'moreover', 'nevertheless',
            'consequently', 'additionally', 'similarly', 'in contrast',
            'on the other hand', 'as a result', 'in addition', 'finally',
            'meanwhile', 'subsequently', 'thus', 'hence'
        ]
        
        text2_start = text2.lower().split()[:10]  # First 10 words
        has_explicit_transition = any(word in transition_words for word in text2_start)
        
        # Check for topic overlap (simplified)
        words1 = set(re.findall(r'\b[a-zA-Z]{4,}\b', text1.lower()))
        words2 = set(re.findall(r'\b[a-zA-Z]{4,}\b', text2.lower()))
        
        if len(words1) == 0 or len(words2) == 0:
            return 0.0
        
        overlap = len(words1.intersection(words2))
        overlap_ratio = overlap / min(len(words1), len(words2))
        
        # Combine scores
        transition_score = 0.0
        if has_explicit_transition:
            transition_score += 0.4
        transition_score += overlap_ratio * 0.6
        
        return min(1.0, transition_score)

    def _calculate_topic_continuity(self, text_content: str) -> float:
        """Calculate topic continuity across the document."""
        # Split into chunks (e.g., paragraphs or sentences)
        chunks = re.split(r'\n\n|\. ', text_content)
        chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) > 50]
        
        if len(chunks) < 2:
            return 1.0
        
        # Extract key terms from each chunk
        chunk_terms = []
        for chunk in chunks:
            terms = set(re.findall(r'\b[a-zA-Z]{4,}\b', chunk.lower()))
            chunk_terms.append(terms)
        
        # Calculate continuity between adjacent chunks
        continuity_scores = []
        for i in range(len(chunk_terms) - 1):
            current_terms = chunk_terms[i]
            next_terms = chunk_terms[i + 1]
            
            if len(current_terms) == 0 or len(next_terms) == 0:
                continuity_scores.append(0.0)
            else:
                overlap = len(current_terms.intersection(next_terms))
                continuity = overlap / min(len(current_terms), len(next_terms))
                continuity_scores.append(continuity)
        
        return statistics.mean(continuity_scores) if continuity_scores else 0.5

    async def _assess_presentation_readiness(
        self, 
        processing_result: ProcessingResult
    ) -> PresentationReadiness:
        """Assess document readiness for presentation conversion."""
        # Count visual elements
        visual_elements = sum(
            1 for element in processing_result.elements
            if element.element_type in [ElementType.IMAGE, ElementType.TABLE, ElementType.EQUATION]
        )
        
        total_elements = len(processing_result.elements)
        visual_ratio = visual_elements / max(total_elements, 1)
        visual_elements_score = min(100, visual_ratio * 200)  # Up to 100 for 50% visual content
        
        # Assess slide adaptability based on structure
        sections = processing_result.sections
        section_count = len(sections)
        
        # Ideal number of sections for slides is 5-15
        if 5 <= section_count <= 15:
            slide_adaptability_score = 100
        elif 3 <= section_count < 5 or 15 < section_count <= 20:
            slide_adaptability_score = 80
        else:
            slide_adaptability_score = max(20, 100 - abs(section_count - 10) * 5)
        
        # Assess content density
        total_words = sum(
            len(element.text.split()) for element in processing_result.elements
            if isinstance(element, TextElement)
        )
        
        words_per_section = total_words / max(section_count, 1)
        
        # Ideal words per section for slides: 100-300 words
        if 100 <= words_per_section <= 300:
            content_density_score = 100
        elif 50 <= words_per_section < 100 or 300 < words_per_section <= 500:
            content_density_score = 80
        else:
            content_density_score = max(20, 100 - abs(words_per_section - 200) / 10)
        
        # Assess structure clarity (based on heading hierarchy)
        headings = [element for element in processing_result.elements 
                   if isinstance(element, HeadingElement)]
        
        heading_levels = [getattr(element, 'level', 1) for element in headings]
        has_clear_hierarchy = len(set(heading_levels)) <= 3 and min(heading_levels) == 1
        structure_clarity_score = 90 if has_clear_hierarchy else 60
        
        # Assess key points identifiability
        bullet_points = len(re.findall(r'^\s*[•\-\*]\s', 
                                     '\n'.join(element.text for element in processing_result.elements
                                             if isinstance(element, TextElement)), 
                                     re.MULTILINE))
        
        numbered_lists = len(re.findall(r'^\s*\d+\.\s', 
                                      '\n'.join(element.text for element in processing_result.elements
                                              if isinstance(element, TextElement)), 
                                      re.MULTILINE))
        
        list_density = (bullet_points + numbered_lists) / max(section_count, 1)
        key_points_identifiable = min(100, list_density * 25)  # Up to 100 for 4 lists per section
        
        # Assess narrative flow
        narrative_indicators = ['first', 'second', 'third', 'finally', 'next', 'then', 'therefore']
        narrative_count = sum(
            len(re.findall(rf'\b{indicator}\b', 
                         '\n'.join(element.text for element in processing_result.elements
                                 if isinstance(element, TextElement)).lower()))
            for indicator in narrative_indicators
        )
        
        narrative_flow_score = min(100, narrative_count * 5)  # Up to 100 for 20 narrative indicators
        
        # Calculate overall readiness
        weights = {
            'visual_elements': 0.15,
            'slide_adaptability': 0.25,
            'content_density': 0.20,
            'structure_clarity': 0.20,
            'key_points': 0.10,
            'narrative_flow': 0.10
        }
        
        overall_readiness = (
            visual_elements_score * weights['visual_elements'] +
            slide_adaptability_score * weights['slide_adaptability'] +
            content_density_score * weights['content_density'] +
            structure_clarity_score * weights['structure_clarity'] +
            key_points_identifiable * weights['key_points'] +
            narrative_flow_score * weights['narrative_flow']
        )
        
        # Generate recommendations
        recommendations = []
        slide_suggestions = []
        
        if visual_elements_score < 50:
            recommendations.append("Add more visual elements (charts, diagrams, images)")
            slide_suggestions.append({
                "type": "visual_enhancement",
                "description": "Create visual representations of key concepts",
                "priority": "high"
            })
        
        if content_density_score < 60:
            if words_per_section > 400:
                recommendations.append("Break down dense sections into smaller, digestible parts")
                slide_suggestions.append({
                    "type": "content_chunking",
                    "description": "Split large sections into multiple slides",
                    "priority": "medium"
                })
            else:
                recommendations.append("Expand sections with more detailed content")
        
        if key_points_identifiable < 60:
            recommendations.append("Add more bullet points and numbered lists for key information")
            slide_suggestions.append({
                "type": "key_points",
                "description": "Convert prose to bullet points for better slide format",
                "priority": "high"
            })
        
        if structure_clarity_score < 70:
            recommendations.append("Improve heading hierarchy and section organization")
        
        return PresentationReadiness(
            overall_readiness=overall_readiness,
            visual_elements_score=visual_elements_score,
            slide_adaptability_score=slide_adaptability_score,
            content_density_score=content_density_score,
            structure_clarity_score=structure_clarity_score,
            key_points_identifiable=key_points_identifiable,
            narrative_flow_score=narrative_flow_score,
            recommendations=recommendations,
            slide_suggestions=slide_suggestions
        )

    def _generate_priority_improvements(
        self, 
        quality_metrics: QualityMetrics,
        missing_sections: List[MissingSection],
        writing_issues: List[WritingIssue]
    ) -> List[str]:
        """Generate priority improvement recommendations."""
        improvements = []
        
        # Critical quality issues
        if quality_metrics.overall_score < 50:
            improvements.append("Overall document quality needs significant improvement")
        
        # Missing required sections
        required_missing = [
            section for section in missing_sections 
            if section.importance == "required"
        ]
        
        if required_missing:
            improvements.append(
                f"Add missing required sections: {', '.join(s.section_type.value for s in required_missing)}"
            )
        
        # High-severity writing issues
        critical_issues = [
            issue for issue in writing_issues 
            if issue.severity in ["high", "critical"]
        ]
        
        if critical_issues:
            improvements.append(
                f"Address {len(critical_issues)} critical writing issues"
            )
        
        # Specific quality metrics below threshold
        if quality_metrics.readability_score < 40:
            improvements.append("Improve document readability and sentence structure")
        
        if quality_metrics.coherence_score < 50:
            improvements.append("Enhance document coherence and logical flow")
        
        if quality_metrics.academic_tone_score < 60:
            improvements.append("Adopt more formal academic writing tone")
        
        return improvements[:5]  # Return top 5 priorities

    def _generate_quick_fixes(self, writing_issues: List[WritingIssue]) -> List[str]:
        """Generate quick fix recommendations."""
        quick_fixes = []
        
        # Group issues by type
        issue_groups = defaultdict(list)
        for issue in writing_issues:
            issue_groups[issue.issue_type].append(issue)
        
        # Generate fixes for common issues
        if WritingIssueType.GRAMMAR in issue_groups:
            quick_fixes.append("Review and fix sentence fragments and run-on sentences")
        
        if WritingIssueType.ACADEMIC_TONE in issue_groups:
            tone_issues = issue_groups[WritingIssueType.ACADEMIC_TONE]
            if any("contraction" in issue.description.lower() for issue in tone_issues):
                quick_fixes.append("Expand contractions (don't → do not, can't → cannot)")
            
            if any("first person" in issue.description.lower() for issue in tone_issues):
                quick_fixes.append("Reduce first-person pronouns, use third person or passive voice")
        
        if WritingIssueType.STYLE in issue_groups:
            style_issues = issue_groups[WritingIssueType.STYLE]
            if any("passive voice" in issue.description.lower() for issue in style_issues):
                quick_fixes.append("Convert some passive voice sentences to active voice")
        
        if WritingIssueType.CLARITY in issue_groups:
            quick_fixes.append("Replace overly complex words with clearer alternatives")
        
        return quick_fixes[:7]  # Return top 7 quick fixes

    def _generate_long_term_suggestions(
        self, 
        content_gaps: List[ContentGap],
        quality_metrics: QualityMetrics
    ) -> List[str]:
        """Generate long-term improvement suggestions."""
        suggestions = []
        
        # Content structure improvements
        high_priority_gaps = [gap for gap in content_gaps if gap.priority == "high"]
        if high_priority_gaps:
            suggestions.append(
                "Conduct thorough content review to address structural gaps"
            )
        
        # Research and citation improvements
        suggestions.append("Strengthen literature review and increase citation diversity")
        
        # Quality-based suggestions
        if quality_metrics.coherence_score < 70:
            suggestions.append(
                "Develop stronger thematic coherence through better paragraph transitions"
            )
        
        if quality_metrics.completeness_score < 80:
            suggestions.append(
                "Expand methodology and results sections with more detailed information"
            )
        
        # Advanced improvements
        suggestions.extend([
            "Consider peer review for academic rigor assessment",
            "Develop visual aids and diagrams to support key concepts",
            "Create executive summary for broader accessibility",
            "Implement consistent terminology throughout the document"
        ])
        
        return suggestions[:6]  # Return top 6 long-term suggestions

    def _calculate_analysis_confidence(self, processing_result: ProcessingResult) -> float:
        """Calculate confidence in the analysis results."""
        # Factors affecting confidence
        factors = {
            'element_count': len(processing_result.elements),
            'section_count': len(processing_result.sections),
            'text_elements': len([e for e in processing_result.elements 
                                if isinstance(e, TextElement)]),
            'has_headings': len([e for e in processing_result.elements 
                               if isinstance(e, HeadingElement)]) > 0,
            'has_references': len([e for e in processing_result.elements 
                                 if isinstance(e, ReferenceElement)]) > 0
        }
        
        # Calculate confidence score
        confidence = 0.5  # Base confidence
        
        # More elements = higher confidence
        if factors['element_count'] > 50:
            confidence += 0.2
        elif factors['element_count'] > 20:
            confidence += 0.1
        
        # Good structure = higher confidence
        if factors['section_count'] > 3:
            confidence += 0.15
        
        if factors['has_headings']:
            confidence += 0.1
        
        if factors['has_references']:
            confidence += 0.05
        
        # Sufficient text content
        if factors['text_elements'] > 10:
            confidence += 0.1
        
        return min(1.0, confidence)

    def _extract_text_content(self, processing_result: ProcessingResult) -> str:
        """Extract all text content from the processing result."""
        text_parts = []
        
        for element in processing_result.elements:
            if isinstance(element, (TextElement, HeadingElement)):
                text_parts.append(element.text)
            elif isinstance(element, ReferenceElement):
                text_parts.append(element.text)
            elif isinstance(element, CitationElement):
                text_parts.append(element.text)
        
        return " ".join(text_parts)


# Add required import
import time
from datetime import datetime