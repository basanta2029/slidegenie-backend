"""
Account lockout service for SlideGenie authentication system.

Provides comprehensive account security features:
- Failed login attempt tracking
- Progressive lockout durations
- Brute force protection
- Account suspension mechanisms
- Lockout recovery
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.cache.redis import RedisCache, get_redis

logger = get_logger(__name__)


class LockoutReason(str, Enum):
    """Reasons for account lockout."""
    FAILED_LOGIN_ATTEMPTS = "failed_login_attempts"
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ADMINISTRATIVE_LOCK = "administrative_lock"
    PASSWORD_RESET_ABUSE = "password_reset_abuse"


class LockoutSeverity(str, Enum):
    """Lockout severity levels."""
    LOW = "low"           # Short lockout (5-15 minutes)
    MEDIUM = "medium"     # Medium lockout (30-60 minutes)
    HIGH = "high"         # Long lockout (2-24 hours)
    CRITICAL = "critical" # Indefinite lockout (manual review required)


class AccountLockoutInfo:
    """Information about account lockout status."""
    
    def __init__(
        self,
        is_locked: bool,
        failed_attempts: int,
        lockout_until: Optional[datetime] = None,
        reason: Optional[LockoutReason] = None,
        severity: Optional[LockoutSeverity] = None,
        remaining_attempts: Optional[int] = None,
    ):
        self.is_locked = is_locked
        self.failed_attempts = failed_attempts
        self.lockout_until = lockout_until
        self.reason = reason
        self.severity = severity
        self.remaining_attempts = remaining_attempts
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        return {
            "is_locked": self.is_locked,
            "failed_attempts": self.failed_attempts,
            "lockout_until": self.lockout_until.isoformat() if self.lockout_until else None,
            "reason": self.reason.value if self.reason else None,
            "severity": self.severity.value if self.severity else None,
            "remaining_attempts": self.remaining_attempts,
        }


class AccountLockoutService:
    """
    Service for managing account lockouts and failed login attempts.
    
    Features:
    - Progressive lockout durations
    - Different lockout reasons and severities
    - IP-based and account-based tracking
    - Automatic lockout recovery
    - Brute force detection
    """
    
    def __init__(
        self,
        cache: Optional[RedisCache] = None,
        max_attempts: int = 5,
        lockout_duration_minutes: int = 30,
        progressive_lockout: bool = True,
    ):
        """
        Initialize account lockout service.
        
        Args:
            cache: Redis cache instance
            max_attempts: Maximum failed attempts before lockout
            lockout_duration_minutes: Base lockout duration
            progressive_lockout: Enable progressive lockout durations
        """
        self.cache = cache or RedisCache(prefix="lockout")
        self.max_attempts = max_attempts
        self.base_lockout_duration = lockout_duration_minutes
        self.progressive_lockout = progressive_lockout
        
        # Progressive lockout durations (in minutes)
        self.lockout_durations = {
            1: 5,      # First lockout: 5 minutes
            2: 15,     # Second lockout: 15 minutes
            3: 30,     # Third lockout: 30 minutes
            4: 60,     # Fourth lockout: 1 hour
            5: 120,    # Fifth lockout: 2 hours
            6: 360,    # Sixth lockout: 6 hours
            7: 720,    # Seventh lockout: 12 hours
            8: 1440,   # Eighth lockout: 24 hours
        }
        
        # Brute force detection thresholds
        self.brute_force_thresholds = {
            "attempts_per_minute": 10,
            "attempts_per_hour": 50,
            "unique_accounts_per_ip": 5,
        }
    
    async def record_failed_attempt(
        self,
        identifier: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_context: Optional[Dict] = None,
    ) -> AccountLockoutInfo:
        """
        Record a failed login attempt and check for lockout.
        
        Args:
            identifier: Account identifier (email or user ID)
            ip_address: Client IP address
            user_agent: Client user agent
            additional_context: Additional context information
            
        Returns:
            AccountLockoutInfo with current status
        """
        now = time.time()
        
        try:
            client = await get_redis()
            
            # Keys for tracking
            attempts_key = f"attempts:{identifier}"
            lockout_key = f"lockout:{identifier}"
            history_key = f"history:{identifier}"
            
            # Record the failed attempt
            attempt_data = {
                "timestamp": now,
                "ip_address": ip_address,
                "user_agent": user_agent,
                **(additional_context or {}),
            }
            
            # Use pipeline for atomic operations
            async with client.pipeline() as pipe:
                # Increment failed attempts counter
                pipe.incr(attempts_key)
                pipe.expire(attempts_key, 3600)  # Reset after 1 hour
                
                # Add to attempt history
                pipe.lpush(history_key, str(attempt_data))
                pipe.ltrim(history_key, 0, 99)  # Keep last 100 attempts
                pipe.expire(history_key, 86400 * 7)  # Keep for 7 days
                
                results = await pipe.execute()
            
            failed_attempts = results[0]
            
            # Check if account should be locked
            if failed_attempts >= self.max_attempts:
                lockout_info = await self._apply_lockout(
                    identifier,
                    LockoutReason.FAILED_LOGIN_ATTEMPTS,
                    failed_attempts,
                )
                
                # Reset attempts counter after lockout
                await client.delete(attempts_key)
                
                return lockout_info
            
            # Check for brute force patterns
            if ip_address:
                brute_force_detected = await self._check_brute_force_patterns(
                    identifier,
                    ip_address,
                    failed_attempts,
                )
                
                if brute_force_detected:
                    return await self._apply_lockout(
                        identifier,
                        LockoutReason.BRUTE_FORCE_DETECTED,
                        failed_attempts,
                        severity=LockoutSeverity.HIGH,
                    )
            
            remaining_attempts = max(0, self.max_attempts - failed_attempts)
            
            return AccountLockoutInfo(
                is_locked=False,
                failed_attempts=failed_attempts,
                remaining_attempts=remaining_attempts,
            )
            
        except Exception as e:
            logger.error(f"Record failed attempt error: {e}")
            # Fail safe - assume not locked
            return AccountLockoutInfo(
                is_locked=False,
                failed_attempts=0,
                remaining_attempts=self.max_attempts,
            )
    
    async def check_lockout_status(
        self,
        identifier: str,
    ) -> AccountLockoutInfo:
        """
        Check current lockout status for an account.
        
        Args:
            identifier: Account identifier
            
        Returns:
            AccountLockoutInfo with current status
        """
        try:
            client = await get_redis()
            
            # Get lockout information
            lockout_data = await client.hmget(
                f"lockout:{identifier}",
                ["locked_until", "reason", "severity", "lockout_count"]
            )
            
            # Get current failed attempts
            failed_attempts = await client.get(f"attempts:{identifier}")
            failed_attempts = int(failed_attempts) if failed_attempts else 0
            
            locked_until_timestamp = lockout_data[0]
            reason = lockout_data[1]
            severity = lockout_data[2]
            lockout_count = int(lockout_data[3]) if lockout_data[3] else 0
            
            if locked_until_timestamp:
                locked_until = datetime.fromtimestamp(float(locked_until_timestamp))
                
                # Check if lockout has expired
                if datetime.now() > locked_until:
                    await self._clear_lockout(identifier)
                    return AccountLockoutInfo(
                        is_locked=False,
                        failed_attempts=0,
                        remaining_attempts=self.max_attempts,
                    )
                
                return AccountLockoutInfo(
                    is_locked=True,
                    failed_attempts=failed_attempts,
                    lockout_until=locked_until,
                    reason=LockoutReason(reason) if reason else None,
                    severity=LockoutSeverity(severity) if severity else None,
                )
            
            remaining_attempts = max(0, self.max_attempts - failed_attempts)
            
            return AccountLockoutInfo(
                is_locked=False,
                failed_attempts=failed_attempts,
                remaining_attempts=remaining_attempts,
            )
            
        except Exception as e:
            logger.error(f"Check lockout status error: {e}")
            # Fail safe - assume not locked
            return AccountLockoutInfo(
                is_locked=False,
                failed_attempts=0,
                remaining_attempts=self.max_attempts,
            )
    
    async def clear_failed_attempts(
        self,
        identifier: str,
    ) -> bool:
        """
        Clear failed attempts counter for successful login.
        
        Args:
            identifier: Account identifier
            
        Returns:
            Success status
        """
        try:
            client = await get_redis()
            await client.delete(f"attempts:{identifier}")
            logger.info(f"Cleared failed attempts for {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Clear failed attempts error: {e}")
            return False
    
    async def manual_lockout(
        self,
        identifier: str,
        reason: LockoutReason,
        duration_minutes: Optional[int] = None,
        severity: LockoutSeverity = LockoutSeverity.HIGH,
        admin_user: Optional[str] = None,
    ) -> AccountLockoutInfo:
        """
        Manually lock an account.
        
        Args:
            identifier: Account identifier
            reason: Reason for lockout
            duration_minutes: Lockout duration (None for indefinite)
            severity: Lockout severity
            admin_user: Admin user who initiated lockout
            
        Returns:
            AccountLockoutInfo with lockout details
        """
        return await self._apply_lockout(
            identifier,
            reason,
            0,
            severity,
            duration_minutes,
            admin_user,
        )
    
    async def unlock_account(
        self,
        identifier: str,
        admin_user: Optional[str] = None,
    ) -> bool:
        """
        Manually unlock an account.
        
        Args:
            identifier: Account identifier
            admin_user: Admin user who unlocked account
            
        Returns:
            Success status
        """
        try:
            success = await self._clear_lockout(identifier)
            
            if success and admin_user:
                # Log the unlock action
                client = await get_redis()
                unlock_log = {
                    "timestamp": time.time(),
                    "admin_user": admin_user,
                    "action": "manual_unlock",
                }
                await client.lpush(
                    f"unlock_log:{identifier}",
                    str(unlock_log)
                )
                await client.expire(f"unlock_log:{identifier}", 86400 * 30)
            
            return success
            
        except Exception as e:
            logger.error(f"Unlock account error: {e}")
            return False
    
    async def get_lockout_history(
        self,
        identifier: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get lockout history for an account.
        
        Args:
            identifier: Account identifier
            limit: Maximum number of entries to return
            
        Returns:
            List of lockout history entries
        """
        try:
            client = await get_redis()
            
            # Get attempt history
            history_entries = await client.lrange(
                f"history:{identifier}",
                0,
                limit - 1
            )
            
            history = []
            for entry in history_entries:
                try:
                    # Parse the stored data
                    import ast
                    entry_data = ast.literal_eval(entry)
                    history.append(entry_data)
                except Exception:
                    continue
            
            return history
            
        except Exception as e:
            logger.error(f"Get lockout history error: {e}")
            return []
    
    async def get_brute_force_stats(
        self,
        ip_address: str,
        time_window_minutes: int = 60,
    ) -> Dict:
        """
        Get brute force statistics for an IP address.
        
        Args:
            ip_address: IP address to analyze
            time_window_minutes: Time window for analysis
            
        Returns:
            Dictionary with brute force statistics
        """
        try:
            client = await get_redis()
            
            # Get IP-based attempt patterns
            now = time.time()
            window_start = now - (time_window_minutes * 60)
            
            # Count attempts from this IP
            ip_key = f"ip_attempts:{ip_address}"
            
            # This would require additional tracking in record_failed_attempt
            # For now, return basic structure
            return {
                "ip_address": ip_address,
                "time_window_minutes": time_window_minutes,
                "total_attempts": 0,
                "unique_accounts": 0,
                "is_brute_force": False,
            }
            
        except Exception as e:
            logger.error(f"Get brute force stats error: {e}")
            return {}
    
    async def _apply_lockout(
        self,
        identifier: str,
        reason: LockoutReason,
        failed_attempts: int,
        severity: LockoutSeverity = LockoutSeverity.MEDIUM,
        duration_minutes: Optional[int] = None,
        admin_user: Optional[str] = None,
    ) -> AccountLockoutInfo:
        """
        Apply lockout to an account.
        
        Args:
            identifier: Account identifier
            reason: Lockout reason
            failed_attempts: Number of failed attempts
            severity: Lockout severity
            duration_minutes: Custom duration
            admin_user: Admin user (for manual lockouts)
            
        Returns:
            AccountLockoutInfo with lockout details
        """
        try:
            client = await get_redis()
            
            # Determine lockout duration
            if duration_minutes is None:
                if self.progressive_lockout and reason == LockoutReason.FAILED_LOGIN_ATTEMPTS:
                    # Get previous lockout count
                    lockout_count = await client.get(f"lockout_count:{identifier}")
                    lockout_count = int(lockout_count) if lockout_count else 0
                    lockout_count += 1
                    
                    # Use progressive duration
                    duration_minutes = self.lockout_durations.get(
                        lockout_count,
                        self.lockout_durations[max(self.lockout_durations.keys())]
                    )
                    
                    # Update lockout count
                    await client.setex(
                        f"lockout_count:{identifier}",
                        86400 * 30,  # Keep for 30 days
                        lockout_count
                    )
                else:
                    duration_minutes = self.base_lockout_duration
            
            # Calculate lockout end time
            if duration_minutes > 0:
                lockout_until = datetime.now() + timedelta(minutes=duration_minutes)
                lockout_until_timestamp = lockout_until.timestamp()
            else:
                # Indefinite lockout
                lockout_until = None
                lockout_until_timestamp = None
            
            # Store lockout information
            lockout_data = {
                "locked_until": lockout_until_timestamp,
                "reason": reason.value,
                "severity": severity.value,
                "failed_attempts": failed_attempts,
                "locked_at": time.time(),
                "admin_user": admin_user,
            }
            
            await client.hmset(f"lockout:{identifier}", lockout_data)
            
            if lockout_until_timestamp:
                # Set expiration for automatic cleanup
                expire_time = int(duration_minutes * 60) + 3600  # Add 1 hour buffer
                await client.expire(f"lockout:{identifier}", expire_time)
            
            logger.warning(
                f"Account locked: {identifier}, reason: {reason.value}, "
                f"duration: {duration_minutes} minutes"
            )
            
            return AccountLockoutInfo(
                is_locked=True,
                failed_attempts=failed_attempts,
                lockout_until=lockout_until,
                reason=reason,
                severity=severity,
            )
            
        except Exception as e:
            logger.error(f"Apply lockout error: {e}")
            # Return lockout info even if storage fails
            return AccountLockoutInfo(
                is_locked=True,
                failed_attempts=failed_attempts,
                reason=reason,
                severity=severity,
            )
    
    async def _clear_lockout(
        self,
        identifier: str,
    ) -> bool:
        """
        Clear lockout for an account.
        
        Args:
            identifier: Account identifier
            
        Returns:
            Success status
        """
        try:
            client = await get_redis()
            
            keys_to_delete = [
                f"lockout:{identifier}",
                f"attempts:{identifier}",
            ]
            
            await client.delete(*keys_to_delete)
            logger.info(f"Cleared lockout for {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Clear lockout error: {e}")
            return False
    
    async def _check_brute_force_patterns(
        self,
        identifier: str,
        ip_address: str,
        current_attempts: int,
    ) -> bool:
        """
        Check for brute force attack patterns.
        
        Args:
            identifier: Account identifier
            ip_address: Client IP address
            current_attempts: Current failed attempts
            
        Returns:
            True if brute force detected
        """
        try:
            client = await get_redis()
            
            # Track IP-based attempts
            ip_attempts_key = f"ip_attempts:{ip_address}"
            
            # Increment IP attempt counter
            ip_attempts = await client.incr(ip_attempts_key)
            await client.expire(ip_attempts_key, 3600)  # 1 hour window
            
            # Check if IP exceeds brute force threshold
            threshold = self.brute_force_thresholds["attempts_per_hour"]
            if ip_attempts > threshold:
                logger.warning(f"Brute force detected from IP {ip_address}: {ip_attempts} attempts")
                return True
            
            # Additional patterns could be checked here:
            # - Multiple accounts from same IP
            # - Rapid succession attempts
            # - Geographic anomalies
            
            return False
            
        except Exception as e:
            logger.error(f"Check brute force patterns error: {e}")
            return False


# Create default lockout service instance
lockout_service = AccountLockoutService(
    max_attempts=5,
    lockout_duration_minutes=30,
    progressive_lockout=True,
)