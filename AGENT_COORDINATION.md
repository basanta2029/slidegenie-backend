# SlideGenie Backend - Agent Coordination Guide

## Overview

This document outlines how to coordinate multiple agents working on different components of the SlideGenie backend. Each agent has specific responsibilities and interfaces to ensure smooth parallel development.

## Agent Assignments

### Agent 1: AI & Content Generation Services
**Location**: `/app/services/ai/`

**Responsibilities**:
- AI model integration (Claude, OpenAI)
- Content generation from abstracts/papers
- Citation extraction and formatting
- LaTeX equation processing
- Prompt engineering

**Key Interfaces**:
- `IAIService`
- `IContentGenerationService`
- `ICitationExtractionService`
- `ILatexProcessingService`
- `IPromptEngineeringService`

**Dependencies**:
- `httpx` for API calls
- `bibtexparser` for citations
- `latex2mathml` for equations

### Agent 2: Presentation & Slide Management
**Location**: `/app/services/presentation/`

**Responsibilities**:
- Presentation CRUD operations
- Slide management and reordering
- Collaboration features
- Version control
- Template application

**Key Interfaces**:
- `IPresentationService`
- `ISlideService`
- `ICollaborationService`
- `IVersionControlService`
- `ITemplateApplicationService`

**Dependencies**:
- Database repositories
- Cache service
- Event publishing

### Agent 3: Academic Features & References
**Location**: `/app/services/academic/`

**Responsibilities**:
- Reference management (BibTeX import/export)
- Academic database lookups (DOI, PubMed, arXiv)
- Template management and marketplace
- Institution branding

**Key Interfaces**:
- `IReferenceManagementService`
- `IAcademicLookupService`
- `ITemplateManagementService`
- `IInstitutionBrandingService`
- `ITemplateMarketplaceService`

**Dependencies**:
- External API clients
- Database repositories
- File storage

### Agent 4: File Processing & Storage
**Location**: `/app/services/storage/`

**Responsibilities**:
- PDF parsing and content extraction
- Image processing and optimization
- File storage (MinIO/S3)
- Export services (PDF, PPTX, LaTeX)
- Thumbnail generation

**Key Interfaces**:
- `IDocumentProcessingService`
- `IStorageService`
- `IExportService`
- `IThumbnailService`
- `IImageOptimizationService`

**Dependencies**:
- `PyPDF2` for PDF processing
- `python-pptx` for PowerPoint
- `Pillow` for image processing
- MinIO client

### Agent 5: Background Jobs & Queue System
**Location**: `/app/services/jobs/`

**Responsibilities**:
- Job queue management (Celery)
- Progress tracking
- Export job processing
- Generation job handling
- Scheduled jobs

**Key Interfaces**:
- `IJobQueueService`
- `IProgressTrackingService`
- `IExportJobService`
- `IGenerationJobService`
- `IScheduledJobService`

**Dependencies**:
- Celery
- Redis
- Database repositories

### Agent 6: Search & Analytics
**Location**: `/app/services/search/`

**Responsibilities**:
- Full-text search implementation
- Vector similarity search
- Analytics tracking
- Usage metrics
- Cost analysis

**Key Interfaces**:
- `ISearchService`
- `IEmbeddingService`
- `IAnalyticsService`
- `IUsageMetricsService`
- `ICostAnalysisService`

**Dependencies**:
- PostgreSQL full-text search
- pgvector
- Analytics database

## Communication Between Agents

### 1. Service Registry
All services register their interfaces in `/app/core/service_registry.py`:

```python
from app.services.ai import AIService
from app.services.presentation import PresentationService

SERVICE_REGISTRY = {
    'ai': AIService,
    'presentation': PresentationService,
    # ... other services
}
```

### 2. Event Bus
Services communicate through events in `/app/core/events.py`:

```python
# Agent 2 publishes event
await event_bus.publish('presentation.created', {
    'presentation_id': presentation_id,
    'user_id': user_id
})

# Agent 6 subscribes to track analytics
@event_handler('presentation.created')
async def track_presentation_created(data):
    await analytics_service.track_event('presentation_created', data)
```

### 3. Shared Data Models
All agents use common schemas from `/app/domain/schemas/`

### 4. API Contracts
Each agent exposes REST endpoints in `/app/api/v1/endpoints/`:
- Agent 1: `/api/v1/generation/`
- Agent 2: `/api/v1/presentations/`
- Agent 3: `/api/v1/references/`, `/api/v1/templates/`
- Agent 4: `/api/v1/files/`, `/api/v1/export/`
- Agent 5: `/api/v1/jobs/`
- Agent 6: `/api/v1/search/`, `/api/v1/analytics/`

## Development Workflow

### 1. Initial Setup (All Agents)
```bash
# Clone repository
git clone <repo-url>
cd slidegenie-backend

# Create feature branch
git checkout -b agent-X-feature-name

# Install dependencies
poetry install

# Start services
docker-compose up -d
```

### 2. Daily Development
1. **Morning Sync**: Check `#agent-coordination` channel
2. **Interface Updates**: Announce any interface changes
3. **Integration Tests**: Run before end of day
4. **PR Creation**: Include agent number in PR title

### 3. Integration Points

#### Week 1-2: Foundation
- All agents implement base service structure
- Define and agree on interfaces
- Set up database models and repositories

#### Week 3-4: Core Implementation
- Agent 1 & 2: Basic generation and presentation management
- Agent 3 & 4: File processing and reference management
- Agent 5 & 6: Queue system and basic search

#### Week 5-6: Integration
- Cross-agent feature implementation
- End-to-end testing
- Performance optimization

## Testing Strategy

### Unit Tests
Each agent maintains tests in `/tests/unit/services/<agent-area>/`

### Integration Tests
Cross-agent tests in `/tests/integration/`

### Mock Services
Use mock implementations for development:

```python
# /tests/mocks/ai_service_mock.py
class AIServiceMock:
    async def generate_completion(self, prompt, **kwargs):
        return {"content": "Mocked response"}
```

## Common Patterns

### 1. Service Initialization
```python
class MyService:
    def __init__(self, uow: UnitOfWork, cache: ICacheService):
        self.uow = uow
        self.cache = cache
```

### 2. Error Handling
```python
from app.core.exceptions import SlideGenieException

try:
    result = await external_service.call()
except Exception as e:
    raise ExternalServiceError("Service name", str(e))
```

### 3. Logging
```python
from app.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Operation completed", extra={"key": "value"})
```

### 4. Caching
```python
cache_key = f"presentation:{presentation_id}"
cached = await cache.get(cache_key)
if not cached:
    result = await expensive_operation()
    await cache.set(cache_key, result, ttl=3600)
```

## Deployment Considerations

### Environment Variables
Each agent may need specific env vars:
- Agent 1: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- Agent 3: `CROSSREF_API_KEY`, `PUBMED_API_KEY`
- Agent 4: `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- Agent 5: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

### Resource Requirements
- Agent 1: High CPU for AI processing
- Agent 4: High storage for file processing
- Agent 5: Redis memory for queue
- Agent 6: PostgreSQL resources for search

## Troubleshooting

### Common Issues

1. **Import Errors**: Check service registry and circular imports
2. **Database Conflicts**: Coordinate migration files
3. **API Timeouts**: Implement proper async handling
4. **Queue Bottlenecks**: Scale worker processes

### Debug Commands
```bash
# Check service health
make check-health

# View agent logs
docker-compose logs -f agent-X-service

# Run specific agent tests
pytest tests/unit/services/agent_X/
```

## Contact Points

- **Technical Lead**: Coordinate interface changes
- **DevOps**: Infrastructure and deployment
- **QA**: Integration test coordination

## Next Steps

1. Each agent should create their service implementation following the interfaces
2. Implement unit tests for all service methods
3. Create API endpoints for service exposure
4. Document any deviations from interfaces
5. Participate in daily integration tests

Remember: **Communication is key!** When in doubt, over-communicate about changes that might affect other agents.