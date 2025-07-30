"""
Security quarantine system for suspicious and infected files.

Provides comprehensive quarantine management including:
- Secure file isolation
- Quarantine storage encryption
- Automated cleanup policies
- Audit trail maintenance
- Recovery and analysis capabilities
- Integration with threat detection
"""

import asyncio
import json
import logging
import shutil
import tempfile
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import uuid4

import aiofiles
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.infrastructure.cache.redis import RedisClient
from .audit_logger import SecurityAuditLogger, AuditEventType

logger = logging.getLogger(__name__)


class QuarantineReason(str, Enum):
    """Quarantine reason enumeration."""
    VIRUS_DETECTED = "virus_detected"
    MALWARE_DETECTED = "malware_detected"
    SUSPICIOUS_CONTENT = "suspicious_content"
    VALIDATION_FAILED = "validation_failed"
    POLICY_VIOLATION = "policy_violation"
    MANUAL_QUARANTINE = "manual_quarantine"
    THREAT_INTELLIGENCE = "threat_intelligence"
    UNKNOWN_THREAT = "unknown_threat"


class QuarantineStatus(str, Enum):
    """Quarantine status enumeration."""
    QUARANTINED = "quarantined"
    UNDER_ANALYSIS = "under_analysis"
    RELEASED = "released"
    PERMANENTLY_DELETED = "permanently_deleted"
    EXPIRED = "expired"


class QuarantineAction(str, Enum):
    """Quarantine action enumeration."""
    ISOLATE = "isolate"
    ENCRYPT = "encrypt"
    ANALYZE = "analyze"
    NOTIFY = "notify"
    DELETE = "delete"
    RELEASE = "release"


class QuarantineRecord(BaseModel):
    """Quarantine record model."""
    quarantine_id: str = Field(..., description="Unique quarantine identifier")
    original_path: str = Field(..., description="Original file path")
    quarantine_path: str = Field(..., description="Quarantine storage path")
    file_hash: str = Field(..., description="File SHA-256 hash")
    file_size: int = Field(..., description="File size in bytes")
    quarantine_reason: QuarantineReason = Field(..., description="Reason for quarantine")
    status: QuarantineStatus = Field(..., description="Current status")
    quarantine_time: datetime = Field(default_factory=datetime.utcnow, description="Quarantine timestamp")
    detection_details: Dict = Field(default_factory=dict, description="Detection details")
    threat_info: Dict = Field(default_factory=dict, description="Threat information")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")
    retention_until: datetime = Field(..., description="Retention expiry date")
    encrypted: bool = Field(default=True, description="Whether file is encrypted")
    analysis_results: Dict = Field(default_factory=dict, description="Analysis results")
    user_id: Optional[str] = Field(None, description="User who uploaded the file")
    session_id: Optional[str] = Field(None, description="Session identifier")


class QuarantineConfig(BaseModel):
    """Quarantine configuration."""
    quarantine_dir: str = "/tmp/quarantine"
    encryption_enabled: bool = True
    retention_days: int = 30
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    max_quarantine_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    auto_cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24
    notify_on_quarantine: bool = True
    audit_enabled: bool = True
    compression_enabled: bool = True


class QuarantineManager:
    """
    Security quarantine manager.
    
    Manages secure isolation and storage of suspicious/infected files.
    """
    
    def __init__(
        self,
        config: Optional[QuarantineConfig] = None,
        redis_client: Optional[RedisClient] = None,
        audit_logger: Optional[SecurityAuditLogger] = None
    ):
        """Initialize quarantine manager."""
        self.config = config or QuarantineConfig()
        self.redis_client = redis_client
        self.audit_logger = audit_logger or SecurityAuditLogger()
        self.settings = get_settings()
        
        # Setup quarantine directory
        self.quarantine_dir = Path(self.config.quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Setup encryption
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key) if self.config.encryption_enabled else None
        
        # Create subdirectories
        self._setup_directories()
        
        logger.info(f"QuarantineManager initialized - Dir: {self.quarantine_dir}, Encryption: {bool(self._cipher)}")
    
    async def quarantine_file(
        self,
        file_path: Union[str, Path],
        reason: QuarantineReason,
        detection_details: Optional[Dict] = None,
        threat_info: Optional[Dict] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> QuarantineRecord:
        """
        Quarantine a file.
        
        Args:
            file_path: Path to file to quarantine
            reason: Reason for quarantine
            detection_details: Detection details from scanner
            threat_info: Threat information
            user_id: User who uploaded the file
            session_id: Session identifier
            
        Returns:
            QuarantineRecord: Quarantine record
        """
        file_path = Path(file_path)
        quarantine_id = self._generate_quarantine_id()
        
        logger.info(f"Quarantining file {file_path} (reason: {reason}, ID: {quarantine_id})")
        
        # Validate file
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size > self.config.max_file_size:
            raise ValueError(f"File too large for quarantine: {file_size} bytes")
        
        # Check quarantine space
        await self._check_quarantine_space(file_size)
        
        # Calculate file hash
        file_hash = await self._calculate_file_hash(file_path)
        
        # Create quarantine record
        record = QuarantineRecord(
            quarantine_id=quarantine_id,
            original_path=str(file_path),
            quarantine_path="",  # Will be set after storage
            file_hash=file_hash,
            file_size=file_size,
            quarantine_reason=reason,
            status=QuarantineStatus.QUARANTINED,
            detection_details=detection_details or {},
            threat_info=threat_info or {},
            user_id=user_id,
            session_id=session_id,
            retention_until=datetime.utcnow() + timedelta(days=self.config.retention_days),
            encrypted=self.config.encryption_enabled
        )
        
        try:
            # Store file securely
            quarantine_path = await self._store_file_securely(file_path, record)
            record.quarantine_path = str(quarantine_path)
            
            # Save record
            await self._save_record(record)
            
            # Remove original file
            file_path.unlink()
            
            # Log audit event
            if self.config.audit_enabled:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.FILE_QUARANTINED,
                    details={
                        "quarantine_id": quarantine_id,
                        "file_path": str(file_path),
                        "reason": reason,
                        "file_hash": file_hash,
                        "file_size": file_size
                    },
                    user_id=user_id,
                    session_id=session_id
                )
            
            logger.info(f"File quarantined successfully: {quarantine_id}")
            
            return record
        
        except Exception as e:
            logger.error(f"Failed to quarantine file: {e}")
            raise
    
    async def quarantine_buffer(
        self,
        data: bytes,
        filename: str,
        reason: QuarantineReason,
        detection_details: Optional[Dict] = None,
        threat_info: Optional[Dict] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> QuarantineRecord:
        """
        Quarantine data buffer.
        
        Args:
            data: Data to quarantine
            filename: Original filename
            reason: Reason for quarantine
            detection_details: Detection details
            threat_info: Threat information
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            QuarantineRecord: Quarantine record
        """
        # Write to temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(data)
            temp_path = temp_file.name
        
        try:
            record = await self.quarantine_file(
                file_path=temp_path,
                reason=reason,
                detection_details=detection_details,
                threat_info=threat_info,
                user_id=user_id,
                session_id=session_id
            )
            
            # Update metadata with original filename
            record.metadata["original_filename"] = filename
            await self._save_record(record)
            
            return record
        
        finally:
            # Clean up temp file (if still exists)
            try:
                Path(temp_path).unlink()
            except FileNotFoundError:
                pass
    
    async def get_quarantine_record(self, quarantine_id: str) -> Optional[QuarantineRecord]:
        """Get quarantine record by ID."""
        try:
            if self.redis_client:
                data = await self.redis_client.get(f"quarantine:{quarantine_id}")
                if data:
                    return QuarantineRecord(**json.loads(data))
            
            # Fallback to file storage
            record_file = self.quarantine_dir / "records" / f"{quarantine_id}.json"
            if record_file.exists():
                async with aiofiles.open(record_file, 'r') as f:
                    data = await f.read()
                    return QuarantineRecord(**json.loads(data))
        
        except Exception as e:
            logger.error(f"Failed to get quarantine record: {e}")
        
        return None
    
    async def list_quarantined_files(
        self,
        status: Optional[QuarantineStatus] = None,
        reason: Optional[QuarantineReason] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[QuarantineRecord]:
        """List quarantined files with optional filtering."""
        records = []
        
        try:
            records_dir = self.quarantine_dir / "records"
            if not records_dir.exists():
                return records
            
            count = 0
            for record_file in records_dir.glob("*.json"):
                if count >= limit:
                    break
                
                try:
                    async with aiofiles.open(record_file, 'r') as f:
                        data = await f.read()
                        record = QuarantineRecord(**json.loads(data))
                    
                    # Apply filters
                    if status and record.status != status:
                        continue
                    if reason and record.quarantine_reason != reason:
                        continue
                    if user_id and record.user_id != user_id:
                        continue
                    
                    records.append(record)
                    count += 1
                
                except Exception as e:
                    logger.error(f"Failed to load record {record_file}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to list quarantined files: {e}")
        
        return records
    
    async def release_file(
        self,
        quarantine_id: str,
        destination_path: Union[str, Path],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Release file from quarantine.
        
        Args:
            quarantine_id: Quarantine ID
            destination_path: Where to restore the file
            user_id: User performing the action
            
        Returns:
            bool: Success status
        """
        logger.info(f"Releasing file from quarantine: {quarantine_id}")
        
        try:
            record = await self.get_quarantine_record(quarantine_id)
            if not record:
                logger.error(f"Quarantine record not found: {quarantine_id}")
                return False
            
            if record.status != QuarantineStatus.QUARANTINED:
                logger.error(f"File not in quarantined status: {record.status}")
                return False
            
            # Retrieve and decrypt file
            quarantine_path = Path(record.quarantine_path)
            if not quarantine_path.exists():
                logger.error(f"Quarantined file not found: {quarantine_path}")
                return False
            
            # Read quarantined file
            async with aiofiles.open(quarantine_path, 'rb') as f:
                file_data = await f.read()
            
            # Decrypt if encrypted
            if record.encrypted and self._cipher:
                file_data = self._cipher.decrypt(file_data)
            
            # Decompress if compressed
            if record.metadata.get("compressed"):
                import gzip
                file_data = gzip.decompress(file_data)
            
            # Write to destination
            destination_path = Path(destination_path)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(destination_path, 'wb') as f:
                await f.write(file_data)
            
            # Update record status
            record.status = QuarantineStatus.RELEASED
            record.metadata["release_time"] = datetime.utcnow().isoformat()
            record.metadata["release_destination"] = str(destination_path)
            record.metadata["released_by"] = user_id
            
            await self._save_record(record)
            
            # Log audit event
            if self.config.audit_enabled:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.FILE_RELEASED,
                    details={
                        "quarantine_id": quarantine_id,
                        "destination": str(destination_path),
                        "original_path": record.original_path
                    },
                    user_id=user_id
                )
            
            logger.info(f"File released from quarantine: {quarantine_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to release file from quarantine: {e}")
            return False
    
    async def delete_quarantined_file(
        self,
        quarantine_id: str,
        user_id: Optional[str] = None,
        permanent: bool = False
    ) -> bool:
        """
        Delete quarantined file.
        
        Args:
            quarantine_id: Quarantine ID
            user_id: User performing the action
            permanent: Whether to permanently delete
            
        Returns:
            bool: Success status
        """
        logger.info(f"Deleting quarantined file: {quarantine_id} (permanent: {permanent})")
        
        try:
            record = await self.get_quarantine_record(quarantine_id)
            if not record:
                logger.error(f"Quarantine record not found: {quarantine_id}")
                return False
            
            # Delete physical file
            quarantine_path = Path(record.quarantine_path)
            if quarantine_path.exists():
                quarantine_path.unlink()
            
            # Update record status
            if permanent:
                record.status = QuarantineStatus.PERMANENTLY_DELETED
                # Remove record entirely after audit
                await self._delete_record(quarantine_id)
            else:
                record.metadata["deletion_time"] = datetime.utcnow().isoformat()
                record.metadata["deleted_by"] = user_id
                await self._save_record(record)
            
            # Log audit event
            if self.config.audit_enabled:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.FILE_DELETED,
                    details={
                        "quarantine_id": quarantine_id,
                        "permanent": permanent,
                        "original_path": record.original_path
                    },
                    user_id=user_id
                )
            
            logger.info(f"Quarantined file deleted: {quarantine_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete quarantined file: {e}")
            return False
    
    async def analyze_quarantined_file(
        self,
        quarantine_id: str,
        analysis_type: str = "basic"
    ) -> Dict:
        """
        Analyze quarantined file.
        
        Args:
            quarantine_id: Quarantine ID
            analysis_type: Type of analysis to perform
            
        Returns:
            Dict: Analysis results
        """
        logger.info(f"Analyzing quarantined file: {quarantine_id}")
        
        try:
            record = await self.get_quarantine_record(quarantine_id)
            if not record:
                return {"error": "Quarantine record not found"}
            
            # Update status
            record.status = QuarantineStatus.UNDER_ANALYSIS
            await self._save_record(record)
            
            # Read quarantined file
            quarantine_path = Path(record.quarantine_path)
            if not quarantine_path.exists():
                return {"error": "Quarantined file not found"}
            
            async with aiofiles.open(quarantine_path, 'rb') as f:
                file_data = await f.read()
            
            # Decrypt if encrypted
            if record.encrypted and self._cipher:
                file_data = self._cipher.decrypt(file_data)
            
            # Perform analysis
            analysis_results = {
                "analysis_time": datetime.utcnow().isoformat(),
                "analysis_type": analysis_type,
                "file_size": len(file_data),
                "file_hash": record.file_hash
            }
            
            if analysis_type == "basic":
                # Basic file analysis
                analysis_results.update({
                    "entropy": self._calculate_entropy(file_data),
                    "has_null_bytes": b'\x00' in file_data,
                    "printable_ratio": self._calculate_printable_ratio(file_data)
                })
            
            # Update record with analysis results
            record.analysis_results = analysis_results
            record.status = QuarantineStatus.QUARANTINED  # Return to quarantined status
            await self._save_record(record)
            
            logger.info(f"Analysis completed for quarantined file: {quarantine_id}")
            return analysis_results
        
        except Exception as e:
            logger.error(f"Failed to analyze quarantined file: {e}")
            return {"error": str(e)}
    
    async def cleanup_expired_files(self) -> int:
        """Clean up expired quarantined files."""
        logger.info("Starting cleanup of expired quarantined files")
        
        cleaned_count = 0
        
        try:
            records = await self.list_quarantined_files(limit=1000)  # Process in batches
            
            for record in records:
                if datetime.utcnow() > record.retention_until:
                    logger.info(f"Cleaning up expired file: {record.quarantine_id}")
                    
                    # Delete physical file
                    quarantine_path = Path(record.quarantine_path)
                    if quarantine_path.exists():
                        quarantine_path.unlink()
                    
                    # Update record status
                    record.status = QuarantineStatus.EXPIRED
                    await self._save_record(record)
                    
                    cleaned_count += 1
            
            logger.info(f"Cleanup completed: {cleaned_count} files processed")
        
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        return cleaned_count
    
    async def get_quarantine_stats(self) -> Dict:
        """Get quarantine statistics."""
        try:
            records = await self.list_quarantined_files(limit=10000)
            
            stats = {
                "total_files": len(records),
                "by_status": {},
                "by_reason": {},
                "total_size": 0,
                "oldest_quarantine": None,
                "newest_quarantine": None
            }
            
            for record in records:
                # Count by status
                status = record.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                
                # Count by reason
                reason = record.quarantine_reason.value
                stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1
                
                # Total size
                stats["total_size"] += record.file_size
                
                # Date tracking
                if not stats["oldest_quarantine"] or record.quarantine_time < stats["oldest_quarantine"]:
                    stats["oldest_quarantine"] = record.quarantine_time
                
                if not stats["newest_quarantine"] or record.quarantine_time > stats["newest_quarantine"]:
                    stats["newest_quarantine"] = record.quarantine_time
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get quarantine stats: {e}")
            return {"error": str(e)}
    
    async def _store_file_securely(self, file_path: Path, record: QuarantineRecord) -> Path:
        """Store file securely in quarantine."""
        # Create quarantine path
        quarantine_subdir = self.quarantine_dir / "files" / record.quarantine_id[:2]
        quarantine_subdir.mkdir(parents=True, exist_ok=True, mode=0o700)
        quarantine_path = quarantine_subdir / f"{record.quarantine_id}.quar"
        
        # Read original file
        async with aiofiles.open(file_path, 'rb') as f:
            file_data = await f.read()
        
        # Compress if enabled
        if self.config.compression_enabled:
            import gzip
            file_data = gzip.compress(file_data)
            record.metadata["compressed"] = True
        
        # Encrypt if enabled
        if self.config.encryption_enabled and self._cipher:
            file_data = self._cipher.encrypt(file_data)
        
        # Write to quarantine
        async with aiofiles.open(quarantine_path, 'wb') as f:
            await f.write(file_data)
        
        # Set restrictive permissions
        quarantine_path.chmod(0o600)
        
        return quarantine_path
    
    async def _save_record(self, record: QuarantineRecord):
        """Save quarantine record."""
        # Save to Redis if available
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"quarantine:{record.quarantine_id}",
                    86400 * self.config.retention_days,  # TTL in seconds
                    json.dumps(record.dict(), default=str)
                )
            except Exception as e:
                logger.error(f"Failed to save record to Redis: {e}")
        
        # Save to file system
        records_dir = self.quarantine_dir / "records"
        records_dir.mkdir(exist_ok=True, mode=0o700)
        
        record_file = records_dir / f"{record.quarantine_id}.json"
        async with aiofiles.open(record_file, 'w') as f:
            await f.write(json.dumps(record.dict(), default=str, indent=2))
        
        record_file.chmod(0o600)
    
    async def _delete_record(self, quarantine_id: str):
        """Delete quarantine record."""
        # Delete from Redis
        if self.redis_client:
            try:
                await self.redis_client.delete(f"quarantine:{quarantine_id}")
            except Exception as e:
                logger.error(f"Failed to delete record from Redis: {e}")
        
        # Delete from file system
        record_file = self.quarantine_dir / "records" / f"{quarantine_id}.json"
        if record_file.exists():
            record_file.unlink()
    
    async def _check_quarantine_space(self, required_size: int):
        """Check if there's enough space in quarantine."""
        try:
            # Calculate current quarantine size
            current_size = 0
            files_dir = self.quarantine_dir / "files"
            
            if files_dir.exists():
                for file_path in files_dir.rglob("*.quar"):
                    current_size += file_path.stat().st_size
            
            if current_size + required_size > self.config.max_quarantine_size:
                # Try to clean up expired files
                await self.cleanup_expired_files()
                
                # Recalculate
                current_size = 0
                if files_dir.exists():
                    for file_path in files_dir.rglob("*.quar"):
                        current_size += file_path.stat().st_size
                
                if current_size + required_size > self.config.max_quarantine_size:
                    raise ValueError("Quarantine storage full")
        
        except Exception as e:
            logger.error(f"Failed to check quarantine space: {e}")
            raise
    
    def _setup_directories(self):
        """Setup quarantine directory structure."""
        subdirs = ["files", "records", "temp", "logs"]
        
        for subdir in subdirs:
            dir_path = self.quarantine_dir / subdir
            dir_path.mkdir(exist_ok=True, mode=0o700)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key."""
        key_file = self.quarantine_dir / ".encryption_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            key_file.chmod(0o600)
            return key
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
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
    
    def _calculate_printable_ratio(self, data: bytes) -> float:
        """Calculate ratio of printable characters."""
        if not data:
            return 0.0
        
        printable_count = sum(1 for byte in data if 32 <= byte <= 126)
        return printable_count / len(data)
    
    def _generate_quarantine_id(self) -> str:
        """Generate unique quarantine ID."""
        return f"quar_{uuid4().hex[:16]}_{int(datetime.utcnow().timestamp())}"
    
    async def start_background_cleanup(self):
        """Start background cleanup task."""
        if not self.config.auto_cleanup_enabled:
            return
        
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                    await self.cleanup_expired_files()
                except Exception as e:
                    logger.error(f"Background cleanup failed: {e}")
        
        asyncio.create_task(cleanup_task())