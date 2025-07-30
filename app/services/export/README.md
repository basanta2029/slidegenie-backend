# SlideGenie Export Services

Comprehensive export services for generating presentations in various formats with academic templates and advanced features.

## Overview

The export services provide a unified interface for converting SlideGenie slide content into multiple presentation formats, with particular emphasis on academic presentations and professional styling.

## Features

### 🎯 **Core Capabilities**
- **Multi-format Export**: PPTX, PDF, HTML, JSON (extensible architecture)
- **Academic Templates**: IEEE, ACM, Nature, Springer, university-specific themes
- **Custom Branding**: Logo placement, color schemes, typography customization
- **Advanced Content**: Equations, charts, images, tables, citations
- **Responsive Design**: Automatic content fitting and layout optimization

### 📋 **PPTX Generator Features**

#### **Academic Template System**
- **IEEE Style**: Blue color scheme, Arial fonts, professional layout
- **ACM Style**: Modern blue/orange theme, Helvetica typography
- **Nature Style**: Green theme, Times New Roman, scientific layout
- **University Templates**: MIT, Stanford, Harvard, Oxford, Cambridge
- **Custom Templates**: Full customization support

#### **Advanced Content Support**
- **Mathematical Equations**: LaTeX rendering with MathML integration
- **High-Quality Images**: Automatic optimization and responsive sizing
- **Interactive Charts**: Column, line, pie, bar charts with data visualization
- **Citation Management**: IEEE, APA, MLA, Chicago formatting styles
- **Speaker Notes**: Comprehensive presenter guidance integration

#### **Layout Management**
- **Responsive Design**: Automatic content fitting and overflow handling
- **Multiple Layouts**: Title slides, two-column, section headers, comparison
- **Smart Positioning**: Automatic element placement with margin management
- **Branding Integration**: Logo placement, headers, footers, slide numbers

#### **Quality Assurance**
- **Error Handling**: Graceful fallbacks for missing content or resources
- **Content Validation**: Automatic slide structure and format validation
- **Performance Optimization**: Efficient image processing and file generation
- **Memory Management**: Streaming output for large presentations

## Quick Start

### Basic Usage

```python
from app.services.export.export_service import export_to_pptx
from app.domain.schemas.generation import SlideContent

# Create slide content
slides = [
    SlideContent(
        title="My Presentation",
        subtitle="Academic Research Overview",
        body=[
            {"type": "text", "content": "Dr. Jane Smith\nMIT"}
        ],
        metadata={"slide_type": "title"}
    ),
    SlideContent(
        title="Introduction",
        body=[
            {
                "type": "bullet_list",
                "items": [
                    "Research objectives",
                    "Methodology overview", 
                    "Expected outcomes"
                ]
            }
        ]
    )
]

# Export to PPTX
buffer = export_to_pptx(
    slides=slides,
    template='ieee',
    university_name='MIT',
    output_path='presentation.pptx'
)
```

### Advanced Academic Presentation

```python
from app.services.export.generators.pptx_generator import (
    PPTXGenerator, 
    create_academic_template_config,
    AcademicTemplate
)
from app.domain.schemas.generation import Citation

# Create citations
citations = [
    Citation(
        key="smith2024",
        authors=["Jane Smith", "John Doe"],
        title="Advanced Machine Learning Techniques",
        year=2024,
        venue="Nature Machine Intelligence",
        doi="10.1038/s42256-024-00123-4"
    )
]

# Configure template
config = create_academic_template_config(
    template=AcademicTemplate.NATURE,
    university_name="Stanford University",
    logo_path="/path/to/logo.png",
    custom_colors={
        "primary": "#8c1515",  # Stanford red
        "secondary": "#b83a4b"
    }
)

# Generate presentation
generator = PPTXGenerator(config)
buffer = generator.export_to_buffer(
    slides=slides,
    citations=citations,
    metadata={
        "title": "Research Presentation",
        "author": "Dr. Jane Smith",
        "subject": "Machine Learning",
        "keywords": "research, AI, neural networks"
    }
)
```

## Content Types

### Text Content
```python
{
    "type": "text",
    "content": "Your text content here"
}
```

### Bullet Lists
```python
{
    "type": "bullet_list",
    "items": [
        "First bullet point",
        "Second bullet point",
        "Third bullet point"
    ],
    "level": 0  # Optional nesting level
}
```

### Mathematical Equations
```python
{
    "type": "equation",
    "latex": r"E = mc^2",
    "content": "Einstein's mass-energy equivalence"
}
```

### Images
```python
{
    "type": "image",
    "path": "/path/to/image.jpg",  # or URL
    "caption": "Figure 1: Sample visualization",
    "alt_text": "Description for accessibility"
}
```

### Charts
```python
{
    "type": "chart",
    "chart_type": "column",  # column, line, pie, bar
    "title": "Performance Comparison",
    "data": {
        "categories": ["Method A", "Method B", "Method C"],
        "series": [
            {
                "name": "Accuracy",
                "values": [0.85, 0.91, 0.87]
            },
            {
                "name": "Speed", 
                "values": [0.78, 0.82, 0.95]
            }
        ]
    }
}
```

### Tables
```python
{
    "type": "table",
    "data": {
        "headers": ["Method", "Accuracy", "Time"],
        "rows": [
            ["Baseline", "85.2%", "10ms"],
            ["Our Method", "91.7%", "8ms"]
        ]
    }
}
```

## Template Configuration

### Color Schemes
```python
from app.services.export.generators.pptx_generator import ColorScheme

custom_colors = ColorScheme(
    primary="#1f4e79",      # Main theme color
    secondary="#70ad47",    # Secondary theme color  
    accent="#c5504b",       # Accent color for highlights
    text_primary="#000000", # Main text color
    text_secondary="#404040", # Secondary text color
    background="#ffffff",   # Slide background
    background_alt="#f2f2f2" # Alternative background
)
```

### Typography
```python
from app.services.export.generators.pptx_generator import Typography

custom_typography = Typography(
    title_font="Arial",      # Font for slide titles
    body_font="Calibri",     # Font for body text
    code_font="Consolas",    # Font for code blocks
    title_size=44,           # Title font size (points)
    subtitle_size=32,        # Subtitle font size
    body_size=24,            # Body text font size
    caption_size=18,         # Caption font size
    footnote_size=14         # Footnote font size
)
```

### Branding
```python
from app.services.export.generators.pptx_generator import BrandingConfig

branding = BrandingConfig(
    logo_path="/path/to/logo.png",
    logo_position="top_right",  # top_left, top_right, bottom_left, bottom_right
    logo_size=(1.5, 0.75),     # Width, height in inches
    university_name="Your University",
    department_name="Department Name",
    show_slide_numbers=True,
    show_date=True,
    custom_footer="Conference Name • Institution"
)
```

## Academic Templates

### IEEE Template
- **Colors**: Professional blue theme (#003f7f primary)
- **Typography**: Arial fonts, clean layout
- **Features**: Conservative styling, technical presentation focus
- **Best for**: Engineering conferences, technical papers

### Nature Template  
- **Colors**: Green theme (#006633 primary)
- **Typography**: Times New Roman, scientific styling
- **Features**: Nature journal styling, research emphasis
- **Best for**: Scientific publications, research presentations

### ACM Template
- **Colors**: Blue and orange theme (#0085ca primary)
- **Typography**: Helvetica, modern styling
- **Features**: Contemporary design, computing focus
- **Best for**: Computer science conferences, technical talks

### University Templates
- **MIT**: Crimson and gray theme, Source Sans Pro fonts
- **Stanford**: Cardinal red theme, professional layout
- **Harvard**: Crimson theme, traditional academic styling
- **Oxford**: Oxford blue theme, classical design
- **Cambridge**: Light blue theme, elegant typography

## Export Service Integration

### Using the Export Service

```python
from app.services.export.export_service import ExportService, ExportFormat

service = ExportService()

# Get supported formats
formats = service.get_supported_formats()
# Returns: ['pptx', 'pdf', 'html', 'json'] (as available)

# Get template options
options = service.get_template_options(ExportFormat.PPTX)
# Returns detailed template configuration options

# Export presentation
buffer = service.export_presentation(
    slides=slides,
    format=ExportFormat.PPTX,
    template_config={
        'template': 'ieee',
        'university_name': 'MIT',
        'branding': {
            'show_slide_numbers': True,
            'custom_footer': 'AAAI 2024'
        }
    },
    citations=citations,
    metadata=metadata
)
```

### Academic Presentation Export

```python
from app.services.export.export_service import export_academic_presentation

buffer = export_academic_presentation(
    slides=slides,
    conference_name="AAAI 2024",
    author_name="Dr. Jane Smith",
    institution="Stanford University",
    template="nature",
    citations=citations,
    output_path="academic_presentation.pptx"
)
```

## Error Handling

The export system includes comprehensive error handling:

### Graceful Degradation
- **Missing Images**: Automatic placeholder generation
- **Invalid Equations**: Fallback to text representation
- **Malformed Content**: Error slide generation with diagnostic info
- **Font Issues**: Automatic font substitution

### Validation
- **Content Validation**: Automatic slide structure checking
- **Template Validation**: Configuration parameter verification
- **Resource Validation**: Image and asset availability checking

### Logging
```python
import logging

# Configure logging to see export process details
logging.getLogger('app.services.export').setLevel(logging.DEBUG)
```

## Performance Considerations

### Optimization Features
- **Image Processing**: Automatic resizing and compression
- **Memory Management**: Streaming output for large presentations
- **Caching**: Template and resource caching
- **Parallel Processing**: Multi-threaded image processing

### Best Practices
- **Image Sizes**: Use appropriate resolution (max 1920x1080)
- **Equation Complexity**: Keep LaTeX equations reasonably simple
- **Slide Count**: No hard limits, but 100+ slides may take longer
- **Resource Paths**: Use absolute paths or URLs for reliability

## Testing

### Run Tests
```bash
# Run all export service tests
pytest app/services/export/

# Run specific test file
pytest app/services/export/generators/test_pptx_generator.py

# Run with coverage
pytest --cov=app.services.export app/services/export/
```

### Test Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end presentation generation
- **Edge Cases**: Error conditions and malformed input
- **Performance Tests**: Large presentation handling

## Examples

### Complete Example Files
- `example_usage.py`: Comprehensive usage examples
- `test_pptx_generator.py`: Test suite with examples
- Template-specific examples for each academic style

### Sample Presentations
Run the examples to generate sample presentations:

```bash
cd app/services/export/generators/
python example_usage.py
```

This generates:
- `ieee_presentation_example.pptx`
- `nature_presentation_example.pptx`  
- `custom_presentation_example.pptx`
- `mit_branded_presentation.pptx`
- `equation_heavy_presentation.pptx`

## Dependencies

### Required Packages
```
python-pptx>=0.6.23    # PowerPoint generation
pillow>=11.0.0         # Image processing
requests>=2.32.0       # HTTP requests for remote images
```

### Optional Packages
```
matplotlib>=3.7.0      # Enhanced equation rendering
latex2mathml>=3.76.0   # LaTeX to MathML conversion
```

## Extension Points

### Adding New Templates
1. Add template enum to `AcademicTemplate`
2. Define template configuration in `_load_template_definitions()`
3. Create template-specific formatting rules
4. Add tests and examples

### Adding New Export Formats
1. Create format-specific generator class
2. Implement `export_to_buffer()` and `export_to_file()` methods
3. Register generator in `ExportService`
4. Add format-specific configuration options

### Custom Content Types
1. Add content type handling in `_add_body_content()`
2. Implement content-specific rendering logic
3. Add validation for new content structure
4. Update documentation and examples

## Troubleshooting

### Common Issues

**Font Not Available**
```python
# Specify fallback fonts
typography = Typography(
    title_font="Arial",  # Widely available
    body_font="Calibri"  # Office standard
)
```

**Large File Sizes**
```python
# Optimize image processing
generator.image_processor.max_image_size = (1280, 720)  # Reduce max resolution
```

**Equation Rendering Issues**
```python
# Use simpler LaTeX syntax
equation = {
    "type": "equation",
    "latex": r"x^2 + y^2 = z^2"  # Avoid complex packages
}
```

**Memory Issues with Large Presentations**
```python
# Process in chunks for very large presentations
def process_large_presentation(slides, chunk_size=50):
    for i in range(0, len(slides), chunk_size):
        chunk = slides[i:i+chunk_size]
        # Process chunk...
```

## Contributing

When contributing to the export services:

1. **Follow Patterns**: Use existing patterns for new generators
2. **Add Tests**: Include comprehensive test coverage
3. **Document Features**: Update README and docstrings
4. **Consider Performance**: Optimize for large presentations
5. **Handle Errors**: Implement graceful error handling

## License

Part of the SlideGenie project. See main project LICENSE for details.