"""
Usage examples for the SlideGenie content rules engine.

This file demonstrates how to integrate the rules engine into your application.
"""
from typing import Dict, Any, List
from app.services.slides.rules import (
    validate_presentation,
    validate_slide,
    quick_validate_text,
    PresentationValidator,
    ConfigurableValidator,
    RuleEngine,
    Rule,
    RuleCategory,
    RuleSeverity,
    RuleContext,
    RuleViolation,
    get_rule_engine
)


def example_1_basic_presentation_validation():
    """Example 1: Validate a complete presentation."""
    print("Example 1: Basic Presentation Validation")
    print("-" * 50)
    
    # Sample presentation data
    presentation = {
        "title": "Introduction to Quantum Computing",
        "author": "Dr. Jane Smith",
        "slides": [
            {
                "slide_number": 1,
                "content": {
                    "title": "Introduction to Quantum Computing",
                    "subtitle": "The Future of Computation"
                }
            },
            {
                "slide_number": 2,
                "content": {
                    "title": "Classical vs Quantum",
                    "body": [
                        {
                            "type": "bullet_list",
                            "items": [
                                {"text": "Classical bits: 0 or 1"},
                                {"text": "Quantum bits (qubits): superposition of 0 and 1"},
                                {"text": "Entanglement enables parallel computation"},
                                {"text": "Quantum interference for optimization"},
                                {"text": "Decoherence is the main challenge"},
                                {"text": "Error correction is crucial"},  # Too many bullets
                                {"text": "Applications in cryptography"}
                            ]
                        }
                    ]
                }
            },
            {
                "slide_number": 3,
                "content": {
                    "title": "Key Research Findings",
                    "body": [
                        {
                            "type": "text",
                            "content": "Recent studies show quantum supremacy achieved with 53 qubits."  # Missing citation
                        },
                        {
                            "type": "image",
                            "url": "quantum_processor.jpg"
                            # Missing attribution
                        }
                    ]
                }
            }
        ]
    }
    
    # Validate the presentation
    result = validate_presentation(
        presentation=presentation,
        presentation_type="conference",
        academic_level="graduate",
        duration_minutes=15,
        strict_mode=False
    )
    
    # Display results
    print(f"Validation Result: {'PASSED' if result['valid'] else 'FAILED'}")
    print(f"Total Errors: {result['summary']['total_errors']}")
    print(f"Total Warnings: {result['summary']['total_warnings']}")
    print(f"Total Info: {result['summary']['total_info']}")
    
    # Show specific violations
    if not result['valid']:
        print("\nViolations Found:")
        for slide_num, slide_result in result['slide_results'].items():
            if slide_result['violations']:
                print(f"\n  Slide {slide_num}:")
                for violation in slide_result['violations']:
                    print(f"    [{violation.severity.value}] {violation.message}")
                    if violation.suggestion:
                        print(f"      → {violation.suggestion}")
    
    print()


def example_2_real_time_validation():
    """Example 2: Real-time validation during editing."""
    print("Example 2: Real-time Text Validation")
    print("-" * 50)
    
    # Simulate user typing different content
    test_inputs = [
        ("This is a good bullet point", "bullet"),
        ("This bullet point is way too long and contains too many words that make it hard to read quickly", "bullet"),
        ("We can't use contractions in formal presentations", "text"),
        ("Studies indicate 90% improvement in performance", "text"),
        ("Quantum Computing: The Future of Technology and Its Implications for Modern Society", "title"),
    ]
    
    for text, element_type in test_inputs:
        print(f"\nValidating: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        print(f"Element type: {element_type}")
        
        issues = quick_validate_text(
            text=text,
            element_type=element_type,
            presentation_type="conference"
        )
        
        if issues:
            for issue in issues:
                print(f"  [{issue['severity']}] {issue['message']}")
                if issue.get('suggestion'):
                    print(f"    → {issue['suggestion']}")
        else:
            print("  ✓ No issues found")


def example_3_custom_configuration():
    """Example 3: Custom rule configuration for different contexts."""
    print("Example 3: Custom Rule Configuration")
    print("-" * 50)
    
    # Configuration for a more relaxed workshop presentation
    workshop_config = {
        "rules": {
            "text.bullet_count": {
                "enabled": True,
                "severity": "info",  # Downgrade from warning
                "config": {"max_bullets": 7}  # Allow more bullets
            },
            "text.bullet_length": {
                "enabled": True,
                "config": {"max_words": 15}  # Allow slightly longer bullets
            },
            "academic.tone": {
                "enabled": False  # Disable formal tone checking
            },
            "academic.citation_presence": {
                "enabled": False  # Don't require citations
            }
        }
    }
    
    # Configuration for strict academic defense
    defense_config = {
        "rules": {
            "text.bullet_count": {
                "enabled": True,
                "severity": "error",  # Upgrade to error
                "config": {"max_bullets": 4}  # Stricter limit
            },
            "text.bullet_length": {
                "enabled": True,
                "severity": "error",
                "config": {"max_words": 8}  # Shorter bullets
            },
            "academic.tone": {
                "enabled": True,
                "severity": "error"  # Strict tone enforcement
            },
            "academic.citation_presence": {
                "enabled": True,
                "severity": "error"  # Citations required
            }
        }
    }
    
    # Test slide with informal content
    test_slide = {
        "slide_number": 1,
        "content": {
            "title": "Results",
            "body": [{
                "type": "bullet_list",
                "items": [
                    {"text": "We got awesome results"},
                    {"text": "Performance improved a lot"},
                    {"text": "Users really loved the new features"},
                    {"text": "System is way faster now"},
                    {"text": "Bugs are pretty much gone"}
                ]
            }]
        }
    }
    
    # Validate with workshop configuration
    print("\nValidating with Workshop Configuration:")
    workshop_validator = ConfigurableValidator(workshop_config)
    context = RuleContext("workshop", "undergraduate", 30, 10)
    workshop_result = workshop_validator.validate(test_slide, context)
    print(f"  Errors: {len(workshop_result['errors'])}")
    print(f"  Warnings: {len(workshop_result['warnings'])}")
    print(f"  Info: {len(workshop_result['info'])}")
    
    # Validate with defense configuration
    print("\nValidating with Defense Configuration:")
    defense_validator = ConfigurableValidator(defense_config)
    context = RuleContext("defense", "graduate", 30, 10)
    defense_result = defense_validator.validate(test_slide, context)
    print(f"  Errors: {len(defense_result['errors'])}")
    print(f"  Warnings: {len(defense_result['warnings'])}")
    print(f"  Info: {len(defense_result['info'])}")


def example_4_custom_rule():
    """Example 4: Creating and registering custom rules."""
    print("Example 4: Custom Rule Implementation")
    print("-" * 50)
    
    class InstitutionBrandingRule(Rule):
        """Custom rule to ensure institution branding compliance."""
        
        def __init__(self, institution_name: str):
            super().__init__(
                rule_id="custom.institution_branding",
                name="Institution Branding Check",
                description=f"Ensures {institution_name} branding guidelines are followed",
                category=RuleCategory.VISUAL,
                severity=RuleSeverity.WARNING
            )
            self.institution_name = institution_name
        
        def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
            violations = []
            
            # Check if first slide has institution name
            if isinstance(content, dict) and content.get("slide_number") == 1:
                title = content.get("content", {}).get("title", "")
                subtitle = content.get("content", {}).get("subtitle", "")
                
                if self.institution_name not in title and self.institution_name not in subtitle:
                    violations.append(self.create_violation(
                        message=f"First slide should include '{self.institution_name}'",
                        suggestion=f"Add '{self.institution_name}' to title or subtitle",
                        location={"slide_number": 1}
                    ))
            
            return violations
    
    class AcronymDefinitionRule(Rule):
        """Custom rule to ensure acronyms are defined on first use."""
        
        def __init__(self):
            super().__init__(
                rule_id="custom.acronym_definition",
                name="Acronym Definition Check",
                description="Ensures acronyms are defined on first use",
                category=RuleCategory.TEXT,
                severity=RuleSeverity.INFO
            )
            self.seen_acronyms = set()
        
        def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
            violations = []
            
            if isinstance(content, dict) and "content" in content:
                # Extract all text
                all_text = self._extract_text(content.get("content", {}))
                
                # Find potential acronyms (2+ capital letters)
                import re
                acronyms = re.findall(r'\b[A-Z]{2,}\b', all_text)
                
                for acronym in acronyms:
                    if acronym not in self.seen_acronyms:
                        # Check if definition follows the acronym
                        pattern = rf'{acronym}\s*\([^)]+\)'
                        if not re.search(pattern, all_text):
                            violations.append(self.create_violation(
                                message=f"Acronym '{acronym}' used without definition",
                                suggestion=f"Define '{acronym}' on first use, e.g., '{acronym} (Full Name)'",
                                location={"slide_number": content.get("slide_number")}
                            ))
                        self.seen_acronyms.add(acronym)
            
            return violations
        
        def _extract_text(self, content: Dict[str, Any]) -> str:
            """Extract all text from content."""
            texts = []
            texts.append(content.get("title", ""))
            texts.append(content.get("subtitle", ""))
            
            for element in content.get("body", []):
                if element.get("type") == "text":
                    texts.append(element.get("content", ""))
                elif element.get("type") == "bullet_list":
                    for item in element.get("items", []):
                        texts.append(item.get("text", ""))
            
            return " ".join(texts)
    
    # Register custom rules
    engine = get_rule_engine()
    engine.register_rule(
        InstitutionBrandingRule("MIT"),
        ["conference", "defense"]
    )
    engine.register_rule(
        AcronymDefinitionRule(),
        ["conference", "lecture", "defense"]
    )
    
    # Test with custom rules
    test_slide = {
        "slide_number": 1,
        "content": {
            "title": "Advanced AI Research",
            "body": [{
                "type": "text",
                "content": "Our ML and NLP systems use BERT for text processing."
            }]
        }
    }
    
    validator = PresentationValidator()
    result = validator.validate_slide(test_slide, "conference", "graduate")
    
    print("Custom Rule Violations:")
    for violation in result['violations']:
        if violation.rule_id.startswith("custom."):
            print(f"  [{violation.severity.value}] {violation.message}")
            if violation.suggestion:
                print(f"    → {violation.suggestion}")


def example_5_integration_with_api():
    """Example 5: Integration with FastAPI endpoint."""
    print("Example 5: API Integration Example")
    print("-" * 50)
    
    # This would typically be in your FastAPI route
    async def validate_slide_endpoint(
        slide_data: Dict[str, Any],
        presentation_type: str = "lecture",
        academic_level: str = "graduate"
    ) -> Dict[str, Any]:
        """API endpoint for slide validation."""
        
        # Validate the slide
        result = validate_slide(
            slide=slide_data,
            presentation_type=presentation_type,
            academic_level=academic_level
        )
        
        # Format response for API
        response = {
            "valid": result["valid"],
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "severity": v.severity.value,
                    "message": v.message,
                    "suggestion": v.suggestion,
                    "location": v.location
                }
                for v in result["violations"]
            ],
            "summary": result["summary"]
        }
        
        return response
    
    # Example usage
    test_slide = {
        "slide_number": 2,
        "content": {
            "title": "Methodology",
            "body": [{
                "type": "bullet_list",
                "items": [
                    {"text": "Collected data from 100 participants"},
                    {"text": "Used standard statistical analysis"},
                    {"text": "Results were pretty good"}  # Informal
                ]
            }]
        }
    }
    
    # Simulate API call
    import asyncio
    api_result = asyncio.run(validate_slide_endpoint(test_slide, "conference", "graduate"))
    
    print("API Response:")
    print(f"  Valid: {api_result['valid']}")
    print(f"  Violations: {len(api_result['violations'])}")
    for v in api_result['violations']:
        print(f"    - [{v['severity']}] {v['message']}")


if __name__ == "__main__":
    # Run all examples
    examples = [
        example_1_basic_presentation_validation,
        example_2_real_time_validation,
        example_3_custom_configuration,
        example_4_custom_rule,
        example_5_integration_with_api
    ]
    
    for i, example in enumerate(examples, 1):
        example()
        if i < len(examples):
            print("\n" + "=" * 70 + "\n")