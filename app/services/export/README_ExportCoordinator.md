# SlideGenie Export Coordinator System

A comprehensive export orchestration system that manages the complete export pipeline for presentations across multiple formats including PowerPoint, LaTeX Beamer, PDF, and Google Slides.

## Overview

The Export Coordinator system provides:

- **Format Orchestration**: Unified management of PowerPoint, LaTeX Beamer, PDF, and Google Slides exports
- **Progress Tracking**: Real-time progress monitoring with unified status reporting
- **Error Recovery**: Format-specific fallback strategies and error handling
- **Resource Management**: Load balancing and resource allocation across export generators
- **Export Validation**: Quality assurance and validation checks
- **Template Consistency**: Consistent template management across all formats
- **Configuration Management**: User preferences and export settings management
- **API Integration**: RESTful endpoints and WebSocket support

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Layer    │────│ Export Coordinator │────│ Config Manager  │
│                │    │                    │    │                 │
│ - REST API     │    │ - Job Management   │    │ - User Prefs    │
│ - WebSocket    │    │ - Progress Track   │    │ - Templates     │
│ - Validation   │    │ - Error Handling   │    │ - Validation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼───┐ ┌───▼───┐ ┌───▼────┐
            │ Resource  │ │Export │ │Quality │
            │ Manager   │ │Validator│ │Checker │
            └───────────┘ └───────┘ └────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
              ┌─────▼───┐ ┌───▼───┐ ┌───▼────┐ ┌─────────┐
              │  PPTX   │ │Beamer │ │  PDF   │ │ Google  │
              │Generator│ │Gen    │ │ Gen    │ │ Slides  │
              └─────────┘ └───────┘ └────────┘ └─────────┘
```

## Core Components

### 1. ExportCoordinator

The central orchestrator that manages all export operations:

```python
from app.services.export.export_coordinator import (
    ExportCoordinator,
    ExportConfig,
    ExportFormat,
    ExportQuality,
    create_export_coordinator
)

# Create coordinator
coordinator = create_export_coordinator(max_concurrent_exports=5)

# Submit export job
config = ExportConfig(
    format=ExportFormat.PPTX,
    template_name="ieee",
    quality=ExportQuality.HIGH,
    fallback_formats=[ExportFormat.PDF]
)

job_id = await coordinator.submit_export_job(
    slides=slides,
    config=config,
    citations=citations,
    user_id="user123"
)
```

### 2. Export Configuration

Comprehensive configuration system with inheritance:

```python
from app.services.export.config_manager import (
    ConfigManager,
    BrandingConfig,
    TypographyConfig,
    create_config_manager
)

# Create config manager
config_manager = create_config_manager()

# Customize user preferences
preferences = config_manager.get_user_preferences("user123")
preferences.branding = BrandingConfig(
    university_name="Stanford University",
    logo_position="top_left",
    color_scheme={
        "primary": "#8C1515",
        "secondary": "#B83A4B"
    }
)

# Save preferences
config_manager.save_user_preferences("user123", preferences)
```

### 3. Progress Tracking

Real-time progress monitoring with callbacks:

```python
# Monitor progress
progress = await coordinator.get_job_progress(job_id)
print(f"Progress: {progress.progress_percent}% - {progress.current_step}")

# Add progress callback
async def progress_callback(progress):
    print(f"Job {progress.job_id}: {progress.progress_percent}%")

coordinator.add_progress_callback(job_id, progress_callback)
```

### 4. Quality Validation

Comprehensive export validation:

```python
# Get export result with validation
result = await coordinator.get_job_result(job_id)
validation = result.validation_results

print(f"Quality score: {validation['score']}/100")
for check_name, passed in validation['checks'].items():
    print(f"{'✓' if passed else '✗'} {check_name}")
```

## API Endpoints

### Job Management

- `POST /api/v1/export/jobs` - Submit export job
- `GET /api/v1/export/jobs/{job_id}/progress` - Get job progress
- `GET /api/v1/export/jobs/{job_id}/result` - Get job result
- `GET /api/v1/export/jobs/{job_id}/download` - Download file
- `DELETE /api/v1/export/jobs/{job_id}` - Cancel job

### Format and Template Management

- `GET /api/v1/export/formats` - List supported formats
- `GET /api/v1/export/formats/{format}/templates` - Get format templates
- `GET /api/v1/export/jobs` - Export history
- `GET /api/v1/export/stats` - Export statistics

### WebSocket

- `WS /api/v1/export/jobs/{job_id}/progress/ws` - Real-time progress updates

## Export Formats

### 1. PowerPoint (PPTX)

- **Templates**: IEEE, ACM, Nature, MIT, Custom
- **Features**: Animations, slide masters, embedded fonts
- **Quality**: Standard to Premium with different DPI settings
- **Output**: `.pptx` file with full PowerPoint compatibility

### 2. LaTeX Beamer

- **Templates**: Berlin, Madrid, Warsaw, Singapore, etc.
- **Features**: Mathematical equations, bibliography, custom themes
- **Quality**: High-resolution PDF compilation
- **Output**: `.tex` source and compiled `.pdf`

### 3. PDF

- **Formats**: Slides, handouts, notes
- **Features**: Bookmarks, hyperlinks, security settings
- **Quality**: Configurable compression and optimization
- **Output**: Standard PDF with metadata

### 4. Google Slides

- **Integration**: Direct upload to Google Drive
- **Features**: Sharing permissions, collaboration
- **Templates**: Academic, Corporate, Creative
- **Output**: Google Slides presentation with sharing URLs

## Configuration System

### Hierarchical Configuration

Configurations inherit and override in this order:

1. **System Defaults** - Base system configuration
2. **Organization Settings** - Organization-wide preferences
3. **User Preferences** - User-specific settings
4. **Project Overrides** - Project-specific customizations
5. **Job Settings** - Job-specific overrides

### Configuration Sections

#### Branding Configuration
```python
@dataclass
class BrandingConfig:
    logo_url: Optional[str] = None
    logo_position: str = "top_right"
    university_name: Optional[str] = None
    custom_footer: Optional[str] = None
    show_slide_numbers: bool = True
    color_scheme: Dict[str, str] = field(default_factory=dict)
```

#### Typography Configuration
```python
@dataclass
class TypographyConfig:
    title_font: str = "Arial"
    body_font: str = "Arial"
    title_size: int = 44
    body_size: int = 24
    line_height: float = 1.2
```

#### Layout Configuration
```python
@dataclass
class LayoutConfig:
    slide_size: str = "16:9"  # 16:9, 4:3, 16:10
    margins: Dict[str, float] = field(default_factory=dict)
    content_spacing: float = 0.25
    image_max_width: float = 0.8
```

#### Quality Configuration
```python
@dataclass
class QualityConfig:
    image_dpi: int = 300
    image_quality: int = 95
    compression_level: str = "moderate"
    include_metadata: bool = True
    embed_fonts: bool = True
```

## Resource Management

### Load Balancing

The system automatically balances load across export generators:

- **Global Limit**: Maximum concurrent exports (default: 5)
- **Format Limits**: Per-format concurrency limits
- **Priority Queue**: High-priority jobs get preference
- **Resource Allocation**: Automatic resource allocation and release

### Format-Specific Limits

- **Google Slides**: 2 concurrent (API rate limits)
- **LaTeX Beamer**: 3 concurrent (compilation overhead)
- **PDF**: 4 concurrent (moderate processing)
- **PowerPoint**: 5 concurrent (lightweight)

## Error Handling and Fallbacks

### Fallback Strategy

When primary format fails, the system automatically tries fallback formats:

```python
config = ExportConfig(
    format=ExportFormat.GOOGLE_SLIDES,  # Primary
    fallback_formats=[ExportFormat.PPTX, ExportFormat.PDF]  # Fallbacks
)
```

### Error Recovery

- **Validation Errors**: Pre-export content validation
- **Generation Failures**: Format-specific error handling
- **Resource Exhaustion**: Automatic queuing and retry
- **Timeout Handling**: Configurable timeouts with cleanup

## Quality Assurance

### Validation System

The system performs comprehensive validation:

1. **Pre-Export Validation**
   - Slide content structure
   - Required fields presence
   - Content size limits

2. **Post-Export Validation**
   - File integrity checks
   - Format-specific validation
   - Quality metrics calculation

3. **Quality Scoring**
   - Overall quality score (0-100)
   - Individual check results
   - Recommendations for improvement

### Validation Rules

- `check_file_integrity` - Verify file structure
- `validate_slide_count` - Ensure correct slide count
- `check_image_quality` - Validate image resolution
- `validate_text_readability` - Check text formatting

## Monitoring and Statistics

### System Statistics

```python
stats = coordinator.get_statistics()
print(f"Total exports: {stats['total_exports']}")
print(f"Success rate: {stats['successful_exports']/stats['total_exports']*100:.1f}%")
```

### Health Monitoring

```python
health = await coordinator.health_check()
print(f"System status: {health['status']}")
for check, result in health['checks'].items():
    print(f"{check}: {result}")
```

### Performance Metrics

- Average processing times per format
- Resource utilization statistics
- Error rates and patterns
- Queue depth and wait times

## Usage Examples

### Basic Export

```python
import asyncio
from app.services.export.export_coordinator import *

async def basic_export():
    coordinator = create_export_coordinator()
    
    config = ExportConfig(
        format=ExportFormat.PPTX,
        template_name="ieee",
        quality=ExportQuality.HIGH
    )
    
    job_id = await coordinator.submit_export_job(
        slides=slides,
        config=config,
        user_id="user123"
    )
    
    # Wait for completion
    while True:
        progress = await coordinator.get_job_progress(job_id)
        if progress.status.value == "completed":
            break
        await asyncio.sleep(1)
    
    result = await coordinator.get_job_result(job_id)
    print(f"Export completed: {result.file_path}")

asyncio.run(basic_export())
```

### Parallel Exports

```python
async def parallel_exports():
    coordinator = create_export_coordinator()
    
    formats = [ExportFormat.PPTX, ExportFormat.PDF, ExportFormat.BEAMER]
    jobs = []
    
    for fmt in formats:
        config = ExportConfig(format=fmt, template_name="default")
        job_id = await coordinator.submit_export_job(
            slides=slides, config=config, user_id="user123"
        )
        jobs.append(job_id)
    
    # Wait for all to complete
    while jobs:
        for job_id in jobs[:]:
            progress = await coordinator.get_job_progress(job_id)
            if progress.status.value in ["completed", "failed"]:
                jobs.remove(job_id)
                print(f"Job {job_id} completed")
        await asyncio.sleep(1)

asyncio.run(parallel_exports())
```

### Custom Configuration

```python
from app.services.export.config_manager import *

def setup_custom_config():
    config_manager = create_config_manager()
    
    # Create custom branding
    branding = BrandingConfig(
        university_name="My University",
        logo_position="top_left",
        color_scheme={
            "primary": "#003f7f",
            "secondary": "#0066cc",
            "accent": "#ff6600"
        }
    )
    
    # Create preferences
    preferences = ExportPreferences(branding=branding)
    
    # Save for user
    config_manager.save_user_preferences("user123", preferences)
    
    # Use in export
    config = config_manager.get_format_config(
        user_id="user123",
        format=ExportFormat.PPTX,
        template_name="custom"
    )
```

## Integration with SlideGenie

### Database Integration

The system integrates with SlideGenie's database for:

- User preferences storage
- Export job history
- Template management
- Analytics and reporting

### Authentication

All API endpoints require authentication:

```python
from app.api.v1.dependencies import get_current_user

@router.post("/export/jobs")
async def submit_export(
    request: ExportRequest,
    current_user: UserRead = Depends(get_current_user)
):
    # Export logic here
```

### WebSocket Integration

Real-time progress updates via WebSocket:

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/export/jobs/${jobId}/progress/ws`);
ws.onmessage = (event) => {
    const progress = JSON.parse(event.data);
    updateProgressBar(progress.progress_percent);
};
```

## Deployment and Scaling

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

```env
# Export Configuration
MAX_CONCURRENT_EXPORTS=5
EXPORT_STORAGE_PATH=/app/exports
EXPORT_CLEANUP_HOURS=24

# Google Slides Integration
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# LaTeX Configuration
LATEX_COMPILER=pdflatex
LATEX_TIMEOUT=300
```

### Scaling Considerations

- **Horizontal Scaling**: Multiple coordinator instances with shared storage
- **Resource Limits**: Configure per-format concurrency based on resources
- **Storage Management**: Automatic cleanup of temporary files
- **Monitoring**: Health checks and metrics collection

## Security

### File Security

- Temporary file cleanup
- Secure file storage paths
- Access control on generated files
- Virus scanning integration points

### API Security

- Authentication required for all endpoints
- Rate limiting on export submissions
- Input validation and sanitization
- CORS configuration for web clients

### Data Privacy

- User data encryption in transit and at rest
- Configurable data retention policies
- GDPR compliance features
- Audit logging for all operations

## Troubleshooting

### Common Issues

1. **Export Failures**
   - Check generator availability
   - Verify input data format
   - Review error logs

2. **Performance Issues**
   - Monitor resource usage
   - Adjust concurrency limits
   - Check queue depth

3. **Quality Issues**
   - Review validation results
   - Check template configurations
   - Verify input content quality

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger('app.services.export').setLevel(logging.DEBUG)
```

Check health status:

```bash
curl http://localhost:8000/api/v1/export/health
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Consider backward compatibility
5. Add appropriate error handling

## License

This project is part of the SlideGenie system and follows the same licensing terms.