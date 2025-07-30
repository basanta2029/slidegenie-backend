# SlideGenie Quality Assurance System

A comprehensive quality assurance system for academic presentations that evaluates content across multiple dimensions and provides actionable feedback for improvement.

## Overview

The Quality Assurance (QA) system analyzes presentations across six key dimensions:

1. **Content Coherence** - Logical flow and consistent terminology
2. **Slide Transitions** - Smooth progression between slides  
3. **Citation Completeness** - Proper academic citations and references
4. **Timing Estimation** - Appropriate content density for presentation duration
5. **Visual Balance** - Well-distributed text and visual elements
6. **Readability** - Clear, accessible writing for target audience

## Architecture

The system follows a modular design with pluggable quality checkers:

```
quality/
├── base.py              # Base classes and interfaces
├── coherence.py         # Content coherence checker
├── transitions.py       # Slide transition validator
├── citations.py         # Citation completeness checker
├── timing.py           # Timing estimation validator
├── visual_balance.py   # Visual balance assessor
├── readability.py      # Readability scorer
├── metrics.py          # Quality metrics calculator
└── __init__.py         # Package exports
```

## Quick Start

```python
from app.services.slides.quality import create_quality_assurance_system, QualityMetricsCalculator

# Create QA system with all checkers
qa_system = create_quality_assurance_system()
metrics_calculator = QualityMetricsCalculator(qa_system)

# Run quality assessment
report = metrics_calculator.calculate_metrics(
    presentation=presentation,
    slides=slides,
    references=references
)

# Access results
print(f"Overall Score: {report.metrics.overall_score:.2f}")
print(f"Quality Level: {report.metrics.quality_level.value}")
print(f"Issues Found: {len(report.metrics.issues)}")
```

## Quality Dimensions

### 1. Content Coherence (`coherence.py`)
- **Weight**: 1.5 (highest priority)
- **Checks**:
  - Logical flow between slides
  - Terminology consistency
  - Section structure adherence
  - Topic coherence across presentation
  - Transition phrase usage

**Key Features**:
- Academic section detection (introduction, methods, results, conclusion)
- Keyword overlap analysis between slides
- Technical term consistency validation
- Transition phrase recognition

### 2. Slide Transitions (`transitions.py`)
- **Weight**: 1.0
- **Checks**:
  - Appropriate slide type sequences
  - Visual transition effects
  - Content density pacing
  - Section boundary transitions

**Key Features**:
- Slide type identification (title, overview, content, section, conclusion)
- Layout-content matching validation
- Transition effect appropriateness assessment

### 3. Citation Completeness (`citations.py`)
- **Weight**: 1.3 (high priority for academic integrity)
- **Checks**:
  - Uncited claims detection
  - Citation format consistency
  - Reference completeness
  - Citation-reference matching

**Key Features**:
- Pattern-based claim detection requiring citations
- Multiple citation format support (APA, IEEE, numbered)
- BibTeX field completeness validation
- Source diversity analysis

### 4. Timing Estimation (`timing.py`)
- **Weight**: 0.8
- **Checks**:
  - Individual slide timing appropriateness
  - Total presentation duration matching
  - Content density distribution
  - Pacing consistency

**Key Features**:
- Content-based time estimation (words, figures, equations)
- Reading speed calculations for academic content
- Density-based timing adjustments

### 5. Visual Balance (`visual_balance.py`)
- **Weight**: 1.0
- **Checks**:
  - Element distribution across slides
  - Content density appropriateness
  - Layout consistency
  - Text-visual balance

**Key Features**:
- Element counting and categorization
- Layout-content matching validation
- Visual hierarchy assessment
- Consistency checks across slides

### 6. Readability (`readability.py`)
- **Weight**: 1.0
- **Checks**:
  - Sentence structure and length
  - Vocabulary complexity for target audience
  - Text clarity and directness
  - Visual text elements
  - Style consistency

**Key Features**:
- Academic level-appropriate vocabulary analysis
- Passive voice detection
- Sentence length optimization
- Bullet point and title consistency

## Quality Metrics

### Scoring System
- **Overall Score**: 0.0 to 1.0 (weighted average of dimension scores)
- **Quality Levels**:
  - Excellent: ≥ 0.9
  - Good: 0.8 - 0.89
  - Satisfactory: 0.6 - 0.79
  - Needs Improvement: 0.4 - 0.59
  - Poor: < 0.4

### Issue Severity
- **Critical**: Major problems requiring immediate attention
- **Major**: Important issues affecting quality significantly
- **Minor**: Small improvements that would enhance quality
- **Suggestion**: Optional improvements for best practices

## Advanced Features

### Quality Tracking
```python
# Track quality over time
history = metrics_calculator.get_presentation_metrics_history(presentation_id)

# Compare presentations
comparison = metrics_calculator.compare_presentations(id1, id2)

# Generate insights
insights = metrics_calculator.generate_quality_insights(presentation_id)
```

### Custom Rules
```python
custom_rules = {
    'max_slides': 20,
    'min_references': 10,
    'required_sections': ['introduction', 'methodology', 'results'],
    'citation_style': 'ieee'
}

report = qa_system.assess_quality(
    presentation, slides, references, custom_rules
)
```

### Aggregated Analytics
```python
# Get organization-wide metrics
aggregated = metrics_calculator.get_aggregated_metrics(
    presentation_ids=org_presentations,
    time_period=timedelta(days=30)
)
```

## Dependencies

Add these to your `pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies ...
    "nltk>=3.8.1",              # For text processing
    "email-validator>=2.0.0",   # For pydantic email validation
    "statistics>=1.0.3.5",      # For statistical calculations
]
```

### NLTK Data
The system requires NLTK data for text processing:

```python
import nltk
nltk.download('punkt')        # Sentence tokenization
nltk.download('stopwords')    # Stop words for filtering
```

## Configuration

### Environment Variables
```bash
# Optional: Custom quality thresholds
QA_COHERENCE_WEIGHT=1.5
QA_CITATION_WEIGHT=1.3
QA_READABILITY_MIN_SCORE=0.6

# Academic level defaults
QA_DEFAULT_ACADEMIC_LEVEL=research
QA_DEFAULT_CITATION_STYLE=apa
```

### Custom Checker Registration
```python
# Create custom quality checker
class CustomChecker(QualityChecker):
    @property
    def dimension(self) -> QualityDimension:
        return QualityDimension.CUSTOM
    
    def check(self, presentation, slides, references):
        # Custom quality logic
        return score, issues, metadata

# Register with system
qa_system.register_checker(CustomChecker())
```

## Usage Examples

### Basic Quality Check
```python
from app.services.slides.quality import create_quality_assurance_system

qa_system = create_quality_assurance_system()
report = qa_system.assess_quality(presentation, slides, references)

print(f"Score: {report.metrics.overall_score:.2f}")
for issue in report.metrics.issues:
    print(f"- {issue.description}")
```

### Detailed Analysis
```python
# Get dimension-specific analysis
for dimension, analysis in report.detailed_analysis.items():
    print(f"\n{dimension.value.title()} Analysis:")
    if 'strengths' in analysis:
        for strength in analysis['strengths']:
            print(f"  ✓ {strength}")
```

### Export Results
```python
# Export as JSON
json_report = metrics_calculator.export_metrics(
    presentation_id=presentation.id,
    format='json'
)

# Export as CSV for analysis
csv_data = metrics_calculator.export_metrics(format='csv')
```

## Integration

### With Generation Pipeline
```python
# In your generation service
from app.services.slides.quality import create_quality_assurance_system

class PresentationGenerationService:
    def __init__(self):
        self.qa_system = create_quality_assurance_system()
    
    async def generate_and_validate(self, request):
        # Generate presentation
        presentation, slides = await self.generate_presentation(request)
        
        # Run quality check
        report = self.qa_system.assess_quality(presentation, slides)
        
        # Auto-improve if quality is low
        if report.metrics.overall_score < 0.7:
            presentation, slides = await self.improve_presentation(
                presentation, slides, report
            )
        
        return presentation, slides, report
```

### With API Endpoints
```python
@router.post("/presentations/{id}/quality-check")
async def check_presentation_quality(id: UUID):
    presentation = await get_presentation(id)
    slides = await get_slides(id)
    references = await get_references(id)
    
    report = qa_system.assess_quality(presentation, slides, references)
    return report.to_dict()
```

## Testing

Run the example usage script:
```bash
python -m app.services.slides.quality.example_usage
```

This will demonstrate the complete quality assessment workflow with sample data.

## Performance Considerations

- **Text Processing**: NLTK operations can be slow for large presentations
- **Memory Usage**: Quality reports store detailed metadata
- **Caching**: Consider caching quality assessments for unchanged presentations
- **Batch Processing**: Use async processing for multiple presentations

## Future Enhancements

1. **Machine Learning Integration**: Train models on quality patterns
2. **Custom Academic Styles**: Support for discipline-specific requirements
3. **Real-time Feedback**: Live quality scoring during editing
4. **Collaborative Feedback**: Multi-reviewer quality assessments
5. **A/B Testing**: Quality metric effectiveness measurement

## Contributing

When adding new quality checkers:

1. Inherit from `QualityChecker`
2. Implement required methods (`check`, `dimension`, `weight`)
3. Add comprehensive tests
4. Update this documentation
5. Consider performance implications

## Support

For issues or questions about the quality assurance system, please refer to the main SlideGenie documentation or contact the development team.