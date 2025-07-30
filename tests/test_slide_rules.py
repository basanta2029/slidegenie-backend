"""Tests for slide rules engine."""

import pytest
from unittest.mock import Mock, patch
from typing import List

from app.services.slides.interfaces import (
    IRule, IRulesEngine, SlideContent, PresentationContent,
    ValidationResult
)


class MockRule(IRule):
    """Mock implementation of a rule."""
    
    def __init__(self, name: str, category: str, is_valid: bool = True):
        self._name = name
        self._category = category
        self._is_valid = is_valid
        self.validate_called = False
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def category(self) -> str:
        return self._category
    
    def validate(self, content) -> ValidationResult:
        self.validate_called = True
        self.last_content = content
        
        if self._is_valid:
            return ValidationResult(
                is_valid=True,
                warnings=["Minor issue"] if self.name == "warning_rule" else None
            )
        else:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation failed for {self.name}"],
                suggestions=["Fix the issue"]
            )


class MockRulesEngine(IRulesEngine):
    """Mock implementation of rules engine."""
    
    def __init__(self):
        self.rules: List[IRule] = []
        self.validate_slide_calls = 0
        self.validate_presentation_calls = 0
    
    def add_rule(self, rule: IRule) -> None:
        self.rules.append(rule)
    
    def validate_slide(self, slide: SlideContent) -> ValidationResult:
        self.validate_slide_calls += 1
        
        errors = []
        warnings = []
        suggestions = []
        
        for rule in self.rules:
            result = rule.validate(slide)
            if not result.is_valid:
                if result.errors:
                    errors.extend(result.errors)
                if result.suggestions:
                    suggestions.extend(result.suggestions)
            if result.warnings:
                warnings.extend(result.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors if errors else None,
            warnings=warnings if warnings else None,
            suggestions=suggestions if suggestions else None
        )
    
    def validate_presentation(self, presentation: PresentationContent) -> ValidationResult:
        self.validate_presentation_calls += 1
        
        all_errors = []
        all_warnings = []
        all_suggestions = []
        
        # Validate each slide
        for slide in presentation.slides:
            result = self.validate_slide(slide)
            if result.errors:
                all_errors.extend(result.errors)
            if result.warnings:
                all_warnings.extend(result.warnings)
            if result.suggestions:
                all_suggestions.extend(result.suggestions)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors if all_errors else None,
            warnings=all_warnings if all_warnings else None,
            suggestions=all_suggestions if all_suggestions else None
        )
    
    def get_rules_by_category(self, category: str) -> List[IRule]:
        return [rule for rule in self.rules if rule.category == category]


class TestRules:
    """Test suite for individual rules."""
    
    def test_rule_properties(self):
        """Test rule basic properties."""
        rule = MockRule("test_rule", "content")
        
        assert rule.name == "test_rule"
        assert rule.category == "content"
    
    def test_rule_validation_pass(self):
        """Test successful validation."""
        rule = MockRule("test_rule", "content", is_valid=True)
        slide = SlideContent(title="Test", content="Content")
        
        result = rule.validate(slide)
        
        assert result.is_valid is True
        assert result.errors is None
        assert rule.validate_called
        assert rule.last_content == slide
    
    def test_rule_validation_fail(self):
        """Test failed validation."""
        rule = MockRule("test_rule", "content", is_valid=False)
        slide = SlideContent(title="Test", content="Content")
        
        result = rule.validate(slide)
        
        assert result.is_valid is False
        assert result.errors == ["Validation failed for test_rule"]
        assert result.suggestions == ["Fix the issue"]
    
    def test_rule_with_warnings(self):
        """Test rule that produces warnings."""
        rule = MockRule("warning_rule", "design", is_valid=True)
        slide = SlideContent(title="Test", content="Content")
        
        result = rule.validate(slide)
        
        assert result.is_valid is True
        assert result.warnings == ["Minor issue"]
        assert result.errors is None


class TestRulesEngine:
    """Test suite for rules engine."""
    
    @pytest.fixture
    def engine(self):
        """Create a rules engine instance."""
        return MockRulesEngine()
    
    @pytest.fixture
    def sample_slide(self):
        """Create sample slide."""
        return SlideContent(
            title="Sample Slide",
            content="This is sample content",
            bullet_points=["Point 1", "Point 2"],
            layout_type="content"
        )
    
    @pytest.fixture
    def sample_presentation(self):
        """Create sample presentation."""
        return PresentationContent(
            title="Sample Presentation",
            slides=[
                SlideContent(title="Slide 1", content="Content 1"),
                SlideContent(title="Slide 2", content="Content 2"),
                SlideContent(title="Slide 3", content="Content 3")
            ]
        )
    
    def test_add_rule(self, engine):
        """Test adding rules to engine."""
        rule1 = MockRule("rule1", "content")
        rule2 = MockRule("rule2", "design")
        
        engine.add_rule(rule1)
        engine.add_rule(rule2)
        
        assert len(engine.rules) == 2
        assert rule1 in engine.rules
        assert rule2 in engine.rules
    
    def test_get_rules_by_category(self, engine):
        """Test filtering rules by category."""
        content_rule1 = MockRule("content1", "content")
        content_rule2 = MockRule("content2", "content")
        design_rule = MockRule("design1", "design")
        
        engine.add_rule(content_rule1)
        engine.add_rule(content_rule2)
        engine.add_rule(design_rule)
        
        content_rules = engine.get_rules_by_category("content")
        design_rules = engine.get_rules_by_category("design")
        
        assert len(content_rules) == 2
        assert len(design_rules) == 1
        assert content_rule1 in content_rules
        assert content_rule2 in content_rules
        assert design_rule in design_rules
    
    def test_validate_slide_all_pass(self, engine, sample_slide):
        """Test slide validation when all rules pass."""
        engine.add_rule(MockRule("rule1", "content", is_valid=True))
        engine.add_rule(MockRule("rule2", "design", is_valid=True))
        
        result = engine.validate_slide(sample_slide)
        
        assert result.is_valid is True
        assert result.errors is None
        assert engine.validate_slide_calls == 1
    
    def test_validate_slide_with_failures(self, engine, sample_slide):
        """Test slide validation with failing rules."""
        engine.add_rule(MockRule("rule1", "content", is_valid=True))
        engine.add_rule(MockRule("rule2", "design", is_valid=False))
        engine.add_rule(MockRule("rule3", "accessibility", is_valid=False))
        
        result = engine.validate_slide(sample_slide)
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "Validation failed for rule2" in result.errors
        assert "Validation failed for rule3" in result.errors
        assert len(result.suggestions) == 2
    
    def test_validate_slide_with_warnings(self, engine, sample_slide):
        """Test slide validation with warnings."""
        engine.add_rule(MockRule("rule1", "content", is_valid=True))
        engine.add_rule(MockRule("warning_rule", "design", is_valid=True))
        
        result = engine.validate_slide(sample_slide)
        
        assert result.is_valid is True
        assert result.errors is None
        assert result.warnings == ["Minor issue"]
    
    def test_validate_presentation(self, engine, sample_presentation):
        """Test presentation validation."""
        engine.add_rule(MockRule("rule1", "content", is_valid=True))
        engine.add_rule(MockRule("rule2", "design", is_valid=True))
        
        result = engine.validate_presentation(sample_presentation)
        
        assert result.is_valid is True
        assert engine.validate_presentation_calls == 1
        # Each slide should be validated
        assert engine.validate_slide_calls == len(sample_presentation.slides)
    
    def test_validate_presentation_with_failures(self, engine, sample_presentation):
        """Test presentation validation with failures."""
        engine.add_rule(MockRule("rule1", "content", is_valid=False))
        
        result = engine.validate_presentation(sample_presentation)
        
        assert result.is_valid is False
        # Should have one error per slide
        assert len(result.errors) == len(sample_presentation.slides)


class TestSpecificRules:
    """Test specific rule implementations."""
    
    def test_text_length_rule(self):
        """Test rule for checking text length."""
        class TextLengthRule(IRule):
            @property
            def name(self) -> str:
                return "text_length"
            
            @property
            def category(self) -> str:
                return "content"
            
            def validate(self, content: SlideContent) -> ValidationResult:
                max_length = 150
                if content.content and len(content.content) > max_length:
                    return ValidationResult(
                        is_valid=False,
                        errors=[f"Text exceeds {max_length} characters"],
                        suggestions=["Reduce text or split into multiple slides"]
                    )
                return ValidationResult(is_valid=True)
        
        rule = TextLengthRule()
        
        # Test with short text
        short_slide = SlideContent(content="Short text")
        assert rule.validate(short_slide).is_valid is True
        
        # Test with long text
        long_slide = SlideContent(content="x" * 200)
        result = rule.validate(long_slide)
        assert result.is_valid is False
        assert "Text exceeds 150 characters" in result.errors[0]
    
    def test_bullet_points_rule(self):
        """Test rule for bullet points."""
        class BulletPointsRule(IRule):
            @property
            def name(self) -> str:
                return "bullet_points"
            
            @property
            def category(self) -> str:
                return "design"
            
            def validate(self, content: SlideContent) -> ValidationResult:
                max_bullets = 6
                if content.bullet_points and len(content.bullet_points) > max_bullets:
                    return ValidationResult(
                        is_valid=False,
                        errors=[f"Too many bullet points ({len(content.bullet_points)} > {max_bullets})"],
                        suggestions=["Reduce to 6 or fewer bullet points"]
                    )
                return ValidationResult(is_valid=True)
        
        rule = BulletPointsRule()
        
        # Test with acceptable bullets
        good_slide = SlideContent(bullet_points=["1", "2", "3", "4"])
        assert rule.validate(good_slide).is_valid is True
        
        # Test with too many bullets
        bad_slide = SlideContent(bullet_points=["1", "2", "3", "4", "5", "6", "7", "8"])
        result = rule.validate(bad_slide)
        assert result.is_valid is False
        assert "Too many bullet points" in result.errors[0]
    
    def test_accessibility_rule(self):
        """Test accessibility rule."""
        class AccessibilityRule(IRule):
            @property
            def name(self) -> str:
                return "image_alt_text"
            
            @property
            def category(self) -> str:
                return "accessibility"
            
            def validate(self, content: SlideContent) -> ValidationResult:
                warnings = []
                
                if content.visual_elements:
                    for element in content.visual_elements:
                        if element.get("type") == "image" and not element.get("alt_text"):
                            warnings.append(f"Image missing alt text: {element.get('src', 'unknown')}")
                
                return ValidationResult(
                    is_valid=True,  # Warnings don't fail validation
                    warnings=warnings if warnings else None
                )
        
        rule = AccessibilityRule()
        
        # Test slide with proper alt text
        good_slide = SlideContent(
            visual_elements=[
                {"type": "image", "src": "img1.jpg", "alt_text": "Description"}
            ]
        )
        assert rule.validate(good_slide).warnings is None
        
        # Test slide without alt text
        bad_slide = SlideContent(
            visual_elements=[
                {"type": "image", "src": "img1.jpg"},
                {"type": "image", "src": "img2.jpg", "alt_text": ""}
            ]
        )
        result = rule.validate(bad_slide)
        assert len(result.warnings) == 1
        assert "missing alt text" in result.warnings[0]


class TestRulesEngineIntegration:
    """Integration tests for rules engine."""
    
    def test_complex_validation_scenario(self):
        """Test complex validation with multiple rule types."""
        engine = MockRulesEngine()
        
        # Add various rules
        engine.add_rule(MockRule("content_check", "content", is_valid=True))
        engine.add_rule(MockRule("design_check", "design", is_valid=False))
        engine.add_rule(MockRule("accessibility_check", "accessibility", is_valid=True))
        engine.add_rule(MockRule("warning_rule", "content", is_valid=True))
        
        presentation = PresentationContent(
            title="Complex Presentation",
            slides=[
                SlideContent(title="Intro", content="Introduction"),
                SlideContent(title="Main", content="Main content"),
                SlideContent(title="End", content="Conclusion")
            ]
        )
        
        result = engine.validate_presentation(presentation)
        
        assert result.is_valid is False
        assert len(result.errors) == 3  # One design error per slide
        assert len(result.warnings) == 3  # One warning per slide
        
    def test_rule_categories(self):
        """Test working with different rule categories."""
        engine = MockRulesEngine()
        
        # Add rules in different categories
        categories = ["content", "design", "accessibility", "citation"]
        for i, category in enumerate(categories):
            for j in range(3):
                engine.add_rule(MockRule(f"{category}_rule_{j}", category))
        
        # Verify categorization
        for category in categories:
            rules = engine.get_rules_by_category(category)
            assert len(rules) == 3
            assert all(rule.category == category for rule in rules)