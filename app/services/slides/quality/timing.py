"""
Timing Estimation Validator for SlideGenie presentations.

This module validates that estimated slide timings are appropriate
for the content density and presentation duration.
"""
import statistics
from typing import Any, Dict, List, Optional, Tuple

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation
from .base import QualityChecker, QualityDimension, QualityIssue


class TimingValidator(QualityChecker):
    """
    Validates timing estimates for presentation slides.
    """
    
    def __init__(self):
        """Initialize timing validator."""
        # Average reading speeds (words per minute)
        self.reading_speeds = {
            'fast': 180,
            'normal': 150,
            'slow': 120,
            'academic': 130  # Slower for technical content
        }
        
        # Time factors for different content types (seconds)
        self.content_time_factors = {
            'title_slide': 10,
            'section_slide': 15,
            'text_paragraph': 30,  # Per paragraph
            'bullet_point': 10,    # Per bullet
            'equation': 20,        # Per equation
            'code_snippet': 45,    # Per code block
            'figure': 30,          # Per figure/chart
            'table': 40,           # Per table
            'citation': 5,         # Per citation
            'transition': 3        # Between slides
        }
        
        # Recommended time ranges by slide type
        self.recommended_times = {
            'title': (10, 20),
            'overview': (30, 60),
            'content': (45, 120),
            'section': (15, 30),
            'conclusion': (60, 120),
            'references': (10, 30),
            'questions': (10, 20)
        }
    
    @property
    def dimension(self) -> QualityDimension:
        """Return the quality dimension."""
        return QualityDimension.TIMING
    
    @property
    def weight(self) -> float:
        """Weight of timing in overall quality."""
        return 0.8
    
    def check(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """
        Check timing estimates for slides.
        
        Returns:
            Tuple of (score, issues, metadata)
        """
        issues = []
        metadata = {}
        
        # Calculate timing estimates
        timing_data = self._calculate_slide_timings(slides)
        metadata['timing_breakdown'] = timing_data
        
        # Check individual slide timings
        individual_score, individual_issues = self._check_individual_timings(
            slides, timing_data
        )
        issues.extend(individual_issues)
        
        # Check total presentation timing
        total_score, total_issues, total_metadata = self._check_total_timing(
            presentation, timing_data
        )
        issues.extend(total_issues)
        metadata.update(total_metadata)
        
        # Check timing distribution
        distribution_score, distribution_issues = self._check_timing_distribution(
            timing_data
        )
        issues.extend(distribution_issues)
        
        # Check pacing consistency
        pacing_score, pacing_issues = self._check_pacing_consistency(
            slides, timing_data
        )
        issues.extend(pacing_issues)
        
        # Calculate overall score
        overall_score = (
            individual_score * 0.3 +
            total_score * 0.3 +
            distribution_score * 0.2 +
            pacing_score * 0.2
        )
        
        # Add metadata
        metadata.update({
            'individual_score': individual_score,
            'total_score': total_score,
            'distribution_score': distribution_score,
            'pacing_score': pacing_score,
            'avg_slide_time': statistics.mean(timing_data['estimated_times']),
            'total_estimated_time': sum(timing_data['estimated_times'])
        })
        
        # Identify strengths
        strengths = []
        if individual_score >= 0.8:
            strengths.append("Appropriate timing for individual slides")
        if total_score >= 0.8:
            strengths.append("Total timing matches presentation duration")
        if pacing_score >= 0.8:
            strengths.append("Consistent pacing throughout presentation")
        
        metadata['strengths'] = strengths
        
        return overall_score, issues, metadata
    
    def _calculate_slide_timings(self, slides: List[SlideResponse]) -> Dict[str, Any]:
        """Calculate estimated timing for each slide."""
        estimated_times = []
        slide_types = []
        content_densities = []
        
        for slide in slides:
            # Determine slide type
            slide_type = self._determine_slide_type(slide)
            slide_types.append(slide_type)
            
            # Calculate base time
            if slide.duration_seconds:
                # Use provided duration
                estimated_time = slide.duration_seconds
            else:
                # Estimate based on content
                estimated_time = self._estimate_slide_time(slide, slide_type)
            
            estimated_times.append(estimated_time)
            
            # Calculate content density
            density = self._calculate_content_density(slide)
            content_densities.append(density)
        
        return {
            'estimated_times': estimated_times,
            'slide_types': slide_types,
            'content_densities': content_densities
        }
    
    def _determine_slide_type(self, slide: SlideResponse) -> str:
        """Determine the type of slide."""
        if slide.layout_type:
            return slide.layout_type
        
        # Infer from title
        if slide.title:
            title_lower = slide.title.lower()
            if any(word in title_lower for word in ['overview', 'outline', 'agenda']):
                return 'overview'
            elif any(word in title_lower for word in ['conclusion', 'summary']):
                return 'conclusion'
            elif any(word in title_lower for word in ['reference', 'bibliography']):
                return 'references'
            elif slide.section:
                return 'section'
        
        return 'content'
    
    def _estimate_slide_time(self, slide: SlideResponse, slide_type: str) -> int:
        """Estimate time needed for a slide in seconds."""
        base_time = 0
        
        # Add base time for slide type
        if slide_type == 'title':
            base_time += self.content_time_factors['title_slide']
        elif slide_type == 'section':
            base_time += self.content_time_factors['section_slide']
        else:
            base_time += 20  # Base time for content slides
        
        # Add time for text content
        if slide.content:
            # Count words for reading time
            text_content = self._extract_all_text(slide)
            word_count = len(text_content.split())
            reading_time = (word_count / self.reading_speeds['academic']) * 60
            base_time += reading_time
            
            # Add time for special content
            if 'body' in slide.content:
                for item in slide.content['body']:
                    item_type = item.get('type', '')
                    if item_type == 'bullet_list':
                        bullet_count = len(item.get('items', []))
                        base_time += bullet_count * self.content_time_factors['bullet_point']
                    elif item_type == 'equation':
                        base_time += self.content_time_factors['equation']
                    elif item_type == 'code':
                        base_time += self.content_time_factors['code_snippet']
                    elif item_type in ['image', 'chart', 'diagram']:
                        base_time += self.content_time_factors['figure']
                    elif item_type == 'table':
                        base_time += self.content_time_factors['table']
        
        # Add time for figures
        if slide.figure_count > 0:
            base_time += slide.figure_count * self.content_time_factors['figure']
        
        # Add transition time
        base_time += self.content_time_factors['transition']
        
        return int(base_time)
    
    def _extract_all_text(self, slide: SlideResponse) -> str:
        """Extract all text from slide."""
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
                        # Don't include bullets in word count, handled separately
                        pass
        
        return ' '.join(text_parts)
    
    def _calculate_content_density(self, slide: SlideResponse) -> float:
        """Calculate content density score (0-1)."""
        density_score = 0.0
        
        # Word count factor
        text = self._extract_all_text(slide)
        word_count = len(text.split())
        density_score += min(word_count / 150, 1.0) * 0.3
        
        # Visual elements factor
        if slide.figure_count > 0:
            density_score += min(slide.figure_count / 3, 1.0) * 0.2
        
        # Special content factor
        if slide.contains_equations:
            density_score += 0.15
        if slide.contains_code:
            density_score += 0.2
        if slide.contains_citations:
            density_score += 0.1
        
        # Bullet points factor
        if slide.content and 'body' in slide.content:
            bullet_count = sum(
                len(item.get('items', []))
                for item in slide.content['body']
                if item.get('type') == 'bullet_list'
            )
            density_score += min(bullet_count / 7, 1.0) * 0.15
        
        return min(density_score, 1.0)
    
    def _check_individual_timings(
        self,
        slides: List[SlideResponse],
        timing_data: Dict[str, Any]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check if individual slide timings are appropriate."""
        issues = []
        appropriate_count = 0
        
        for i, (slide, estimated_time, slide_type, density) in enumerate(zip(
            slides,
            timing_data['estimated_times'],
            timing_data['slide_types'],
            timing_data['content_densities']
        )):
            # Get recommended range
            min_time, max_time = self.recommended_times.get(
                slide_type, (30, 120)
            )
            
            # Adjust for content density
            if density > 0.7:
                max_time *= 1.3
            elif density < 0.3:
                min_time *= 0.7
            
            # Check if timing is appropriate
            if estimated_time < min_time:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description=f"Slide may be too rushed ({estimated_time}s estimated)",
                    suggestion=f"Consider allowing {min_time}-{max_time}s for this content"
                ))
            elif estimated_time > max_time:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    slide_number=i + 1,
                    description=f"Slide too dense ({estimated_time}s estimated)",
                    suggestion="Split content across multiple slides or reduce detail"
                ))
            else:
                appropriate_count += 1
        
        # Calculate score
        score = appropriate_count / len(slides) if slides else 0.5
        
        return score, issues
    
    def _check_total_timing(
        self,
        presentation: PresentationResponse,
        timing_data: Dict[str, Any]
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """Check if total timing matches presentation duration."""
        issues = []
        metadata = {}
        
        total_estimated = sum(timing_data['estimated_times']) / 60  # Convert to minutes
        target_duration = presentation.duration_minutes or 15  # Default 15 minutes
        
        metadata['total_estimated_minutes'] = total_estimated
        metadata['target_minutes'] = target_duration
        
        # Calculate deviation
        deviation = abs(total_estimated - target_duration) / target_duration
        
        if deviation > 0.2:  # More than 20% off
            if total_estimated > target_duration:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="critical",
                    description=f"Presentation too long: {total_estimated:.1f} min vs {target_duration} min target",
                    suggestion="Reduce content or increase presentation duration"
                ))
            else:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    description=f"Presentation too short: {total_estimated:.1f} min vs {target_duration} min target",
                    suggestion="Add more content or reduce presentation duration"
                ))
        elif deviation > 0.1:  # 10-20% off
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description=f"Slight timing mismatch: {total_estimated:.1f} min vs {target_duration} min",
                suggestion="Fine-tune content for better timing match"
            ))
        
        # Calculate score based on deviation
        score = max(0, 1 - deviation)
        
        return score, issues, metadata
    
    def _check_timing_distribution(
        self,
        timing_data: Dict[str, Any]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check if timing is well-distributed across slides."""
        issues = []
        times = timing_data['estimated_times']
        
        if len(times) < 3:
            return 1.0, issues
        
        # Calculate statistics
        mean_time = statistics.mean(times)
        stdev_time = statistics.stdev(times)
        cv = stdev_time / mean_time if mean_time > 0 else 0
        
        # Check for high variation
        if cv > 0.5:  # Coefficient of variation > 50%
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="High variation in slide timings",
                suggestion="Balance content distribution for more consistent pacing"
            ))
        
        # Check for outliers
        for i, time in enumerate(times):
            if time > mean_time + 2 * stdev_time:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description="Slide timing significantly above average",
                    suggestion="Consider splitting this slide"
                ))
            elif time < mean_time - 2 * stdev_time and time < 20:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description="Slide may be too brief",
                    suggestion="Add more detail or combine with adjacent slide"
                ))
        
        # Calculate score
        score = max(0, 1 - cv)  # Lower CV is better
        
        return score, issues
    
    def _check_pacing_consistency(
        self,
        slides: List[SlideResponse],
        timing_data: Dict[str, Any]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check for consistent pacing throughout presentation."""
        issues = []
        times = timing_data['estimated_times']
        densities = timing_data['content_densities']
        
        # Group slides into thirds
        third_size = len(slides) // 3
        if third_size < 2:
            return 0.8, issues
        
        first_third = times[:third_size]
        middle_third = times[third_size:2*third_size]
        last_third = times[2*third_size:]
        
        # Calculate average pace for each third
        avg_first = statistics.mean(first_third) if first_third else 0
        avg_middle = statistics.mean(middle_third) if middle_third else 0
        avg_last = statistics.mean(last_third) if last_third else 0
        
        # Check for pacing issues
        if avg_first > avg_middle * 1.5:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Slow start - first third has longer slide times",
                suggestion="Consider condensing introductory content"
            ))
        
        if avg_last < avg_middle * 0.5:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Rushed ending - last third has very short slide times",
                suggestion="Allow more time for conclusion and discussion"
            ))
        
        # Check for sudden pace changes
        for i in range(1, len(times)):
            if times[i] > times[i-1] * 2 and times[i] > 60:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    slide_number=i + 1,
                    description="Sudden increase in slide duration",
                    suggestion="Smooth out pacing by redistributing content"
                ))
        
        # Calculate pacing score
        pace_variance = statistics.variance([avg_first, avg_middle, avg_last])
        normalized_variance = pace_variance / (statistics.mean([avg_first, avg_middle, avg_last]) ** 2)
        score = max(0, 1 - normalized_variance)
        
        return score, issues