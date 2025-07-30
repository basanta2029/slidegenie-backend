"""
Academic tone and citation rules for ensuring scholarly quality.
"""
import re
from typing import Any, Dict, List, Set

from app.services.slides.rules.base import (
    Rule,
    RuleCategory,
    RuleContext,
    RuleSeverity,
    RuleViolation,
    get_rule_engine
)


class AcademicToneRule(Rule):
    """Ensures content maintains academic tone and avoids informal language."""
    
    def __init__(self):
        super().__init__(
            rule_id="academic.tone",
            name="Academic Tone Enforcement",
            description="Ensures content maintains formal academic tone",
            category=RuleCategory.ACADEMIC,
            severity=RuleSeverity.WARNING
        )
        
        # Common informal phrases to avoid
        self.informal_phrases = {
            "a lot of": "many/numerous",
            "lots of": "many/numerous",
            "kind of": "somewhat/rather",
            "sort of": "somewhat/rather",
            "pretty much": "essentially/largely",
            "really": "very/significantly",
            "stuff": "material/content",
            "things": "elements/factors",
            "gonna": "going to",
            "wanna": "want to",
            "can't": "cannot",
            "won't": "will not",
            "don't": "do not",
            "isn't": "is not",
            "aren't": "are not",
            "wasn't": "was not",
            "weren't": "were not",
            "hasn't": "has not",
            "haven't": "have not",
            "shouldn't": "should not",
            "wouldn't": "would not",
            "couldn't": "could not",
            "didn't": "did not",
            "doesn't": "does not",
            "let's": "let us",
            "that's": "that is",
            "what's": "what is",
            "here's": "here is",
            "there's": "there is",
            "where's": "where is",
            "how's": "how is",
            "who's": "who is",
            "it's": "it is",
            "you're": "you are",
            "they're": "they are",
            "we're": "we are",
            "I'm": "I am",
            "awesome": "excellent/remarkable",
            "cool": "interesting/notable",
            "guys": "individuals/colleagues",
            "etc.": "and so forth",
            "e.g.": "for example",
            "i.e.": "that is",
            "basically": "fundamentally/essentially",
            "obviously": "evidently/clearly",
            "actually": "in fact",
            "anyway": "nevertheless",
            "anyways": "nevertheless",
            "plus": "additionally/moreover",
            "tons of": "numerous/many",
            "huge": "substantial/significant",
            "tiny": "minimal/small",
            "big": "large/significant",
            "good": "effective/beneficial",
            "bad": "ineffective/detrimental",
            "nice": "satisfactory/pleasant",
            "okay": "acceptable/adequate",
            "ok": "acceptable/adequate"
        }
        
        # First-person pronouns to check
        self.first_person_pronouns = {"i", "me", "my", "mine", "we", "us", "our", "ours"}
        
        # Vague quantifiers
        self.vague_quantifiers = {
            "some", "many", "few", "several", "various", "numerous",
            "a number of", "a variety of", "a range of"
        }
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            slide_num = content.get("slide_number")
            
            # Check all text elements
            texts_to_check = []
            
            # Title and subtitle
            if "title" in slide_content:
                texts_to_check.append(("title", slide_content["title"]))
            if "subtitle" in slide_content:
                texts_to_check.append(("subtitle", slide_content["subtitle"]))
            
            # Body elements
            for idx, element in enumerate(slide_content.get("body", [])):
                if element.get("type") == "text":
                    texts_to_check.append((f"text_{idx}", element.get("content", "")))
                elif element.get("type") == "bullet_list":
                    for bullet_idx, item in enumerate(element.get("items", [])):
                        texts_to_check.append(
                            (f"bullet_{idx}_{bullet_idx}", item.get("text", ""))
                        )
            
            # Check each text
            for location, text in texts_to_check:
                text_lower = text.lower()
                
                # Check for informal phrases
                for informal, formal in self.informal_phrases.items():
                    if informal in text_lower:
                        violations.append(self.create_violation(
                            message=f"Informal phrase '{informal}' detected",
                            suggestion=f"Consider using '{formal}' instead",
                            context={"phrase": informal, "suggestion": formal, "text": text},
                            location={"slide_number": slide_num, "element": location}
                        ))
                
                # Check for first-person pronouns (warning for certain presentation types)
                if context.presentation_type in ["conference", "defense"]:
                    words = set(text_lower.split())
                    used_pronouns = words.intersection(self.first_person_pronouns)
                    if used_pronouns:
                        violations.append(self.create_violation(
                            message=f"First-person pronoun(s) detected: {', '.join(used_pronouns)}",
                            suggestion="Consider using passive voice or third-person perspective",
                            context={"pronouns": list(used_pronouns)},
                            location={"slide_number": slide_num, "element": location},
                            severity=RuleSeverity.INFO
                        ))
        
        return violations


class CitationPresenceRule(Rule):
    """Ensures slides with claims have proper citations."""
    
    def __init__(self):
        super().__init__(
            rule_id="academic.citation_presence",
            name="Citation Requirement",
            description="Ensures claims and data have proper citations",
            category=RuleCategory.ACADEMIC,
            severity=RuleSeverity.WARNING
        )
        
        # Patterns that typically require citations
        self.citation_triggers = [
            r"studies (show|indicate|suggest|demonstrate)",
            r"research (shows|indicates|suggests|demonstrates)",
            r"according to",
            r"data (shows|indicates|suggests|demonstrates)",
            r"evidence (shows|indicates|suggests|demonstrates)",
            r"findings (show|indicate|suggest|demonstrate)",
            r"results (show|indicate|suggest|demonstrate)",
            r"analysis (shows|indicates|reveals)",
            r"\d+\s*%",  # Percentages
            r"statistics",
            r"survey",
            r"study",
            r"report",
            r"published",
            r"discovered",
            r"found that",
            r"proven",
            r"demonstrated"
        ]
        
        # Common citation patterns
        self.citation_patterns = [
            r'\([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][a-zA-Z]+)*,?\s+\d{4}\)',  # (Author, 2024)
            r'\[[A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][a-zA-Z]+)*,?\s+\d{4}\]',  # [Author, 2024]
            r'\[\d+\]',  # [1]
            r'\(\d+\)',  # (1)
            r'<sup>\d+</sup>',  # Superscript numbers
            r'\^\d+',  # ^1
        ]
    
    def _needs_citation(self, text: str) -> bool:
        """Check if text contains claims that need citations."""
        text_lower = text.lower()
        for pattern in self.citation_triggers:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def _has_citation(self, text: str) -> bool:
        """Check if text contains a citation."""
        for pattern in self.citation_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        # Skip citation checks for certain presentation types
        if context.presentation_type in ["lecture", "workshop"]:
            return violations
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            slide_num = content.get("slide_number")
            
            # Check body elements
            for idx, element in enumerate(slide_content.get("body", [])):
                if element.get("type") == "text":
                    text = element.get("content", "")
                    if self._needs_citation(text) and not self._has_citation(text):
                        violations.append(self.create_violation(
                            message="Statement appears to need citation",
                            suggestion="Add appropriate citation for the claim or data presented",
                            context={"text": text[:100] + "..." if len(text) > 100 else text},
                            location={"slide_number": slide_num, "element_index": idx}
                        ))
                
                elif element.get("type") == "bullet_list":
                    for bullet_idx, item in enumerate(element.get("items", [])):
                        text = item.get("text", "")
                        if self._needs_citation(text) and not self._has_citation(text):
                            violations.append(self.create_violation(
                                message="Bullet point appears to need citation",
                                suggestion="Add citation for the claim or data",
                                context={"text": text},
                                location={
                                    "slide_number": slide_num,
                                    "element_index": idx,
                                    "bullet_index": bullet_idx
                                }
                            ))
        
        return violations


class CitationFormatRule(Rule):
    """Validates citation format consistency."""
    
    def __init__(self, preferred_style: str = "APA"):
        super().__init__(
            rule_id="academic.citation_format",
            name="Citation Format Validation",
            description=f"Ensures citations follow {preferred_style} format",
            category=RuleCategory.ACADEMIC,
            severity=RuleSeverity.INFO,
            config={"style": preferred_style}
        )
        self.preferred_style = preferred_style
        
        # Define patterns for different citation styles
        self.style_patterns = {
            "APA": r'\([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|&)\s+[A-Z][a-zA-Z]+)*,\s+\d{4}\)',
            "MLA": r'\([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|and)\s+[A-Z][a-zA-Z]+)*\s+\d+\)',
            "Chicago": r'\([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|and)\s+[A-Z][a-zA-Z]+)*\s+\d{4},\s+\d+\)',
            "IEEE": r'\[\d+\]',
            "Vancouver": r'\(\d+\)'
        }
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            all_text = self._extract_all_text(slide_content)
            
            # Find all citations
            found_styles = {}
            for style, pattern in self.style_patterns.items():
                matches = re.findall(pattern, all_text)
                if matches:
                    found_styles[style] = len(matches)
            
            # Check for mixed citation styles
            if len(found_styles) > 1:
                styles_used = list(found_styles.keys())
                violations.append(self.create_violation(
                    message=f"Mixed citation styles detected: {', '.join(styles_used)}",
                    suggestion=f"Use consistent {self.preferred_style} citation format throughout",
                    context={"styles_found": found_styles},
                    location={"slide_number": content.get("slide_number")}
                ))
            
            # Check if non-preferred style is used
            elif found_styles and self.preferred_style not in found_styles:
                used_style = list(found_styles.keys())[0]
                violations.append(self.create_violation(
                    message=f"Using {used_style} style instead of preferred {self.preferred_style}",
                    suggestion=f"Convert citations to {self.preferred_style} format",
                    context={"current_style": used_style},
                    location={"slide_number": content.get("slide_number")},
                    severity=RuleSeverity.INFO
                ))
        
        return violations
    
    def _extract_all_text(self, content: Dict[str, Any]) -> str:
        """Extract all text from slide content."""
        texts = []
        
        for element in content.get("body", []):
            if element.get("type") == "text":
                texts.append(element.get("content", ""))
            elif element.get("type") == "bullet_list":
                for item in element.get("items", []):
                    texts.append(item.get("text", ""))
        
        return " ".join(texts)


class AcademicVocabularyRule(Rule):
    """Ensures appropriate academic vocabulary level."""
    
    def __init__(self):
        super().__init__(
            rule_id="academic.vocabulary",
            name="Academic Vocabulary Check",
            description="Ensures appropriate academic vocabulary usage",
            category=RuleCategory.ACADEMIC,
            severity=RuleSeverity.INFO
        )
        
        # Academic transition words and phrases
        self.academic_transitions = {
            "furthermore", "moreover", "consequently", "therefore", "thus",
            "hence", "accordingly", "nevertheless", "nonetheless", "however",
            "conversely", "alternatively", "similarly", "likewise", "specifically",
            "particularly", "notably", "significantly", "importantly", "additionally"
        }
        
        # Words to encourage for precision
        self.precision_terms = {
            "approximately", "precisely", "specifically", "particularly",
            "predominantly", "primarily", "substantially", "marginally",
            "demonstrably", "empirically", "theoretically", "conceptually"
        }
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        # Only check for higher academic levels
        if context.academic_level not in ["graduate", "research", "professional"]:
            return violations
        
        if isinstance(content, dict) and "content" in content:
            slide_content = content.get("content", {})
            all_text = self._extract_all_text(slide_content).lower()
            words = set(all_text.split())
            
            # Check for academic transition usage
            transitions_used = words.intersection(self.academic_transitions)
            if not transitions_used and len(all_text.split()) > 50:
                violations.append(self.create_violation(
                    message="Consider using academic transition words for better flow",
                    suggestion=f"Add transitions like: {', '.join(list(self.academic_transitions)[:5])}",
                    location={"slide_number": content.get("slide_number")},
                    severity=RuleSeverity.INFO
                ))
            
            # Check for vague language that could be more precise
            vague_words = ["very", "really", "quite", "rather", "somewhat"]
            vague_found = [w for w in vague_words if w in words]
            if vague_found:
                violations.append(self.create_violation(
                    message=f"Vague intensifiers found: {', '.join(vague_found)}",
                    suggestion="Use more precise academic language",
                    context={"vague_words": vague_found},
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
        
        return " ".join(texts)


class ReferencesSlideRule(Rule):
    """Ensures presentations have proper references slide."""
    
    def __init__(self):
        super().__init__(
            rule_id="academic.references_slide",
            name="References Slide Requirement",
            description="Ensures academic presentations have references",
            category=RuleCategory.ACADEMIC,
            severity=RuleSeverity.ERROR
        )
    
    def validate(self, content: Any, context: RuleContext) -> List[RuleViolation]:
        violations = []
        
        # This rule works at presentation level
        if isinstance(content, dict) and "slides" in content:
            # Check if this is a type that requires references
            if context.presentation_type in ["conference", "defense", "research"]:
                has_references = False
                
                for slide in content.get("slides", []):
                    title = slide.get("content", {}).get("title", "").lower()
                    if any(ref_word in title for ref_word in ["reference", "bibliography", "works cited", "citation"]):
                        has_references = True
                        break
                
                if not has_references:
                    violations.append(self.create_violation(
                        message="Academic presentation missing references slide",
                        suggestion="Add a References or Bibliography slide at the end",
                        severity=RuleSeverity.ERROR
                    ))
        
        return violations


def register_academic_rules(engine=None):
    """Register all academic rules with the rule engine."""
    if engine is None:
        engine = get_rule_engine()
    
    # Register rules with appropriate rule sets
    rules = [
        (AcademicToneRule(), ["conference", "defense", "research"]),
        (CitationPresenceRule(), ["conference", "defense", "research"]),
        (CitationFormatRule(), ["conference", "defense", "research"]),
        (AcademicVocabularyRule(), ["graduate", "research", "professional"]),
        (ReferencesSlideRule(), ["conference", "defense", "research"])
    ]
    
    for rule, rule_sets in rules:
        engine.register_rule(rule, rule_sets)