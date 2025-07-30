"""
Academic Content Analyzer with IMRAD Classification and Advanced Analysis.

This module provides comprehensive analysis of academic documents including:
- IMRAD structure detection (Introduction, Methods, Results, Abstract, Discussion)
- Abstract identification and quality assessment
- Section classification with confidence scoring
- Equation extraction and indexing
- Reference list parsing and validation
- Author information extraction and validation
- Academic writing style analysis
- Content completeness assessment
"""

import re
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
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


class IMRADSection(str, Enum):
    """IMRAD section types for academic papers."""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    ACKNOWLEDGMENTS = "acknowledgments"
    APPENDIX = "appendix"
    UNKNOWN = "unknown"


class AcademicStructureType(str, Enum):
    """Types of academic document structures."""
    IMRAD = "imrad"
    THESIS = "thesis"
    CONFERENCE_PAPER = "conference_paper"
    JOURNAL_ARTICLE = "journal_article"
    REVIEW_PAPER = "review_paper"
    TECHNICAL_REPORT = "technical_report"
    UNKNOWN = "unknown"


class WritingQualityMetric(str, Enum):
    """Academic writing quality metrics."""
    READABILITY = "readability"
    COHERENCE = "coherence"
    ACADEMIC_TONE = "academic_tone"
    CITATION_DENSITY = "citation_density"
    VOCABULARY_SOPHISTICATION = "vocabulary_sophistication"
    SENTENCE_VARIETY = "sentence_variety"
    PASSIVE_VOICE_USAGE = "passive_voice_usage"


@dataclass
class IMRADClassificationResult:
    """Result of IMRAD section classification."""
    section_type: IMRADSection
    confidence: float
    evidence: List[str]  # List of evidence supporting the classification
    start_element_id: Optional[UUID] = None
    end_element_id: Optional[UUID] = None
    word_count: int = 0
    key_phrases: List[str] = None


@dataclass
class AbstractQualityAssessment:
    """Quality assessment for abstract section."""
    overall_score: float  # 0-100
    structure_score: float  # How well structured (background, methods, results, conclusion)
    completeness_score: float  # Contains all essential elements
    conciseness_score: float  # Appropriate length and density
    clarity_score: float  # Readability and coherence
    keyword_coverage: float  # Coverage of important keywords
    recommendations: List[str]  # Specific improvement suggestions
    word_count: int
    sentence_count: int
    has_background: bool
    has_methods: bool
    has_results: bool
    has_conclusion: bool


@dataclass
class SectionClassificationResult:
    """Result of section classification with confidence."""
    section: DocumentSection
    predicted_type: IMRADSection
    confidence: float
    features: Dict[str, float]  # Feature scores used for classification
    subsection_classifications: List['SectionClassificationResult'] = None


@dataclass
class EquationAnalysisResult:
    """Result of equation analysis."""
    equations: List[EquationElement]
    equation_density: float  # Equations per page
    complexity_score: float  # 0-100 based on mathematical content
    equation_types: Dict[str, int]  # Count of different equation types
    cross_references: Dict[str, List[str]]  # Equation references throughout document
    consistency_score: float  # Consistency in equation formatting


@dataclass
class ReferenceAnalysisResult:
    """Result of reference analysis."""
    references: List[ReferenceElement]
    citation_network: Dict[str, List[str]]  # Citation relationships
    reference_quality_score: float  # 0-100 based on completeness and formatting
    citation_density: float  # Citations per page
    recency_score: float  # How recent the references are
    diversity_score: float  # Diversity of reference types and sources
    formatting_consistency: float  # Consistency in reference formatting
    missing_fields: Dict[str, List[str]]  # Missing required fields per reference


@dataclass
class AuthorAnalysisResult:
    """Result of author information analysis."""
    authors: List[str]
    affiliations: List[str]
    author_affiliation_mapping: Dict[str, List[str]]
    corresponding_author: Optional[str]
    orcid_ids: Dict[str, str]  # Author to ORCID mapping
    email_addresses: Dict[str, str]  # Author to email mapping
    validation_score: float  # 0-100 for author info completeness
    formatting_issues: List[str]


@dataclass
class WritingQualityAnalysis:
    """Academic writing quality analysis results."""
    overall_score: float  # 0-100
    metric_scores: Dict[WritingQualityMetric, float]
    readability_metrics: Dict[str, float]  # Flesch-Kincaid, etc.
    vocabulary_analysis: Dict[str, Any]
    sentence_analysis: Dict[str, Any]
    coherence_analysis: Dict[str, Any]
    recommendations: List[str]
    strengths: List[str]
    weaknesses: List[str]


@dataclass
class ContentCompletenessAssessment:
    """Assessment of content completeness."""
    overall_completeness: float  # 0-100
    section_completeness: Dict[IMRADSection, float]
    missing_sections: List[IMRADSection]
    underdeveloped_sections: List[IMRADSection]
    content_balance_score: float  # Balance between sections
    essential_elements: Dict[str, bool]  # Title, abstract, intro, etc.
    recommendations: List[str]


@dataclass
class ContentSuggestion:
    """Content improvement suggestion."""
    section: IMRADSection
    suggestion_type: str  # "missing", "improve", "restructure", etc.
    priority: str  # "high", "medium", "low"
    description: str
    specific_recommendations: List[str]
    expected_improvement: float  # Expected score improvement (0-100)


class AcademicAnalyzer:
    """
    Comprehensive academic content analyzer with IMRAD classification and advanced analysis.
    
    This analyzer provides:
    - IMRAD structure detection with machine learning-based classification
    - Abstract quality assessment with detailed scoring
    - Section classification with confidence metrics
    - Equation extraction and cross-reference analysis
    - Reference parsing, validation, and network analysis
    - Author information extraction and validation
    - Academic writing quality analysis
    - Content completeness assessment with improvement suggestions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the academic analyzer with configuration."""
        self.config = config or {}
        self.logger = structlog.get_logger(__name__)
        
        # Initialize pattern dictionaries for different analysis tasks
        self._init_patterns()
        self._init_weights()
        
        # Quality thresholds
        self.quality_thresholds = {
            'excellent': 90,
            'good': 75,
            'fair': 60,
            'poor': 40
        }
        
    def _init_patterns(self) -> None:
        """Initialize regex patterns for content analysis."""
        self.patterns = {
            # IMRAD section patterns
            'abstract': [
                r'\babstract\b',
                r'\bsummary\b',
                r'\bexecutive\s+summary\b'
            ],
            'introduction': [
                r'\bintroduction\b',
                r'\bbackground\b',
                r'\bmotivation\b',
                r'\boverview\b'
            ],
            'methods': [
                r'\bmethods?\b',
                r'\bmethodology\b',
                r'\bapproach\b',
                r'\bexperimental\s+setup\b',
                r'\bmaterials?\s+and\s+methods?\b',
                r'\bdata\s+collection\b'
            ],
            'results': [
                r'\bresults?\b',
                r'\bfindings?\b',
                r'\boutcomes?\b',
                r'\banalysis\b',
                r'\bevaluation\b'
            ],
            'discussion': [
                r'\bdiscussion\b',
                r'\binterpretation\b',
                r'\bimplications?\b',
                r'\banalysis\s+and\s+discussion\b'
            ],
            'conclusion': [
                r'\bconclusions?\b',
                r'\bsummary\b',
                r'\bfinal\s+remarks?\b',
                r'\bclosing\s+thoughts?\b'
            ],
            'references': [
                r'\breferences?\b',
                r'\bbibliography\b',
                r'\bworks?\s+cited\b',
                r'\bliterature\s+cited\b'
            ],
            
            # Content indicators
            'method_indicators': [
                r'\bwe\s+(used|employed|applied|implemented)\b',
                r'\bthe\s+(method|approach|technique|algorithm)\b',
                r'\bdata\s+was\s+collected\b',
                r'\bexperiments?\s+were\s+conducted\b',
                r'\bparticipants?\b',
                r'\bsamples?\b'
            ],
            'result_indicators': [
                r'\bour\s+results?\s+show\b',
                r'\bwe\s+found\s+that\b',
                r'\bthe\s+analysis\s+revealed\b',
                r'\bfigure\s+\d+\s+shows?\b',
                r'\btable\s+\d+\s+presents?\b',
                r'\bstatistically\s+significant\b'
            ],
            'discussion_indicators': [
                r'\bthese\s+results?\s+suggest\b',
                r'\bour\s+findings?\s+indicate\b',
                r'\bthis\s+implies?\b',
                r'\bin\s+contrast\s+to\s+previous\b',
                r'\bcompared\s+to\s+other\s+studies\b',
                r'\blimitations?\b'
            ],
            
            # Citation patterns
            'citations': [
                r'\[[\d,\s\-]+\]',  # [1], [1,2], [1-3]
                r'\(\w+(?:\s+et\s+al\.?)?,?\s+\d{4}\w?\)',  # (Smith, 2020)
                r'\(\w+(?:\s+et\s+al\.?)?\s+\d{4}\w?(?:;\s*\w+(?:\s+et\s+al\.?)?\s+\d{4}\w?)*\)'  # Multiple citations
            ],
            
            # Author patterns
            'author_names': [
                r'[A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+',  # First M. Last
                r'[A-Z][a-z]+,\s+[A-Z]\.(?:\s+[A-Z]\.)*',     # Last, F. M.
            ],
            
            # Email patterns
            'emails': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            
            # Equation patterns
            'equations': [
                r'\$[^$]+\$',  # Inline math
                r'\$\$[^$]+\$\$',  # Display math
                r'\\begin\{equation\}.*?\\end\{equation\}',
                r'\\begin\{align\}.*?\\end\{align\}',
                r'\\begin\{eqnarray\}.*?\\end\{eqnarray\}'
            ],
            
            # Academic vocabulary
            'academic_words': [
                'furthermore', 'moreover', 'consequently', 'nevertheless',
                'hypothesis', 'methodology', 'analysis', 'synthesize',
                'empirical', 'theoretical', 'significant', 'correlation',
                'investigation', 'framework', 'paradigm', 'phenomenon'
            ],
            
            # Passive voice indicators
            'passive_voice': [
                r'\b(?:is|are|was|were|being|been)\s+\w+ed\b',
                r'\b(?:is|are|was|were|being|been)\s+\w+en\b'
            ]
        }
        
    def _init_weights(self) -> None:
        """Initialize feature weights for classification."""
        self.weights = {
            'title_match': 0.4,
            'content_indicators': 0.3,
            'position_score': 0.2,
            'length_score': 0.1,
            'citation_density': 0.1,
            'vocabulary_score': 0.1
        }
        
    async def analyze_document(self, processing_result: ProcessingResult) -> Dict[str, Any]:
        """
        Perform comprehensive academic analysis of a document.
        
        Args:
            processing_result: Document processing result with extracted elements
            
        Returns:
            Dictionary containing all analysis results
        """
        self.logger.info("starting_academic_analysis", 
                        document_id=str(processing_result.document_id))
        
        try:
            # Perform all analysis tasks
            analysis_results = {}
            
            # 1. IMRAD Structure Detection
            imrad_analysis = await self.classify_imrad_structure(processing_result)
            analysis_results['imrad_classification'] = imrad_analysis
            
            # 2. Abstract Quality Assessment
            abstract_analysis = await self.assess_abstract_quality(processing_result)
            analysis_results['abstract_quality'] = abstract_analysis
            
            # 3. Section Classification
            section_analysis = await self.classify_sections(processing_result)
            analysis_results['section_classification'] = section_analysis
            
            # 4. Equation Analysis
            equation_analysis = await self.analyze_equations(processing_result)
            analysis_results['equation_analysis'] = equation_analysis
            
            # 5. Reference Analysis
            reference_analysis = await self.analyze_references(processing_result)
            analysis_results['reference_analysis'] = reference_analysis
            
            # 6. Author Analysis
            author_analysis = await self.analyze_authors(processing_result)
            analysis_results['author_analysis'] = author_analysis
            
            # 7. Writing Quality Analysis
            writing_analysis = await self.analyze_writing_quality(processing_result)
            analysis_results['writing_quality'] = writing_analysis
            
            # 8. Content Completeness Assessment
            completeness_analysis = await self.assess_content_completeness(processing_result)
            analysis_results['content_completeness'] = completeness_analysis
            
            # 9. Generate Content Suggestions
            suggestions = await self.generate_content_suggestions(analysis_results)
            analysis_results['content_suggestions'] = suggestions
            
            # 10. Overall Academic Score
            overall_score = self._calculate_overall_academic_score(analysis_results)
            analysis_results['overall_academic_score'] = overall_score
            
            self.logger.info("academic_analysis_completed",
                           document_id=str(processing_result.document_id),
                           overall_score=overall_score)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error("academic_analysis_failed",
                            document_id=str(processing_result.document_id),
                            error=str(e))
            raise
    
    async def classify_imrad_structure(
        self, 
        processing_result: ProcessingResult
    ) -> Dict[str, Any]:
        """
        Classify document structure according to IMRAD format.
        
        Args:
            processing_result: Document processing result
            
        Returns:
            Dictionary with IMRAD classification results
        """
        sections = processing_result.sections
        elements = processing_result.elements
        
        # Extract text content for analysis
        full_text = self._extract_full_text(elements)
        
        # Detect overall document structure type
        structure_type = self._detect_structure_type(sections, full_text)
        
        # Classify individual sections
        section_classifications = []
        for section in sections:
            classification = self._classify_imrad_section(section, elements)
            section_classifications.append(classification)
        
        # Calculate structure completeness
        completeness = self._calculate_imrad_completeness(section_classifications)
        
        # Generate structure confidence score
        confidence = self._calculate_structure_confidence(section_classifications)
        
        return {
            'structure_type': structure_type,
            'section_classifications': section_classifications,
            'completeness_score': completeness,
            'confidence_score': confidence,
            'missing_sections': self._identify_missing_imrad_sections(section_classifications),
            'section_order_score': self._evaluate_section_order(section_classifications),
            'recommendations': self._generate_structure_recommendations(
                section_classifications, completeness
            )
        }
    
    async def assess_abstract_quality(
        self, 
        processing_result: ProcessingResult
    ) -> AbstractQualityAssessment:
        """
        Assess quality of abstract section.
        
        Args:
            processing_result: Document processing result
            
        Returns:
            Abstract quality assessment
        """
        # Find abstract section
        abstract_text = self._find_abstract_text(processing_result.elements)
        
        if not abstract_text:
            return AbstractQualityAssessment(
                overall_score=0.0,
                structure_score=0.0,
                completeness_score=0.0,
                conciseness_score=0.0,
                clarity_score=0.0,
                keyword_coverage=0.0,
                recommendations=["No abstract found in document"],
                word_count=0,
                sentence_count=0,
                has_background=False,
                has_methods=False,
                has_results=False,
                has_conclusion=False
            )
        
        # Analyze abstract structure and content
        word_count = len(abstract_text.split())
        sentence_count = len(re.split(r'[.!?]+', abstract_text))
        
        # Check for structural components
        has_background = self._has_background_component(abstract_text)
        has_methods = self._has_methods_component(abstract_text)
        has_results = self._has_results_component(abstract_text)
        has_conclusion = self._has_conclusion_component(abstract_text)
        
        # Calculate component scores
        structure_score = self._calculate_abstract_structure_score(
            has_background, has_methods, has_results, has_conclusion
        )
        
        completeness_score = self._calculate_abstract_completeness_score(
            abstract_text, word_count, sentence_count
        )
        
        conciseness_score = self._calculate_abstract_conciseness_score(word_count)
        
        clarity_score = self._calculate_abstract_clarity_score(abstract_text)
        
        keyword_coverage = self._calculate_keyword_coverage(
            abstract_text, processing_result.elements
        )
        
        # Calculate overall score
        overall_score = (
            structure_score * 0.3 +
            completeness_score * 0.25 +
            conciseness_score * 0.2 +
            clarity_score * 0.15 +
            keyword_coverage * 0.1
        )
        
        # Generate recommendations
        recommendations = self._generate_abstract_recommendations(
            structure_score, completeness_score, conciseness_score,
            clarity_score, keyword_coverage, word_count,
            has_background, has_methods, has_results, has_conclusion
        )
        
        return AbstractQualityAssessment(
            overall_score=overall_score,
            structure_score=structure_score,
            completeness_score=completeness_score,
            conciseness_score=conciseness_score,
            clarity_score=clarity_score,
            keyword_coverage=keyword_coverage,
            recommendations=recommendations,
            word_count=word_count,
            sentence_count=sentence_count,
            has_background=has_background,
            has_methods=has_methods,
            has_results=has_results,
            has_conclusion=has_conclusion
        )
    
    async def classify_sections(
        self,
        processing_result: ProcessingResult
    ) -> List[SectionClassificationResult]:
        """
        Classify document sections with confidence scoring.
        
        Args:
            processing_result: Document processing result
            
        Returns:
            List of section classification results
        """
        classification_results = []
        
        for section in processing_result.sections:
            # Extract features for classification
            features = self._extract_section_features(section, processing_result.elements)
            
            # Predict section type using feature-based classification
            predicted_type, confidence = self._predict_section_type(features)
            
            # Classify subsections if present
            subsection_classifications = []
            if section.subsections:
                for subsection in section.subsections:
                    sub_features = self._extract_section_features(subsection, processing_result.elements)
                    sub_type, sub_confidence = self._predict_section_type(sub_features)
                    
                    subsection_classifications.append(
                        SectionClassificationResult(
                            section=subsection,
                            predicted_type=sub_type,
                            confidence=sub_confidence,
                            features=sub_features
                        )
                    )
            
            classification_results.append(
                SectionClassificationResult(
                    section=section,
                    predicted_type=predicted_type,
                    confidence=confidence,
                    features=features,
                    subsection_classifications=subsection_classifications
                )
            )
            
        return classification_results
    
    async def analyze_equations(
        self,
        processing_result: ProcessingResult
    ) -> EquationAnalysisResult:
        """
        Analyze mathematical equations in the document.
        
        Args:
            processing_result: Document processing result
            
        Returns:
            Equation analysis results
        """
        # Extract equations from document elements
        equations = [elem for elem in processing_result.elements 
                    if isinstance(elem, EquationElement)]
        
        # Additional equation extraction from text elements
        additional_equations = self._extract_equations_from_text(processing_result.elements)
        equations.extend(additional_equations)
        
        if not equations:
            return EquationAnalysisResult(
                equations=[],
                equation_density=0.0,
                complexity_score=0.0,
                equation_types={},
                cross_references={},
                consistency_score=0.0
            )
        
        # Calculate equation density (equations per page)
        total_pages = max([layout.page_number for layout in processing_result.layout_info], default=1) + 1
        equation_density = len(equations) / total_pages
        
        # Analyze equation types
        equation_types = self._classify_equation_types(equations)
        
        # Calculate complexity score
        complexity_score = self._calculate_equation_complexity(equations)
        
        # Find cross-references
        cross_references = self._find_equation_references(equations, processing_result.elements)
        
        # Assess formatting consistency
        consistency_score = self._assess_equation_consistency(equations)
        
        return EquationAnalysisResult(
            equations=equations,
            equation_density=equation_density,
            complexity_score=complexity_score,
            equation_types=equation_types,
            cross_references=cross_references,
            consistency_score=consistency_score
        )
    
    async def analyze_references(
        self,
        processing_result: ProcessingResult
    ) -> ReferenceAnalysisResult:
        """
        Analyze bibliography and citations.
        
        Args:
            processing_result: Document processing result
            
        Returns:
            Reference analysis results
        """
        references = processing_result.references
        citations = processing_result.citations
        
        if not references:
            return ReferenceAnalysisResult(
                references=[],
                citation_network={},
                reference_quality_score=0.0,
                citation_density=0.0,
                recency_score=0.0,
                diversity_score=0.0,
                formatting_consistency=0.0,
                missing_fields={}
            )
        
        # Build citation network
        citation_network = self._build_citation_network(references, citations)
        
        # Assess reference quality
        reference_quality_score = self._assess_reference_quality(references)
        
        # Calculate citation density
        total_pages = max([layout.page_number for layout in processing_result.layout_info], default=1) + 1
        citation_density = len(citations) / total_pages
        
        # Analyze reference recency
        recency_score = self._calculate_reference_recency(references)
        
        # Assess reference diversity
        diversity_score = self._assess_reference_diversity(references)
        
        # Check formatting consistency
        formatting_consistency = self._assess_reference_formatting_consistency(references)
        
        # Identify missing fields
        missing_fields = self._identify_missing_reference_fields(references)
        
        return ReferenceAnalysisResult(
            references=references,
            citation_network=citation_network,
            reference_quality_score=reference_quality_score,
            citation_density=citation_density,
            recency_score=recency_score,
            diversity_score=diversity_score,
            formatting_consistency=formatting_consistency,
            missing_fields=missing_fields
        )
    
    async def analyze_authors(
        self,
        processing_result: ProcessingResult
    ) -> AuthorAnalysisResult:
        """
        Analyze author information and affiliations.
        
        Args:
            processing_result: Document processing result
            
        Returns:
            Author analysis results
        """
        metadata = processing_result.metadata
        elements = processing_result.elements
        
        # Extract author information from metadata and text
        authors = list(metadata.authors) if metadata.authors else []
        affiliations = list(metadata.affiliations) if metadata.affiliations else []
        
        # Extract additional author info from document text
        additional_authors, additional_affiliations = self._extract_author_info_from_text(elements)
        authors.extend(additional_authors)
        affiliations.extend(additional_affiliations)
        
        # Remove duplicates
        authors = list(dict.fromkeys(authors))
        affiliations = list(dict.fromkeys(affiliations))
        
        # Map authors to affiliations
        author_affiliation_mapping = self._map_authors_to_affiliations(
            authors, affiliations, elements
        )
        
        # Find corresponding author
        corresponding_author = self._find_corresponding_author(elements)
        
        # Extract ORCID IDs
        orcid_ids = self._extract_orcid_ids(elements)
        
        # Extract email addresses
        email_addresses = self._extract_author_emails(elements)
        
        # Calculate validation score
        validation_score = self._calculate_author_validation_score(
            authors, affiliations, author_affiliation_mapping,
            corresponding_author, orcid_ids, email_addresses
        )
        
        # Identify formatting issues
        formatting_issues = self._identify_author_formatting_issues(
            authors, affiliations, elements
        )
        
        return AuthorAnalysisResult(
            authors=authors,
            affiliations=affiliations,
            author_affiliation_mapping=author_affiliation_mapping,
            corresponding_author=corresponding_author,
            orcid_ids=orcid_ids,
            email_addresses=email_addresses,
            validation_score=validation_score,
            formatting_issues=formatting_issues
        )
    
    async def analyze_writing_quality(
        self,
        processing_result: ProcessingResult
    ) -> WritingQualityAnalysis:
        """
        Analyze academic writing quality.
        
        Args:
            processing_result: Document processing result
            
        Returns:
            Writing quality analysis results
        """
        # Extract full text for analysis
        full_text = self._extract_full_text(processing_result.elements)
        
        if not full_text:
            return WritingQualityAnalysis(
                overall_score=0.0,
                metric_scores={},
                readability_metrics={},
                vocabulary_analysis={},
                sentence_analysis={},
                coherence_analysis={},
                recommendations=[],
                strengths=[],
                weaknesses=[]
            )
        
        # Calculate individual quality metrics
        metric_scores = {}
        
        # Readability analysis
        readability_metrics = self._calculate_readability_metrics(full_text)
        metric_scores[WritingQualityMetric.READABILITY] = readability_metrics.get('flesch_kincaid', 0)
        
        # Coherence analysis
        coherence_analysis = self._analyze_text_coherence(processing_result.elements)
        metric_scores[WritingQualityMetric.COHERENCE] = coherence_analysis.get('overall_coherence', 0)
        
        # Academic tone analysis
        academic_tone_score = self._analyze_academic_tone(full_text)
        metric_scores[WritingQualityMetric.ACADEMIC_TONE] = academic_tone_score
        
        # Citation density
        citation_density = len(processing_result.citations) / len(full_text.split()) * 1000
        metric_scores[WritingQualityMetric.CITATION_DENSITY] = min(100, citation_density * 10)
        
        # Vocabulary sophistication
        vocabulary_analysis = self._analyze_vocabulary_sophistication(full_text)
        metric_scores[WritingQualityMetric.VOCABULARY_SOPHISTICATION] = vocabulary_analysis.get('sophistication_score', 0)
        
        # Sentence variety
        sentence_analysis = self._analyze_sentence_variety(full_text)
        metric_scores[WritingQualityMetric.SENTENCE_VARIETY] = sentence_analysis.get('variety_score', 0)
        
        # Passive voice usage
        passive_voice_score = self._analyze_passive_voice_usage(full_text)
        metric_scores[WritingQualityMetric.PASSIVE_VOICE_USAGE] = passive_voice_score
        
        # Calculate overall score
        overall_score = sum(metric_scores.values()) / len(metric_scores)
        
        # Generate recommendations, strengths, and weaknesses
        recommendations = self._generate_writing_recommendations(metric_scores)
        strengths = self._identify_writing_strengths(metric_scores)
        weaknesses = self._identify_writing_weaknesses(metric_scores)
        
        return WritingQualityAnalysis(
            overall_score=overall_score,
            metric_scores=metric_scores,
            readability_metrics=readability_metrics,
            vocabulary_analysis=vocabulary_analysis,
            sentence_analysis=sentence_analysis,
            coherence_analysis=coherence_analysis,
            recommendations=recommendations,
            strengths=strengths,
            weaknesses=weaknesses
        )
    
    async def assess_content_completeness(
        self,
        processing_result: ProcessingResult
    ) -> ContentCompletenessAssessment:
        """
        Assess completeness of academic content.
        
        Args:
            processing_result: Document processing result
            
        Returns:
            Content completeness assessment
        """
        # Get IMRAD classification results
        imrad_analysis = await self.classify_imrad_structure(processing_result)
        section_classifications = imrad_analysis['section_classifications']
        
        # Assess completeness of each IMRAD section
        section_completeness = {}
        for imrad_section in IMRADSection:
            if imrad_section != IMRADSection.UNKNOWN:
                completeness = self._assess_section_completeness(
                    imrad_section, section_classifications, processing_result.elements
                )
                section_completeness[imrad_section] = completeness
        
        # Identify missing and underdeveloped sections
        missing_sections = [
            section for section, completeness in section_completeness.items()
            if completeness < 0.1
        ]
        
        underdeveloped_sections = [
            section for section, completeness in section_completeness.items()
            if 0.1 <= completeness < 0.5
        ]
        
        # Calculate content balance score
        content_balance_score = self._calculate_content_balance_score(section_completeness)
        
        # Check essential elements
        essential_elements = {
            'title': bool(processing_result.metadata.title),
            'abstract': bool(self._find_abstract_text(processing_result.elements)),
            'introduction': IMRADSection.INTRODUCTION not in missing_sections,
            'methodology': IMRADSection.METHODS not in missing_sections,
            'results': IMRADSection.RESULTS not in missing_sections,
            'discussion': IMRADSection.DISCUSSION not in missing_sections,
            'references': bool(processing_result.references),
            'figures_or_tables': bool(processing_result.figures or processing_result.tables)
        }
        
        # Calculate overall completeness
        overall_completeness = (
            sum(section_completeness.values()) / len(section_completeness) * 0.7 +
            content_balance_score * 0.2 +
            sum(essential_elements.values()) / len(essential_elements) * 100 * 0.1
        )
        
        # Generate recommendations
        recommendations = self._generate_completeness_recommendations(
            missing_sections, underdeveloped_sections, essential_elements, content_balance_score
        )
        
        return ContentCompletenessAssessment(
            overall_completeness=overall_completeness,
            section_completeness=section_completeness,
            missing_sections=missing_sections,
            underdeveloped_sections=underdeveloped_sections,
            content_balance_score=content_balance_score,
            essential_elements=essential_elements,
            recommendations=recommendations
        )
    
    async def generate_content_suggestions(
        self,
        analysis_results: Dict[str, Any]
    ) -> List[ContentSuggestion]:
        """
        Generate intelligent content improvement suggestions.
        
        Args:
            analysis_results: Complete analysis results
            
        Returns:
            List of content improvement suggestions
        """
        suggestions = []
        
        # Suggestions based on IMRAD analysis
        imrad_analysis = analysis_results.get('imrad_classification', {})
        missing_sections = imrad_analysis.get('missing_sections', [])
        
        for missing_section in missing_sections:
            suggestions.append(
                ContentSuggestion(
                    section=missing_section,
                    suggestion_type="missing",
                    priority="high",
                    description=f"Add missing {missing_section.value} section",
                    specific_recommendations=self._get_section_content_suggestions(missing_section),
                    expected_improvement=15.0
                )
            )
        
        # Suggestions based on abstract quality
        abstract_quality = analysis_results.get('abstract_quality')
        if abstract_quality and abstract_quality.overall_score < 70:
            suggestions.append(
                ContentSuggestion(
                    section=IMRADSection.ABSTRACT,
                    suggestion_type="improve",
                    priority="high",
                    description="Improve abstract quality",
                    specific_recommendations=abstract_quality.recommendations,
                    expected_improvement=abstract_quality.overall_score * 0.3
                )
            )
        
        # Suggestions based on writing quality
        writing_quality = analysis_results.get('writing_quality')
        if writing_quality:
            for weakness in writing_quality.weaknesses:
                suggestions.append(
                    ContentSuggestion(
                        section=IMRADSection.UNKNOWN,
                        suggestion_type="improve",
                        priority="medium",
                        description=f"Address writing quality issue: {weakness}",
                        specific_recommendations=[weakness],
                        expected_improvement=5.0
                    )
                )
        
        # Suggestions based on reference analysis
        reference_analysis = analysis_results.get('reference_analysis')
        if reference_analysis and reference_analysis.reference_quality_score < 70:
            suggestions.append(
                ContentSuggestion(
                    section=IMRADSection.REFERENCES,
                    suggestion_type="improve",
                    priority="medium",
                    description="Improve reference quality and formatting",
                    specific_recommendations=[
                        "Ensure all references have complete information",
                        "Check reference formatting consistency",
                        "Add more recent references if applicable"
                    ],
                    expected_improvement=10.0
                )
            )
        
        # Sort suggestions by priority and expected improvement
        priority_order = {"high": 3, "medium": 2, "low": 1}
        suggestions.sort(
            key=lambda x: (priority_order[x.priority], x.expected_improvement),
            reverse=True
        )
        
        return suggestions
    
    # Helper methods for analysis implementation
    
    def _extract_full_text(self, elements: List[DocumentElement]) -> str:
        """Extract full text content from document elements."""
        text_parts = []
        for element in elements:
            if hasattr(element, 'content') and element.content:
                text_parts.append(element.content)
        return ' '.join(text_parts)
    
    def _detect_structure_type(
        self, 
        sections: List[DocumentSection], 
        full_text: str
    ) -> AcademicStructureType:
        """Detect the overall document structure type."""
        # Simple heuristic-based detection
        section_titles = [section.title.lower() for section in sections]
        
        # Check for IMRAD pattern
        imrad_indicators = ['abstract', 'introduction', 'method', 'result', 'discussion']
        imrad_score = sum(1 for indicator in imrad_indicators 
                         if any(indicator in title for title in section_titles))
        
        if imrad_score >= 3:
            # Check for journal vs conference patterns
            if any('journal' in full_text.lower() or 'vol.' in full_text.lower()):
                return AcademicStructureType.JOURNAL_ARTICLE
            elif any('conference' in full_text.lower() or 'proceedings' in full_text.lower()):
                return AcademicStructureType.CONFERENCE_PAPER
            else:
                return AcademicStructureType.IMRAD
        
        # Check for thesis pattern
        thesis_indicators = ['chapter', 'literature review', 'related work', 'future work']
        thesis_score = sum(1 for indicator in thesis_indicators 
                          if any(indicator in title for title in section_titles))
        
        if thesis_score >= 2:
            return AcademicStructureType.THESIS
        
        # Check for review paper
        if any('review' in title or 'survey' in title for title in section_titles):
            return AcademicStructureType.REVIEW_PAPER
        
        # Check for technical report
        if any('report' in full_text.lower() or 'technical' in full_text.lower()):
            return AcademicStructureType.TECHNICAL_REPORT
        
        return AcademicStructureType.UNKNOWN
    
    def _classify_imrad_section(
        self, 
        section: DocumentSection, 
        elements: List[DocumentElement]
    ) -> IMRADClassificationResult:
        """Classify a section according to IMRAD structure."""
        title = section.title.lower()
        content = self._extract_section_content(section, elements)
        
        # Initialize scores for each IMRAD section type
        scores = {imrad_type: 0.0 for imrad_type in IMRADSection}
        
        # Title-based scoring
        for imrad_type in IMRADSection:
            if imrad_type != IMRADSection.UNKNOWN:
                patterns = self.patterns.get(imrad_type.value, [])
                for pattern in patterns:
                    if re.search(pattern, title, re.IGNORECASE):
                        scores[imrad_type] += self.weights['title_match']
        
        # Content-based scoring
        content_indicators = {
            IMRADSection.METHODS: self.patterns['method_indicators'],
            IMRADSection.RESULTS: self.patterns['result_indicators'],
            IMRADSection.DISCUSSION: self.patterns['discussion_indicators']
        }
        
        for imrad_type, indicators in content_indicators.items():
            for indicator in indicators:
                matches = len(re.findall(indicator, content, re.IGNORECASE))
                scores[imrad_type] += matches * self.weights['content_indicators']
        
        # Find best match
        best_match = max(scores, key=scores.get)
        confidence = scores[best_match] / max(sum(scores.values()), 1.0)
        
        # Generate evidence
        evidence = self._generate_classification_evidence(best_match, title, content)
        
        return IMRADClassificationResult(
            section_type=best_match,
            confidence=confidence,
            evidence=evidence,
            start_element_id=section.elements[0].id if section.elements else None,
            end_element_id=section.elements[-1].id if section.elements else None,
            word_count=len(content.split()),
            key_phrases=self._extract_key_phrases(content, best_match)
        )
    
    def _extract_section_content(
        self, 
        section: DocumentSection, 
        elements: List[DocumentElement]
    ) -> str:
        """Extract text content from a section."""
        section_element_ids = {elem.id for elem in section.elements}
        content_parts = []
        
        for element in elements:
            if element.id in section_element_ids and hasattr(element, 'content'):
                content_parts.append(element.content)
        
        return ' '.join(content_parts)
    
    def _calculate_imrad_completeness(
        self, 
        classifications: List[IMRADClassificationResult]
    ) -> float:
        """Calculate IMRAD structure completeness score."""
        required_sections = {
            IMRADSection.ABSTRACT,
            IMRADSection.INTRODUCTION,
            IMRADSection.METHODS,
            IMRADSection.RESULTS,
            IMRADSection.DISCUSSION
        }
        
        found_sections = {cls.section_type for cls in classifications 
                         if cls.confidence > 0.5}
        
        completeness = len(found_sections & required_sections) / len(required_sections)
        return completeness * 100
    
    def _calculate_structure_confidence(
        self, 
        classifications: List[IMRADClassificationResult]
    ) -> float:
        """Calculate overall structure classification confidence."""
        if not classifications:
            return 0.0
        
        confidences = [cls.confidence for cls in classifications]
        return sum(confidences) / len(confidences) * 100
    
    def _identify_missing_imrad_sections(
        self, 
        classifications: List[IMRADClassificationResult]
    ) -> List[IMRADSection]:
        """Identify missing IMRAD sections."""
        required_sections = {
            IMRADSection.ABSTRACT,
            IMRADSection.INTRODUCTION,
            IMRADSection.METHODS,
            IMRADSection.RESULTS,
            IMRADSection.DISCUSSION
        }
        
        found_sections = {cls.section_type for cls in classifications 
                         if cls.confidence > 0.3}
        
        return list(required_sections - found_sections)
    
    def _evaluate_section_order(
        self, 
        classifications: List[IMRADClassificationResult]
    ) -> float:
        """Evaluate the order of IMRAD sections."""
        expected_order = [
            IMRADSection.ABSTRACT,
            IMRADSection.INTRODUCTION,
            IMRADSection.METHODS,
            IMRADSection.RESULTS,
            IMRADSection.DISCUSSION,
            IMRADSection.CONCLUSION,
            IMRADSection.REFERENCES
        ]
        
        found_order = [cls.section_type for cls in classifications 
                      if cls.section_type in expected_order and cls.confidence > 0.3]
        
        if len(found_order) < 2:
            return 100.0  # Can't evaluate order with fewer than 2 sections
        
        # Calculate order score based on position violations
        violations = 0
        for i in range(len(found_order) - 1):
            current_pos = expected_order.index(found_order[i])
            next_pos = expected_order.index(found_order[i + 1])
            if current_pos >= next_pos:
                violations += 1
        
        order_score = max(0, 100 - (violations / len(found_order)) * 100)
        return order_score
    
    def _generate_structure_recommendations(
        self, 
        classifications: List[IMRADClassificationResult], 
        completeness: float
    ) -> List[str]:
        """Generate recommendations for improving document structure."""
        recommendations = []
        
        if completeness < 60:
            recommendations.append("Consider adding missing IMRAD sections to improve document structure")
        
        missing_sections = self._identify_missing_imrad_sections(classifications)
        for section in missing_sections:
            recommendations.append(f"Add {section.value} section")
        
        low_confidence_sections = [cls for cls in classifications if cls.confidence < 0.5]
        if low_confidence_sections:
            recommendations.append("Review section titles and content to better align with IMRAD structure")
        
        return recommendations
    
    def _find_abstract_text(self, elements: List[DocumentElement]) -> Optional[str]:
        """Find and extract abstract text from document elements."""
        for element in elements:
            if (hasattr(element, 'content') and element.content and
                any(re.search(pattern, element.content, re.IGNORECASE) 
                    for pattern in self.patterns['abstract'])):
                # Look for abstract content in subsequent elements
                abstract_parts = []
                found_abstract_start = False
                
                for elem in elements:
                    if elem == element:
                        found_abstract_start = True
                        continue
                    
                    if found_abstract_start and hasattr(elem, 'content'):
                        # Stop if we hit another section header
                        if (isinstance(elem, HeadingElement) or
                            any(re.search(pattern, elem.content, re.IGNORECASE)
                                for pattern_list in [self.patterns['introduction'], 
                                                   self.patterns['methods']]
                                for pattern in pattern_list)):
                            break
                        abstract_parts.append(elem.content)
                
                if abstract_parts:
                    return ' '.join(abstract_parts)
        
        return None
    
    def _has_background_component(self, abstract_text: str) -> bool:
        """Check if abstract contains background/motivation component."""
        background_indicators = [
            r'\b(background|motivation|context|problem|challenge)\b',
            r'\b(important|significant|critical|essential)\b',
            r'\b(previous|prior|existing|current)\s+(work|research|studies)\b'
        ]
        
        return any(re.search(pattern, abstract_text, re.IGNORECASE) 
                  for pattern in background_indicators)
    
    def _has_methods_component(self, abstract_text: str) -> bool:
        """Check if abstract contains methods component."""
        return any(re.search(pattern, abstract_text, re.IGNORECASE) 
                  for pattern in self.patterns['method_indicators'])
    
    def _has_results_component(self, abstract_text: str) -> bool:
        """Check if abstract contains results component."""
        return any(re.search(pattern, abstract_text, re.IGNORECASE) 
                  for pattern in self.patterns['result_indicators'])
    
    def _has_conclusion_component(self, abstract_text: str) -> bool:
        """Check if abstract contains conclusion component."""
        conclusion_indicators = [
            r'\b(conclude|conclusion|finding|demonstrate)\b',
            r'\b(show|reveal|indicate|suggest)\s+that\b',
            r'\b(implication|impact|significance)\b'
        ]
        
        return any(re.search(pattern, abstract_text, re.IGNORECASE) 
                  for pattern in conclusion_indicators)
    
    def _calculate_abstract_structure_score(
        self, 
        has_background: bool, 
        has_methods: bool, 
        has_results: bool, 
        has_conclusion: bool
    ) -> float:
        """Calculate structure score for abstract."""
        components = [has_background, has_methods, has_results, has_conclusion]
        return sum(components) / len(components) * 100
    
    def _calculate_abstract_completeness_score(
        self, 
        abstract_text: str, 
        word_count: int, 
        sentence_count: int
    ) -> float:
        """Calculate completeness score for abstract."""
        # Check for key elements
        has_objective = bool(re.search(r'\b(objective|aim|purpose|goal)\b', 
                                     abstract_text, re.IGNORECASE))
        has_methodology = bool(re.search(r'\b(method|approach|technique|analysis)\b', 
                                       abstract_text, re.IGNORECASE))
        has_findings = bool(re.search(r'\b(result|finding|outcome|show)\b', 
                                    abstract_text, re.IGNORECASE))
        has_implications = bool(re.search(r'\b(implication|significance|impact|conclusion)\b', 
                                        abstract_text, re.IGNORECASE))
        
        element_score = sum([has_objective, has_methodology, has_findings, has_implications]) / 4
        
        # Length appropriateness (150-300 words ideal)
        length_score = 1.0
        if word_count < 100:
            length_score = word_count / 100
        elif word_count > 400:
            length_score = max(0.5, 400 / word_count)
        
        return (element_score * 0.7 + length_score * 0.3) * 100
    
    def _calculate_abstract_conciseness_score(self, word_count: int) -> float:
        """Calculate conciseness score for abstract."""
        # Optimal range: 150-250 words
        if 150 <= word_count <= 250:
            return 100.0
        elif word_count < 150:
            return (word_count / 150) * 100
        else:  # word_count > 250
            return max(50, (300 / word_count) * 100)
    
    def _calculate_abstract_clarity_score(self, abstract_text: str) -> float:
        """Calculate clarity score for abstract."""
        sentences = re.split(r'[.!?]+', abstract_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        # Average sentence length (15-25 words ideal)
        words_per_sentence = [len(sentence.split()) for sentence in sentences]
        avg_sentence_length = sum(words_per_sentence) / len(words_per_sentence)
        
        length_score = 100.0
        if avg_sentence_length < 10:
            length_score = (avg_sentence_length / 10) * 100
        elif avg_sentence_length > 30:
            length_score = max(50, (30 / avg_sentence_length) * 100)
        
        # Check for clarity indicators
        clarity_issues = [
            len(re.findall(r'\b(however|although|nevertheless|nonetheless)\b', 
                          abstract_text, re.IGNORECASE)),  # Complex transitions
            len(re.findall(r'\([^)]{20,}\)', abstract_text)),  # Long parenthetical remarks
            len(re.findall(r'\b\w{15,}\b', abstract_text))  # Very long words
        ]
        
        issue_penalty = min(30, sum(clarity_issues) * 5)
        return max(50, length_score - issue_penalty)
    
    def _calculate_keyword_coverage(
        self, 
        abstract_text: str, 
        elements: List[DocumentElement]
    ) -> float:
        """Calculate keyword coverage in abstract."""
        # Extract potential keywords from document
        full_text = self._extract_full_text(elements)
        
        # Simple keyword extraction based on frequency and academic vocabulary
        words = re.findall(r'\b[a-z]{4,}\b', full_text.lower())
        word_freq = Counter(words)
        
        # Filter for potential keywords (academic words, high frequency)
        academic_words_lower = [word.lower() for word in self.patterns['academic_words']]
        potential_keywords = []
        
        for word, freq in word_freq.most_common(50):
            if (freq > 3 and len(word) > 4 and 
                (word in academic_words_lower or 
                 word.endswith(('tion', 'ment', 'ness', 'ity', 'ism')))):
                potential_keywords.append(word)
        
        if not potential_keywords:
            return 50.0  # Default score if no keywords identified
        
        # Check coverage in abstract
        abstract_words = set(re.findall(r'\b[a-z]{4,}\b', abstract_text.lower()))
        coverage = len(set(potential_keywords[:20]) & abstract_words) / min(20, len(potential_keywords))
        
        return coverage * 100
    
    def _generate_abstract_recommendations(
        self, 
        structure_score: float, 
        completeness_score: float, 
        conciseness_score: float,
        clarity_score: float, 
        keyword_coverage: float, 
        word_count: int,
        has_background: bool, 
        has_methods: bool, 
        has_results: bool, 
        has_conclusion: bool
    ) -> List[str]:
        """Generate specific recommendations for abstract improvement."""
        recommendations = []
        
        if structure_score < 75:
            missing_components = []
            if not has_background:
                missing_components.append("background/motivation")
            if not has_methods:
                missing_components.append("methodology")
            if not has_results:
                missing_components.append("key findings")
            if not has_conclusion:
                missing_components.append("implications/conclusions")
            
            if missing_components:
                recommendations.append(f"Include {', '.join(missing_components)} in the abstract")
        
        if conciseness_score < 75:
            if word_count < 150:
                recommendations.append("Expand the abstract to provide more detail (aim for 150-250 words)")
            elif word_count > 300:
                recommendations.append("Reduce abstract length for better conciseness (aim for 150-250 words)")
        
        if clarity_score < 75:
            recommendations.append("Improve clarity by using shorter, more direct sentences")
            recommendations.append("Avoid overly complex terminology where simpler alternatives exist")
        
        if keyword_coverage < 60:
            recommendations.append("Include more relevant keywords to improve discoverability")
        
        if completeness_score < 75:
            recommendations.append("Ensure all essential elements are covered: objective, methods, findings, significance")
        
        return recommendations
    
    def _extract_section_features(
        self, 
        section: DocumentSection, 
        elements: List[DocumentElement]
    ) -> Dict[str, float]:
        """Extract features for section classification."""
        content = self._extract_section_content(section, elements)
        title = section.title.lower()
        
        features = {}
        
        # Title matching features
        for imrad_type in IMRADSection:
            if imrad_type != IMRADSection.UNKNOWN:
                patterns = self.patterns.get(imrad_type.value, [])
                match_score = sum(1 for pattern in patterns 
                                if re.search(pattern, title, re.IGNORECASE))
                features[f'title_match_{imrad_type.value}'] = match_score
        
        # Content indicator features
        content_indicators = {
            'methods': self.patterns['method_indicators'],
            'results': self.patterns['result_indicators'],
            'discussion': self.patterns['discussion_indicators']
        }
        
        for category, indicators in content_indicators.items():
            indicator_count = sum(len(re.findall(indicator, content, re.IGNORECASE))
                                for indicator in indicators)
            features[f'content_{category}'] = indicator_count
        
        # Position features
        features['position_ratio'] = section.start_page / max(section.end_page, 1) if section.start_page else 0
        
        # Length features
        features['word_count'] = len(content.split())
        features['sentence_count'] = len(re.split(r'[.!?]+', content))
        
        # Citation features
        citation_count = sum(len(re.findall(pattern, content)) 
                           for pattern in self.patterns['citations'])
        features['citation_density'] = citation_count / max(len(content.split()), 1)
        
        return features
    
    def _predict_section_type(self, features: Dict[str, float]) -> Tuple[IMRADSection, float]:
        """Predict section type using feature-based classification."""
        # Simple scoring-based classification
        scores = {imrad_type: 0.0 for imrad_type in IMRADSection}
        
        # Title matching scores
        for imrad_type in IMRADSection:
            if imrad_type != IMRADSection.UNKNOWN:
                title_feature = f'title_match_{imrad_type.value}'
                if title_feature in features:
                    scores[imrad_type] += features[title_feature] * 0.4
        
        # Content-based scores
        if features.get('content_methods', 0) > 0:
            scores[IMRADSection.METHODS] += features['content_methods'] * 0.3
        
        if features.get('content_results', 0) > 0:
            scores[IMRADSection.RESULTS] += features['content_results'] * 0.3
        
        if features.get('content_discussion', 0) > 0:
            scores[IMRADSection.DISCUSSION] += features['content_discussion'] * 0.3
        
        # Position-based scoring
        position_ratio = features.get('position_ratio', 0)
        if position_ratio < 0.2:  # Early in document
            scores[IMRADSection.ABSTRACT] += 0.2
            scores[IMRADSection.INTRODUCTION] += 0.1
        elif position_ratio > 0.8:  # Late in document
            scores[IMRADSection.CONCLUSION] += 0.2
            scores[IMRADSection.REFERENCES] += 0.1
        
        # Find best match
        best_match = max(scores, key=scores.get)
        confidence = scores[best_match] / max(sum(scores.values()), 1.0)
        
        return best_match, confidence
    
    def _extract_equations_from_text(self, elements: List[DocumentElement]) -> List[EquationElement]:
        """Extract equations from text elements using pattern matching."""
        equations = []
        
        for element in elements:
            if hasattr(element, 'content') and element.content:
                # Find equation patterns in text
                for pattern in self.patterns['equations']:
                    matches = re.finditer(pattern, element.content, re.DOTALL)
                    for match in matches:
                        equation = EquationElement(
                            content=match.group(),
                            latex_code=match.group(),
                            equation_type="inline" if pattern.startswith(r'\$[^$]+\$') else "display",
                            bbox=element.bbox if hasattr(element, 'bbox') else None
                        )
                        equations.append(equation)
        
        return equations
    
    def _classify_equation_types(self, equations: List[EquationElement]) -> Dict[str, int]:
        """Classify equations by type."""
        type_counts = defaultdict(int)
        
        for equation in equations:
            # Simple classification based on LaTeX content
            latex = equation.latex_code.lower()
            
            if any(keyword in latex for keyword in ['sum', 'int', 'integral']):
                type_counts['calculus'] += 1
            elif any(keyword in latex for keyword in ['matrix', 'vec', 'dot']):
                type_counts['linear_algebra'] += 1
            elif any(keyword in latex for keyword in ['frac', '/']):
                type_counts['fraction'] += 1
            elif any(keyword in latex for keyword in ['^', 'pow', 'exp']):
                type_counts['exponential'] += 1
            elif any(keyword in latex for keyword in ['sqrt', 'root']):
                type_counts['radical'] += 1
            else:
                type_counts['basic'] += 1
        
        return dict(type_counts)
    
    def _calculate_equation_complexity(self, equations: List[EquationElement]) -> float:
        """Calculate overall complexity score for equations."""
        if not equations:
            return 0.0
        
        complexity_scores = []
        
        for equation in equations:
            latex = equation.latex_code
            
            # Count complexity indicators
            complexity_indicators = {
                r'\\frac': 2,  # Fractions
                r'\\int': 3,   # Integrals
                r'\\sum': 3,   # Summations
                r'\\prod': 3,  # Products
                r'\\sqrt': 2,  # Square roots
                r'\^': 1,      # Exponents
                r'_': 1,       # Subscripts
                r'\\matrix': 4, # Matrices
                r'\\begin': 3,  # Environments
            }
            
            score = 0
            for pattern, weight in complexity_indicators.items():
                score += len(re.findall(pattern, latex)) * weight
            
            # Normalize by equation length
            normalized_score = score / max(len(latex), 1) * 100
            complexity_scores.append(min(100, normalized_score))
        
        return sum(complexity_scores) / len(complexity_scores)
    
    def _find_equation_references(
        self, 
        equations: List[EquationElement], 
        elements: List[DocumentElement]
    ) -> Dict[str, List[str]]:
        """Find cross-references to equations in the document."""
        references = {}
        full_text = self._extract_full_text(elements)
        
        for i, equation in enumerate(equations):
            equation_refs = []
            
            # Look for equation references (Eq. 1, Equation 1, etc.)
            ref_patterns = [
                rf'\bEq\.?\s*{i+1}\b',
                rf'\bEquation\s*{i+1}\b',
                rf'\(\s*{i+1}\s*\)',
            ]
            
            for pattern in ref_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                equation_refs.extend(matches)
            
            if equation_refs:
                equation_id = str(equation.id) if equation.id else f"equation_{i}"
                references[equation_id] = equation_refs
        
        return references
    
    def _assess_equation_consistency(self, equations: List[EquationElement]) -> float:
        """Assess formatting consistency of equations."""
        if len(equations) < 2:
            return 100.0
        
        # Check consistency in numbering, formatting, etc.
        numbered_equations = [eq for eq in equations if eq.equation_number]
        unnumbered_equations = [eq for eq in equations if not eq.equation_number]
        
        # Consistency in numbering approach
        numbering_consistency = 100.0
        if numbered_equations and unnumbered_equations:
            # Mixed approach - reduce score
            numbering_consistency = 70.0
        
        # Check LaTeX formatting consistency
        display_types = [eq.equation_type for eq in equations]
        type_consistency = (len(set(display_types)) / len(display_types)) * 100
        
        return (numbering_consistency + type_consistency) / 2
    
    def _build_citation_network(
        self, 
        references: List[ReferenceElement], 
        citations: List[CitationElement]
    ) -> Dict[str, List[str]]:
        """Build citation network showing relationships."""
        network = {}
        
        # Map citations to references
        for citation in citations:
            if citation.citation_key:
                # Find corresponding reference
                matching_refs = [ref for ref in references 
                               if ref.reference_key == citation.citation_key]
                
                if matching_refs:
                    ref = matching_refs[0]
                    if citation.citation_key not in network:
                        network[citation.citation_key] = []
                    
                    # Add reference info to network
                    ref_info = f"{ref.authors[0] if ref.authors else 'Unknown'} ({ref.year})"
                    if ref_info not in network[citation.citation_key]:
                        network[citation.citation_key].append(ref_info)
        
        return network
    
    def _assess_reference_quality(self, references: List[ReferenceElement]) -> float:
        """Assess overall quality of references."""
        if not references:
            return 0.0
        
        quality_scores = []
        
        for ref in references:
            score = 0.0
            max_score = 0.0
            
            # Check for essential fields
            essential_fields = ['authors', 'title', 'year']
            for field in essential_fields:
                max_score += 1
                if hasattr(ref, field) and getattr(ref, field):
                    score += 1
            
            # Check for additional fields based on reference type
            if ref.reference_type == 'journal':
                additional_fields = ['journal', 'volume', 'pages']
            elif ref.reference_type == 'book':
                additional_fields = ['publisher']
            elif ref.reference_type == 'conference':
                additional_fields = ['journal', 'pages']  # journal field often contains conference name
            else:
                additional_fields = ['journal', 'volume']
            
            for field in additional_fields:
                max_score += 0.5
                if hasattr(ref, field) and getattr(ref, field):
                    score += 0.5
            
            # Bonus for DOI
            if ref.doi:
                score += 0.5
                max_score += 0.5
            
            quality_scores.append((score / max_score) * 100 if max_score > 0 else 0)
        
        return sum(quality_scores) / len(quality_scores)
    
    def _calculate_reference_recency(self, references: List[ReferenceElement]) -> float:
        """Calculate recency score for references."""
        if not references:
            return 0.0
        
        current_year = 2024  # Could be made dynamic
        years = [ref.year for ref in references if ref.year]
        
        if not years:
            return 50.0  # Default score if no years found
        
        # Calculate average age
        ages = [current_year - year for year in years if year <= current_year]
        
        if not ages:
            return 50.0
        
        avg_age = sum(ages) / len(ages)
        
        # Score based on average age (newer is better)
        if avg_age <= 3:
            return 100.0
        elif avg_age <= 5:
            return 90.0
        elif avg_age <= 10:
            return 70.0
        elif avg_age <= 15:
            return 50.0
        else:
            return 30.0
    
    def _assess_reference_diversity(self, references: List[ReferenceElement]) -> float:
        """Assess diversity of reference types and sources."""
        if not references:
            return 0.0
        
        # Type diversity
        types = [ref.reference_type for ref in references if ref.reference_type]
        type_diversity = len(set(types)) / len(types) if types else 0
        
        # Journal diversity
        journals = [ref.journal for ref in references if ref.journal]
        journal_diversity = len(set(journals)) / len(journals) if journals else 0
        
        # Author diversity (check for self-citations or repeated authors)
        all_authors = []
        for ref in references:
            if ref.authors:
                all_authors.extend(ref.authors)
        
        author_diversity = len(set(all_authors)) / len(all_authors) if all_authors else 0
        
        # Overall diversity score
        diversity_score = (type_diversity + journal_diversity + author_diversity) / 3 * 100
        return diversity_score
    
    def _assess_reference_formatting_consistency(self, references: List[ReferenceElement]) -> float:
        """Assess consistency in reference formatting."""
        if len(references) < 2:
            return 100.0
        
        # Check consistency in field completeness
        field_patterns = []
        for ref in references:
            pattern = []
            fields_to_check = ['authors', 'title', 'journal', 'year', 'volume', 'pages', 'doi']
            
            for field in fields_to_check:
                pattern.append(bool(getattr(ref, field, None)))
            
            field_patterns.append(tuple(pattern))
        
        # Calculate consistency as percentage of references with same pattern
        pattern_counts = Counter(field_patterns)
        most_common_count = pattern_counts.most_common(1)[0][1]
        consistency = (most_common_count / len(references)) * 100
        
        return consistency
    
    def _identify_missing_reference_fields(self, references: List[ReferenceElement]) -> Dict[str, List[str]]:
        """Identify missing fields in references."""
        missing_fields = {}
        
        essential_fields = {
            'journal': ['authors', 'title', 'journal', 'year', 'volume', 'pages'],
            'book': ['authors', 'title', 'publisher', 'year'],
            'conference': ['authors', 'title', 'journal', 'year', 'pages'],  # journal often contains conference name
        }
        
        for i, ref in enumerate(references):
            ref_id = f"reference_{i+1}"
            missing_fields[ref_id] = []
            
            ref_type = ref.reference_type or 'journal'  # Default to journal
            required_fields = essential_fields.get(ref_type, essential_fields['journal'])
            
            for field in required_fields:
                if not getattr(ref, field, None):
                    missing_fields[ref_id].append(field)
        
        # Remove entries with no missing fields
        missing_fields = {k: v for k, v in missing_fields.items() if v}
        
        return missing_fields
    
    def _extract_author_info_from_text(
        self, 
        elements: List[DocumentElement]
    ) -> Tuple[List[str], List[str]]:
        """Extract additional author information from document text."""
        authors = []
        affiliations = []
        
        # Look for author patterns in the first few elements (typically near title)
        for element in elements[:10]:  # Check first 10 elements
            if hasattr(element, 'content') and element.content:
                content = element.content
                
                # Extract author names
                for pattern in self.patterns['author_names']:
                    matches = re.findall(pattern, content)
                    authors.extend(matches)
                
                # Extract affiliations (typically contain university, institute, etc.)
                affiliation_indicators = [
                    r'\b(?:university|institute|college|department|school)\s+of\s+\w+',
                    r'\b\w+\s+(?:university|institute|college|department|school)\b',
                    r'\b(?:university|institute|college)\s+\w+',
                ]
                
                for pattern in affiliation_indicators:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    affiliations.extend(matches)
        
        return authors, affiliations
    
    def _map_authors_to_affiliations(
        self, 
        authors: List[str], 
        affiliations: List[str], 
        elements: List[DocumentElement]
    ) -> Dict[str, List[str]]:
        """Map authors to their affiliations."""
        mapping = {}
        
        # Simple mapping based on proximity in text
        full_text = self._extract_full_text(elements[:20])  # Check beginning of document
        
        for author in authors:
            author_affiliations = []
            
            # Find author position in text
            author_pos = full_text.find(author)
            if author_pos != -1:
                # Look for affiliations within 500 characters of author
                search_start = max(0, author_pos - 250)
                search_end = min(len(full_text), author_pos + len(author) + 250)
                search_text = full_text[search_start:search_end]
                
                for affiliation in affiliations:
                    if affiliation.lower() in search_text.lower():
                        author_affiliations.append(affiliation)
            
            if author_affiliations:
                mapping[author] = author_affiliations
        
        return mapping
    
    def _find_corresponding_author(self, elements: List[DocumentElement]) -> Optional[str]:
        """Find corresponding author information."""
        full_text = self._extract_full_text(elements[:20])
        
        # Look for corresponding author indicators
        corresponding_patterns = [
            r'corresponding\s+author[:\s]*([^.]+)',
            r'correspondence[:\s]*([^.]+)',
            r'contact[:\s]*([^.]+)',
        ]
        
        for pattern in corresponding_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_orcid_ids(self, elements: List[DocumentElement]) -> Dict[str, str]:
        """Extract ORCID IDs from document."""
        orcid_map = {}
        full_text = self._extract_full_text(elements[:20])
        
        # ORCID pattern
        orcid_pattern = r'(?:ORCID|orcid)[:\s]*([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])'
        matches = re.finditer(orcid_pattern, full_text, re.IGNORECASE)
        
        for i, match in enumerate(matches):
            # Simple mapping - would need more sophisticated author-ORCID association
            orcid_map[f"author_{i+1}"] = match.group(1)
        
        return orcid_map
    
    def _extract_author_emails(self, elements: List[DocumentElement]) -> Dict[str, str]:
        """Extract author email addresses."""
        email_map = {}
        full_text = self._extract_full_text(elements[:20])
        
        # Find email patterns
        emails = re.findall(self.patterns['emails'], full_text)
        
        for i, email in enumerate(emails):
            # Simple mapping - would need more sophisticated author-email association
            email_map[f"author_{i+1}"] = email
        
        return email_map
    
    def _calculate_author_validation_score(
        self, 
        authors: List[str], 
        affiliations: List[str],
        author_affiliation_mapping: Dict[str, List[str]], 
        corresponding_author: Optional[str],
        orcid_ids: Dict[str, str], 
        email_addresses: Dict[str, str]
    ) -> float:
        """Calculate author information validation score."""
        score = 0.0
        max_score = 0.0
        
        # Authors present
        max_score += 30
        if authors:
            score += min(30, len(authors) * 10)  # Up to 30 points for having authors
        
        # Affiliations present
        max_score += 20
        if affiliations:
            score += min(20, len(affiliations) * 5)  # Up to 20 points for affiliations
        
        # Author-affiliation mapping
        max_score += 20
        if author_affiliation_mapping:
            mapped_authors = len(author_affiliation_mapping)
            total_authors = len(authors)
            if total_authors > 0:
                score += (mapped_authors / total_authors) * 20
        
        # Corresponding author
        max_score += 10
        if corresponding_author:
            score += 10
        
        # ORCID IDs
        max_score += 10
        if orcid_ids:
            score += min(10, len(orcid_ids) * 2)
        
        # Email addresses
        max_score += 10
        if email_addresses:
            score += min(10, len(email_addresses) * 2)
        
        return (score / max_score) * 100 if max_score > 0 else 0
    
    def _identify_author_formatting_issues(
        self, 
        authors: List[str], 
        affiliations: List[str], 
        elements: List[DocumentElement]
    ) -> List[str]:
        """Identify formatting issues in author information."""
        issues = []
        
        if not authors:
            issues.append("No author information found")
        
        if not affiliations:
            issues.append("No affiliation information found")
        
        # Check for inconsistent author name formatting
        if authors:
            name_formats = []
            for author in authors:
                if ',' in author:
                    name_formats.append('last_first')
                else:
                    name_formats.append('first_last')
            
            if len(set(name_formats)) > 1:
                issues.append("Inconsistent author name formatting")
        
        # Check for incomplete affiliations
        incomplete_affiliations = [aff for aff in affiliations 
                                 if len(aff.split()) < 3]  # Very short affiliations
        if incomplete_affiliations:
            issues.append("Some affiliations appear incomplete")
        
        return issues
    
    def _calculate_readability_metrics(self, text: str) -> Dict[str, float]:
        """Calculate readability metrics for text."""
        if not text:
            return {}
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        words = text.split()
        
        if not sentences or not words:
            return {}
        
        # Basic metrics
        avg_sentence_length = len(words) / len(sentences)
        
        # Count syllables (approximation)
        def count_syllables(word):
            word = word.lower()
            vowels = 'aeiouy'
            syllable_count = 0
            prev_was_vowel = False
            
            for char in word:
                is_vowel = char in vowels
                if is_vowel and not prev_was_vowel:
                    syllable_count += 1
                prev_was_vowel = is_vowel
            
            # Handle silent e
            if word.endswith('e') and syllable_count > 1:
                syllable_count -= 1
            
            return max(1, syllable_count)
        
        total_syllables = sum(count_syllables(word) for word in words)
        avg_syllables_per_word = total_syllables / len(words)
        
        # Flesch-Kincaid Grade Level
        flesch_kincaid = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59
        
        # Flesch Reading Ease
        flesch_reading_ease = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
        
        return {
            'flesch_kincaid': max(0, min(100, 100 - flesch_kincaid * 5)),  # Convert to 0-100 score
            'flesch_reading_ease': max(0, min(100, flesch_reading_ease)),
            'avg_sentence_length': avg_sentence_length,
            'avg_syllables_per_word': avg_syllables_per_word
        }
    
    def _analyze_text_coherence(self, elements: List[DocumentElement]) -> Dict[str, Any]:
        """Analyze text coherence and flow."""
        # Extract paragraphs
        paragraphs = []
        for element in elements:
            if (hasattr(element, 'content') and element.content and 
                hasattr(element, 'element_type') and 
                element.element_type == ElementType.PARAGRAPH):
                paragraphs.append(element.content)
        
        if len(paragraphs) < 2:
            return {'overall_coherence': 50.0}
        
        # Simple coherence analysis based on transition words and repeated terms
        transition_words = [
            'however', 'furthermore', 'moreover', 'therefore', 'consequently',
            'nevertheless', 'nonetheless', 'additionally', 'similarly', 'conversely'
        ]
        
        coherence_scores = []
        
        for i in range(len(paragraphs) - 1):
            current_para = paragraphs[i].lower()
            next_para = paragraphs[i + 1].lower()
            
            # Check for transition words
            transition_score = sum(1 for word in transition_words 
                                 if word in next_para[:100])  # Check first 100 chars
            
            # Check for repeated key terms
            current_words = set(re.findall(r'\b\w{4,}\b', current_para))
            next_words = set(re.findall(r'\b\w{4,}\b', next_para))
            
            common_words = len(current_words & next_words)
            repetition_score = min(5, common_words)
            
            paragraph_coherence = (transition_score * 20 + repetition_score * 10)
            coherence_scores.append(min(100, paragraph_coherence))
        
        overall_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 50
        
        return {
            'overall_coherence': overall_coherence,
            'paragraph_count': len(paragraphs),
            'avg_paragraph_coherence': overall_coherence
        }
    
    def _analyze_academic_tone(self, text: str) -> float:
        """Analyze academic tone of text."""
        if not text:
            return 0.0
        
        academic_indicators = {
            'formal_verbs': ['demonstrate', 'indicate', 'suggest', 'reveal', 'establish'],
            'hedging': ['might', 'could', 'may', 'appear', 'seem', 'likely'],
            'citation_phrases': ['according to', 'as noted by', 'previous research'],
            'academic_vocabulary': self.patterns['academic_words']
        }
        
        text_lower = text.lower()
        words = text_lower.split()
        
        score = 0.0
        
        # Check for academic vocabulary
        academic_word_count = sum(1 for word in words 
                                if word in [w.lower() for w in academic_indicators['academic_vocabulary']])
        vocab_score = min(30, (academic_word_count / len(words)) * 1000)
        score += vocab_score
        
        # Check for formal verbs
        formal_verb_count = sum(1 for verb in academic_indicators['formal_verbs'] 
                              if verb in text_lower)
        formal_score = min(25, formal_verb_count * 5)
        score += formal_score
        
        # Check for appropriate hedging
        hedging_count = sum(1 for hedge in academic_indicators['hedging'] 
                          if hedge in text_lower)
        hedging_score = min(20, hedging_count * 3)
        score += hedging_score
        
        # Check for citation integration
        citation_phrase_count = sum(1 for phrase in academic_indicators['citation_phrases'] 
                                  if phrase in text_lower)
        citation_score = min(25, citation_phrase_count * 8)
        score += citation_score
        
        return min(100, score)
    
    def _analyze_vocabulary_sophistication(self, text: str) -> Dict[str, Any]:
        """Analyze vocabulary sophistication."""
        if not text:
            return {'sophistication_score': 0.0}
        
        words = re.findall(r'\b\w+\b', text.lower())
        
        if not words:
            return {'sophistication_score': 0.0}
        
        # Count long words (7+ characters)
        long_words = [w for w in words if len(w) >= 7]
        long_word_ratio = len(long_words) / len(words)
        
        # Count unique words (vocabulary diversity)
        unique_words = len(set(words))
        vocabulary_diversity = unique_words / len(words)
        
        # Count academic/sophisticated words
        academic_words_lower = [w.lower() for w in self.patterns['academic_words']]
        academic_word_count = sum(1 for w in words if w in academic_words_lower)
        academic_ratio = academic_word_count / len(words)
        
        # Calculate sophistication score
        sophistication_score = (
            long_word_ratio * 40 +
            vocabulary_diversity * 30 +
            academic_ratio * 30
        ) * 100
        
        return {
            'sophistication_score': min(100, sophistication_score),
            'long_word_ratio': long_word_ratio,
            'vocabulary_diversity': vocabulary_diversity,
            'academic_ratio': academic_ratio,
            'total_words': len(words),
            'unique_words': unique_words
        }
    
    def _analyze_sentence_variety(self, text: str) -> Dict[str, Any]:
        """Analyze sentence variety and structure."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return {'variety_score': 0.0}
        
        # Analyze sentence lengths
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        
        # Calculate variety metrics
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        length_variance = sum((length - avg_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)
        length_variety = math.sqrt(length_variance) / avg_length if avg_length > 0 else 0
        
        # Check for sentence structure variety
        structure_types = []
        for sentence in sentences:
            if sentence.count(',') >= 2:
                structure_types.append('complex')
            elif ',' in sentence or 'and' in sentence or 'but' in sentence:
                structure_types.append('compound')
            else:
                structure_types.append('simple')
        
        structure_variety = len(set(structure_types)) / len(structure_types) if structure_types else 0
        
        # Overall variety score
        variety_score = (length_variety * 50 + structure_variety * 50)
        
        return {
            'variety_score': min(100, variety_score * 100),
            'avg_sentence_length': avg_length,
            'length_variety': length_variety,
            'structure_variety': structure_variety,
            'sentence_count': len(sentences)
        }
    
    def _analyze_passive_voice_usage(self, text: str) -> float:
        """Analyze passive voice usage (lower score for excessive passive voice)."""
        if not text:
            return 50.0
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 50.0
        
        passive_count = 0
        
        for sentence in sentences:
            # Count passive voice patterns
            for pattern in self.patterns['passive_voice']:
                if re.search(pattern, sentence, re.IGNORECASE):
                    passive_count += 1
                    break  # Count each sentence only once
        
        passive_ratio = passive_count / len(sentences)
        
        # Optimal passive voice usage: 10-20%
        if 0.1 <= passive_ratio <= 0.2:
            return 100.0
        elif passive_ratio < 0.1:
            return 80.0  # Too little passive voice (might be too informal)
        elif passive_ratio < 0.3:
            return 60.0
        elif passive_ratio < 0.5:
            return 40.0
        else:
            return 20.0  # Too much passive voice
    
    def _generate_writing_recommendations(
        self, 
        metric_scores: Dict[WritingQualityMetric, float]
    ) -> List[str]:
        """Generate writing quality recommendations."""
        recommendations = []
        
        for metric, score in metric_scores.items():
            if score < 60:  # Below acceptable threshold
                if metric == WritingQualityMetric.READABILITY:
                    recommendations.append("Simplify sentence structure and reduce complex vocabulary for better readability")
                elif metric == WritingQualityMetric.COHERENCE:
                    recommendations.append("Improve text flow with better transitions between paragraphs")
                elif metric == WritingQualityMetric.ACADEMIC_TONE:
                    recommendations.append("Use more formal academic language and vocabulary")
                elif metric == WritingQualityMetric.CITATION_DENSITY:
                    recommendations.append("Include more citations to support claims and arguments")
                elif metric == WritingQualityMetric.VOCABULARY_SOPHISTICATION:
                    recommendations.append("Use more sophisticated academic vocabulary where appropriate")
                elif metric == WritingQualityMetric.SENTENCE_VARIETY:
                    recommendations.append("Vary sentence length and structure for better engagement")
                elif metric == WritingQualityMetric.PASSIVE_VOICE_USAGE:
                    recommendations.append("Balance active and passive voice usage (aim for 10-20% passive)")
        
        return recommendations
    
    def _identify_writing_strengths(self, metric_scores: Dict[WritingQualityMetric, float]) -> List[str]:
        """Identify writing strengths."""
        strengths = []
        
        for metric, score in metric_scores.items():
            if score >= 80:  # High score
                if metric == WritingQualityMetric.READABILITY:
                    strengths.append("Excellent readability and clarity")
                elif metric == WritingQualityMetric.COHERENCE:
                    strengths.append("Strong coherence and logical flow")
                elif metric == WritingQualityMetric.ACADEMIC_TONE:
                    strengths.append("Appropriate academic tone and formality")
                elif metric == WritingQualityMetric.CITATION_DENSITY:
                    strengths.append("Good integration of citations and references")
                elif metric == WritingQualityMetric.VOCABULARY_SOPHISTICATION:
                    strengths.append("Sophisticated and appropriate vocabulary")
                elif metric == WritingQualityMetric.SENTENCE_VARIETY:
                    strengths.append("Good variety in sentence structure")
                elif metric == WritingQualityMetric.PASSIVE_VOICE_USAGE:
                    strengths.append("Appropriate balance of active and passive voice")
        
        return strengths
    
    def _identify_writing_weaknesses(self, metric_scores: Dict[WritingQualityMetric, float]) -> List[str]:
        """Identify writing weaknesses."""
        weaknesses = []
        
        for metric, score in metric_scores.items():
            if score < 50:  # Low score
                if metric == WritingQualityMetric.READABILITY:
                    weaknesses.append("Poor readability - text is difficult to understand")
                elif metric == WritingQualityMetric.COHERENCE:
                    weaknesses.append("Lack of coherence and logical flow between sections")
                elif metric == WritingQualityMetric.ACADEMIC_TONE:
                    weaknesses.append("Informal tone inappropriate for academic writing")
                elif metric == WritingQualityMetric.CITATION_DENSITY:
                    weaknesses.append("Insufficient citations to support claims")
                elif metric == WritingQualityMetric.VOCABULARY_SOPHISTICATION:
                    weaknesses.append("Limited use of academic vocabulary")
                elif metric == WritingQualityMetric.SENTENCE_VARIETY:
                    weaknesses.append("Monotonous sentence structure")
                elif metric == WritingQualityMetric.PASSIVE_VOICE_USAGE:
                    weaknesses.append("Excessive or insufficient use of passive voice")
        
        return weaknesses
    
    def _assess_section_completeness(
        self, 
        imrad_section: IMRADSection, 
        section_classifications: List[IMRADClassificationResult],
        elements: List[DocumentElement]
    ) -> float:
        """Assess completeness of a specific IMRAD section."""
        # Find classifications for this section type
        section_results = [cls for cls in section_classifications 
                          if cls.section_type == imrad_section and cls.confidence > 0.3]
        
        if not section_results:
            return 0.0  # Section not found
        
        # Assess based on word count and content quality
        total_word_count = sum(result.word_count for result in section_results)
        
        # Expected word counts for different sections (rough estimates)
        expected_word_counts = {
            IMRADSection.ABSTRACT: (150, 300),
            IMRADSection.INTRODUCTION: (500, 1500),
            IMRADSection.METHODS: (300, 1000),
            IMRADSection.RESULTS: (500, 1500),
            IMRADSection.DISCUSSION: (500, 1500),
            IMRADSection.CONCLUSION: (200, 500),
            IMRADSection.REFERENCES: (100, 2000),  # Variable based on reference count
        }
        
        min_expected, max_expected = expected_word_counts.get(imrad_section, (100, 500))
        
        # Calculate completeness score based on word count
        if total_word_count < min_expected * 0.5:
            return 20.0  # Very incomplete
        elif total_word_count < min_expected:
            return 50.0  # Somewhat incomplete
        elif total_word_count <= max_expected:
            return 100.0  # Complete
        else:
            return 90.0  # Complete but possibly too long
    
    def _calculate_content_balance_score(self, section_completeness: Dict[IMRADSection, float]) -> float:
        """Calculate balance score between different sections."""
        if len(section_completeness) < 3:
            return 50.0  # Not enough sections to assess balance
        
        completeness_values = list(section_completeness.values())
        
        # Calculate coefficient of variation (lower is better for balance)
        mean_completeness = sum(completeness_values) / len(completeness_values)
        
        if mean_completeness == 0:
            return 0.0
        
        variance = sum((x - mean_completeness) ** 2 for x in completeness_values) / len(completeness_values)
        std_dev = math.sqrt(variance)
        coefficient_of_variation = std_dev / mean_completeness
        
        # Convert to balance score (lower CV = higher balance score)
        balance_score = max(0, 100 - coefficient_of_variation * 100)
        
        return balance_score
    
    def _generate_completeness_recommendations(
        self,
        missing_sections: List[IMRADSection],
        underdeveloped_sections: List[IMRADSection],
        essential_elements: Dict[str, bool],
        content_balance_score: float
    ) -> List[str]:
        """Generate recommendations for improving content completeness."""
        recommendations = []
        
        # Missing sections
        for section in missing_sections:
            recommendations.append(f"Add missing {section.value} section")
        
        # Underdeveloped sections
        for section in underdeveloped_sections:
            recommendations.append(f"Expand {section.value} section with more detail")
        
        # Missing essential elements
        for element, present in essential_elements.items():
            if not present:
                recommendations.append(f"Add {element.replace('_', ' ')}")
        
        # Content balance
        if content_balance_score < 60:
            recommendations.append("Balance content distribution across sections")
        
        return recommendations
    
    def _get_section_content_suggestions(self, section: IMRADSection) -> List[str]:
        """Get specific content suggestions for a missing section."""
        suggestions = {
            IMRADSection.ABSTRACT: [
                "Provide brief background and motivation",
                "Describe methodology concisely",
                "Summarize key findings",
                "State implications or conclusions"
            ],
            IMRADSection.INTRODUCTION: [
                "Review relevant literature",
                "Identify research gap",
                "State research objectives",
                "Outline paper structure"
            ],
            IMRADSection.METHODS: [
                "Describe experimental setup",
                "Detail data collection procedures",
                "Explain analysis methods",
                "Address ethical considerations if applicable"
            ],
            IMRADSection.RESULTS: [
                "Present findings systematically",
                "Include appropriate figures and tables",
                "Describe statistical analyses",
                "Avoid interpretation (save for discussion)"
            ],
            IMRADSection.DISCUSSION: [
                "Interpret results in context",
                "Compare with previous research",
                "Discuss limitations",
                "Suggest future research directions"
            ],
            IMRADSection.CONCLUSION: [
                "Summarize key findings",
                "Restate significance",
                "Provide final thoughts",
                "Avoid introducing new information"
            ],
            IMRADSection.REFERENCES: [
                "Include all cited sources",
                "Use consistent formatting",
                "Ensure references are recent and relevant",
                "Check for completeness of bibliographic information"
            ]
        }
        
        return suggestions.get(section, ["Develop this section with appropriate content"])
    
    def _calculate_overall_academic_score(self, analysis_results: Dict[str, Any]) -> float:
        """Calculate overall academic quality score."""
        scores = []
        weights = []
        
        # IMRAD structure completeness
        imrad_analysis = analysis_results.get('imrad_classification', {})
        if 'completeness_score' in imrad_analysis:
            scores.append(imrad_analysis['completeness_score'])
            weights.append(0.15)
        
        # Abstract quality
        abstract_quality = analysis_results.get('abstract_quality')
        if abstract_quality:
            scores.append(abstract_quality.overall_score)
            weights.append(0.15)
        
        # Writing quality
        writing_quality = analysis_results.get('writing_quality')
        if writing_quality:
            scores.append(writing_quality.overall_score)
            weights.append(0.20)
        
        # Reference quality
        reference_analysis = analysis_results.get('reference_analysis')
        if reference_analysis:
            scores.append(reference_analysis.reference_quality_score)
            weights.append(0.15)
        
        # Author information completeness
        author_analysis = analysis_results.get('author_analysis')
        if author_analysis:
            scores.append(author_analysis.validation_score)
            weights.append(0.10)
        
        # Content completeness
        content_completeness = analysis_results.get('content_completeness')
        if content_completeness:
            scores.append(content_completeness.overall_completeness)
            weights.append(0.20)
        
        # Equation analysis (if applicable)
        equation_analysis = analysis_results.get('equation_analysis')
        if equation_analysis and equation_analysis.equations:
            equation_score = (equation_analysis.complexity_score + 
                            equation_analysis.consistency_score) / 2
            scores.append(equation_score)
            weights.append(0.05)
        
        # Calculate weighted average
        if scores and weights:
            # Normalize weights
            total_weight = sum(weights)
            normalized_weights = [w / total_weight for w in weights]
            
            overall_score = sum(score * weight for score, weight in zip(scores, normalized_weights))
            return overall_score
        
        return 0.0
    
    def _generate_classification_evidence(
        self, 
        section_type: IMRADSection, 
        title: str, 
        content: str
    ) -> List[str]:
        """Generate evidence for section classification."""
        evidence = []
        
        # Title evidence
        if section_type != IMRADSection.UNKNOWN:
            patterns = self.patterns.get(section_type.value, [])
            for pattern in patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    evidence.append(f"Title matches {section_type.value} pattern: '{pattern}'")
        
        # Content evidence
        content_indicators = {
            IMRADSection.METHODS: self.patterns['method_indicators'],
            IMRADSection.RESULTS: self.patterns['result_indicators'],
            IMRADSection.DISCUSSION: self.patterns['discussion_indicators']
        }
        
        if section_type in content_indicators:
            for indicator in content_indicators[section_type]:
                matches = re.findall(indicator, content, re.IGNORECASE)
                if matches:
                    evidence.append(f"Content contains {section_type.value} indicators: {matches[:3]}")
        
        return evidence[:5]  # Limit to top 5 pieces of evidence
    
    def _extract_key_phrases(self, content: str, section_type: IMRADSection) -> List[str]:
        """Extract key phrases relevant to the section type."""
        # Simple extraction based on section type
        phrases = []
        
        if section_type == IMRADSection.METHODS:
            method_phrases = re.findall(r'\b(?:we|the)\s+(?:used|employed|applied|implemented)\s+\w+(?:\s+\w+){0,3}', 
                                      content, re.IGNORECASE)
            phrases.extend(method_phrases[:5])
        
        elif section_type == IMRADSection.RESULTS:
            result_phrases = re.findall(r'\b(?:results?|findings?|analysis)\s+(?:show|reveal|indicate|demonstrate)\s+\w+(?:\s+\w+){0,3}', 
                                      content, re.IGNORECASE)
            phrases.extend(result_phrases[:5])
        
        elif section_type == IMRADSection.DISCUSSION:
            discussion_phrases = re.findall(r'\b(?:this|these)\s+(?:results?|findings?)\s+(?:suggest|indicate|imply)\s+\w+(?:\s+\w+){0,3}', 
                                          content, re.IGNORECASE)
            phrases.extend(discussion_phrases[:5])
        
        return phrases