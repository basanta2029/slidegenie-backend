"""
Virus scanning service with ClamAV and VirusTotal integration.

Provides comprehensive malware detection capabilities including:
- Local ClamAV scanning
- VirusTotal API integration
- Real-time threat intelligence
- Quarantine integration
- Scan result caching
"""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

import aiofiles
import aiohttp
import pyclamd
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.infrastructure.cache.redis import RedisClient

logger = logging.getLogger(__name__)


class ScanStatus(str, Enum):
    """Scan status enumeration."""
    CLEAN = "clean"
    INFECTED = "infected"
    SUSPICIOUS = "suspicious"
    ERROR = "error"
    PENDING = "pending"


class ThreatType(str, Enum):
    """Threat type enumeration."""
    VIRUS = "virus"
    MALWARE = "malware"
    TROJAN = "trojan"
    ROOTKIT = "rootkit"
    ADWARE = "adware"
    SPYWARE = "spyware"
    RANSOMWARE = "ransomware"
    PHISHING = "phishing"
    SUSPICIOUS = "suspicious"
    UNKNOWN = "unknown"


class ScanResult(BaseModel):
    """Scan result model."""
    scan_id: str = Field(..., description="Unique scan identifier")
    file_hash: str = Field(..., description="File SHA-256 hash")
    status: ScanStatus = Field(..., description="Scan status")
    threats: List[Dict] = Field(default_factory=list, description="Detected threats")
    scan_engines: Dict[str, Dict] = Field(default_factory=dict, description="Engine results")
    scan_time: datetime = Field(default_factory=datetime.utcnow, description="Scan timestamp")
    engine_count: int = Field(default=0, description="Number of engines used")
    detection_count: int = Field(default=0, description="Number of detections")
    confidence_score: float = Field(default=0.0, description="Overall confidence score")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class ScannerConfig(BaseModel):
    """Scanner configuration."""
    clamav_enabled: bool = True
    virustotal_enabled: bool = True
    virustotal_api_key: Optional[str] = None
    virustotal_timeout: int = 300
    clamav_socket: str = "/var/run/clamav/clamd.sock"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    cache_ttl: int = 3600  # 1 hour
    parallel_scans: int = 3
    threat_threshold: float = 0.3
    quarantine_threats: bool = True


class VirusScanner:
    """
    Comprehensive virus scanning service.
    
    Integrates multiple scanning engines for robust malware detection.
    """
    
    def __init__(self, config: Optional[ScannerConfig] = None, redis_client: Optional[RedisClient] = None):
        """Initialize virus scanner."""
        self.config = config or ScannerConfig()
        self.redis_client = redis_client
        self.settings = get_settings()
        
        # Initialize ClamAV connection
        self._clamav = None
        if self.config.clamav_enabled:
            try:
                self._clamav = pyclamd.ClamdUnixSocket(self.config.clamav_socket)
                if not self._clamav.ping():
                    logger.warning("ClamAV daemon not responding")
                    self._clamav = None
            except Exception as e:
                logger.warning(f"Failed to connect to ClamAV: {e}")
                self._clamav = None
        
        # VirusTotal API configuration
        self._vt_api_key = self.config.virustotal_api_key or os.getenv('VIRUSTOTAL_API_KEY')
        self._vt_base_url = "https://www.virustotal.com/vtapi/v2/"
        
        logger.info(f"VirusScanner initialized - ClamAV: {self._clamav is not None}, VirusTotal: {bool(self._vt_api_key)}")
    
    async def scan_file(self, file_path: Union[str, Path], scan_id: Optional[str] = None) -> ScanResult:
        """
        Scan a file for malware.
        
        Args:
            file_path: Path to file to scan
            scan_id: Optional scan identifier
            
        Returns:
            ScanResult: Comprehensive scan results
        """
        file_path = Path(file_path)
        scan_id = scan_id or self._generate_scan_id()
        
        logger.info(f"Starting virus scan for {file_path} (scan_id: {scan_id})")
        
        # Check file exists and size
        if not file_path.exists():
            return ScanResult(
                scan_id=scan_id,
                file_hash="",
                status=ScanStatus.ERROR,
                metadata={"error": "File not found"}
            )
        
        file_size = file_path.stat().st_size
        if file_size > self.config.max_file_size:
            return ScanResult(
                scan_id=scan_id,
                file_hash="",
                status=ScanStatus.ERROR,
                metadata={"error": f"File too large: {file_size} bytes"}
            )
        
        # Calculate file hash
        file_hash = await self._calculate_file_hash(file_path)
        
        # Check cache first
        cached_result = await self._get_cached_result(file_hash)
        if cached_result:
            logger.info(f"Using cached scan result for {file_hash}")
            cached_result.scan_id = scan_id
            return cached_result
        
        # Perform scans
        scan_tasks = []
        
        if self._clamav:
            scan_tasks.append(self._scan_with_clamav(file_path))
        
        if self._vt_api_key:
            scan_tasks.append(self._scan_with_virustotal(file_path, file_hash))
        
        if not scan_tasks:
            return ScanResult(
                scan_id=scan_id,
                file_hash=file_hash,
                status=ScanStatus.ERROR,
                metadata={"error": "No scanning engines available"}
            )
        
        # Execute scans in parallel
        scan_results = await asyncio.gather(*scan_tasks, return_exceptions=True)
        
        # Aggregate results
        result = await self._aggregate_scan_results(
            scan_id=scan_id,
            file_hash=file_hash,
            scan_results=scan_results
        )
        
        # Cache result
        await self._cache_result(file_hash, result)
        
        logger.info(f"Scan completed for {file_path}: {result.status} ({result.detection_count} detections)")
        
        return result
    
    async def scan_buffer(self, data: bytes, filename: str = "buffer", scan_id: Optional[str] = None) -> ScanResult:
        """
        Scan data buffer for malware.
        
        Args:
            data: Data to scan
            filename: Filename for identification
            scan_id: Optional scan identifier
            
        Returns:
            ScanResult: Scan results
        """
        if len(data) > self.config.max_file_size:
            return ScanResult(
                scan_id=scan_id or self._generate_scan_id(),
                file_hash="",
                status=ScanStatus.ERROR,
                metadata={"error": f"Buffer too large: {len(data)} bytes"}
            )
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(data)
            temp_path = temp_file.name
        
        try:
            result = await self.scan_file(temp_path, scan_id)
            result.metadata["original_filename"] = filename
            return result
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    async def get_scan_status(self, scan_id: str) -> Optional[ScanStatus]:
        """Get status of a scan by ID."""
        if not self.redis_client:
            return None
        
        try:
            status_data = await self.redis_client.get(f"scan_status:{scan_id}")
            if status_data:
                return ScanStatus(status_data)
        except Exception as e:
            logger.error(f"Failed to get scan status: {e}")
        
        return None
    
    async def _scan_with_clamav(self, file_path: Path) -> Dict:
        """Scan file with ClamAV."""
        if not self._clamav:
            return {"engine": "clamav", "error": "ClamAV not available"}
        
        try:
            result = self._clamav.scan_file(str(file_path))
            
            if result is None:
                return {
                    "engine": "clamav",
                    "status": "clean",
                    "threats": []
                }
            elif isinstance(result, dict) and str(file_path) in result:
                threat_info = result[str(file_path)]
                threat_name = threat_info[1] if isinstance(threat_info, tuple) else str(threat_info)
                
                return {
                    "engine": "clamav",
                    "status": "infected",
                    "threats": [{
                        "name": threat_name,
                        "type": self._classify_threat(threat_name),
                        "confidence": 0.9
                    }]
                }
            else:
                return {
                    "engine": "clamav",
                    "status": "clean",
                    "threats": []
                }
        
        except Exception as e:
            logger.error(f"ClamAV scan failed: {e}")
            return {"engine": "clamav", "error": str(e)}
    
    async def _scan_with_virustotal(self, file_path: Path, file_hash: str) -> Dict:
        """Scan file with VirusTotal."""
        if not self._vt_api_key:
            return {"engine": "virustotal", "error": "VirusTotal API key not available"}
        
        try:
            async with aiohttp.ClientSession() as session:
                # First check if hash is already known
                report = await self._get_virustotal_report(session, file_hash)
                
                if report and report.get("response_code") == 1:
                    # Hash found, use existing report
                    return self._parse_virustotal_report(report)
                
                # Upload file for scanning
                upload_result = await self._upload_to_virustotal(session, file_path)
                
                if not upload_result or upload_result.get("response_code") != 1:
                    return {"engine": "virustotal", "error": "Upload failed"}
                
                # Wait for scan completion
                resource = upload_result.get("resource") or file_hash
                
                for attempt in range(10):  # Max 10 attempts
                    await asyncio.sleep(5)  # Wait 5 seconds between checks
                    
                    report = await self._get_virustotal_report(session, resource)
                    
                    if report and report.get("response_code") == 1:
                        return self._parse_virustotal_report(report)
                
                return {"engine": "virustotal", "status": "pending"}
        
        except Exception as e:
            logger.error(f"VirusTotal scan failed: {e}")
            return {"engine": "virustotal", "error": str(e)}
    
    async def _get_virustotal_report(self, session: aiohttp.ClientSession, resource: str) -> Optional[Dict]:
        """Get VirusTotal scan report."""
        url = urljoin(self._vt_base_url, "file/report")
        params = {
            "apikey": self._vt_api_key,
            "resource": resource
        }
        
        try:
            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to get VirusTotal report: {e}")
        
        return None
    
    async def _upload_to_virustotal(self, session: aiohttp.ClientSession, file_path: Path) -> Optional[Dict]:
        """Upload file to VirusTotal."""
        url = urljoin(self._vt_base_url, "file/scan")
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()
            
            data = aiohttp.FormData()
            data.add_field('apikey', self._vt_api_key)
            data.add_field('file', file_data, filename=file_path.name)
            
            async with session.post(url, data=data, timeout=60) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to upload to VirusTotal: {e}")
        
        return None
    
    def _parse_virustotal_report(self, report: Dict) -> Dict:
        """Parse VirusTotal scan report."""
        scans = report.get("scans", {})
        positives = report.get("positives", 0)
        total = report.get("total", 0)
        
        threats = []
        for engine, result in scans.items():
            if result.get("detected"):
                threat_name = result.get("result", "Unknown")
                threats.append({
                    "name": threat_name,
                    "type": self._classify_threat(threat_name),
                    "engine": engine,
                    "confidence": 0.8,
                    "version": result.get("version"),
                    "update": result.get("update")
                })
        
        status = "infected" if positives > 0 else "clean"
        if total > 0 and positives / total < self.config.threat_threshold:
            status = "suspicious"
        
        return {
            "engine": "virustotal",
            "status": status,
            "threats": threats,
            "positives": positives,
            "total": total,
            "scan_date": report.get("scan_date"),
            "permalink": report.get("permalink")
        }
    
    def _classify_threat(self, threat_name: str) -> ThreatType:
        """Classify threat based on name."""
        threat_name_lower = threat_name.lower()
        
        if any(keyword in threat_name_lower for keyword in ["virus", "viral"]):
            return ThreatType.VIRUS
        elif any(keyword in threat_name_lower for keyword in ["trojan", "trj"]):
            return ThreatType.TROJAN
        elif any(keyword in threat_name_lower for keyword in ["rootkit"]):
            return ThreatType.ROOTKIT
        elif any(keyword in threat_name_lower for keyword in ["adware", "adw"]):
            return ThreatType.ADWARE
        elif any(keyword in threat_name_lower for keyword in ["spyware", "spy"]):
            return ThreatType.SPYWARE
        elif any(keyword in threat_name_lower for keyword in ["ransom", "crypt", "locker"]):
            return ThreatType.RANSOMWARE
        elif any(keyword in threat_name_lower for keyword in ["phish", "fake"]):
            return ThreatType.PHISHING
        elif any(keyword in threat_name_lower for keyword in ["malware", "malicious"]):
            return ThreatType.MALWARE
        elif any(keyword in threat_name_lower for keyword in ["suspicious", "suspect", "heur"]):
            return ThreatType.SUSPICIOUS
        else:
            return ThreatType.UNKNOWN
    
    async def _aggregate_scan_results(self, scan_id: str, file_hash: str, scan_results: List) -> ScanResult:
        """Aggregate results from multiple scanning engines."""
        all_threats = []
        engine_results = {}
        total_engines = 0
        detection_count = 0
        
        for result in scan_results:
            if isinstance(result, Exception):
                logger.error(f"Scan engine error: {result}")
                continue
            
            if "error" in result:
                logger.warning(f"Engine {result.get('engine')} error: {result['error']}")
                continue
            
            engine_name = result.get("engine", "unknown")
            engine_results[engine_name] = result
            total_engines += 1
            
            if result.get("status") in ["infected", "suspicious"]:
                detection_count += 1
                threats = result.get("threats", [])
                all_threats.extend(threats)
        
        # Determine overall status
        if detection_count == 0:
            status = ScanStatus.CLEAN
        elif detection_count == total_engines:
            status = ScanStatus.INFECTED
        else:
            status = ScanStatus.SUSPICIOUS
        
        # Calculate confidence score
        confidence_score = 0.0
        if total_engines > 0:
            if status == ScanStatus.INFECTED:
                confidence_score = min(0.9, detection_count / total_engines)
            elif status == ScanStatus.SUSPICIOUS:
                confidence_score = detection_count / total_engines * 0.5
            else:
                confidence_score = 1.0 - (detection_count / total_engines * 0.1)
        
        # Deduplicate threats
        unique_threats = self._deduplicate_threats(all_threats)
        
        return ScanResult(
            scan_id=scan_id,
            file_hash=file_hash,
            status=status,
            threats=unique_threats,
            scan_engines=engine_results,
            engine_count=total_engines,
            detection_count=detection_count,
            confidence_score=confidence_score,
            metadata={
                "scan_engines_used": list(engine_results.keys()),
                "total_scan_time": sum(
                    result.get("scan_time", 0) for result in engine_results.values()
                    if isinstance(result.get("scan_time"), (int, float))
                )
            }
        )
    
    def _deduplicate_threats(self, threats: List[Dict]) -> List[Dict]:
        """Remove duplicate threats based on name similarity."""
        if not threats:
            return []
        
        unique_threats = []
        seen_names = set()
        
        for threat in threats:
            name = threat.get("name", "").lower()
            
            # Simple deduplication based on threat name
            if name not in seen_names:
                unique_threats.append(threat)
                seen_names.add(name)
        
        return unique_threats
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _get_cached_result(self, file_hash: str) -> Optional[ScanResult]:
        """Get cached scan result."""
        if not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(f"scan_result:{file_hash}")
            if cached_data:
                data = json.loads(cached_data)
                return ScanResult(**data)
        except Exception as e:
            logger.error(f"Failed to get cached result: {e}")
        
        return None
    
    async def _cache_result(self, file_hash: str, result: ScanResult):
        """Cache scan result."""
        if not self.redis_client:
            return
        
        try:
            cached_data = result.dict()
            await self.redis_client.setex(
                f"scan_result:{file_hash}",
                self.config.cache_ttl,
                json.dumps(cached_data, default=str)
            )
        except Exception as e:
            logger.error(f"Failed to cache result: {e}")
    
    def _generate_scan_id(self) -> str:
        """Generate unique scan ID."""
        import uuid
        return f"scan_{uuid.uuid4().hex[:12]}"
    
    async def get_engine_status(self) -> Dict[str, Dict]:
        """Get status of all scanning engines."""
        status = {}
        
        # ClamAV status
        if self._clamav:
            try:
                clamav_version = self._clamav.version()
                status["clamav"] = {
                    "available": True,
                    "version": clamav_version,
                    "last_update": self._clamav.stats().get("DatabaseDate", "Unknown")
                }
            except Exception as e:
                status["clamav"] = {
                    "available": False,
                    "error": str(e)
                }
        else:
            status["clamav"] = {"available": False, "error": "Not configured"}
        
        # VirusTotal status
        if self._vt_api_key:
            status["virustotal"] = {
                "available": True,
                "api_key_configured": True
            }
        else:
            status["virustotal"] = {
                "available": False,
                "error": "API key not configured"
            }
        
        return status