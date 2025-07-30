"""
Presentation timing and pacing rules.
"""
from typing import Any, Dict, List

from app.services.slides.rules.base import (
    Rule,
    RuleCategory,
    RuleContext,
    RuleSeverity,
    RuleViolation,
    get_rule_engine
)


class SlideCountRule(Rule):
    """Ensures appropriate number of slides for presentation duration."""
    
    def __init__(self, seconds_per_slide: int = 60):
        super().__init__(
            rule_id="timing.slide_count",
            name="Slide Count for Duration",
            description="Ensures appropriate number of slides for presentation time",
            category=RuleCategory.TIMING,
            severity=RuleSeverity.WARNING,
            config={"seconds_per_slide": seconds_per_slide}
        )
        self.seconds_per_slide = seconds_per_slide
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        # This rule works at presentation level
        if isinstance(content, dict) and "slides" in content:
            slide_count = len(content.get("slides", []))
            duration_minutes = context.duration_minutes
            
            # Calculate recommended slide count
            recommended_min = int((duration_minutes * 60) / (self.seconds_per_slide * 1.2))  # 20% buffer
            recommended_max = int((duration_minutes * 60) / (self.seconds_per_slide * 0.8))  # 20% buffer
            
            if slide_count < recommended_min:
                violations.append(self.create_violation(
                    message=f"Too few slides ({slide_count}) for {duration_minutes} minute presentation",
                    suggestion=f"Consider adding {recommended_min - slide_count} more slides",
                    context={
                        "current_slides": slide_count,
                        "recommended_range": f"{recommended_min}-{recommended_max}",
                        "duration_minutes": duration_minutes
                    }
                ))
            elif slide_count > recommended_max:
                violations.append(self.create_violation(
                    message=f"Too many slides ({slide_count}) for {duration_minutes} minute presentation",
                    suggestion=f"Consider reducing by {slide_count - recommended_max} slides or increasing pace",
                    context={
                        "current_slides": slide_count,
                        "recommended_range": f"{recommended_min}-{recommended_max}",
                        "duration_minutes": duration_minutes
                    }
                ))
        
        return violations


class SlideTimingEstimateRule(Rule):
    """Estimates time needed for each slide based on content."""
    
    def __init__(self):
        super().__init__(
            rule_id="timing.slide_estimate",
            name="Slide Timing Estimate",
            description="Estimates speaking time for slide content",
            category=RuleCategory.TIMING,
            severity=RuleSeverity.INFO
        )
        
        # Speaking rates (words per minute)
        self.speaking_rates = {
            "slow": 110,      # Deliberate, technical content
            "normal": 130,    # Average presentation pace
            "fast": 150       # Quick overview pace
        }
        
        # Time additions for various elements (seconds)
        self.element_times = {
            "image": 5,
            "chart": 10,
            "table": 15,
            "equation": 10,
            "code": 20,
            "diagram": 10,
            "video": 30  # Placeholder, actual time from metadata
        }
    
    def _count_words(self, content: Dict[str, Any]) -> int:
        """Count speakable words in slide content."""
        word_count = 0
        
        # Title and subtitle (usually spoken)
        word_count += len(content.get("title", "").split())
        word_count += len(content.get("subtitle", "").split())
        
        # Body elements
        for element in content.get("body", []):
            if element.get("type") == "text":
                word_count += len(element.get("content", "").split())
            elif element.get("type") == "bullet_list":
                for item in element.get("items", []):
                    word_count += len(item.get("text", "").split())
            elif element.get("type") in ["table", "chart", "image"]:
                # Add caption words
                caption = element.get("caption", "")
                word_count += len(caption.split())
        
        return word_count
    
    def _calculate_slide_time(self, slide: Dict[str, Any], pace: str = "normal") -> float:
        """Calculate estimated time for a slide in seconds."""
        content = slide.get("content", {})
        
        # Base time from word count
        word_count = self._count_words(content)
        words_per_second = self.speaking_rates[pace] / 60
        base_time = word_count / words_per_second
        
        # Add time for visual elements
        visual_time = 0
        for element in content.get("body", []):
            element_type = element.get("type")
            if element_type in self.element_times:
                visual_time += self.element_times[element_type]
            
            # Special handling for videos
            if element_type == "video":
                duration = element.get("duration", 30)  # Default 30s if not specified
                visual_time = visual_time - 30 + duration
        
        # Add transition time
        transition_time = 3  # seconds between slides
        
        return base_time + visual_time + transition_time
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "slide_number" in content:
            # Single slide validation
            estimated_time = self._calculate_slide_time(content)
            
            if estimated_time > 120:  # More than 2 minutes per slide
                violations.append(self.create_violation(
                    message=f"Slide may take too long ({estimated_time:.0f} seconds)",
                    suggestion="Consider splitting content across multiple slides",
                    context={"estimated_seconds": estimated_time},
                    location={"slide_number": content.get("slide_number")},
                    severity=RuleSeverity.WARNING
                ))
            
        elif isinstance(content, dict) and "slides" in content:
            # Presentation-level validation
            total_time = 0
            slide_times = []
            
            for slide in content.get("slides", []):
                slide_time = self._calculate_slide_time(slide)
                total_time += slide_time
                slide_times.append({
                    "slide_number": slide.get("slide_number"),
                    "estimated_seconds": slide_time
                })
            
            total_minutes = total_time / 60
            if abs(total_minutes - context.duration_minutes) > context.duration_minutes * 0.1:
                violations.append(self.create_violation(
                    message=f"Estimated time ({total_minutes:.1f} min) differs from target ({context.duration_minutes} min)",
                    suggestion="Adjust content density or speaking pace",
                    context={
                        "estimated_minutes": total_minutes,
                        "target_minutes": context.duration_minutes,
                        "slide_times": slide_times
                    },
                    severity=RuleSeverity.INFO
                ))
        
        return violations


class PacingConsistencyRule(Rule):
    """Ensures consistent pacing throughout presentation."""
    
    def __init__(self):
        super().__init__(
            rule_id="timing.pacing",
            name="Pacing Consistency",
            description="Ensures slides have consistent information density",
            category=RuleCategory.TIMING,
            severity=RuleSeverity.INFO
        )
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        # This rule works at presentation level
        if isinstance(content, dict) and "slides" in content:
            slide_densities = []
            
            for slide in content.get("slides", []):
                # Skip title and conclusion slides
                title = slide.get("content", {}).get("title", "").lower()
                if any(skip in title for skip in ["title", "outline", "conclusion", "questions", "thank"]):
                    continue
                
                # Calculate content density (words + visual elements)
                word_count = self._count_words(slide.get("content", {}))
                visual_count = self._count_visual_elements(slide.get("content", {}))
                density = word_count + (visual_count * 20)  # Visual elements count as ~20 words
                
                slide_densities.append({
                    "slide_number": slide.get("slide_number"),
                    "density": density,
                    "word_count": word_count,
                    "visual_count": visual_count
                })
            
            if slide_densities:
                # Calculate average and standard deviation
                avg_density = sum(s["density"] for s in slide_densities) / len(slide_densities)
                variance = sum((s["density"] - avg_density) ** 2 for s in slide_densities) / len(slide_densities)
                std_dev = variance ** 0.5
                
                # Flag slides that are outliers (>2 standard deviations)
                for slide_info in slide_densities:
                    deviation = abs(slide_info["density"] - avg_density)
                    if deviation > 2 * std_dev and std_dev > 0:
                        if slide_info["density"] > avg_density:
                            violations.append(self.create_violation(
                                message=f"Slide {slide_info['slide_number']} has significantly more content than average",
                                suggestion="Consider splitting this slide or reducing content",
                                context=slide_info,
                                location={"slide_number": slide_info["slide_number"]}
                            ))
                        else:
                            violations.append(self.create_violation(
                                message=f"Slide {slide_info['slide_number']} has significantly less content than average",
                                suggestion="Consider adding more content or combining with another slide",
                                context=slide_info,
                                location={"slide_number": slide_info["slide_number"]}
                            ))
        
        return violations
    
    def _count_words(self, content: Dict[str, Any]) -> int:
        """Count words in slide content."""
        word_count = 0
        
        word_count += len(content.get("title", "").split())
        word_count += len(content.get("subtitle", "").split())
        
        for element in content.get("body", []):
            if element.get("type") == "text":
                word_count += len(element.get("content", "").split())
            elif element.get("type") == "bullet_list":
                for item in element.get("items", []):
                    word_count += len(item.get("text", "").split())
        
        return word_count
    
    def _count_visual_elements(self, content: Dict[str, Any]) -> int:
        """Count visual elements in slide."""
        visual_types = {"image", "chart", "table", "diagram", "video", "equation", "code"}
        count = 0
        
        for element in content.get("body", []):
            if element.get("type") in visual_types:
                count += 1
        
        return count


class QuestionTimeRule(Rule):
    """Ensures time is allocated for Q&A in appropriate presentations."""
    
    def __init__(self):
        super().__init__(
            rule_id="timing.question_time",
            name="Q&A Time Allocation",
            description="Ensures time for questions in formal presentations",
            category=RuleCategory.TIMING,
            severity=RuleSeverity.INFO
        )
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        # Check if presentation type typically includes Q&A
        if context.presentation_type in ["conference", "defense", "seminar"]:
            if isinstance(content, dict) and "slides" in content:
                # Check for Q&A slide
                has_qa_slide = False
                for slide in content.get("slides", []):
                    title = slide.get("content", {}).get("title", "").lower()
                    if any(qa in title for qa in ["question", "q&a", "discussion", "q & a"]):
                        has_qa_slide = True
                        break
                
                if not has_qa_slide:
                    # Calculate recommended Q&A time
                    qa_time = max(5, int(context.duration_minutes * 0.2))  # 20% or min 5 minutes
                    
                    violations.append(self.create_violation(
                        message="No Q&A slide found for formal presentation",
                        suggestion=f"Add a Questions slide and allocate ~{qa_time} minutes for discussion",
                        context={"presentation_type": context.presentation_type},
                        severity=RuleSeverity.INFO
                    ))
        
        return violations


class TransitionTimeRule(Rule):
    """Accounts for transition time between slides and sections."""
    
    def __init__(self):
        super().__init__(
            rule_id="timing.transitions",
            name="Transition Time Accounting",
            description="Ensures adequate time for slide transitions",
            category=RuleCategory.TIMING,
            severity=RuleSeverity.INFO
        )
        
        self.transition_times = {
            "normal": 3,      # Standard slide transition
            "section": 5,     # Section change
            "demo": 10,       # Live demo setup
            "video": 5,       # Video start/stop
            "interactive": 15  # Audience interaction
        }
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "slides" in content:
            slides = content.get("slides", [])
            total_transitions = len(slides) - 1
            
            # Count special transitions
            section_transitions = 0
            demo_transitions = 0
            
            for i, slide in enumerate(slides[:-1]):
                title = slide.get("content", {}).get("title", "").lower()
                next_title = slides[i + 1].get("content", {}).get("title", "").lower()
                
                # Check for section transitions
                if any(section in title for section in ["section", "part", "chapter"]):
                    section_transitions += 1
                
                # Check for demo transitions
                if "demo" in title or "demo" in next_title:
                    demo_transitions += 1
            
            # Calculate total transition time
            normal_transitions = total_transitions - section_transitions - demo_transitions
            transition_time = (
                normal_transitions * self.transition_times["normal"] +
                section_transitions * self.transition_times["section"] +
                demo_transitions * self.transition_times["demo"]
            )
            
            transition_minutes = transition_time / 60
            
            # Warn if transitions take significant time
            if transition_minutes > context.duration_minutes * 0.1:  # More than 10% of time
                violations.append(self.create_violation(
                    message=f"Slide transitions may take {transition_minutes:.1f} minutes",
                    suggestion="Account for transition time in your presentation planning",
                    context={
                        "total_transitions": total_transitions,
                        "transition_seconds": transition_time
                    },
                    severity=RuleSeverity.INFO
                ))
        
        return violations


def register_timing_rules(engine=None):
    """Register all timing rules with the rule engine."""
    if engine is None:
        engine = get_rule_engine()
    
    # Register rules with appropriate rule sets
    rules = [
        (SlideCountRule(), ["conference", "lecture", "defense", "seminar", "workshop"]),
        (SlideTimingEstimateRule(), ["conference", "defense", "seminar"]),
        (PacingConsistencyRule(), ["conference", "lecture", "defense"]),
        (QuestionTimeRule(), ["conference", "defense", "seminar"]),
        (TransitionTimeRule(), ["conference", "defense"])
    ]
    
    for rule, rule_sets in rules:
        engine.register_rule(rule, rule_sets)