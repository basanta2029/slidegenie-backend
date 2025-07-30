"""
Slide Transition Validator for SlideGenie presentations.

This module validates the quality and appropriateness of transitions
between slides, ensuring smooth flow and logical progression.
"""
from typing import Any, Dict, List, Optional, Tuple

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation
from .base import QualityChecker, QualityDimension, QualityIssue


class TransitionValidator(QualityChecker):
    """
    Validates slide transitions for smooth flow and logical progression.
    """
    
    def __init__(self):
        """Initialize transition validator."""
        # Define transition patterns for different slide types
        self.transition_patterns = {
            'title_to_overview': {
                'expected': ['overview', 'outline', 'agenda', 'introduction'],
                'severity': 'major'
            },
            'overview_to_content': {
                'expected': ['first', 'begin', 'start', 'let us'],
                'severity': 'minor'
            },
            'content_to_content': {
                'expected': ['next', 'furthermore', 'additionally', 'moreover'],
                'severity': 'minor'
            },
            'section_to_content': {
                'expected': ['in this section', 'we will discuss', 'focus on'],
                'severity': 'minor'
            },
            'content_to_conclusion': {
                'expected': ['in conclusion', 'to summarize', 'finally'],
                'severity': 'major'
            },
            'conclusion_to_references': {
                'expected': ['references', 'bibliography', 'sources'],
                'severity': 'minor'
            }
        }
        
        # Define slide type indicators
        self.slide_type_indicators = {
            'title': ['title slide', 'presentation title'],
            'overview': ['overview', 'outline', 'agenda', 'contents', 'roadmap'],
            'section': ['section', 'part', 'chapter'],
            'content': [],  # Default type
            'conclusion': ['conclusion', 'summary', 'concluding', 'final thoughts'],
            'references': ['references', 'bibliography', 'sources', 'citations'],
            'questions': ['questions', 'q&a', 'thank you', 'discussion']
        }
        
        # Animation and transition effect appropriateness
        self.appropriate_effects = {
            'title': ['fade', 'zoom', 'appear'],
            'overview': ['fade', 'push', 'wipe'],
            'section': ['cube', 'flip', 'fade'],
            'content': ['fade', 'push', 'slide'],
            'conclusion': ['fade', 'zoom'],
            'references': ['fade', 'appear']
        }
    
    @property
    def dimension(self) -> QualityDimension:
        """Return the quality dimension."""
        return QualityDimension.TRANSITIONS
    
    @property
    def weight(self) -> float:
        """Weight of transitions in overall quality."""
        return 1.0
    
    def check(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """
        Check transition quality between slides.
        
        Returns:
            Tuple of (score, issues, metadata)
        """
        issues = []
        metadata = {}
        
        # Identify slide types
        slide_types = self._identify_slide_types(slides)
        metadata['slide_types'] = slide_types
        
        # Check transition flow
        flow_score, flow_issues = self._check_transition_flow(slides, slide_types)
        issues.extend(flow_issues)
        
        # Check transition effects
        effects_score, effects_issues = self._check_transition_effects(slides, slide_types)
        issues.extend(effects_issues)
        
        # Check pacing
        pacing_score, pacing_issues = self._check_transition_pacing(slides)
        issues.extend(pacing_issues)
        
        # Check section transitions
        section_score, section_issues = self._check_section_transitions(slides, slide_types)
        issues.extend(section_issues)
        
        # Calculate overall score
        overall_score = (
            flow_score * 0.4 +
            effects_score * 0.2 +
            pacing_score * 0.2 +
            section_score * 0.2
        )
        
        # Add metadata
        metadata.update({
            'flow_score': flow_score,
            'effects_score': effects_score,
            'pacing_score': pacing_score,
            'section_score': section_score,
            'total_transitions': len(slides) - 1 if slides else 0,
            'smooth_transitions': sum(1 for i in issues if i.severity != 'critical')
        })
        
        # Identify strengths
        strengths = []
        if flow_score >= 0.8:
            strengths.append("Smooth logical flow between slides")
        if effects_score >= 0.8:
            strengths.append("Appropriate transition effects")
        if pacing_score >= 0.8:
            strengths.append("Well-paced transitions")
        
        metadata['strengths'] = strengths
        
        return overall_score, issues, metadata
    
    def _identify_slide_types(self, slides: List[SlideResponse]) -> List[str]:
        """Identify the type of each slide."""
        slide_types = []
        
        for i, slide in enumerate(slides):
            slide_type = 'content'  # Default
            
            # Check title and content for type indicators
            title_lower = slide.title.lower() if slide.title else ''
            
            # Special handling for first and last slides
            if i == 0:
                slide_type = 'title'
            elif i == len(slides) - 1 and 'reference' in title_lower:
                slide_type = 'references'
            else:
                # Check against indicators
                for type_name, indicators in self.slide_type_indicators.items():
                    if any(indicator in title_lower for indicator in indicators):
                        slide_type = type_name
                        break
                
                # Check layout type
                if slide.layout_type in ['section', 'title']:
                    slide_type = slide.layout_type
            
            slide_types.append(slide_type)
        
        return slide_types
    
    def _check_transition_flow(
        self,
        slides: List[SlideResponse],
        slide_types: List[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check logical flow of transitions."""
        issues = []
        good_transitions = 0
        total_transitions = len(slides) - 1
        
        for i in range(total_transitions):
            current_type = slide_types[i]
            next_type = slide_types[i + 1]
            
            # Check specific transition patterns
            if current_type == 'title' and next_type not in ['overview', 'introduction', 'content']:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    slide_number=i + 2,
                    description="Title slide should transition to overview or introduction",
                    suggestion="Add an overview or introduction slide after the title"
                ))
            elif current_type == 'overview' and next_type == 'conclusion':
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="critical",
                    slide_number=i + 2,
                    description="Missing main content between overview and conclusion",
                    suggestion="Add content slides to present your main points"
                ))
            elif current_type == 'conclusion' and next_type not in ['references', 'questions']:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    slide_number=i + 2,
                    description="Content after conclusion disrupts flow",
                    suggestion="Move content before conclusion or into appendix"
                ))
            else:
                good_transitions += 1
            
            # Check for abrupt section changes
            if current_type == 'content' and next_type == 'section':
                # Check if previous content is properly concluded
                current_content = self._extract_slide_text(slides[i])
                if not self._has_concluding_phrase(current_content):
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description="Abrupt transition to new section",
                        suggestion="Add concluding remarks before transitioning to new section"
                    ))
        
        # Calculate flow score
        flow_score = good_transitions / total_transitions if total_transitions > 0 else 1.0
        
        return flow_score, issues
    
    def _check_transition_effects(
        self,
        slides: List[SlideResponse],
        slide_types: List[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check appropriateness of transition effects."""
        issues = []
        appropriate_count = 0
        effects_count = 0
        
        for i, slide in enumerate(slides):
            if slide.transitions:
                effects_count += 1
                slide_type = slide_types[i]
                
                # Check if transition effect is appropriate
                transition_type = slide.transitions.get('type', 'fade')
                appropriate_effects = self.appropriate_effects.get(slide_type, ['fade'])
                
                if transition_type not in appropriate_effects:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description=f"Transition effect '{transition_type}' may be distracting for {slide_type} slide",
                        suggestion=f"Consider using {', '.join(appropriate_effects)} for {slide_type} slides"
                    ))
                else:
                    appropriate_count += 1
                
                # Check transition duration
                duration = slide.transitions.get('duration', 1.0)
                if duration > 2.0:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description="Transition duration too long",
                        suggestion="Keep transition duration under 2 seconds"
                    ))
        
        # Check for consistency
        if effects_count > 0:
            all_effects = [s.transitions.get('type', 'fade') for s in slides if s.transitions]
            unique_effects = set(all_effects)
            if len(unique_effects) > 3:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description="Too many different transition effects",
                    suggestion="Limit to 2-3 transition effects for consistency"
                ))
        
        # Calculate effects score
        effects_score = appropriate_count / effects_count if effects_count > 0 else 0.8
        
        return effects_score, issues
    
    def _check_transition_pacing(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check pacing of transitions based on content density."""
        issues = []
        pacing_scores = []
        
        for i in range(len(slides) - 1):
            current_slide = slides[i]
            next_slide = slides[i + 1]
            
            # Estimate content density
            current_density = self._estimate_content_density(current_slide)
            next_density = self._estimate_content_density(next_slide)
            
            # Check for dramatic density changes
            density_change = abs(next_density - current_density)
            if density_change > 0.7:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 2,
                    description="Large change in content density between slides",
                    suggestion="Consider adding intermediate slide or redistributing content"
                ))
                pacing_scores.append(0.3)
            elif density_change > 0.5:
                pacing_scores.append(0.7)
            else:
                pacing_scores.append(1.0)
        
        # Calculate pacing score
        pacing_score = sum(pacing_scores) / len(pacing_scores) if pacing_scores else 0.8
        
        return pacing_score, issues
    
    def _check_section_transitions(
        self,
        slides: List[SlideResponse],
        slide_types: List[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check transitions at section boundaries."""
        issues = []
        section_transitions = []
        
        for i in range(len(slides) - 1):
            if slide_types[i] == 'section' or slide_types[i + 1] == 'section':
                # This is a section boundary
                transition_quality = self._evaluate_section_transition(
                    slides[i], slides[i + 1], slide_types[i], slide_types[i + 1]
                )
                section_transitions.append(transition_quality)
                
                if transition_quality < 0.5:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="major",
                        slide_number=i + 1,
                        description="Weak section transition",
                        suggestion="Add clear transition text or summary before new section"
                    ))
        
        # Calculate section score
        section_score = (
            sum(section_transitions) / len(section_transitions)
            if section_transitions else 0.8
        )
        
        return section_score, issues
    
    def _extract_slide_text(self, slide: SlideResponse) -> str:
        """Extract all text from a slide."""
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
        
        if slide.speaker_notes:
            text_parts.append(slide.speaker_notes)
        
        return ' '.join(text_parts)
    
    def _has_concluding_phrase(self, text: str) -> bool:
        """Check if text contains concluding phrases."""
        concluding_phrases = [
            'in summary', 'to conclude', 'therefore', 'thus',
            'this shows', 'we have seen', 'as shown'
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in concluding_phrases)
    
    def _estimate_content_density(self, slide: SlideResponse) -> float:
        """Estimate content density of a slide (0-1)."""
        density_factors = 0.0
        
        # Word count factor
        text = self._extract_slide_text(slide)
        word_count = len(text.split())
        density_factors += min(word_count / 100, 1.0) * 0.3
        
        # Visual elements factor
        if slide.figure_count > 0:
            density_factors += min(slide.figure_count / 3, 1.0) * 0.2
        
        # Code/equation factor
        if slide.contains_code:
            density_factors += 0.2
        if slide.contains_equations:
            density_factors += 0.15
        
        # Bullet points factor
        if slide.content and 'body' in slide.content:
            bullet_count = sum(
                1 for item in slide.content['body']
                if item.get('type') == 'bullet_list'
            )
            density_factors += min(bullet_count / 5, 1.0) * 0.15
        
        return min(density_factors, 1.0)
    
    def _evaluate_section_transition(
        self,
        slide1: SlideResponse,
        slide2: SlideResponse,
        type1: str,
        type2: str
    ) -> float:
        """Evaluate quality of section transition."""
        score = 0.5  # Base score
        
        # Check if section slide has clear title
        if type2 == 'section' and slide2.title:
            score += 0.2
        
        # Check if previous slide has concluding remarks
        if type1 != 'section':
            text1 = self._extract_slide_text(slide1)
            if self._has_concluding_phrase(text1):
                score += 0.2
        
        # Check if new section has introduction
        if type2 != 'section':
            text2 = self._extract_slide_text(slide2)
            intro_phrases = ['in this section', 'we will', 'let us', 'now we']
            if any(phrase in text2.lower() for phrase in intro_phrases):
                score += 0.1
        
        return min(score, 1.0)