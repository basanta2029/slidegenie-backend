# SlideGenie Academic Slide Generators

This module provides specialized slide generators for creating academic presentations with proper formatting, structure, and visual suggestions.

## Overview

The slide generator system is designed to transform structured academic content into presentation slides with:
- **Academic formatting rules** (bullet limits, word counts, citation styles)
- **Visual suggestions** for diagrams, charts, and layouts
- **Speaker notes** generation
- **Extensible architecture** for new slide types

## Architecture

### Base Generator (`base.py`)
- `BaseSlideGenerator`: Abstract base class for all generators
- `GeneratorOptions`: Configuration options (language, academic level, citation style)
- `GeneratorInput`: Input data structure with content, context, and options
- Common utilities for formatting, visual suggestions, and slide creation

### Section Generators

| Generator | Purpose | Key Features |
|-----------|---------|--------------|
| **TitleSlideGenerator** | Title slides | Author formatting, affiliations, conference info |
| **OutlineGenerator** | Table of contents | Timeline view, navigation links, duration estimates |
| **IntroductionGenerator** | Background & motivation | Problem statements, research questions, contributions |
| **LiteratureReviewGenerator** | Related work | Categorization, comparison tables, timeline views |
| **MethodologyGenerator** | Approach details | Architecture diagrams, algorithms, implementation |
| **ResultsGenerator** | Experimental findings | Visualizations, statistical tests, ablation studies |
| **DiscussionGenerator** | Analysis & implications | Limitations, validity threats, positioning |
| **ConclusionGenerator** | Summary & future work | Impact assessment, lessons learned, call-to-action |
| **ReferencesGenerator** | Bibliography | Multiple citation styles (IEEE, APA, MLA, Chicago, ACM) |

## Usage

### Basic Usage

```python
from app.services.slides.generators import get_generator, GeneratorInput, GeneratorOptions

# Get a generator
generator = get_generator("introduction")

# Prepare content
content = {
    "background": {
        "context": "Machine learning has transformed industries...",
        "gaps": ["Limited scalability", "High computational cost"]
    },
    "research_questions": [
        "RQ1: Can we improve efficiency?",
        "RQ2: How does this affect accuracy?"
    ]
}

# Configure options
options = GeneratorOptions(
    language="en",
    academic_level="research",
    presentation_type="conference",
    citation_style="ieee"
)

# Generate slides
input_data = GeneratorInput(content=content, options=options)
slides = generator.generate(input_data)
```

### Pipeline Usage

```python
from app.services.slides.generators import create_generator_pipeline, get_presentation_structure

# Get standard structure for conference presentation
sections = get_presentation_structure("conference")
# Returns: ["title", "outline", "introduction", "methodology", "results", "conclusion", "references"]

# Create generator pipeline
generators = create_generator_pipeline(sections)

# Process each section
all_slides = []
for generator, section_content in zip(generators, section_contents):
    slides = generator.generate(GeneratorInput(content=section_content, options=options))
    all_slides.extend(slides)
```

## Content Structure

Each generator expects specific content structures. Here are examples:

### Title Generator
```python
content = {
    "title": "Novel Approach to Machine Learning",
    "subtitle": "Advancing the State of the Art",
    "authors": [
        {
            "name": "John Smith",
            "affiliation": "University of Example",
            "email": "john.smith@example.edu",
            "is_corresponding": True
        }
    ],
    "conference": {
        "name": "International Conference on AI",
        "acronym": "ICAI 2024",
        "date": "March 15-17, 2024",
        "location": "San Francisco, CA"
    }
}
```

### Results Generator
```python
content = {
    "experiments": [
        {
            "name": "Performance Evaluation",
            "results": {
                "metrics": {"accuracy": 0.95, "f1": 0.93},
                "comparison": {
                    "our_method": {"accuracy": 0.95},
                    "baseline": {"accuracy": 0.87}
                }
            }
        }
    ],
    "statistical_significance": {
        "tests": [
            {
                "name": "t-test",
                "p_value": 0.002,
                "significant": True
            }
        ]
    }
}
```

## Features

### Academic Formatting
- **Bullet point limits**: Max 6 bullets per slide, 25 words per bullet
- **Content splitting**: Automatically splits long content across slides
- **Citation formatting**: Multiple academic styles (IEEE, APA, MLA, Chicago, ACM)
- **Visual hierarchy**: Proper heading levels and emphasis

### Visual Suggestions
Generators create structured suggestions for visual elements:
```python
{
    "type": "visual_suggestion",
    "visual_type": "diagram",
    "description": "System architecture showing components and data flow",
    "data": {"components": [...], "connections": [...]},
    "caption": "System Architecture"
}
```

### Speaker Notes
Each slide includes automatically generated speaker notes:
- Contextual information about content
- Transition suggestions
- Time estimates and pacing advice

### Extensibility
Add new generators by:
1. Extending `BaseSlideGenerator`
2. Implementing required abstract methods
3. Adding to `GENERATOR_REGISTRY`

```python
class CustomGenerator(BaseSlideGenerator):
    @property
    def section_type(self) -> str:
        return "custom_section"
    
    @property 
    def default_layout(self) -> str:
        return "content"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        # Implementation here
        pass
```

## Presentation Structures

Pre-defined structures for different presentation types:

- **Academic**: Full research presentation (9 sections)
- **Conference**: Shorter conference talk (7 sections)  
- **Defense**: Comprehensive thesis defense (9 sections)
- **Lecture**: Educational presentation (5 sections)

## Integration

The generators integrate with:
- **SlideContent schema**: Structured slide data format
- **Citation system**: BibTeX and formatted references
- **Template system**: Layout and styling configuration
- **Export pipeline**: Multiple output formats (PPTX, PDF, LaTeX)

## Configuration Options

### GeneratorOptions
- `language`: Presentation language (default: "en")
- `academic_level`: Target audience level ("undergraduate", "graduate", "research")
- `presentation_type`: Presentation context ("conference", "lecture", "defense", "seminar")
- `citation_style`: Bibliography format ("ieee", "apa", "mla", "chicago", "acm")
- `include_speaker_notes`: Generate speaker notes (default: True)
- `max_bullets_per_slide`: Maximum bullet points per slide (default: 6)
- `max_words_per_bullet`: Maximum words per bullet point (default: 25)

### Content Guidelines
- Use structured dictionaries for complex content
- Include metadata for enhanced processing
- Provide context for better visual suggestions
- Follow naming conventions for consistency

## Error Handling

Generators include validation and error handling:
- Input validation with descriptive error messages
- Graceful handling of missing optional content
- Fallback behavior for malformed data
- Logging for debugging and monitoring

## Future Extensions

The architecture supports future enhancements:
- **Interactive elements**: Polls, quizzes, animations
- **Multilingual support**: Content translation and localization
- **AI-enhanced generation**: Smart content suggestions and optimization
- **Domain-specific generators**: Medicine, engineering, business specializations
- **Collaborative features**: Version control and multi-author support