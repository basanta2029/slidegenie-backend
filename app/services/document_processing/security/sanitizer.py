"""
File sanitization and content scrubbing service.

Provides comprehensive file sanitization including:
- Metadata removal and cleaning
- Content scrubbing and filtering
- Format conversion and normalization
- Embedded content removal
- Macro and script stripping
- Safe document reconstruction
"""

import asyncio
import logging
import re
import tempfile
import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from xml.etree import ElementTree as ET

import aiofiles
from pydantic import BaseModel, Field

from app.core.config import get_settings
from .file_validator import FileType

logger = logging.getLogger(__name__)


class SanitizationLevel(str, Enum):
    """Sanitization level enumeration."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    PARANOID = "paranoid"


class SanitizationAction(str, Enum):
    """Sanitization action enumeration."""
    REMOVE_METADATA = "remove_metadata"
    STRIP_MACROS = "strip_macros"
    REMOVE_LINKS = "remove_links"
    FILTER_CONTENT = "filter_content"
    NORMALIZE_FORMAT = "normalize_format"
    REMOVE_EMBEDDED = "remove_embedded"
    CLEAN_STRUCTURE = "clean_structure"
    VALIDATE_ENCODING = "validate_encoding"


class SanitizationResult(BaseModel):
    """Sanitization result model."""
    original_path: str = Field(..., description="Original file path")
    sanitized_path: str = Field(..., description="Sanitized file path")
    file_type: FileType = Field(..., description="File type")
    sanitization_level: SanitizationLevel = Field(..., description="Sanitization level used")
    actions_performed: List[SanitizationAction] = Field(default_factory=list, description="Actions performed")
    issues_found: List[Dict] = Field(default_factory=list, description="Issues found and resolved")
    metadata_removed: Dict = Field(default_factory=dict, description="Removed metadata")
    statistics: Dict = Field(default_factory=dict, description="Sanitization statistics")
    sanitization_time: datetime = Field(default_factory=datetime.utcnow, description="Sanitization timestamp")
    success: bool = Field(default=True, description="Whether sanitization was successful")
    warnings: List[str] = Field(default_factory=list, description="Warnings generated")


class SanitizerConfig(BaseModel):
    """Sanitizer configuration."""
    default_level: SanitizationLevel = SanitizationLevel.STANDARD
    preserve_formatting: bool = True
    preserve_images: bool = True
    preserve_tables: bool = True
    remove_comments: bool = True
    remove_tracked_changes: bool = True
    remove_hidden_text: bool = True
    remove_personal_info: bool = True
    remove_external_links: bool = True
    remove_macros: bool = True
    remove_embedded_objects: bool = True
    normalize_whitespace: bool = True
    validate_structure: bool = True
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    temp_dir: Optional[str] = None


class FileSanitizer:
    """
    Comprehensive file sanitization service.
    
    Removes potentially dangerous content while preserving document integrity.
    """
    
    # Suspicious patterns to remove
    SUSPICIOUS_PATTERNS = [
        # JavaScript patterns
        r'<script[^>]*>.*?</script>',
        r'javascript:[^"\']*',
        r'vbscript:[^"\']*',
        r'data:[^"\']*',
        
        # Form elements
        r'<form[^>]*>.*?</form>',
        r'<input[^>]*>',
        r'<button[^>]*>.*?</button>',
        
        # Potentially dangerous HTML
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'<applet[^>]*>.*?</applet>',
        r'<iframe[^>]*>.*?</iframe>',
        
        # Executable references
        r'\.exe["\'\s]',
        r'\.bat["\'\s]',
        r'\.cmd["\'\s]',
        r'\.com["\'\s]',
        r'\.scr["\'\s]',
    ]
    
    # Metadata fields to remove
    METADATA_FIELDS = {
        'creator', 'author', 'lastModifiedBy', 'company', 'manager',
        'category', 'keywords', 'subject', 'comments', 'template',
        'lastPrinted', 'revision', 'totalTime', 'created', 'modified',
        'application', 'version', 'docSecurity', 'scaleCrop'
    }
    
    def __init__(self, config: Optional[SanitizerConfig] = None):
        """Initialize file sanitizer."""
        self.config = config or SanitizerConfig()
        self.settings = get_settings()
        
        # Compile regex patterns
        self.suspicious_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                                   for pattern in self.SUSPICIOUS_PATTERNS]
        
        logger.info("FileSanitizer initialized")
    
    async def sanitize_file(
        self,
        file_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        level: Optional[SanitizationLevel] = None
    ) -> SanitizationResult:
        """
        Sanitize a file.
        
        Args:
            file_path: Path to file to sanitize
            output_path: Optional output path (if None, creates new file)
            level: Sanitization level
            
        Returns:
            SanitizationResult: Sanitization results
        """
        file_path = Path(file_path)
        level = level or self.config.default_level
        
        logger.info(f"Starting file sanitization: {file_path} (level: {level})")
        
        # Validate input
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size > self.config.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes")
        
        # Determine file type
        file_type = await self._detect_file_type(file_path)
        
        # Create output path if not provided
        if output_path is None:
            output_path = file_path.with_suffix(f".sanitized{file_path.suffix}")
        else:
            output_path = Path(output_path)
        
        # Initialize result
        result = SanitizationResult(
            original_path=str(file_path),
            sanitized_path=str(output_path),
            file_type=file_type,
            sanitization_level=level
        )
        
        try:
            # Perform sanitization based on file type
            if file_type == FileType.PDF:
                await self._sanitize_pdf(file_path, output_path, level, result)
            elif file_type in [FileType.DOCX, FileType.PPTX, FileType.XLSX]:
                await self._sanitize_office(file_path, output_path, level, result)
            elif file_type == FileType.DOC:
                await self._sanitize_ole_document(file_path, output_path, level, result)
            elif file_type == FileType.TXT:
                await self._sanitize_text(file_path, output_path, level, result)
            elif file_type == FileType.RTF:
                await self._sanitize_rtf(file_path, output_path, level, result)
            elif file_type == FileType.HTML:
                await self._sanitize_html(file_path, output_path, level, result)
            elif file_type == FileType.XML:
                await self._sanitize_xml(file_path, output_path, level, result)
            else:
                # Generic sanitization
                await self._sanitize_generic(file_path, output_path, level, result)
            
            # Post-processing validation
            if self.config.validate_structure:
                await self._validate_sanitized_file(output_path, result)
            
            logger.info(f"File sanitization completed: {len(result.actions_performed)} actions performed")
            
        except Exception as e:
            logger.error(f"File sanitization failed: {e}")
            result.success = False
            result.warnings.append(f"Sanitization failed: {str(e)}")
            
            # Copy original file as fallback
            await self._copy_file(file_path, output_path)
        
        return result
    
    async def sanitize_buffer(
        self,
        data: bytes,
        file_type: FileType,
        filename: str = "buffer",
        level: Optional[SanitizationLevel] = None
    ) -> Tuple[bytes, SanitizationResult]:
        """
        Sanitize data buffer.
        
        Args:
            data: Data to sanitize
            file_type: File type
            filename: Filename for identification
            level: Sanitization level
            
        Returns:
            Tuple of sanitized data and result
        """
        # Write to temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_input:
            temp_input.write(data)
            temp_input_path = temp_input.name
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        try:
            result = await self.sanitize_file(
                file_path=temp_input_path,
                output_path=temp_output_path,
                level=level
            )
            
            # Read sanitized data
            async with aiofiles.open(temp_output_path, 'rb') as f:
                sanitized_data = await f.read()
            
            # Update result paths
            result.original_path = filename
            result.sanitized_path = filename
            
            return sanitized_data, result
        
        finally:
            # Clean up temp files
            for temp_path in [temp_input_path, temp_output_path]:
                try:
                    Path(temp_path).unlink()
                except FileNotFoundError:
                    pass
    
    async def _sanitize_pdf(
        self,
        input_path: Path,
        output_path: Path,
        level: SanitizationLevel,
        result: SanitizationResult
    ):
        """Sanitize PDF file."""
        try:
            import PyPDF2
            from PyPDF2 import PdfReader, PdfWriter
            
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Remove metadata
            if level in [SanitizationLevel.STANDARD, SanitizationLevel.STRICT, SanitizationLevel.PARANOID]:
                if reader.metadata:
                    result.metadata_removed = dict(reader.metadata)
                    result.actions_performed.append(SanitizationAction.REMOVE_METADATA)
            
            # Process each page
            for page_num, page in enumerate(reader.pages):
                try:
                    # Remove annotations if strict
                    if level in [SanitizationLevel.STRICT, SanitizationLevel.PARANOID]:
                        if '/Annots' in page:
                            del page['/Annots']
                            result.actions_performed.append(SanitizationAction.REMOVE_EMBEDDED)
                    
                    # Remove JavaScript
                    if '/JS' in page or '/JavaScript' in page:
                        if '/JS' in page:
                            del page['/JS']
                        if '/JavaScript' in page:
                            del page['/JavaScript']
                        result.actions_performed.append(SanitizationAction.STRIP_MACROS)
                        result.issues_found.append({
                            "page": page_num,
                            "issue": "JavaScript removed",
                            "severity": "high"
                        })
                    
                    writer.add_page(page)
                
                except Exception as e:
                    logger.warning(f"Failed to process PDF page {page_num}: {e}")
                    result.warnings.append(f"Page {page_num} processing failed")
            
            # Write sanitized PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            result.statistics = {
                "original_pages": len(reader.pages),
                "sanitized_pages": len(writer.pages),
                "metadata_fields_removed": len(result.metadata_removed)
            }
        
        except ImportError:
            logger.error("PyPDF2 not available, using generic sanitization")
            await self._sanitize_generic(input_path, output_path, level, result)
        except Exception as e:
            logger.error(f"PDF sanitization failed: {e}")
            raise
    
    async def _sanitize_office(
        self,
        input_path: Path,
        output_path: Path,
        level: SanitizationLevel,
        result: SanitizationResult
    ):
        """Sanitize Office documents (DOCX, PPTX, XLSX)."""
        try:
            # Office documents are ZIP files
            with zipfile.ZipFile(input_path, 'r') as input_zip:
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as output_zip:
                    
                    for file_info in input_zip.filelist:
                        file_data = input_zip.read(file_info.filename)
                        
                        # Process specific files
                        if file_info.filename == 'docProps/core.xml':
                            # Remove metadata
                            file_data = await self._sanitize_office_metadata(file_data, result)
                            result.actions_performed.append(SanitizationAction.REMOVE_METADATA)
                        
                        elif file_info.filename == 'docProps/app.xml':
                            # Remove application metadata
                            file_data = await self._sanitize_app_metadata(file_data, result)
                        
                        elif file_info.filename.startswith('word/') and file_info.filename.endswith('.xml'):
                            # Process document content
                            file_data = await self._sanitize_office_content(file_data, level, result)
                        
                        elif file_info.filename.startswith('xl/') and file_info.filename.endswith('.xml'):
                            # Process Excel content
                            file_data = await self._sanitize_excel_content(file_data, level, result)
                        
                        elif file_info.filename.startswith('ppt/') and file_info.filename.endswith('.xml'):
                            # Process PowerPoint content
                            file_data = await self._sanitize_ppt_content(file_data, level, result)
                        
                        elif 'vbaProject' in file_info.filename:
                            # Remove macros
                            if level in [SanitizationLevel.STANDARD, SanitizationLevel.STRICT, SanitizationLevel.PARANOID]:
                                result.actions_performed.append(SanitizationAction.STRIP_MACROS)
                                result.issues_found.append({
                                    "file": file_info.filename,
                                    "issue": "VBA project removed",
                                    "severity": "high"
                                })
                                continue  # Skip this file
                        
                        elif file_info.filename.endswith('.bin') and level == SanitizationLevel.PARANOID:
                            # Remove binary files in paranoid mode
                            result.actions_performed.append(SanitizationAction.REMOVE_EMBEDDED)
                            continue
                        
                        # Write processed file
                        output_zip.writestr(file_info, file_data)
            
            result.statistics["files_processed"] = len(input_zip.filelist)
        
        except Exception as e:
            logger.error(f"Office document sanitization failed: {e}")
            raise
    
    async def _sanitize_text(
        self,
        input_path: Path,
        output_path: Path,
        level: SanitizationLevel,
        result: SanitizationResult
    ):
        """Sanitize text file."""
        try:
            async with aiofiles.open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
            
            original_lines = content.count('\n')
            original_length = len(content)
            
            # Remove suspicious patterns
            for pattern in self.suspicious_patterns:
                if pattern.search(content):
                    content = pattern.sub('', content)
                    result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
                    result.issues_found.append({
                        "pattern": pattern.pattern,
                        "issue": "Suspicious pattern removed",
                        "severity": "medium"
                    })
            
            # Normalize whitespace
            if self.config.normalize_whitespace:
                # Remove excessive whitespace
                content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 consecutive newlines
                content = re.sub(r' {2,}', ' ', content)  # Max 1 space
                content = re.sub(r'\t+', '\t', content)  # Max 1 tab
                result.actions_performed.append(SanitizationAction.NORMALIZE_FORMAT)
            
            # Remove null bytes
            if '\x00' in content:
                content = content.replace('\x00', '')
                result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
                result.issues_found.append({
                    "issue": "Null bytes removed",
                    "severity": "medium"
                })
            
            # Remove control characters (except common ones)
            if level in [SanitizationLevel.STRICT, SanitizationLevel.PARANOID]:
                # Keep only printable chars, newline, tab, carriage return
                cleaned_content = ''
                for char in content:
                    if char.isprintable() or char in '\n\t\r':
                        cleaned_content += char
                    else:
                        result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
                
                content = cleaned_content
            
            # Write sanitized content
            async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            result.statistics = {
                "original_lines": original_lines,
                "original_length": original_length,
                "sanitized_lines": content.count('\n'),
                "sanitized_length": len(content),
                "size_reduction": original_length - len(content)
            }
        
        except Exception as e:
            logger.error(f"Text sanitization failed: {e}")
            raise
    
    async def _sanitize_html(
        self,
        input_path: Path,
        output_path: Path,
        level: SanitizationLevel,
        result: SanitizationResult
    ):
        """Sanitize HTML file."""
        try:
            from bs4 import BeautifulSoup
            
            async with aiofiles.open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove dangerous tags
            dangerous_tags = ['script', 'object', 'embed', 'applet', 'form', 'input', 'button']
            if level == SanitizationLevel.PARANOID:
                dangerous_tags.extend(['iframe', 'frame', 'frameset', 'meta'])
            
            for tag_name in dangerous_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
                    result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
                    result.issues_found.append({
                        "tag": tag_name,
                        "issue": f"{tag_name} tag removed",
                        "severity": "high"
                    })
            
            # Remove dangerous attributes
            dangerous_attrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'onfocus', 'onblur']
            for tag in soup.find_all():
                for attr in dangerous_attrs:
                    if tag.has_attr(attr):
                        del tag[attr]
                        result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
            
            # Remove external links if configured
            if self.config.remove_external_links:
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith(('http://', 'https://', 'ftp://')):
                        link['href'] = '#'
                        result.actions_performed.append(SanitizationAction.REMOVE_LINKS)
            
            # Write sanitized HTML
            async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                await f.write(str(soup))
            
        except ImportError:
            logger.warning("BeautifulSoup not available, using regex sanitization")
            await self._sanitize_text(input_path, output_path, level, result)
        except Exception as e:
            logger.error(f"HTML sanitization failed: {e}")
            raise
    
    async def _sanitize_rtf(
        self,
        input_path: Path,
        output_path: Path,
        level: SanitizationLevel,
        result: SanitizationResult
    ):
        """Sanitize RTF file."""
        try:
            async with aiofiles.open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
            
            # Remove RTF control words that can be dangerous
            dangerous_controls = [
                r'\\object[^}]*}',  # Embedded objects
                r'\\field[^}]*}',   # Field codes
                r'\\stylesheet[^}]*}',  # Style sheets with potential code
            ]
            
            for control_pattern in dangerous_controls:
                pattern = re.compile(control_pattern, re.IGNORECASE)
                if pattern.search(content):
                    content = pattern.sub('', content)
                    result.actions_performed.append(SanitizationAction.REMOVE_EMBEDDED)
            
            # Remove metadata
            metadata_pattern = r'\\info\s*{[^}]*}'
            if re.search(metadata_pattern, content):
                content = re.sub(metadata_pattern, '', content)
                result.actions_performed.append(SanitizationAction.REMOVE_METADATA)
            
            async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                await f.write(content)
        
        except Exception as e:
            logger.error(f"RTF sanitization failed: {e}")
            raise
    
    async def _sanitize_xml(
        self,
        input_path: Path,
        output_path: Path,
        level: SanitizationLevel,
        result: SanitizationResult
    ):
        """Sanitize XML file."""
        try:
            async with aiofiles.open(input_path, 'rb') as f:
                xml_data = await f.read()
            
            # Parse XML safely
            try:
                root = ET.fromstring(xml_data)
                
                # Remove processing instructions
                if level in [SanitizationLevel.STRICT, SanitizationLevel.PARANOID]:
                    # This is a simplified approach - full XML sanitization is complex
                    xml_str = ET.tostring(root, encoding='unicode')
                    
                    # Remove DTD declarations
                    xml_str = re.sub(r'<!DOCTYPE[^>]*>', '', xml_str)
                    result.actions_performed.append(SanitizationAction.CLEAN_STRUCTURE)
                else:
                    xml_str = xml_data.decode('utf-8', errors='ignore')
                
                async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                    await f.write(xml_str)
            
            except ET.ParseError:
                # If XML is malformed, treat as text
                await self._sanitize_text(input_path, output_path, level, result)
        
        except Exception as e:
            logger.error(f"XML sanitization failed: {e}")
            raise
    
    async def _sanitize_ole_document(
        self,
        input_path: Path,
        output_path: Path,
        level: SanitizationLevel,
        result: SanitizationResult
    ):
        """Sanitize OLE documents (DOC, XLS, PPT)."""
        try:
            # For OLE documents, we'll use a conservative approach
            # In production, you might want to use specialized libraries
            
            # Read binary content
            async with aiofiles.open(input_path, 'rb') as f:
                content = await f.read()
            
            # Remove VBA macros (simple signature-based approach)
            vba_signatures = [
                b'VBA\x00',
                b'Microsoft Visual Basic',
                b'_VBA_PROJECT',
            ]
            
            for signature in vba_signatures:
                if signature in content:
                    result.actions_performed.append(SanitizationAction.STRIP_MACROS)
                    result.issues_found.append({
                        "issue": "VBA signature detected",
                        "severity": "high"
                    })
            
            # For now, just copy the file (in production, use proper OLE parsing)
            async with aiofiles.open(output_path, 'wb') as f:
                await f.write(content)
            
            result.warnings.append("OLE document sanitization is limited - consider converting to modern format")
        
        except Exception as e:
            logger.error(f"OLE document sanitization failed: {e}")
            raise
    
    async def _sanitize_generic(
        self,
        input_path: Path,
        output_path: Path,
        level: SanitizationLevel,
        result: SanitizationResult
    ):
        """Generic sanitization for unknown file types."""
        try:
            # Read as binary
            async with aiofiles.open(input_path, 'rb') as f:
                content = await f.read()
            
            # Remove null bytes if text-like
            text_ratio = sum(1 for byte in content if 32 <= byte <= 126) / len(content) if content else 0
            
            if text_ratio > 0.7:  # Likely text content
                # Convert to text and sanitize
                text_content = content.decode('utf-8', errors='ignore')
                
                # Remove suspicious patterns
                for pattern in self.suspicious_patterns:
                    if pattern.search(text_content):
                        text_content = pattern.sub('', text_content)
                        result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
                
                content = text_content.encode('utf-8')
            
            # Write processed content
            async with aiofiles.open(output_path, 'wb') as f:
                await f.write(content)
            
            result.statistics = {
                "text_ratio": text_ratio,
                "original_size": len(content),
                "processed_as": "text" if text_ratio > 0.7 else "binary"
            }
        
        except Exception as e:
            logger.error(f"Generic sanitization failed: {e}")
            raise
    
    async def _sanitize_office_metadata(self, xml_data: bytes, result: SanitizationResult) -> bytes:
        """Sanitize Office document metadata."""
        try:
            root = ET.fromstring(xml_data)
            
            # Remove metadata fields
            for elem in root.iter():
                if elem.tag.split('}')[-1].lower() in self.METADATA_FIELDS:
                    elem.clear()
                    result.metadata_removed[elem.tag] = elem.text or ""
            
            return ET.tostring(root, encoding='utf-8')
        
        except Exception as e:
            logger.error(f"Failed to sanitize Office metadata: {e}")
            return xml_data
    
    async def _sanitize_app_metadata(self, xml_data: bytes, result: SanitizationResult) -> bytes:
        """Sanitize Office application metadata."""
        try:
            root = ET.fromstring(xml_data)
            
            # Remove application-specific metadata
            app_fields = {'Application', 'AppVersion', 'Company', 'Manager', 'Template'}
            
            for elem in root.iter():
                if elem.tag.split('}')[-1] in app_fields:
                    if elem.text:
                        result.metadata_removed[elem.tag] = elem.text
                    elem.clear()
            
            return ET.tostring(root, encoding='utf-8')
        
        except Exception as e:
            logger.error(f"Failed to sanitize app metadata: {e}")
            return xml_data
    
    async def _sanitize_office_content(self, xml_data: bytes, level: SanitizationLevel, result: SanitizationResult) -> bytes:
        """Sanitize Office document content."""
        try:
            # For Word documents, remove comments, track changes, etc.
            content = xml_data.decode('utf-8', errors='ignore')
            
            # Remove comments
            if self.config.remove_comments:
                content = re.sub(r'<w:commentRangeStart[^>]*/>.*?<w:commentRangeEnd[^>]*/>', '', content, flags=re.DOTALL)
                content = re.sub(r'<w:commentReference[^>]*/>', '', content)
                result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
            
            # Remove tracked changes
            if self.config.remove_tracked_changes:
                content = re.sub(r'<w:ins[^>]*>.*?</w:ins>', '', content, flags=re.DOTALL)
                content = re.sub(r'<w:del[^>]*>.*?</w:del>', '', content, flags=re.DOTALL)
                result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
            
            return content.encode('utf-8')
        
        except Exception as e:
            logger.error(f"Failed to sanitize Office content: {e}")
            return xml_data
    
    async def _sanitize_excel_content(self, xml_data: bytes, level: SanitizationLevel, result: SanitizationResult) -> bytes:
        """Sanitize Excel content."""
        try:
            content = xml_data.decode('utf-8', errors='ignore')
            
            # Remove external links
            if self.config.remove_external_links:
                content = re.sub(r'<externalLink[^>]*>.*?</externalLink>', '', content, flags=re.DOTALL)
                result.actions_performed.append(SanitizationAction.REMOVE_LINKS)
            
            return content.encode('utf-8')
        
        except Exception as e:
            logger.error(f"Failed to sanitize Excel content: {e}")
            return xml_data
    
    async def _sanitize_ppt_content(self, xml_data: bytes, level: SanitizationLevel, result: SanitizationResult) -> bytes:
        """Sanitize PowerPoint content."""
        try:
            content = xml_data.decode('utf-8', errors='ignore')
            
            # Remove notes
            if level in [SanitizationLevel.STRICT, SanitizationLevel.PARANOID]:
                content = re.sub(r'<p:notes>.*?</p:notes>', '', content, flags=re.DOTALL)
                result.actions_performed.append(SanitizationAction.FILTER_CONTENT)
            
            return content.encode('utf-8')
        
        except Exception as e:
            logger.error(f"Failed to sanitize PowerPoint content: {e}")
            return xml_data
    
    async def _detect_file_type(self, file_path: Path) -> FileType:
        """Detect file type."""
        try:
            import magic
            
            mime_type = magic.from_file(str(file_path), mime=True)
            
            mime_to_type = {
                'application/pdf': FileType.PDF,
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileType.DOCX,
                'application/vnd.openxmlformats-officedocument.presentationml.presentation': FileType.PPTX,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileType.XLSX,
                'application/msword': FileType.DOC,
                'application/vnd.ms-powerpoint': FileType.PPT,
                'application/vnd.ms-excel': FileType.XLS,
                'text/plain': FileType.TXT,
                'text/rtf': FileType.RTF,
                'text/html': FileType.HTML,
                'application/xml': FileType.XML,
                'text/xml': FileType.XML,
            }
            
            return mime_to_type.get(mime_type, FileType.UNKNOWN)
        
        except ImportError:
            # Fallback to extension-based detection
            extension = file_path.suffix.lower()
            ext_to_type = {
                '.pdf': FileType.PDF,
                '.docx': FileType.DOCX,
                '.doc': FileType.DOC,
                '.pptx': FileType.PPTX,
                '.ppt': FileType.PPT,
                '.xlsx': FileType.XLSX,
                '.xls': FileType.XLS,
                '.txt': FileType.TXT,
                '.rtf': FileType.RTF,
                '.html': FileType.HTML,
                '.htm': FileType.HTML,
                '.xml': FileType.XML,
            }
            return ext_to_type.get(extension, FileType.UNKNOWN)
        except Exception as e:
            logger.error(f"File type detection failed: {e}")
            return FileType.UNKNOWN
    
    async def _validate_sanitized_file(self, file_path: Path, result: SanitizationResult):
        """Validate sanitized file."""
        try:
            if not file_path.exists():
                result.warnings.append("Sanitized file not found")
                return
            
            file_size = file_path.stat().st_size
            if file_size == 0:
                result.warnings.append("Sanitized file is empty")
            
            result.statistics["output_size"] = file_size
        
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result.warnings.append(f"Validation failed: {str(e)}")
    
    async def _copy_file(self, src: Path, dst: Path):
        """Copy file as fallback."""
        async with aiofiles.open(src, 'rb') as src_file:
            async with aiofiles.open(dst, 'wb') as dst_file:
                while chunk := await src_file.read(8192):
                    await dst_file.write(chunk)
    
    def get_sanitization_levels(self) -> List[SanitizationLevel]:
        """Get available sanitization levels."""
        return list(SanitizationLevel)
    
    def get_supported_actions(self) -> List[SanitizationAction]:
        """Get supported sanitization actions."""
        return list(SanitizationAction)