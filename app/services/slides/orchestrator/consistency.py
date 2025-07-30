"""Consistency manager for maintaining coherence across slides."""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyRule:
    """Defines a consistency rule for slides."""
    id: str
    name: str
    type: str  # style, content, format, reference
    scope: str  # global, section, slide_type
    check_function: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    severity: str = "warning"  # info, warning, error
    auto_fix: bool = False


@dataclass
class ConsistencyIssue:
    """Represents a consistency issue found."""
    rule_id: str
    slide_indices: List[int]
    issue_type: str
    message: str
    severity: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: Optional[str] = None


class ConsistencyManager:
    """Manages consistency across presentation slides."""
    
    def __init__(self):
        """Initialize the consistency manager."""
        self.rules: Dict[str, ConsistencyRule] = {}
        self.global_context: Dict[str, Any] = {}
        self.style_registry: Dict[str, Dict[str, Any]] = {}
        self.content_registry: Dict[str, Any] = defaultdict(dict)
        self._init_default_rules()
        
    def _init_default_rules(self):
        """Initialize default consistency rules."""
        default_rules = [
            ConsistencyRule(
                id="font_consistency",
                name="Font Consistency",
                type="style",
                scope="global",
                check_function="check_font_consistency",
                parameters={"allowed_variations": 3}
            ),
            ConsistencyRule(
                id="color_scheme",
                name="Color Scheme Consistency",
                type="style",
                scope="global",
                check_function="check_color_consistency",
                parameters={"max_colors": 5}
            ),
            ConsistencyRule(
                id="heading_hierarchy",
                name="Heading Hierarchy",
                type="content",
                scope="section",
                check_function="check_heading_hierarchy"
            ),
            ConsistencyRule(
                id="bullet_format",
                name="Bullet Point Format",
                type="format",
                scope="slide_type",
                check_function="check_bullet_format"
            ),
            ConsistencyRule(
                id="reference_validity",
                name="Reference Validity",
                type="reference",
                scope="global",
                check_function="check_references",
                severity="error"
            ),
            ConsistencyRule(
                id="terminology",
                name="Terminology Consistency",
                type="content",
                scope="global",
                check_function="check_terminology",
                auto_fix=True
            ),
            ConsistencyRule(
                id="spacing_consistency",
                name="Spacing Consistency",
                type="style",
                scope="slide_type",
                check_function="check_spacing"
            ),
            ConsistencyRule(
                id="image_quality",
                name="Image Quality Standards",
                type="content",
                scope="global",
                check_function="check_image_quality",
                parameters={"min_resolution": 300}
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
            
    def add_rule(self, rule: ConsistencyRule) -> None:
        """Add a consistency rule."""
        self.rules[rule.id] = rule
        logger.info(f"Added consistency rule: {rule.name}")
        
    async def apply_rules(
        self, 
        slide_data: Dict[str, Any], 
        context: Any
    ) -> Dict[str, Any]:
        """Apply consistency rules to a slide."""
        # Update registries
        self._update_registries(slide_data)
        
        # Apply auto-fix rules
        for rule in self.rules.values():
            if rule.auto_fix and rule.scope in ["global", "slide_type"]:
                slide_data = await self._apply_auto_fix(rule, slide_data, context)
                
        return slide_data
        
    async def validate_presentation(
        self,
        slides: Dict[int, Dict[str, Any]],
        custom_rules: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate consistency across all slides."""
        issues = []
        
        # Add custom rules if provided
        if custom_rules:
            for rule_data in custom_rules:
                rule = ConsistencyRule(**rule_data)
                self.add_rule(rule)
                
        # Run each consistency check
        for rule in self.rules.values():
            rule_issues = await self._check_rule(rule, slides)
            issues.extend(rule_issues)
            
        # Sort issues by severity
        severity_order = {"error": 0, "warning": 1, "info": 2}
        issues.sort(key=lambda x: severity_order.get(x.severity, 3))
        
        return {
            "issues": [self._issue_to_dict(issue) for issue in issues],
            "summary": {
                "total_issues": len(issues),
                "errors": sum(1 for i in issues if i.severity == "error"),
                "warnings": sum(1 for i in issues if i.severity == "warning"),
                "info": sum(1 for i in issues if i.severity == "info")
            },
            "is_valid": all(i.severity != "error" for i in issues)
        }
        
    def _update_registries(self, slide_data: Dict[str, Any]) -> None:
        """Update internal registries with slide data."""
        slide_index = slide_data.get("slide_index", -1)
        
        # Update style registry
        style = slide_data.get("style", {})
        if style:
            self.style_registry[str(slide_index)] = style
            
        # Update content registry
        content = slide_data.get("content", {})
        if content:
            self.content_registry["terms"][slide_index] = self._extract_terms(content)
            self.content_registry["headings"][slide_index] = self._extract_headings(content)
            
    async def _check_rule(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check a specific rule across slides."""
        check_method = getattr(self, rule.check_function, None)
        if not check_method:
            logger.warning(f"Check function {rule.check_function} not found")
            return []
            
        try:
            return await check_method(rule, slides)
        except Exception as e:
            logger.error(f"Error checking rule {rule.id}: {e}")
            return []
            
    async def check_font_consistency(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check font consistency across slides."""
        issues = []
        font_usage = defaultdict(list)
        
        for idx, slide in slides.items():
            style = slide.get("style", {})
            fonts = self._extract_fonts(style)
            
            for font in fonts:
                font_usage[font].append(idx)
                
        # Check if too many font variations
        allowed_variations = rule.parameters.get("allowed_variations", 3)
        if len(font_usage) > allowed_variations:
            issues.append(ConsistencyIssue(
                rule_id=rule.id,
                slide_indices=list(slides.keys()),
                issue_type="font_variation",
                message=f"Too many font variations: {len(font_usage)} (max allowed: {allowed_variations})",
                severity=rule.severity,
                details={"fonts": list(font_usage.keys())},
                suggested_fix="Standardize to primary font family"
            ))
            
        return issues
        
    async def check_color_consistency(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check color scheme consistency."""
        issues = []
        color_usage = defaultdict(list)
        
        for idx, slide in slides.items():
            style = slide.get("style", {})
            colors = self._extract_colors(style)
            
            for color in colors:
                color_usage[color].append(idx)
                
        # Check color count
        max_colors = rule.parameters.get("max_colors", 5)
        if len(color_usage) > max_colors:
            issues.append(ConsistencyIssue(
                rule_id=rule.id,
                slide_indices=list(slides.keys()),
                issue_type="color_overuse",
                message=f"Too many colors used: {len(color_usage)} (max allowed: {max_colors})",
                severity=rule.severity,
                details={"colors": list(color_usage.keys())[:10]},
                suggested_fix="Limit to brand color palette"
            ))
            
        return issues
        
    async def check_heading_hierarchy(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check heading hierarchy consistency."""
        issues = []
        
        # Group slides by section
        sections = self._group_slides_by_section(slides)
        
        for section_slides in sections.values():
            heading_levels = []
            
            for idx in section_slides:
                slide = slides[idx]
                headings = self._extract_headings(slide.get("content", {}))
                heading_levels.extend([(idx, h) for h in headings])
                
            # Check hierarchy
            hierarchy_issues = self._validate_heading_hierarchy(heading_levels)
            for issue in hierarchy_issues:
                issues.append(ConsistencyIssue(
                    rule_id=rule.id,
                    slide_indices=issue["slides"],
                    issue_type="heading_hierarchy",
                    message=issue["message"],
                    severity=rule.severity
                ))
                
        return issues
        
    async def check_bullet_format(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check bullet point formatting consistency."""
        issues = []
        bullet_styles = defaultdict(list)
        
        for idx, slide in slides.items():
            content = slide.get("content", {})
            bullets = self._extract_bullet_styles(content)
            
            for style in bullets:
                bullet_styles[style].append(idx)
                
        # Check for inconsistent styles within same slide type
        slide_types = self._group_slides_by_type(slides)
        
        for slide_type, type_slides in slide_types.items():
            type_bullet_styles = set()
            affected_slides = []
            
            for idx in type_slides:
                if idx in slides:
                    content = slides[idx].get("content", {})
                    styles = self._extract_bullet_styles(content)
                    if styles:
                        type_bullet_styles.update(styles)
                        affected_slides.append(idx)
                        
            if len(type_bullet_styles) > 1:
                issues.append(ConsistencyIssue(
                    rule_id=rule.id,
                    slide_indices=affected_slides,
                    issue_type="bullet_inconsistency",
                    message=f"Inconsistent bullet styles in {slide_type} slides",
                    severity=rule.severity,
                    details={"styles": list(type_bullet_styles)}
                ))
                
        return issues
        
    async def check_references(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check reference validity."""
        issues = []
        all_references = []
        available_slides = set(slides.keys())
        
        for idx, slide in slides.items():
            references = slide.get("references", [])
            for ref in references:
                ref_idx = ref.get("slide_index")
                if ref_idx is not None:
                    all_references.append((idx, ref_idx))
                    
                    if ref_idx not in available_slides:
                        issues.append(ConsistencyIssue(
                            rule_id=rule.id,
                            slide_indices=[idx],
                            issue_type="invalid_reference",
                            message=f"Slide {idx} references non-existent slide {ref_idx}",
                            severity=rule.severity
                        ))
                        
        return issues
        
    async def check_terminology(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check terminology consistency."""
        issues = []
        term_variations = defaultdict(lambda: defaultdict(list))
        
        # Build terminology map
        for idx, slide in slides.items():
            content = slide.get("content", {})
            terms = self._extract_terms(content)
            
            for term in terms:
                normalized = term.lower()
                term_variations[normalized][term].append(idx)
                
        # Find inconsistent terminology
        for base_term, variations in term_variations.items():
            if len(variations) > 1:
                # Find the most common variation
                most_common = max(variations.items(), key=lambda x: len(x[1]))
                
                affected_slides = []
                for variant, slide_list in variations.items():
                    if variant != most_common[0]:
                        affected_slides.extend(slide_list)
                        
                if affected_slides:
                    issues.append(ConsistencyIssue(
                        rule_id=rule.id,
                        slide_indices=affected_slides,
                        issue_type="terminology_variation",
                        message=f"Inconsistent terminology: {list(variations.keys())}",
                        severity=rule.severity,
                        details={
                            "variations": dict(variations),
                            "suggested": most_common[0]
                        },
                        suggested_fix=f"Use '{most_common[0]}' consistently"
                    ))
                    
        return issues
        
    async def check_spacing(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check spacing consistency."""
        issues = []
        spacing_patterns = defaultdict(list)
        
        for idx, slide in slides.items():
            style = slide.get("style", {})
            spacing = self._extract_spacing(style)
            
            if spacing:
                spacing_key = f"{spacing.get('line_height')}_{spacing.get('paragraph_spacing')}"
                spacing_patterns[spacing_key].append(idx)
                
        # Check for inconsistent spacing within slide types
        slide_types = self._group_slides_by_type(slides)
        
        for slide_type, type_slides in slide_types.items():
            type_spacings = set()
            
            for idx in type_slides:
                if idx in slides:
                    style = slides[idx].get("style", {})
                    spacing = self._extract_spacing(style)
                    if spacing:
                        spacing_key = f"{spacing.get('line_height')}_{spacing.get('paragraph_spacing')}"
                        type_spacings.add(spacing_key)
                        
            if len(type_spacings) > 1:
                issues.append(ConsistencyIssue(
                    rule_id=rule.id,
                    slide_indices=type_slides,
                    issue_type="spacing_inconsistency",
                    message=f"Inconsistent spacing in {slide_type} slides",
                    severity=rule.severity
                ))
                
        return issues
        
    async def check_image_quality(
        self, 
        rule: ConsistencyRule, 
        slides: Dict[int, Dict[str, Any]]
    ) -> List[ConsistencyIssue]:
        """Check image quality standards."""
        issues = []
        min_resolution = rule.parameters.get("min_resolution", 300)
        
        for idx, slide in slides.items():
            images = self._extract_images(slide.get("content", {}))
            
            for image in images:
                resolution = image.get("resolution")
                if resolution and resolution < min_resolution:
                    issues.append(ConsistencyIssue(
                        rule_id=rule.id,
                        slide_indices=[idx],
                        issue_type="low_resolution_image",
                        message=f"Image resolution {resolution}dpi below minimum {min_resolution}dpi",
                        severity=rule.severity,
                        details={"image": image.get("url", "unknown")}
                    ))
                    
        return issues
        
    async def _apply_auto_fix(
        self, 
        rule: ConsistencyRule, 
        slide_data: Dict[str, Any],
        context: Any
    ) -> Dict[str, Any]:
        """Apply automatic fixes for consistency issues."""
        if rule.id == "terminology":
            # Fix terminology inconsistencies
            content = slide_data.get("content", {})
            fixed_content = self._fix_terminology(content)
            slide_data["content"] = fixed_content
            
        return slide_data
        
    def _extract_fonts(self, style: Dict[str, Any]) -> List[str]:
        """Extract font families from style."""
        fonts = []
        
        for key, value in style.items():
            if "font" in key.lower() and isinstance(value, str):
                fonts.append(value)
            elif isinstance(value, dict):
                fonts.extend(self._extract_fonts(value))
                
        return list(set(fonts))
        
    def _extract_colors(self, style: Dict[str, Any]) -> List[str]:
        """Extract colors from style."""
        colors = []
        color_pattern = re.compile(r'#[0-9a-fA-F]{6}|rgb\([^)]+\)')
        
        for key, value in style.items():
            if isinstance(value, str):
                matches = color_pattern.findall(value)
                colors.extend(matches)
            elif isinstance(value, dict):
                colors.extend(self._extract_colors(value))
                
        return list(set(colors))
        
    def _extract_headings(self, content: Dict[str, Any]) -> List[Tuple[int, str]]:
        """Extract headings with their levels."""
        headings = []
        
        if "title" in content:
            headings.append((1, content["title"]))
            
        if "headings" in content:
            for idx, heading in enumerate(content["headings"]):
                level = heading.get("level", 2)
                text = heading.get("text", "")
                headings.append((level, text))
                
        return headings
        
    def _extract_bullet_styles(self, content: Dict[str, Any]) -> List[str]:
        """Extract bullet point styles."""
        styles = []
        
        if "bullets" in content:
            for bullet in content["bullets"]:
                style = bullet.get("style", "default")
                styles.append(style)
                
        return list(set(styles))
        
    def _extract_terms(self, content: Dict[str, Any]) -> List[str]:
        """Extract significant terms from content."""
        terms = []
        text_content = []
        
        # Collect all text
        for key, value in content.items():
            if isinstance(value, str):
                text_content.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        text_content.append(item)
                    elif isinstance(item, dict) and "text" in item:
                        text_content.append(item["text"])
                        
        # Extract significant terms (simplified)
        all_text = " ".join(text_content)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', all_text)
        terms.extend(words)
        
        return terms
        
    def _extract_spacing(self, style: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract spacing information."""
        spacing = {}
        
        if "line_height" in style:
            spacing["line_height"] = style["line_height"]
        if "paragraph_spacing" in style:
            spacing["paragraph_spacing"] = style["paragraph_spacing"]
            
        return spacing if spacing else None
        
    def _extract_images(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract image information."""
        images = []
        
        if "images" in content:
            images.extend(content["images"])
            
        for key, value in content.items():
            if isinstance(value, dict) and "image" in value:
                images.append(value["image"])
                
        return images
        
    def _group_slides_by_section(self, slides: Dict[int, Dict[str, Any]]) -> Dict[str, List[int]]:
        """Group slides by section."""
        sections = defaultdict(list)
        current_section = "main"
        
        for idx in sorted(slides.keys()):
            slide = slides[idx]
            if slide.get("type") == "section":
                current_section = f"section_{idx}"
            sections[current_section].append(idx)
            
        return dict(sections)
        
    def _group_slides_by_type(self, slides: Dict[int, Dict[str, Any]]) -> Dict[str, List[int]]:
        """Group slides by type."""
        types = defaultdict(list)
        
        for idx, slide in slides.items():
            slide_type = slide.get("type", "content")
            types[slide_type].append(idx)
            
        return dict(types)
        
    def _validate_heading_hierarchy(self, headings: List[Tuple[int, Tuple[int, str]]]) -> List[Dict[str, Any]]:
        """Validate heading hierarchy."""
        issues = []
        
        # Check for skipped levels
        prev_level = 0
        for slide_idx, (level, text) in headings:
            if level > prev_level + 1:
                issues.append({
                    "slides": [slide_idx],
                    "message": f"Skipped heading level: jumped from H{prev_level} to H{level}"
                })
            prev_level = level
            
        return issues
        
    def _fix_terminology(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Fix terminology in content."""
        # This would implement actual terminology fixes
        # For now, return content as-is
        return content
        
    def _issue_to_dict(self, issue: ConsistencyIssue) -> Dict[str, Any]:
        """Convert issue to dictionary."""
        return {
            "rule_id": issue.rule_id,
            "slide_indices": issue.slide_indices,
            "issue_type": issue.issue_type,
            "message": issue.message,
            "severity": issue.severity,
            "details": issue.details,
            "suggested_fix": issue.suggested_fix
        }