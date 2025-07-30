"""
Security services for SlideGenie authentication system.

This package provides comprehensive security features including:
- Rate limiting
- Account lockout mechanisms
- Brute force protection
- Security headers middleware
- Audit logging
- IP whitelisting
"""

from .audit import AuditLogger, SecurityEvent, AuditSeverity, audit_logger
from .lockout import AccountLockoutService, LockoutReason, LockoutSeverity, lockout_service
from .middleware import SecurityMiddleware, RateLimitMiddleware, SecurityHeaders
from .rate_limiter import RateLimiter, RateLimitStrategy, rate_limiter

__all__ = [
    # Audit logging
    "AuditLogger",
    "SecurityEvent",
    "AuditSeverity",
    "audit_logger",
    
    # Account lockout
    "AccountLockoutService",
    "LockoutReason",
    "LockoutSeverity",
    "lockout_service",
    
    # Rate limiting
    "RateLimiter",
    "RateLimitStrategy",
    "rate_limiter",
    
    # Middleware
    "SecurityMiddleware",
    "RateLimitMiddleware",
    "SecurityHeaders",
]