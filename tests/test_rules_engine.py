"""
Tests for the SlideGenie content rules engine.
"""
import pytest
from app.services.slides.rules import (
    validate_presentation,
    validate_slide,
    quick_validate_text,
    RuleCategory,
    RuleSeverity,
    ConfigurableValidator
)


class TestTextRules:
    """Test text constraint rules."""
    
    def test_bullet_point_count_rule(self):
        """Test bullet point count limits."""
        slide = {
            "slide_number": 1,
            "content": {
                "title": "Test Slide",
                "body": [{
                    "type": "bullet_list",
                    "items": [
                        {"text": "Point 1"},
                        {"text": "Point 2"},
                        {"text": "Point 3"},
                        {"text": "Point 4"},
                        {"text": "Point 5"},
                        {"text": "Point 6"},  # Exceeds default limit of 5
                    ]
                }]
            }
        }
        
        result = validate_slide(slide, "conference", "graduate")
        assert not result["valid"]
        assert any("bullet points" in v.message for v in result["violations"])
    
    def test_bullet_point_length_rule(self):
        """Test bullet point word limit."""
        issues = quick_validate_text(
            "This is a very long bullet point that contains way too many words",
            "bullet",
            "conference"
        )
        
        assert len(issues) > 0
        assert any("words" in issue["message"] for issue in issues)
    
    def test_title_length_rule(self):
        """Test slide title character limit."""
        slide = {
            "slide_number": 1,
            "content": {
                "title": "This is an extremely long title that definitely exceeds the character limit and should be shortened"
            }
        }
        
        result = validate_slide(slide, "conference", "graduate")
        assert any("Title" in v.message and "characters" in v.message for v in result["violations"])


class TestAcademicRules:
    """Test academic tone and citation rules."""
    
    def test_informal_language_detection(self):
        """Test detection of informal phrases."""
        slide = {
            "slide_number": 1,
            "content": {
                "title": "Test Results",
                "body": [{
                    "type": "text",
                    "content": "The results are pretty much awesome and show lots of cool stuff."
                }]
            }
        }
        
        result = validate_slide(slide, "conference", "graduate")
        violations = [v for v in result["violations"] if "informal" in v.message.lower()]
        assert len(violations) > 0
    
    def test_citation_requirement(self):
        """Test citation presence for claims."""
        slide = {
            "slide_number": 1,
            "content": {
                "body": [{
                    "type": "text",
                    "content": "Studies show that 85% of presentations lack proper citations."
                }]
            }
        }
        
        result = validate_slide(slide, "conference", "graduate")
        assert any("citation" in v.message.lower() for v in result["violations"])
    
    def test_citation_format_consistency(self):
        """Test mixed citation format detection."""
        slide = {
            "slide_number": 1,
            "content": {
                "body": [{
                    "type": "text",
                    "content": "Some research (Smith, 2023) contradicts earlier findings [1]."
                }]
            }
        }
        
        result = validate_slide(slide, "conference", "graduate")
        assert any("mixed citation" in v.message.lower() for v in result["violations"])


class TestTimingRules:
    """Test presentation timing rules."""
    
    def test_slide_count_for_duration(self):
        """Test appropriate slide count for presentation duration."""
        presentation = {
            "title": "Test Presentation",
            "slides": [{"slide_number": i, "content": {}} for i in range(1, 6)]  # 5 slides
        }
        
        # 5 slides for 15 minutes should be fine
        result = validate_presentation(presentation, "conference", "graduate", 15)
        timing_errors = [v for v in result["presentation_violations"] if v.rule_id == "timing.slide_count"]
        assert len(timing_errors) == 0
        
        # 5 slides for 3 minutes is too many
        result = validate_presentation(presentation, "conference", "graduate", 3)
        timing_errors = [v for v in result["presentation_violations"] if v.rule_id == "timing.slide_count"]
        assert len(timing_errors) > 0


class TestVisualRules:
    """Test visual element rules."""
    
    def test_visual_element_count(self):
        """Test visual element limits."""
        slide = {
            "slide_number": 1,
            "content": {
                "body": [
                    {"type": "image", "url": "image1.png"},
                    {"type": "chart", "data": {}},
                    {"type": "table", "headers": [], "rows": []},  # Exceeds default limit of 2
                ]
            }
        }
        
        result = validate_slide(slide, "conference", "graduate")
        assert any("visual elements" in v.message for v in result["violations"])
    
    def test_table_size_limit(self):
        """Test table size constraints."""
        slide = {
            "slide_number": 1,
            "content": {
                "body": [{
                    "type": "table",
                    "headers": ["Col1", "Col2", "Col3", "Col4", "Col5", "Col6"],  # Too many columns
                    "rows": [["data"] * 6 for _ in range(10)]  # Too many rows
                }]
            }
        }
        
        result = validate_slide(slide, "conference", "graduate")
        table_violations = [v for v in result["violations"] if "table" in v.message.lower()]
        assert len(table_violations) > 0


class TestPresentationValidation:
    """Test full presentation validation."""
    
    def test_complete_presentation_validation(self):
        """Test validation of a complete presentation."""
        presentation = {
            "title": "Machine Learning in Healthcare",
            "slides": [
                {
                    "slide_number": 1,
                    "content": {
                        "title": "Machine Learning in Healthcare",
                        "subtitle": "Transforming Patient Care"
                    }
                },
                {
                    "slide_number": 2,
                    "content": {
                        "title": "Introduction",
                        "body": [{
                            "type": "bullet_list",
                            "items": [
                                {"text": "ML applications in diagnosis"},
                                {"text": "Predictive analytics"},
                                {"text": "Treatment optimization"}
                            ]
                        }]
                    }
                },
                {
                    "slide_number": 3,
                    "content": {
                        "title": "Key Findings",
                        "body": [
                            {
                                "type": "text",
                                "content": "Recent studies demonstrate 95% accuracy in early detection (Smith et al., 2023)."
                            },
                            {
                                "type": "chart",
                                "data": {
                                    "x_label": "Year",
                                    "y_label": "Accuracy (%)",
                                    "series": [{"data": [85, 90, 95]}]
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        result = validate_presentation(
            presentation,
            "conference",
            "graduate",
            duration_minutes=10
        )
        
        assert "valid" in result
        assert "summary" in result
        assert "slide_results" in result
        assert result["summary"]["total_slides"] == 3


class TestConfigurableValidator:
    """Test configurable validation."""
    
    def test_custom_rule_configuration(self):
        """Test custom rule configuration."""
        config = {
            "rules": {
                "text.bullet_count": {
                    "enabled": True,
                    "severity": "error",
                    "config": {"max_bullets": 3}  # Stricter than default
                },
                "academic.tone": {
                    "enabled": False  # Disable for this test
                }
            }
        }
        
        validator = ConfigurableValidator(config)
        
        slide = {
            "slide_number": 1,
            "content": {
                "body": [{
                    "type": "bullet_list",
                    "items": [
                        {"text": "Point 1"},
                        {"text": "Point 2"},
                        {"text": "Point 3"},
                        {"text": "Point 4"}  # Exceeds configured limit of 3
                    ]
                }]
            }
        }
        
        from app.services.slides.rules import RuleContext
        context = RuleContext(
            presentation_type="conference",
            academic_level="graduate",
            duration_minutes=15,
            slide_count=1
        )
        
        result = validator.validate(slide, context)
        
        # Should have error (not warning) due to configuration
        assert len(result["errors"]) > 0
        assert any("bullet points" in v.message for v in result["errors"])


class TestQuickValidation:
    """Test quick validation for real-time feedback."""
    
    def test_quick_text_validation(self):
        """Test quick validation during typing."""
        # Test various text inputs
        test_cases = [
            ("Short bullet", "bullet", []),  # Should pass
            ("This is a very long bullet point with too many words", "bullet", ["words"]),
            ("Can't use contractions", "text", ["informal"]),
            ("Good academic text", "text", [])
        ]
        
        for text, element_type, expected_keywords in test_cases:
            issues = quick_validate_text(text, element_type, "conference")
            
            if expected_keywords:
                assert len(issues) > 0
                issue_messages = " ".join(issue["message"] for issue in issues)
                for keyword in expected_keywords:
                    assert keyword in issue_messages.lower()
            else:
                # Clean text should have no issues
                assert len(issues) == 0 or all(issue["severity"] == "info" for issue in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])