"""
Domain schemas for document processing services.

Defines data models for PDF processing results, extracted elements,
and document structure analysis.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel, Field, validator


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"
    LATEX = "latex"


class ElementType(str, Enum):
    """Types of document elements that can be extracted."""
    TEXT = "text"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    FIGURE = "figure"
    TABLE = "table"
    CAPTION = "caption"
    CITATION = "citation"
    REFERENCE = "reference"
    FOOTER = "footer"
    HEADER = "header"
    EQUATION = "equation"
    LIST = "list"
    MATH_INLINE = "math_inline"
    MATH_DISPLAY = "math_display"
    THEOREM = "theorem"
    PROOF = "proof"
    DEFINITION = "definition"
    LEMMA = "lemma"
    COROLLARY = "corollary"
    ENVIRONMENT = "environment"
    COMMAND = "command"


class ProcessingStatus(str, Enum):
    """Processing status for documents."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BoundingBox(BaseModel):
    """Bounding box coordinates for document elements."""
    x0: float = Field(..., description="Left coordinate")
    y0: float = Field(..., description="Bottom coordinate") 
    x1: float = Field(..., description="Right coordinate")
    y1: float = Field(..., description="Top coordinate")
    page: int = Field(..., ge=0, description="Page number (0-indexed)")
    
    @property
    def width(self) -> float:
        """Width of the bounding box."""
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        """Height of the bounding box."""
        return self.y1 - self.y0
    
    @property
    def center(self) -> tuple[float, float]:
        """Center coordinates of the bounding box."""
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)
    
    def overlaps(self, other: "BoundingBox") -> bool:
        """Check if this bounding box overlaps with another."""
        if self.page != other.page:
            return False
        return not (self.x1 < other.x0 or other.x1 < self.x0 or 
                   self.y1 < other.y0 or other.y1 < self.y0)


class TextStyle(BaseModel):
    """Text styling information."""
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: Optional[str] = None  # normal, bold
    font_style: Optional[str] = None   # normal, italic
    color: Optional[str] = None        # hex color code
    is_bold: bool = False
    is_italic: bool = False
    is_underlined: bool = False


class DocumentElement(BaseModel):
    """Base class for all document elements."""
    id: UUID = Field(default_factory=uuid4)
    element_type: ElementType
    content: str
    bbox: Optional[BoundingBox] = None
    style: Optional[TextStyle] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class TextElement(DocumentElement):
    """Text element with layout information."""
    element_type: ElementType = ElementType.TEXT
    reading_order: Optional[int] = None
    column_index: Optional[int] = None
    line_height: Optional[float] = None
    words_bbox: List[BoundingBox] = Field(default_factory=list)


class HeadingElement(TextElement):
    """Heading element with hierarchy information."""
    element_type: ElementType = ElementType.HEADING
    level: int = Field(..., ge=1, le=6, description="Heading level (1-6)")
    section_number: Optional[str] = None


class FigureElement(DocumentElement):
    """Figure/image element."""
    element_type: ElementType = ElementType.FIGURE
    image_data: Optional[bytes] = None
    image_format: Optional[str] = None  # png, jpg, etc.
    caption: Optional[str] = None
    caption_bbox: Optional[BoundingBox] = None
    figure_number: Optional[str] = None
    referenced_from: List[str] = Field(default_factory=list)  # page references


class TableElement(DocumentElement):
    """Table element with structure information."""
    element_type: ElementType = ElementType.TABLE
    rows: List[List[str]] = Field(default_factory=list)
    headers: Optional[List[str]] = None
    caption: Optional[str] = None
    caption_bbox: Optional[BoundingBox] = None
    table_number: Optional[str] = None
    referenced_from: List[str] = Field(default_factory=list)


class CitationElement(DocumentElement):
    """In-text citation element."""
    element_type: ElementType = ElementType.CITATION
    citation_key: Optional[str] = None
    citation_type: Optional[str] = None  # numeric, author-year, etc.
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    page_numbers: Optional[str] = None


class ReferenceElement(DocumentElement):
    """Bibliography reference element."""
    element_type: ElementType = ElementType.REFERENCE
    reference_key: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    title: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    reference_type: Optional[str] = None  # journal, book, conference, etc.


class EquationElement(DocumentElement):
    """Mathematical equation element."""
    element_type: ElementType = ElementType.EQUATION
    latex_code: str
    equation_type: str = "display"  # inline, display, align, etc.
    equation_number: Optional[str] = None
    label: Optional[str] = None
    referenced_from: List[str] = Field(default_factory=list)
    rendered_image: Optional[bytes] = None
    mathml: Optional[str] = None


class MathElement(DocumentElement):
    """Inline or display math element."""
    element_type: ElementType = ElementType.MATH_INLINE
    latex_code: str
    math_type: str = "inline"  # inline, display
    rendered_image: Optional[bytes] = None
    mathml: Optional[str] = None


class TheoremElement(DocumentElement):
    """Theorem-like environment element."""
    element_type: ElementType = ElementType.THEOREM
    theorem_type: str  # theorem, lemma, corollary, definition, etc.
    theorem_number: Optional[str] = None
    theorem_name: Optional[str] = None
    label: Optional[str] = None
    referenced_from: List[str] = Field(default_factory=list)


class LaTeXEnvironmentElement(DocumentElement):
    """Generic LaTeX environment element."""
    element_type: ElementType = ElementType.ENVIRONMENT
    environment_name: str
    environment_args: List[str] = Field(default_factory=list)
    environment_options: Dict[str, str] = Field(default_factory=dict)
    raw_content: str
    label: Optional[str] = None


class LaTeXCommandElement(DocumentElement):
    """LaTeX command element."""
    element_type: ElementType = ElementType.COMMAND
    command_name: str
    arguments: List[str] = Field(default_factory=list)
    optional_args: Dict[str, str] = Field(default_factory=dict)
    raw_command: str


class DocumentSection(BaseModel):
    """Document section with hierarchical structure."""
    id: UUID = Field(default_factory=uuid4)
    title: str
    level: int = Field(..., ge=1, description="Section hierarchy level")
    section_number: Optional[str] = None
    elements: List[DocumentElement] = Field(default_factory=list)
    subsections: List["DocumentSection"] = Field(default_factory=list)
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    bbox: Optional[BoundingBox] = None


class DocumentMetadata(BaseModel):
    """Document metadata extracted from PDF."""
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    affiliations: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    subject: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    conference: Optional[str] = None
    pages: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    year: Optional[int] = None
    language: Optional[str] = None
    document_type: Optional[str] = None  # research paper, thesis, report, etc.


class LayoutInfo(BaseModel):
    """Layout information for a document page."""
    page_number: int = Field(..., ge=0)
    page_width: float
    page_height: float
    columns: int = Field(default=1, ge=1)
    column_boundaries: List[tuple[float, float]] = Field(default_factory=list)
    text_regions: List[BoundingBox] = Field(default_factory=list)
    figure_regions: List[BoundingBox] = Field(default_factory=list)
    table_regions: List[BoundingBox] = Field(default_factory=list)
    header_region: Optional[BoundingBox] = None
    footer_region: Optional[BoundingBox] = None
    margins: Dict[str, float] = Field(default_factory=dict)  # top, bottom, left, right


class ProcessingResult(BaseModel):
    """Complete document processing result."""
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    document_type: DocumentType
    status: ProcessingStatus
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    sections: List[DocumentSection] = Field(default_factory=list)
    elements: List[DocumentElement] = Field(default_factory=list)
    figures: List[FigureElement] = Field(default_factory=list)
    tables: List[TableElement] = Field(default_factory=list)
    citations: List[CitationElement] = Field(default_factory=list)
    references: List[ReferenceElement] = Field(default_factory=list)
    layout_info: List[LayoutInfo] = Field(default_factory=list)
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class ProcessingRequest(BaseModel):
    """Request for document processing."""
    document_id: UUID
    file_path: str
    document_type: DocumentType
    options: Dict[str, Any] = Field(default_factory=dict)
    extract_text: bool = True
    extract_figures: bool = True
    extract_tables: bool = True
    extract_citations: bool = True
    extract_references: bool = True
    extract_metadata: bool = True
    preserve_layout: bool = True
    multi_column_handling: bool = True
    
    class Config:
        use_enum_values = True


class ProcessingProgress(BaseModel):
    """Processing progress information."""
    job_id: UUID
    status: ProcessingStatus
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    current_step: str
    total_steps: int
    completed_steps: int
    estimated_time_remaining: Optional[float] = None
    error_message: Optional[str] = None
    started_at: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


# Update forward references
DocumentSection.model_rebuild()