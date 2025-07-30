# SlideGenie AI Service Documentation

## Overview

The SlideGenie AI service provides intelligent presentation generation capabilities using multiple LLM providers, advanced content processing, and cost optimization strategies.

## Architecture

### Core Components

1. **AI Provider Abstraction** (`app/services/ai/base.py`)
   - Unified interface for multiple LLM providers
   - Support for Anthropic Claude (primary) and OpenAI GPT-4 (fallback)
   - Structured output generation with Pydantic models
   - Token counting and cost estimation

2. **Content Processor** (`app/services/ai/content_processor.py`)
   - Academic paper parsing and section extraction
   - Intelligent text chunking respecting section boundaries
   - Key point and citation extraction
   - Figure/table reference detection

3. **Prompt Management** (`app/services/ai/prompt_manager.py`)
   - Version-controlled prompt templates
   - A/B testing capabilities
   - Performance tracking and optimization
   - Academic-specific prompt library

4. **Cost Optimizer** (`app/services/ai/cost_optimizer.py`)
   - Token counting before requests
   - Response caching with content hashing
   - Batch processing for efficiency
   - Budget monitoring and alerts
   - Provider selection based on cost/quality tradeoffs

5. **Generation Pipeline** (`app/services/ai/generation_pipeline.py`)
   - AsyncIO-based processing
   - Real-time progress tracking via WebSockets
   - Graceful fallbacks between providers
   - Error recovery mechanisms

## API Endpoints

### Generate Presentation

```http
POST /api/v1/generation/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "content": "Your research paper or abstract text...",
  "title": "Presentation Title",
  "options": {
    "audience": "academic researchers",
    "duration": 20,
    "slide_count": 15,
    "include_speaker_notes": true,
    "citation_style": "APA"
  }
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Generation started. Connect via WebSocket for updates."
}
```

### Stream Generation Updates

```http
POST /api/v1/generation/generate/stream
Content-Type: application/json
Authorization: Bearer <token>
```

Returns Server-Sent Events (SSE) stream with real-time updates.

### WebSocket Updates

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/generation/generate/ws/{job_id}');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`Progress: ${update.progress * 100}%`);
  console.log(`Status: ${update.message}`);
};
```

### Analyze Content

```http
POST /api/v1/generation/analyze
Content-Type: application/json
Authorization: Bearer <token>

{
  "content": "Your research paper text..."
}
```

**Response:**
```json
{
  "word_count": 3500,
  "estimated_slides": 18,
  "estimated_duration": 25.5,
  "detected_sections": ["introduction", "methods", "results", "discussion"],
  "key_topics": ["quantum computing", "error correction", "topological qubits"],
  "citations_found": 42
}
```

### Estimate Cost

```http
POST /api/v1/generation/estimate-cost
Content-Type: application/json
Authorization: Bearer <token>

{
  "content": "Your content...",
  "options": {}
}
```

**Response:**
```json
{
  "estimates": [
    {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "estimated_tokens": 2500,
      "estimated_cost": 0.0375,
      "cached": false,
      "cache_hit_probability": 0.3
    }
  ],
  "recommended_provider": "anthropic:claude-3-5-sonnet-20241022",
  "estimated_total_cost": 0.1125,
  "cache_savings_potential": 0.0337
}
```

## Configuration

### Environment Variables

```bash
# Required (at least one)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# AI Models
AI_MODEL_PRIMARY=claude-3-5-sonnet-20241022
AI_MODEL_FALLBACK=gpt-4o-mini

# Budget Limits (monthly USD)
AI_BUDGET_ANTHROPIC=1000.0
AI_BUDGET_OPENAI=500.0

# Cache Settings
AI_CACHE_TTL_DAYS=7
AI_CACHE_ENABLED=true
```

## Content Processing

### Academic Paper Structure

The content processor recognizes standard academic paper structures:

1. **Abstract** - Automatically extracted for outline generation
2. **Introduction/Background** - Used for context setting
3. **Methods/Methodology** - Visualized with diagrams
4. **Results** - Converted to charts and tables
5. **Discussion** - Key insights highlighted
6. **Conclusion** - Summary points extracted

### Chunking Strategy

- Respects section boundaries
- Maintains paragraph integrity
- Optimal chunk size: 1000 tokens
- Overlapping for context preservation

## Prompt Templates

### Available Content Types

1. **ABSTRACT_TO_OUTLINE** - Converts abstract to presentation structure
2. **CONTENT_TO_SLIDES** - Transforms content into slide format
3. **CITATION_FORMAT** - Formats references per style guide
4. **METHODOLOGY_VISUAL** - Creates visual representations
5. **RESULTS_SUMMARY** - Summarizes findings with visuals
6. **KEY_POINTS** - Extracts main arguments
7. **SPEAKER_NOTES** - Generates presentation notes

### Template Variables

- `{abstract}` - Paper abstract
- `{content}` - Section content
- `{audience}` - Target audience
- `{duration}` - Presentation duration
- `{slide_count}` - Number of slides
- `{citation_style}` - Citation format (APA, MLA, etc.)

## Cost Optimization

### Caching Strategy

1. **Content Hashing** - SHA256 hash of content + parameters
2. **TTL** - 7 days default, configurable
3. **Redis Backend** - Fast retrieval
4. **Hit Rate Tracking** - For optimization

### Provider Selection

```python
# Complex tasks → Anthropic Claude
- Abstract to outline generation
- Methodology visualization
- Results summarization

# Simple tasks → OpenAI GPT-4o-mini
- Citation formatting
- Key point extraction
- Speaker notes generation
```

### Batch Processing

- Groups similar content types
- Respects token limits (4000/batch)
- Priority-based ordering
- Reduces API calls by 30-50%

## Monitoring

### Metrics Tracked

1. **Usage Metrics**
   - Tokens consumed per provider/model
   - Cost per request
   - Cache hit rate
   - Average latency

2. **Quality Metrics**
   - Prompt performance scores
   - User feedback ratings
   - Error rates by provider

3. **Budget Tracking**
   - Daily/monthly spend
   - Budget utilization %
   - Cost per user/presentation

### Alerts

- 75% budget utilization warning
- 90% budget critical alert
- Provider failure notifications
- Abnormal latency detection

## Error Handling

### Retry Strategy

1. **Transient Errors** - 3 retries with exponential backoff
2. **Rate Limits** - Automatic provider switching
3. **API Failures** - Fallback to secondary provider
4. **Token Limits** - Content splitting and reassembly

### Error Codes

- `GEN_001` - Content too short
- `GEN_002` - Content too long
- `GEN_003` - Provider unavailable
- `GEN_004` - Budget exceeded
- `GEN_005` - Invalid content format

## Best Practices

### Content Preparation

1. **Clean Formatting** - Remove excessive whitespace
2. **Clear Sections** - Use standard headings
3. **Complete Sentences** - Avoid fragments
4. **Citations Included** - For proper formatting

### Optimal Settings

```json
{
  "audience": "academic researchers",
  "duration": 20,
  "slide_count": 15-20,
  "include_speaker_notes": true,
  "visual_complexity": "medium",
  "citation_style": "APA"
}
```

### Performance Tips

1. **Pre-analyze Content** - Use `/analyze` endpoint first
2. **Cache Warming** - Generate similar content together
3. **Batch Requests** - For multiple presentations
4. **Off-peak Hours** - Lower latency

## Troubleshooting

### Common Issues

1. **Slow Generation**
   - Check content length
   - Verify provider status
   - Consider simpler model

2. **Poor Quality Output**
   - Improve content structure
   - Adjust temperature settings
   - Try different provider

3. **High Costs**
   - Enable caching
   - Use appropriate models
   - Batch similar requests

4. **WebSocket Disconnects**
   - Check connection timeout
   - Implement reconnection logic
   - Use SSE as fallback

## Future Enhancements

1. **Multi-modal Input** - Support for images/charts
2. **Language Support** - Non-English presentations
3. **Custom Models** - Fine-tuned academic models
4. **Collaborative Generation** - Real-time co-editing
5. **Export Formats** - Direct PPTX/PDF generation