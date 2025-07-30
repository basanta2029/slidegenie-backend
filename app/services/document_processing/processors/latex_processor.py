"""
Comprehensive LaTeX document processor for academic .tex files.

Provides complete LaTeX document processing including:
- Tokenization and parsing of LaTeX source
- Document structure extraction (sections, chapters, etc.)
- Mathematical equation processing and rendering
- Citation and bibliography management
- Cross-reference resolution
- Figure and table extraction
- Metadata extraction from document and packages
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Tuple, Set
from uuid import UUID, uuid4
import structlog

from app.services.document_processing.base import (
    BaseDocumentProcessor,
    DocumentProcessorError,
    InvalidDocumentError,
    ProcessorCapability
)
from app.domain.schemas.document_processing import (
    DocumentType,
    ElementType,
    ProcessingRequest,
    ProcessingResult,
    ProcessingProgress,
    ProcessingStatus,
    DocumentElement,
    DocumentMetadata,
    DocumentSection,
    TextElement,
    HeadingElement,
    FigureElement,
    TableElement,
    CitationElement,
    ReferenceElement,
    EquationElement,
    MathElement,
    TheoremElement,
    LaTeXEnvironmentElement,
    LaTeXCommandElement,
    BoundingBox,
    TextStyle
)
from app.services.document_processing.utils.latex_parser import (
    LaTeXTokenizer,
    LaTeXParser,
    LaTeXCommand,
    LaTeXEnvironment,
    CrossReferenceResolver,
    TokenType
)
from app.services.document_processing.utils.equation_renderer import (
    EquationRenderer,
    EquationParser,
    MathEnvironmentAnalyzer
)
from app.services.document_processing.utils.citation_manager import (
    BibTeXParser,
    CitationExtractor,
    CitationResolver,
    BibEntry,
    Citation,
    CitationType
)

logger = structlog.get_logger(__name__)


class LaTeXProcessor(BaseDocumentProcessor):
    """Comprehensive LaTeX document processor."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Initialize component processors
        self.tokenizer = LaTeXTokenizer()
        self.parser = LaTeXParser([])  # Will be initialized with tokens
        self.equation_renderer = EquationRenderer(
            dpi=self.config.get('equation_dpi', 150),
            font_size=self.config.get('equation_font_size', 12)
        )
        self.equation_parser = EquationParser()
        self.math_analyzer = MathEnvironmentAnalyzer()
        self.bibtex_parser = BibTeXParser()
        self.citation_extractor = CitationExtractor()
        self.cross_ref_resolver = CrossReferenceResolver()
        
        # Processing state
        self.current_source = ""
        self.current_tokens = []
        self.current_commands = []
        self.current_environments = []
        self.bibliography: Dict[str, BibEntry] = {}
        self.citations: List[Citation] = []
        
        # Document structure
        self.document_class = ""
        self.packages = []
        self.preamble_commands = []
        
    @property
    def supported_types(self) -> List[DocumentType]:
        """Return supported document types."""
        return [DocumentType.LATEX]
    
    @property
    def capabilities(self) -> Dict[str, ProcessorCapability]:
        """Return processor capabilities."""
        return {
            "text_extraction": ProcessorCapability(
                name="Text Extraction",
                description="Extract text content with structure preservation",
                supported=True,
                confidence=0.95
            ),
            "structure_analysis": ProcessorCapability(
                name="Document Structure Analysis",
                description="Extract sections, chapters, and hierarchical structure",
                supported=True,
                confidence=0.9
            ),
            "equation_processing": ProcessorCapability(
                name="Mathematical Equation Processing",
                description="Parse and render LaTeX equations",
                supported=True,
                confidence=0.85
            ),
            "citation_management": ProcessorCapability(
                name="Citation and Bibliography Management",
                description="Extract and resolve citations and references",
                supported=True,
                confidence=0.9
            ),
            "cross_reference_resolution": ProcessorCapability(
                name="Cross-reference Resolution",
                description="Resolve internal document references",
                supported=True,
                confidence=0.8
            ),
            "metadata_extraction": ProcessorCapability(
                name="Metadata Extraction",
                description="Extract document metadata and author information",
                supported=True,
                confidence=0.85
            ),
            "figure_table_extraction": ProcessorCapability(
                name="Figure and Table Extraction",
                description="Extract figures and tables with captions",
                supported=True,
                confidence=0.75
            ),
            "multi_file_handling": ProcessorCapability(
                name="Multi-file Document Support",
                description="Handle documents with \\input and \\include commands",
                supported=True,
                confidence=0.7
            )
        }
    
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """Process a LaTeX document according to request specifications."""
        job_id = request.document_id
        self._start_job(job_id, total_steps=12)
        
        try:
            file_path = Path(request.file_path)
            await self.validate_document(file_path)
            
            # Step 1: Load and preprocess document
            self._update_progress(job_id, 8.3, "Loading document", 1, 12)
            source_content = await self._load_document(file_path)
            
            # Step 2: Tokenize LaTeX source
            self._update_progress(job_id, 16.6, "Tokenizing LaTeX source", 2, 12)
            self.current_tokens = self.tokenizer.tokenize(source_content)
            
            # Step 3: Parse commands and environments
            self._update_progress(job_id, 25.0, "Parsing commands and environments", 3, 12)
            self.parser = LaTeXParser(self.current_tokens)
            self.current_commands, self.current_environments = self.parser.parse()
            
            # Step 4: Extract document structure
            self._update_progress(job_id, 33.3, "Extracting document structure", 4, 12)
            sections = await self._extract_document_structure()
            
            # Step 5: Process equations
            equations = []
            if request.extract_figures:  # Using figures flag for equations
                self._update_progress(job_id, 41.6, "Processing equations", 5, 12)
                equations = await self._process_equations()
            
            # Step 6: Extract figures and tables
            figures, tables = [], []
            if request.extract_figures or request.extract_tables:
                self._update_progress(job_id, 50.0, "Extracting figures and tables", 6, 12)
                if request.extract_figures:
                    figures = await self._extract_figures()
                if request.extract_tables:
                    tables = await self._extract_tables()
            
            # Step 7: Process citations and bibliography
            citations, references = [], []
            if request.extract_citations or request.extract_references:
                self._update_progress(job_id, 58.3, "Processing citations", 7, 12)
                citations, references = await self._process_citations_and_bibliography(file_path)
            
            # Step 8: Extract text elements
            text_elements = []
            if request.extract_text:
                self._update_progress(job_id, 66.6, "Extracting text elements", 8, 12)
                text_elements = await self.extract_text(file_path, request.preserve_layout)
            
            # Step 9: Resolve cross-references
            self._update_progress(job_id, 75.0, "Resolving cross-references", 9, 12)
            await self._resolve_cross_references()
            
            # Step 10: Extract metadata
            metadata = DocumentMetadata()
            if request.extract_metadata:
                self._update_progress(job_id, 83.3, "Extracting metadata", 10, 12)
                metadata = await self.extract_metadata(file_path)
            
            # Step 11: Combine all elements
            self._update_progress(job_id, 91.6, "Combining elements", 11, 12)
            all_elements = text_elements + equations + figures + tables + citations
            
            # Step 12: Create final result
            self._update_progress(job_id, 100.0, "Finalizing result", 12, 12)
            
            result = ProcessingResult(
                document_id=request.document_id,
                document_type=DocumentType.LATEX,
                status=ProcessingStatus.COMPLETED,
                metadata=metadata,
                sections=sections,
                elements=all_elements,
                figures=figures,
                tables=tables,
                citations=citations,
                references=references
            )
            
            self._complete_job(job_id, success=True)
            logger.info(f"Successfully processed LaTeX document: {file_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process LaTeX document: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._complete_job(job_id, success=False, error=error_msg)
            
            return ProcessingResult(
                document_id=request.document_id,
                document_type=DocumentType.LATEX,
                status=ProcessingStatus.FAILED,
                error_message=error_msg
            )
    
    async def extract_text(self, file_path: Union[str, Path], preserve_layout: bool = True) -> List[DocumentElement]:
        """Extract text elements from LaTeX document."""
        text_elements = []
        
        # Extract text from parsed environments and commands
        for env in self.current_environments:
            if env.name in ['document']:
                # Main document content
                elements = await self._extract_text_from_content(env.content, preserve_layout)
                text_elements.extend(elements)
            elif env.name in LaTeXParser.THEOREM_ENVIRONMENTS:
                # Theorem-like environments
                theorem_element = TheoremElement(
                    content=env.content.strip(),
                    theorem_type=env.name,
                    metadata={
                        'begin_line': env.begin_line,
                        'end_line': env.end_line,
                        'raw_content': env.raw_content
                    }
                )
                text_elements.append(theorem_element)
        
        # Extract text from commands
        for cmd in self.current_commands:
            if cmd.name in LaTeXParser.SECTIONING_COMMANDS:
                # Section headings
                if cmd.arguments:
                    heading = HeadingElement(
                        content=cmd.arguments[0],
                        level=LaTeXParser.SECTIONING_COMMANDS[cmd.name] + 1,
                        metadata={
                            'line': cmd.line,
                            'column': cmd.column,
                            'command': cmd.name,
                            'raw_content': cmd.raw_content
                        }
                    )
                    text_elements.append(heading)
        
        return text_elements
    
    async def extract_metadata(self, file_path: Union[str, Path]) -> DocumentMetadata:
        """Extract document metadata from LaTeX source."""
        metadata = DocumentMetadata()
        
        # Extract from document commands
        for cmd in self.current_commands:
            if cmd.name == 'title' and cmd.arguments:
                metadata.title = self._clean_text(cmd.arguments[0])
            elif cmd.name == 'author' and cmd.arguments:
                # Parse multiple authors
                authors_str = cmd.arguments[0]
                authors = [self._clean_text(author.strip()) 
                          for author in re.split(r'\\and|,', authors_str)]
                metadata.authors = [author for author in authors if author]
            elif cmd.name == 'date' and cmd.arguments:
                # Try to parse date
                date_str = self._clean_text(cmd.arguments[0])
                if date_str and date_str != r'\today':
                    # Basic year extraction
                    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
                    if year_match:
                        metadata.year = int(year_match.group())
        
        # Extract from document class and packages
        metadata.document_type = self.document_class or "article"
        
        # Extract abstract
        for env in self.current_environments:
            if env.name == 'abstract':
                metadata.abstract = self._clean_text(env.content)
                break
        
        # Extract keywords (if using packages like keywords)
        for env in self.current_environments:
            if env.name in ['keywords', 'keyword']:
                keywords_text = self._clean_text(env.content)
                metadata.keywords = [kw.strip() for kw in keywords_text.split(',')]
                break
        
        # Add processing metadata
        metadata.language = self._detect_language()
        
        return metadata
    
    async def validate_document(self, file_path: Union[str, Path]) -> bool:
        """Validate that the LaTeX document can be processed."""
        path = self._validate_file_path(file_path)
        
        # Check file extension
        if path.suffix.lower() not in ['.tex', '.latex']:
            raise InvalidDocumentError(f"Invalid LaTeX file extension: {path.suffix}")
        
        # Check file size
        self._check_file_size_limit(path, max_size_mb=50)  # LaTeX files should be relatively small
        
        # Try to read file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read(1000)  # Read first 1000 characters
                
            # Basic LaTeX structure validation
            if not re.search(r'\\documentclass', content, re.IGNORECASE):
                logger.warning(f"Document may not be a complete LaTeX file: {path}")
            
            return True
            
        except UnicodeDecodeError:
            # Try different encodings
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    content = f.read(1000)
                logger.info(f"Using latin-1 encoding for file: {path}")
                return True
            except Exception as e:
                raise InvalidDocumentError(f"Cannot read LaTeX file: {e}")
        except Exception as e:
            raise InvalidDocumentError(f"Cannot validate LaTeX file: {e}")
    
    async def _load_document(self, file_path: Path) -> str:
        """Load LaTeX document and handle includes."""
        try:
            # Try UTF-8 first
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        self.current_source = content
        
        # Process includes and inputs
        content = await self._process_includes(content, file_path.parent)
        
        # Extract document class and packages
        self._extract_preamble_info(content)
        
        return content
    
    async def _process_includes(self, content: str, base_dir: Path) -> str:
        """Process \\input and \\include commands."""
        # Find all input/include commands
        include_pattern = re.compile(r'\\(?:input|include)\{([^}]+)\}')
        
        def replace_include(match):
            filename = match.group(1)
            if not filename.endswith('.tex'):
                filename += '.tex'
            
            include_path = base_dir / filename
            if include_path.exists():
                try:
                    with open(include_path, 'r', encoding='utf-8') as f:
                        included_content = f.read()
                    logger.info(f"Included file: {include_path}")
                    return included_content
                except Exception as e:
                    logger.warning(f"Failed to include file {include_path}: {e}")
                    return match.group(0)  # Return original command
            else:
                logger.warning(f"Include file not found: {include_path}")
                return match.group(0)
        
        # Process includes recursively (simple approach, could be improved)
        old_content = ""
        while old_content != content:
            old_content = content
            content = include_pattern.sub(replace_include, content)
        
        return content
    
    def _extract_preamble_info(self, content: str):
        """Extract document class and package information."""
        # Extract document class
        doc_class_match = re.search(r'\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}', content)
        if doc_class_match:
            self.document_class = doc_class_match.group(1)
        
        # Extract packages
        package_matches = re.findall(r'\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}', content)
        self.packages = []
        for package_list in package_matches:
            packages = [pkg.strip() for pkg in package_list.split(',')]
            self.packages.extend(packages)
    
    async def _extract_document_structure(self) -> List[DocumentSection]:
        """Extract hierarchical document structure."""
        sections = []
        current_section_stack = []
        
        for cmd in self.current_commands:
            if cmd.name in LaTeXParser.SECTIONING_COMMANDS:
                level = LaTeXParser.SECTIONING_COMMANDS[cmd.name] + 1
                title = cmd.arguments[0] if cmd.arguments else f"Untitled {cmd.name}"
                
                # Create section
                section = DocumentSection(
                    title=self._clean_text(title),
                    level=level,
                    start_page=None,  # LaTeX doesn't have explicit page info
                    bbox=None
                )
                
                # Handle section hierarchy
                # Pop sections with level >= current level
                while current_section_stack and current_section_stack[-1].level >= level:
                    current_section_stack.pop()
                
                # Add as subsection if we have a parent
                if current_section_stack:
                    current_section_stack[-1].subsections.append(section)
                else:
                    sections.append(section)
                
                current_section_stack.append(section)
        
        return sections
    
    async def _process_equations(self) -> List[EquationElement]:
        """Process mathematical equations and environments."""
        equations = []
        
        # Process math environments
        for env in self.current_environments:
            if env.name in LaTeXParser.MATH_ENVIRONMENTS:
                equation_element = await self._create_equation_element(env)
                if equation_element:
                    equations.append(equation_element)
        
        # Process inline math from tokens
        inline_equations = await self._extract_inline_math()
        equations.extend(inline_equations)
        
        return equations
    
    async def _create_equation_element(self, env: LaTeXEnvironment) -> Optional[EquationElement]:
        """Create equation element from math environment."""
        try:
            # Analyze the environment
            analysis = self.math_analyzer.analyze_environment(env.name, env.content)
            
            # Render equation
            rendered = self.equation_renderer.render_equation(
                env.content, 
                env.name,
                formats=['png', 'plain_text']
            )
            
            # Extract label if present
            label_match = re.search(r'\\label\{([^}]+)\}', env.content)
            label = label_match.group(1) if label_match else None
            
            # Extract equation number (basic approach)
            equation_number = None
            if analysis['is_numbered']:
                # This would need proper equation counter tracking
                equation_number = "(?)"
            
            equation_element = EquationElement(
                content=env.content.strip(),
                latex_code=env.content.strip(),
                equation_type=env.name,
                equation_number=equation_number,
                label=label,
                rendered_image=rendered.png_data,
                mathml=rendered.mathml,
                metadata={
                    'analysis': analysis,
                    'complexity_score': analysis['complexity_score'],
                    'variables': analysis['variables'],
                    'functions': analysis['functions'],
                    'begin_line': env.begin_line,
                    'end_line': env.end_line,
                    'rendered_width': rendered.width,
                    'rendered_height': rendered.height
                }
            )
            
            return equation_element
            
        except Exception as e:
            logger.error(f"Failed to process equation environment {env.name}: {e}")
            return None
    
    async def _extract_inline_math(self) -> List[MathElement]:
        """Extract inline math from tokens."""
        math_elements = []
        i = 0
        
        while i < len(self.current_tokens):
            token = self.current_tokens[i]
            
            if token.type == TokenType.MATH_INLINE and token.content == '$':
                # Find matching closing $
                math_content = ""
                j = i + 1
                
                while j < len(self.current_tokens):
                    next_token = self.current_tokens[j]
                    if next_token.type == TokenType.MATH_INLINE and next_token.content == '$':
                        # Found closing delimiter
                        break
                    math_content += next_token.content
                    j += 1
                
                if j < len(self.current_tokens):
                    # Successfully found matching delimiter
                    try:
                        rendered = self.equation_renderer.render_equation(
                            math_content, 
                            'inline',
                            formats=['png', 'plain_text']
                        )
                        
                        math_element = MathElement(
                            element_type=ElementType.MATH_INLINE,
                            content=math_content.strip(),
                            latex_code=math_content.strip(),
                            math_type='inline',
                            rendered_image=rendered.png_data,
                            mathml=rendered.mathml,
                            metadata={
                                'line': token.line,
                                'column': token.column,
                                'rendered_width': rendered.width,
                                'rendered_height': rendered.height
                            }
                        )
                        
                        math_elements.append(math_element)
                        
                    except Exception as e:
                        logger.warning(f"Failed to render inline math: {math_content[:50]}... Error: {e}")
                    
                    i = j + 1  # Skip to after closing delimiter
                else:
                    i += 1  # Unmatched delimiter, continue
            else:
                i += 1
        
        return math_elements
    
    async def _extract_figures(self) -> List[FigureElement]:
        """Extract figure environments and graphics."""
        figures = []
        
        for env in self.current_environments:
            if env.name in ['figure', 'figure*']:
                figure_element = await self._create_figure_element(env)
                if figure_element:
                    figures.append(figure_element)
        
        return figures
    
    async def _create_figure_element(self, env: LaTeXEnvironment) -> Optional[FigureElement]:
        """Create figure element from figure environment."""
        try:
            # Extract caption
            caption_match = re.search(r'\\caption\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', env.content)
            caption = self._clean_text(caption_match.group(1)) if caption_match else None
            
            # Extract label
            label_match = re.search(r'\\label\{([^}]+)\}', env.content)
            label = label_match.group(1) if label_match else None
            
            # Extract graphics commands
            graphics_matches = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', env.content)
            
            # Try to load image data (basic approach)
            image_data = None
            image_format = None
            if graphics_matches:
                # This would require proper path resolution and image loading
                # For now, just record the filename
                filename = graphics_matches[0]
                
            figure_element = FigureElement(
                content=caption or f"Figure with graphics: {graphics_matches}",
                caption=caption,
                figure_number=None,  # Would need proper counter tracking
                metadata={
                    'graphics_files': graphics_matches,
                    'label': label,
                    'begin_line': env.begin_line,
                    'end_line': env.end_line,
                    'raw_content': env.raw_content
                }
            )
            
            return figure_element
            
        except Exception as e:
            logger.error(f"Failed to process figure environment: {e}")
            return None
    
    async def _extract_tables(self) -> List[TableElement]:
        """Extract table environments."""
        tables = []
        
        for env in self.current_environments:
            if env.name in ['table', 'table*', 'tabular', 'longtable', 'tabularx']:
                table_element = await self._create_table_element(env)
                if table_element:
                    tables.append(table_element)
        
        return tables
    
    async def _create_table_element(self, env: LaTeXEnvironment) -> Optional[TableElement]:
        """Create table element from table environment."""
        try:
            # Extract caption
            caption_match = re.search(r'\\caption\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', env.content)
            caption = self._clean_text(caption_match.group(1)) if caption_match else None
            
            # Extract label
            label_match = re.search(r'\\label\{([^}]+)\}', env.content)
            label = label_match.group(1) if label_match else None
            
            # Basic table parsing (this is quite complex for full LaTeX tables)
            rows = []
            if env.name in ['tabular', 'tabularx']:
                # Extract table rows (simplified)
                content_lines = env.content.split('\\\\')
                for line in content_lines:
                    line = line.strip()
                    if line and not line.startswith('\\'):
                        # Split by & (very basic)
                        cells = [self._clean_text(cell.strip()) for cell in line.split('&')]
                        if cells:
                            rows.append(cells)
            
            table_element = TableElement(
                content=caption or f"Table with {len(rows)} rows",
                caption=caption,
                rows=rows,
                table_number=None,  # Would need proper counter tracking
                metadata={
                    'environment': env.name,
                    'label': label,
                    'begin_line': env.begin_line,
                    'end_line': env.end_line,
                    'raw_content': env.raw_content
                }
            )
            
            return table_element
            
        except Exception as e:
            logger.error(f"Failed to process table environment: {e}")
            return None
    
    async def _process_citations_and_bibliography(self, file_path: Path) -> Tuple[List[CitationElement], List[ReferenceElement]]:
        """Process citations and bibliography."""
        citations = []
        references = []
        
        # Extract citations from source
        latex_citations = self.citation_extractor.extract_citations(self.current_source)
        
        # Look for bibliography files
        bib_files = await self._find_bibliography_files(file_path)
        
        # Parse bibliography files
        for bib_file in bib_files:
            try:
                bib_entries = self.bibtex_parser.parse_file(bib_file)
                self.bibliography.update(bib_entries)
            except Exception as e:
                logger.warning(f"Failed to parse bibliography file {bib_file}: {e}")
        
        # Convert citations to elements
        for latex_citation in latex_citations:
            citation_element = self._create_citation_element(latex_citation)
            if citation_element:
                citations.append(citation_element)
        
        # Convert bibliography entries to reference elements
        for bib_entry in self.bibliography.values():
            reference_element = self._create_reference_element(bib_entry)
            if reference_element:
                references.append(reference_element)
        
        # Resolve citations
        if citations and references:
            resolver = CitationResolver(self.bibliography)
            resolution_stats = resolver.resolve_citations(latex_citations)
            logger.info(f"Citation resolution: {resolution_stats}")
        
        return citations, references
    
    async def _find_bibliography_files(self, file_path: Path) -> List[Path]:
        """Find bibliography files referenced in the document."""
        bib_files = []
        
        # Look for \\bibliography commands
        bib_matches = re.findall(r'\\bibliography\{([^}]+)\}', self.current_source)
        
        for bib_match in bib_matches:
            bib_names = [name.strip() for name in bib_match.split(',')]
            for bib_name in bib_names:
                if not bib_name.endswith('.bib'):
                    bib_name += '.bib'
                
                bib_path = file_path.parent / bib_name
                if bib_path.exists():
                    bib_files.append(bib_path)
                else:
                    logger.warning(f"Bibliography file not found: {bib_path}")
        
        return bib_files
    
    def _create_citation_element(self, citation: Citation) -> Optional[CitationElement]:
        """Create citation element from parsed citation."""
        try:
            citation_element = CitationElement(
                content=citation.raw_content,
                citation_key=citation.citation_key,
                citation_type=citation.citation_type.value,
                page_numbers=citation.postnote if citation.postnote else None,
                metadata={
                    'prenote': citation.prenote,
                    'postnote': citation.postnote,
                    'line': citation.line,
                    'column': citation.column,
                    'multiple_keys': citation.multiple_keys
                }
            )
            
            return citation_element
            
        except Exception as e:
            logger.error(f"Failed to create citation element: {e}")
            return None
    
    def _create_reference_element(self, bib_entry: BibEntry) -> Optional[ReferenceElement]:
        """Create reference element from bibliography entry."""
        try:
            reference_element = ReferenceElement(
                content=bib_entry.raw_entry,
                reference_key=bib_entry.key,
                authors=bib_entry.get_author_names(),
                title=bib_entry.title,
                journal=bib_entry.journal,
                year=bib_entry.year,
                volume=bib_entry.volume,
                issue=bib_entry.number,
                pages=bib_entry.pages,
                doi=bib_entry.doi,
                url=bib_entry.url,
                reference_type=bib_entry.entry_type.value,
                metadata={
                    'booktitle': bib_entry.booktitle,
                    'publisher': bib_entry.publisher,
                    'address': bib_entry.address,
                    'edition': bib_entry.edition,
                    'isbn': bib_entry.isbn,
                    'issn': bib_entry.issn,
                    'note': bib_entry.note,
                    'abstract': bib_entry.abstract,
                    'keywords': bib_entry.keywords,
                    'all_fields': bib_entry.fields
                }
            )
            
            return reference_element
            
        except Exception as e:
            logger.error(f"Failed to create reference element: {e}")
            return None
    
    async def _resolve_cross_references(self):
        """Resolve cross-references in the document."""
        self.cross_ref_resolver.extract_labels(self.current_commands, self.current_environments)
        self.cross_ref_resolver.extract_references(self.current_commands)
        resolved_refs = self.cross_ref_resolver.resolve_references()
        
        logger.info(f"Resolved {len(resolved_refs)} cross-references")
    
    async def _extract_text_from_content(self, content: str, preserve_layout: bool) -> List[DocumentElement]:
        """Extract text elements from LaTeX content."""
        # This is a simplified implementation
        # A full implementation would need proper LaTeX parsing
        
        elements = []
        
        # Clean content
        clean_content = self._clean_text(content)
        
        if clean_content.strip():
            # Split into paragraphs
            paragraphs = re.split(r'\n\s*\n', clean_content)
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if paragraph:
                    element = TextElement(
                        content=paragraph,
                        metadata={'source': 'document_content'}
                    )
                    elements.append(element)
        
        return elements
    
    def _clean_text(self, text: str) -> str:
        """Clean LaTeX text by removing commands and formatting."""
        if not text:
            return ""
        
        # Remove comments
        text = re.sub(r'%.*', '', text)
        
        # Remove common formatting commands
        text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\textit\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\emph\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\texttt\{([^}]+)\}', r'\1', text)
        
        # Remove other common commands
        text = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})*', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _detect_language(self) -> str:
        """Detect document language from packages and content."""
        # Check for babel or polyglossia packages
        for pkg in self.packages:
            if 'babel' in pkg:
                # Extract language from babel options
                lang_match = re.search(r'\\usepackage\[([^\]]*)\]\{babel\}', self.current_source)
                if lang_match:
                    return lang_match.group(1).split(',')[-1].strip()  # Last language is main
            elif 'polyglossia' in pkg:
                # Look for setmainlanguage command
                main_lang_match = re.search(r'\\setmainlanguage\{([^}]+)\}', self.current_source)
                if main_lang_match:
                    return main_lang_match.group(1)
        
        return "english"  # Default