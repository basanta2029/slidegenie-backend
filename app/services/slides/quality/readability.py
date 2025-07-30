"""
Readability Scorer for SlideGenie presentations.

This module assesses the readability and clarity of slide content,
ensuring it's appropriate for the target audience.
"""
import re
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation
from .base import QualityChecker, QualityDimension, QualityIssue


class ReadabilityScorer(QualityChecker):
    """
    Scores readability and clarity of presentation content.
    """
    
    def __init__(self):
        """Initialize readability scorer."""
        # Academic level requirements
        self.level_requirements = {
            'undergraduate': {
                'avg_sentence_length': 20,
                'max_sentence_length': 35,
                'complex_words_ratio': 0.15,
                'technical_terms_ratio': 0.1
            },
            'graduate': {
                'avg_sentence_length': 25,
                'max_sentence_length': 40,
                'complex_words_ratio': 0.25,
                'technical_terms_ratio': 0.2
            },
            'research': {
                'avg_sentence_length': 30,
                'max_sentence_length': 50,
                'complex_words_ratio': 0.35,
                'technical_terms_ratio': 0.3
            }
        }
        
        # Common academic words (simplified list)
        self.academic_words = {
            'analysis', 'approach', 'concept', 'data', 'demonstrate',
            'evaluate', 'evidence', 'factor', 'hypothesis', 'indicate',
            'method', 'process', 'research', 'result', 'significant',
            'study', 'theory', 'variable', 'furthermore', 'however',
            'therefore', 'moreover', 'consequently', 'nevertheless'
        }
        
        # Readability issues to detect
        self.readability_patterns = {
            'passive_voice': r'\b(is|are|was|were|been|being)\s+\w+ed\b',
            'long_sentences': 40,  # words per sentence
            'complex_phrases': [
                'in order to', 'due to the fact that', 'it is important to note',
                'it should be noted that', 'as a matter of fact'
            ],
            'jargon_indicators': [
                'utilize', 'facilitate', 'implement', 'optimize',
                'paradigm', 'leverage', 'synergy'
            ]
        }
    
    @property
    def dimension(self) -> QualityDimension:
        """Return the quality dimension."""
        return QualityDimension.READABILITY
    
    @property
    def weight(self) -> float:
        """Weight of readability in overall quality."""
        return 1.0
    
    def check(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """
        Check readability of presentation content.
        
        Returns:
            Tuple of (score, issues, metadata)
        """
        issues = []
        metadata = {}
        
        # Extract text content
        all_text = self._extract_all_text(slides)
        
        # Calculate readability metrics
        sentence_metrics, sentence_issues = self._analyze_sentences(slides, all_text)
        issues.extend(sentence_issues)
        metadata['sentence_metrics'] = sentence_metrics
        
        # Check vocabulary complexity
        vocab_score, vocab_issues, vocab_metadata = self._analyze_vocabulary(
            all_text, presentation.academic_level or 'research'
        )
        issues.extend(vocab_issues)
        metadata['vocabulary'] = vocab_metadata
        
        # Check text clarity
        clarity_score, clarity_issues = self._check_text_clarity(slides)
        issues.extend(clarity_issues)
        
        # Check visual text elements
        visual_score, visual_issues = self._check_visual_text_elements(slides)
        issues.extend(visual_issues)
        
        # Check consistency
        consistency_score, consistency_issues = self._check_text_consistency(slides)
        issues.extend(consistency_issues)
        
        # Calculate overall readability score
        overall_score = (
            sentence_metrics['score'] * 0.3 +
            vocab_score * 0.25 +
            clarity_score * 0.2 +
            visual_score * 0.15 +
            consistency_score * 0.1
        )
        
        # Add metadata
        metadata.update({
            'sentence_score': sentence_metrics['score'],
            'vocabulary_score': vocab_score,
            'clarity_score': clarity_score,
            'visual_score': visual_score,
            'consistency_score': consistency_score,
            'academic_level': presentation.academic_level or 'research',
            'total_words': len(all_text.split())
        })
        
        # Identify strengths
        strengths = []
        if sentence_metrics['score'] >= 0.8:
            strengths.append("Appropriate sentence structure and length")
        if vocab_score >= 0.8:
            strengths.append("Good vocabulary for target audience")
        if clarity_score >= 0.8:
            strengths.append("Clear and concise writing")
        
        metadata['strengths'] = strengths
        
        return overall_score, issues, metadata
    
    def _extract_all_text(self, slides: List[SlideResponse]) -> str:
        """Extract all text content from slides."""
        text_parts = []
        
        for slide in slides:
            if slide.title:
                text_parts.append(slide.title)
            
            if slide.content:
                if 'subtitle' in slide.content:
                    text_parts.append(slide.content['subtitle'])
                
                if 'body' in slide.content:
                    for item in slide.content['body']:
                        if item.get('type') == 'text':
                            text_parts.append(item.get('content', ''))
                        elif item.get('type') == 'bullet_list':
                            text_parts.extend(item.get('items', []))
            
            if slide.speaker_notes:
                text_parts.append(slide.speaker_notes)
        
        return ' '.join(text_parts)
    
    def _analyze_sentences(
        self,
        slides: List[SlideResponse],
        all_text: str
    ) -> Tuple[Dict[str, Any], List[QualityIssue]]:
        """Analyze sentence structure and length."""
        issues = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', all_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return {'score': 0.5, 'avg_length': 0}, issues
        
        # Calculate sentence lengths
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        avg_length = statistics.mean(sentence_lengths)
        max_length = max(sentence_lengths) if sentence_lengths else 0
        
        # Check for overly long sentences
        long_sentences = [i for i, length in enumerate(sentence_lengths) if length > 35]
        
        # Find which slides have long sentences
        sentence_count = 0
        for i, slide in enumerate(slides):
            slide_text = self._extract_slide_text(slide)
            slide_sentences = re.split(r'[.!?]+', slide_text)
            slide_sentences = [s.strip() for s in slide_sentences if s.strip()]
            
            for j, sentence in enumerate(slide_sentences):
                if sentence_count in long_sentences:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description=f"Overly long sentence ({len(sentence.split())} words)",
                        suggestion="Break into shorter, clearer sentences"
                    ))
                sentence_count += 1
        
        # Check for very short sentences in content
        very_short = sum(1 for length in sentence_lengths if length < 5)
        if very_short > len(sentences) * 0.3:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Many very short sentences may sound choppy",
                suggestion="Combine related short sentences for better flow"
            ))
        
        # Calculate score based on appropriate sentence length
        ideal_range = (15, 25)  # Ideal sentence length range
        in_range = sum(1 for length in sentence_lengths 
                      if ideal_range[0] <= length <= ideal_range[1])
        score = in_range / len(sentence_lengths) if sentence_lengths else 0.5
        
        metrics = {
            'score': score,
            'avg_length': avg_length,
            'max_length': max_length,
            'total_sentences': len(sentences),
            'long_sentences': len(long_sentences)
        }
        
        return metrics, issues
    
    def _analyze_vocabulary(
        self,
        text: str,
        academic_level: str
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """Analyze vocabulary complexity and appropriateness."""
        issues = []
        metadata = {}
        
        # Get level requirements
        requirements = self.level_requirements.get(
            academic_level, 
            self.level_requirements['research']
        )
        
        # Tokenize words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        if not words:
            return 0.5, issues, metadata
        
        # Count complex words (>= 3 syllables, simplified by length)
        complex_words = [w for w in words if len(w) >= 8]
        complex_ratio = len(complex_words) / len(words)
        
        # Count technical/academic terms
        academic_terms = [w for w in words if w in self.academic_words]
        academic_ratio = len(academic_terms) / len(words)
        
        # Check vocabulary appropriateness
        if complex_ratio > requirements['complex_words_ratio'] * 1.5:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description=f"Vocabulary may be too complex for {academic_level} level",
                suggestion="Simplify complex terms or provide definitions"
            ))
        elif complex_ratio < requirements['complex_words_ratio'] * 0.5:
            if academic_level == 'research':
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description="Vocabulary may be too simple for research level",
                    suggestion="Use more precise academic terminology"
                ))
        
        # Check for jargon
        jargon_words = [w for w in words if w in self.readability_patterns['jargon_indicators']]
        if len(jargon_words) > len(words) * 0.05:  # More than 5% jargon
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Excessive use of jargon may reduce clarity",
                suggestion="Replace jargon with clearer alternatives"
            ))
        
        # Calculate vocabulary score
        complexity_score = 1.0 - abs(complex_ratio - requirements['complex_words_ratio']) * 2
        academic_score = min(1.0, academic_ratio / requirements['technical_terms_ratio'])
        jargon_penalty = len(jargon_words) / len(words) * 2
        
        vocab_score = max(0, (complexity_score + academic_score) / 2 - jargon_penalty)
        
        metadata = {
            'total_words': len(words),
            'unique_words': len(set(words)),
            'complex_words': len(complex_words),
            'complex_ratio': complex_ratio,
            'academic_terms': len(academic_terms),
            'academic_ratio': academic_ratio,
            'jargon_words': len(jargon_words)
        }
        
        return vocab_score, issues, metadata
    
    def _check_text_clarity(self, slides: List[SlideResponse]) -> Tuple[float, List[QualityIssue]]:
        """Check text clarity and directness."""
        issues = []
        clarity_scores = []
        
        for i, slide in enumerate(slides):
            slide_text = self._extract_slide_text(slide)
            if not slide_text.strip():
                continue
                
            slide_score = 1.0
            
            # Check for passive voice
            passive_count = len(re.findall(self.readability_patterns['passive_voice'], slide_text))
            sentences = len(re.split(r'[.!?]+', slide_text))
            if sentences > 0 and passive_count / sentences > 0.3:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description="Heavy use of passive voice",
                    suggestion="Use active voice for clearer communication"
                ))
                slide_score -= 0.2
            
            # Check for wordy phrases
            wordy_count = 0
            for phrase in self.readability_patterns['complex_phrases']:
                wordy_count += slide_text.lower().count(phrase)
            
            if wordy_count > 2:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description="Use of wordy phrases reduces clarity",
                    suggestion="Replace wordy phrases with concise alternatives"
                ))
                slide_score -= 0.1
            
            # Check for unclear pronouns
            unclear_pronouns = ['this', 'that', 'these', 'those', 'it']
            for pronoun in unclear_pronouns:
                # Simple check for pronoun at sentence start
                pattern = r'\.\s+' + pronoun.capitalize() + r'\s+'
                if re.search(pattern, slide_text):
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="suggestion",
                        slide_number=i + 1,
                        description=f"Unclear pronoun reference: '{pronoun}'",
                        suggestion="Be specific about what the pronoun refers to"
                    ))
                    slide_score -= 0.05
            
            clarity_scores.append(max(0, slide_score))
        
        # Calculate overall clarity score
        clarity_score = statistics.mean(clarity_scores) if clarity_scores else 0.5
        
        return clarity_score, issues
    
    def _check_visual_text_elements(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check visual aspects of text presentation."""
        issues = []
        visual_scores = []
        
        for i, slide in enumerate(slides):
            slide_score = 1.0
            
            # Check title length
            if slide.title and len(slide.title) > 80:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description="Title too long for easy reading",
                    suggestion="Shorten title to under 80 characters"
                ))
                slide_score -= 0.2
            
            # Check bullet point length
            if slide.content and 'body' in slide.content:
                for item in slide.content['body']:
                    if item.get('type') == 'bullet_list':
                        long_bullets = [
                            bullet for bullet in item.get('items', [])
                            if len(bullet) > 100
                        ]
                        if long_bullets:
                            issues.append(QualityIssue(
                                dimension=self.dimension,
                                severity="minor",
                                slide_number=i + 1,
                                description=f"{len(long_bullets)} bullet points are too long",
                                suggestion="Keep bullet points under 100 characters"
                            ))
                            slide_score -= 0.1
            
            # Check for text density
            text_content = self._extract_slide_text(slide)
            word_count = len(text_content.split())
            if word_count > 150:  # Too many words for a slide
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    slide_number=i + 1,
                    description=f"Too much text ({word_count} words) on single slide",
                    suggestion="Split content across multiple slides"
                ))
                slide_score -= 0.3
            
            visual_scores.append(max(0, slide_score))
        
        # Calculate visual score
        visual_score = statistics.mean(visual_scores) if visual_scores else 0.5
        
        return visual_score, issues
    
    def _check_text_consistency(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check consistency in text style and formatting."""
        issues = []
        
        # Check title case consistency
        title_cases = []
        for slide in slides:
            if slide.title:
                if slide.title.istitle():
                    title_cases.append('title')
                elif slide.title.isupper():
                    title_cases.append('upper')
                elif slide.title.islower():
                    title_cases.append('lower')
                else:
                    title_cases.append('mixed')
        
        if len(set(title_cases)) > 2:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Inconsistent title capitalization",
                suggestion="Use consistent capitalization style for all titles"
            ))
        
        # Check bullet point style consistency
        bullet_styles = []
        for slide in slides:
            if slide.content and 'body' in slide.content:
                for item in slide.content['body']:
                    if item.get('type') == 'bullet_list':
                        bullets = item.get('items', [])
                        for bullet in bullets:
                            if bullet.endswith('.'):
                                bullet_styles.append('period')
                            else:
                                bullet_styles.append('no_period')
        
        if len(set(bullet_styles)) > 1 and len(bullet_styles) > 3:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Inconsistent bullet point punctuation",
                suggestion="Use consistent punctuation for all bullet points"
            ))
        
        # Calculate consistency score
        title_consistency = 1.0 - (len(set(title_cases)) - 1) * 0.2 if title_cases else 1.0
        bullet_consistency = (
            1.0 - (len(set(bullet_styles)) - 1) * 0.1 
            if bullet_styles else 1.0
        )
        
        consistency_score = (title_consistency + bullet_consistency) / 2
        
        return max(0, consistency_score), issues
    
    def _extract_slide_text(self, slide: SlideResponse) -> str:
        """Extract all text from a single slide."""
        text_parts = []
        
        if slide.title:
            text_parts.append(slide.title)
        
        if slide.content:
            if 'subtitle' in slide.content:
                text_parts.append(slide.content['subtitle'])
            
            if 'body' in slide.content:
                for item in slide.content['body']:
                    if item.get('type') == 'text':
                        text_parts.append(item.get('content', ''))
                    elif item.get('type') == 'bullet_list':
                        text_parts.extend(item.get('items', []))
        
        return ' '.join(text_parts)