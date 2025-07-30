"""
High-level validators that combine multiple rules for comprehensive validation.
"""
from typing import Any, Dict, List, Optional

from app.services.slides.rules.base import (
    RuleContext,
    RuleCategory,
    RuleSeverity,
    get_rule_engine
)
from app.services.slides.rules.text_rules import register_text_rules
from app.services.slides.rules.academic_rules import register_academic_rules
from app.services.slides.rules.timing_rules import register_timing_rules
from app.services.slides.rules.visual_rules import register_visual_rules


class PresentationValidator:
    """Main validator for entire presentations."""
    
    def __init__(self):
        self.engine = get_rule_engine()
        self._register_all_rules()
    
    def _register_all_rules(self):
        """Register all rule modules with the engine."""
        register_text_rules(self.engine)
        register_academic_rules(self.engine)
        register_timing_rules(self.engine)
        register_visual_rules(self.engine)
    
    def validate_presentation(
        self,
        presentation: Dict[str, Any],
        presentation_type: str,
        academic_level: str,
        duration_minutes: int,
        strict_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Validate an entire presentation.
        
        Args:
            presentation: Presentation data with slides
            presentation_type: Type of presentation (conference, lecture, etc.)
            academic_level: Academic level (undergraduate, graduate, etc.)
            duration_minutes: Target presentation duration
            strict_mode: If True, warnings are treated as errors
            
        Returns:
            Validation results with violations and suggestions
        """
        # Create context
        context = RuleContext(
            presentation_type=presentation_type,
            academic_level=academic_level,
            duration_minutes=duration_minutes,
            slide_count=len(presentation.get("slides", []))
        )
        
        # Validate presentation-level rules
        pres_result = self.engine.validate_content(
            presentation,
            context,
            categories=[RuleCategory.STRUCTURE, RuleCategory.TIMING, RuleCategory.ACADEMIC]
        )
        
        # Validate each slide
        slide_results = {}
        total_errors = 0
        total_warnings = 0
        total_info = 0
        
        for slide in presentation.get("slides", []):
            slide_num = slide.get("slide_number", 0)
            context.current_slide = slide
            
            # Validate slide
            slide_result = self.engine.validate_content(slide, context)
            slide_results[slide_num] = slide_result
            
            # Update totals
            total_errors += len(slide_result["errors"])
            total_warnings += len(slide_result["warnings"])
            total_info += len(slide_result["info"])
        
        # In strict mode, treat warnings as errors
        if strict_mode:
            total_errors += total_warnings
            total_warnings = 0
        
        # Compile final results
        return {
            "valid": total_errors == 0,
            "presentation_type": presentation_type,
            "academic_level": academic_level,
            "duration_minutes": duration_minutes,
            "summary": {
                "total_slides": len(presentation.get("slides", [])),
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_info": total_info,
                "rules_checked": pres_result["rules_checked"]
            },
            "presentation_violations": pres_result["violations"],
            "slide_results": slide_results,
            "suggestions": self._generate_suggestions(pres_result, slide_results)
        }
    
    def _generate_suggestions(
        self,
        pres_result: Dict[str, Any],
        slide_results: Dict[int, Dict[str, Any]]
    ) -> List[str]:
        """Generate high-level suggestions based on validation results."""
        suggestions = []
        
        # Analyze common issues
        error_counts = {}
        warning_counts = {}
        
        for violation in pres_result["violations"]:
            key = violation.rule_id
            if violation.severity == RuleSeverity.ERROR:
                error_counts[key] = error_counts.get(key, 0) + 1
            elif violation.severity == RuleSeverity.WARNING:
                warning_counts[key] = warning_counts.get(key, 0) + 1
        
        for slide_result in slide_results.values():
            for violation in slide_result["violations"]:
                key = violation.rule_id
                if violation.severity == RuleSeverity.ERROR:
                    error_counts[key] = error_counts.get(key, 0) + 1
                elif violation.severity == RuleSeverity.WARNING:
                    warning_counts[key] = warning_counts.get(key, 0) + 1
        
        # Generate suggestions for most common issues
        if error_counts:
            most_common_error = max(error_counts, key=error_counts.get)
            count = error_counts[most_common_error]
            suggestions.append(
                f"Focus on fixing '{most_common_error}' errors (found {count} times)"
            )
        
        if warning_counts:
            most_common_warning = max(warning_counts, key=warning_counts.get)
            count = warning_counts[most_common_warning]
            if count > 3:
                suggestions.append(
                    f"Consider addressing '{most_common_warning}' warnings (found {count} times)"
                )
        
        return suggestions


class SlideValidator:
    """Validator for individual slides."""
    
    def __init__(self):
        self.engine = get_rule_engine()
        self._register_all_rules()
    
    def _register_all_rules(self):
        """Register all rule modules with the engine."""
        register_text_rules(self.engine)
        register_academic_rules(self.engine)
        register_timing_rules(self.engine)
        register_visual_rules(self.engine)
    
    def validate_slide(
        self,
        slide: Dict[str, Any],
        presentation_type: str,
        academic_level: str,
        categories: Optional[List[RuleCategory]] = None
    ) -> Dict[str, Any]:
        """
        Validate a single slide.
        
        Args:
            slide: Slide data
            presentation_type: Type of presentation
            academic_level: Academic level
            categories: Specific categories to validate (None = all)
            
        Returns:
            Validation results
        """
        context = RuleContext(
            presentation_type=presentation_type,
            academic_level=academic_level,
            duration_minutes=30,  # Default, not used for single slide
            slide_count=1,
            current_slide=slide
        )
        
        return self.engine.validate_content(slide, context, categories=categories)


class QuickValidator:
    """Quick validation for real-time feedback during editing."""
    
    def __init__(self):
        self.engine = get_rule_engine()
        # Only register essential rules for speed
        register_text_rules(self.engine)
    
    def validate_text(
        self,
        text: str,
        element_type: str,
        presentation_type: str = "lecture"
    ) -> List[Dict[str, Any]]:
        """
        Quick validation for text input.
        
        Args:
            text: Text to validate
            element_type: Type of element (bullet, title, text)
            presentation_type: Type of presentation
            
        Returns:
            List of validation issues
        """
        # Create minimal content structure
        if element_type == "bullet":
            content = {
                "content": {
                    "body": [{
                        "type": "bullet_list",
                        "items": [{"text": text}]
                    }]
                }
            }
        elif element_type == "title":
            content = {
                "content": {
                    "title": text
                }
            }
        else:
            content = {
                "content": {
                    "body": [{
                        "type": "text",
                        "content": text
                    }]
                }
            }
        
        context = RuleContext(
            presentation_type=presentation_type,
            academic_level="graduate",
            duration_minutes=30,
            slide_count=1
        )
        
        result = self.engine.validate_content(
            content,
            context,
            categories=[RuleCategory.TEXT]
        )
        
        # Return simplified results
        issues = []
        for violation in result["violations"]:
            issues.append({
                "severity": violation.severity.value,
                "message": violation.message,
                "suggestion": violation.suggestion
            })
        
        return issues


class ConfigurableValidator:
    """Validator with configurable rules and thresholds."""
    
    def __init__(self, config: Dict[str, Any]):
        self.engine = get_rule_engine()
        self.config = config
        self._configure_rules()
    
    def _configure_rules(self):
        """Configure rules based on provided config."""
        # Register all rules first
        register_text_rules(self.engine)
        register_academic_rules(self.engine)
        register_timing_rules(self.engine)
        register_visual_rules(self.engine)
        
        # Apply configuration
        for rule_id, rule_config in self.config.get("rules", {}).items():
            if rule_id in self.engine.rules:
                rule = self.engine.rules[rule_id]
                
                # Update enabled status
                if "enabled" in rule_config:
                    rule.enabled = rule_config["enabled"]
                
                # Update severity
                if "severity" in rule_config:
                    severity_str = rule_config["severity"]
                    rule.severity = RuleSeverity[severity_str.upper()]
                
                # Update rule-specific config
                if "config" in rule_config:
                    rule.config.update(rule_config["config"])
    
    def validate(
        self,
        content: Any,
        context: RuleContext,
        **kwargs
    ) -> Dict[str, Any]:
        """Validate content with configured rules."""
        return self.engine.validate_content(content, context, **kwargs)


# Convenience functions
def validate_presentation(
    presentation: Dict[str, Any],
    presentation_type: str,
    academic_level: str,
    duration_minutes: int,
    strict_mode: bool = False
) -> Dict[str, Any]:
    """Convenience function to validate a presentation."""
    validator = PresentationValidator()
    return validator.validate_presentation(
        presentation,
        presentation_type,
        academic_level,
        duration_minutes,
        strict_mode
    )


def validate_slide(
    slide: Dict[str, Any],
    presentation_type: str,
    academic_level: str,
    categories: Optional[List[RuleCategory]] = None
) -> Dict[str, Any]:
    """Convenience function to validate a slide."""
    validator = SlideValidator()
    return validator.validate_slide(
        slide,
        presentation_type,
        academic_level,
        categories
    )


def quick_validate_text(
    text: str,
    element_type: str,
    presentation_type: str = "lecture"
) -> List[Dict[str, Any]]:
    """Convenience function for quick text validation."""
    validator = QuickValidator()
    return validator.validate_text(text, element_type, presentation_type)