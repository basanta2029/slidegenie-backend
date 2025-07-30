"""
Citation and bibliography management utilities for LaTeX documents.

Provides comprehensive functionality for:
- Parsing BibTeX files and bibliography entries
- Extracting in-text citations from LaTeX source
- Resolving citation references to bibliography entries
- Handling different citation styles and formats
- Cross-referencing and validation
"""

import re
from typing import List, Dict, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class CitationType(Enum):
    """Types of citation commands."""
    CITE = "cite"
    CITEP = "citep"  # Parenthetical citation
    CITET = "citet"  # Textual citation
    CITEALP = "citealp"  # Parenthetical without parentheses
    CITEALT = "citealt"  # Textual without parentheses
    CITEAUTHOR = "citeauthor"  # Author only
    CITEYEAR = "citeyear"  # Year only
    FOOTCITE = "footcite"  # Footnote citation
    PARENCITE = "parencite"  # Parenthetical (biblatex)
    TEXTCITE = "textcite"  # Textual (biblatex)
    AUTOCITE = "autocite"  # Automatic (biblatex)
    FULLCITE = "fullcite"  # Full citation (biblatex)
    FOOTFULLCITE = "footfullcite"  # Full footnote citation


class ReferenceType(Enum):
    """Types of bibliography entries."""
    ARTICLE = "article"
    BOOK = "book"
    INBOOK = "inbook"
    INCOLLECTION = "incollection"
    INPROCEEDINGS = "inproceedings"
    PROCEEDINGS = "proceedings"
    CONFERENCE = "conference"
    MASTERSTHESIS = "mastersthesis"
    PHDTHESIS = "phdthesis"
    TECHREPORT = "techreport"
    MANUAL = "manual"
    MISC = "misc"
    UNPUBLISHED = "unpublished"
    ONLINE = "online"
    ELECTRONIC = "electronic"


@dataclass
class Author:
    """Represents an author with parsed name components."""
    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""
    von_part: str = ""  # von, de, van, etc.
    jr_part: str = ""   # Jr., Sr., III, etc.
    full_name: str = ""
    
    def __post_init__(self):
        if not self.full_name:
            self.full_name = self._construct_full_name()
    
    def _construct_full_name(self) -> str:
        """Construct full name from components."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        if self.von_part:
            parts.append(self.von_part)
        if self.last_name:
            parts.append(self.last_name)
        if self.jr_part:
            parts.append(self.jr_part)
        return " ".join(parts)


@dataclass
class Citation:
    """Represents an in-text citation."""
    citation_key: str
    citation_type: CitationType
    prenote: str = ""  # Text before citation
    postnote: str = ""  # Text after citation (usually page numbers)
    position: int = 0
    line: int = 0
    column: int = 0
    raw_content: str = ""
    multiple_keys: List[str] = field(default_factory=list)  # For multiple citations
    
    def __post_init__(self):
        if ',' in self.citation_key and not self.multiple_keys:
            self.multiple_keys = [key.strip() for key in self.citation_key.split(',')]


@dataclass
class BibEntry:
    """Represents a bibliography entry."""
    key: str
    entry_type: ReferenceType
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    journal: str = ""
    booktitle: str = ""
    publisher: str = ""
    year: Optional[int] = None
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    isbn: str = ""
    issn: str = ""
    address: str = ""
    edition: str = ""
    chapter: str = ""
    note: str = ""
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    raw_entry: str = ""
    fields: Dict[str, str] = field(default_factory=dict)  # All other fields
    
    def get_author_names(self) -> List[str]:
        """Get list of author full names."""
        return [author.full_name for author in self.authors]
    
    def get_first_author_lastname(self) -> str:
        """Get last name of first author."""
        if self.authors:
            return self.authors[0].last_name
        return ""


class BibTeXParser:
    """Parser for BibTeX bibliography files."""
    
    # BibTeX entry pattern
    ENTRY_PATTERN = re.compile(
        r'@(\w+)\s*\{\s*([^,\s]+)\s*,\s*(.*?)\n\}',
        re.DOTALL | re.IGNORECASE
    )
    
    # Field pattern
    FIELD_PATTERN = re.compile(
        r'(\w+)\s*=\s*(?:\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}|"([^"]*)"|(\w+))',
        re.DOTALL
    )
    
    # Author name patterns
    AUTHOR_PATTERNS = [
        re.compile(r'^(.+?),\s*(.+)$'),  # Last, First Middle
        re.compile(r'^(.+?)\s+(.+?)$'),  # First Middle Last
    ]
    
    def __init__(self):
        self.entries: Dict[str, BibEntry] = {}
        self.parse_errors: List[str] = []
    
    def parse_file(self, file_path: str) -> Dict[str, BibEntry]:
        """Parse a BibTeX file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse_string(content)
        except Exception as e:
            logger.error(f"Failed to parse BibTeX file {file_path}: {e}")
            self.parse_errors.append(f"File error: {e}")
            return {}
    
    def parse_string(self, bibtex_content: str) -> Dict[str, BibEntry]:
        """Parse BibTeX content from string."""
        self.entries = {}
        self.parse_errors = []
        
        # Clean content
        content = self._clean_bibtex(bibtex_content)
        
        # Find all entries
        matches = self.ENTRY_PATTERN.findall(content)
        
        for entry_type, key, fields_str in matches:
            try:
                entry = self._parse_entry(entry_type, key, fields_str)
                if entry:
                    self.entries[key] = entry
            except Exception as e:
                error_msg = f"Error parsing entry '{key}': {e}"
                logger.warning(error_msg)
                self.parse_errors.append(error_msg)
        
        logger.info(f"Parsed {len(self.entries)} BibTeX entries with {len(self.parse_errors)} errors")
        return self.entries
    
    def _clean_bibtex(self, content: str) -> str:
        """Clean BibTeX content for parsing."""
        # Remove comments (lines starting with %)
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove inline comments but preserve % in URLs and strings
            if not line.strip().startswith('%'):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _parse_entry(self, entry_type: str, key: str, fields_str: str) -> Optional[BibEntry]:
        """Parse a single BibTeX entry."""
        try:
            ref_type = ReferenceType(entry_type.lower())
        except ValueError:
            ref_type = ReferenceType.MISC
            logger.warning(f"Unknown entry type '{entry_type}', treating as misc")
        
        entry = BibEntry(
            key=key,
            entry_type=ref_type,
            raw_entry=f"@{entry_type}{{{key}, {fields_str}}}"
        )
        
        # Parse fields
        fields = self._parse_fields(fields_str)
        entry.fields = fields
        
        # Extract standard fields
        entry.title = self._clean_field_value(fields.get('title', ''))
        entry.journal = self._clean_field_value(fields.get('journal', ''))
        entry.booktitle = self._clean_field_value(fields.get('booktitle', ''))
        entry.publisher = self._clean_field_value(fields.get('publisher', ''))
        entry.volume = fields.get('volume', '')
        entry.number = fields.get('number', '')
        entry.pages = fields.get('pages', '')
        entry.doi = fields.get('doi', '')
        entry.url = fields.get('url', '')
        entry.isbn = fields.get('isbn', '')
        entry.issn = fields.get('issn', '')
        entry.address = fields.get('address', '')
        entry.edition = fields.get('edition', '')
        entry.chapter = fields.get('chapter', '')
        entry.note = self._clean_field_value(fields.get('note', ''))
        entry.abstract = self._clean_field_value(fields.get('abstract', ''))
        
        # Parse year
        if 'year' in fields:
            try:
                entry.year = int(re.search(r'\d{4}', fields['year']).group())
            except (ValueError, AttributeError):
                pass
        
        # Parse authors
        if 'author' in fields:
            entry.authors = self._parse_authors(fields['author'])
        
        # Parse keywords
        if 'keywords' in fields:
            keywords_str = self._clean_field_value(fields['keywords'])
            entry.keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        
        return entry
    
    def _parse_fields(self, fields_str: str) -> Dict[str, str]:
        """Parse BibTeX fields from field string."""
        fields = {}
        
        matches = self.FIELD_PATTERN.findall(fields_str)
        
        for match in matches:
            field_name = match[0].lower()
            # Get the non-empty group (braced, quoted, or bare value)
            field_value = match[1] or match[2] or match[3]
            fields[field_name] = field_value
        
        return fields
    
    def _clean_field_value(self, value: str) -> str:
        """Clean field value by removing LaTeX commands and formatting."""
        if not value:
            return ""
        
        # Remove common LaTeX commands
        value = re.sub(r'\\textbf\{([^}]+)\}', r'\1', value)
        value = re.sub(r'\\textit\{([^}]+)\}', r'\1', value)
        value = re.sub(r'\\emph\{([^}]+)\}', r'\1', value)
        value = re.sub(r'\\texttt\{([^}]+)\}', r'\1', value)
        value = re.sub(r'\\url\{([^}]+)\}', r'\1', value)
        value = re.sub(r'\\href\{[^}]+\}\{([^}]+)\}', r'\1', value)
        
        # Remove other LaTeX commands
        value = re.sub(r'\\[a-zA-Z]+(?:\[[^\]]*\])?(?:\{[^}]*\})*', '', value)
        
        # Clean up spaces
        value = re.sub(r'\s+', ' ', value).strip()
        
        return value
    
    def _parse_authors(self, authors_str: str) -> List[Author]:
        """Parse author string into Author objects."""
        authors = []
        
        # Split by 'and'
        author_parts = re.split(r'\s+and\s+', authors_str, flags=re.IGNORECASE)
        
        for author_str in author_parts:
            author_str = self._clean_field_value(author_str.strip())
            if not author_str:
                continue
            
            author = self._parse_single_author(author_str)
            if author:
                authors.append(author)
        
        return authors
    
    def _parse_single_author(self, author_str: str) -> Optional[Author]:
        """Parse a single author name."""
        if not author_str:
            return None
        
        author = Author(full_name=author_str)
        
        # Try different patterns
        for pattern in self.AUTHOR_PATTERNS:
            match = pattern.match(author_str)
            if match:
                if ',' in author_str:
                    # Last, First Middle format
                    author.last_name = match.group(1).strip()
                    first_middle = match.group(2).strip()
                    if first_middle:
                        parts = first_middle.split()
                        author.first_name = parts[0]
                        if len(parts) > 1:
                            author.middle_name = ' '.join(parts[1:])
                else:
                    # First Middle Last format
                    parts = author_str.split()
                    if len(parts) >= 2:
                        author.last_name = parts[-1]
                        author.first_name = parts[0]
                        if len(parts) > 2:
                            author.middle_name = ' '.join(parts[1:-1])
                break
        
        # If no pattern matched, treat entire string as last name
        if not author.last_name and not author.first_name:
            author.last_name = author_str
        
        return author


class CitationExtractor:
    """Extracts citations from LaTeX source code."""
    
    # Citation command patterns
    CITATION_PATTERNS = {
        CitationType.CITE: re.compile(r'\\cite(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.CITEP: re.compile(r'\\citep(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.CITET: re.compile(r'\\citet(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.CITEALP: re.compile(r'\\citealp(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.CITEALT: re.compile(r'\\citealt(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.CITEAUTHOR: re.compile(r'\\citeauthor\{([^}]+)\}'),
        CitationType.CITEYEAR: re.compile(r'\\citeyear\{([^}]+)\}'),
        CitationType.FOOTCITE: re.compile(r'\\footcite(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.PARENCITE: re.compile(r'\\parencite(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.TEXTCITE: re.compile(r'\\textcite(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.AUTOCITE: re.compile(r'\\autocite(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}'),
        CitationType.FULLCITE: re.compile(r'\\fullcite\{([^}]+)\}'),
        CitationType.FOOTFULLCITE: re.compile(r'\\footfullcite\{([^}]+)\}'),
    }
    
    # Pattern for extracting pre/post notes
    DETAILED_CITATION_PATTERN = re.compile(
        r'\\(cite[a-z]*)\s*(?:\[([^\]]*)\])?\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}',
        re.IGNORECASE
    )
    
    def __init__(self):
        self.citations: List[Citation] = []
    
    def extract_citations(self, latex_content: str) -> List[Citation]:
        """Extract all citations from LaTeX content."""
        self.citations = []
        
        # Use detailed pattern to capture all information
        matches = self.DETAILED_CITATION_PATTERN.finditer(latex_content)
        
        for match in matches:
            command = match.group(1).lower()
            prenote = match.group(2) or ""
            postnote = match.group(3) or ""
            keys = match.group(4)
            
            # If only one optional argument, it's usually postnote
            if prenote and not postnote:
                postnote = prenote
                prenote = ""
            
            # Determine citation type
            try:
                citation_type = CitationType(command)
            except ValueError:
                citation_type = CitationType.CITE
            
            # Calculate position
            position = match.start()
            line, column = self._get_line_column(latex_content, position)
            
            citation = Citation(
                citation_key=keys,
                citation_type=citation_type,
                prenote=prenote.strip(),
                postnote=postnote.strip(),
                position=position,
                line=line,
                column=column,
                raw_content=match.group(0)
            )
            
            self.citations.append(citation)
        
        logger.info(f"Extracted {len(self.citations)} citations")
        return self.citations
    
    def _get_line_column(self, content: str, position: int) -> Tuple[int, int]:
        """Get line and column numbers for a position in content."""
        lines = content[:position].split('\n')
        line = len(lines)
        column = len(lines[-1]) + 1
        return line, column
    
    def get_cited_keys(self) -> Set[str]:
        """Get all unique citation keys."""
        keys = set()
        for citation in self.citations:
            if citation.multiple_keys:
                keys.update(citation.multiple_keys)
            else:
                keys.add(citation.citation_key)
        return keys


class CitationResolver:
    """Resolves citations against bibliography entries."""
    
    def __init__(self, bibliography: Dict[str, BibEntry]):
        self.bibliography = bibliography
        self.resolved_citations: Dict[str, BibEntry] = {}
        self.unresolved_keys: Set[str] = set()
    
    def resolve_citations(self, citations: List[Citation]) -> Dict[str, Any]:
        """Resolve all citations against bibliography."""
        citation_stats = {
            'total_citations': len(citations),
            'unique_keys': set(),
            'resolved': {},
            'unresolved': set(),
            'citation_types': {},
            'multiple_citations': []
        }
        
        # Count citation types
        for citation in citations:
            citation_type = citation.citation_type.value
            citation_stats['citation_types'][citation_type] = \
                citation_stats['citation_types'].get(citation_type, 0) + 1
        
        # Collect all keys
        all_keys = set()
        for citation in citations:
            if citation.multiple_keys:
                all_keys.update(citation.multiple_keys)
                citation_stats['multiple_citations'].append(citation)
            else:
                all_keys.add(citation.citation_key)
        
        citation_stats['unique_keys'] = all_keys
        
        # Resolve each key
        for key in all_keys:
            if key in self.bibliography:
                citation_stats['resolved'][key] = self.bibliography[key]
                self.resolved_citations[key] = self.bibliography[key]
            else:
                citation_stats['unresolved'].add(key)
                self.unresolved_keys.add(key)
        
        logger.info(f"Resolved {len(citation_stats['resolved'])} of {len(all_keys)} citation keys")
        
        return citation_stats
    
    def generate_citation_report(self) -> Dict[str, Any]:
        """Generate a detailed citation analysis report."""
        report = {
            'bibliography_entries': len(self.bibliography),
            'resolved_citations': len(self.resolved_citations),
            'unresolved_citations': len(self.unresolved_keys),
            'resolution_rate': len(self.resolved_citations) / max(1, len(self.resolved_citations) + len(self.unresolved_keys)),
            'unused_entries': [],
            'author_analysis': {},
            'year_distribution': {},
            'journal_analysis': {},
            'entry_type_distribution': {}
        }
        
        # Find unused bibliography entries
        cited_keys = set(self.resolved_citations.keys())
        all_bib_keys = set(self.bibliography.keys())
        report['unused_entries'] = list(all_bib_keys - cited_keys)
        
        # Analyze resolved citations
        for entry in self.resolved_citations.values():
            # Year distribution
            if entry.year:
                year_key = str(entry.year)
                report['year_distribution'][year_key] = \
                    report['year_distribution'].get(year_key, 0) + 1
            
            # Entry type distribution
            entry_type = entry.entry_type.value
            report['entry_type_distribution'][entry_type] = \
                report['entry_type_distribution'].get(entry_type, 0) + 1
            
            # Journal analysis
            if entry.journal:
                report['journal_analysis'][entry.journal] = \
                    report['journal_analysis'].get(entry.journal, 0) + 1
            
            # Author analysis
            for author in entry.authors:
                author_key = author.get_first_author_lastname()
                if author_key:
                    if author_key not in report['author_analysis']:
                        report['author_analysis'][author_key] = {
                            'count': 0,
                            'papers': [],
                            'years': set()
                        }
                    report['author_analysis'][author_key]['count'] += 1
                    report['author_analysis'][author_key]['papers'].append(entry.title)
                    if entry.year:
                        report['author_analysis'][author_key]['years'].add(entry.year)
        
        # Convert sets to lists for JSON serialization
        for author_info in report['author_analysis'].values():
            author_info['years'] = sorted(list(author_info['years']))
        
        return report