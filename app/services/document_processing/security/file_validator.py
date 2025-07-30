"""
File validation service with magic number checking and content analysis.

Provides comprehensive file validation including:
- Magic number verification
- File type detection
- Content structure analysis
- Metadata validation
- Security policy enforcement
- File integrity checks
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
import struct
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import aiofiles
import magic
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Validation status enumeration."""
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    CORRUPTED = "corrupted"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class FileType(str, Enum):
    """Supported file types."""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    PPTX = "pptx"
    PPT = "ppt"
    XLSX = "xlsx"
    XLS = "xls"
    TXT = "txt"
    RTF = "rtf"
    LATEX = "latex"
    TEX = "tex"
    MARKDOWN = "markdown"
    HTML = "html"
    XML = "xml"
    JSON = "json"
    CSV = "csv"
    IMAGE = "image"
    ARCHIVE = "archive"
    EXECUTABLE = "executable"
    SCRIPT = "script"
    UNKNOWN = "unknown"


class SecurityRisk(str, Enum):
    """Security risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationIssue(BaseModel):
    """Validation issue model."""
    code: str = Field(..., description="Issue code")
    message: str = Field(..., description="Issue description")
    severity: SecurityRisk = Field(..., description="Issue severity")
    details: Dict = Field(default_factory=dict, description="Additional details")


class ValidationResult(BaseModel):
    """File validation result."""
    file_path: str = Field(..., description="Path to validated file")
    file_hash: str = Field(..., description="File SHA-256 hash")
    file_size: int = Field(..., description="File size in bytes")
    detected_type: FileType = Field(..., description="Detected file type")
    mime_type: str = Field(..., description="MIME type")
    magic_number: str = Field(..., description="File magic number")
    status: ValidationStatus = Field(..., description="Validation status")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Validation issues")
    metadata: Dict = Field(default_factory=dict, description="File metadata")
    structure_analysis: Dict = Field(default_factory=dict, description="Content structure analysis")
    security_score: float = Field(default=0.0, description="Security score (0-1)")
    validation_time: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")


class FileValidatorConfig(BaseModel):
    """File validator configuration."""
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_types: Set[FileType] = {
        FileType.PDF, FileType.DOCX, FileType.DOC, FileType.PPTX,
        FileType.PPT, FileType.TXT, FileType.RTF, FileType.LATEX,
        FileType.TEX, FileType.MARKDOWN
    }
    blocked_extensions: Set[str] = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs',
        '.js', '.jar', '.msi', '.deb', '.rpm', '.dmg'
    }
    require_magic_validation: bool = True
    deep_content_analysis: bool = True
    metadata_validation: bool = True
    structure_validation: bool = True
    security_checks: bool = True


class FileValidator:
    """
    Comprehensive file validation service.
    
    Validates files for security, integrity, and compliance with policies.
    """
    
    # Magic number signatures for common file types
    MAGIC_SIGNATURES = {
        b'\x25\x50\x44\x46': FileType.PDF,  # PDF
        b'\x50\x4B\x03\x04': FileType.DOCX,  # ZIP-based (DOCX, PPTX, etc.)
        b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1': FileType.DOC,  # OLE2 (DOC, XLS, PPT)
        b'\x7B\x5C\x72\x74\x66': FileType.RTF,  # RTF
        b'\xFF\xFE': FileType.TXT,  # UTF-16 LE BOM
        b'\xFE\xFF': FileType.TXT,  # UTF-16 BE BOM
        b'\xEF\xBB\xBF': FileType.TXT,  # UTF-8 BOM
        b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': FileType.IMAGE,  # PNG
        b'\xFF\xD8\xFF': FileType.IMAGE,  # JPEG
        b'\x47\x49\x46\x38': FileType.IMAGE,  # GIF
    }
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'data:',
        b'ActiveXObject',
        b'eval(',
        b'document.write',
        b'innerHTML',
        b'exec(',
        b'system(',
        b'shell_exec',
        b'base64_decode',
    ]
    
    def __init__(self, config: Optional[FileValidatorConfig] = None):
        """Initialize file validator."""
        self.config = config or FileValidatorConfig()
        self.settings = get_settings()
        
        # Initialize magic library
        try:
            self.magic = magic.Magic(mime=True)
            self.magic_description = magic.Magic()
        except Exception as e:
            logger.error(f"Failed to initialize magic library: {e}")
            self.magic = None
            self.magic_description = None
    
    async def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate a file comprehensively.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            ValidationResult: Comprehensive validation results
        """
        file_path = Path(file_path)
        
        logger.info(f"Starting file validation for {file_path}")
        
        # Initialize result
        result = ValidationResult(
            file_path=str(file_path),
            file_hash="",
            file_size=0,
            detected_type=FileType.UNKNOWN,
            mime_type="",
            magic_number="",
            status=ValidationStatus.UNKNOWN
        )
        
        try:
            # Basic file checks
            await self._basic_file_checks(file_path, result)
            
            # Magic number validation
            if self.config.require_magic_validation:
                await self._validate_magic_number(file_path, result)
            
            # Content analysis
            if self.config.deep_content_analysis:
                await self._analyze_content(file_path, result)
            
            # Metadata validation
            if self.config.metadata_validation:
                await self._validate_metadata(file_path, result)
            
            # Structure validation
            if self.config.structure_validation:
                await self._validate_structure(file_path, result)
            
            # Security checks
            if self.config.security_checks:
                await self._security_checks(file_path, result)
            
            # Calculate overall security score
            result.security_score = self._calculate_security_score(result)
            
            # Determine final status
            result.status = self._determine_final_status(result)
            
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            result.status = ValidationStatus.INVALID
            result.issues.append(ValidationIssue(
                code="VALIDATION_ERROR",
                message=f"Validation failed: {str(e)}",
                severity=SecurityRisk.HIGH
            ))
        
        logger.info(f"File validation completed: {result.status} (score: {result.security_score:.2f})")
        
        return result
    
    async def validate_buffer(self, data: bytes, filename: str = "buffer") -> ValidationResult:
        """
        Validate data buffer.
        
        Args:
            data: Data to validate
            filename: Filename for identification
            
        Returns:
            ValidationResult: Validation results
        """
        import tempfile
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(data)
            temp_path = temp_file.name
        
        try:
            result = await self.validate_file(temp_path)
            result.file_path = filename
            result.metadata["original_filename"] = filename
            return result
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    async def _basic_file_checks(self, file_path: Path, result: ValidationResult):
        """Perform basic file checks."""
        # Check file exists
        if not file_path.exists():
            result.issues.append(ValidationIssue(
                code="FILE_NOT_FOUND",
                message="File does not exist",
                severity=SecurityRisk.HIGH
            ))
            return
        
        # Check file size
        file_size = file_path.stat().st_size
        result.file_size = file_size
        
        if file_size == 0:
            result.issues.append(ValidationIssue(
                code="EMPTY_FILE",
                message="File is empty",
                severity=SecurityRisk.MEDIUM
            ))
        
        if file_size > self.config.max_file_size:
            result.issues.append(ValidationIssue(
                code="FILE_TOO_LARGE",
                message=f"File size ({file_size} bytes) exceeds limit ({self.config.max_file_size} bytes)",
                severity=SecurityRisk.HIGH
            ))
        
        # Calculate file hash
        result.file_hash = await self._calculate_file_hash(file_path)
        
        # Check file extension
        extension = file_path.suffix.lower()
        if extension in self.config.blocked_extensions:
            result.issues.append(ValidationIssue(
                code="BLOCKED_EXTENSION",
                message=f"File extension '{extension}' is blocked",
                severity=SecurityRisk.CRITICAL
            ))
        
        # Get MIME type
        if self.magic:
            try:
                result.mime_type = self.magic.from_file(str(file_path))
            except Exception as e:
                logger.warning(f"Failed to get MIME type: {e}")
                result.mime_type = mimetypes.guess_type(str(file_path))[0] or "unknown"
        else:
            result.mime_type = mimetypes.guess_type(str(file_path))[0] or "unknown"
    
    async def _validate_magic_number(self, file_path: Path, result: ValidationResult):
        """Validate file magic number."""
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                header = await f.read(16)  # Read first 16 bytes
            
            result.magic_number = header.hex()
            
            # Check against known signatures
            detected_type = None
            for signature, file_type in self.MAGIC_SIGNATURES.items():
                if header.startswith(signature):
                    detected_type = file_type
                    break
            
            if detected_type:
                result.detected_type = detected_type
                
                # Special handling for ZIP-based files
                if detected_type == FileType.DOCX:
                    actual_type = await self._detect_office_type(file_path)
                    if actual_type:
                        result.detected_type = actual_type
            else:
                # Try to detect based on extension and content
                result.detected_type = self._detect_type_by_extension(file_path)
            
            # Validate type is allowed
            if result.detected_type not in self.config.allowed_types:
                result.issues.append(ValidationIssue(
                    code="UNSUPPORTED_TYPE",
                    message=f"File type '{result.detected_type}' is not allowed",
                    severity=SecurityRisk.HIGH
                ))
            
            # Check for magic number mismatch
            extension_type = self._detect_type_by_extension(file_path)
            if extension_type != FileType.UNKNOWN and extension_type != result.detected_type:
                result.issues.append(ValidationIssue(
                    code="MAGIC_EXTENSION_MISMATCH",
                    message=f"Magic number indicates '{result.detected_type}' but extension suggests '{extension_type}'",
                    severity=SecurityRisk.MEDIUM
                ))
        
        except Exception as e:
            logger.error(f"Magic number validation failed: {e}")
            result.issues.append(ValidationIssue(
                code="MAGIC_VALIDATION_ERROR",
                message=f"Failed to validate magic number: {str(e)}",
                severity=SecurityRisk.MEDIUM
            ))
    
    async def _analyze_content(self, file_path: Path, result: ValidationResult):
        """Analyze file content for suspicious patterns."""
        try:
            # Read file content (limited to avoid memory issues)
            max_read_size = min(1024 * 1024, result.file_size)  # Max 1MB
            
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read(max_read_size)
            
            # Check for suspicious patterns
            suspicious_patterns_found = []
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern in content:
                    suspicious_patterns_found.append(pattern.decode('utf-8', errors='ignore'))
            
            if suspicious_patterns_found:
                result.issues.append(ValidationIssue(
                    code="SUSPICIOUS_CONTENT",
                    message="Suspicious patterns detected in file content",
                    severity=SecurityRisk.HIGH,
                    details={"patterns": suspicious_patterns_found}
                ))
            
            # Entropy analysis for encrypted/compressed content
            entropy = self._calculate_entropy(content)
            result.metadata["entropy"] = entropy
            
            if entropy > 7.5:  # High entropy might indicate encryption or compression
                result.issues.append(ValidationIssue(
                    code="HIGH_ENTROPY",
                    message=f"High entropy ({entropy:.2f}) detected - possible encryption or compression",
                    severity=SecurityRisk.MEDIUM
                ))
            
            # Text/binary ratio analysis
            text_ratio = self._calculate_text_ratio(content)
            result.metadata["text_ratio"] = text_ratio
            
            # Check for embedded files or unusual structures
            if result.detected_type in [FileType.PDF, FileType.DOCX]:
                await self._check_embedded_content(file_path, result)
        
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            result.issues.append(ValidationIssue(
                code="CONTENT_ANALYSIS_ERROR",
                message=f"Content analysis failed: {str(e)}",
                severity=SecurityRisk.MEDIUM
            ))
    
    async def _validate_metadata(self, file_path: Path, result: ValidationResult):
        """Validate file metadata."""
        try:
            stat = file_path.stat()
            
            result.metadata.update({
                "creation_time": datetime.fromtimestamp(stat.st_ctime),
                "modification_time": datetime.fromtimestamp(stat.st_mtime),
                "access_time": datetime.fromtimestamp(stat.st_atime),
                "permissions": oct(stat.st_mode)[-3:],
                "inode": stat.st_ino,
                "device": stat.st_dev
            })
            
            # Check for suspicious timestamps
            now = datetime.now()
            creation_time = datetime.fromtimestamp(stat.st_ctime)
            
            if creation_time > now:
                result.issues.append(ValidationIssue(
                    code="FUTURE_TIMESTAMP",
                    message="File has future creation timestamp",
                    severity=SecurityRisk.MEDIUM
                ))
            
            # Check file permissions
            if stat.st_mode & 0o111:  # Executable bit set
                result.issues.append(ValidationIssue(
                    code="EXECUTABLE_PERMISSIONS",
                    message="File has executable permissions",
                    severity=SecurityRisk.HIGH
                ))
        
        except Exception as e:
            logger.error(f"Metadata validation failed: {e}")
            result.issues.append(ValidationIssue(
                code="METADATA_VALIDATION_ERROR",
                message=f"Metadata validation failed: {str(e)}",
                severity=SecurityRisk.LOW
            ))
    
    async def _validate_structure(self, file_path: Path, result: ValidationResult):
        """Validate file structure based on type."""
        try:
            if result.detected_type == FileType.PDF:
                await self._validate_pdf_structure(file_path, result)
            elif result.detected_type in [FileType.DOCX, FileType.PPTX, FileType.XLSX]:
                await self._validate_office_structure(file_path, result)
            elif result.detected_type == FileType.TXT:
                await self._validate_text_structure(file_path, result)
        
        except Exception as e:
            logger.error(f"Structure validation failed: {e}")
            result.issues.append(ValidationIssue(
                code="STRUCTURE_VALIDATION_ERROR",
                message=f"Structure validation failed: {str(e)}",
                severity=SecurityRisk.MEDIUM
            ))
    
    async def _security_checks(self, file_path: Path, result: ValidationResult):
        """Perform additional security checks."""
        try:
            # Check for polyglot files (files that are valid in multiple formats)
            await self._check_polyglot(file_path, result)
            
            # Check for steganography indicators
            await self._check_steganography_indicators(file_path, result)
            
            # Check for unusual file size patterns
            self._check_size_anomalies(result)
            
        except Exception as e:
            logger.error(f"Security checks failed: {e}")
            result.issues.append(ValidationIssue(
                code="SECURITY_CHECK_ERROR",
                message=f"Security checks failed: {str(e)}",
                severity=SecurityRisk.MEDIUM
            ))
    
    async def _detect_office_type(self, file_path: Path) -> Optional[FileType]:
        """Detect specific Office document type from ZIP structure."""
        try:
            import zipfile
            
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                filenames = zip_file.namelist()
                
                if 'word/' in str(filenames):
                    return FileType.DOCX
                elif 'ppt/' in str(filenames):
                    return FileType.PPTX
                elif 'xl/' in str(filenames):
                    return FileType.XLSX
                elif '[Content_Types].xml' in filenames:
                    # Check content types
                    content_types = zip_file.read('[Content_Types].xml').decode('utf-8')
                    if 'wordprocessingml' in content_types:
                        return FileType.DOCX
                    elif 'presentationml' in content_types:
                        return FileType.PPTX
                    elif 'spreadsheetml' in content_types:
                        return FileType.XLSX
        
        except Exception as e:
            logger.debug(f"Failed to detect Office type: {e}")
        
        return None
    
    def _detect_type_by_extension(self, file_path: Path) -> FileType:
        """Detect file type by extension."""
        extension = file_path.suffix.lower()
        
        extension_map = {
            '.pdf': FileType.PDF,
            '.docx': FileType.DOCX,
            '.doc': FileType.DOC,
            '.pptx': FileType.PPTX,
            '.ppt': FileType.PPT,
            '.xlsx': FileType.XLSX,
            '.xls': FileType.XLS,
            '.txt': FileType.TXT,
            '.rtf': FileType.RTF,
            '.tex': FileType.LATEX,
            '.latex': FileType.LATEX,
            '.md': FileType.MARKDOWN,
            '.markdown': FileType.MARKDOWN,
            '.html': FileType.HTML,
            '.htm': FileType.HTML,
            '.xml': FileType.XML,
            '.json': FileType.JSON,
            '.csv': FileType.CSV,
        }
        
        return extension_map.get(extension, FileType.UNKNOWN)
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of data."""
        if not data:
            return 0.0
        
        # Count byte frequencies
        counts = [0] * 256
        for byte in data:
            counts[byte] += 1
        
        # Calculate entropy
        entropy = 0.0
        length = len(data)
        
        for count in counts:
            if count > 0:
                p = count / length
                entropy -= p * (p.bit_length() - 1)
        
        return entropy
    
    def _calculate_text_ratio(self, data: bytes) -> float:
        """Calculate ratio of printable text characters."""
        if not data:
            return 0.0
        
        printable_count = sum(1 for byte in data if 32 <= byte <= 126 or byte in [9, 10, 13])
        return printable_count / len(data)
    
    async def _check_embedded_content(self, file_path: Path, result: ValidationResult):
        """Check for embedded content in complex file formats."""
        # This would need specific implementations for each format
        # For example, checking PDF for embedded JavaScript, Flash, etc.
        # For now, just a placeholder
        pass
    
    async def _validate_pdf_structure(self, file_path: Path, result: ValidationResult):
        """Validate PDF file structure."""
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read(1024)  # Read first 1KB
            
            # Check PDF version
            if content.startswith(b'%PDF-'):
                version_line = content.split(b'\n')[0]
                result.structure_analysis["pdf_version"] = version_line.decode('ascii', errors='ignore')
            
            # Check for suspicious PDF features
            if b'/JavaScript' in content or b'/JS' in content:
                result.issues.append(ValidationIssue(
                    code="PDF_JAVASCRIPT",
                    message="PDF contains JavaScript",
                    severity=SecurityRisk.HIGH
                ))
            
            if b'/EmbeddedFile' in content:
                result.issues.append(ValidationIssue(
                    code="PDF_EMBEDDED_FILE",
                    message="PDF contains embedded files",
                    severity=SecurityRisk.MEDIUM
                ))
        
        except Exception as e:
            logger.debug(f"PDF structure validation failed: {e}")
    
    async def _validate_office_structure(self, file_path: Path, result: ValidationResult):
        """Validate Office document structure."""
        try:
            import zipfile
            
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                filenames = zip_file.namelist()
                result.structure_analysis["zip_files"] = len(filenames)
                
                # Check for suspicious files
                suspicious_files = [f for f in filenames if f.endswith(('.exe', '.dll', '.com', '.bat'))]
                if suspicious_files:
                    result.issues.append(ValidationIssue(
                        code="OFFICE_SUSPICIOUS_FILES",
                        message="Office document contains suspicious files",
                        severity=SecurityRisk.CRITICAL,
                        details={"files": suspicious_files}
                    ))
                
                # Check for macros
                macro_files = [f for f in filenames if 'vbaProject' in f or f.endswith('.bin')]
                if macro_files:
                    result.issues.append(ValidationIssue(
                        code="OFFICE_MACROS",
                        message="Office document contains macros",
                        severity=SecurityRisk.HIGH,
                        details={"files": macro_files}
                    ))
        
        except Exception as e:
            logger.debug(f"Office structure validation failed: {e}")
    
    async def _validate_text_structure(self, file_path: Path, result: ValidationResult):
        """Validate text file structure."""
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read(8192)  # Read first 8KB
            
            # Check encoding
            try:
                text_content = content.decode('utf-8')
                result.structure_analysis["encoding"] = "utf-8"
            except UnicodeDecodeError:
                try:
                    text_content = content.decode('latin-1')
                    result.structure_analysis["encoding"] = "latin-1"
                except UnicodeDecodeError:
                    result.issues.append(ValidationIssue(
                        code="TEXT_ENCODING_ERROR",
                        message="Unable to decode text file",
                        severity=SecurityRisk.MEDIUM
                    ))
                    return
            
            # Check for null bytes (might indicate binary content)
            if b'\x00' in content:
                result.issues.append(ValidationIssue(
                    code="TEXT_NULL_BYTES",
                    message="Text file contains null bytes",
                    severity=SecurityRisk.MEDIUM
                ))
            
            # Basic statistics
            lines = text_content.count('\n')
            result.structure_analysis["line_count"] = lines
        
        except Exception as e:
            logger.debug(f"Text structure validation failed: {e}")
    
    async def _check_polyglot(self, file_path: Path, result: ValidationResult):
        """Check for polyglot files."""
        # Read first few KB and check for multiple format signatures
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                header = await f.read(4096)
            
            # Count how many format signatures are present
            signature_matches = 0
            for signature in self.MAGIC_SIGNATURES.keys():
                if signature in header:
                    signature_matches += 1
            
            if signature_matches > 1:
                result.issues.append(ValidationIssue(
                    code="POLYGLOT_FILE",
                    message="File appears to be valid in multiple formats (polyglot)",
                    severity=SecurityRisk.HIGH,
                    details={"signature_matches": signature_matches}
                ))
        
        except Exception as e:
            logger.debug(f"Polyglot check failed: {e}")
    
    async def _check_steganography_indicators(self, file_path: Path, result: ValidationResult):
        """Check for steganography indicators."""
        try:
            # This is a basic check - real steganography detection is complex
            if result.detected_type == FileType.IMAGE:
                # Check for unusual entropy patterns in images
                async with aiofiles.open(file_path, 'rb') as f:
                    content = await f.read()
                
                entropy = self._calculate_entropy(content)
                if entropy > 7.0:  # High entropy in images might indicate hidden data
                    result.issues.append(ValidationIssue(
                        code="POSSIBLE_STEGANOGRAPHY",
                        message="Image has high entropy, possible steganography",
                        severity=SecurityRisk.MEDIUM,
                        details={"entropy": entropy}
                    ))
        
        except Exception as e:
            logger.debug(f"Steganography check failed: {e}")
    
    def _check_size_anomalies(self, result: ValidationResult):
        """Check for unusual file size patterns."""
        # Check if file size is suspicious for its type
        size_limits = {
            FileType.TXT: 50 * 1024 * 1024,  # 50MB for text seems excessive
            FileType.DOCX: 200 * 1024 * 1024,  # 200MB for DOCX
            FileType.PDF: 500 * 1024 * 1024,  # 500MB for PDF
        }
        
        limit = size_limits.get(result.detected_type)
        if limit and result.file_size > limit:
            result.issues.append(ValidationIssue(
                code="UNUSUAL_SIZE",
                message=f"File size ({result.file_size} bytes) is unusually large for type {result.detected_type}",
                severity=SecurityRisk.MEDIUM
            ))
    
    def _calculate_security_score(self, result: ValidationResult) -> float:
        """Calculate overall security score."""
        base_score = 1.0
        
        for issue in result.issues:
            penalty = {
                SecurityRisk.LOW: 0.1,
                SecurityRisk.MEDIUM: 0.2,
                SecurityRisk.HIGH: 0.4,
                SecurityRisk.CRITICAL: 0.8
            }.get(issue.severity, 0.1)
            
            base_score -= penalty
        
        return max(0.0, min(1.0, base_score))
    
    def _determine_final_status(self, result: ValidationResult) -> ValidationStatus:
        """Determine final validation status."""
        if not result.issues:
            return ValidationStatus.VALID
        
        # Check for critical issues
        critical_issues = [i for i in result.issues if i.severity == SecurityRisk.CRITICAL]
        if critical_issues:
            return ValidationStatus.INVALID
        
        # Check for high severity issues
        high_issues = [i for i in result.issues if i.severity == SecurityRisk.HIGH]
        if high_issues:
            return ValidationStatus.SUSPICIOUS
        
        # Check security score
        if result.security_score < 0.3:
            return ValidationStatus.INVALID
        elif result.security_score < 0.7:
            return ValidationStatus.SUSPICIOUS
        
        return ValidationStatus.VALID
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def get_supported_types(self) -> List[FileType]:
        """Get list of supported file types."""
        return list(self.config.allowed_types)
    
    def is_type_allowed(self, file_type: FileType) -> bool:
        """Check if file type is allowed."""
        return file_type in self.config.allowed_types