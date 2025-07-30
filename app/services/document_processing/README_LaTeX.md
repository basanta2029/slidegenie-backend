# LaTeX Document Processor

A comprehensive LaTeX processor for academic `.tex` files that provides complete document analysis, structure extraction, and content processing capabilities.

## Features

### Core Capabilities

- **LaTeX Tokenization**: Complete tokenization of LaTeX source code with proper command and environment recognition
- **Document Structure Extraction**: Hierarchical extraction of sections, chapters, and document organization
- **Mathematical Equation Processing**: Parse, analyze, and render LaTeX equations with complexity analysis
- **Citation Management**: Extract in-text citations and resolve against BibTeX bibliography files
- **Cross-reference Resolution**: Resolve internal document references (equations, figures, tables, sections)
- **Figure and Table Extraction**: Extract figures and tables with captions and labels
- **Metadata Extraction**: Extract author information, title, abstract, keywords, and document metadata
- **Multi-file Support**: Handle documents with `\input` and `\include` commands

### Advanced Features

- **Equation Rendering**: Render equations to PNG, SVG, MathML, and plain text formats
- **Theorem Environment Processing**: Handle theorem-like environments (theorem, lemma, definition, proof)
- **Complex Math Analysis**: Analyze equation complexity, variables, functions, and mathematical structures
- **Bibliography Integration**: Parse BibTeX files and resolve citation references
- **Document Language Detection**: Detect document language from babel/polyglossia packages
- **Robust Error Handling**: Comprehensive error handling for malformed LaTeX

## Installation and Dependencies

The LaTeX processor requires the following optional dependencies for full functionality:

```bash
# For equation rendering (optional)
pip install matplotlib numpy

# For advanced equation processing (optional)
pip install sympy

# For enhanced text processing (optional)
pip install nltk spacy
```

## Usage

### Basic Usage

```python
from app.services.document_processing.processors.latex_processor import LaTeXProcessor
from app.domain.schemas.document_processing import ProcessingRequest, DocumentType
from uuid import uuid4

# Initialize processor
processor = LaTeXProcessor()

# Create processing request
request = ProcessingRequest(
    document_id=uuid4(),
    file_path="/path/to/document.tex",
    document_type=DocumentType.LATEX,
    extract_text=True,
    extract_figures=True,
    extract_tables=True,
    extract_citations=True,
    extract_references=True,
    extract_metadata=True,
    preserve_layout=True
)

# Process document
result = await processor.process(request)

# Access results
print(f"Title: {result.metadata.title}")
print(f"Authors: {', '.join(result.metadata.authors)}")
print(f"Sections: {len(result.sections)}")
print(f"Equations: {len([e for e in result.elements if e.element_type == 'equation'])}")
print(f"Citations: {len(result.citations)}")
```

### Advanced Usage Examples

#### Equation Processing

```python
from app.services.document_processing.utils.equation_renderer import EquationRenderer

renderer = EquationRenderer()

# Render equation to multiple formats
equation = r"\sum_{i=0}^{n} \alpha_i |i\rangle = |\psi\rangle"
rendered = renderer.render_equation(
    equation, 
    equation_type="display",
    formats=['png', 'svg', 'mathml', 'plain_text']
)

# Access rendered formats
png_data = rendered.png_data
svg_data = rendered.svg_data
mathml = rendered.mathml
plain_text = rendered.plain_text
```

#### Citation Management

```python
from app.services.document_processing.utils.citation_manager import (
    BibTeXParser, CitationExtractor, CitationResolver
)

# Parse bibliography file
bib_parser = BibTeXParser()
bibliography = bib_parser.parse_file("references.bib")

# Extract citations from LaTeX source
citation_extractor = CitationExtractor()
citations = citation_extractor.extract_citations(latex_source)

# Resolve citations
resolver = CitationResolver(bibliography)
resolution_stats = resolver.resolve_citations(citations)
```

#### LaTeX Parsing

```python
from app.services.document_processing.utils.latex_parser import (
    LaTeXTokenizer, LaTeXParser
)

# Tokenize LaTeX source
tokenizer = LaTeXTokenizer()
tokens = tokenizer.tokenize(latex_source)

# Parse commands and environments
parser = LaTeXParser(tokens)
commands, environments = parser.parse()

# Access parsed structures
for command in commands:
    print(f"Command: {command.name}, Args: {command.arguments}")

for env in environments:
    print(f"Environment: {env.name}, Content: {env.content[:50]}...")
```

## Document Structure

### Supported LaTeX Elements

#### Sectioning Commands
- `\part`, `\chapter`, `\section`, `\subsection`, `\subsubsection`
- `\paragraph`, `\subparagraph`

#### Mathematical Environments
- `equation`, `equation*`, `align`, `align*`, `alignat`, `alignat*`
- `gather`, `gather*`, `multline`, `multline*`, `split`
- `array`, `matrix`, `pmatrix`, `bmatrix`, etc.

#### Theorem-like Environments
- `theorem`, `lemma`, `corollary`, `proposition`, `definition`
- `remark`, `example`, `proof`, `claim`, `conjecture`

#### Citation Commands
- `\cite`, `\citep`, `\citet`, `\citealp`, `\citealt`
- `\citeauthor`, `\citeyear`, `\footcite`
- `\parencite`, `\textcite`, `\autocite` (biblatex)

#### Reference Commands
- `\ref`, `\eqref`, `\pageref`, `\nameref`
- `\autoref`, `\cref`, `\Cref`

### Output Structure

The processor returns a `ProcessingResult` containing:

```python
{
    "metadata": {
        "title": "Document Title",
        "authors": ["Author 1", "Author 2"],
        "abstract": "Document abstract",
        "keywords": ["keyword1", "keyword2"],
        "document_type": "article",
        "language": "english"
    },
    "sections": [
        {
            "title": "Introduction",
            "level": 2,
            "elements": [...],
            "subsections": [...]
        }
    ],
    "elements": [
        {
            "element_type": "equation",
            "content": "E = mc^2",
            "latex_code": "E = mc^2",
            "equation_number": "(1)",
            "label": "eq:mass_energy"
        }
    ],
    "figures": [...],
    "tables": [...],
    "citations": [...],
    "references": [...]
}
```

## Configuration Options

The processor can be configured with various options:

```python
config = {
    "equation_dpi": 150,           # DPI for equation rendering
    "equation_font_size": 12,      # Font size for equations
    "max_file_size_mb": 50,        # Maximum file size in MB
    "include_nested_files": True,  # Process \input and \include
    "resolve_references": True,    # Resolve cross-references
    "render_equations": True,      # Render equations to images
    "parse_bibliography": True     # Parse bibliography files
}

processor = LaTeXProcessor(config=config)
```

## Error Handling

The processor provides robust error handling:

```python
try:
    result = await processor.process(request)
    if result.status == ProcessingStatus.FAILED:
        print(f"Processing failed: {result.error_message}")
        print(f"Warnings: {result.warnings}")
except InvalidDocumentError as e:
    print(f"Invalid document: {e}")
except ProcessingTimeoutError as e:
    print(f"Processing timeout: {e}")
except DocumentProcessorError as e:
    print(f"Processing error: {e}")
```

## Performance Considerations

### Memory Usage
- Large documents with many equations may require significant memory for rendering
- Bibliography files are loaded entirely into memory

### Processing Time
- Equation rendering can be time-intensive for complex mathematics
- Multi-file documents require additional I/O operations

### Optimization Tips
- Disable equation rendering for faster text-only processing
- Use appropriate DPI settings for equation images
- Cache bibliography parsing results for repeated processing

## Testing

Run the comprehensive test suite:

```bash
python app/services/document_processing/test_latex_processor.py
```

The test suite includes:
- Document validation tests
- Full processing pipeline tests
- Individual component tests
- Complex LaTeX construct handling
- Error condition testing

## Examples

### Sample Academic Paper Processing

```python
# Process a complete academic paper
result = await processor.process(ProcessingRequest(
    document_id=uuid4(),
    file_path="paper.tex",
    document_type=DocumentType.LATEX
))

# Analyze document structure
print(f"Document has {len(result.sections)} main sections")
for section in result.sections:
    print(f"- {section.title} (Level {section.level})")
    print(f"  Contains {len(section.elements)} elements")

# Analyze mathematical content
equations = [e for e in result.elements if e.element_type == "equation"]
print(f"Found {len(equations)} equations")

complex_equations = [e for e in equations 
                    if e.metadata.get('complexity_score', 0) > 5.0]
print(f"Complex equations: {len(complex_equations)}")

# Citation analysis
print(f"Citations: {len(result.citations)}")
print(f"References: {len(result.references)}")

# Check for unresolved references
unresolved = [c for c in result.citations 
             if c.citation_key not in [r.reference_key for r in result.references]]
print(f"Unresolved citations: {len(unresolved)}")
```

### Equation Analysis

```python
from app.services.document_processing.utils.equation_renderer import EquationParser

parser = EquationParser()

# Analyze a complex equation
equation = r"\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}"
info = parser.parse_equation(equation)

print(f"Variables: {info.variables}")
print(f"Functions: {info.functions}")
print(f"Complexity: {info.complexity_score}")
print(f"Has integrals: {info.has_integrals}")
```

## Contributing

When contributing to the LaTeX processor:

1. Add comprehensive tests for new features
2. Update documentation for new capabilities
3. Handle edge cases gracefully
4. Maintain backward compatibility
5. Follow the existing code structure and patterns

## Future Enhancements

- TikZ/PGF diagram extraction
- Advanced table parsing (complex layouts)
- Custom command/environment definitions
- Package-specific processing (algorithm, listings, etc.)
- PDF output generation
- Real-time collaborative editing support