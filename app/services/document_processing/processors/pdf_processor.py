"""
Comprehensive PDF processor for academic documents.

Uses pdfplumber and PyMuPDF to extract text, figures, tables, citations,
and document structure with advanced layout preservation and multi-column handling.
"""

import asyncio
import io
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from uuid import UUID, uuid4
from datetime import datetime
import concurrent.futures

import structlog
import pdfplumber
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from app.services.document_processing.base import (
    BaseDocumentProcessor,
    ProcessorCapability,
    DocumentProcessorError,
    InvalidDocumentError,
    ExtractionError,
)
from app.services.document_processing.utils.text_analysis import TextAnalyzer, TextCategory
from app.services.document_processing.utils.layout_detector import LayoutDetector, RegionType
from app.services.document_processing.utils.citation_parser import CitationParser, CitationStyle

from app.domain.schemas.document_processing import (
    ProcessingRequest,
    ProcessingResult,
    ProcessingProgress,
    DocumentElement,
    TextElement,
    HeadingElement,
    FigureElement,
    TableElement,
    CitationElement,
    ReferenceElement,
    DocumentMetadata,
    DocumentSection,
    LayoutInfo,
    BoundingBox,
    TextStyle,
    DocumentType,
    ElementType,
    ProcessingStatus,
)

logger = structlog.get_logger(__name__)


class PDFProcessor(BaseDocumentProcessor):
    """
    Comprehensive PDF processor for academic documents.
    
    Combines pdfplumber for precise text extraction and PyMuPDF for
    image processing, providing comprehensive document analysis capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Initialize processors
        self.text_analyzer = TextAnalyzer(config)
        self.layout_detector = LayoutDetector(config)
        self.citation_parser = CitationParser(config)
        
        # Configuration
        self.max_file_size_mb = self.config.get('max_file_size_mb', 100)
        self.max_pages = self.config.get('max_pages', 500)
        self.image_dpi = self.config.get('image_dpi', 150)
        self.min_figure_size = self.config.get('min_figure_size', 50)
        self.enable_ocr = self.config.get('enable_ocr', False)
        
        # Threading
        self.max_workers = self.config.get('max_workers', 4)
        
    @property
    def supported_types(self) -> List[DocumentType]:
        """Return supported document types."""
        return [DocumentType.PDF]
    
    @property
    def capabilities(self) -> Dict[str, ProcessorCapability]:
        """Return processor capabilities."""
        return {
            'text_extraction': ProcessorCapability(
                name="Text Extraction",
                description="Extract text with layout preservation",
                supported=True,
                confidence=0.95
            ),
            'layout_analysis': ProcessorCapability(
                name="Layout Analysis", 
                description="Detect columns, regions, and document structure",
                supported=True,
                confidence=0.9
            ),
            'figure_extraction': ProcessorCapability(
                name="Figure Extraction",
                description="Extract figures and images with captions",
                supported=True,
                confidence=0.85
            ),
            'table_extraction': ProcessorCapability(
                name="Table Extraction",
                description="Extract tables with structure preservation",
                supported=True,
                confidence=0.8
            ),
            'citation_parsing': ProcessorCapability(
                name="Citation Parsing",
                description="Parse in-text citations and references",
                supported=True,
                confidence=0.75
            ),
            'metadata_extraction': ProcessorCapability(
                name="Metadata Extraction",
                description="Extract document metadata and properties",
                supported=True,
                confidence=0.9
            ),
            'multi_column_handling': ProcessorCapability(
                name="Multi-column Handling",
                description="Handle multi-column layouts correctly",
                supported=True,
                confidence=0.85
            ),
        }
    
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """
        Process a PDF document according to request specifications.
        
        Args:
            request: Processing request with options
            
        Returns:
            ProcessingResult with extracted elements
        """
        job_id = uuid4()
        start_time = time.time()
        
        try:
            self._start_job(job_id, total_steps=10)
            
            # Validate document
            file_path = self._validate_file_path(request.file_path)
            await self.validate_document(file_path)
            
            self._update_progress(job_id, 10, "Document validated", 1, 10)
            
            # Initialize result
            result = ProcessingResult(
                document_id=request.document_id,
                document_type=request.document_type,
                status=ProcessingStatus.PROCESSING
            )
            
            # Extract metadata if requested
            if request.extract_metadata:
                self._update_progress(job_id, 20, "Extracting metadata", 2, 10)
                result.metadata = await self.extract_metadata(file_path)
            
            # Extract text elements
            if request.extract_text:
                self._update_progress(job_id, 30, "Extracting text", 3, 10)
                text_elements = await self.extract_text(
                    file_path, 
                    preserve_layout=request.preserve_layout
                )
                result.elements.extend(text_elements)
                
                # Analyze layout if multi-column handling is enabled
                if request.multi_column_handling:
                    self._update_progress(job_id, 40, "Analyzing layout", 4, 10)
                    result.layout_info = await self._extract_layout_info(file_path, text_elements)
                    
                    # Apply reading order detection
                    text_elements = self.layout_detector.detect_reading_flow(text_elements)
            
            # Extract figures if requested
            if request.extract_figures:
                self._update_progress(job_id, 50, "Extracting figures", 5, 10)
                figures = await self._extract_figures(file_path)
                result.figures.extend(figures)
                result.elements.extend(figures)
            
            # Extract tables if requested
            if request.extract_tables:
                self._update_progress(job_id, 60, "Extracting tables", 6, 10)
                tables = await self._extract_tables(file_path)
                result.tables.extend(tables)
                result.elements.extend(tables)
            
            # Parse citations if requested
            if request.extract_citations:
                self._update_progress(job_id, 70, "Parsing citations", 7, 10)
                citations = await self._extract_citations(text_elements)
                result.citations.extend(citations)
                result.elements.extend(citations)
            
            # Parse references if requested
            if request.extract_references:
                self._update_progress(job_id, 80, "Parsing references", 8, 10)
                references = await self._extract_references(file_path)
                result.references.extend(references)
                result.elements.extend(references)
            
            # Build document structure
            self._update_progress(job_id, 90, "Building document structure", 9, 10)
            result.sections = await self._build_document_structure(result.elements)
            
            # Finalize result
            result.status = ProcessingStatus.COMPLETED
            result.processing_time = time.time() - start_time
            
            self._complete_job(job_id, success=True)
            self._update_progress(job_id, 100, "Processing complete", 10, 10, ProcessingStatus.COMPLETED)
            
            return result
            
        except Exception as e:
            error_msg = f"PDF processing failed: {str(e)}"
            self.logger.error("pdf_processing_failed", error=error_msg, job_id=str(job_id))
            
            self._complete_job(job_id, success=False, error=error_msg)
            
            return ProcessingResult(
                document_id=request.document_id,
                document_type=request.document_type,
                status=ProcessingStatus.FAILED,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )
    
    async def extract_text(
        self, 
        file_path: Union[str, Path], 
        preserve_layout: bool = True
    ) -> List[DocumentElement]:
        """
        Extract text elements with layout preservation.
        
        Args:
            file_path: Path to PDF file
            preserve_layout: Whether to preserve layout information
            
        Returns:
            List of text elements with positioning
        """
        file_path = self._validate_file_path(file_path)
        elements = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_elements = await self._extract_page_text(
                        page, page_num, preserve_layout
                    )
                    elements.extend(page_elements)
                    
        except Exception as e:
            raise ExtractionError(f"Text extraction failed: {str(e)}")
        
        # Classify and analyze text elements
        if elements:
            # Classify text elements
            clusters = self.text_analyzer.classify_text_elements(elements)
            
            # Update elements with classifications
            for cluster in clusters:
                for element in cluster.elements:
                    if cluster.category == TextCategory.HEADING:
                        # Convert to heading element
                        level = self._determine_heading_level(element, clusters)
                        heading = HeadingElement(
                            content=element.content,
                            bbox=element.bbox,
                            style=element.style,
                            level=level,
                            reading_order=element.reading_order,
                            column_index=element.column_index
                        )
                        # Replace in list
                        if element in elements:
                            idx = elements.index(element)
                            elements[idx] = heading
            
            # Detect reading order
            elements = self.text_analyzer.detect_reading_order(elements)
        
        return elements
    
    async def extract_metadata(self, file_path: Union[str, Path]) -> DocumentMetadata:
        """
        Extract document metadata from PDF.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            DocumentMetadata object
        """
        file_path = self._validate_file_path(file_path)
        metadata = DocumentMetadata()
        
        try:
            # Extract metadata using PyMuPDF
            with fitz.open(file_path) as doc:
                pdf_metadata = doc.metadata
                
                # Basic metadata
                metadata.title = pdf_metadata.get('title')
                metadata.subject = pdf_metadata.get('subject')
                metadata.creation_date = self._parse_pdf_date(pdf_metadata.get('creationDate'))
                metadata.modification_date = self._parse_pdf_date(pdf_metadata.get('modDate'))
                
                # Extract additional metadata from first page
                if len(doc) > 0:
                    first_page_metadata = await self._extract_first_page_metadata(doc[0])
                    metadata.title = metadata.title or first_page_metadata.get('title')
                    metadata.authors = first_page_metadata.get('authors', [])
                    metadata.affiliations = first_page_metadata.get('affiliations', [])
                    metadata.abstract = first_page_metadata.get('abstract')
                    metadata.keywords = first_page_metadata.get('keywords', [])
                    metadata.doi = first_page_metadata.get('doi')
                    
        except Exception as e:
            self.logger.warning("metadata_extraction_partial_failure", error=str(e))
        
        return metadata
    
    async def validate_document(self, file_path: Union[str, Path]) -> bool:
        """
        Validate PDF document.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            True if valid
            
        Raises:
            InvalidDocumentError: If invalid
        """
        file_path = self._validate_file_path(file_path)
        
        # Check file size
        self._check_file_size_limit(file_path, self.max_file_size_mb)
        
        # Try to open with both libraries
        try:
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) == 0:
                    raise InvalidDocumentError("PDF has no pages")
                
                if len(pdf.pages) > self.max_pages:
                    raise InvalidDocumentError(f"PDF has too many pages: {len(pdf.pages)} (max: {self.max_pages})")
            
            with fitz.open(file_path) as doc:
                if doc.is_encrypted:
                    raise InvalidDocumentError("PDF is encrypted")
                
                if doc.page_count != len(pdf.pages):
                    self.logger.warning("page_count_mismatch", 
                                      pdfplumber=len(pdf.pages), 
                                      pymupdf=doc.page_count)
                    
        except Exception as e:
            if isinstance(e, InvalidDocumentError):
                raise
            raise InvalidDocumentError(f"Invalid PDF: {str(e)}")
        
        return True
    
    async def _extract_page_text(
        self, 
        page: pdfplumber.page.Page, 
        page_num: int, 
        preserve_layout: bool
    ) -> List[TextElement]:
        """Extract text elements from a single page."""
        elements = []
        
        try:
            if preserve_layout:
                # Use character-level extraction for precise layout
                chars = page.chars
                
                if chars:
                    # Group characters into words and lines
                    words = self._group_chars_to_words(chars)
                    lines = self._group_words_to_lines(words)
                    
                    for line in lines:
                        if line['text'].strip():
                            element = TextElement(
                                content=line['text'],
                                bbox=BoundingBox(
                                    x0=line['x0'],
                                    y0=line['y0'],
                                    x1=line['x1'],
                                    y1=line['y1'],
                                    page=page_num
                                ),
                                style=TextStyle(
                                    font_name=line.get('fontname'),
                                    font_size=line.get('size'),
                                    is_bold='Bold' in (line.get('fontname', '') or ''),
                                    is_italic='Italic' in (line.get('fontname', '') or ''),
                                ),
                                line_height=line['y1'] - line['y0']
                            )
                            elements.append(element)
            else:
                # Simple text extraction
                text = page.extract_text()
                if text and text.strip():
                    element = TextElement(
                        content=text.strip(),
                        bbox=BoundingBox(
                            x0=0, y0=0, 
                            x1=page.width, y1=page.height,
                            page=page_num
                        )
                    )
                    elements.append(element)
                    
        except Exception as e:
            self.logger.warning("page_text_extraction_failed", 
                              page=page_num, error=str(e))
        
        return elements
    
    async def _extract_figures(self, file_path: Path) -> List[FigureElement]:
        """Extract figures from PDF."""
        figures = []
        
        try:
            with fitz.open(file_path) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    
                    # Get image list
                    image_list = page.get_images()
                    
                    for img_index, img in enumerate(image_list):
                        try:
                            # Extract image
                            xref = img[0]
                            pix = fitz.Pixmap(doc, xref)
                            
                            # Skip very small images
                            if pix.width < self.min_figure_size or pix.height < self.min_figure_size:
                                pix = None
                                continue
                            
                            # Convert to bytes
                            if pix.n - pix.alpha < 4:  # GRAY or RGB
                                img_data = pix.tobytes("png")
                                img_format = "png"
                            else:  # CMYK: convert to RGB first
                                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                                img_data = pix1.tobytes("png")
                                img_format = "png"
                                pix1 = None
                            
                            # Get image rectangle on page
                            img_rects = page.get_image_rects(xref)
                            
                            if img_rects:
                                rect = img_rects[0]  # Use first occurrence
                                
                                figure = FigureElement(
                                    content=f"Figure {len(figures) + 1}",
                                    bbox=BoundingBox(
                                        x0=rect.x0,
                                        y0=rect.y0,
                                        x1=rect.x1,
                                        y1=rect.y1,
                                        page=page_num
                                    ),
                                    image_data=img_data,
                                    image_format=img_format,
                                    figure_number=str(len(figures) + 1)
                                )
                                figures.append(figure)
                            
                            pix = None
                            
                        except Exception as e:
                            self.logger.warning("figure_extraction_failed",
                                              page=page_num, image=img_index, error=str(e))
                            
        except Exception as e:
            self.logger.error("figures_extraction_failed", error=str(e))
        
        return figures
    
    async def _extract_tables(self, file_path: Path) -> List[TableElement]:
        """Extract tables from PDF."""
        tables = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Extract tables using pdfplumber
                        page_tables = page.extract_tables()
                        
                        for table_index, table_data in enumerate(page_tables):
                            if table_data and len(table_data) > 1:  # At least header + 1 row
                                # Get table bounding box
                                table_bbox = self._calculate_table_bbox(page, table_data)
                                
                                # Clean table data
                                cleaned_rows = []
                                headers = None
                                
                                for row_index, row in enumerate(table_data):
                                    if row and any(cell for cell in row if cell and cell.strip()):
                                        cleaned_row = [cell.strip() if cell else "" for cell in row]
                                        if row_index == 0 and not headers:
                                            headers = cleaned_row
                                        else:
                                            cleaned_rows.append(cleaned_row)
                                
                                if cleaned_rows:
                                    table = TableElement(
                                        content=f"Table {len(tables) + 1}",
                                        bbox=table_bbox,
                                        rows=cleaned_rows,
                                        headers=headers,
                                        table_number=str(len(tables) + 1)
                                    )
                                    tables.append(table)
                                    
                    except Exception as e:
                        self.logger.warning("table_extraction_failed",
                                          page=page_num, error=str(e))
                        
        except Exception as e:
            self.logger.error("tables_extraction_failed", error=str(e))
        
        return tables
    
    async def _extract_citations(self, text_elements: List[TextElement]) -> List[CitationElement]:
        """Extract citations from text elements."""
        citations = []
        
        for element in text_elements:
            try:
                element_citations = self.citation_parser.parse_citations(
                    element.content, element.bbox
                )
                citations.extend(element_citations)
            except Exception as e:
                self.logger.warning("citation_extraction_failed", 
                                  element_id=str(element.id), error=str(e))
        
        return citations
    
    async def _extract_references(self, file_path: Path) -> List[ReferenceElement]:
        """Extract references from PDF."""
        references = []
        
        try:
            # Find references section
            with pdfplumber.open(file_path) as pdf:
                reference_lines = []
                in_references = False
                
                for page in pdf.pages:
                    text_lines = page.extract_text().split('\n')
                    
                    for line in text_lines:
                        line = line.strip()
                        
                        # Check if we've entered references section
                        if not in_references:
                            if any(keyword in line.lower() for keyword in 
                                  ['references', 'bibliography', 'works cited', 'literature cited']):
                                in_references = True
                                continue
                        
                        # If in references, collect lines
                        if in_references and line:
                            # Stop if we hit a new major section
                            if (line.lower().startswith(('appendix', 'acknowledgment', 'index'))
                                and len(line.split()) < 5):
                                break
                            reference_lines.append(line)
                
                # Parse reference lines
                if reference_lines:
                    references = self.citation_parser.parse_references(reference_lines)
                    
        except Exception as e:
            self.logger.error("references_extraction_failed", error=str(e))
        
        return references
    
    async def _extract_layout_info(
        self, 
        file_path: Path, 
        text_elements: List[TextElement]
    ) -> List[LayoutInfo]:
        """Extract layout information for each page."""
        layout_info = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Get elements for this page
                    page_elements = [elem for elem in text_elements 
                                   if elem.bbox and elem.bbox.page == page_num]
                    
                    if page_elements:
                        layout = self.layout_detector.analyze_page_layout(
                            page_elements, page.width, page.height
                        )
                        layout_info.append(layout)
                        
        except Exception as e:
            self.logger.warning("layout_analysis_failed", error=str(e))
        
        return layout_info
    
    async def _build_document_structure(
        self, 
        elements: List[DocumentElement]
    ) -> List[DocumentSection]:
        """Build hierarchical document structure."""
        sections = []
        
        # Find heading elements
        headings = [elem for elem in elements 
                   if isinstance(elem, HeadingElement)]
        
        if not headings:
            # Create a single section with all elements
            main_section = DocumentSection(
                title="Document Content",
                level=1,
                elements=elements
            )
            sections.append(main_section)
            return sections
        
        # Sort headings by reading order
        headings.sort(key=lambda h: h.reading_order or 0)
        
        # Build hierarchy
        current_sections = {}  # level -> section
        
        for heading in headings:
            # Create section for this heading
            section = DocumentSection(
                title=heading.content,
                level=heading.level,
                section_number=getattr(heading, 'section_number', None),
                start_page=heading.bbox.page if heading.bbox else None
            )
            
            # Find parent section
            parent_level = heading.level - 1
            if parent_level > 0 and parent_level in current_sections:
                parent = current_sections[parent_level]
                parent.subsections.append(section)
            else:
                sections.append(section)
            
            # Update current sections at this level and remove deeper levels
            current_sections[heading.level] = section
            levels_to_remove = [level for level in current_sections.keys() 
                              if level > heading.level]
            for level in levels_to_remove:
                del current_sections[level]
        
        # Assign elements to sections
        self._assign_elements_to_sections(sections, elements)
        
        return sections
    
    def _group_chars_to_words(self, chars: List[Dict]) -> List[Dict]:
        """Group characters into words."""
        if not chars:
            return []
        
        words = []
        current_word = {
            'chars': [],
            'text': '',
            'x0': float('inf'),
            'y0': float('inf'),
            'x1': 0,
            'y1': 0,
        }
        
        for char in chars:
            # Check if this character should start a new word
            if (current_word['chars'] and 
                (char.get('text', '').isspace() or 
                 abs(char.get('x0', 0) - current_word['x1']) > 3)):  # Gap threshold
                
                if current_word['text'].strip():
                    # Finalize current word
                    current_word['text'] = current_word['text'].strip()
                    words.append(current_word)
                
                # Start new word
                current_word = {
                    'chars': [],
                    'text': '',
                    'x0': float('inf'),
                    'y0': float('inf'),
                    'x1': 0,
                    'y1': 0,
                }
            
            # Add character to current word if not whitespace
            if not char.get('text', '').isspace():
                current_word['chars'].append(char)
                current_word['text'] += char.get('text', '')
                current_word['x0'] = min(current_word['x0'], char.get('x0', 0))
                current_word['y0'] = min(current_word['y0'], char.get('y0', 0))
                current_word['x1'] = max(current_word['x1'], char.get('x1', 0))
                current_word['y1'] = max(current_word['y1'], char.get('y1', 0))
                
                # Copy font information from first character
                if len(current_word['chars']) == 1:
                    current_word['fontname'] = char.get('fontname')
                    current_word['size'] = char.get('size')
        
        # Add final word
        if current_word['text'].strip():
            current_word['text'] = current_word['text'].strip()
            words.append(current_word)
        
        return words
    
    def _group_words_to_lines(self, words: List[Dict]) -> List[Dict]:
        """Group words into lines."""
        if not words:
            return []
        
        lines = []
        current_line = {
            'words': [],
            'text': '',
            'x0': float('inf'),
            'y0': float('inf'),
            'x1': 0,
            'y1': 0,
        }
        
        for word in words:
            # Check if this word should start a new line
            if (current_line['words'] and
                abs(word.get('y0', 0) - current_line['y0']) > 5):  # Line height threshold
                
                if current_line['text'].strip():
                    # Finalize current line
                    current_line['text'] = current_line['text'].strip()
                    lines.append(current_line)
                
                # Start new line
                current_line = {
                    'words': [],
                    'text': '',
                    'x0': float('inf'),
                    'y0': float('inf'),
                    'x1': 0,
                    'y1': 0,
                }
            
            # Add word to current line
            current_line['words'].append(word)
            if current_line['text']:
                current_line['text'] += ' '
            current_line['text'] += word.get('text', '')
            current_line['x0'] = min(current_line['x0'], word.get('x0', 0))
            current_line['y0'] = min(current_line['y0'], word.get('y0', 0))
            current_line['x1'] = max(current_line['x1'], word.get('x1', 0))
            current_line['y1'] = max(current_line['y1'], word.get('y1', 0))
            
            # Copy font information from first word
            if len(current_line['words']) == 1:
                current_line['fontname'] = word.get('fontname')
                current_line['size'] = word.get('size')
        
        # Add final line
        if current_line['text'].strip():
            current_line['text'] = current_line['text'].strip()
            lines.append(current_line)
        
        return lines
    
    def _determine_heading_level(
        self, 
        element: TextElement, 
        clusters: List
    ) -> int:
        """Determine heading level based on font size and style."""
        if not element.style or not element.style.font_size:
            return 1
        
        # Get all font sizes in document
        font_sizes = []
        for cluster in clusters:
            for elem in cluster.elements:
                if elem.style and elem.style.font_size:
                    font_sizes.append(elem.style.font_size)
        
        if not font_sizes:
            return 1
        
        font_sizes.sort(reverse=True)  # Largest first
        unique_sizes = sorted(list(set(font_sizes)), reverse=True)
        
        # Assign levels based on font size ranking
        element_size = element.style.font_size
        try:
            level = unique_sizes.index(element_size) + 1
            return min(level, 6)  # Max level 6
        except ValueError:
            return 1
    
    def _calculate_table_bbox(self, page, table_data: List[List]) -> BoundingBox:
        """Calculate bounding box for a table."""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated table detection
        
        page_height = page.height
        page_width = page.width
        
        # Estimate table position (simplified)
        x0 = page_width * 0.1  # 10% from left
        x1 = page_width * 0.9  # 90% from left
        y0 = page_height * 0.3  # Estimated position
        y1 = y0 + len(table_data) * 20  # Estimated height
        
        return BoundingBox(
            x0=x0, y0=y0, x1=x1, y1=y1,
            page=0  # Would need actual page number
        )
    
    def _parse_pdf_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse PDF date string."""
        if not date_str:
            return None
        
        try:
            # PDF date format: D:YYYYMMDDHHmmSSOHH'mm
            if date_str.startswith('D:'):
                date_str = date_str[2:]
            
            # Extract basic date part
            if len(date_str) >= 8:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                return datetime(year, month, day)
                
        except (ValueError, IndexError):
            pass
        
        return None
    
    async def _extract_first_page_metadata(self, page) -> Dict[str, Any]:
        """Extract metadata from first page text."""
        metadata = {}
        
        try:
            # Get text blocks from first page
            blocks = page.get_text("dict")["blocks"]
            
            text_blocks = []
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span.get("text", "").strip():
                                text_blocks.append({
                                    'text': span["text"].strip(),
                                    'size': span.get("size", 12),
                                    'flags': span.get("flags", 0),
                                    'y': span.get("bbox", [0,0,0,0])[1]
                                })
            
            # Sort by y-coordinate (top to bottom)
            text_blocks.sort(key=lambda x: -x['y'])
            
            # Extract title (usually largest text at top)
            if text_blocks:
                largest_size = max(block['size'] for block in text_blocks[:5])  # Check first 5 blocks
                title_candidates = [block for block in text_blocks[:5] 
                                  if block['size'] >= largest_size * 0.9]
                
                if title_candidates:
                    metadata['title'] = title_candidates[0]['text']
            
            # Extract authors, DOI, etc. from text
            full_text = '\n'.join(block['text'] for block in text_blocks[:20])  # First 20 blocks
            
            # Look for authors
            metadata['authors'] = self.citation_parser.extract_author_names(full_text)
            
            # Look for DOI
            doi_match = re.search(r'(?:doi:?\s*)?10\.[0-9]+\/[^\s]+', full_text, re.IGNORECASE)
            if doi_match:
                metadata['doi'] = doi_match.group(0).replace('doi:', '').strip()
            
            # Look for abstract
            abstract_match = re.search(r'abstract[:\-\s]*([^.]+(?:\.[^.]+)*)', 
                                     full_text, re.IGNORECASE | re.DOTALL)
            if abstract_match:
                metadata['abstract'] = abstract_match.group(1)[:500]  # Limit length
                
        except Exception as e:
            self.logger.warning("first_page_metadata_extraction_failed", error=str(e))
        
        return metadata
    
    def _assign_elements_to_sections(
        self, 
        sections: List[DocumentSection], 
        elements: List[DocumentElement]
    ) -> None:
        """Assign elements to appropriate sections."""
        # This is a simplified implementation
        # In practice, you'd use more sophisticated logic based on reading order and positions
        
        if not sections:
            return
        
        # For now, assign all elements to the first section
        if sections:
            sections[0].elements = elements