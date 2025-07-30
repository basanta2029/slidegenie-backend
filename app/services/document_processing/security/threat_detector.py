"""
Threat detection and response service.

Provides comprehensive threat detection including:
- Advanced heuristic analysis
- Behavioral pattern detection  
- Machine learning threat classification
- Threat intelligence integration
- Automated response workflows
- Risk scoring and prioritization
"""

import asyncio
import hashlib
import json
import logging
import pickle
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import aiofiles
import aiohttp
import numpy as np
from pydantic import BaseModel, Field
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

from app.core.config import get_settings
from app.infrastructure.cache.redis import RedisClient
from .audit_logger import SecurityAuditLogger, AuditEventType, AuditLevel
from .file_validator import ValidationResult, SecurityRisk

logger = logging.getLogger(__name__)


class ThreatType(str, Enum):
    """Threat type enumeration."""
    MALWARE = "malware"
    VIRUS = "virus"
    RANSOMWARE = "ransomware"
    TROJAN = "trojan"
    ROOTKIT = "rootkit"
    SPYWARE = "spyware"
    ADWARE = "adware"
    PHISHING = "phishing"
    EXPLOIT = "exploit"
    BACKDOOR = "backdoor"
    BOTNET = "botnet"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    UNKNOWN = "unknown"


class ThreatSeverity(str, Enum):
    """Threat severity levels."""
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatSource(str, Enum):
    """Threat detection source."""
    HEURISTIC = "heuristic"
    SIGNATURE = "signature"
    BEHAVIORAL = "behavioral"
    MACHINE_LEARNING = "machine_learning"
    THREAT_INTELLIGENCE = "threat_intelligence"
    USER_REPORT = "user_report"
    SANDBOX = "sandbox"


class ResponseAction(str, Enum):
    """Automated response actions."""
    QUARANTINE = "quarantine"
    BLOCK = "block"
    ALERT = "alert"
    LOG = "log"
    NOTIFY_ADMIN = "notify_admin"
    DELETE = "delete"
    ISOLATE_USER = "isolate_user"
    SCAN_SYSTEM = "scan_system"


class ThreatIndicator(BaseModel):
    """Threat indicator model."""
    indicator_type: str = Field(..., description="Type of indicator")
    value: str = Field(..., description="Indicator value")
    confidence: float = Field(..., description="Confidence score (0-1)")
    source: ThreatSource = Field(..., description="Detection source")
    first_seen: datetime = Field(default_factory=datetime.utcnow, description="First seen timestamp")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="Last seen timestamp")
    count: int = Field(default=1, description="Number of times seen")


class ThreatDetection(BaseModel):
    """Threat detection result."""
    detection_id: str = Field(..., description="Unique detection identifier")
    threat_type: ThreatType = Field(..., description="Type of threat")
    severity: ThreatSeverity = Field(..., description="Threat severity")
    confidence: float = Field(..., description="Detection confidence (0-1)")
    risk_score: float = Field(..., description="Risk score (0-1)")
    
    # Detection details
    source: ThreatSource = Field(..., description="Detection source")
    detection_time: datetime = Field(default_factory=datetime.utcnow, description="Detection timestamp")
    indicators: List[ThreatIndicator] = Field(default_factory=list, description="Threat indicators")
    
    # Context
    file_path: Optional[str] = Field(None, description="Associated file path")
    file_hash: Optional[str] = Field(None, description="Associated file hash")
    user_id: Optional[str] = Field(None, description="Associated user")
    session_id: Optional[str] = Field(None, description="Associated session")
    
    # Analysis details
    analysis_results: Dict[str, Any] = Field(default_factory=dict, description="Detailed analysis results")
    mitre_tactics: List[str] = Field(default_factory=list, description="MITRE ATT&CK tactics")
    mitre_techniques: List[str] = Field(default_factory=list, description="MITRE ATT&CK techniques")
    
    # Response
    recommended_actions: List[ResponseAction] = Field(default_factory=list, description="Recommended response actions")
    automated_actions: List[ResponseAction] = Field(default_factory=list, description="Automated actions taken")
    
    # Intelligence
    threat_intel_matches: List[Dict] = Field(default_factory=list, description="Threat intelligence matches")
    family: Optional[str] = Field(None, description="Threat family")
    campaign: Optional[str] = Field(None, description="Associated campaign")


class ThreatProfile(BaseModel):
    """User/system threat profile."""
    profile_id: str = Field(..., description="Profile identifier")
    entity_type: str = Field(..., description="Profile entity type (user, system, etc.)")
    entity_id: str = Field(..., description="Entity identifier")
    
    # Risk metrics
    baseline_risk: float = Field(default=0.0, description="Baseline risk score")
    current_risk: float = Field(default=0.0, description="Current risk score")
    risk_history: List[Tuple[datetime, float]] = Field(default_factory=list, description="Risk score history")
    
    # Behavioral patterns
    normal_behavior: Dict[str, Any] = Field(default_factory=dict, description="Normal behavior patterns")
    anomaly_threshold: float = Field(default=0.7, description="Anomaly detection threshold")
    
    # Threat history
    detections: List[str] = Field(default_factory=list, description="Historical detection IDs")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class ThreatDetectorConfig(BaseModel):
    """Threat detector configuration."""
    # Detection settings
    enable_heuristics: bool = True
    enable_ml_detection: bool = True
    enable_behavioral_analysis: bool = True
    enable_threat_intel: bool = True
    
    # Thresholds
    low_risk_threshold: float = 0.3
    medium_risk_threshold: float = 0.6
    high_risk_threshold: float = 0.8
    confidence_threshold: float = 0.5
    
    # Machine learning
    ml_model_path: str = "/var/lib/threat_models/"
    retrain_interval_hours: int = 24
    feature_update_interval: int = 3600  # 1 hour
    
    # Threat intelligence
    threat_intel_sources: List[str] = ["abuse_ch", "malware_bazaar", "urlhaus"]
    intel_update_interval: int = 3600  # 1 hour
    intel_api_keys: Dict[str, str] = {}
    
    # Response settings
    auto_quarantine_critical: bool = True
    auto_quarantine_high: bool = False
    auto_notify_admin: bool = True
    max_response_time: int = 300  # 5 minutes
    
    # Performance
    max_concurrent_analyses: int = 5
    analysis_timeout: int = 300  # 5 minutes
    cache_results: bool = True
    cache_ttl: int = 3600  # 1 hour


class ThreatDetector:
    """
    Advanced threat detection and response service.
    
    Combines multiple detection methods for comprehensive threat analysis.
    """
    
    def __init__(
        self,
        config: Optional[ThreatDetectorConfig] = None,
        redis_client: Optional[RedisClient] = None,
        audit_logger: Optional[SecurityAuditLogger] = None
    ):
        """Initialize threat detector."""
        self.config = config or ThreatDetectorConfig()
        self.redis_client = redis_client
        self.audit_logger = audit_logger or SecurityAuditLogger()
        self.settings = get_settings()
        
        # Initialize models
        self._ml_models = {}
        self._vectorizers = {}
        self._scalers = {}
        
        # Threat intelligence cache
        self._threat_intel_cache = {}
        self._intel_last_update = {}
        
        # Behavioral profiles
        self._threat_profiles = {}
        
        # Detection rules
        self._heuristic_rules = self._load_heuristic_rules()
        
        # Initialize ML models
        asyncio.create_task(self._initialize_ml_models())
        
        # Start background tasks
        asyncio.create_task(self._start_background_tasks())
        
        logger.info("ThreatDetector initialized")
    
    async def analyze_file(
        self,
        file_path: Union[str, Path],
        file_hash: str,
        validation_result: Optional[ValidationResult] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ThreatDetection:
        """
        Analyze file for threats.
        
        Args:
            file_path: Path to file to analyze
            file_hash: File hash
            validation_result: File validation results
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            ThreatDetection: Threat analysis results
        """
        file_path = Path(file_path)
        detection_id = self._generate_detection_id()
        
        logger.info(f"Starting threat analysis for {file_path} (detection_id: {detection_id})")
        
        # Check cache first
        cached_result = await self._get_cached_detection(file_hash)
        if cached_result:
            logger.info(f"Using cached threat detection for {file_hash}")
            cached_result.detection_id = detection_id
            return cached_result
        
        # Initialize detection result
        detection = ThreatDetection(
            detection_id=detection_id,
            threat_type=ThreatType.UNKNOWN,
            severity=ThreatSeverity.INFORMATIONAL,
            confidence=0.0,
            risk_score=0.0,
            source=ThreatSource.HEURISTIC,
            file_path=str(file_path),
            file_hash=file_hash,
            user_id=user_id,
            session_id=session_id
        )
        
        try:
            # Perform multiple analysis methods
            analysis_tasks = []
            
            if self.config.enable_heuristics:
                analysis_tasks.append(self._heuristic_analysis(file_path, detection))
            
            if self.config.enable_ml_detection:
                analysis_tasks.append(self._ml_analysis(file_path, detection))
            
            if self.config.enable_behavioral_analysis and user_id:
                analysis_tasks.append(self._behavioral_analysis(user_id, detection))
            
            if self.config.enable_threat_intel:
                analysis_tasks.append(self._threat_intel_analysis(file_hash, detection))
            
            # Run analyses concurrently with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*analysis_tasks, return_exceptions=True),
                    timeout=self.config.analysis_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Threat analysis timed out for {file_path}")
                detection.analysis_results["timeout"] = True
            
            # Incorporate validation results
            if validation_result:
                await self._incorporate_validation_results(validation_result, detection)
            
            # Calculate final scores
            detection = await self._calculate_final_scores(detection)
            
            # Determine response actions
            detection.recommended_actions = self._determine_response_actions(detection)
            
            # Execute automated responses
            if self._should_auto_respond(detection):
                detection.automated_actions = await self._execute_automated_response(detection)
            
            # Cache result
            if self.config.cache_results:
                await self._cache_detection(file_hash, detection)
            
            # Log detection
            await self._log_detection(detection)
            
            logger.info(f"Threat analysis completed: {detection.threat_type} (severity: {detection.severity}, risk: {detection.risk_score:.2f})")
            
        except Exception as e:
            logger.error(f"Threat analysis failed: {e}")
            detection.analysis_results["error"] = str(e)
            detection.severity = ThreatSeverity.MEDIUM
            detection.confidence = 0.1
        
        return detection
    
    async def analyze_buffer(
        self,
        data: bytes,
        filename: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ThreatDetection:
        """Analyze data buffer for threats."""
        # Calculate hash
        file_hash = hashlib.sha256(data).hexdigest()
        
        # Write to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(data)
            temp_path = temp_file.name
        
        try:
            detection = await self.analyze_file(
                file_path=temp_path,
                file_hash=file_hash,
                user_id=user_id,
                session_id=session_id
            )
            
            # Update file path to original filename
            detection.file_path = filename
            
            return detection
        
        finally:
            # Clean up temp file
            try:
                Path(temp_path).unlink()
            except FileNotFoundError:
                pass
    
    async def get_threat_profile(self, entity_type: str, entity_id: str) -> ThreatProfile:
        """Get or create threat profile for entity."""
        profile_id = f"{entity_type}:{entity_id}"
        
        if profile_id in self._threat_profiles:
            return self._threat_profiles[profile_id]
        
        # Try to load from cache/storage
        if self.redis_client:
            try:
                data = await self.redis_client.get(f"threat_profile:{profile_id}")
                if data:
                    profile = ThreatProfile(**json.loads(data))
                    self._threat_profiles[profile_id] = profile
                    return profile
            except Exception as e:
                logger.error(f"Failed to load threat profile: {e}")
        
        # Create new profile
        profile = ThreatProfile(
            profile_id=profile_id,
            entity_type=entity_type,
            entity_id=entity_id
        )
        
        self._threat_profiles[profile_id] = profile
        await self._save_threat_profile(profile)
        
        return profile
    
    async def update_threat_intelligence(self, source: str = "all") -> Dict[str, int]:
        """Update threat intelligence data."""
        logger.info(f"Updating threat intelligence from source: {source}")
        
        results = {}
        
        if source == "all" or source == "abuse_ch":
            results["abuse_ch"] = await self._update_abuse_ch_intel()
        
        if source == "all" or source == "malware_bazaar":
            results["malware_bazaar"] = await self._update_malware_bazaar_intel()
        
        if source == "all" or source == "urlhaus":
            results["urlhaus"] = await self._update_urlhaus_intel()
        
        logger.info(f"Threat intelligence update completed: {results}")
        return results
    
    async def _heuristic_analysis(self, file_path: Path, detection: ThreatDetection):
        """Perform heuristic-based threat analysis."""
        try:
            logger.debug(f"Starting heuristic analysis for {file_path}")
            
            # Read file content (limited)
            max_read_size = min(1024 * 1024, file_path.stat().st_size)  # Max 1MB
            
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read(max_read_size)
            
            threats_found = []
            total_score = 0.0
            
            # Apply heuristic rules
            for rule in self._heuristic_rules:
                try:
                    score = await self._apply_heuristic_rule(rule, content, file_path)
                    if score > 0:
                        threats_found.append({
                            "rule": rule["name"],
                            "score": score,
                            "description": rule["description"]
                        })
                        total_score += score
                
                except Exception as e:
                    logger.error(f"Heuristic rule {rule.get('name', 'unknown')} failed: {e}")
            
            # Update detection
            if threats_found:
                detection.indicators.extend([
                    ThreatIndicator(
                        indicator_type="heuristic_rule",
                        value=threat["rule"],
                        confidence=min(1.0, threat["score"]),
                        source=ThreatSource.HEURISTIC
                    )
                    for threat in threats_found
                ])
                
                detection.analysis_results["heuristic"] = {
                    "threats_found": threats_found,
                    "total_score": total_score,
                    "rules_triggered": len(threats_found)
                }
                
                # Classify threat type based on rules
                if any("ransomware" in t["rule"].lower() for t in threats_found):
                    detection.threat_type = ThreatType.RANSOMWARE
                elif any("trojan" in t["rule"].lower() for t in threats_found):
                    detection.threat_type = ThreatType.TROJAN
                elif any("virus" in t["rule"].lower() for t in threats_found):
                    detection.threat_type = ThreatType.VIRUS
                else:
                    detection.threat_type = ThreatType.MALWARE
            
            logger.debug(f"Heuristic analysis completed: {len(threats_found)} threats found")
        
        except Exception as e:
            logger.error(f"Heuristic analysis failed: {e}")
            detection.analysis_results["heuristic_error"] = str(e)
    
    async def _ml_analysis(self, file_path: Path, detection: ThreatDetection):
        """Perform machine learning based threat analysis."""
        try:
            logger.debug(f"Starting ML analysis for {file_path}")
            
            if not self._ml_models:
                logger.warning("ML models not available")
                return
            
            # Extract features
            features = await self._extract_ml_features(file_path)
            
            if not features:
                logger.warning("Failed to extract ML features")
                return
            
            # Apply ML models
            ml_results = {}
            
            for model_name, model in self._ml_models.items():
                try:
                    # Prepare features
                    if model_name in self._scalers:
                        scaled_features = self._scalers[model_name].transform([features])
                    else:
                        scaled_features = [features]
                    
                    # Predict
                    if hasattr(model, 'predict_proba'):
                        proba = model.predict_proba(scaled_features)[0]
                        prediction = model.classes_[np.argmax(proba)]
                        confidence = np.max(proba)
                    else:
                        prediction = model.predict(scaled_features)[0]
                        confidence = 0.8 if prediction == 1 else 0.2
                    
                    ml_results[model_name] = {
                        "prediction": prediction,
                        "confidence": float(confidence),
                        "is_threat": prediction == 1 or prediction == "malware"
                    }
                
                except Exception as e:
                    logger.error(f"ML model {model_name} prediction failed: {e}")
            
            # Update detection based on ML results
            if ml_results:
                threat_predictions = [r for r in ml_results.values() if r["is_threat"]]
                
                if threat_predictions:
                    avg_confidence = sum(r["confidence"] for r in threat_predictions) / len(threat_predictions)
                    
                    detection.indicators.append(ThreatIndicator(
                        indicator_type="ml_prediction",
                        value="threat_detected",
                        confidence=avg_confidence,
                        source=ThreatSource.MACHINE_LEARNING
                    ))
                    
                    detection.analysis_results["ml"] = ml_results
                    
                    # Update threat type if not already set
                    if detection.threat_type == ThreatType.UNKNOWN:
                        detection.threat_type = ThreatType.MALWARE
            
            logger.debug(f"ML analysis completed: {len(ml_results)} models applied")
        
        except Exception as e:
            logger.error(f"ML analysis failed: {e}")
            detection.analysis_results["ml_error"] = str(e)
    
    async def _behavioral_analysis(self, user_id: str, detection: ThreatDetection):
        """Perform behavioral analysis based on user profile."""
        try:
            logger.debug(f"Starting behavioral analysis for user {user_id}")
            
            # Get user threat profile
            profile = await self.get_threat_profile("user", user_id)
            
            # Analyze current behavior against baseline
            current_behavior = {
                "upload_time": datetime.utcnow().hour,
                "file_type": Path(detection.file_path).suffix.lower() if detection.file_path else "",
                "file_size": Path(detection.file_path).stat().st_size if detection.file_path else 0
            }
            
            anomaly_score = 0.0
            
            # Check for behavioral anomalies
            if profile.normal_behavior:
                anomaly_score = self._calculate_behavior_anomaly(current_behavior, profile.normal_behavior)
            
            # Update user profile
            await self._update_behavior_profile(profile, current_behavior)
            
            if anomaly_score > profile.anomaly_threshold:
                detection.indicators.append(ThreatIndicator(
                    indicator_type="behavioral_anomaly",
                    value=f"anomaly_score_{anomaly_score:.2f}",
                    confidence=min(1.0, anomaly_score),
                    source=ThreatSource.BEHAVIORAL
                ))
                
                detection.analysis_results["behavioral"] = {
                    "anomaly_score": anomaly_score,
                    "threshold": profile.anomaly_threshold,
                    "baseline_behavior": profile.normal_behavior,
                    "current_behavior": current_behavior
                }
            
            logger.debug(f"Behavioral analysis completed: anomaly_score={anomaly_score:.2f}")
        
        except Exception as e:
            logger.error(f"Behavioral analysis failed: {e}")
            detection.analysis_results["behavioral_error"] = str(e)
    
    async def _threat_intel_analysis(self, file_hash: str, detection: ThreatDetection):
        """Perform threat intelligence analysis."""
        try:
            logger.debug(f"Starting threat intel analysis for hash {file_hash}")
            
            matches = []
            
            # Check against threat intelligence sources
            for source_name, intel_data in self._threat_intel_cache.items():
                if file_hash in intel_data.get("hashes", {}):
                    match_info = intel_data["hashes"][file_hash]
                    matches.append({
                        "source": source_name,
                        "threat_type": match_info.get("threat_type", "unknown"),
                        "family": match_info.get("family"),
                        "first_seen": match_info.get("first_seen"),
                        "confidence": 0.9  # High confidence for intel matches
                    })
            
            # Update detection with intel matches
            if matches:
                for match in matches:
                    detection.indicators.append(ThreatIndicator(
                        indicator_type="threat_intel_hash",
                        value=file_hash,
                        confidence=match["confidence"],
                        source=ThreatSource.THREAT_INTELLIGENCE
                    ))
                
                detection.threat_intel_matches = matches
                detection.analysis_results["threat_intel"] = {
                    "matches": matches,
                    "sources_checked": list(self._threat_intel_cache.keys())
                }
                
                # Update threat classification
                if matches[0]["threat_type"] != "unknown":
                    threat_type_map = {
                        "malware": ThreatType.MALWARE,
                        "virus": ThreatType.VIRUS,
                        "trojan": ThreatType.TROJAN,
                        "ransomware": ThreatType.RANSOMWARE,
                        "rootkit": ThreatType.ROOTKIT,
                        "spyware": ThreatType.SPYWARE,
                        "adware": ThreatType.ADWARE,
                    }
                    
                    detected_type = threat_type_map.get(
                        matches[0]["threat_type"].lower(),
                        ThreatType.MALWARE
                    )
                    
                    detection.threat_type = detected_type
                
                # Set family and campaign info
                if matches[0].get("family"):
                    detection.family = matches[0]["family"]
            
            logger.debug(f"Threat intel analysis completed: {len(matches)} matches found")
        
        except Exception as e:
            logger.error(f"Threat intel analysis failed: {e}")
            detection.analysis_results["threat_intel_error"] = str(e)
    
    async def _incorporate_validation_results(self, validation_result: ValidationResult, detection: ThreatDetection):
        """Incorporate file validation results into threat detection."""
        try:
            # Convert validation issues to threat indicators
            for issue in validation_result.issues:
                severity_to_confidence = {
                    SecurityRisk.LOW: 0.3,
                    SecurityRisk.MEDIUM: 0.5,
                    SecurityRisk.HIGH: 0.7,
                    SecurityRisk.CRITICAL: 0.9
                }
                
                detection.indicators.append(ThreatIndicator(
                    indicator_type="validation_issue",
                    value=issue.code,
                    confidence=severity_to_confidence[issue.severity],
                    source=ThreatSource.HEURISTIC
                ))
            
            # Update risk based on security score
            if validation_result.security_score < 0.3:
                detection.analysis_results["validation_risk"] = "high"
            elif validation_result.security_score < 0.7:
                detection.analysis_results["validation_risk"] = "medium"
            else:
                detection.analysis_results["validation_risk"] = "low"
            
            detection.analysis_results["validation"] = {
                "security_score": validation_result.security_score,
                "issues_count": len(validation_result.issues),
                "status": validation_result.status.value
            }
        
        except Exception as e:
            logger.error(f"Failed to incorporate validation results: {e}")
    
    async def _calculate_final_scores(self, detection: ThreatDetection) -> ThreatDetection:
        """Calculate final confidence and risk scores."""
        try:
            # Calculate confidence based on indicators
            if detection.indicators:
                # Weighted average of indicator confidences
                total_weight = 0
                weighted_confidence = 0
                
                source_weights = {
                    ThreatSource.THREAT_INTELLIGENCE: 0.9,
                    ThreatSource.MACHINE_LEARNING: 0.8,
                    ThreatSource.SIGNATURE: 0.8,
                    ThreatSource.HEURISTIC: 0.6,
                    ThreatSource.BEHAVIORAL: 0.5,
                    ThreatSource.SANDBOX: 0.7,
                    ThreatSource.USER_REPORT: 0.3
                }
                
                for indicator in detection.indicators:
                    weight = source_weights.get(indicator.source, 0.5)
                    weighted_confidence += indicator.confidence * weight
                    total_weight += weight
                
                if total_weight > 0:
                    detection.confidence = min(1.0, weighted_confidence / total_weight)
            
            # Calculate risk score
            base_risk = detection.confidence
            
            # Amplify risk based on threat type
            threat_multipliers = {
                ThreatType.RANSOMWARE: 1.3,
                ThreatType.ROOTKIT: 1.2,
                ThreatType.TROJAN: 1.1,
                ThreatType.VIRUS: 1.1,
                ThreatType.MALWARE: 1.0,
                ThreatType.SPYWARE: 0.9,
                ThreatType.ADWARE: 0.7,
                ThreatType.SUSPICIOUS_BEHAVIOR: 0.6,
                ThreatType.UNKNOWN: 0.5
            }
            
            multiplier = threat_multipliers.get(detection.threat_type, 1.0)
            detection.risk_score = min(1.0, base_risk * multiplier)
            
            # Determine severity based on risk score
            if detection.risk_score >= self.config.high_risk_threshold:
                detection.severity = ThreatSeverity.CRITICAL
            elif detection.risk_score >= self.config.medium_risk_threshold:
                detection.severity = ThreatSeverity.HIGH
            elif detection.risk_score >= self.config.low_risk_threshold:
                detection.severity = ThreatSeverity.MEDIUM
            else:
                detection.severity = ThreatSeverity.LOW
            
        except Exception as e:
            logger.error(f"Failed to calculate final scores: {e}")
            detection.confidence = 0.1
            detection.risk_score = 0.1
            detection.severity = ThreatSeverity.LOW
        
        return detection
    
    def _determine_response_actions(self, detection: ThreatDetection) -> List[ResponseAction]:
        """Determine recommended response actions."""
        actions = []
        
        # Always log detections
        actions.append(ResponseAction.LOG)
        
        # Actions based on severity
        if detection.severity == ThreatSeverity.CRITICAL:
            actions.extend([
                ResponseAction.QUARANTINE,
                ResponseAction.BLOCK,
                ResponseAction.NOTIFY_ADMIN,
                ResponseAction.ALERT
            ])
        elif detection.severity == ThreatSeverity.HIGH:
            actions.extend([
                ResponseAction.QUARANTINE,
                ResponseAction.ALERT,
                ResponseAction.NOTIFY_ADMIN
            ])
        elif detection.severity == ThreatSeverity.MEDIUM:
            actions.extend([
                ResponseAction.ALERT
            ])
        
        # Specific actions for threat types
        if detection.threat_type == ThreatType.RANSOMWARE:
            actions.extend([
                ResponseAction.ISOLATE_USER,
                ResponseAction.SCAN_SYSTEM
            ])
        elif detection.threat_type == ThreatType.ROOTKIT:
            actions.append(ResponseAction.SCAN_SYSTEM)
        
        return list(set(actions))  # Remove duplicates
    
    def _should_auto_respond(self, detection: ThreatDetection) -> bool:
        """Determine if automated response should be triggered."""
        if detection.severity == ThreatSeverity.CRITICAL and self.config.auto_quarantine_critical:
            return True
        elif detection.severity == ThreatSeverity.HIGH and self.config.auto_quarantine_high:
            return True
        
        return False
    
    async def _execute_automated_response(self, detection: ThreatDetection) -> List[ResponseAction]:
        """Execute automated response actions."""
        executed_actions = []
        
        try:
            for action in detection.recommended_actions:
                if action == ResponseAction.QUARANTINE:
                    # This would integrate with QuarantineManager
                    logger.info(f"Auto-quarantining file: {detection.file_path}")
                    executed_actions.append(action)
                
                elif action == ResponseAction.ALERT:
                    await self._send_threat_alert(detection)
                    executed_actions.append(action)
                
                elif action == ResponseAction.NOTIFY_ADMIN:
                    await self._notify_admin(detection)
                    executed_actions.append(action)
                
                elif action == ResponseAction.LOG:
                    # Already logged in main flow
                    executed_actions.append(action)
        
        except Exception as e:
            logger.error(f"Failed to execute automated response: {e}")
        
        return executed_actions
    
    async def _send_threat_alert(self, detection: ThreatDetection):
        """Send threat alert."""
        # This would integrate with your alerting system
        logger.critical(f"THREAT ALERT: {detection.threat_type} detected - Risk: {detection.risk_score:.2f}")
    
    async def _notify_admin(self, detection: ThreatDetection):
        """Notify administrators of threat."""
        # This would integrate with your notification system
        logger.warning(f"Admin notification: {detection.threat_type} - {detection.file_path}")
    
    async def _log_detection(self, detection: ThreatDetection):
        """Log threat detection event."""
        if self.audit_logger:
            await self.audit_logger.log_event(
                event_type=AuditEventType.THREAT_DETECTED,
                level=AuditLevel.CRITICAL if detection.severity == ThreatSeverity.CRITICAL else AuditLevel.WARNING,
                details={
                    "detection_id": detection.detection_id,
                    "threat_type": detection.threat_type.value,
                    "severity": detection.severity.value,
                    "confidence": detection.confidence,
                    "risk_score": detection.risk_score,
                    "indicators_count": len(detection.indicators),
                    "source": detection.source.value
                },
                user_id=detection.user_id,
                session_id=detection.session_id,
                file_path=detection.file_path,
                file_hash=detection.file_hash,
                risk_score=detection.risk_score
            )
    
    def _load_heuristic_rules(self) -> List[Dict]:
        """Load heuristic detection rules."""
        # In production, load from configuration files
        return [
            {
                "name": "suspicious_entropy",
                "description": "High entropy content indicating encryption/packing",
                "pattern": None,
                "function": self._check_entropy
            },
            {
                "name": "executable_headers",
                "description": "Executable file headers in non-executable files",
                "pattern": rb"MZ\x90\x00",
                "function": None
            },
            {
                "name": "suspicious_strings",
                "description": "Suspicious string patterns",
                "pattern": None,
                "function": self._check_suspicious_strings
            },
            {
                "name": "macro_indicators",
                "description": "VBA/macro indicators",
                "pattern": rb"vbaProject",
                "function": None
            },
            {
                "name": "javascript_in_pdf",
                "description": "JavaScript in PDF files",
                "pattern": rb"/JavaScript",
                "function": None
            }
        ]
    
    async def _apply_heuristic_rule(self, rule: Dict, content: bytes, file_path: Path) -> float:
        """Apply individual heuristic rule."""
        try:
            if rule.get("function"):
                return await rule["function"](content, file_path)
            elif rule.get("pattern"):
                if rule["pattern"] in content:
                    return 0.7  # Base score for pattern match
            
            return 0.0
        
        except Exception as e:
            logger.error(f"Heuristic rule application failed: {e}")
            return 0.0
    
    async def _check_entropy(self, content: bytes, file_path: Path) -> float:
        """Check content entropy."""
        if not content:
            return 0.0
        
        # Calculate Shannon entropy
        byte_counts = [0] * 256
        for byte in content:
            byte_counts[byte] += 1
        
        entropy = 0.0
        length = len(content)
        
        for count in byte_counts:
            if count > 0:
                p = count / length
                entropy -= p * np.log2(p)
        
        # High entropy (>7.5) might indicate packing/encryption
        if entropy > 7.5:
            return min(1.0, (entropy - 7.5) * 2)
        
        return 0.0
    
    async def _check_suspicious_strings(self, content: bytes, file_path: Path) -> float:
        """Check for suspicious string patterns."""
        try:
            text_content = content.decode('utf-8', errors='ignore').lower()
            
            suspicious_strings = [
                'eval(', 'exec(', 'system(', 'shell_exec', 'cmd.exe',
                'powershell', 'base64_decode', 'gzinflate', 'str_rot13',
                'createobject', 'wscript.shell', 'microsoft.xmlhttp'
            ]
            
            matches = sum(1 for s in suspicious_strings if s in text_content)
            
            if matches > 0:
                return min(1.0, matches * 0.2)
            
            return 0.0
        
        except Exception:
            return 0.0
    
    async def _extract_ml_features(self, file_path: Path) -> Optional[List[float]]:
        """Extract features for ML analysis."""
        try:
            features = []
            
            # File size features
            file_size = file_path.stat().st_size
            features.append(float(file_size))
            features.append(float(np.log10(max(1, file_size))))
            
            # Read file content
            max_read = min(64 * 1024, file_size)  # Max 64KB
            
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read(max_read)
            
            if not content:
                return None
            
            # Entropy
            features.append(self._calculate_entropy_simple(content))
            
            # Byte histogram features (first 16 bytes)
            byte_hist = [0] * 16
            for byte in content[:1000]:  # First 1000 bytes
                byte_hist[byte % 16] += 1
            
            # Normalize
            total = sum(byte_hist)
            if total > 0:
                features.extend([count / total for count in byte_hist])
            else:
                features.extend([0.0] * 16)
            
            # Binary/text ratio
            printable_count = sum(1 for byte in content if 32 <= byte <= 126)
            features.append(printable_count / len(content))
            
            # Null byte ratio
            null_count = content.count(b'\x00')
            features.append(null_count / len(content))
            
            return features
        
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None
    
    def _calculate_entropy_simple(self, data: bytes) -> float:
        """Calculate simple entropy."""
        if not data:
            return 0.0
        
        counts = [0] * 256
        for byte in data:
            counts[byte] += 1
        
        entropy = 0.0
        length = len(data)
        
        for count in counts:
            if count > 0:
                p = count / length
                entropy -= p * np.log2(p)
        
        return entropy / 8.0  # Normalize to 0-1
    
    def _calculate_behavior_anomaly(self, current: Dict, baseline: Dict) -> float:
        """Calculate behavioral anomaly score."""
        try:
            anomaly_score = 0.0
            
            # Time-based anomaly
            if "upload_hours" in baseline:
                current_hour = current.get("upload_time", 12)
                normal_hours = baseline["upload_hours"]
                
                if current_hour not in normal_hours:
                    anomaly_score += 0.3
            
            # File type anomaly
            if "file_types" in baseline:
                current_type = current.get("file_type", "")
                normal_types = baseline["file_types"]
                
                if current_type and current_type not in normal_types:
                    anomaly_score += 0.4
            
            # File size anomaly
            if "avg_file_size" in baseline:
                current_size = current.get("file_size", 0)
                avg_size = baseline["avg_file_size"]
                std_size = baseline.get("std_file_size", avg_size * 0.5)
                
                if abs(current_size - avg_size) > 2 * std_size:
                    anomaly_score += 0.3
            
            return min(1.0, anomaly_score)
        
        except Exception as e:
            logger.error(f"Behavior anomaly calculation failed: {e}")
            return 0.0
    
    async def _update_behavior_profile(self, profile: ThreatProfile, current_behavior: Dict):
        """Update behavioral baseline for user."""
        try:
            if not profile.normal_behavior:
                profile.normal_behavior = {
                    "upload_hours": set(),
                    "file_types": set(),
                    "file_sizes": [],
                    "avg_file_size": 0,
                    "std_file_size": 0
                }
            
            # Update upload hours
            current_hour = current_behavior.get("upload_time")
            if current_hour is not None:
                if isinstance(profile.normal_behavior["upload_hours"], set):
                    profile.normal_behavior["upload_hours"].add(current_hour)
                else:
                    profile.normal_behavior["upload_hours"] = {current_hour}
            
            # Update file types
            current_type = current_behavior.get("file_type")
            if current_type:
                if isinstance(profile.normal_behavior["file_types"], set):
                    profile.normal_behavior["file_types"].add(current_type)
                else:
                    profile.normal_behavior["file_types"] = {current_type}
            
            # Update file sizes
            current_size = current_behavior.get("file_size", 0)
            if current_size > 0:
                file_sizes = profile.normal_behavior.get("file_sizes", [])
                file_sizes.append(current_size)
                
                # Keep only recent sizes (last 100)
                if len(file_sizes) > 100:
                    file_sizes = file_sizes[-100:]
                
                profile.normal_behavior["file_sizes"] = file_sizes
                profile.normal_behavior["avg_file_size"] = sum(file_sizes) / len(file_sizes)
                
                if len(file_sizes) > 1:
                    variance = sum((x - profile.normal_behavior["avg_file_size"]) ** 2 for x in file_sizes) / len(file_sizes)
                    profile.normal_behavior["std_file_size"] = variance ** 0.5
            
            # Update risk history
            profile.risk_history.append((datetime.utcnow(), profile.current_risk))
            
            # Keep only recent history (last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            profile.risk_history = [
                (date, risk) for date, risk in profile.risk_history
                if date > cutoff_date
            ]
            
            profile.last_updated = datetime.utcnow()
            
            # Save updated profile
            await self._save_threat_profile(profile)
        
        except Exception as e:
            logger.error(f"Failed to update behavior profile: {e}")
    
    async def _save_threat_profile(self, profile: ThreatProfile):
        """Save threat profile to storage."""
        try:
            if self.redis_client:
                # Convert sets to lists for JSON serialization
                profile_data = profile.dict()
                
                if "normal_behavior" in profile_data:
                    for key, value in profile_data["normal_behavior"].items():
                        if isinstance(value, set):
                            profile_data["normal_behavior"][key] = list(value)
                
                await self.redis_client.setex(
                    f"threat_profile:{profile.profile_id}",
                    86400 * 30,  # 30 days TTL
                    json.dumps(profile_data, default=str)
                )
        
        except Exception as e:
            logger.error(f"Failed to save threat profile: {e}")
    
    async def _get_cached_detection(self, file_hash: str) -> Optional[ThreatDetection]:
        """Get cached threat detection result."""
        if not self.config.cache_results or not self.redis_client:
            return None
        
        try:
            data = await self.redis_client.get(f"threat_detection:{file_hash}")
            if data:
                detection_data = json.loads(data)
                
                # Convert datetime strings back
                if "detection_time" in detection_data:
                    detection_data["detection_time"] = datetime.fromisoformat(detection_data["detection_time"])
                
                return ThreatDetection(**detection_data)
        
        except Exception as e:
            logger.error(f"Failed to get cached detection: {e}")
        
        return None
    
    async def _cache_detection(self, file_hash: str, detection: ThreatDetection):
        """Cache threat detection result."""
        if not self.config.cache_results or not self.redis_client:
            return
        
        try:
            detection_data = detection.dict()
            
            await self.redis_client.setex(
                f"threat_detection:{file_hash}",
                self.config.cache_ttl,
                json.dumps(detection_data, default=str)
            )
        
        except Exception as e:
            logger.error(f"Failed to cache detection: {e}")
    
    async def _update_abuse_ch_intel(self) -> int:
        """Update threat intelligence from abuse.ch."""
        try:
            # This would fetch from abuse.ch APIs
            # For now, return mock count
            return 100
        except Exception as e:
            logger.error(f"Failed to update abuse.ch intel: {e}")
            return 0
    
    async def _update_malware_bazaar_intel(self) -> int:
        """Update threat intelligence from MalwareBazaar."""
        try:
            # This would fetch from MalwareBazaar APIs
            return 50
        except Exception as e:
            logger.error(f"Failed to update MalwareBazaar intel: {e}")
            return 0
    
    async def _update_urlhaus_intel(self) -> int:
        """Update threat intelligence from URLhaus."""
        try:
            # This would fetch from URLhaus APIs
            return 25
        except Exception as e:
            logger.error(f"Failed to update URLhaus intel: {e}")
            return 0
    
    async def _initialize_ml_models(self):
        """Initialize machine learning models."""
        try:
            # In production, load pre-trained models
            # For now, create simple models
            
            # Simple isolation forest for anomaly detection
            self._ml_models["anomaly_detector"] = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            
            # TF-IDF vectorizer for text analysis
            self._vectorizers["text_analyzer"] = TfidfVectorizer(
                max_features=1000,
                stop_words='english'
            )
            
            # Standard scaler for numerical features
            self._scalers["feature_scaler"] = StandardScaler()
            
            logger.info("ML models initialized")
        
        except Exception as e:
            logger.error(f"Failed to initialize ML models: {e}")
    
    async def _start_background_tasks(self):
        """Start background tasks."""
        try:
            # Update threat intelligence periodically
            async def update_intel_task():
                while True:
                    try:
                        await asyncio.sleep(self.config.intel_update_interval)
                        await self.update_threat_intelligence()
                    except Exception as e:
                        logger.error(f"Intel update task failed: {e}")
            
            asyncio.create_task(update_intel_task())
            
            logger.info("Background tasks started")
        
        except Exception as e:
            logger.error(f"Failed to start background tasks: {e}")
    
    def _generate_detection_id(self) -> str:
        """Generate unique detection ID."""
        from uuid import uuid4
        return f"det_{uuid4().hex[:12]}_{int(datetime.utcnow().timestamp())}"