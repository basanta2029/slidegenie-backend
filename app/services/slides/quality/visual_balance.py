"""
Visual Balance Assessor for SlideGenie presentations.

This module assesses the visual balance of slides, ensuring proper
distribution of text, images, and whitespace.
"""
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation
from .base import QualityChecker, QualityDimension, QualityIssue


class VisualBalanceAssessor(QualityChecker):
    """
    Assesses visual balance and design consistency across slides.
    """
    
    def __init__(self):
        """Initialize visual balance assessor."""
        # Ideal content ratios
        self.ideal_ratios = {
            'text_to_visual': 0.6,  # 60% text, 40% visual
            'content_to_whitespace': 0.7,  # 70% content, 30% whitespace
            'title_to_body': 0.15  # 15% title, 85% body
        }
        
        # Maximum recommended elements per slide
        self.max_elements = {
            'bullet_points': 7,
            'text_blocks': 3,
            'images': 2,
            'equations': 2,
            'total_elements': 5
        }
        
        # Visual hierarchy guidelines
        self.hierarchy_rules = {
            'title_prominence': True,
            'consistent_alignment': True,
            'balanced_layout': True
        }
        
        # Layout patterns and their characteristics
        self.layout_patterns = {
            'single': {'max_elements': 3, 'ideal_text_ratio': 0.7},
            'two_column': {'max_elements': 6, 'ideal_text_ratio': 0.5},
            'image_left': {'max_elements': 4, 'ideal_text_ratio': 0.5},
            'image_right': {'max_elements': 4, 'ideal_text_ratio': 0.5},
            'comparison': {'max_elements': 8, 'ideal_text_ratio': 0.6},
            'grid': {'max_elements': 9, 'ideal_text_ratio': 0.3}
        }
    
    @property
    def dimension(self) -> QualityDimension:
        """Return the quality dimension."""
        return QualityDimension.VISUAL_BALANCE
    
    @property
    def weight(self) -> float:
        """Weight of visual balance in overall quality."""
        return 1.0
    
    def check(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """
        Check visual balance across slides.
        
        Returns:
            Tuple of (score, issues, metadata)
        """
        issues = []
        metadata = {}
        
        # Check element distribution
        distribution_score, distribution_issues, distribution_metadata = (
            self._check_element_distribution(slides)
        )
        issues.extend(distribution_issues)
        metadata['element_distribution'] = distribution_metadata
        
        # Check content density
        density_score, density_issues = self._check_content_density(slides)
        issues.extend(density_issues)
        
        # Check visual consistency
        consistency_score, consistency_issues = self._check_visual_consistency(slides)
        issues.extend(consistency_issues)
        
        # Check layout appropriateness
        layout_score, layout_issues = self._check_layout_appropriateness(slides)
        issues.extend(layout_issues)
        
        # Check text-visual balance
        balance_score, balance_issues, balance_metadata = self._check_text_visual_balance(slides)
        issues.extend(balance_issues)
        metadata['text_visual_balance'] = balance_metadata
        
        # Calculate overall score
        overall_score = (
            distribution_score * 0.25 +
            density_score * 0.25 +
            consistency_score * 0.2 +
            layout_score * 0.15 +
            balance_score * 0.15
        )
        
        # Add metadata
        metadata.update({
            'distribution_score': distribution_score,
            'density_score': density_score,
            'consistency_score': consistency_score,
            'layout_score': layout_score,
            'balance_score': balance_score,
            'total_slides': len(slides)
        })
        
        # Identify strengths
        strengths = []
        if distribution_score >= 0.8:
            strengths.append("Well-distributed visual elements")
        if density_score >= 0.8:
            strengths.append("Appropriate content density")
        if consistency_score >= 0.8:
            strengths.append("Consistent visual design")
        
        metadata['strengths'] = strengths
        
        return overall_score, issues, metadata
    
    def _check_element_distribution(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """Check distribution of visual elements across slides."""
        issues = []
        metadata = {
            'slides_with_visuals': 0,
            'slides_text_only': 0,
            'slides_overloaded': 0,
            'element_counts': []
        }
        
        element_counts = []
        
        for i, slide in enumerate(slides):
            # Count elements on slide
            element_count = self._count_slide_elements(slide)
            element_counts.append(element_count)
            metadata['element_counts'].append(element_count)
            
            # Check for text-only slides
            if element_count['visuals'] == 0 and i > 0 and i < len(slides) - 1:
                metadata['slides_text_only'] += 1
                if element_count['text'] > 3:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description="Text-heavy slide with no visual elements",
                        suggestion="Add diagram, chart, or image to break up text"
                    ))
            elif element_count['visuals'] > 0:
                metadata['slides_with_visuals'] += 1
            
            # Check for overloaded slides
            total_elements = sum(element_count.values())
            if total_elements > self.max_elements['total_elements']:
                metadata['slides_overloaded'] += 1
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    slide_number=i + 1,
                    description=f"Too many elements ({total_elements}) on single slide",
                    suggestion="Split content across multiple slides"
                ))
            
            # Check specific element limits
            if element_count['bullets'] > self.max_elements['bullet_points']:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description=f"Too many bullet points ({element_count['bullets']})",
                    suggestion=f"Limit to {self.max_elements['bullet_points']} bullet points"
                ))
        
        # Check overall distribution
        visual_ratio = metadata['slides_with_visuals'] / len(slides) if slides else 0
        if visual_ratio < 0.3:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="major",
                description="Too few slides with visual elements",
                suggestion="Add more diagrams, charts, or images throughout"
            ))
        
        # Calculate score
        score = 0.5  # Base score
        if visual_ratio >= 0.4:
            score += 0.2
        if metadata['slides_overloaded'] < len(slides) * 0.1:
            score += 0.2
        if metadata['slides_text_only'] < len(slides) * 0.3:
            score += 0.1
        
        return score, issues, metadata
    
    def _check_content_density(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check content density on slides."""
        issues = []
        density_scores = []
        
        for i, slide in enumerate(slides):
            # Calculate content density
            density = self._calculate_content_density(slide)
            density_scores.append(density)
            
            # Check for overcrowded slides
            if density > 0.85:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    slide_number=i + 1,
                    description="Slide appears overcrowded",
                    suggestion="Reduce content or use larger font sizes"
                ))
            elif density < 0.3 and slide.layout_type == 'content':
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description="Slide appears too sparse",
                    suggestion="Add more content or combine with adjacent slide"
                ))
        
        # Check density variation
        if len(density_scores) > 3:
            max_density = max(density_scores)
            min_density = min(density_scores)
            if max_density - min_density > 0.6:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description="High variation in slide density",
                    suggestion="Balance content distribution across slides"
                ))
        
        # Calculate score
        avg_density = sum(density_scores) / len(density_scores) if density_scores else 0.5
        optimal_density = 0.65
        deviation = abs(avg_density - optimal_density)
        score = max(0, 1 - deviation * 2)
        
        return score, issues
    
    def _check_visual_consistency(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check visual design consistency."""
        issues = []
        
        # Track layout usage
        layout_counter = Counter()
        for slide in slides:
            layout = slide.content.get('layout', 'single') if slide.content else 'single'
            layout_counter[layout] += 1
        
        # Check for too many different layouts
        if len(layout_counter) > 4:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Too many different layout types used",
                suggestion="Limit to 3-4 layout types for consistency"
            ))
        
        # Check for consistent element positioning
        title_positions = []
        for slide in slides:
            if slide.title and slide.content:
                # Simple check - in real implementation would analyze actual positions
                title_positions.append('top')  # Placeholder
        
        # Check for orphaned layout types
        for layout, count in layout_counter.items():
            if count == 1 and len(slides) > 5:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description=f"Layout '{layout}' used only once",
                    suggestion="Use consistent layouts or remove one-off designs"
                ))
        
        # Calculate consistency score
        most_common_count = layout_counter.most_common(1)[0][1] if layout_counter else 0
        consistency_ratio = most_common_count / len(slides) if slides else 0
        score = min(1.0, consistency_ratio * 1.5)  # Boost score for consistency
        
        return score, issues
    
    def _check_layout_appropriateness(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check if layouts are appropriate for content."""
        issues = []
        appropriate_count = 0
        
        for i, slide in enumerate(slides):
            layout = slide.content.get('layout', 'single') if slide.content else 'single'
            elements = self._count_slide_elements(slide)
            
            # Check layout-content match
            if layout in self.layout_patterns:
                pattern = self.layout_patterns[layout]
                
                # Check element count
                total_elements = sum(elements.values())
                if total_elements > pattern['max_elements']:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description=f"Too many elements for {layout} layout",
                        suggestion="Use different layout or reduce content"
                    ))
                else:
                    appropriate_count += 1
                
                # Check specific layout requirements
                if layout == 'two_column' and elements['text'] < 2:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description="Two-column layout with insufficient content",
                        suggestion="Use single column layout instead"
                    ))
                elif layout in ['image_left', 'image_right'] and elements['visuals'] == 0:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="major",
                        slide_number=i + 1,
                        description=f"{layout} layout without image",
                        suggestion="Add image or change layout type"
                    ))
            else:
                appropriate_count += 1
        
        # Calculate score
        score = appropriate_count / len(slides) if slides else 0.5
        
        return score, issues
    
    def _check_text_visual_balance(
        self,
        slides: List[SlideResponse]
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """Check balance between text and visual content."""
        issues = []
        metadata = {
            'avg_text_ratio': 0,
            'slides_text_heavy': 0,
            'slides_visual_heavy': 0
        }
        
        text_ratios = []
        
        for i, slide in enumerate(slides):
            # Calculate text-to-visual ratio
            elements = self._count_slide_elements(slide)
            total_content = elements['text'] + elements['bullets'] + elements['visuals']
            
            if total_content > 0:
                text_ratio = (elements['text'] + elements['bullets']) / total_content
                text_ratios.append(text_ratio)
                
                # Check for imbalance
                if text_ratio > 0.85:
                    metadata['slides_text_heavy'] += 1
                    if slide.layout_type != 'title':
                        issues.append(QualityIssue(
                            dimension=self.dimension,
                            severity="minor",
                            slide_number=i + 1,
                            description="Slide is text-heavy",
                            suggestion="Add visual element or diagram"
                        ))
                elif text_ratio < 0.15 and elements['visuals'] > 0:
                    metadata['slides_visual_heavy'] += 1
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="minor",
                        slide_number=i + 1,
                        description="Slide lacks explanatory text",
                        suggestion="Add captions or explanatory text for visuals"
                    ))
        
        # Calculate average ratio
        metadata['avg_text_ratio'] = (
            sum(text_ratios) / len(text_ratios) if text_ratios else 0.5
        )
        
        # Calculate score based on deviation from ideal
        ideal_ratio = self.ideal_ratios['text_to_visual']
        deviation = abs(metadata['avg_text_ratio'] - ideal_ratio)
        score = max(0, 1 - deviation * 2)
        
        return score, issues, metadata
    
    def _count_slide_elements(self, slide: SlideResponse) -> Dict[str, int]:
        """Count different types of elements on a slide."""
        counts = {
            'text': 0,
            'bullets': 0,
            'visuals': 0,
            'equations': 0,
            'code': 0,
            'tables': 0
        }
        
        # Count from content structure
        if slide.content and 'body' in slide.content:
            for item in slide.content['body']:
                item_type = item.get('type', '')
                if item_type == 'text':
                    counts['text'] += 1
                elif item_type == 'bullet_list':
                    counts['bullets'] += len(item.get('items', []))
                elif item_type in ['image', 'chart', 'diagram']:
                    counts['visuals'] += 1
                elif item_type == 'equation':
                    counts['equations'] += 1
                elif item_type == 'code':
                    counts['code'] += 1
                elif item_type == 'table':
                    counts['tables'] += 1
        
        # Use slide metadata
        if slide.figure_count > 0:
            counts['visuals'] = max(counts['visuals'], slide.figure_count)
        if slide.contains_equations:
            counts['equations'] = max(counts['equations'], 1)
        if slide.contains_code:
            counts['code'] = max(counts['code'], 1)
        
        return counts
    
    def _calculate_content_density(self, slide: SlideResponse) -> float:
        """Calculate content density (0-1) for a slide."""
        density = 0.0
        
        # Count all elements
        elements = self._count_slide_elements(slide)
        total_elements = sum(elements.values())
        
        # Base density on element count
        density += min(total_elements / 8, 1.0) * 0.4
        
        # Factor in text length
        if slide.content:
            text_length = 0
            if 'body' in slide.content:
                for item in slide.content['body']:
                    if item.get('type') == 'text':
                        text_length += len(item.get('content', ''))
            
            # Assume ~150 chars per "unit" of space
            density += min(text_length / 600, 1.0) * 0.3
        
        # Factor in special content
        if elements['equations'] > 0:
            density += 0.1
        if elements['code'] > 0:
            density += 0.15
        if elements['tables'] > 0:
            density += 0.05
        
        return min(density, 1.0)