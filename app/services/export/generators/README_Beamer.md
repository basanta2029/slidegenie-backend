# LaTeX Beamer Generator

A comprehensive LaTeX Beamer export system for academic presentations with full feature support including themes, citations, mathematics, figures, tables, and handout generation.

## Features

### Core Functionality
- **Complete Beamer document generation** with proper preamble and package management
- **Academic themes** (Berlin, Madrid, Warsaw, Singapore, etc.) with customization options
- **BibTeX/biblatex integration** with citation management and bibliography generation
- **Mathematical equation rendering** with LaTeX math environments
- **Figure placement optimization** with subfigures and positioning
- **Handout version generation** with different layouts (1x1, 2x2, 3x3, etc.)
- **Professional table formatting** with booktabs and advanced styling
- **Frame transitions and overlays** for dynamic presentations

### Advanced Features
- **Package management** with automatic dependency resolution
- **Template system** with customizable LaTeX templates
- **Error handling** with comprehensive validation
- **Citation processing** with markdown-style citation conversion
- **Content processing** with markdown to LaTeX conversion
- **Compilation support** with automatic PDF generation
- **Multi-format exports** (presentation and handout versions)

## Quick Start

### Basic Usage

```python
from beamer_generator import create_academic_presentation, BeamerSlide

# Create a presentation
generator = create_academic_presentation(
    title="My Research Presentation",
    author="Dr. Jane Smith",
    institute="University of Excellence"
)

# Add slides
slide = BeamerSlide(
    title="Introduction",
    content="""
    This presentation covers:
    - Research objectives
    - Methodology overview
    - Key findings
    
    **Main contribution:** Novel approach to problem solving.
    """
)

generator.add_slide(slide)

# Generate LaTeX
latex_content = generator.generate_latex()

# Save to file
generator.save_latex("presentation.tex")

# Compile to PDF (requires LaTeX installation)
pdf_path, success = generator.compile_pdf("presentation.tex")
```

### Advanced Configuration

```python
from beamer_generator import (
    BeamerGenerator, BeamerConfig, BeamerSlide, BeamerFigure, BeamerTable,
    BeamerTheme, ColorTheme, HandoutLayout, BibliographyConfig
)

# Custom configuration
config = BeamerConfig(
    title="Advanced Research Presentation",
    author="Prof. John Doe",
    institute="Research Institute",
    theme=BeamerTheme.WARSAW,
    color_theme=ColorTheme.DOLPHIN,
    aspect_ratio="16:9",
    font_size="11pt",
    generate_handout=True,
    handout_layout=HandoutLayout.FOUR_PER_PAGE,
    bibliography=BibliographyConfig(
        bib_file="references.bib",
        style="authoryear",
        biblatex=True
    ),
    custom_commands=[
        "\\newcommand{\\important}[1]{\\textcolor{red}{\\textbf{#1}}}",
        "\\DeclareMathOperator{\\argmax}{argmax}"
    ]
)

generator = BeamerGenerator(config)
```

## Configuration Options

### Themes and Styling

#### Available Themes
- `BeamerTheme.BERLIN` - Clean, professional theme with navigation
- `BeamerTheme.MADRID` - Simple theme with colored headers
- `BeamerTheme.WARSAW` - Classic academic theme with shadows
- `BeamerTheme.SINGAPORE` - Minimal theme with subtle styling
- `BeamerTheme.COPENHAGEN` - Blue-toned professional theme
- And many more...

#### Color Themes
- `ColorTheme.DEFAULT` - Standard Beamer colors
- `ColorTheme.DOLPHIN` - Blue color scheme
- `ColorTheme.CRANE` - Orange/yellow color scheme
- `ColorTheme.ORCHID` - Purple color scheme
- And others...

#### Document Options
```python
config = BeamerConfig(
    aspect_ratio="16:9",  # 4:3, 16:9, 14:9, 16:10, 3:2, 5:4
    font_size="11pt",     # 8pt, 9pt, 10pt, 11pt, 12pt, 14pt, 17pt, 20pt
    navigation_symbols=False,  # Show/hide navigation symbols
)
```

### Bibliography Integration

#### BibLaTeX (Recommended)
```python
bibliography = BibliographyConfig(
    bib_file="references.bib",
    style="authoryear",     # authoryear, numeric, alphabetic
    backend="biber",        # biber, bibtex
    biblatex=True,
    sorting="nyt",          # name, year, title
    max_names=3,
    min_names=1
)
```

#### Citation in Content
```python
slide_content = """
Recent work [@smith2020] shows promising results.
The foundational paper [Jones2021] provides the theoretical framework.
"""
```

### Slide Content

#### Basic Slide
```python
slide = BeamerSlide(
    title="Research Methodology",
    content="""
    Our approach consists of three phases:
    
    1. **Data Collection**
       - Survey design
       - Sample selection
    
    2. **Analysis**
       - Statistical methods
       - Machine learning techniques
    
    3. **Validation**
       - Cross-validation
       - Expert review
    """
)
```

#### Slide with Figures
```python
slide = BeamerSlide(
    title="Experimental Results",
    content="Performance comparison across different methods:",
    figures=[
        BeamerFigure(
            path="results_chart.png",
            caption="Performance metrics comparison",
            width="0.8\\textwidth",
            label="fig:results"
        )
    ]
)
```

#### Slide with Subfigures
```python
figure = BeamerFigure(
    caption="Experimental setup and results",
    subfigures=[
        BeamerFigure(
            path="setup.png",
            caption="Experimental setup",
            width="0.45\\textwidth"
        ),
        BeamerFigure(
            path="results.png", 
            caption="Results visualization",
            width="0.45\\textwidth"
        )
    ]
)
```

#### Slide with Tables
```python
table = BeamerTable(
    headers=["Method", "Accuracy", "F1-Score", "Runtime"],
    data=[
        ["Baseline", "0.82", "0.78", "5.2s"],
        ["Our Method", "0.94", "0.91", "3.8s"],
        ["State-of-art", "0.89", "0.85", "12.1s"]
    ],
    caption="Performance comparison",
    booktabs=True  # Professional table formatting
)

slide = BeamerSlide(
    title="Performance Evaluation",
    content="Quantitative results:",
    tables=[table]
)
```

#### Slide with Mathematics
```python
slide = BeamerSlide(
    title="Mathematical Framework",
    content="The optimization problem is formulated as:",
    equations=[
        "\\min_{\\theta} \\mathcal{L}(\\theta) = \\frac{1}{n}\\sum_{i=1}^{n} \\ell(f(x_i; \\theta), y_i)",
        "\\text{subject to } \\|\\theta\\|_2 \\leq C"
    ]
)
```

### Handout Generation

```python
config = BeamerConfig(
    generate_handout=True,
    handout_layout=HandoutLayout.FOUR_PER_PAGE,  # 1x1, 2x1, 2x2, 3x2, 3x3
    handout_notes=True  # Include speaker notes
)

# Generate both presentation and handout
generator = BeamerGenerator(config)
# ... add slides ...

# Save presentation
generator.save_latex("presentation.tex")

# Generate handout
handout_pdf, success = generator.generate_handout("presentation.tex")
```

### Overlays and Transitions

```python
# Figure with overlay
figure = BeamerFigure(
    path="diagram.png",
    caption="System architecture",
    overlay="<2->"  # Show from slide 2 onwards
)

# Table with overlay
table = BeamerTable(
    headers=["Item", "Value"],
    data=[["A", "1"], ["B", "2"]],
    overlay="<3->"  # Show from slide 3 onwards
)

# Frame with options
slide = BeamerSlide(
    title="Dynamic Content",
    content="Content appears progressively",
    frame_options=["fragile"],  # For complex content
    figures=[figure],
    tables=[table]
)
```

## Factory Functions

### Academic Presentation
```python
generator = create_academic_presentation(
    title="Research Presentation",
    author="Dr. Smith",
    institute="University"
)
# Pre-configured with:
# - Berlin theme
# - Handout generation enabled
# - Bibliography support
# - Standard academic packages
```

### Mathematics Presentation
```python
generator = create_math_presentation(
    title="Advanced Calculus",
    author="Prof. Mathematics"
)
# Pre-configured with:
# - Warsaw theme with Crane colors
# - Mathematical packages (amsmath, physics, etc.)
# - Custom math commands
# - TikZ libraries for diagrams
```

## Content Processing

### Markdown Support
The generator automatically converts markdown-style content to LaTeX:

```python
content = """
**Bold text** becomes \\textbf{Bold text}
*Italic text* becomes \\textit{Italic text}
`Code text` becomes \\texttt{Code text}

- Bullet lists become itemize environments
- With proper nesting

1. Numbered lists become enumerate environments
2. With automatic numbering
"""
```

### Citation Processing
```python
content = """
Recent advances [@smith2020] show promising results.
The seminal work [Jones2021] established the foundation.
"""
# Automatically converts to \cite{smith2020} and \cite{Jones2021}
```

## Compilation and Output

### LaTeX to PDF
```python
# Compile to PDF
pdf_path, success = generator.compile_pdf("presentation.tex")

if success:
    print(f"PDF generated: {pdf_path}")
else:
    print("Compilation failed")
```

### Package Requirements
The generator automatically manages LaTeX packages, but ensure your LaTeX installation includes:

```latex
% Core packages
\usepackage{beamer}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{babel}

% Mathematics
\usepackage{amsmath}
\usepackage{amsfonts} 
\usepackage{amssymb}

% Graphics and tables
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tikz}

% Bibliography (if used)
\usepackage{biblatex}  % or natbib
```

### Validation
```python
# Validate configuration
issues = generator.validate_config()
if issues:
    for issue in issues:
        print(f"Configuration issue: {issue}")
```

## Error Handling

```python
try:
    # Generate LaTeX
    latex_content = generator.generate_latex()
    
    # Save to file
    output_path = generator.save_latex("presentation.tex")
    
    # Compile to PDF
    pdf_path, success = generator.compile_pdf(output_path)
    
    if not success:
        print("PDF compilation failed - check LaTeX installation")
        
except Exception as e:
    print(f"Error generating presentation: {e}")
```

## Examples

### Complete Research Presentation

```python
from beamer_generator import *

# Configure presentation
config = BeamerConfig(
    title="Machine Learning for Climate Prediction",
    author="Dr. Climate Researcher",
    institute="Environmental Science Institute",
    date="Conference 2024",
    theme=BeamerTheme.MADRID,
    color_theme=ColorTheme.DOLPHIN,
    bibliography=BibliographyConfig(
        bib_file="climate.bib",
        style="authoryear",
        biblatex=True
    )
)

generator = BeamerGenerator(config)

# Title slide is automatic

# Introduction
intro_slide = BeamerSlide(
    title="Climate Prediction Challenges",
    content="""
    Current climate models face several challenges:
    
    - **Computational complexity**: High-resolution simulations
    - **Data scarcity**: Limited historical records  
    - **Uncertainty quantification**: Model ensemble methods
    
    Machine learning offers promising solutions [@chen2023ml].
    """
)

# Methodology
method_slide = BeamerSlide(
    title="Proposed Methodology",
    content="Our hybrid approach combines physics and ML:",
    figures=[
        BeamerFigure(
            path="methodology_diagram.png",
            caption="Hybrid physics-ML framework",
            width="0.9\\textwidth"
        )
    ],
    equations=[
        "\\hat{T}(t+\\Delta t) = f_{physics}(T(t), P(t)) + f_{ML}(\\mathbf{X}(t))"
    ]
)

# Results
results_slide = BeamerSlide(
    title="Experimental Results", 
    content="Performance on benchmark datasets:",
    tables=[
        BeamerTable(
            headers=["Dataset", "RMSE", "MAE", "R²"],
            data=[
                ["Climate-1000", "0.82", "0.65", "0.94"],
                ["Weather-EU", "1.23", "0.98", "0.89"],
                ["Global-Ocean", "0.91", "0.72", "0.92"]
            ],
            caption="Prediction accuracy metrics"
        )
    ]
)

# Add slides
generator.add_slides([intro_slide, method_slide, results_slide])

# Generate and save
latex_content = generator.generate_latex()
generator.save_latex("climate_presentation.tex")

# Generate handout
generator.config.generate_handout = True
handout_pdf, success = generator.generate_handout("climate_presentation.tex")
```

## Integration with SlideGenie

The Beamer generator integrates seamlessly with the SlideGenie backend:

```python
# In export service
from app.services.export.generators import BeamerGenerator, BeamerConfig

def export_to_beamer(presentation_data: dict) -> str:
    """Export presentation to LaTeX Beamer format."""
    
    # Configure from presentation data
    config = BeamerConfig(
        title=presentation_data["title"],
        author=presentation_data["author"],
        institute=presentation_data.get("institute"),
        theme=BeamerTheme(presentation_data.get("theme", "Berlin")),
        generate_handout=presentation_data.get("generate_handout", False)
    )
    
    generator = BeamerGenerator(config)
    
    # Convert slides
    for slide_data in presentation_data["slides"]:
        slide = BeamerSlide(
            title=slide_data["title"],
            content=slide_data["content"],
            figures=[
                BeamerFigure(
                    path=fig["path"],
                    caption=fig["caption"],
                    width=fig.get("width", "0.8\\textwidth")
                ) for fig in slide_data.get("figures", [])
            ]
        )
        generator.add_slide(slide)
    
    return generator.generate_latex()
```

## Best Practices

1. **Theme Selection**: Choose themes appropriate for your audience and setting
2. **Content Structure**: Keep slides focused with clear hierarchies
3. **Figure Quality**: Use high-resolution images with clear captions
4. **Mathematics**: Use proper LaTeX math environments for equations
5. **Citations**: Maintain a well-formatted bibliography file
6. **Handouts**: Generate handouts for distribution to audience
7. **Testing**: Validate configuration and test compilation before presentation

## Troubleshooting

### Common Issues

1. **Missing LaTeX packages**: Install required packages through your LaTeX distribution
2. **Bibliography errors**: Ensure .bib file exists and is properly formatted
3. **Figure not found**: Check image paths are correct and files exist
4. **Font size issues**: Use valid Beamer font sizes (8pt-20pt)
5. **Compilation errors**: Check LaTeX syntax in custom commands

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging
generator = BeamerGenerator(config)
# ... operations will now log detailed information
```

This comprehensive Beamer generator provides all the tools needed for creating professional academic presentations with LaTeX Beamer, from simple slides to complex multi-media presentations with citations, mathematics, and advanced formatting.