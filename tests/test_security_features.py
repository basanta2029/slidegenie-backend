"""
Tests for SlideGenie security features.

Tests rate limiting, account lockout, security middleware, and audit logging.
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.services.security import (
    AccountLockoutService,
    AuditLogger,
    RateLimiter,
    RateLimitStrategy,
    SecurityEvent,
    SecurityMiddleware,
    RateLimitMiddleware,
    LockoutReason,
)


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limit(self):
        """Test sliding window rate limiting."""
        rate_limiter = RateLimiter(
            default_limit=5,
            default_window=10,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        
        identifier = "test_user_1"
        
        # Make 5 requests (should all pass)
        for i in range(5):
            result = await rate_limiter.check_rate_limit(identifier)
            assert result.allowed is True
            assert result.remaining == 4 - i
        
        # 6th request should fail
        result = await rate_limiter.check_rate_limit(identifier)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
    
    @pytest.mark.asyncio
    async def test_endpoint_specific_limits(self):
        """Test endpoint-specific rate limits."""
        rate_limiter = RateLimiter()
        
        # Test login endpoint (5 per 5 minutes)
        identifier = "test_user_2"
        endpoint = "auth:login"
        
        # First 5 should pass
        for i in range(5):
            result = await rate_limiter.check_rate_limit(
                identifier=identifier,
                endpoint=endpoint,
            )
            assert result.allowed is True
        
        # 6th should fail
        result = await rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=endpoint,
        )
        assert result.allowed is False
        assert result.limit == 5
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self):
        """Test resetting rate limits."""
        rate_limiter = RateLimiter(default_limit=3, default_window=60)
        
        identifier = "test_user_3"
        
        # Use up the limit
        for _ in range(3):
            await rate_limiter.check_rate_limit(identifier)
        
        # Should be blocked
        result = await rate_limiter.check_rate_limit(identifier)
        assert result.allowed is False
        
        # Reset the limit
        success = await rate_limiter.reset_rate_limit(identifier)
        assert success is True
        
        # Should be allowed again
        result = await rate_limiter.check_rate_limit(identifier)
        assert result.allowed is True


class TestAccountLockout:
    """Test account lockout functionality."""
    
    @pytest.mark.asyncio
    async def test_failed_login_tracking(self):
        """Test tracking failed login attempts."""
        lockout_service = AccountLockoutService(
            max_attempts=3,
            lockout_duration_minutes=15,
        )
        
        identifier = "test@example.com"
        ip_address = "192.168.1.1"
        
        # First 2 attempts should not lock
        for i in range(2):
            info = await lockout_service.record_failed_attempt(
                identifier=identifier,
                ip_address=ip_address,
            )
            assert info.is_locked is False
            assert info.failed_attempts == i + 1
            assert info.remaining_attempts == 2 - i
        
        # 3rd attempt should trigger lockout
        info = await lockout_service.record_failed_attempt(
            identifier=identifier,
            ip_address=ip_address,
        )
        assert info.is_locked is True
        assert info.failed_attempts == 3
        assert info.lockout_until is not None
        assert info.reason == LockoutReason.FAILED_LOGIN_ATTEMPTS
    
    @pytest.mark.asyncio
    async def test_progressive_lockout(self):
        """Test progressive lockout durations."""
        lockout_service = AccountLockoutService(
            max_attempts=2,
            progressive_lockout=True,
        )
        
        identifier = "progressive@example.com"
        
        # First lockout - 5 minutes
        for _ in range(2):
            await lockout_service.record_failed_attempt(identifier)
        
        info = await lockout_service.check_lockout_status(identifier)
        assert info.is_locked is True
        
        # Clear lockout
        await lockout_service.unlock_account(identifier)
        
        # Second lockout - should be longer (15 minutes)
        for _ in range(2):
            await lockout_service.record_failed_attempt(identifier)
        
        info = await lockout_service.check_lockout_status(identifier)
        assert info.is_locked is True
        # Duration should be longer for second lockout
    
    @pytest.mark.asyncio
    async def test_clear_failed_attempts(self):
        """Test clearing failed attempts on successful login."""
        lockout_service = AccountLockoutService(max_attempts=5)
        
        identifier = "success@example.com"
        
        # Record 3 failed attempts
        for _ in range(3):
            await lockout_service.record_failed_attempt(identifier)
        
        # Clear attempts (successful login)
        success = await lockout_service.clear_failed_attempts(identifier)
        assert success is True
        
        # Check status - should be reset
        info = await lockout_service.check_lockout_status(identifier)
        assert info.is_locked is False
        assert info.failed_attempts == 0
        assert info.remaining_attempts == 5


class TestSecurityMiddleware:
    """Test security middleware functionality."""
    
    def test_security_headers(self):
        """Test security headers are added to responses."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Add security middleware
        app.add_middleware(
            SecurityMiddleware,
            enable_hsts=True,
            enable_csp=True,
        )
        
        client = TestClient(app)
        response = client.get("/test")
        
        # Check security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    
    def test_request_id_generation(self):
        """Test request ID generation."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"request_id": request.state.request_id}
        
        app.add_middleware(SecurityMiddleware)
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert "X-Request-ID" in response.headers
        assert response.json()["request_id"] is not None
    
    def test_suspicious_pattern_detection(self):
        """Test detection of suspicious patterns."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        app.add_middleware(SecurityMiddleware)
        
        client = TestClient(app)
        
        # Test SQL injection pattern
        response = client.get("/test?query='; DROP TABLE users; --")
        assert response.status_code == 400
        assert "Suspicious SQL pattern" in response.json()["detail"]
        
        # Test XSS pattern
        response = client.get("/test?input=<script>alert('xss')</script>")
        assert response.status_code == 400
        assert "Suspicious XSS pattern" in response.json()["detail"]
        
        # Test path traversal
        response = client.get("/test/../../../etc/passwd")
        assert response.status_code == 400
        assert "Path traversal" in response.json()["detail"]


class TestAuditLogger:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_log_security_event(self):
        """Test logging security events."""
        audit_logger = AuditLogger(retention_days=30)
        
        # Log a login success event
        entry_id = await audit_logger.log_event(
            event=SecurityEvent.LOGIN_SUCCESS,
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            session_id="session123",
            details={"login_method": "password"},
        )
        
        assert entry_id is not None
        
        # Query the log
        logs = await audit_logger.query_logs(
            user_id="user123",
            event_type=SecurityEvent.LOGIN_SUCCESS,
        )
        
        assert len(logs) > 0
        assert logs[0]["event"] == SecurityEvent.LOGIN_SUCCESS.value
        assert logs[0]["user_id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_query_logs_with_filters(self):
        """Test querying logs with various filters."""
        audit_logger = AuditLogger()
        
        # Log various events
        events = [
            (SecurityEvent.LOGIN_SUCCESS, "user1", "192.168.1.1"),
            (SecurityEvent.LOGIN_FAILURE, "user2", "192.168.1.2"),
            (SecurityEvent.ACCOUNT_LOCKED, "user1", "192.168.1.1"),
            (SecurityEvent.PASSWORD_CHANGE, "user1", "192.168.1.3"),
        ]
        
        for event, user_id, ip in events:
            await audit_logger.log_event(
                event=event,
                user_id=user_id,
                ip_address=ip,
            )
        
        # Query by user
        user1_logs = await audit_logger.query_logs(user_id="user1")
        assert len(user1_logs) >= 3
        
        # Query by event type
        login_failures = await audit_logger.query_logs(
            event_type=SecurityEvent.LOGIN_FAILURE
        )
        assert len(login_failures) >= 1
        
        # Query by IP
        ip_logs = await audit_logger.query_logs(ip_address="192.168.1.1")
        assert len(ip_logs) >= 2
    
    @pytest.mark.asyncio
    async def test_user_activity_summary(self):
        """Test user activity summary generation."""
        audit_logger = AuditLogger()
        
        user_id = "activity_test_user"
        
        # Log various activities
        await audit_logger.log_event(
            SecurityEvent.LOGIN_SUCCESS,
            user_id=user_id,
        )
        await audit_logger.log_event(
            SecurityEvent.LOGIN_FAILURE,
            user_id=user_id,
        )
        await audit_logger.log_event(
            SecurityEvent.LOGIN_FAILURE,
            user_id=user_id,
        )
        await audit_logger.log_event(
            SecurityEvent.PASSWORD_CHANGE,
            user_id=user_id,
        )
        
        # Get activity summary
        summary = await audit_logger.get_user_activity(
            user_id=user_id,
            days=7,
        )
        
        assert summary["user_id"] == user_id
        assert summary["total_events"] >= 4
        assert summary["login_count"] >= 1
        assert summary["failed_login_count"] >= 2
        assert SecurityEvent.PASSWORD_CHANGE.value in summary["events_by_type"]
    
    @pytest.mark.asyncio
    async def test_security_metrics(self):
        """Test security metrics generation."""
        audit_logger = AuditLogger()
        
        # Log various security events
        await audit_logger.log_event(
            SecurityEvent.LOGIN_FAILURE,
            ip_address="192.168.1.10",
        )
        await audit_logger.log_event(
            SecurityEvent.ACCOUNT_LOCKED,
            user_id="locked_user",
        )
        await audit_logger.log_event(
            SecurityEvent.RATE_LIMIT_EXCEEDED,
            ip_address="192.168.1.11",
        )
        
        # Get metrics
        metrics = await audit_logger.get_security_metrics(hours=1)
        
        assert metrics["period_hours"] == 1
        assert metrics["failed_logins"] >= 1
        assert metrics["account_lockouts"] >= 1
        assert metrics["rate_limit_hits"] >= 1


class TestIntegration:
    """Test integration of security features."""
    
    def test_rate_limit_middleware(self):
        """Test rate limit middleware integration."""
        app = FastAPI()
        
        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "success"}
        
        # Add rate limit middleware
        app.add_middleware(
            RateLimitMiddleware,
            default_limit=3,
            default_window=60,
        )
        
        client = TestClient(app)
        
        # First 3 requests should succeed
        for i in range(3):
            response = client.get("/api/test")
            assert response.status_code == 200
            assert int(response.headers["X-RateLimit-Remaining"]) == 2 - i
        
        # 4th request should be rate limited
        response = client.get("/api/test")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
        assert "Retry-After" in response.headers
    
    @pytest.mark.asyncio
    async def test_login_with_lockout(self):
        """Test login endpoint with lockout integration."""
        lockout_service = AccountLockoutService(max_attempts=3)
        audit_logger = AuditLogger()
        
        email = "test@example.com"
        ip_address = "192.168.1.100"
        
        # Simulate failed login attempts
        for i in range(3):
            info = await lockout_service.record_failed_attempt(
                identifier=email,
                ip_address=ip_address,
            )
            
            await audit_logger.log_event(
                event=SecurityEvent.LOGIN_FAILURE,
                user_id=email,
                ip_address=ip_address,
                details={"attempt": i + 1},
            )
            
            if info.is_locked:
                await audit_logger.log_event(
                    event=SecurityEvent.ACCOUNT_LOCKED,
                    user_id=email,
                    ip_address=ip_address,
                    details={"reason": "max_attempts_exceeded"},
                )
        
        # Verify account is locked
        status = await lockout_service.check_lockout_status(email)
        assert status.is_locked is True
        
        # Verify audit logs
        logs = await audit_logger.query_logs(
            user_id=email,
            event_type=SecurityEvent.ACCOUNT_LOCKED,
        )
        assert len(logs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])