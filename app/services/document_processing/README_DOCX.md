# DOCX Processor for Academic Documents

A comprehensive DOCX document processor designed specifically for academic documents, providing advanced text extraction, formatting preservation, and structural analysis capabilities.

## Features

### Core Capabilities

- **Text Extraction with Style Preservation**: Extract text while maintaining formatting (bold, italic, underline, fonts, colors)
- **Document Structure Analysis**: Hierarchical heading detection, section organization, and cross-reference resolution
- **Table Extraction**: Complete table structure with headers, cell content, and formatting
- **Figure and Media Extraction**: Embedded images, captions, and figure numbering
- **Citation Detection**: Multiple citation formats (APA, MLA, IEEE, numeric, author-year)
- **Reference Parsing**: Bibliography extraction with author, title, journal, and publication details
- **Metadata Extraction**: Document properties, author information, keywords, and abstracts
- **Advanced Features**: Comments, track changes, embedded objects, and custom properties

### Supported Document Elements

- Headings and section hierarchy
- Paragraphs with full formatting
- Tables with complex structures
- Figures and embedded images
- In-text citations
- Bibliography references
- Headers and footers
- Comments and annotations
- Track changes and revisions
- Mathematical equations (basic)
- Lists and enumerations

## Installation

The DOCX processor requires the `python-docx` and `lxml` libraries:

```bash
pip install python-docx>=1.1.2 lxml>=5.3.0
```

These dependencies are included in the project's `pyproject.toml` file.

## Usage

### Basic Usage

```python
import asyncio
from pathlib import Path
from uuid import uuid4

from app.services.document_processing.processors.docx_processor import DOCXProcessor
from app.domain.schemas.document_processing import ProcessingRequest, DocumentType

async def process_docx_document():
    # Initialize processor
    processor = DOCXProcessor()
    
    # Create processing request
    request = ProcessingRequest(
        document_id=uuid4(),
        file_path="path/to/document.docx",
        document_type=DocumentType.DOCX,
        extract_text=True,
        extract_tables=True,
        extract_figures=True,
        extract_citations=True,
        extract_references=True,
        extract_metadata=True
    )
    
    # Process document
    result = await processor.process(request)
    
    # Access results
    print(f"Title: {result.metadata.title}")
    print(f"Authors: {', '.join(result.metadata.authors)}")
    print(f"Sections: {len(result.sections)}")
    print(f"Tables: {len(result.tables)}")
    print(f"Citations: {len(result.citations)}")

# Run the example
asyncio.run(process_docx_document())
```

### Advanced Configuration

```python
# Configure processor with custom settings
config = {
    'max_file_size_mb': 100,
    'extract_images': True,
    'extract_embedded_objects': True,
    'process_comments': True,
    'process_track_changes': True,
    'preserve_styles': True,
    'max_workers': 4
}

processor = DOCXProcessor(config)
```

### Text Extraction Only

```python
# Extract text with formatting
elements = await processor.extract_text("document.docx", preserve_layout=True)

# Process elements
for element in elements:
    print(f"Type: {element.element_type}")
    print(f"Content: {element.content}")
    if element.style:
        print(f"Font: {element.style.font_name}")
        print(f"Bold: {element.style.is_bold}")
        print(f"Italic: {element.style.is_italic}")
```

### Metadata Extraction

```python
# Extract document metadata
metadata = await processor.extract_metadata("document.docx")

print(f"Title: {metadata.title}")
print(f"Authors: {metadata.authors}")
print(f"Keywords: {metadata.keywords}")
print(f"Abstract: {metadata.abstract}")
print(f"Creation Date: {metadata.creation_date}")
print(f"Document Type: {metadata.document_type}")
```

## Processing Results

### Document Structure

The processor organizes content into a hierarchical structure:

```python
# Access document sections
for section in result.sections:
    print(f"Section: {section.title} (Level {section.level})")
    print(f"Elements: {len(section.elements)}")
    
    # Access subsections
    for subsection in section.subsections:
        print(f"  Subsection: {subsection.title} (Level {subsection.level})")
```

### Table Data

```python
# Process extracted tables
for table in result.tables:
    print(f"Table {table.table_number}: {table.caption}")
    print(f"Headers: {table.headers}")
    print(f"Rows: {len(table.rows)}")
    
    # Access table data
    for row in table.rows:
        print(" | ".join(row))
```

### Citations and References

```python
# Process citations
for citation in result.citations:
    print(f"Citation: {citation.content}")
    print(f"Authors: {citation.authors}")
    print(f"Year: {citation.year}")

# Process references
for reference in result.references:
    print(f"Reference: {reference.title}")
    print(f"Authors: {reference.authors}")
    print(f"Journal: {reference.journal}")
    print(f"DOI: {reference.doi}")
```

### Figure Extraction

```python
# Process extracted figures
for figure in result.figures:
    print(f"Figure {figure.figure_number}: {figure.caption}")
    print(f"Format: {figure.image_format}")
    print(f"Size: {len(figure.image_data)} bytes")
    
    # Save image data
    with open(f"figure_{figure.figure_number}.{figure.image_format}", "wb") as f:
        f.write(figure.image_data)
```

## Academic Document Features

### Citation Formats Supported

- **Author-Year**: (Smith et al., 2023), (Johnson & Brown, 2022)
- **Numeric**: [1], [2, 3], [Smith et al.]
- **Footnote**: Superscript numbers with footnote references
- **Mixed**: Documents with multiple citation styles

### Reference Parsing

Automatically extracts and parses:
- Author names and affiliations
- Article/book titles
- Journal names and publication details
- Publication years and page numbers
- DOIs and URLs
- Publication types (journal, conference, book, etc.)

### Document Types Detected

- Research papers and journal articles
- Conference papers and proceedings
- Thesis and dissertations
- Book chapters and monographs
- Technical reports
- Grant proposals and white papers

## Error Handling

The processor includes comprehensive error handling:

```python
try:
    result = await processor.process(request)
    if result.status == ProcessingStatus.FAILED:
        print(f"Processing failed: {result.error_message}")
        print(f"Warnings: {result.warnings}")
except DOCXProcessorError as e:
    print(f"DOCX-specific error: {e}")
except DocumentProcessorError as e:
    print(f"General processing error: {e}")
```

### Common Error Scenarios

- **File Not Found**: Invalid file path
- **Corrupted Document**: Damaged or invalid DOCX file
- **Large File**: Document exceeds size limits
- **Empty Document**: Document with no extractable content
- **Missing Dependencies**: python-docx not installed

## Performance Considerations

- **Memory Usage**: Large documents are processed efficiently with streaming
- **Processing Time**: Typical academic papers (10-50 pages) process in 2-10 seconds
- **Concurrent Processing**: Supports multiple documents with configurable thread pools
- **Progress Tracking**: Real-time progress updates for long-running operations

## Integration with SlideGenie

The DOCX processor integrates seamlessly with the SlideGenie presentation generation pipeline:

1. **Document Analysis**: Extract structured content for slide generation
2. **Citation Handling**: Preserve academic references in presentations
3. **Table Integration**: Convert document tables to presentation slides
4. **Figure Extraction**: Use document figures in slide content
5. **Structural Mapping**: Map document sections to slide organization

## Testing

Run the comprehensive test suite:

```bash
# Run all DOCX processor tests
pytest app/services/document_processing/test_docx_processor.py -v

# Run specific test categories
pytest app/services/document_processing/test_docx_processor.py::TestDOCXProcessor::test_metadata_extraction -v
```

## Example Usage

See the complete example in `example_docx_usage.py` which demonstrates:

- Creating sample academic documents
- Processing with all features enabled
- Analyzing extracted content
- Handling different document structures
- Error handling and edge cases

## Limitations

- **Mathematical Equations**: Basic support; complex LaTeX equations may not be fully parsed
- **Complex Tables**: Merged cells and complex formatting may have limitations
- **Embedded Objects**: Some embedded object types may not be extractable
- **Track Changes**: Basic support; complex revision tracking may be incomplete
- **Custom Styles**: Some custom formatting may not be preserved

## Future Enhancements

- Enhanced mathematical equation parsing with MathML support
- Improved track changes and comment processing
- Better handling of complex table structures
- Support for additional embedded object types
- Integration with OCR for scanned document sections
- Real-time collaborative document processing

## Dependencies

- `python-docx>=1.1.2`: Core DOCX document processing
- `lxml>=5.3.0`: XML parsing and manipulation
- `pillow>=11.0.0`: Image processing
- `structlog>=25.4.0`: Structured logging

## License

This component is part of the SlideGenie project and follows the same licensing terms.