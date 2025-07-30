# Google Slides Generator

A comprehensive Google Slides integration for academic presentations with OAuth authentication, collaborative features, and automated formatting.

## Features

### Core Functionality
- **OAuth 2.0 Authentication**: Complete Google API authentication flow
- **Direct Google Drive Integration**: Upload and organize presentations
- **Format Preservation**: Convert internal slide format to Google Slides
- **Template System**: Academic and professional templates
- **Collaborative Sharing**: Permission management and link generation
- **Batch Operations**: Create multiple presentations efficiently
- **Progress Tracking**: Real-time progress updates for large operations
- **Export Capabilities**: PDF and PPTX export from Google Slides

### Academic Focus
- **University Branding**: Logo and color scheme integration
- **Citation Management**: Automatic references slide generation
- **Template Library**: IEEE, ACM, Nature, university-specific themes
- **Folder Organization**: Automatic organization by date/topic
- **Permission Control**: Fine-grained access control for academic environments

## Installation

Install required dependencies:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client httpx pillow requests
```

## Quick Start

### 1. Basic Setup

```python
from app.services.export.generators.google_slides_generator import (
    GoogleSlidesGenerator,
    GoogleCredentials,
    create_academic_google_slides_generator
)

# Configure credentials
credentials = GoogleCredentials(
    client_id="your_google_client_id",
    client_secret="your_google_client_secret"
)

# Create generator
generator = GoogleSlidesGenerator(credentials)
```

### 2. Authentication

```python
import asyncio

async def authenticate():
    # Start authentication flow
    auth_url = generator.authenticate_user("credentials.json")
    
    if auth_url != "authenticated":
        print(f"Visit: {auth_url}")
        auth_code = input("Enter authorization code: ")
        generator.complete_authentication(auth_code, "credentials.json")
    
    print("Authentication complete!")

# Run authentication
asyncio.run(authenticate())
```

### 3. Create Presentation

```python
from app.domain.schemas.generation import SlideContent, Citation

async def create_presentation():
    # Define slides
    slides = [
        SlideContent(
            title="Research Presentation",
            subtitle="Machine Learning Applications",
            body=[
                {"type": "text", "content": "Dr. Jane Smith"},
                {"type": "text", "content": "University of Technology"}
            ],
            metadata={"slide_type": "title"}
        ),
        SlideContent(
            title="Introduction",
            body=[
                {
                    "type": "bullet_list",
                    "items": [
                        "Background and motivation",
                        "Research objectives",
                        "Methodology overview"
                    ]
                }
            ]
        )
    ]
    
    # Create presentation
    result = await generator.create_presentation(
        slides=slides,
        title="ML Research Presentation",
        citations=[...],  # Optional citations
        metadata={"author": "Dr. Jane Smith", "department": "CS"}
    )
    
    print(f"Created: {result['presentation_id']}")
    print(f"View: {result['links']['view']}")
    return result

# Create presentation
asyncio.run(create_presentation())
```

## Advanced Usage

### Academic Template

```python
# Create academic generator with university branding
generator = create_academic_google_slides_generator(
    client_id="your_client_id",
    client_secret="your_client_secret",
    university_name="University of Technology",
    template_type=GoogleSlidesTemplate.FOCUS,
    theme_color="#003366"
)

# The generator will automatically:
# - Apply university branding
# - Organize presentations by date/topic
# - Use academic-appropriate templates
# - Restrict sharing permissions
```

### Collaborative Workflow

```python
from app.services.export.generators.google_slides_generator import (
    create_collaborative_google_slides_generator,
    PermissionRole
)

# Create collaborative generator
generator = create_collaborative_google_slides_generator(
    client_id="your_client_id",
    client_secret="your_client_secret",
    allow_public_sharing=True
)

# Create and share presentation
result = await generator.create_presentation(slides, "Team Presentation")

# Share with team members
generator.share_presentation(
    result['presentation_id'],
    "colleague@university.edu",
    PermissionRole.EDITOR,
    "Please review and provide feedback"
)

# Make publicly accessible
public_result = generator.make_presentation_public(
    result['presentation_id'],
    PermissionRole.VIEWER
)
```

### Batch Processing

```python
async def batch_create():
    # Prepare multiple presentations
    presentations_data = [
        {
            'title': 'Lecture 1: Introduction',
            'slides': lecture1_slides,
            'metadata': {'course': 'CS 101', 'lecture': 1}
        },
        {
            'title': 'Lecture 2: Fundamentals',
            'slides': lecture2_slides,
            'metadata': {'course': 'CS 101', 'lecture': 2}
        }
        # ... more presentations
    ]
    
    # Create all presentations in batch
    results = await generator.batch_create_presentations(
        presentations_data,
        progress_callback=lambda data: print(f"Progress: {data['progress_percent']:.1f}%")
    )
    
    # Process results
    successful = [r for r in results if r.get('status') == 'completed']
    print(f"Created {len(successful)} presentations successfully")

asyncio.run(batch_create())
```

## Configuration Options

### Google Credentials

```python
from app.services.export.generators.google_slides_generator import GoogleCredentials

credentials = GoogleCredentials(
    client_id="your_client_id",
    client_secret="your_client_secret",
    redirect_uri="http://localhost:8080/callback",  # Custom redirect
    scopes=[  # Custom scopes
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/drive.file"
    ]
)
```

### Drive Configuration

```python
from app.services.export.generators.google_slides_generator import DriveConfig

drive_config = DriveConfig(
    folder_name="My Presentations",
    parent_folder_id="parent_folder_id",  # Optional parent folder
    organize_by_date=True,  # Create YYYY-MM subfolders
    organize_by_topic=True,  # Create topic-based subfolders
    auto_create_folders=True  # Create folders automatically
)
```

### Template Configuration

```python
from app.services.export.generators.google_slides_generator import (
    TemplateConfig,
    GoogleSlidesTemplate
)

template_config = TemplateConfig(
    template_type=GoogleSlidesTemplate.FOCUS,
    theme_color="#1f4e79",  # Primary color
    font_family="Arial",
    university_name="University Name",
    logo_url="https://university.edu/logo.png",
    apply_branding=True
)
```

### Sharing Configuration

```python
from app.services.export.generators.google_slides_generator import (
    SharingConfig,
    PermissionRole
)

sharing_config = SharingConfig(
    default_role=PermissionRole.VIEWER,  # Default permission level
    allow_public_sharing=False,  # Restrict public access
    notify_on_share=True,  # Send notifications
    send_notification_email=True,  # Email notifications
    message="Default sharing message"
)
```

### Batch Configuration

```python
from app.services.export.generators.google_slides_generator import BatchConfig

batch_config = BatchConfig(
    max_concurrent_requests=5,  # Concurrent API requests
    retry_attempts=3,  # Retry failed requests
    retry_delay=1.0,  # Delay between retries (seconds)
    batch_size=100,  # Requests per batch
    rate_limit_delay=0.1  # Delay between batches
)
```

## Slide Content Format

### Basic Slide Structure

```python
from app.domain.schemas.generation import SlideContent

slide = SlideContent(
    title="Slide Title",
    subtitle="Optional Subtitle",
    body=[...],  # Content items
    speaker_notes="Notes for presenter",
    metadata={"slide_type": "content"}  # Optional metadata
)
```

### Content Types

#### Text Content
```python
{
    "type": "text",
    "content": "Plain text content with basic formatting support."
}
```

#### Bullet Lists
```python
{
    "type": "bullet_list",
    "items": [
        "First bullet point",
        "Second bullet point",
        "Third bullet point"
    ],
    "level": 0  # Indentation level (optional)
}
```

#### Images
```python
{
    "type": "image",
    "url": "https://example.com/image.png",  # Image URL
    "path": "/local/path/image.png",  # Or local path
    "alt_text": "Description of image",
    "caption": "Figure 1: Image caption"
}
```

#### Tables
```python
{
    "type": "table",
    "data": {
        "headers": ["Column 1", "Column 2", "Column 3"],
        "rows": [
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
        ]
    }
}
```

#### Charts
```python
{
    "type": "chart",
    "chart_type": "column",  # column, line, pie, bar
    "title": "Chart Title",
    "data": {
        "categories": ["Category 1", "Category 2", "Category 3"],
        "series": [
            {
                "name": "Series 1",
                "values": [10, 20, 30]
            },
            {
                "name": "Series 2", 
                "values": [15, 25, 35]
            }
        ]
    }
}
```

## Permission Management

### Share with Specific Users

```python
# Share with individual user
generator.share_presentation(
    presentation_id,
    "user@example.com",
    PermissionRole.EDITOR,
    "Please review this presentation"
)

# Bulk sharing
users = [
    ("student1@university.edu", PermissionRole.VIEWER),
    ("professor@university.edu", PermissionRole.COMMENTER),
    ("colleague@university.edu", PermissionRole.EDITOR)
]

for email, role in users:
    generator.share_presentation(presentation_id, email, role)
```

### Permission Roles

- `PermissionRole.VIEWER`: Can view the presentation
- `PermissionRole.COMMENTER`: Can view and comment
- `PermissionRole.EDITOR`: Can view, comment, and edit
- `PermissionRole.OWNER`: Full control (transfer ownership)

### Public Sharing

```python
# Make presentation publicly accessible
public_result = generator.make_presentation_public(
    presentation_id,
    PermissionRole.VIEWER
)

print(f"Public link: {public_result['links']['view']}")
```

## Export Features

### Export to PDF

```python
# Export presentation as PDF
pdf_buffer = generator.export_to_pdf(presentation_id)

# Save to file
with open("presentation.pdf", "wb") as f:
    f.write(pdf_buffer.getvalue())
```

### Export to PPTX

```python
# Export presentation as PowerPoint
pptx_buffer = generator.export_to_pptx(presentation_id)

# Save to file
with open("presentation.pptx", "wb") as f:
    f.write(pptx_buffer.getvalue())
```

## Error Handling

### Common Error Patterns

```python
from googleapiclient.errors import HttpError

try:
    result = await generator.create_presentation(slides, title)
except HttpError as e:
    if e.resp.status == 403:
        print("Permission denied - check API credentials")
    elif e.resp.status == 429:
        print("Rate limit exceeded - retry later")
    else:
        print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Retry Mechanisms

The generator includes built-in retry mechanisms for:
- Rate limit errors (HTTP 429)
- Temporary network issues
- Authentication token refresh

```python
# Configure retry behavior
batch_config = BatchConfig(
    retry_attempts=5,      # Retry up to 5 times
    retry_delay=2.0,       # Wait 2 seconds between retries
    rate_limit_delay=1.0   # Extra delay for rate limits
)

generator = GoogleSlidesGenerator(
    credentials,
    batch_config=batch_config
)
```

## Best Practices

### Authentication Management

1. **Store Credentials Securely**: Save OAuth tokens in secure location
2. **Handle Token Refresh**: Implement automatic token refresh
3. **Environment Variables**: Use environment variables for client credentials

```python
import os

credentials = GoogleCredentials(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
)
```

### Performance Optimization

1. **Batch Operations**: Use batch processing for multiple presentations
2. **Rate Limiting**: Respect API rate limits
3. **Concurrent Requests**: Limit concurrent requests appropriately

```python
# Optimize for large-scale operations
batch_config = BatchConfig(
    max_concurrent_requests=3,  # Conservative concurrency
    batch_size=50,              # Reasonable batch size
    rate_limit_delay=0.2        # Small delays between requests
)
```

### Content Organization

1. **Folder Structure**: Use consistent folder organization
2. **Naming Conventions**: Follow clear naming patterns
3. **Metadata**: Include relevant metadata for searchability

```python
# Consistent metadata structure
metadata = {
    "course": "CS 598",
    "semester": "Fall 2024",
    "topic": "Machine Learning",
    "author": "Dr. Smith",
    "version": "1.0"
}
```

### Error Recovery

1. **Progress Tracking**: Implement progress callbacks
2. **Partial Success Handling**: Handle partial failures in batch operations
3. **Logging**: Use comprehensive logging for debugging

```python
def progress_callback(data):
    # Log progress and handle errors
    if data.get('error'):
        logger.error(f"Error: {data['error']}")
    else:
        logger.info(f"Progress: {data['progress_percent']:.1f}%")
```

## API Limits and Quotas

### Google Slides API Limits

- **Requests per minute**: 100 per user
- **Requests per day**: 100,000 per project
- **Batch request size**: 100 requests per batch

### Best Practices for Limits

1. **Rate Limiting**: Use built-in rate limiter
2. **Batch Processing**: Group operations efficiently
3. **Error Handling**: Handle quota exceeded errors

```python
# Configure for API limits
rate_limiter = RateLimiter(requests_per_minute=90)  # Stay under limit
```

## Troubleshooting

### Common Issues

#### Authentication Errors
```
Error: invalid_client
```
**Solution**: Verify client ID and secret are correct

#### Permission Errors
```
Error: 403 Forbidden
```
**Solution**: Check API scopes and user permissions

#### Rate Limit Errors
```
Error: 429 Too Many Requests
```
**Solution**: Implement exponential backoff and retry

#### Network Errors
```
Error: Connection timeout
```
**Solution**: Implement retry with timeout handling

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('google_slides_generator')
logger.setLevel(logging.DEBUG)
```

### Testing

Run the test suite:

```bash
# Unit tests
python -m pytest test_google_slides_generator.py -v

# Integration tests (requires credentials)
python -m pytest test_google_slides_generator.py::IntegrationTestGoogleSlidesGenerator -v
```

## Examples

See `example_google_slides_usage.py` for comprehensive examples including:

- Basic presentation creation
- Academic template usage
- Collaborative workflows
- Batch processing
- Export operations
- Configuration examples

Run examples:

```bash
python example_google_slides_usage.py
```

## Contributing

1. Follow existing code patterns
2. Add comprehensive tests
3. Update documentation
4. Handle errors gracefully
5. Consider API rate limits

## Support

For issues and questions:

1. Check troubleshooting section
2. Review example usage
3. Check Google Slides API documentation
4. File issue with detailed error information