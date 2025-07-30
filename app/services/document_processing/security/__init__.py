"""
Security module for document processing.

This module provides comprehensive security features including:
- Virus scanning and malware detection
- File validation and content analysis
- Security quarantine system
- File sanitization and content scrubbing
- Threat detection and response
- Security audit logging
- Compliance reporting
"""

from .virus_scanner import VirusScanner, ScanResult
from .file_validator import FileValidator, ValidationResult
from .quarantine_manager import QuarantineManager
from .sanitizer import FileSanitizer
from .audit_logger import SecurityAuditLogger
from .threat_detector import ThreatDetector

__all__ = [
    'VirusScanner',
    'ScanResult',
    'FileValidator',
    'ValidationResult',
    'QuarantineManager',
    'FileSanitizer',
    'SecurityAuditLogger',
    'ThreatDetector',
]