# PDF Generator for Academic Presentations

The PDF Generator provides comprehensive PDF export functionality for academic presentations with multiple formats, quality settings, and styling options.

## Features

### 📄 Multiple PDF Formats

- **Presentation Format**: Standard slide view with one slide per page
- **Handout Format**: Multiple slides per page in customizable grid layouts
- **Notes Format**: Slides combined with speaker notes
- **Print-Optimized Format**: High contrast, print-friendly version with enhanced readability

### 🎨 Layout Options

#### Handout Layouts
- 1×1: One slide per page
- 2×1: Two slides horizontally  
- 1×2: Two slides vertically
- 2×2: Four slides in 2×2 grid
- 2×3: Six slides in 2×3 grid
- 3×2: Six slides in 3×2 grid
- 3×3: Nine slides in 3×3 grid
- 4×3: Twelve slides in 4×3 grid
- 4×4: Sixteen slides in 4×4 grid

#### Page Sizes & Orientations
- **Sizes**: A4, A3, A5, Letter, Legal, Custom
- **Orientations**: Portrait, Landscape
- **Custom dimensions**: Specify exact width/height in points

### ⚙️ Quality Settings

- **Draft**: Fast generation, optimized for speed
- **Standard**: Balanced quality and file size
- **High Quality**: Maximum image quality and detail
- **Print Ready**: Optimized for professional printing (300 DPI)

### 🎓 Academic Templates

Pre-configured templates for major academic venues:

- **IEEE Conference Style**: Blue color scheme, Times fonts
- **ACM Conference Style**: Orange accent colors, modern typography
- **Nature Journal Style**: Green accents, high contrast for readability

### 🖼️ Image Processing

- Automatic image optimization and compression
- Support for web URLs and local file paths
- Configurable DPI settings (150-300 DPI)
- Smart resizing while maintaining aspect ratios
- High contrast mode for print optimization

### 🔤 Typography & Styling

- Custom font selection (Helvetica, Times, Computer Modern)
- Configurable font sizes for titles, body text, and captions
- Color customization for primary, accent, text, and background
- Adjustable margins and spacing
- Support for mathematical notation and special characters

### 🏷️ Document Features

- **Table of Contents**: Automatically generated with slide titles
- **Bookmarks**: PDF navigation bookmarks for easy browsing
- **Page Numbers**: Optional page numbering with custom positioning
- **Headers/Footers**: Customizable header and footer content
- **Watermarks**: Text watermarks with opacity and rotation control
- **Metadata**: Author, title, subject, keywords, creation date

### ♿ Accessibility

- Tagged PDF support for screen readers
- Alt text for images
- High contrast mode for visual accessibility
- Proper document structure and navigation

## Quick Start

### Basic Usage

```python
from pdf_generator import create_presentation_pdf, PDFSlide

# Create slides
slides = [
    PDFSlide(
        title="Introduction to Machine Learning",
        content="Machine learning is a subset of AI...",
        notes="Spend 3 minutes on this topic",
        slide_number=1
    ),
    PDFSlide(
        title="Neural Networks",
        content="Neural networks consist of...",
        notes="Draw diagram on whiteboard",
        slide_number=2
    )
]

# Generate PDF
success = create_presentation_pdf(slides, "presentation.pdf")
```

### Advanced Configuration

```python
from pdf_generator import PDFGenerator, PDFConfig, PDFFormat, PageSize

# Custom configuration
config = PDFConfig(
    format=PDFFormat.HANDOUT,
    handout_layout=HandoutLayout.LAYOUT_2x3,
    page_size=PageSize.A4,
    orientation=PageOrientation.PORTRAIT,
    watermark_text="CONFIDENTIAL",
    primary_color="#003366",
    include_toc=True,
    quality=PDFQuality.HIGH_QUALITY
)

# Generate with custom config
generator = PDFGenerator(config)
success = generator.generate_pdf(slides, "handout.pdf")
```

### Academic Templates

```python
from pdf_generator import PDFGenerator, get_ieee_config

# Use IEEE conference template
ieee_generator = PDFGenerator(get_ieee_config())
success = ieee_generator.generate_pdf(slides, "ieee_presentation.pdf")
```

## API Reference

### PDFSlide Class

Represents individual slide content:

```python
@dataclass
class PDFSlide:
    title: str = ""                    # Slide title
    content: str = ""                  # Main slide content
    notes: str = ""                    # Speaker notes
    images: List[Dict] = []            # Image references
    citations: List[Citation] = []     # Academic citations
    slide_number: int = 1              # Slide number
    layout_type: str = "title_and_content"  # Layout template
    background_color: Optional[str] = None   # Custom background
```

### PDFConfig Class

Configuration options for PDF generation:

```python
@dataclass
class PDFConfig:
    # Format settings
    format: PDFFormat = PDFFormat.PRESENTATION
    quality: PDFQuality = PDFQuality.STANDARD
    page_size: PageSize = PageSize.A4
    orientation: PageOrientation = PageOrientation.PORTRAIT
    
    # Layout settings
    handout_layout: HandoutLayout = HandoutLayout.LAYOUT_2x3
    margin_top: float = 72      # Points
    margin_bottom: float = 72
    margin_left: float = 72
    margin_right: float = 72
    
    # Content settings
    include_toc: bool = True
    include_bookmarks: bool = True
    include_page_numbers: bool = True
    include_headers: bool = False
    include_footers: bool = True
    
    # Watermark settings
    watermark_text: Optional[str] = None
    watermark_opacity: float = 0.1
    watermark_rotation: float = 45
    
    # Typography
    title_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    font_size_title: int = 16
    font_size_body: int = 11
    
    # Colors
    primary_color: str = "#2E3440"
    accent_color: str = "#5E81AC"
    text_color: str = "#2E3440"
    background_color: str = "#FFFFFF"
    
    # Image settings
    image_dpi: int = 150
    image_quality: int = 85
    compress_images: bool = True
```

### Convenience Functions

```python
# Standard presentation
create_presentation_pdf(slides, "output.pdf", config=None)

# Handout with specific layout
create_handout_pdf(slides, "handout.pdf", HandoutLayout.LAYOUT_2x3, config=None)

# Notes format
create_notes_pdf(slides, "notes.pdf", config=None)

# Print-optimized
create_print_pdf(slides, "print.pdf", config=None)
```

### Template Functions

```python
# Get predefined academic templates
ieee_config = get_ieee_config()      # IEEE conference style
acm_config = get_acm_config()        # ACM conference style  
nature_config = get_nature_config()  # Nature journal style
```

## Examples

### 1. Conference Presentation

```python
from pdf_generator import *

# Create slides with citations
slides = [
    PDFSlide(
        title="Quantum Machine Learning",
        content="""
        Recent advances in quantum computing have opened new possibilities 
        for machine learning algorithms that could provide exponential 
        speedups for certain problems.
        """,
        citations=[
            Citation(
                title="Quantum machine learning",
                authors="Jacob Biamonte, Peter Wittek",
                year="2017",
                url="https://doi.org/10.1038/nature23474"
            )
        ]
    )
]

# Generate IEEE-style conference PDF
ieee_generator = PDFGenerator(get_ieee_config())
ieee_generator.generate_pdf(slides, "quantum_ml_conference.pdf")
```

### 2. Student Handouts

```python
# Create handout with 6 slides per page
config = PDFConfig(
    format=PDFFormat.HANDOUT,
    handout_layout=HandoutLayout.LAYOUT_2x3,
    page_size=PageSize.A4,
    include_page_numbers=True,
    watermark_text="Class Material",
    watermark_opacity=0.05
)

generator = PDFGenerator(config)
generator.generate_pdf(slides, "student_handout.pdf")
```

### 3. Lecture Notes

```python
# Generate notes format with speaker notes
config = PDFConfig(
    format=PDFFormat.NOTES,
    font_size_body=12,
    margin_left=100,  # More space for annotations
    include_headers=True,
    include_footers=True
)

generator = PDFGenerator(config)
generator.generate_pdf(slides, "lecture_notes.pdf")
```

### 4. Print-Ready Version

```python
# High-quality print version
config = PDFConfig(
    format=PDFFormat.PRINT_OPTIMIZED,
    quality=PDFQuality.PRINT_READY,
    high_contrast=True,
    image_dpi=300,
    compress_images=False,
    text_color="#000000",
    background_color="#FFFFFF"
)

generator = PDFGenerator(config)
generator.generate_pdf(slides, "print_version.pdf")
```

## Dependencies

The PDF generator requires the following Python packages:

```python
# Core PDF generation
reportlab              # Primary PDF library
weasyprint            # Alternative HTML/CSS to PDF (optional)

# Image processing  
Pillow (PIL)          # Image manipulation and optimization

# Utilities
requests              # For downloading web images
```

Install dependencies:

```bash
pip install reportlab pillow requests weasyprint
```

## Performance Considerations

### Generation Speed
- **Draft quality**: ~1-2 seconds per slide
- **Standard quality**: ~2-4 seconds per slide  
- **High quality**: ~4-8 seconds per slide
- **Print ready**: ~8-15 seconds per slide

### File Size Optimization
- Enable `compress_images` for smaller files
- Use appropriate `image_dpi` settings
- Choose `PDFQuality.DRAFT` for preview versions
- Optimize image sources before processing

### Memory Usage
- Large presentations (50+ slides) may require 100-500MB RAM
- Image-heavy presentations need additional memory
- Consider processing in batches for very large presentations

## Error Handling

The PDF generator includes comprehensive error handling:

```python
try:
    generator = PDFGenerator(config)
    success = generator.generate_pdf(slides, output_path)
    
    if not success:
        print("PDF generation failed - check logs for details")
        
except Exception as e:
    print(f"Error: {e}")
    # Handle specific error cases
```

Common issues and solutions:

- **Font not found**: Falls back to system fonts automatically
- **Image loading failure**: Skips problematic images, logs warning
- **Invalid output path**: Returns False, logs error
- **Memory limitations**: Reduce image quality or process in batches

## Integration Examples

### Web API Integration

```python
from fastapi import FastAPI, HTTPException
from pdf_generator import PDFGenerator, PDFConfig, PDFSlide

app = FastAPI()

@app.post("/generate-pdf")
async def generate_pdf(request: PresentationRequest):
    try:
        # Convert request to slides
        slides = [PDFSlide(**slide_data) for slide_data in request.slides]
        
        # Configure generator
        config = PDFConfig(
            format=PDFFormat(request.format),
            quality=PDFQuality(request.quality)
        )
        
        # Generate PDF
        generator = PDFGenerator(config)
        output_path = f"temp/{request.id}.pdf"
        
        success = generator.generate_pdf(slides, output_path)
        
        if success:
            return {"status": "success", "file_path": output_path}
        else:
            raise HTTPException(status_code=500, detail="PDF generation failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Batch Processing

```python
def batch_generate_pdfs(presentations: List[Dict], output_dir: str):
    """Generate PDFs for multiple presentations."""
    
    results = []
    
    for i, presentation in enumerate(presentations):
        try:
            slides = [PDFSlide(**slide) for slide in presentation["slides"]]
            output_path = f"{output_dir}/presentation_{i+1}.pdf"
            
            generator = PDFGenerator()
            success = generator.generate_pdf(slides, output_path)
            
            results.append({
                "id": presentation.get("id", i+1),
                "success": success,
                "output_path": output_path if success else None
            })
            
        except Exception as e:
            results.append({
                "id": presentation.get("id", i+1),
                "success": False,
                "error": str(e)
            })
    
    return results
```

## Contributing

To contribute to the PDF generator:

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Consider backwards compatibility
5. Test with various slide content types

## License

This PDF generator is part of the SlideGenie academic presentation system.