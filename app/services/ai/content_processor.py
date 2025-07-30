"""
Intelligent content processor for academic papers.
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


@dataclass
class Section:
    """Represents a document section."""
    title: str
    content: str
    level: int
    start_pos: int
    end_pos: int
    subsections: List['Section'] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []
            
            
@dataclass
class ExtractedElement:
    """Extracted element from content."""
    type: str  # 'figure', 'table', 'equation', 'citation'
    content: str
    caption: Optional[str] = None
    reference_id: Optional[str] = None
    position: int = 0
    

class ProcessedChunk(BaseModel):
    """Processed content chunk."""
    text: str
    section: Optional[str] = None
    subsection: Optional[str] = None
    token_count: int
    has_figures: bool = False
    has_tables: bool = False
    has_equations: bool = False
    citations: List[str] = []
    key_points: List[str] = []
    

class ContentProcessor:
    """Processes academic content for presentation generation."""
    
    def __init__(self):
        # Common section patterns in academic papers
        self.section_patterns = [
            r'^#+\s+(.+)$',  # Markdown headers
            r'^(\d+\.?\s+)?(?:Abstract|Introduction|Background|Methods?|Methodology|Results?|Discussion|Conclusion|References)\s*$',
            r'^(\d+\.\d+\.?\s+)?[A-Z][\w\s]+:?$',  # Numbered sections
        ]
        
        # Element extraction patterns
        self.figure_pattern = r'(?:Figure|Fig\.?)\s+(\d+[a-zA-Z]?)(?::|\.)\s*([^\n]+)'
        self.table_pattern = r'(?:Table)\s+(\d+[a-zA-Z]?)(?::|\.)\s*([^\n]+)'
        self.equation_pattern = r'(?:Equation|Eq\.?)\s*\(?(\d+)\)?'
        self.citation_pattern = r'\[([\d,\s-]+)\]|\(([^)]+(?:19|20)\d{2}[^)]*?)\)'
        
    def process_document(self, content: str, chunk_size: int = 1000) -> List[ProcessedChunk]:
        """Process entire document into chunks."""
        # Clean content
        content = self._clean_content(content)
        
        # Extract structure
        sections = self._extract_sections(content)
        
        # Extract elements
        figures = self._extract_figures(content)
        tables = self._extract_tables(content)
        equations = self._extract_equations(content)
        
        # Process into chunks
        chunks = self._create_chunks(content, sections, chunk_size)
        
        # Enhance chunks with metadata
        processed_chunks = []
        for chunk in chunks:
            processed = self._process_chunk(
                chunk,
                sections,
                figures,
                tables,
                equations
            )
            processed_chunks.append(processed)
            
        logger.info(
            "document_processed",
            total_chunks=len(processed_chunks),
            sections_found=len(sections),
            figures_found=len(figures),
            tables_found=len(tables)
        )
        
        return processed_chunks
        
    def extract_abstract(self, content: str) -> Optional[str]:
        """Extract abstract from document."""
        # Common abstract patterns
        patterns = [
            r'(?:^|\n)(?:Abstract|ABSTRACT)\s*\n+([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\n(?:Keywords|KEYWORDS|Introduction|INTRODUCTION|1\.|I\.))',
            r'(?:^|\n)(?:Summary|SUMMARY)\s*\n+([^\n]+(?:\n[^\n]+)*?)(?=\n\n)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()
                # Clean up the abstract
                abstract = re.sub(r'\s+', ' ', abstract)
                return abstract
                
        return None
        
    def extract_key_sections(self, content: str) -> Dict[str, str]:
        """Extract key sections from document."""
        sections = self._extract_sections(content)
        
        key_sections = {}
        section_mapping = {
            'introduction': ['introduction', 'background', 'motivation'],
            'methods': ['methods', 'methodology', 'materials and methods', 'experimental setup'],
            'results': ['results', 'findings', 'experiments', 'evaluation'],
            'discussion': ['discussion', 'analysis', 'implications'],
            'conclusion': ['conclusion', 'conclusions', 'summary', 'future work'],
        }
        
        for section in sections:
            section_lower = section.title.lower()
            
            for key, patterns in section_mapping.items():
                if any(pattern in section_lower for pattern in patterns):
                    if key not in key_sections:
                        key_sections[key] = section.content
                    else:
                        key_sections[key] += "\n\n" + section.content
                        
        return key_sections
        
    def extract_key_points(self, content: str, max_points: int = 5) -> List[str]:
        """Extract key points from content."""
        key_points = []
        
        # Look for explicitly marked key points
        patterns = [
            r'(?:Key (?:points?|findings?|contributions?)|Main (?:points?|findings?|contributions?)):\s*\n([^\n]+(?:\n[^\n]+)*?)(?=\n\n)',
            r'(?:^|\n)(?:\d+\.\s+|[•·▪▫◦‣⁃]\s+)([^\n]+)(?=\n(?:\d+\.\s+|[•·▪▫◦‣⁃]\s+|\n|$))',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                point = match.group(1).strip()
                if len(point) > 20 and len(point) < 200:  # Reasonable length
                    key_points.append(point)
                    
        # If no explicit points, extract from important sentences
        if not key_points:
            sentences = self._extract_important_sentences(content)
            key_points = sentences[:max_points]
            
        return key_points[:max_points]
        
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        
        # Remove page numbers and headers/footers
        content = re.sub(r'\n\d+\n', '\n', content)
        content = re.sub(r'Page \d+ of \d+', '', content)
        
        # Clean up special characters
        content = content.replace('\r\n', '\n')
        content = content.replace('\r', '\n')
        
        return content.strip()
        
    def _extract_sections(self, content: str) -> List[Section]:
        """Extract document sections."""
        sections = []
        lines = content.split('\n')
        
        current_section = None
        current_content = []
        
        for i, line in enumerate(lines):
            is_section = False
            
            # Check if line matches section pattern
            for pattern in self.section_patterns:
                match = re.match(pattern, line.strip(), re.IGNORECASE)
                if match:
                    # Save previous section
                    if current_section:
                        current_section.content = '\n'.join(current_content).strip()
                        current_section.end_pos = i - 1
                        sections.append(current_section)
                        
                    # Start new section
                    title = match.group(1) if match.groups() else line.strip()
                    level = self._determine_section_level(line)
                    current_section = Section(
                        title=title,
                        content='',
                        level=level,
                        start_pos=i,
                        end_pos=i
                    )
                    current_content = []
                    is_section = True
                    break
                    
            if not is_section and current_section:
                current_content.append(line)
                
        # Save last section
        if current_section:
            current_section.content = '\n'.join(current_content).strip()
            current_section.end_pos = len(lines) - 1
            sections.append(current_section)
            
        # Build section hierarchy
        return self._build_section_hierarchy(sections)
        
    def _determine_section_level(self, line: str) -> int:
        """Determine section hierarchy level."""
        # Markdown headers
        if line.startswith('#'):
            return len(re.match(r'^#+', line).group())
            
        # Numbered sections
        match = re.match(r'^(\d+)(\.\d+)*', line)
        if match:
            return len(match.group().split('.'))
            
        # Default to level 1
        return 1
        
    def _build_section_hierarchy(self, sections: List[Section]) -> List[Section]:
        """Build hierarchical structure of sections."""
        if not sections:
            return []
            
        root_sections = []
        stack = []
        
        for section in sections:
            # Find parent
            while stack and stack[-1].level >= section.level:
                stack.pop()
                
            if stack:
                # Add as subsection
                stack[-1].subsections.append(section)
            else:
                # Add as root section
                root_sections.append(section)
                
            stack.append(section)
            
        return root_sections
        
    def _extract_figures(self, content: str) -> List[ExtractedElement]:
        """Extract figure references."""
        figures = []
        
        for match in re.finditer(self.figure_pattern, content, re.IGNORECASE):
            figure = ExtractedElement(
                type='figure',
                reference_id=f'fig_{match.group(1)}',
                caption=match.group(2).strip(),
                content=match.group(0),
                position=match.start()
            )
            figures.append(figure)
            
        return figures
        
    def _extract_tables(self, content: str) -> List[ExtractedElement]:
        """Extract table references."""
        tables = []
        
        for match in re.finditer(self.table_pattern, content, re.IGNORECASE):
            table = ExtractedElement(
                type='table',
                reference_id=f'table_{match.group(1)}',
                caption=match.group(2).strip(),
                content=match.group(0),
                position=match.start()
            )
            tables.append(table)
            
        return tables
        
    def _extract_equations(self, content: str) -> List[ExtractedElement]:
        """Extract equation references."""
        equations = []
        
        for match in re.finditer(self.equation_pattern, content, re.IGNORECASE):
            equation = ExtractedElement(
                type='equation',
                reference_id=f'eq_{match.group(1)}',
                content=match.group(0),
                position=match.start()
            )
            equations.append(equation)
            
        return equations
        
    def _extract_citations(self, text: str) -> List[str]:
        """Extract citations from text."""
        citations = []
        
        for match in re.finditer(self.citation_pattern, text):
            citation = match.group(1) or match.group(2)
            if citation:
                citations.append(citation.strip())
                
        return list(set(citations))  # Remove duplicates
        
    def _create_chunks(
        self,
        content: str,
        sections: List[Section],
        chunk_size: int
    ) -> List[Tuple[str, Optional[Section]]]:
        """Create content chunks respecting section boundaries."""
        chunks = []
        
        # Process each section
        for section in sections:
            section_text = section.content
            
            # If section is small enough, keep as single chunk
            if self._estimate_tokens(section_text) <= chunk_size:
                chunks.append((section_text, section))
            else:
                # Split section into smaller chunks
                paragraphs = section_text.split('\n\n')
                current_chunk = []
                current_size = 0
                
                for para in paragraphs:
                    para_size = self._estimate_tokens(para)
                    
                    if current_size + para_size > chunk_size and current_chunk:
                        # Save current chunk
                        chunks.append(('\n\n'.join(current_chunk), section))
                        current_chunk = [para]
                        current_size = para_size
                    else:
                        current_chunk.append(para)
                        current_size += para_size
                        
                # Save last chunk
                if current_chunk:
                    chunks.append(('\n\n'.join(current_chunk), section))
                    
        return chunks
        
    def _process_chunk(
        self,
        chunk: Tuple[str, Optional[Section]],
        sections: List[Section],
        figures: List[ExtractedElement],
        tables: List[ExtractedElement],
        equations: List[ExtractedElement]
    ) -> ProcessedChunk:
        """Process a chunk with metadata."""
        text, section = chunk
        
        # Extract citations
        citations = self._extract_citations(text)
        
        # Check for elements
        has_figures = any(fig.content in text for fig in figures)
        has_tables = any(table.content in text for table in tables)
        has_equations = any(eq.content in text for eq in equations)
        
        # Extract key points (simplified)
        key_points = self._extract_important_sentences(text, max_sentences=3)
        
        return ProcessedChunk(
            text=text,
            section=section.title if section else None,
            subsection=None,  # Could be enhanced
            token_count=self._estimate_tokens(text),
            has_figures=has_figures,
            has_tables=has_tables,
            has_equations=has_equations,
            citations=citations,
            key_points=key_points
        )
        
    def _extract_important_sentences(self, text: str, max_sentences: int = 5) -> List[str]:
        """Extract important sentences using simple heuristics."""
        sentences = re.split(r'[.!?]\s+', text)
        
        # Score sentences
        scored_sentences = []
        
        importance_indicators = [
            'significant', 'important', 'key', 'main', 'primary',
            'novel', 'contribution', 'finding', 'result', 'conclude',
            'demonstrate', 'show', 'reveal', 'indicate', 'suggest'
        ]
        
        for sentence in sentences:
            if len(sentence) < 20:  # Skip very short sentences
                continue
                
            score = 0
            sentence_lower = sentence.lower()
            
            # Check for importance indicators
            for indicator in importance_indicators:
                if indicator in sentence_lower:
                    score += 2
                    
            # Bonus for sentences with numbers (likely results)
            if re.search(r'\d+\.?\d*%?', sentence):
                score += 1
                
            # Bonus for sentences at paragraph start
            if sentence == sentences[0]:
                score += 1
                
            scored_sentences.append((score, sentence.strip()))
            
        # Sort by score and return top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        return [sent for _, sent in scored_sentences[:max_sentences]]
        
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Approximate: 1 token ≈ 4 characters
        return len(text) // 4