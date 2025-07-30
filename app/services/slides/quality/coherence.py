"""
Content Coherence Checker for SlideGenie presentations.

This module assesses the logical flow and content coherence across slides,
ensuring smooth progression of ideas and consistent terminology.
"""
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation
from .base import QualityChecker, QualityDimension, QualityIssue


class CoherenceChecker(QualityChecker):
    """
    Checks content coherence across presentation slides.
    """
    
    def __init__(self):
        """Initialize coherence checker."""
        # Download required NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            self.stop_words = set(stopwords.words('english'))
        except:
            self.stop_words = set()
        
        # Academic transition phrases that indicate good flow
        self.transition_phrases = {
            'introduction': [
                'first', 'to begin', 'initially', 'let us start',
                'introduction', 'overview', 'outline'
            ],
            'continuation': [
                'furthermore', 'moreover', 'additionally', 'also',
                'next', 'then', 'following', 'subsequently'
            ],
            'contrast': [
                'however', 'but', 'although', 'despite', 'whereas',
                'on the other hand', 'in contrast', 'nevertheless'
            ],
            'example': [
                'for example', 'for instance', 'such as', 'specifically',
                'to illustrate', 'namely', 'in particular'
            ],
            'conclusion': [
                'in conclusion', 'to summarize', 'therefore', 'thus',
                'finally', 'in summary', 'to conclude', 'overall'
            ],
            'evidence': [
                'research shows', 'studies indicate', 'evidence suggests',
                'according to', 'as shown', 'demonstrated by'
            ]
        }
        
        # Expected presentation structure
        self.expected_sections = [
            'introduction', 'background', 'motivation', 'objectives',
            'methodology', 'methods', 'approach', 'results', 'findings',
            'discussion', 'conclusion', 'future work', 'references'
        ]
    
    @property
    def dimension(self) -> QualityDimension:
        """Return the quality dimension."""
        return QualityDimension.COHERENCE
    
    @property
    def weight(self) -> float:
        """Weight of coherence in overall quality."""
        return 1.5  # Higher weight as coherence is crucial
    
    def check(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """
        Check content coherence across slides.
        
        Returns:
            Tuple of (score, issues, metadata)
        """
        issues = []
        metadata = {}
        
        # Extract text content from all slides
        slide_texts = self._extract_slide_texts(slides)
        
        # Check logical flow
        flow_score, flow_issues = self._check_logical_flow(slides, slide_texts)
        issues.extend(flow_issues)
        
        # Check terminology consistency
        term_score, term_issues, term_metadata = self._check_terminology_consistency(slide_texts)
        issues.extend(term_issues)
        metadata['terminology'] = term_metadata
        
        # Check section structure
        structure_score, structure_issues = self._check_section_structure(slides)
        issues.extend(structure_issues)
        
        # Check topic coherence
        topic_score, topic_issues, topic_metadata = self._check_topic_coherence(slide_texts)
        issues.extend(topic_issues)
        metadata['topics'] = topic_metadata
        
        # Check transition quality
        transition_score, transition_issues = self._check_transitions(slide_texts)
        issues.extend(transition_issues)
        
        # Calculate overall coherence score
        overall_score = (
            flow_score * 0.3 +
            term_score * 0.2 +
            structure_score * 0.2 +
            topic_score * 0.2 +
            transition_score * 0.1
        )
        
        # Add metadata
        metadata.update({
            'flow_score': flow_score,
            'terminology_score': term_score,
            'structure_score': structure_score,
            'topic_score': topic_score,
            'transition_score': transition_score,
            'slide_count': len(slides),
            'avg_words_per_slide': sum(len(text.split()) for text in slide_texts) / len(slides) if slides else 0
        })
        
        # Identify strengths
        strengths = []
        if flow_score >= 0.8:
            strengths.append("Excellent logical progression")
        if term_score >= 0.8:
            strengths.append("Consistent terminology usage")
        if structure_score >= 0.8:
            strengths.append("Well-organized section structure")
        
        metadata['strengths'] = strengths
        
        return overall_score, issues, metadata
    
    def _extract_slide_texts(self, slides: List[SlideResponse]) -> List[str]:
        """Extract text content from slides."""
        texts = []
        
        for slide in slides:
            text_parts = []
            
            # Add title
            if slide.title:
                text_parts.append(slide.title)
            
            # Extract text from content
            if slide.content:
                # Add subtitle if present
                if 'subtitle' in slide.content:
                    text_parts.append(slide.content['subtitle'])
                
                # Extract body text
                if 'body' in slide.content:
                    for item in slide.content['body']:
                        if item.get('type') == 'text':
                            text_parts.append(item.get('content', ''))
                        elif item.get('type') == 'bullet_list':
                            for bullet in item.get('items', []):
                                text_parts.append(bullet)
            
            # Add speaker notes
            if slide.speaker_notes:
                text_parts.append(slide.speaker_notes)
            
            texts.append(' '.join(text_parts))
        
        return texts
    
    def _check_logical_flow(
        self,
        slides: List[SlideResponse],
        slide_texts: List[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check logical flow between slides."""
        issues = []
        flow_scores = []
        
        for i in range(1, len(slides)):
            prev_text = slide_texts[i-1]
            curr_text = slide_texts[i]
            
            # Check for abrupt topic changes
            prev_keywords = self._extract_keywords(prev_text)
            curr_keywords = self._extract_keywords(curr_text)
            
            # Calculate keyword overlap
            if prev_keywords and curr_keywords:
                overlap = len(prev_keywords & curr_keywords) / min(len(prev_keywords), len(curr_keywords))
                flow_scores.append(overlap)
                
                if overlap < 0.1:  # Too little connection
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="major",
                        slide_number=i + 1,
                        description=f"Abrupt topic change from slide {i} to {i+1}",
                        suggestion="Add transitional content or reorder slides for better flow"
                    ))
            
            # Check for missing transitions
            if not self._has_transition_phrase(curr_text):
                if i > 1 and i < len(slides) - 2:  # Not first/last few slides
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description="Missing transition phrase",
                        suggestion="Consider adding transition phrases like 'Furthermore', 'Next', etc."
                    ))
        
        # Calculate average flow score
        avg_flow = sum(flow_scores) / len(flow_scores) if flow_scores else 0.7
        
        return avg_flow, issues
    
    def _check_terminology_consistency(
        self,
        slide_texts: List[str]
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """Check for consistent use of terminology."""
        issues = []
        metadata = {}
        
        # Extract all terms (nouns and technical terms)
        all_terms = []
        for text in slide_texts:
            terms = self._extract_technical_terms(text)
            all_terms.extend(terms)
        
        # Find potential inconsistencies
        term_variations = self._find_term_variations(all_terms)
        
        inconsistency_count = 0
        for base_term, variations in term_variations.items():
            if len(variations) > 1:
                inconsistency_count += 1
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description=f"Inconsistent terminology: {', '.join(variations)}",
                    suggestion=f"Use consistent terminology throughout (e.g., always use '{base_term}')"
                ))
        
        # Calculate consistency score
        unique_terms = len(set(all_terms))
        consistency_score = 1.0 - (inconsistency_count / unique_terms) if unique_terms > 0 else 1.0
        
        metadata['total_terms'] = len(all_terms)
        metadata['unique_terms'] = unique_terms
        metadata['inconsistencies'] = inconsistency_count
        
        return consistency_score, issues, metadata
    
    def _check_section_structure(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check if presentation follows expected academic structure."""
        issues = []
        found_sections = []
        
        # Identify sections based on slide titles and content
        for i, slide in enumerate(slides):
            if slide.title:
                title_lower = slide.title.lower()
                for section in self.expected_sections:
                    if section in title_lower:
                        found_sections.append((section, i))
                        break
        
        # Check for missing critical sections
        found_section_names = {s[0] for s in found_sections}
        critical_sections = {'introduction', 'conclusion'}
        missing_critical = critical_sections - found_section_names
        
        for section in missing_critical:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="major",
                description=f"Missing {section} section",
                suggestion=f"Add a clear {section} section to the presentation"
            ))
        
        # Check section order
        if len(found_sections) >= 2:
            # Check if introduction comes first
            if found_sections[0][0] not in ['introduction', 'title', 'overview']:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    slide_number=1,
                    description="Presentation doesn't start with introduction",
                    suggestion="Begin with an introduction or overview slide"
                ))
            
            # Check if conclusion comes last
            last_content_slide = len(slides) - 2  # Assuming last is references
            conclusion_slides = [i for s, i in found_sections if 'conclusion' in s]
            if conclusion_slides and conclusion_slides[0] < last_content_slide - 2:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description="Conclusion appears too early",
                    suggestion="Move conclusion closer to the end"
                ))
        
        # Calculate structure score
        expected_count = min(5, len(self.expected_sections))  # At least 5 sections
        structure_score = len(found_section_names) / expected_count
        structure_score = min(1.0, structure_score)
        
        return structure_score, issues
    
    def _check_topic_coherence(
        self,
        slide_texts: List[str]
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """Check overall topic coherence using keyword analysis."""
        issues = []
        metadata = {}
        
        # Extract keywords from entire presentation
        all_text = ' '.join(slide_texts)
        main_keywords = self._extract_keywords(all_text, top_n=10)
        
        # Check keyword distribution across slides
        slide_keyword_counts = []
        for i, text in enumerate(slide_texts):
            slide_keywords = self._extract_keywords(text)
            main_keyword_count = len(slide_keywords & main_keywords)
            slide_keyword_counts.append(main_keyword_count)
            
            # Flag slides with no connection to main topics
            if main_keyword_count == 0 and len(text.split()) > 20:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description="Slide appears disconnected from main topics",
                    suggestion="Ensure slide content relates to presentation theme"
                ))
        
        # Calculate topic coherence score
        avg_keyword_presence = sum(slide_keyword_counts) / len(slide_keyword_counts) if slide_keyword_counts else 0
        max_possible = min(3, len(main_keywords))  # Expect at least 3 main keywords per slide
        coherence_score = min(1.0, avg_keyword_presence / max_possible) if max_possible > 0 else 0.7
        
        metadata['main_keywords'] = list(main_keywords)
        metadata['avg_keywords_per_slide'] = avg_keyword_presence
        
        return coherence_score, issues, metadata
    
    def _check_transitions(self, slide_texts: List[str]) -> Tuple[float, List[QualityIssue]]:
        """Check quality of transitions between slides."""
        issues = []
        transition_count = 0
        
        for i, text in enumerate(slide_texts):
            if self._has_transition_phrase(text):
                transition_count += 1
        
        # Calculate transition score
        expected_transitions = max(1, len(slide_texts) // 3)  # Expect transitions in 1/3 of slides
        transition_score = min(1.0, transition_count / expected_transitions)
        
        if transition_score < 0.5:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Limited use of transition phrases",
                suggestion="Add transition phrases to improve flow between topics"
            ))
        
        return transition_score, issues
    
    def _extract_keywords(self, text: str, top_n: int = 15) -> Set[str]:
        """Extract keywords from text."""
        # Tokenize and filter
        words = word_tokenize(text.lower())
        words = [w for w in words if w.isalnum() and len(w) > 3]
        words = [w for w in words if w not in self.stop_words]
        
        # Get most common words
        word_freq = Counter(words)
        keywords = {word for word, _ in word_freq.most_common(top_n)}
        
        return keywords
    
    def _extract_technical_terms(self, text: str) -> List[str]:
        """Extract technical terms and important nouns."""
        # Simple extraction based on capitalization and patterns
        terms = []
        
        # Find capitalized terms (not at sentence start)
        sentences = sent_tokenize(text)
        for sentence in sentences:
            words = sentence.split()
            for i, word in enumerate(words[1:], 1):  # Skip first word
                if word and word[0].isupper() and word.lower() not in self.stop_words:
                    terms.append(word)
        
        # Find acronyms
        acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
        terms.extend(acronyms)
        
        # Find hyphenated terms
        hyphenated = re.findall(r'\b\w+(?:-\w+)+\b', text)
        terms.extend(hyphenated)
        
        return terms
    
    def _find_term_variations(self, terms: List[str]) -> Dict[str, Set[str]]:
        """Find potential variations of the same term."""
        variations = defaultdict(set)
        
        # Group by lowercase base
        for term in terms:
            base = term.lower().replace('-', '').replace('_', '')
            variations[base].add(term)
        
        # Filter out single-use terms
        return {k: v for k, v in variations.items() if len(v) > 1}
    
    def _has_transition_phrase(self, text: str) -> bool:
        """Check if text contains transition phrases."""
        text_lower = text.lower()
        for category, phrases in self.transition_phrases.items():
            for phrase in phrases:
                if phrase in text_lower:
                    return True
        return False