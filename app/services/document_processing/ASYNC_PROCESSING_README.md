# Async Document Processing System

## Overview

This comprehensive async processing system provides scalable document handling with multipart uploads, background task processing, real-time progress tracking, and WebSocket-based updates. The system is designed for high throughput and reliability with support for distributed processing.

## Architecture

### Core Components

1. **AsyncDocumentProcessor** (`async_processor.py`)
   - Main coordinator for document processing workflows
   - Manages task orchestration and resource allocation
   - Provides comprehensive monitoring and metrics

2. **S3StorageManager** (`storage/s3_manager.py`)
   - Handles file storage with S3/MinIO integration
   - Supports multipart uploads for large files
   - Provides resumable upload capabilities

3. **TaskQueue** (`queue/task_queue.py`)
   - Manages background task processing
   - Supports both ARQ and Celery backends
   - Provides priority queuing and retry mechanisms

4. **ProgressTracker** (`progress/tracker.py`)
   - Real-time progress tracking with WebSocket support
   - Persistent progress history storage
   - Comprehensive analytics and metrics

## Features

### File Upload System

#### Multipart Upload Support
- **Chunked Uploads**: Large files are split into manageable chunks (default 8MB)
- **Resume Capability**: Interrupted uploads can be resumed from where they left off
- **Progress Tracking**: Real-time upload progress with WebSocket updates
- **Integrity Validation**: MD5 checksums for each chunk ensure data integrity

#### Simple Upload
- **Small Files**: Direct upload for files under the multipart threshold
- **File Validation**: Content-type validation and security scanning
- **Rate Limiting**: Configurable rate limits to prevent abuse

### Background Processing

#### Task Orchestration
The system processes documents through a multi-stage pipeline:

1. **Upload Stage**: File validation and storage
2. **Validation Stage**: Content validation and security checks
3. **Extraction Stage**: Content extraction using existing processors
4. **Analysis Stage**: Document analysis and metadata extraction
5. **Indexing Stage**: Search indexing and database updates
6. **Completion Stage**: Final processing and notifications

#### Queue Management
- **Priority Queues**: Support for LOW, NORMAL, HIGH, and CRITICAL priorities
- **Retry Logic**: Exponential backoff with configurable retry limits
- **Resource Management**: CPU and memory usage monitoring with throttling
- **Distributed Processing**: Support for multiple worker nodes

### Real-time Updates

#### WebSocket Integration
- **Progress Updates**: Real-time processing progress for subscribed clients
- **Job Status**: Live status updates for document processing jobs
- **System Notifications**: General system announcements and alerts
- **Multi-user Support**: User-specific subscriptions and notifications

#### Progress Tracking
- **Detailed Metrics**: Processing time, throughput, and resource usage
- **Historical Data**: Persistent storage of processing history
- **Analytics**: Comprehensive metrics and performance analysis

## API Endpoints

### Document Upload

#### POST `/api/v1/documents/upload/initiate`
Initiate a multipart upload session.

```json
{
  "filename": "document.pdf",
  "file_size": 52428800,
  "content_type": "application/pdf",
  "document_type": "pdf",
  "processing_options": {},
  "priority": "normal"
}
```

#### POST `/api/v1/documents/upload/chunk`
Upload a single chunk of a multipart upload.

```bash
curl -X POST \
  -F "upload_id=abc123" \
  -F "part_number=1" \
  -F "total_parts=10" \
  -F "chunk_hash=d41d8cd98f00b204e9800998ecf8427e" \
  -F "chunk_file=@chunk1.bin" \
  /api/v1/documents/upload/chunk
```

#### POST `/api/v1/documents/upload/complete/{upload_id}`
Complete a multipart upload and start processing.

#### POST `/api/v1/documents/upload/simple`
Simple upload for small files.

#### GET `/api/v1/documents/upload/status/{upload_id}`
Get upload status and progress.

#### DELETE `/api/v1/documents/upload/cancel/{upload_id}`
Cancel an in-progress upload.

#### GET `/api/v1/documents/upload/active`
List active uploads for the current user.

### WebSocket Endpoints

#### WS `/api/v1/ws/progress?token={jwt_token}`
Real-time progress updates for document processing.

```javascript
// Subscribe to job progress
websocket.send(JSON.stringify({
  type: "subscribe",
  user_id: "user-id",
  job_ids: ["job-1", "job-2"],
  channels: ["progress"]
}));

// Get job status
websocket.send(JSON.stringify({
  type: "get_job_status",
  job_id: "job-id"
}));

// Cancel job
websocket.send(JSON.stringify({
  type: "cancel_job",
  job_id: "job-id"
}));
```

#### WS `/api/v1/ws/notifications?token={jwt_token}`
General notifications and system updates.

## Configuration

### Environment Variables

```bash
# Storage Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=slidegenie
MINIO_USE_SSL=false

# Redis Configuration (for queues and caching)
REDIS_URL=redis://localhost:6379/0

# Async Processing Settings
ASYNC_PROCESSING_ENABLED=true
TASK_QUEUE_BACKEND=arq  # Options: arq, celery
MAX_CONCURRENT_TASKS=10
TASK_RETRY_MAX_ATTEMPTS=3
MULTIPART_UPLOAD_THRESHOLD_MB=100
UPLOAD_CHUNK_SIZE_MB=8

# WebSocket Settings
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765
WEBSOCKET_HEARTBEAT_INTERVAL=30

# Resource Management
MAX_MEMORY_MB_PER_TASK=2048
MAX_PROCESSING_TIME_MINUTES=60
CPU_THROTTLE_THRESHOLD=0.8

# Rate Limiting
RATE_LIMIT_UPLOADS_PER_MINUTE=10
RATE_LIMIT_REQUESTS_PER_MINUTE=100
```

### Application Settings

The system uses Pydantic settings for configuration management. See `app/core/config.py` for all available settings.

## Usage Examples

### Client-Side Upload (JavaScript)

```javascript
class DocumentUploader {
  constructor(apiBase, token) {
    this.apiBase = apiBase;
    this.token = token;
    this.chunkSize = 8 * 1024 * 1024; // 8MB
  }

  async uploadDocument(file, options = {}) {
    // Initiate multipart upload
    const initResponse = await fetch(`${this.apiBase}/documents/upload/initiate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        filename: file.name,
        file_size: file.size,
        content_type: file.type,
        document_type: options.documentType || 'pdf',
        priority: options.priority || 'normal'
      })
    });

    const { upload_id, job_id, chunk_size } = await initResponse.json();

    // Upload chunks
    const totalChunks = Math.ceil(file.size / chunk_size);
    
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunk_size;
      const end = Math.min(start + chunk_size, file.size);
      const chunk = file.slice(start, end);
      
      const formData = new FormData();
      formData.append('upload_id', upload_id);
      formData.append('part_number', i + 1);
      formData.append('total_parts', totalChunks);
      formData.append('chunk_hash', await this.calculateMD5(chunk));
      formData.append('is_final_chunk', i === totalChunks - 1);
      formData.append('chunk_file', chunk);

      await fetch(`${this.apiBase}/documents/upload/chunk`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`
        },
        body: formData
      });

      // Report progress
      const progress = ((i + 1) / totalChunks) * 100;
      this.onProgress?.(progress, 'Uploading');
    }

    // Complete upload
    const completeResponse = await fetch(
      `${this.apiBase}/documents/upload/complete/${upload_id}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      }
    );

    return await completeResponse.json();
  }

  async calculateMD5(data) {
    const buffer = await data.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('MD5', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }
}
```

### WebSocket Progress Tracking

```javascript
class ProgressTracker {
  constructor(wsUrl, token) {
    this.wsUrl = wsUrl;
    this.token = token;
    this.websocket = null;
  }

  connect() {
    this.websocket = new WebSocket(`${this.wsUrl}/progress?token=${this.token}`);
    
    this.websocket.onopen = () => {
      console.log('WebSocket connected');
    };

    this.websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.websocket.onclose = () => {
      console.log('WebSocket disconnected');
      // Implement reconnection logic
    };
  }

  subscribeToJobs(jobIds) {
    this.websocket.send(JSON.stringify({
      type: 'subscribe',
      user_id: 'current-user-id',
      job_ids: jobIds,
      channels: ['progress']
    }));
  }

  handleMessage(message) {
    switch (message.type) {
      case 'job_progress':
        this.onJobProgress?.(message.job_id, message.data);
        break;
      case 'job_status_response':
        this.onJobStatus?.(message.job_id, message.data);
        break;
      case 'connected':
        console.log('WebSocket connection confirmed');
        break;
      case 'error':
        console.error('WebSocket error:', message.message);
        break;
    }
  }

  getJobStatus(jobId) {
    this.websocket.send(JSON.stringify({
      type: 'get_job_status',
      job_id: jobId
    }));
  }

  cancelJob(jobId) {
    this.websocket.send(JSON.stringify({
      type: 'cancel_job',
      job_id: jobId
    }));
  }
}
```

## Monitoring and Metrics

### System Metrics

The system provides comprehensive metrics through various endpoints:

- **Processing Metrics**: Task completion rates, average processing times, error rates
- **Storage Metrics**: Upload/download speeds, storage usage, failed transfers
- **Queue Metrics**: Queue lengths, worker utilization, task priorities
- **WebSocket Metrics**: Active connections, message throughput, error rates

### Health Checks

- **Component Health**: Individual component status and health
- **Resource Usage**: CPU, memory, and disk usage monitoring
- **Dependency Status**: Database, Redis, S3/MinIO connectivity

## Error Handling

### Upload Errors
- **Chunk Validation**: MD5 mismatch handling with retry
- **Network Failures**: Automatic retry with exponential backoff
- **Storage Failures**: Graceful degradation and error reporting

### Processing Errors
- **Task Failures**: Retry logic with configurable limits
- **Resource Exhaustion**: Task throttling and queue management
- **External Dependencies**: Fallback mechanisms and circuit breakers

### Recovery Mechanisms
- **Upload Resume**: Automatic detection and resume of interrupted uploads
- **Task Recovery**: Failed task identification and reprocessing
- **Data Consistency**: Integrity checks and repair mechanisms

## Performance Optimization

### Upload Performance
- **Concurrent Chunks**: Parallel chunk uploads for faster transfers
- **Compression**: Optional compression for text-based documents
- **CDN Integration**: Support for CDN-based upload acceleration

### Processing Performance  
- **Resource Pooling**: Efficient resource allocation and pooling
- **Caching**: Intelligent caching of processing results
- **Load Balancing**: Distributed processing across multiple workers

### Storage Performance
- **Multipart Optimization**: Optimal chunk sizes based on file type
- **Storage Classes**: Intelligent storage class selection
- **Compression**: Automatic compression for archival storage

## Security Considerations

### Upload Security
- **File Type Validation**: Strict file type checking and validation
- **Content Scanning**: Malware and threat detection
- **Size Limits**: Configurable file size restrictions

### Access Control
- **Authentication**: JWT-based authentication for all endpoints
- **Authorization**: Role-based access control for sensitive operations
- **Rate Limiting**: Protection against abuse and DoS attacks

### Data Protection
- **Encryption**: Encryption at rest and in transit
- **Access Logging**: Comprehensive audit trails
- **Data Retention**: Configurable data retention policies

## Deployment

### Docker Deployment

```dockerfile
# Add to your existing Dockerfile
RUN pip install celery[redis] arq aioboto3 websockets aiofiles slowapi python-magic

# Environment variables
ENV ASYNC_PROCESSING_ENABLED=true
ENV TASK_QUEUE_BACKEND=arq
ENV REDIS_URL=redis://redis:6379/0
ENV MINIO_ENDPOINT=minio:9000
```

### Docker Compose

```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - ASYNC_PROCESSING_ENABLED=true
      - TASK_QUEUE_BACKEND=arq
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    depends_on:
      - redis
      - minio

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    command: server /data --console-address ":9001"
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: slidegenie-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: slidegenie
  template:
    metadata:
      labels:
        app: slidegenie
    spec:
      containers:
      - name: app
        image: slidegenie:latest
        env:
        - name: ASYNC_PROCESSING_ENABLED
          value: "true"
        - name: TASK_QUEUE_BACKEND
          value: "arq"
        - name: MAX_CONCURRENT_TASKS
          value: "10"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

## Testing

### Unit Tests

```python
import pytest
from app.services.document_processing.async_processor import AsyncDocumentProcessor

@pytest.mark.asyncio
async def test_document_processing():
    processor = AsyncDocumentProcessor()
    await processor.initialize()
    
    # Test processing request submission
    job_id = await processor.submit_processing_request(
        request=ProcessingRequest(...),
        user_id=test_user_id,
        priority=TaskPriority.NORMAL
    )
    
    assert job_id is not None
    
    # Test job status retrieval
    status = await processor.get_job_status(job_id)
    assert status.status == ProcessingStatus.PENDING
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_multipart_upload_flow():
    storage_manager = S3StorageManager()
    await storage_manager.initialize()
    
    # Test upload initiation
    upload_id = await storage_manager.start_multipart_upload(
        key="test/file.pdf",
        total_size=1024*1024,
        metadata={"test": "true"}
    )
    
    # Test chunk upload
    chunk_data = b"test data" * 1024
    part = await storage_manager.upload_part(
        upload_id=upload_id,
        part_number=1,
        data=chunk_data
    )
    
    assert part.etag is not None
    
    # Test upload completion
    result = await storage_manager.complete_multipart_upload(upload_id)
    assert result["key"] == "test/file.pdf"
```

## Troubleshooting

### Common Issues

1. **Upload Failures**
   - Check S3/MinIO connectivity and credentials
   - Verify bucket permissions and policies
   - Check network connectivity for large file transfers

2. **Task Processing Delays**
   - Monitor Redis queue lengths and worker availability
   - Check resource utilization (CPU, memory)
   - Verify database connectivity and performance

3. **WebSocket Connection Issues**
   - Check WebSocket server configuration and ports
   - Verify JWT token validity and user permissions
   - Monitor connection limits and rate limiting

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger("app.services.document_processing").setLevel(logging.DEBUG)
```

### Performance Monitoring

Use the built-in metrics endpoints to monitor system performance:

```bash
# Get processing metrics
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/documents/processing/metrics

# Get WebSocket statistics  
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/ws/stats
```

## Contributing

When contributing to the async processing system:

1. Follow the established patterns for error handling and logging
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Consider performance implications of changes
5. Ensure backward compatibility when possible

## License

This async processing system is part of the SlideGenie project and follows the same license terms.