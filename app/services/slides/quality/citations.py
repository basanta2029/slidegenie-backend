"""
Citation Completeness Checker for SlideGenie presentations.

This module verifies that all claims are properly cited and that
citations are complete and correctly formatted.
"""
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation
from .base import QualityChecker, QualityDimension, QualityIssue


class CitationChecker(QualityChecker):
    """
    Checks citation completeness and accuracy in presentations.
    """
    
    def __init__(self):
        """Initialize citation checker."""
        # Patterns that indicate claims needing citations
        self.claim_patterns = [
            r'studies\s+(show|indicate|suggest|demonstrate)',
            r'research\s+(shows|indicates|suggests|demonstrates)',
            r'according\s+to\s+(?!the\s+(presentation|slide|figure|table))',
            r'it\s+has\s+been\s+(shown|demonstrated|proven)',
            r'evidence\s+(suggests|indicates|shows)',
            r'experiments\s+(show|demonstrate|reveal)',
            r'data\s+(shows|indicates|suggests)',
            r'analysis\s+(reveals|shows|indicates)',
            r'findings\s+(suggest|indicate|show)',
            r'results\s+(demonstrate|show|indicate)',
            r'\d+%\s+of\s+\w+',  # Percentage claims
            r'(increase|decrease|improvement)\s+of\s+\d+',  # Quantitative claims
            r'significantly\s+(better|worse|higher|lower|improved)',
            r'(most|many|several)\s+(researchers|scientists|studies)',
            r'recent\s+(studies|research|findings)',
            r'in\s+\d{4}',  # Year references (potential citation needed)
        ]
        
        # Citation format patterns
        self.citation_patterns = {
            'inline': r'\(([A-Za-z\s&,]+,?\s*\d{4}[a-z]?)\)',  # (Author, 2023)
            'numbered': r'\[(\d+)\]',  # [1]
            'superscript': r'\^(\d+)',  # ^1
            'author_year': r'([A-Z][a-z]+\s+(?:et\s+al\.\s+)?\(\d{4}\))',  # Smith et al. (2023)
        }
        
        # Fields required for complete citation
        self.required_citation_fields = {
            'article': ['authors', 'title', 'year', 'venue'],
            'inproceedings': ['authors', 'title', 'year', 'venue'],
            'book': ['authors', 'title', 'year', 'publisher'],
            'thesis': ['authors', 'title', 'year', 'institution'],
            'techreport': ['authors', 'title', 'year', 'institution'],
            'misc': ['authors', 'title', 'year']
        }
    
    @property
    def dimension(self) -> QualityDimension:
        """Return the quality dimension."""
        return QualityDimension.CITATIONS
    
    @property
    def weight(self) -> float:
        """Weight of citations in overall quality."""
        return 1.3  # Higher weight for academic integrity
    
    def check(
        self,
        presentation: PresentationResponse,
        slides: List[SlideResponse],
        references: Optional[List[Citation]] = None
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """
        Check citation completeness and accuracy.
        
        Returns:
            Tuple of (score, issues, metadata)
        """
        issues = []
        metadata = {}
        
        # Extract all text content and citations
        slide_texts = self._extract_slide_texts(slides)
        all_citations = self._extract_all_citations(slides, slide_texts)
        
        # Check for uncited claims
        uncited_score, uncited_issues, uncited_metadata = self._check_uncited_claims(
            slides, slide_texts, all_citations
        )
        issues.extend(uncited_issues)
        metadata['uncited_claims'] = uncited_metadata
        
        # Check citation completeness
        completeness_score, completeness_issues = self._check_citation_completeness(
            references or []
        )
        issues.extend(completeness_issues)
        
        # Check citation consistency
        consistency_score, consistency_issues = self._check_citation_consistency(
            all_citations, references or []
        )
        issues.extend(consistency_issues)
        
        # Check citation formatting
        format_score, format_issues = self._check_citation_formatting(
            slides, slide_texts
        )
        issues.extend(format_issues)
        
        # Check citation coverage
        coverage_score, coverage_issues, coverage_metadata = self._check_citation_coverage(
            slides, references or []
        )
        issues.extend(coverage_issues)
        metadata['coverage'] = coverage_metadata
        
        # Calculate overall score
        overall_score = (
            uncited_score * 0.35 +
            completeness_score * 0.25 +
            consistency_score * 0.2 +
            format_score * 0.1 +
            coverage_score * 0.1
        )
        
        # Add metadata
        metadata.update({
            'total_citations': len(all_citations),
            'unique_citations': len(set(all_citations)),
            'references_count': len(references) if references else 0,
            'uncited_score': uncited_score,
            'completeness_score': completeness_score,
            'consistency_score': consistency_score,
            'format_score': format_score,
            'coverage_score': coverage_score
        })
        
        # Identify strengths
        strengths = []
        if uncited_score >= 0.9:
            strengths.append("All major claims properly cited")
        if completeness_score >= 0.9:
            strengths.append("Complete citation information provided")
        if format_score >= 0.9:
            strengths.append("Consistent citation formatting")
        
        metadata['strengths'] = strengths
        
        return overall_score, issues, metadata
    
    def _extract_slide_texts(self, slides: List[SlideResponse]) -> List[str]:
        """Extract text content from slides."""
        texts = []
        
        for slide in slides:
            text_parts = []
            
            if slide.title:
                text_parts.append(slide.title)
            
            if slide.content:
                if 'subtitle' in slide.content:
                    text_parts.append(slide.content['subtitle'])
                
                if 'body' in slide.content:
                    for item in slide.content['body']:
                        if item.get('type') == 'text':
                            text_parts.append(item.get('content', ''))
                        elif item.get('type') == 'bullet_list':
                            text_parts.extend(item.get('items', []))
                        elif item.get('type') == 'caption':
                            text_parts.append(item.get('content', ''))
            
            if slide.speaker_notes:
                text_parts.append(slide.speaker_notes)
            
            texts.append(' '.join(text_parts))
        
        return texts
    
    def _extract_all_citations(
        self,
        slides: List[SlideResponse],
        slide_texts: List[str]
    ) -> List[str]:
        """Extract all citations from slides."""
        citations = []
        
        # Extract from slide content
        for slide in slides:
            if slide.content and 'body' in slide.content:
                for item in slide.content['body']:
                    if item.get('type') == 'citation':
                        citations.extend(item.get('keys', []))
        
        # Extract from text using patterns
        for text in slide_texts:
            for pattern_name, pattern in self.citation_patterns.items():
                matches = re.findall(pattern, text)
                citations.extend(matches)
        
        return citations
    
    def _check_uncited_claims(
        self,
        slides: List[SlideResponse],
        slide_texts: List[str],
        all_citations: List[str]
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """Check for claims that need citations."""
        issues = []
        metadata = {
            'total_claims': 0,
            'cited_claims': 0,
            'uncited_claims': []
        }
        
        for i, text in enumerate(slide_texts):
            # Find potential claims
            claims_in_slide = []
            for pattern in self.claim_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    claim_text = text[max(0, match.start()-50):match.end()+50]
                    claims_in_slide.append((match.start(), claim_text))
            
            metadata['total_claims'] += len(claims_in_slide)
            
            # Check if claims have nearby citations
            for pos, claim in claims_in_slide:
                # Look for citation within 100 characters
                nearby_text = text[max(0, pos-50):pos+100]
                has_citation = False
                
                for pattern in self.citation_patterns.values():
                    if re.search(pattern, nearby_text):
                        has_citation = True
                        metadata['cited_claims'] += 1
                        break
                
                if not has_citation:
                    metadata['uncited_claims'].append({
                        'slide': i + 1,
                        'claim': claim.strip()
                    })
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity="major",
                        slide_number=i + 1,
                        description=f"Uncited claim: {claim[:50]}...",
                        suggestion="Add appropriate citation for this claim"
                    ))
        
        # Calculate score
        if metadata['total_claims'] > 0:
            score = metadata['cited_claims'] / metadata['total_claims']
        else:
            score = 1.0  # No claims found, so no issues
        
        return score, issues, metadata
    
    def _check_citation_completeness(
        self,
        references: List[Citation]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check if citations have all required fields."""
        issues = []
        complete_count = 0
        
        for ref in references:
            bibtex_type = ref.bibtex_type or 'misc'
            required_fields = self.required_citation_fields.get(
                bibtex_type,
                self.required_citation_fields['misc']
            )
            
            missing_fields = []
            for field in required_fields:
                if field == 'authors' and not ref.authors:
                    missing_fields.append('authors')
                elif field == 'title' and not ref.title:
                    missing_fields.append('title')
                elif field == 'year' and not ref.year:
                    missing_fields.append('year')
                elif field == 'venue' and not ref.venue:
                    missing_fields.append('venue')
            
            if missing_fields:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description=f"Citation '{ref.key}' missing: {', '.join(missing_fields)}",
                    suggestion=f"Add missing {', '.join(missing_fields)} to citation"
                ))
            else:
                complete_count += 1
        
        # Calculate score
        score = complete_count / len(references) if references else 0.5
        
        return score, issues
    
    def _check_citation_consistency(
        self,
        all_citations: List[str],
        references: List[Citation]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check consistency between cited works and references."""
        issues = []
        
        # Get reference keys
        ref_keys = {ref.key for ref in references}
        
        # Check for citations without references
        unique_citations = set(all_citations)
        missing_refs = []
        
        for citation in unique_citations:
            # Try to match citation to reference
            matched = False
            for ref_key in ref_keys:
                if ref_key in citation or citation in ref_key:
                    matched = True
                    break
            
            if not matched and not citation.isdigit():  # Skip numbered citations
                missing_refs.append(citation)
        
        for missing in missing_refs:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="major",
                description=f"Citation '{missing}' not found in references",
                suggestion="Add missing reference or correct citation"
            ))
        
        # Check for unused references
        cited_keys = set()
        for citation in all_citations:
            for ref in references:
                if ref.key in citation or citation in ref.key:
                    cited_keys.add(ref.key)
        
        unused_refs = ref_keys - cited_keys
        for unused in unused_refs:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description=f"Reference '{unused}' not cited in presentation",
                suggestion="Remove unused reference or add citation"
            ))
        
        # Calculate score
        total_issues = len(missing_refs) + len(unused_refs)
        total_items = len(unique_citations) + len(ref_keys)
        score = 1.0 - (total_issues / total_items) if total_items > 0 else 1.0
        
        return score, issues
    
    def _check_citation_formatting(
        self,
        slides: List[SlideResponse],
        slide_texts: List[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """Check citation format consistency."""
        issues = []
        format_counts = defaultdict(int)
        
        # Count citation formats used
        for text in slide_texts:
            for format_name, pattern in self.citation_patterns.items():
                matches = re.findall(pattern, text)
                if matches:
                    format_counts[format_name] += len(matches)
        
        # Check for mixed formats
        if len(format_counts) > 1:
            dominant_format = max(format_counts, key=format_counts.get)
            total_citations = sum(format_counts.values())
            dominant_percentage = format_counts[dominant_format] / total_citations
            
            if dominant_percentage < 0.8:  # Less than 80% consistency
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description="Inconsistent citation formats used",
                    suggestion=f"Use {dominant_format} format consistently throughout"
                ))
        
        # Calculate score based on consistency
        if format_counts:
            total = sum(format_counts.values())
            max_count = max(format_counts.values())
            score = max_count / total
        else:
            score = 1.0
        
        return score, issues
    
    def _check_citation_coverage(
        self,
        slides: List[SlideResponse],
        references: List[Citation]
    ) -> Tuple[float, List[QualityIssue], Dict[str, Any]]:
        """Check if citations adequately cover the topic."""
        issues = []
        metadata = {
            'year_distribution': {},
            'source_diversity': 0,
            'recent_citations': 0
        }
        
        if not references:
            return 0.5, issues, metadata
        
        # Analyze year distribution
        years = [ref.year for ref in references if ref.year]
        if years:
            current_year = 2024  # Should be dynamic in production
            recent_count = sum(1 for year in years if year >= current_year - 5)
            metadata['recent_citations'] = recent_count
            
            # Check for outdated references
            old_count = sum(1 for year in years if year < current_year - 10)
            if old_count > len(years) * 0.5:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity="minor",
                    description="Many references are over 10 years old",
                    suggestion="Include more recent research (last 5 years)"
                ))
            
            # Year distribution
            for year in years:
                decade = (year // 10) * 10
                metadata['year_distribution'][f"{decade}s"] = (
                    metadata['year_distribution'].get(f"{decade}s", 0) + 1
                )
        
        # Check source diversity
        venues = [ref.venue for ref in references if ref.venue]
        unique_venues = set(venues)
        metadata['source_diversity'] = len(unique_venues)
        
        if len(unique_venues) < 3 and len(references) > 5:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity="minor",
                description="Limited diversity in citation sources",
                suggestion="Include references from various journals/conferences"
            ))
        
        # Calculate coverage score
        score = 0.5  # Base score
        if metadata['recent_citations'] > len(references) * 0.3:
            score += 0.2
        if metadata['source_diversity'] >= 3:
            score += 0.2
        if len(references) >= 10:  # Adequate number
            score += 0.1
        
        return min(score, 1.0), issues, metadata