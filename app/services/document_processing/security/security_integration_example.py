"""
Comprehensive security integration example.

Demonstrates how to integrate all security components for complete
document processing security coverage.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

from app.infrastructure.cache.redis import RedisClient
from .virus_scanner import VirusScanner, ScannerConfig
from .file_validator import FileValidator, FileValidatorConfig, ValidationStatus
from .quarantine_manager import QuarantineManager, QuarantineConfig, QuarantineReason
from .sanitizer import FileSanitizer, SanitizerConfig, SanitizationLevel
from .audit_logger import SecurityAuditLogger, AuditLoggerConfig, AuditEventType
from .threat_detector import ThreatDetector, ThreatDetectorConfig, ThreatSeverity

logger = logging.getLogger(__name__)


class SecurityPipeline:
    """
    Comprehensive security pipeline for document processing.
    
    Integrates all security components for complete protection.
    """
    
    def __init__(
        self,
        virus_scanner_config: Optional[ScannerConfig] = None,
        validator_config: Optional[FileValidatorConfig] = None,
        quarantine_config: Optional[QuarantineConfig] = None,
        sanitizer_config: Optional[SanitizerConfig] = None,
        audit_config: Optional[AuditLoggerConfig] = None,
        threat_detector_config: Optional[ThreatDetectorConfig] = None,
        redis_client: Optional[RedisClient] = None
    ):
        """Initialize security pipeline."""
        
        # Initialize audit logger first (used by other components)
        self.audit_logger = SecurityAuditLogger(
            config=audit_config,
            redis_client=redis_client
        )
        
        # Initialize components
        self.virus_scanner = VirusScanner(
            config=virus_scanner_config,
            redis_client=redis_client
        )
        
        self.file_validator = FileValidator(
            config=validator_config
        )
        
        self.quarantine_manager = QuarantineManager(
            config=quarantine_config,
            redis_client=redis_client,
            audit_logger=self.audit_logger
        )
        
        self.sanitizer = FileSanitizer(
            config=sanitizer_config
        )
        
        self.threat_detector = ThreatDetector(
            config=threat_detector_config,
            redis_client=redis_client,
            audit_logger=self.audit_logger
        )
        
        logger.info("Security pipeline initialized")
    
    async def process_file_upload(
        self,
        file_path: str,
        user_id: str,
        session_id: str,
        sanitize: bool = True,
        sanitization_level: SanitizationLevel = SanitizationLevel.STANDARD
    ) -> Dict:
        """
        Process uploaded file through complete security pipeline.
        
        Args:
            file_path: Path to uploaded file
            user_id: User identifier
            session_id: Session identifier
            sanitize: Whether to sanitize the file
            sanitization_level: Level of sanitization to apply
            
        Returns:
            Dict: Processing results
        """
        file_path = Path(file_path)
        results = {
            "file_path": str(file_path),
            "user_id": user_id,
            "session_id": session_id,
            "processing_steps": [],
            "security_status": "processing",
            "final_action": "unknown"
        }
        
        try:
            # Step 1: File Validation
            logger.info(f"Starting security processing for {file_path}")
            
            await self.audit_logger.log_file_operation(
                operation="upload",
                file_path=str(file_path),
                file_hash="",  # Will be calculated
                user_id=user_id,
                session_id=session_id
            )
            
            validation_result = await self.file_validator.validate_file(file_path)
            results["validation"] = {
                "status": validation_result.status.value,
                "security_score": validation_result.security_score,
                "issues_count": len(validation_result.issues),
                "file_type": validation_result.detected_type.value
            }
            results["processing_steps"].append("validation")
            
            # Check if file should be rejected immediately
            if validation_result.status == ValidationStatus.INVALID:
                await self._handle_invalid_file(file_path, validation_result, user_id, session_id)
                results["security_status"] = "rejected"
                results["final_action"] = "blocked"
                return results
            
            # Step 2: Virus Scanning
            scan_result = await self.virus_scanner.scan_file(file_path)
            results["virus_scan"] = {
                "status": scan_result.status.value,
                "threats_found": len(scan_result.threats),
                "confidence": scan_result.confidence_score,
                "engines_used": scan_result.engine_count
            }
            results["processing_steps"].append("virus_scan")
            
            # Handle infected files
            if scan_result.status.value in ["infected", "suspicious"]:
                quarantine_record = await self._handle_infected_file(
                    file_path, scan_result, user_id, session_id
                )
                results["quarantine_id"] = quarantine_record.quarantine_id
                results["security_status"] = "quarantined"
                results["final_action"] = "quarantined"
                return results
            
            # Step 3: Threat Detection
            threat_detection = await self.threat_detector.analyze_file(
                file_path=file_path,
                file_hash=validation_result.file_hash,
                validation_result=validation_result,
                user_id=user_id,
                session_id=session_id
            )
            results["threat_detection"] = {
                "threat_type": threat_detection.threat_type.value,
                "severity": threat_detection.severity.value,
                "confidence": threat_detection.confidence,
                "risk_score": threat_detection.risk_score,
                "indicators_count": len(threat_detection.indicators)
            }
            results["processing_steps"].append("threat_detection")
            
            # Handle high-risk threats
            if threat_detection.severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]:
                quarantine_record = await self._handle_threat_detection(
                    file_path, threat_detection, user_id, session_id
                )
                results["quarantine_id"] = quarantine_record.quarantine_id
                results["security_status"] = "quarantined"
                results["final_action"] = "quarantined"
                return results
            
            # Step 4: File Sanitization (if requested and safe)
            if sanitize and validation_result.status == ValidationStatus.VALID:
                sanitized_path = file_path.with_suffix(f".sanitized{file_path.suffix}")
                
                sanitization_result = await self.sanitizer.sanitize_file(
                    file_path=file_path,
                    output_path=sanitized_path,
                    level=sanitization_level
                )
                
                results["sanitization"] = {
                    "success": sanitization_result.success,
                    "actions_performed": [a.value for a in sanitization_result.actions_performed],
                    "issues_resolved": len(sanitization_result.issues_found),
                    "warnings": sanitization_result.warnings
                }
                results["processing_steps"].append("sanitization")
                
                # Use sanitized version if successful
                if sanitization_result.success:
                    results["final_file_path"] = str(sanitized_path)
                    results["original_file_path"] = str(file_path)
                else:
                    results["final_file_path"] = str(file_path)
            else:
                results["final_file_path"] = str(file_path)
            
            # Final security assessment
            results["security_status"] = self._determine_final_security_status(
                validation_result, scan_result, threat_detection
            )
            results["final_action"] = "approved" if results["security_status"] == "safe" else "review"
            
            # Log completion
            await self.audit_logger.log_event(
                event_type=AuditEventType.FILE_UPLOADED,
                details={
                    "processing_steps": results["processing_steps"],
                    "security_status": results["security_status"],
                    "final_action": results["final_action"]
                },
                user_id=user_id,
                session_id=session_id,
                file_path=str(file_path),
                file_hash=validation_result.file_hash
            )
            
            logger.info(f"Security processing completed: {results['security_status']}")
            
        except Exception as e:
            logger.error(f"Security processing failed: {e}")
            results["error"] = str(e)
            results["security_status"] = "error"
            results["final_action"] = "blocked"
            
            await self.audit_logger.log_event(
                event_type=AuditEventType.SERVICE_ERROR,
                details={"error": str(e), "step": "security_processing"},
                user_id=user_id,
                session_id=session_id,
                file_path=str(file_path),
                outcome="failure",
                error_message=str(e)
            )
        
        return results
    
    async def _handle_invalid_file(
        self,
        file_path: Path,
        validation_result,
        user_id: str,
        session_id: str
    ):
        """Handle invalid file."""
        logger.warning(f"File validation failed: {file_path}")
        
        # Quarantine invalid file
        await self.quarantine_manager.quarantine_file(
            file_path=file_path,
            reason=QuarantineReason.VALIDATION_FAILED,
            detection_details={
                "validation_issues": [issue.dict() for issue in validation_result.issues],
                "security_score": validation_result.security_score
            },
            user_id=user_id,
            session_id=session_id
        )
        
        await self.audit_logger.log_event(
            event_type=AuditEventType.POLICY_VIOLATION,
            details={
                "reason": "file_validation_failed",
                "issues_count": len(validation_result.issues),
                "security_score": validation_result.security_score
            },
            user_id=user_id,
            session_id=session_id,
            file_path=str(file_path),
            file_hash=validation_result.file_hash
        )
    
    async def _handle_infected_file(
        self,
        file_path: Path,
        scan_result,
        user_id: str,
        session_id: str
    ):
        """Handle infected file."""
        logger.warning(f"Virus detected in file: {file_path}")
        
        # Quarantine infected file
        quarantine_record = await self.quarantine_manager.quarantine_file(
            file_path=file_path,
            reason=QuarantineReason.VIRUS_DETECTED,
            detection_details={
                "scan_result": scan_result.dict(),
                "threats": scan_result.threats,
                "engines_detected": scan_result.detection_count
            },
            threat_info={
                "threat_count": len(scan_result.threats),
                "confidence": scan_result.confidence_score
            },
            user_id=user_id,
            session_id=session_id
        )
        
        await self.audit_logger.log_event(
            event_type=AuditEventType.VIRUS_FOUND,
            details={
                "threats": scan_result.threats,
                "engines_detected": scan_result.detection_count,
                "confidence": scan_result.confidence_score,
                "quarantine_id": quarantine_record.quarantine_id
            },
            user_id=user_id,
            session_id=session_id,
            file_path=str(file_path),
            file_hash=scan_result.file_hash,
            risk_score=min(1.0, scan_result.confidence_score + 0.2)
        )
        
        return quarantine_record
    
    async def _handle_threat_detection(
        self,
        file_path: Path,
        threat_detection,
        user_id: str,
        session_id: str
    ):
        """Handle detected threat."""
        logger.warning(f"Threat detected in file: {file_path} - {threat_detection.threat_type}")
        
        # Quarantine threatening file
        quarantine_record = await self.quarantine_manager.quarantine_file(
            file_path=file_path,
            reason=QuarantineReason.SUSPICIOUS_CONTENT,
            detection_details={
                "threat_detection": threat_detection.dict(),
                "indicators": [ind.dict() for ind in threat_detection.indicators]
            },
            threat_info={
                "threat_type": threat_detection.threat_type.value,
                "severity": threat_detection.severity.value,
                "confidence": threat_detection.confidence,
                "risk_score": threat_detection.risk_score
            },
            user_id=user_id,
            session_id=session_id
        )
        
        return quarantine_record
    
    def _determine_final_security_status(
        self,
        validation_result,
        scan_result,
        threat_detection
    ) -> str:
        """Determine final security status."""
        # Check for any critical issues
        if validation_result.status == ValidationStatus.INVALID:
            return "blocked"
        
        if scan_result.status.value in ["infected", "suspicious"]:
            return "infected"
        
        if threat_detection.severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]:
            return "dangerous"
        
        # Check for medium-level concerns
        if (validation_result.security_score < 0.7 or 
            threat_detection.severity == ThreatSeverity.MEDIUM):
            return "suspicious"
        
        return "safe"
    
    async def get_security_dashboard(self) -> Dict:
        """Get security dashboard statistics."""
        try:
            # Get quarantine statistics
            quarantine_stats = await self.quarantine_manager.get_quarantine_stats()
            
            # Get audit statistics
            audit_stats = await self.audit_logger.get_event_statistics()
            
            # Get virus scanner engine status
            scanner_status = await self.virus_scanner.get_engine_status()
            
            return {
                "quarantine": quarantine_stats,
                "audit": audit_stats,
                "scanner_engines": scanner_status,
                "pipeline_status": "operational"
            }
        
        except Exception as e:
            logger.error(f"Failed to get security dashboard: {e}")
            return {"error": str(e)}
    
    async def cleanup_expired_data(self) -> Dict:
        """Clean up expired security data."""
        try:
            # Clean up expired quarantine files
            quarantine_cleaned = await self.quarantine_manager.cleanup_expired_files()
            
            logger.info(f"Security cleanup completed: {quarantine_cleaned} quarantine files cleaned")
            
            return {
                "quarantine_files_cleaned": quarantine_cleaned,
                "cleanup_status": "completed"
            }
        
        except Exception as e:
            logger.error(f"Security cleanup failed: {e}")
            return {"error": str(e)}


# Example usage and testing functions

async def example_secure_file_processing():
    """Example of secure file processing."""
    
    # Initialize Redis client (optional)
    redis_client = None  # RedisClient() in production
    
    # Initialize security pipeline
    pipeline = SecurityPipeline(redis_client=redis_client)
    
    # Example file upload processing
    test_file_path = "/tmp/test_document.pdf"
    
    # Process file through security pipeline
    results = await pipeline.process_file_upload(
        file_path=test_file_path,
        user_id="user123",
        session_id="session456",
        sanitize=True,
        sanitization_level=SanitizationLevel.STANDARD
    )
    
    print("Security Processing Results:")
    print(f"Status: {results['security_status']}")
    print(f"Action: {results['final_action']}")
    print(f"Steps: {results['processing_steps']}")
    
    if results['security_status'] == 'quarantined':
        print(f"Quarantine ID: {results.get('quarantine_id')}")
    elif results['security_status'] == 'safe':
        print(f"Safe file: {results['final_file_path']}")


async def example_threat_intelligence_update():
    """Example of updating threat intelligence."""
    
    pipeline = SecurityPipeline()
    
    # Update threat intelligence
    intel_results = await pipeline.threat_detector.update_threat_intelligence()
    
    print("Threat Intelligence Update:")
    for source, count in intel_results.items():
        print(f"{source}: {count} indicators updated")


async def example_security_dashboard():
    """Example of security dashboard."""
    
    pipeline = SecurityPipeline()
    
    # Get dashboard data
    dashboard = await pipeline.get_security_dashboard()
    
    print("Security Dashboard:")
    print(f"Quarantine files: {dashboard.get('quarantine', {}).get('total_files', 0)}")
    print(f"Recent audit events: {dashboard.get('audit', {}).get('total_events', 0)}")
    print(f"Scanner engines: {len(dashboard.get('scanner_engines', {}))}")


async def example_compliance_export():
    """Example of compliance data export."""
    
    pipeline = SecurityPipeline()
    
    from datetime import datetime, timedelta
    
    # Export last 30 days of audit data
    start_time = datetime.utcnow() - timedelta(days=30)
    end_time = datetime.utcnow()
    
    export_path = await pipeline.audit_logger.export_audit_log(
        start_time=start_time,
        end_time=end_time,
        format_type="json"
    )
    
    print(f"Compliance export saved to: {export_path}")


if __name__ == "__main__":
    # Run examples
    asyncio.run(example_secure_file_processing())
    asyncio.run(example_threat_intelligence_update())
    asyncio.run(example_security_dashboard())
    asyncio.run(example_compliance_export())