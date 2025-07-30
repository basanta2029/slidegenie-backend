"""
Base rule class and engine for content validation.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union


class RuleSeverity(Enum):
    """Severity levels for rule violations."""
    ERROR = "error"      # Blocks presentation generation
    WARNING = "warning"  # Shows warning but allows continuation
    INFO = "info"        # Informational message only


class RuleCategory(Enum):
    """Categories for organizing rules."""
    TEXT = "text"
    ACADEMIC = "academic"
    VISUAL = "visual"
    TIMING = "timing"
    STRUCTURE = "structure"
    ACCESSIBILITY = "accessibility"


@dataclass
class RuleViolation:
    """Represents a rule violation with details."""
    rule_id: str
    severity: RuleSeverity
    message: str
    suggestion: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None  # slide_number, element_index, etc.


@dataclass
class RuleContext:
    """Context information passed to rules for validation."""
    presentation_type: str  # conference, lecture, defense, etc.
    academic_level: str    # undergraduate, graduate, research, professional
    duration_minutes: int
    slide_count: int
    current_slide: Optional[Dict[str, Any]] = None
    current_element: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Rule(ABC):
    """Base class for all content rules."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        category: RuleCategory,
        severity: RuleSeverity = RuleSeverity.WARNING,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.category = category
        self.severity = severity
        self.enabled = enabled
        self.config = config or {}
    
    @abstractmethod
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        """
        Validate content against this rule.
        
        Args:
            content: The content to validate (could be text, slide, presentation, etc.)
            context: Context information for validation
            
        Returns:
            List of violations found (empty if valid)
        """
        pass
    
    def is_applicable(self, context: RuleContext) -> bool:
        """
        Check if this rule applies to the given context.
        Override to add custom applicability logic.
        """
        return self.enabled
    
    def create_violation(
        self,
        message: str,
        suggestion: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        location: Optional[Dict[str, Any]] = None,
        severity: Optional[RuleSeverity] = None
    ) -> RuleViolation:
        """Helper to create a violation with this rule's defaults."""
        return RuleViolation(
            rule_id=self.rule_id,
            severity=severity or self.severity,
            message=message,
            suggestion=suggestion,
            context=context,
            location=location
        )


class CompositeRule(Rule):
    """Rule that combines multiple sub-rules."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        category: RuleCategory,
        sub_rules: List[Rule],
        require_all: bool = True,
        **kwargs
    ):
        super().__init__(rule_id, name, description, category, **kwargs)
        self.sub_rules = sub_rules
        self.require_all = require_all
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        """Validate using all sub-rules."""
        violations = []
        for rule in self.sub_rules:
            if rule.is_applicable(context):
                violations.extend(rule.validate(content, context))
        return violations


class RuleEngine:
    """Engine for managing and executing content rules."""
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.rule_sets: Dict[str, Set[str]] = {}
        self._initialize_default_rule_sets()
    
    def _initialize_default_rule_sets(self):
        """Initialize default rule sets for different contexts."""
        self.rule_sets = {
            "conference": set(),
            "lecture": set(),
            "defense": set(),
            "seminar": set(),
            "workshop": set(),
            "default": set()
        }
    
    def register_rule(self, rule: Rule, rule_sets: Optional[List[str]] = None):
        """Register a rule with the engine."""
        self.rules[rule.rule_id] = rule
        
        # Add to specified rule sets or default
        if rule_sets:
            for rule_set in rule_sets:
                if rule_set in self.rule_sets:
                    self.rule_sets[rule_set].add(rule.rule_id)
        else:
            self.rule_sets["default"].add(rule.rule_id)
    
    def unregister_rule(self, rule_id: str):
        """Remove a rule from the engine."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            # Remove from all rule sets
            for rule_set in self.rule_sets.values():
                rule_set.discard(rule_id)
    
    def get_rules_for_context(self, context: RuleContext) -> List[Rule]:
        """Get applicable rules for the given context."""
        # Get rules from appropriate rule set
        rule_set_name = context.presentation_type.lower()
        if rule_set_name not in self.rule_sets:
            rule_set_name = "default"
        
        rule_ids = self.rule_sets[rule_set_name] | self.rule_sets["default"]
        
        # Filter by applicability
        applicable_rules = []
        for rule_id in rule_ids:
            rule = self.rules.get(rule_id)
            if rule and rule.is_applicable(context):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def validate_content(
        self,
        content: Any,
        context: RuleContext,
        categories: Optional[List[RuleCategory]] = None,
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Validate content against applicable rules.
        
        Args:
            content: Content to validate
            context: Validation context
            categories: Only validate rules in these categories (None = all)
            stop_on_error: Stop validation on first ERROR severity violation
            
        Returns:
            Dictionary with validation results
        """
        violations = []
        rules_checked = 0
        
        for rule in self.get_rules_for_context(context):
            # Filter by category if specified
            if categories and rule.category not in categories:
                continue
            
            rules_checked += 1
            rule_violations = rule.validate(content, context)
            violations.extend(rule_violations)
            
            # Stop if we hit an error and stop_on_error is True
            if stop_on_error and any(v.severity == RuleSeverity.ERROR for v in rule_violations):
                break
        
        # Organize results
        errors = [v for v in violations if v.severity == RuleSeverity.ERROR]
        warnings = [v for v in violations if v.severity == RuleSeverity.WARNING]
        info = [v for v in violations if v.severity == RuleSeverity.INFO]
        
        return {
            "valid": len(errors) == 0,
            "rules_checked": rules_checked,
            "violations": violations,
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "summary": {
                "total_violations": len(violations),
                "errors": len(errors),
                "warnings": len(warnings),
                "info": len(info)
            }
        }
    
    def validate_presentation(
        self,
        presentation: Dict[str, Any],
        context: RuleContext
    ) -> Dict[str, Any]:
        """Validate an entire presentation."""
        results = {
            "presentation_valid": True,
            "slide_results": {},
            "presentation_violations": [],
            "total_violations": 0
        }
        
        # Validate presentation-level rules
        pres_result = self.validate_content(
            presentation,
            context,
            categories=[RuleCategory.STRUCTURE, RuleCategory.TIMING]
        )
        results["presentation_violations"] = pres_result["violations"]
        results["presentation_valid"] = pres_result["valid"]
        
        # Validate each slide
        for slide in presentation.get("slides", []):
            slide_num = slide.get("slide_number", 0)
            context.current_slide = slide
            
            slide_result = self.validate_content(slide, context)
            results["slide_results"][slide_num] = slide_result
            
            if not slide_result["valid"]:
                results["presentation_valid"] = False
            
            results["total_violations"] += slide_result["summary"]["total_violations"]
        
        return results
    
    def get_rule_documentation(self, category: Optional[RuleCategory] = None) -> List[Dict[str, Any]]:
        """Get documentation for all registered rules."""
        docs = []
        for rule in self.rules.values():
            if category is None or rule.category == category:
                docs.append({
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "description": rule.description,
                    "category": rule.category.value,
                    "severity": rule.severity.value,
                    "enabled": rule.enabled,
                    "config": rule.config
                })
        return sorted(docs, key=lambda x: (x["category"], x["rule_id"]))


# Singleton instance
_rule_engine = None


def get_rule_engine() -> RuleEngine:
    """Get the singleton rule engine instance."""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine