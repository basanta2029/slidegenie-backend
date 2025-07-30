# Document Processing Security System

A comprehensive security framework for document processing that provides multi-layered protection against malware, viruses, and other security threats. This system integrates virus scanning, file validation, quarantine management, sanitization, threat detection, and audit logging to ensure complete security coverage.

## 🛡️ Features

### Core Security Components

1. **Virus Scanner** (`virus_scanner.py`)
   - ClamAV integration for local scanning
   - VirusTotal API integration for cloud-based detection
   - Multi-engine threat detection
   - Real-time threat intelligence
   - Caching for performance optimization

2. **File Validator** (`file_validator.py`)
   - Magic number verification
   - Content structure analysis
   - Metadata validation
   - Security policy enforcement
   - File integrity checks

3. **Quarantine Manager** (`quarantine_manager.py`)
   - Secure file isolation
   - Encrypted quarantine storage
   - Automated cleanup policies
   - Recovery and analysis capabilities
   - Audit trail maintenance

4. **File Sanitizer** (`sanitizer.py`)
   - Metadata removal and cleaning
   - Content scrubbing and filtering
   - Format conversion and normalization
   - Embedded content removal
   - Macro and script stripping

5. **Threat Detector** (`threat_detector.py`)
   - Advanced heuristic analysis
   - Behavioral pattern detection
   - Machine learning threat classification
   - Threat intelligence integration
   - Automated response workflows

6. **Security Audit Logger** (`audit_logger.py`)
   - Comprehensive security event tracking
   - Compliance logging (GDPR, SOC2, HIPAA)
   - Structured audit trails
   - Real-time monitoring integration
   - Query and reporting capabilities

## 🚀 Quick Start

### Basic Setup

```python
from app.services.document_processing.security import (
    SecurityPipeline, 
    SanitizationLevel
)

# Initialize security pipeline
pipeline = SecurityPipeline()

# Process a file upload
results = await pipeline.process_file_upload(
    file_path="/path/to/uploaded/file.pdf",
    user_id="user123",
    session_id="session456",
    sanitize=True,
    sanitization_level=SanitizationLevel.STANDARD
)

# Check results
if results['security_status'] == 'safe':
    print(f"File is safe: {results['final_file_path']}")
elif results['security_status'] == 'quarantined':
    print(f"File quarantined: {results['quarantine_id']}")
```

### Individual Component Usage

#### Virus Scanning

```python
from app.services.document_processing.security import VirusScanner

scanner = VirusScanner()

# Scan a file
scan_result = await scanner.scan_file("/path/to/file.pdf")

print(f"Status: {scan_result.status}")
print(f"Threats: {len(scan_result.threats)}")
print(f"Confidence: {scan_result.confidence_score}")
```

#### File Validation

```python
from app.services.document_processing.security import FileValidator

validator = FileValidator()

# Validate a file
validation_result = await validator.validate_file("/path/to/file.pdf")

print(f"Status: {validation_result.status}")
print(f"Security Score: {validation_result.security_score}")
print(f"Issues: {len(validation_result.issues)}")
```

#### File Sanitization

```python
from app.services.document_processing.security import (
    FileSanitizer, 
    SanitizationLevel
)

sanitizer = FileSanitizer()

# Sanitize a file
sanitization_result = await sanitizer.sanitize_file(
    file_path="/path/to/input.pdf",
    output_path="/path/to/sanitized.pdf",
    level=SanitizationLevel.STRICT
)

print(f"Success: {sanitization_result.success}")
print(f"Actions: {sanitization_result.actions_performed}")
```

## 🔧 Configuration

### Environment Variables

```bash
# Virus scanning
VIRUSTOTAL_API_KEY=your_virustotal_api_key_here
CLAMAV_SOCKET=/var/run/clamav/clamd.sock

# Security settings
QUARANTINE_DIR=/var/quarantine
SECURITY_LOG_PATH=/var/log/security/audit.log

# Redis (optional but recommended)
REDIS_URL=redis://localhost:6379/0
```

### Component Configuration

#### Virus Scanner Configuration

```python
from app.services.document_processing.security import ScannerConfig

config = ScannerConfig(
    clamav_enabled=True,
    virustotal_enabled=True,
    virustotal_api_key="your_api_key",
    max_file_size=100 * 1024 * 1024,  # 100MB
    cache_ttl=3600,  # 1 hour
    threat_threshold=0.3
)

scanner = VirusScanner(config=config)
```

#### File Validator Configuration

```python
from app.services.document_processing.security import (
    FileValidatorConfig,
    FileType
)

config = FileValidatorConfig(
    max_file_size=100 * 1024 * 1024,
    allowed_types={
        FileType.PDF, FileType.DOCX, FileType.TXT
    },
    require_magic_validation=True,
    deep_content_analysis=True,
    security_checks=True
)

validator = FileValidator(config=config)
```

#### Quarantine Configuration

```python
from app.services.document_processing.security import QuarantineConfig

config = QuarantineConfig(
    quarantine_dir="/var/quarantine",
    encryption_enabled=True,
    retention_days=30,
    auto_cleanup_enabled=True,
    max_quarantine_size=10 * 1024 * 1024 * 1024  # 10GB
)

quarantine_manager = QuarantineManager(config=config)
```

## 🔒 Security Features

### Multi-Layer Protection

1. **File Type Validation**
   - Magic number verification
   - Extension validation
   - MIME type checking
   - Content structure analysis

2. **Virus Detection**
   - Local ClamAV scanning
   - Cloud-based VirusTotal analysis
   - Heuristic threat detection
   - Real-time threat intelligence

3. **Content Analysis**
   - Suspicious pattern detection
   - Embedded content analysis
   - Macro and script detection
   - Metadata examination

4. **Behavioral Analysis**
   - User behavior profiling
   - Anomaly detection
   - Risk scoring
   - Pattern recognition

### Threat Response

- **Automatic Quarantine**: High-risk files are automatically isolated
- **Content Sanitization**: Safe files can be cleaned and normalized
- **User Notification**: Security events trigger appropriate alerts
- **Audit Logging**: All security events are comprehensively logged

## 📊 Monitoring and Compliance

### Security Dashboard

```python
# Get security statistics
dashboard = await pipeline.get_security_dashboard()

print(f"Quarantined files: {dashboard['quarantine']['total_files']}")
print(f"Recent threats: {dashboard['audit']['total_events']}")
print(f"Scanner status: {dashboard['scanner_engines']}")
```

### Compliance Reporting

```python
from datetime import datetime, timedelta
from app.services.document_processing.security import ComplianceFramework

# Export GDPR compliance data
start_date = datetime.utcnow() - timedelta(days=30)
end_date = datetime.utcnow()

export_path = await audit_logger.export_audit_log(
    start_time=start_date,
    end_time=end_date,
    format_type="json",
    compliance_framework=ComplianceFramework.GDPR
)

print(f"GDPR export saved to: {export_path}")
```

### Supported Compliance Frameworks

- **GDPR** (General Data Protection Regulation)
- **SOC 2** (Service Organization Control 2)
- **HIPAA** (Health Insurance Portability and Accountability Act)
- **PCI DSS** (Payment Card Industry Data Security Standard)
- **ISO 27001** (Information Security Management)
- **NIST** (National Institute of Standards and Technology)

## 🔧 Advanced Usage

### Custom Threat Detection Rules

```python
# Add custom heuristic rules
custom_rules = [
    {
        "name": "suspicious_filename",
        "description": "Detects suspicious filename patterns",
        "pattern": rb"invoice.*\.exe",
        "severity": "high"
    }
]

# Configure threat detector with custom rules
threat_detector = ThreatDetector()
# Custom rules would be loaded through configuration
```

### Machine Learning Integration

```python
# Update ML models for threat detection
await threat_detector.update_ml_models(
    model_path="/path/to/trained/model.pkl"
)

# Train on new data
training_data = load_training_data()
await threat_detector.train_models(training_data)
```

### Threat Intelligence Integration

```python
# Update threat intelligence feeds
intel_results = await threat_detector.update_threat_intelligence()

print(f"Updated indicators: {sum(intel_results.values())}")

# Query specific hash
threat_info = await threat_detector.query_threat_intel(
    file_hash="abc123..."
)
```

## 📈 Performance Optimization

### Caching Strategy

- **File Hash Caching**: Avoid re-scanning identical files
- **Validation Caching**: Cache validation results for known file types
- **Threat Intel Caching**: Cache threat intelligence data locally
- **User Profile Caching**: Cache behavioral analysis profiles

### Async Processing

```python
# Process multiple files concurrently
files = ["/path/to/file1.pdf", "/path/to/file2.docx"]

# Concurrent processing
tasks = [
    pipeline.process_file_upload(file, user_id, session_id)
    for file in files
]

results = await asyncio.gather(*tasks)
```

### Resource Management

```python
# Configure resource limits
config = ThreatDetectorConfig(
    max_concurrent_analyses=5,
    analysis_timeout=300,  # 5 minutes
    cache_ttl=3600  # 1 hour
)
```

## 🛠️ Installation and Dependencies

### Required Packages

```bash
pip install aiofiles aiohttp pyclamd python-magic
pip install cryptography pydantic redis
pip install scikit-learn numpy beautifulsoup4
pip install PyPDF2  # For PDF processing
```

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install clamav clamav-daemon
sudo apt-get install libmagic1

# CentOS/RHEL
sudo yum install clamav clamav-update
sudo yum install file-libs

# macOS
brew install clamav
brew install libmagic
```

### ClamAV Setup

```bash
# Update virus definitions
sudo freshclam

# Start ClamAV daemon
sudo systemctl start clamav-daemon
sudo systemctl enable clamav-daemon
```

## 🔍 Troubleshooting

### Common Issues

1. **ClamAV Connection Failed**
   ```python
   # Check ClamAV daemon status
   sudo systemctl status clamav-daemon
   
   # Verify socket path
   ls -la /var/run/clamav/clamd.sock
   ```

2. **VirusTotal API Errors**
   ```python
   # Verify API key
   scanner_status = await virus_scanner.get_engine_status()
   print(scanner_status['virustotal'])
   ```

3. **Permission Issues**
   ```bash
   # Set proper permissions for quarantine directory
   sudo mkdir -p /var/quarantine
   sudo chown app:app /var/quarantine
   sudo chmod 750 /var/quarantine
   ```

4. **Redis Connection Issues**
   ```python
   # Test Redis connection
   try:
       await redis_client.ping()
       print("Redis connected")
   except Exception as e:
       print(f"Redis error: {e}")
   ```

### Logging and Debugging

```python
import logging

# Enable debug logging
logging.getLogger('app.services.document_processing.security').setLevel(logging.DEBUG)

# Monitor security events
async def monitor_security_events():
    events = await audit_logger.query_events(
        event_types=[AuditEventType.THREAT_DETECTED],
        limit=10
    )
    
    for event in events:
        print(f"Threat: {event.details}")
```

## 📚 API Reference

### SecurityPipeline

Main integration class that orchestrates all security components.

#### Methods

- `process_file_upload(file_path, user_id, session_id, sanitize=True, sanitization_level=STANDARD)` - Process uploaded file through security pipeline
- `get_security_dashboard()` - Get security statistics and status
- `cleanup_expired_data()` - Clean up expired security data

### VirusScanner

Multi-engine virus scanning service.

#### Methods

- `scan_file(file_path, scan_id=None)` - Scan file for viruses
- `scan_buffer(data, filename="buffer", scan_id=None)` - Scan data buffer
- `get_engine_status()` - Get status of scanning engines

### FileValidator

Comprehensive file validation service.

#### Methods

- `validate_file(file_path)` - Validate file comprehensively
- `validate_buffer(data, filename="buffer")` - Validate data buffer
- `get_supported_types()` - Get list of supported file types

### QuarantineManager

Secure quarantine management service.

#### Methods

- `quarantine_file(file_path, reason, detection_details=None, user_id=None)` - Quarantine a file
- `release_file(quarantine_id, destination_path, user_id=None)` - Release file from quarantine
- `delete_quarantined_file(quarantine_id, user_id=None, permanent=False)` - Delete quarantined file
- `get_quarantine_stats()` - Get quarantine statistics

### FileSanitizer

File sanitization and content scrubbing service.

#### Methods

- `sanitize_file(file_path, output_path=None, level=STANDARD)` - Sanitize a file
- `sanitize_buffer(data, file_type, filename="buffer", level=STANDARD)` - Sanitize data buffer
- `get_sanitization_levels()` - Get available sanitization levels

### ThreatDetector

Advanced threat detection service.

#### Methods

- `analyze_file(file_path, file_hash, validation_result=None, user_id=None)` - Analyze file for threats
- `get_threat_profile(entity_type, entity_id)` - Get threat profile for entity
- `update_threat_intelligence(source="all")` - Update threat intelligence data

### SecurityAuditLogger

Comprehensive security audit logging service.

#### Methods

- `log_event(event_type, details=None, level=None, user_id=None, ...)` - Log security event
- `query_events(start_time=None, end_time=None, event_types=None, ...)` - Query audit events
- `export_audit_log(start_time, end_time, format_type="json", compliance_framework=None)` - Export audit log
- `get_event_statistics(start_time=None, end_time=None, group_by="event_type")` - Get event statistics

## 🤝 Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Ensure all security checks pass
5. Test with various file types and scenarios

## 📄 License

This security system is designed for enterprise document processing applications. Please ensure compliance with all relevant security regulations and best practices in your deployment environment.

## 🆘 Support

For security issues or questions:

1. Check the troubleshooting section above
2. Review the logs for detailed error information
3. Ensure all dependencies are properly installed
4. Verify configuration settings match your environment

Remember: Security is a continuous process. Regularly update threat intelligence, review audit logs, and adjust configurations based on emerging threats and organizational requirements.