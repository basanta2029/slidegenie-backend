"""
Citation parsing utilities for academic documents.

Provides comprehensive citation and reference parsing capabilities
for various academic citation formats including APA, MLA, Chicago, etc.
"""

import re
from typing import Dict, List, Optional, Tuple, Set, NamedTuple
from dataclasses import dataclass
from enum import Enum
import json

import structlog

from app.domain.schemas.document_processing import (
    CitationElement,
    ReferenceElement,
    ElementType,
    BoundingBox
)

logger = structlog.get_logger(__name__)


class CitationStyle(str, Enum):
    """Supported citation styles."""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    HARVARD = "harvard"
    VANCOUVER = "vancouver"
    NUMERIC = "numeric"
    AUTHOR_YEAR = "author_year"
    UNKNOWN = "unknown"


class ReferenceType(str, Enum):
    """Types of references."""
    JOURNAL_ARTICLE = "journal_article"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    CONFERENCE_PAPER = "conference_paper"
    THESIS = "thesis"
    REPORT = "report"
    WEBSITE = "website"
    PATENT = "patent"
    SOFTWARE = "software"
    DATASET = "dataset"
    UNKNOWN = "unknown"


@dataclass
class ParsedCitation:
    """Parsed citation information."""
    original_text: str
    citation_key: Optional[str] = None
    authors: List[str] = None
    year: Optional[int] = None
    page_numbers: Optional[str] = None
    style: CitationStyle = CitationStyle.UNKNOWN
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []


@dataclass
class ParsedReference:
    """Parsed reference information."""
    original_text: str
    authors: List[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    book_title: Optional[str] = None
    conference: Optional[str] = None
    year: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    isbn: Optional[str] = None
    reference_type: ReferenceType = ReferenceType.UNKNOWN
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []


class CitationParser:
    """
    Advanced citation and reference parser for academic documents.
    
    Handles multiple citation styles and formats, with robust pattern
    matching and validation for academic literature.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = structlog.get_logger(__name__)
        
        # Initialize citation patterns
        self._init_citation_patterns()
        self._init_reference_patterns()
        
        # Author name patterns
        self.author_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)',  # First Middle Last
            r'([A-Z][a-z]+,\s+[A-Z]\.(?:\s+[A-Z]\.)*)',      # Last, F. M.
            r'([A-Z]\.(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)',       # F. M. Last
        ]
        
        # Common academic terms for classification
        self.journal_indicators = {
            'journal', 'proceedings', 'transactions', 'letters', 'review',
            'science', 'nature', 'cell', 'lancet', 'ieee', 'acm'
        }
        
        self.conference_indicators = {
            'conference', 'symposium', 'workshop', 'congress', 'meeting',
            'proceedings', 'international', 'annual', 'ieee', 'acm'
        }
        
    def parse_citations(self, text: str, bbox: Optional[BoundingBox] = None) -> List[CitationElement]:
        """
        Parse in-text citations from text.
        
        Args:
            text: Text containing citations
            bbox: Bounding box of the text
            
        Returns:
            List of CitationElement objects
        """
        citations = []
        
        # Try different citation patterns
        for style, patterns in self.citation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    parsed = self._parse_citation_match(match, style)
                    if parsed and parsed.confidence > 0.5:
                        citation = CitationElement(
                            content=match.group(0),
                            bbox=bbox,
                            citation_key=parsed.citation_key,
                            citation_type=style.value,
                            authors=parsed.authors,
                            year=parsed.year,
                            page_numbers=parsed.page_numbers,
                            confidence=parsed.confidence
                        )
                        citations.append(citation)
        
        # Remove duplicates and overlapping citations
        citations = self._deduplicate_citations(citations)
        
        return citations
    
    def parse_references(self, text_lines: List[str]) -> List[ReferenceElement]:
        """
        Parse bibliography references from text lines.
        
        Args:
            text_lines: List of reference text lines
            
        Returns:
            List of ReferenceElement objects
        """
        references = []
        
        for i, line in enumerate(text_lines):
            line = line.strip()
            if not line or len(line) < 20:  # Skip very short lines
                continue
                
            parsed = self._parse_reference_line(line)
            if parsed and parsed.confidence > 0.3:
                reference = ReferenceElement(
                    content=line,
                    reference_key=f"ref_{i+1}",
                    authors=parsed.authors,
                    title=parsed.title,
                    journal=parsed.journal,
                    year=parsed.year,
                    volume=parsed.volume,
                    issue=parsed.issue,
                    pages=parsed.pages,
                    doi=parsed.doi,
                    url=parsed.url,
                    reference_type=parsed.reference_type.value,
                    confidence=parsed.confidence
                )
                references.append(reference)
        
        return references
    
    def detect_citation_style(self, citations: List[str]) -> CitationStyle:
        """
        Detect the predominant citation style from a list of citations.
        
        Args:
            citations: List of citation strings
            
        Returns:
            Detected citation style
        """
        if not citations:
            return CitationStyle.UNKNOWN
        
        style_scores = {style: 0 for style in CitationStyle}
        
        for citation in citations:
            for style, patterns in self.citation_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, citation, re.IGNORECASE):
                        style_scores[style] += 1
                        break
        
        # Return style with highest score
        max_style = max(style_scores.items(), key=lambda x: x[1])
        return max_style[0] if max_style[1] > 0 else CitationStyle.UNKNOWN
    
    def extract_author_names(self, text: str) -> List[str]:
        """
        Extract author names from text using various patterns.
        
        Args:
            text: Text containing author names
            
        Returns:
            List of extracted author names
        """
        authors = []
        
        for pattern in self.author_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean up author name
                author = re.sub(r'\s+', ' ', match.strip())
                if len(author) > 3 and author not in authors:
                    authors.append(author)
        
        return authors
    
    def _init_citation_patterns(self):
        """Initialize citation pattern dictionaries."""
        self.citation_patterns = {
            CitationStyle.NUMERIC: [
                r'\[(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\]',  # [1], [1-3], [1,2,3]
                r'\((\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\)',  # (1), (1-3), (1,2,3)
            ],
            CitationStyle.AUTHOR_YEAR: [
                r'\(([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)*,?\s+\d{4}[a-z]?(?:,\s*pp?\.\s*\d+(?:-\d+)?)?)\)',
                r'([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)*\s+\(\d{4}[a-z]?\))',
            ],
            CitationStyle.APA: [
                r'\(([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)*,\s+\d{4}(?:,\s*p{1,2}\.\s*\d+(?:-\d+)?)?)\)',
                r'([A-Z][a-z]+(?:\s+&\s+[A-Z][a-z]+)*\s+\(\d{4}\))',
            ],
            CitationStyle.MLA: [
                r'\(([A-Z][a-z]+(?:\s+\d+)?)\)',
                r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s+\(\d+\)',
            ],
            CitationStyle.CHICAGO: [
                r'\(([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)*\s+\d{4}(?:,\s*\d+(?:-\d+)?)?)\)',
            ],
        }
    
    def _init_reference_patterns(self):
        """Initialize reference parsing patterns."""
        self.reference_patterns = {
            'authors': r'^([A-Z][a-z]+(?:,\s+[A-Z]\.(?:\s+[A-Z]\.)*)?(?:,?\s+(?:and|&)\s+[A-Z][a-z]+(?:,\s+[A-Z]\.(?:\s+[A-Z]\.)*)?)*)',
            'year': r'\b(19|20)\d{2}\b',
            'title': r'["\u201c]([^"\u201d]+)["\u201d]',  # Quoted titles
            'journal': r'\b([A-Z][A-Za-z\s&]+(?:Journal|Review|Letters|Science|Nature|Cell|Proceedings))\b',
            'volume': r'\bvol(?:ume)?\.?\s*(\d+)\b|\b(\d+)\s*\(',
            'issue': r'\b(?:no|issue)\.?\s*(\d+)\b|\((\d+)\)',
            'pages': r'\bpp?\.?\s*(\d+(?:-\d+)?)\b',
            'doi': r'(?:doi:?\s*)?10\.[0-9]+\/[^\s]+',
            'url': r'https?:\/\/[^\s]+',
            'isbn': r'ISBN:?\s*([\d-]+)',
        }
    
    def _parse_citation_match(self, match: re.Match, style: CitationStyle) -> Optional[ParsedCitation]:
        """Parse a citation match object."""
        citation_text = match.group(0)
        content = match.group(1) if match.groups() else citation_text
        
        parsed = ParsedCitation(original_text=citation_text, style=style)
        
        if style == CitationStyle.NUMERIC:
            # Extract numbers
            numbers = re.findall(r'\d+', content)
            if numbers:
                parsed.citation_key = ','.join(numbers)
                parsed.confidence = 0.9
        
        elif style in [CitationStyle.AUTHOR_YEAR, CitationStyle.APA]:
            # Extract authors and year
            year_match = re.search(r'\b(19|20)\d{2}[a-z]?\b', content)
            if year_match:
                parsed.year = int(year_match.group(0)[:4])
                parsed.confidence += 0.4
            
            # Extract authors (text before year)
            author_text = re.sub(r'\b(19|20)\d{2}[a-z]?\b.*', '', content).strip()
            authors = re.split(r'\s*(?:,|&|and)\s*', author_text)
            parsed.authors = [a.strip() for a in authors if a.strip()]
            
            if parsed.authors:
                parsed.confidence += 0.4
            
            # Extract page numbers
            page_match = re.search(r'pp?\.?\s*(\d+(?:-\d+)?)', content)
            if page_match:
                parsed.page_numbers = page_match.group(1)
                parsed.confidence += 0.2
        
        return parsed if parsed.confidence > 0.5 else None
    
    def _parse_reference_line(self, line: str) -> Optional[ParsedReference]:
        """Parse a single reference line."""
        parsed = ParsedReference(original_text=line)
        confidence = 0.0
        
        # Extract authors
        author_match = re.match(self.reference_patterns['authors'], line)
        if author_match:
            author_text = author_match.group(1)
            parsed.authors = self.extract_author_names(author_text)
            if parsed.authors:
                confidence += 0.3
        
        # Extract year
        year_match = re.search(self.reference_patterns['year'], line)
        if year_match:
            parsed.year = int(year_match.group(0))
            confidence += 0.2
        
        # Extract title
        title_match = re.search(self.reference_patterns['title'], line)
        if title_match:
            parsed.title = title_match.group(1).strip()
            confidence += 0.3
        
        # Extract journal
        journal_match = re.search(self.reference_patterns['journal'], line, re.IGNORECASE)
        if journal_match:
            parsed.journal = journal_match.group(1).strip()
            confidence += 0.2
            parsed.reference_type = ReferenceType.JOURNAL_ARTICLE
        
        # Extract volume
        volume_match = re.search(self.reference_patterns['volume'], line)
        if volume_match:
            parsed.volume = volume_match.group(1) or volume_match.group(2)
            confidence += 0.1
        
        # Extract issue
        issue_match = re.search(self.reference_patterns['issue'], line)
        if issue_match:
            parsed.issue = issue_match.group(1) or issue_match.group(2)
            confidence += 0.1
        
        # Extract pages
        pages_match = re.search(self.reference_patterns['pages'], line)
        if pages_match:
            parsed.pages = pages_match.group(1)
            confidence += 0.1
        
        # Extract DOI
        doi_match = re.search(self.reference_patterns['doi'], line, re.IGNORECASE)
        if doi_match:
            parsed.doi = doi_match.group(0).replace('doi:', '').strip()
            confidence += 0.2
        
        # Extract URL
        url_match = re.search(self.reference_patterns['url'], line)
        if url_match:
            parsed.url = url_match.group(0)
            confidence += 0.1
        
        # Classify reference type if not already determined
        if parsed.reference_type == ReferenceType.UNKNOWN:
            parsed.reference_type = self._classify_reference_type(line)
        
        parsed.confidence = min(1.0, confidence)
        return parsed
    
    def _classify_reference_type(self, text: str) -> ReferenceType:
        """Classify the type of reference based on content."""
        text_lower = text.lower()
        
        # Check for journal indicators
        if any(indicator in text_lower for indicator in self.journal_indicators):
            return ReferenceType.JOURNAL_ARTICLE
        
        # Check for conference indicators
        if any(indicator in text_lower for indicator in self.conference_indicators):
            return ReferenceType.CONFERENCE_PAPER
        
        # Check for book indicators
        if any(word in text_lower for word in ['press', 'publisher', 'edition', 'isbn']):
            return ReferenceType.BOOK
        
        # Check for thesis indicators
        if any(word in text_lower for word in ['thesis', 'dissertation', 'phd', 'master']):
            return ReferenceType.THESIS
        
        # Check for web indicators
        if any(word in text_lower for word in ['http', 'www', 'website', 'retrieved']):
            return ReferenceType.WEBSITE
        
        return ReferenceType.UNKNOWN
    
    def _deduplicate_citations(self, citations: List[CitationElement]) -> List[CitationElement]:
        """Remove duplicate and overlapping citations."""
        if not citations:
            return citations
        
        # Sort by position (if bbox available)
        citations.sort(key=lambda c: (c.bbox.x0, c.bbox.y0) if c.bbox else (0, 0))
        
        deduplicated = []
        
        for citation in citations:
            # Check for overlaps with existing citations
            is_duplicate = False
            
            for existing in deduplicated:
                # Check text similarity
                if citation.content == existing.content:
                    is_duplicate = True
                    break
                
                # Check bbox overlap
                if citation.bbox and existing.bbox and citation.bbox.overlaps(existing.bbox):
                    # Keep the one with higher confidence
                    if citation.confidence > existing.confidence:
                        deduplicated.remove(existing)
                    else:
                        is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(citation)
        
        return deduplicated