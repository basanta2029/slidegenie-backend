"""
SlideGenie Content Rules Engine

Provides comprehensive validation for academic presentations including:
- Text constraints (bullet points, word limits, density)
- Academic tone and citation requirements
- Timing and pacing calculations
- Visual element limits and quality checks
"""

# Base classes and types
from app.services.slides.rules.base import (
    Rule,
    CompositeRule,
    RuleEngine,
    RuleCategory,
    RuleSeverity,
    RuleContext,
    RuleViolation,
    get_rule_engine
)

# Specific rule implementations
from app.services.slides.rules.text_rules import (
    BulletPointCountRule,
    BulletPointLengthRule,
    TitleLengthRule,
    TextDensityRule,
    ReadabilityScoreRule,
    ConsistentTerminologyRule,
    register_text_rules
)

from app.services.slides.rules.academic_rules import (
    AcademicToneRule,
    CitationPresenceRule,
    CitationFormatRule,
    AcademicVocabularyRule,
    ReferencesSlideRule,
    register_academic_rules
)

from app.services.slides.rules.timing_rules import (
    SlideCountRule,
    SlideTimingEstimateRule,
    PacingConsistencyRule,
    QuestionTimeRule,
    TransitionTimeRule,
    register_timing_rules
)

from app.services.slides.rules.visual_rules import (
    VisualElementCountRule,
    ImageQualityRule,
    ChartComplexityRule,
    TableSizeRule,
    ColorContrastRule,
    AnimationUseRule,
    VisualBalanceRule,
    register_visual_rules
)

# High-level validators
from app.services.slides.rules.validators import (
    PresentationValidator,
    SlideValidator,
    QuickValidator,
    ConfigurableValidator,
    validate_presentation,
    validate_slide,
    quick_validate_text
)

__all__ = [
    # Base classes
    "Rule",
    "CompositeRule",
    "RuleEngine",
    "RuleCategory",
    "RuleSeverity",
    "RuleContext",
    "RuleViolation",
    "get_rule_engine",
    
    # Text rules
    "BulletPointCountRule",
    "BulletPointLengthRule",
    "TitleLengthRule",
    "TextDensityRule",
    "ReadabilityScoreRule",
    "ConsistentTerminologyRule",
    "register_text_rules",
    
    # Academic rules
    "AcademicToneRule",
    "CitationPresenceRule",
    "CitationFormatRule",
    "AcademicVocabularyRule",
    "ReferencesSlideRule",
    "register_academic_rules",
    
    # Timing rules
    "SlideCountRule",
    "SlideTimingEstimateRule",
    "PacingConsistencyRule",
    "QuestionTimeRule",
    "TransitionTimeRule",
    "register_timing_rules",
    
    # Visual rules
    "VisualElementCountRule",
    "ImageQualityRule",
    "ChartComplexityRule",
    "TableSizeRule",
    "ColorContrastRule",
    "AnimationUseRule",
    "VisualBalanceRule",
    "register_visual_rules",
    
    # Validators
    "PresentationValidator",
    "SlideValidator",
    "QuickValidator",
    "ConfigurableValidator",
    "validate_presentation",
    "validate_slide",
    "quick_validate_text"
]


# Example usage and configuration
"""
Example 1: Validate a complete presentation
------------------------------------------
from app.services.slides.rules import validate_presentation

result = validate_presentation(
    presentation={
        "title": "My Research Presentation",
        "slides": [...]
    },
    presentation_type="conference",
    academic_level="graduate",
    duration_minutes=15,
    strict_mode=False
)

if not result["valid"]:
    print(f"Found {result['summary']['total_errors']} errors")
    for slide_num, slide_result in result["slide_results"].items():
        for error in slide_result["errors"]:
            print(f"Slide {slide_num}: {error.message}")


Example 2: Quick validation during editing
------------------------------------------
from app.services.slides.rules import quick_validate_text

issues = quick_validate_text(
    text="This bullet point has way too many words and should be shortened",
    element_type="bullet",
    presentation_type="conference"
)

for issue in issues:
    print(f"{issue['severity']}: {issue['message']}")
    if issue['suggestion']:
        print(f"  Suggestion: {issue['suggestion']}")


Example 3: Custom rule configuration
------------------------------------
from app.services.slides.rules import ConfigurableValidator

config = {
    "rules": {
        "text.bullet_count": {
            "enabled": True,
            "severity": "error",
            "config": {"max_bullets": 4}
        },
        "academic.tone": {
            "enabled": False  # Disable for informal presentations
        }
    }
}

validator = ConfigurableValidator(config)
result = validator.validate(content, context)


Example 4: Create custom rules
------------------------------
from app.services.slides.rules import Rule, RuleCategory, RuleSeverity

class CustomBrandingRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="custom.branding",
            name="Company Branding Check",
            description="Ensures company branding guidelines are followed",
            category=RuleCategory.VISUAL,
            severity=RuleSeverity.WARNING
        )
    
    def validate(self, content, context):
        violations = []
        # Custom validation logic
        return violations

# Register with engine
engine = get_rule_engine()
engine.register_rule(CustomBrandingRule(), ["conference"])
"""