"""
Text constraint rules for slide content validation.
"""
import re
from typing import Any, Dict, List, Optional

from app.services.slides.rules.base import (
    Rule,
    RuleCategory,
    RuleContext,
    RuleSeverity,
    RuleViolation,
    get_rule_engine
)


class BulletPointCountRule(Rule):
    """Ensures slides don't exceed maximum bullet points."""
    
    def __init__(self, max_bullets: int = 5):
        super().__init__(
            rule_id="text.bullet_count",
            name="Bullet Point Count Limit",
            description=f"Slides should have no more than {max_bullets} bullet points",
            category=RuleCategory.TEXT,
            severity=RuleSeverity.WARNING,
            config={"max_bullets": max_bullets}
        )
        self.max_bullets = max_bullets
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            # Count bullet points in slide content
            bullet_count = 0
            slide_content = content.get("content", {})
            
            for element in slide_content.get("body", []):
                if element.get("type") == "bullet_list":
                    bullet_count += len(element.get("items", []))
            
            if bullet_count > self.max_bullets:
                violations.append(self.create_violation(
                    message=f"Slide has {bullet_count} bullet points, exceeding the limit of {self.max_bullets}",
                    suggestion=f"Consider splitting content across multiple slides or consolidating points",
                    context={"bullet_count": bullet_count, "limit": self.max_bullets},
                    location={"slide_number": content.get("slide_number")}
                ))
        
        return violations


class BulletPointLengthRule(Rule):
    """Ensures bullet points don't exceed word count."""
    
    def __init__(self, max_words: int = 10):
        super().__init__(
            rule_id="text.bullet_length",
            name="Bullet Point Word Limit",
            description=f"Bullet points should have no more than {max_words} words",
            category=RuleCategory.TEXT,
            severity=RuleSeverity.WARNING,
            config={"max_words": max_words}
        )
        self.max_words = max_words
    
    def _count_words(self, text: str) -> int:
        """Count words in text, excluding citations."""
        # Remove citations in parentheses or brackets
        text = re.sub(r'\([^)]*\d{4}[^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\d{4}[^\]]*\]', '', text)
        # Count words
        return len(text.split())
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            slide_num = content.get("slide_number")
            
            for idx, element in enumerate(slide_content.get("body", [])):
                if element.get("type") == "bullet_list":
                    for bullet_idx, item in enumerate(element.get("items", [])):
                        word_count = self._count_words(item.get("text", ""))
                        if word_count > self.max_words:
                            violations.append(self.create_violation(
                                message=f"Bullet point has {word_count} words, exceeding limit of {self.max_words}",
                                suggestion="Shorten the bullet point to be more concise",
                                context={"word_count": word_count, "text": item.get("text", "")},
                                location={
                                    "slide_number": slide_num,
                                    "element_index": idx,
                                    "bullet_index": bullet_idx
                                }
                            ))
        
        return violations


class TitleLengthRule(Rule):
    """Ensures slide titles are concise."""
    
    def __init__(self, max_chars: int = 60):
        super().__init__(
            rule_id="text.title_length",
            name="Title Length Limit",
            description=f"Slide titles should be no more than {max_chars} characters",
            category=RuleCategory.TEXT,
            severity=RuleSeverity.WARNING,
            config={"max_chars": max_chars}
        )
        self.max_chars = max_chars
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict):
            title = content.get("content", {}).get("title", "")
            if len(title) > self.max_chars:
                violations.append(self.create_violation(
                    message=f"Title has {len(title)} characters, exceeding limit of {self.max_chars}",
                    suggestion="Use a shorter, more focused title",
                    context={"length": len(title), "title": title},
                    location={"slide_number": content.get("slide_number")}
                ))
        
        return violations


class TextDensityRule(Rule):
    """Ensures slides don't have too much text."""
    
    def __init__(self, max_words_per_slide: int = 100):
        super().__init__(
            rule_id="text.density",
            name="Text Density Limit",
            description=f"Slides should have no more than {max_words_per_slide} words total",
            category=RuleCategory.TEXT,
            severity=RuleSeverity.WARNING,
            config={"max_words_per_slide": max_words_per_slide}
        )
        self.max_words = max_words_per_slide
    
    def _count_all_words(self, content: Dict[str, Any]) -> int:
        """Count all words in slide content."""
        word_count = 0
        
        # Title and subtitle
        word_count += len(content.get("title", "").split())
        word_count += len(content.get("subtitle", "").split())
        
        # Body elements
        for element in content.get("body", []):
            if element.get("type") == "text":
                word_count += len(element.get("content", "").split())
            elif element.get("type") == "bullet_list":
                for item in element.get("items", []):
                    word_count += len(item.get("text", "").split())
            elif element.get("type") in ["table", "chart"]:
                # Count caption words
                caption = element.get("caption", "")
                word_count += len(caption.split())
        
        return word_count
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            word_count = self._count_all_words(slide_content)
            
            if word_count > self.max_words:
                violations.append(self.create_violation(
                    message=f"Slide has {word_count} words, exceeding limit of {self.max_words}",
                    suggestion="Reduce text content or split across multiple slides",
                    context={"word_count": word_count},
                    location={"slide_number": content.get("slide_number")}
                ))
        
        return violations


class ReadabilityScoreRule(Rule):
    """Ensures text maintains appropriate readability level."""
    
    def __init__(self, target_level: str = "college", max_score: float = 16.0):
        super().__init__(
            rule_id="text.readability",
            name="Readability Score Check",
            description=f"Text should maintain {target_level} readability level",
            category=RuleCategory.TEXT,
            severity=RuleSeverity.INFO,
            config={"target_level": target_level, "max_score": max_score}
        )
        self.target_level = target_level
        self.max_score = max_score
    
    def _calculate_flesch_kincaid(self, text: str) -> float:
        """Calculate Flesch-Kincaid Grade Level score."""
        # Simple implementation - in production, use textstat library
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        words = text.split()
        syllables = sum(self._count_syllables(word) for word in words)
        
        if len(words) == 0:
            return 0.0
        
        # Flesch-Kincaid Grade Level formula
        score = 0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59
        return max(0.0, score)
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified)."""
        word = word.lower()
        vowels = "aeiouy"
        syllables = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllables += 1
            previous_was_vowel = is_vowel
        
        # Adjust for silent e
        if word.endswith('e'):
            syllables -= 1
        
        # Ensure at least one syllable
        return max(1, syllables)
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            
            # Collect all text
            all_text = []
            for element in slide_content.get("body", []):
                if element.get("type") == "text":
                    all_text.append(element.get("content", ""))
                elif element.get("type") == "bullet_list":
                    for item in element.get("items", []):
                        all_text.append(item.get("text", ""))
            
            if all_text:
                combined_text = " ".join(all_text)
                score = self._calculate_flesch_kincaid(combined_text)
                
                if score > self.max_score:
                    violations.append(self.create_violation(
                        message=f"Text complexity score {score:.1f} may be too high for {self.target_level} level",
                        suggestion="Simplify sentence structure and use shorter words",
                        context={"readability_score": score, "target_level": self.target_level},
                        location={"slide_number": content.get("slide_number")},
                        severity=RuleSeverity.INFO
                    ))
        
        return violations


class ConsistentTerminologyRule(Rule):
    """Ensures consistent use of terminology across slides."""
    
    def __init__(self):
        super().__init__(
            rule_id="text.terminology",
            name="Consistent Terminology",
            description="Ensures consistent use of terms across presentation",
            category=RuleCategory.TEXT,
            severity=RuleSeverity.INFO
        )
        self.term_variations = {}
        self.first_occurrences = {}
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        # This rule needs to track state across slides
        # In practice, this would be handled by the presentation validator
        # For now, we'll check individual slides for common inconsistencies
        
        common_variations = [
            ("e-mail", "email"),
            ("web site", "website"),
            ("data base", "database"),
            ("on-line", "online"),
            ("co-ordinate", "coordinate")
        ]
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            text_content = self._extract_all_text(slide_content)
            
            for variant1, variant2 in common_variations:
                if variant1 in text_content and variant2 in text_content:
                    violations.append(self.create_violation(
                        message=f"Inconsistent terminology: both '{variant1}' and '{variant2}' used",
                        suggestion=f"Choose one form and use it consistently",
                        context={"terms": [variant1, variant2]},
                        location={"slide_number": content.get("slide_number")},
                        severity=RuleSeverity.INFO
                    ))
        
        return violations
    
    def _extract_all_text(self, content: Dict[str, Any]) -> str:
        """Extract all text from slide content."""
        texts = []
        
        texts.append(content.get("title", ""))
        texts.append(content.get("subtitle", ""))
        
        for element in content.get("body", []):
            if element.get("type") == "text":
                texts.append(element.get("content", ""))
            elif element.get("type") == "bullet_list":
                for item in element.get("items", []):
                    texts.append(item.get("text", ""))
        
        return " ".join(texts).lower()


def register_text_rules(engine=None):
    """Register all text rules with the rule engine."""
    if engine is None:
        engine = get_rule_engine()
    
    # Register rules with appropriate rule sets
    rules = [
        (BulletPointCountRule(), ["conference", "lecture", "defense", "seminar", "workshop"]),
        (BulletPointLengthRule(), ["conference", "lecture", "defense", "seminar", "workshop"]),
        (TitleLengthRule(), ["conference", "lecture", "defense", "seminar", "workshop"]),
        (TextDensityRule(), ["conference", "defense"]),
        (ReadabilityScoreRule(), ["lecture", "workshop"]),
        (ConsistentTerminologyRule(), ["defense", "conference"])
    ]
    
    for rule, rule_sets in rules:
        engine.register_rule(rule, rule_sets)