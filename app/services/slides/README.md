# Slide Generation Service

A comprehensive, modular slide generation system for SlideGenie that supports multiple output formats, layouts, quality controls, and extensibility.

## Architecture Overview

The slide generation system is built with a modular architecture consisting of several key components:

```
SlideGenerationService (Main Interface)
├── Generators (Agent 1) - Format-specific slide generation
├── Layout Engine (Agent 2) - Responsive layout and styling
├── Rules Engine (Agent 3) - Content validation and rules
├── Quality Assurance (Agent 4) - Quality checking and improvement
├── Orchestrator (Agent 5) - Workflow coordination
└── Integration Layer (Agent 6) - Service integration and API
```

## Key Features

### Multi-Format Output Support
- **PowerPoint (PPTX)** - Full-featured presentations with animations
- **PDF** - Static presentations for sharing and printing
- **Google Slides** - Cloud-based collaborative presentations
- **Reveal.js** - Web-based interactive presentations
- **Markdown** - Simple text-based presentations

### Intelligent Layout System
- **Responsive Design** - Layouts adapt to content and constraints
- **Multiple Styles** - Minimal, Modern, Academic, Business, Creative
- **Smart Optimization** - Automatic layout selection based on content
- **Accessibility** - WCAG-compliant layouts with proper contrast and structure

### Quality Assurance
- **Readability Analysis** - Ensures content is appropriate for target audience
- **Consistency Checking** - Maintains uniform formatting throughout
- **Accessibility Validation** - Checks for alt text, color contrast, etc.
- **Grammar and Spelling** - Automated proofreading and correction

### Extensible Architecture
- **Plugin System** - Custom generators, layouts, rules, and quality checkers
- **Configuration Presets** - Quick setup for common use cases
- **API Extensions** - Easy integration with external services

## Quick Start

### Basic Usage

```python
from app.services.slides import SlideGenerationService
from app.services.slides.config import OutputFormat

# Initialize service
service = SlideGenerationService()

# Generate presentation
result_bytes, metadata = await service.generate_presentation(
    input_content="Your presentation content here",
    output_format=OutputFormat.PPTX
)

# Save to file
with open("presentation.pptx", "wb") as f:
    f.write(result_bytes)
```

### Using Presets

```python
# Generate academic presentation
result_bytes, metadata = await service.generate_from_preset(
    preset_name="academic_presentation",
    input_content="Research content...",
    overrides={"generator": {"max_slides": 15}}
)
```

### Preview Generation

```python
# Generate preview with limited slides
preview = await service.preview_presentation(
    input_content="Content to preview",
    max_slides=3
)
```

## Configuration

### Basic Configuration

```python
from app.services.slides.config import SlideGenerationConfig, LayoutStyle, QualityLevel

config = SlideGenerationConfig(
    generator={
        "format": "pptx",
        "max_slides": 20,
        "enable_animations": True
    },
    layout={
        "style": LayoutStyle.MODERN,
        "enable_accessibility": True
    },
    quality={
        "quality_level": QualityLevel.PREMIUM,
        "enable_spell_check": True
    }
)

service = SlideGenerationService(config=config)
```

### Available Presets

- **quick_draft** - Fast generation with minimal quality checks
- **academic_presentation** - Optimized for academic content with citations
- **business_pitch** - Professional styling with charts and timelines

### Custom Configuration

```python
# Load from file
config = SlideGenerationConfig.from_file("custom_config.json")

# Merge configurations
base_config = SlideGenerationConfig()
custom_config = base_config.merge_with({
    "generator": {"max_slides": 30},
    "quality": {"quality_level": "premium"}
})
```

## API Endpoints

### Generation Endpoints

```http
POST /api/v1/slides/generate
Content-Type: application/json

{
    "content": "Presentation content",
    "output_format": "pptx",
    "title": "My Presentation",
    "options": {
        "max_slides": 10,
        "style": "modern"
    }
}
```

### Advanced Generation with File Upload

```http
POST /api/v1/slides/generate-advanced
Content-Type: multipart/form-data

content: [file.txt]
layout_style: modern
quality_level: standard
max_slides: 15
```

### Preview and Validation

```http
POST /api/v1/slides/preview
Content-Type: application/json

{
    "content": "Content to preview",
    "max_slides": 3
}
```

```http
POST /api/v1/slides/validate
Content-Type: application/json

{
    "content": "Content to validate"
}
```

### Job Management

```http
GET /api/v1/slides/job/{job_id}
DELETE /api/v1/slides/job/{job_id}
GET /api/v1/slides/download/{job_id}
```

### Information Endpoints

```http
GET /api/v1/slides/formats        # Supported output formats
GET /api/v1/slides/styles         # Available layout styles
GET /api/v1/slides/presets        # Configuration presets
```

## Extension Development

### Creating a Custom Generator

```python
from app.services.slides.extensions import GeneratorExtension
from app.services.slides.interfaces import PresentationContent

class CustomFormatGenerator(GeneratorExtension):
    @property
    def name(self) -> str:
        return "custom_format"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def initialize(self, config):
        self.settings = config
    
    def supports_format(self, format: str) -> bool:
        return format == "custom"
    
    async def generate(self, content: PresentationContent, format: str, options):
        # Custom generation logic
        return custom_output_bytes
```

### Creating Custom Rules

```python
from app.services.slides.extensions import RuleExtension
from app.services.slides.interfaces import ValidationResult

class CustomRule(RuleExtension):
    @property
    def name(self) -> str:
        return "custom_rule"
    
    def get_rules(self):
        return [{"name": "custom_validation", "category": "content"}]
    
    def validate(self, content):
        # Custom validation logic
        return ValidationResult(is_valid=True)
```

### Registering Extensions

```python
from app.services.slides.extensions import ExtensionRegistry

registry = ExtensionRegistry()
registry.register(CustomFormatGenerator)
registry.enable("custom_format", {"setting1": "value1"})

service = SlideGenerationService(extension_registry=registry)
```

## Testing

### Running Tests

```bash
# Run all slide generation tests
pytest tests/test_slide_*.py -v

# Run specific test files
pytest tests/test_slide_generators.py
pytest tests/test_slide_layouts.py
pytest tests/test_slide_rules.py
pytest tests/test_slide_quality.py
pytest tests/test_slide_orchestrator.py

# Run integration tests
pytest tests/test_slide_service_integration.py
pytest tests/test_slides_api_integration.py
```

### Test Coverage

The test suite includes:
- **Unit Tests** - Individual component testing
- **Integration Tests** - Cross-component interactions
- **API Tests** - Endpoint testing with mocked services
- **Performance Tests** - Concurrent generation and memory usage
- **Edge Case Tests** - Error handling and unusual inputs

## Performance Considerations

### Optimization Features

- **Parallel Processing** - Multiple slides generated concurrently
- **Lazy Loading** - Components loaded on demand
- **Caching** - Results cached for repeated requests
- **Streaming** - Large presentations can be streamed
- **Memory Management** - Automatic cleanup of large objects

### Monitoring

```python
# Enable performance monitoring
config = SlideGenerationConfig(
    enable_telemetry=True,
    enable_debugging=True,
    performance={
        "enable_memory_optimization": True,
        "max_memory_usage_mb": 512
    }
)
```

## Security

### Input Validation
- All input content is validated before processing
- File uploads are restricted by type and size
- Malicious content patterns are detected and blocked

### Rate Limiting
- Generation requests are rate-limited per user
- Resource usage is monitored and controlled
- Abuse prevention mechanisms are in place

### Access Control
- Role-based permissions for different features
- API key authentication for external access
- Audit logging for all operations

## Troubleshooting

### Common Issues

1. **Generation Timeout**
   - Increase `timeout_seconds` in orchestrator config
   - Reduce `max_slides` limit
   - Enable parallel processing

2. **Quality Score Too Low**
   - Use higher quality level
   - Enable quality improvement
   - Check content for common issues

3. **Memory Issues**
   - Enable memory optimization
   - Reduce concurrent workers
   - Use streaming for large outputs

4. **Extension Not Loading**
   - Check extension dependencies
   - Verify configuration syntax
   - Review extension registry logs

### Debug Mode

```python
config = SlideGenerationConfig(
    enable_debugging=True,
    log_level="DEBUG"
)
```

### Logging

The service uses structured logging with the following levels:
- **DEBUG** - Detailed execution information
- **INFO** - General operational messages
- **WARN** - Potential issues and recoverable errors
- **ERROR** - Serious problems requiring attention

## Contributing

### Development Setup

1. Install dependencies: `poetry install`
2. Run tests: `pytest`
3. Format code: `black app/services/slides/`
4. Type checking: `mypy app/services/slides/`

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Maintain test coverage above 90%

### Submitting Changes

1. Create feature branch
2. Write tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit pull request

## License

This slide generation system is part of SlideGenie and is subject to the project's licensing terms.