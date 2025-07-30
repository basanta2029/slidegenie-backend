# Document Processing Service

Comprehensive document processing service for SlideGenie, providing advanced PDF analysis capabilities for academic documents.

## Features

### 🔍 **Text Extraction**
- **Layout Preservation**: Maintains original document layout and positioning
- **Multi-column Support**: Correctly handles multi-column academic papers
- **Reading Order Detection**: Intelligently orders text elements for natural flow
- **Font Analysis**: Extracts font information, sizes, and styling

### 📊 **Structure Analysis**
- **Document Sections**: Automatically identifies and organizes document hierarchy
- **Heading Detection**: Recognizes headings and their levels (H1-H6)
- **Layout Analysis**: Detects columns, margins, headers, and footers
- **Region Classification**: Identifies text, figure, table, and other regions

### 🖼️ **Figure & Image Extraction**
- **High-Quality Images**: Extracts figures at configurable DPI
- **Caption Detection**: Links figures with their captions
- **Multiple Formats**: Supports PNG, JPEG, and other image formats
- **Size Filtering**: Filters out decorative elements and icons

### 📋 **Table Processing**
- **Structure Preservation**: Maintains table structure and cell relationships
- **Header Detection**: Identifies table headers and data rows
- **Caption Linking**: Associates tables with their captions
- **Data Cleaning**: Cleans and normalizes table content

### 📚 **Citation & Reference Parsing**
- **Multiple Styles**: Supports APA, MLA, Chicago, IEEE, and other citation styles
- **In-text Citations**: Extracts and parses inline citations
- **Bibliography Processing**: Comprehensive reference list parsing
- **Author Extraction**: Identifies author names and publication years
- **DOI Detection**: Finds and validates DOI links

### 📋 **Metadata Extraction**
- **Document Properties**: Title, authors, creation date, subject
- **Academic Metadata**: Journal, conference, DOI, keywords
- **First Page Analysis**: Extracts title, authors, and abstract from content
- **Affiliation Detection**: Identifies author affiliations and institutions

## Installation

The service requires the following dependencies (already added to `pyproject.toml`):

```toml
pdfplumber = ">=0.11.4,<0.12.0"  # Precise text extraction
pymupdf = ">=1.26.0,<2.0.0"      # Image and advanced PDF processing  
pillow = ">=11.0.0,<12.0.0"      # Image processing
numpy = ">=2.0.0,<3.0.0"         # Numerical operations
```

## Quick Start

```python
import asyncio
from uuid import uuid4
from app.services.document_processing.processors.pdf_processor import PDFProcessor
from app.domain.schemas.document_processing import ProcessingRequest, DocumentType

async def process_pdf():
    # Initialize processor
    processor = PDFProcessor({
        'max_file_size_mb': 50,
        'max_pages': 100,
        'image_dpi': 150,
    })
    
    # Create processing request
    request = ProcessingRequest(
        document_id=uuid4(),
        file_path="/path/to/academic_paper.pdf",
        document_type=DocumentType.PDF,
        extract_text=True,
        extract_figures=True,
        extract_tables=True,
        extract_citations=True,
        extract_references=True,
        extract_metadata=True,
        preserve_layout=True,
        multi_column_handling=True,
    )
    
    # Process document
    result = await processor.process(request)
    
    print(f"Status: {result.status}")
    print(f"Elements extracted: {len(result.elements)}")
    print(f"Figures: {len(result.figures)}")
    print(f"Tables: {len(result.tables)}")
    print(f"Citations: {len(result.citations)}")

# Run processing
asyncio.run(process_pdf())
```

## Configuration Options

### Processor Configuration

```python
config = {
    # File limits
    'max_file_size_mb': 100,      # Maximum file size in MB
    'max_pages': 500,             # Maximum number of pages
    
    # Image processing
    'image_dpi': 150,             # DPI for extracted images
    'min_figure_size': 50,        # Minimum figure size (pixels)
    
    # Performance
    'max_workers': 4,             # Thread pool size
    'enable_ocr': False,          # OCR for scanned documents
    
    # Layout detection
    'column_gap_threshold': 20.0, # Column separation threshold
    'margin_threshold': 50.0,     # Page margin threshold
}
```

### Processing Options

```python
request = ProcessingRequest(
    document_id=uuid4(),
    file_path="document.pdf",
    document_type=DocumentType.PDF,
    
    # Extraction options
    extract_text=True,
    extract_figures=True,
    extract_tables=True,
    extract_citations=True,
    extract_references=True,
    extract_metadata=True,
    
    # Processing options
    preserve_layout=True,         # Maintain positioning info
    multi_column_handling=True,   # Handle multi-column layouts
)
```

## Architecture

### Core Components

```
document_processing/
├── processors/
│   └── pdf_processor.py      # Main PDF processing class
├── utils/
│   ├── text_analysis.py      # Text classification and analysis
│   ├── layout_detector.py    # Layout and structure detection
│   └── citation_parser.py    # Citation and reference parsing
├── base.py                   # Base processor interface
└── example_usage.py          # Usage examples
```

### Data Flow

1. **Document Validation** → Check file integrity and size limits
2. **Metadata Extraction** → Extract document properties and first-page analysis
3. **Text Extraction** → Extract text with precise positioning using pdfplumber
4. **Layout Analysis** → Detect columns, regions, and reading order
5. **Figure Extraction** → Extract images using PyMuPDF
6. **Table Processing** → Extract and structure tabular data
7. **Citation Parsing** → Parse in-text citations and references
8. **Structure Building** → Create hierarchical document structure

### Processing Pipeline

```python
# 1. Initialize processors
processor = PDFProcessor(config)
text_analyzer = TextAnalyzer()
layout_detector = LayoutDetector()
citation_parser = CitationParser()

# 2. Process document
result = await processor.process(request)

# 3. Access results
text_elements = result.elements
figures = result.figures
tables = result.tables
citations = result.citations
references = result.references
layout_info = result.layout_info
sections = result.sections
```

## Data Models

### Core Elements

```python
# Text element with positioning
TextElement(
    content="Academic text content...",
    bbox=BoundingBox(x0=100, y0=200, x1=400, y1=220, page=0),
    style=TextStyle(font_name="Arial", font_size=12, is_bold=False),
    reading_order=1,
    column_index=0
)

# Figure with image data
FigureElement(
    content="Figure 1",
    bbox=BoundingBox(...),
    image_data=b"PNG image data...",
    image_format="png",
    caption="Figure caption text",
    figure_number="1"
)

# Table with structure
TableElement(
    content="Table 1",
    bbox=BoundingBox(...),
    rows=[["Header1", "Header2"], ["Data1", "Data2"]],
    headers=["Header1", "Header2"],
    caption="Table caption text"
)
```

### Processing Result

```python
ProcessingResult(
    document_id=uuid4(),
    status=ProcessingStatus.COMPLETED,
    metadata=DocumentMetadata(...),
    elements=[...],           # All extracted elements
    figures=[...],           # Figure elements
    tables=[...],            # Table elements  
    citations=[...],         # Citation elements
    references=[...],        # Reference elements
    layout_info=[...],       # Layout information per page
    sections=[...],          # Document structure
    processing_time=2.5,     # Processing time in seconds
    warnings=[]              # Any processing warnings
)
```

## Advanced Features

### Multi-Column Layout Handling

The processor automatically detects and handles multi-column academic papers:

```python
# Detect columns
layout_info = processor.layout_detector.analyze_page_layout(elements, page_width, page_height)
columns = layout_info.columns
column_boundaries = layout_info.column_boundaries

# Reading order across columns
ordered_elements = processor.layout_detector.detect_reading_flow(elements)
```

### Citation Style Detection

Automatically detects and parses various citation styles:

```python
# Supported styles
CitationStyle.APA        # (Author, 2023)
CitationStyle.MLA       # (Author 123)
CitationStyle.CHICAGO   # (Author 2023, 45)
CitationStyle.IEEE      # [1], [2-4]
CitationStyle.NUMERIC   # [1], [2,3,4]
CitationStyle.AUTHOR_YEAR # Author (2023)
```

### Text Classification

Automatically classifies text into semantic categories:

```python
TextCategory.TITLE       # Document title
TextCategory.AUTHOR      # Author names
TextCategory.HEADING     # Section headings
TextCategory.PARAGRAPH   # Body paragraphs
TextCategory.CAPTION     # Figure/table captions
TextCategory.REFERENCE   # Bibliography entries
TextCategory.FOOTER      # Page footers
```

## Error Handling

The service provides comprehensive error handling:

```python
# Custom exceptions
DocumentProcessorError      # Base exception
InvalidDocumentError       # Document validation errors
ExtractionError           # Element extraction errors
ProcessingTimeoutError    # Processing timeout errors

# Usage
try:
    result = await processor.process(request)
except InvalidDocumentError as e:
    print(f"Invalid document: {e}")
except ExtractionError as e:
    print(f"Extraction failed: {e}")
```

## Performance Considerations

### Memory Management
- Processes documents page by page to minimize memory usage
- Uses streaming for large documents
- Configurable thread pool for parallel processing

### Processing Speed
- Typical processing time: 1-5 seconds per page
- Multi-threaded image extraction
- Optimized text extraction using pdfplumber
- Configurable DPI for image quality vs. speed trade-off

### File Size Limits
- Default maximum: 100MB files
- Default maximum: 500 pages
- Configurable limits based on available resources

## Testing

Run the example usage script to test the processor:

```bash
cd app/services/document_processing/
python example_usage.py
```

Example test files should be academic PDFs with:
- Multi-column layout
- Figures with captions
- Tables with data
- Citations and references
- Clear document structure

## Integration

### With SlideGenie Pipeline

```python
# In presentation generation service
from app.services.document_processing import PDFProcessor

async def generate_slides_from_pdf(pdf_path: str):
    # Process PDF
    processor = PDFProcessor()
    result = await processor.process_document(pdf_path)
    
    # Extract key content
    sections = result.sections
    figures = result.figures
    tables = result.tables
    
    # Generate slides using AI service
    slides = await ai_service.generate_slides(
        sections=sections,
        figures=figures,
        tables=tables
    )
    
    return slides
```

### With Database Storage

```python
# Store processing results
async def store_document_analysis(result: ProcessingResult):
    # Store metadata
    await metadata_repo.create(result.metadata)
    
    # Store elements
    for element in result.elements:
        await element_repo.create(element)
    
    # Store structure
    for section in result.sections:
        await section_repo.create(section)
```

## Troubleshooting

### Common Issues

1. **Large File Processing**
   - Increase memory limits
   - Process in smaller chunks
   - Reduce image DPI

2. **Multi-column Detection**
   - Adjust `column_gap_threshold`
   - Check text positioning accuracy
   - Verify reading order results

3. **Citation Parsing**
   - Check citation style detection
   - Verify regex patterns
   - Review text preprocessing

4. **Image Extraction Quality**
   - Adjust `image_dpi` setting
   - Check image size filtering
   - Verify image format support

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import structlog

# Configure detailed logging
logger = structlog.get_logger("document_processing")
logger.info("Processing started", document_id=doc_id)
```

## Future Enhancements

### Planned Features
- [ ] OCR support for scanned documents
- [ ] Mathematical equation extraction
- [ ] Enhanced table structure detection
- [ ] Multi-language support
- [ ] Batch processing capabilities
- [ ] Document comparison features

### Performance Improvements
- [ ] GPU acceleration for image processing
- [ ] Distributed processing support
- [ ] Advanced caching mechanisms
- [ ] Stream processing for very large documents

---

For more examples and detailed usage, see `example_usage.py` in this directory.