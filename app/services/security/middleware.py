"""
Security middleware for SlideGenie authentication system.

Provides comprehensive security headers and request protection:
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Request validation and sanitization
- XSS protection
- CSRF protection
- Content type validation
"""

import hashlib
import secrets
import time
from typing import Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger
from app.services.security.audit import AuditLogger, SecurityEvent
from app.services.security.rate_limiter import rate_limiter

logger = get_logger(__name__)


class SecurityHeaders:
    """Security headers configuration."""
    
    # Strict Transport Security
    HSTS = "max-age=31536000; includeSubDomains; preload"
    
    # Content Security Policy
    CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    # Additional security headers
    X_CONTENT_TYPE_OPTIONS = "nosniff"
    X_FRAME_OPTIONS = "DENY"
    X_XSS_PROTECTION = "1; mode=block"
    REFERRER_POLICY = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for FastAPI applications.
    
    Features:
    - Security headers injection
    - Request validation
    - CSRF protection
    - XSS prevention
    - Content type validation
    - Request ID generation
    - Security event logging
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enable_hsts: bool = True,
        enable_csp: bool = True,
        enable_csrf: bool = True,
        trusted_origins: Optional[List[str]] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize security middleware.
        
        Args:
            app: FastAPI application
            enable_hsts: Enable HSTS header
            enable_csp: Enable CSP header
            enable_csrf: Enable CSRF protection
            trusted_origins: List of trusted origins for CORS/CSRF
            audit_logger: Audit logger instance
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.enable_csrf = enable_csrf
        self.trusted_origins = set(trusted_origins or [settings.FRONTEND_URL])
        self.audit_logger = audit_logger or AuditLogger()
        
        # Paths to exclude from CSRF protection
        self.csrf_exempt_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/oauth/callback",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        
        # Content types that require validation
        self.allowed_content_types = {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        }
        
        # Dangerous content types to block
        self.blocked_content_types = {
            "text/html",
            "application/javascript",
            "application/x-shockwave-flash",
        }
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process security middleware.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with security headers
        """
        # Generate request ID
        request_id = self._generate_request_id()
        request.state.request_id = request_id
        
        # Security validations
        security_checks = [
            self._validate_content_type(request),
            self._validate_request_size(request),
            self._check_suspicious_patterns(request),
        ]
        
        # CSRF validation for state-changing requests
        if (
            self.enable_csrf and
            request.method in ["POST", "PUT", "DELETE", "PATCH"] and
            request.url.path not in self.csrf_exempt_paths
        ):
            security_checks.append(self._validate_csrf(request))
        
        # Run security checks
        for check_result in security_checks:
            if check_result:
                await self._log_security_event(
                    request,
                    SecurityEvent.SUSPICIOUS_REQUEST,
                    {"reason": check_result}
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": check_result}
                )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add security headers
        self._add_security_headers(response)
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log security events for specific status codes
        if response.status_code >= 400:
            await self._log_response_event(request, response)
        
        return response
    
    def _add_security_headers(self, response: Response) -> None:
        """
        Add security headers to response.
        
        Args:
            response: Response object
        """
        # Strict Transport Security
        if self.enable_hsts and settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = SecurityHeaders.HSTS
        
        # Content Security Policy
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = SecurityHeaders.CSP
        
        # Standard security headers
        response.headers["X-Content-Type-Options"] = SecurityHeaders.X_CONTENT_TYPE_OPTIONS
        response.headers["X-Frame-Options"] = SecurityHeaders.X_FRAME_OPTIONS
        response.headers["X-XSS-Protection"] = SecurityHeaders.X_XSS_PROTECTION
        response.headers["Referrer-Policy"] = SecurityHeaders.REFERRER_POLICY
        response.headers["Permissions-Policy"] = SecurityHeaders.PERMISSIONS_POLICY
        
        # Remove server header
        response.headers.pop("Server", None)
        
        # Cache control for sensitive data
        if "api" in str(response.headers.get("content-type", "")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    
    def _validate_content_type(self, request: Request) -> Optional[str]:
        """
        Validate request content type.
        
        Args:
            request: Incoming request
            
        Returns:
            Error message if validation fails
        """
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            
            # Check for blocked content types
            if content_type in self.blocked_content_types:
                return f"Blocked content type: {content_type}"
            
            # For API endpoints, ensure proper content type
            if request.url.path.startswith("/api/"):
                if content_type and content_type not in self.allowed_content_types:
                    return f"Invalid content type: {content_type}"
        
        return None
    
    def _validate_request_size(self, request: Request) -> Optional[str]:
        """
        Validate request size.
        
        Args:
            request: Incoming request
            
        Returns:
            Error message if validation fails
        """
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                max_size = 10 * 1024 * 1024  # 10MB default
                
                if size > max_size:
                    return f"Request too large: {size} bytes"
            except ValueError:
                return "Invalid content-length header"
        
        return None
    
    def _check_suspicious_patterns(self, request: Request) -> Optional[str]:
        """
        Check for suspicious patterns in request.
        
        Args:
            request: Incoming request
            
        Returns:
            Error message if suspicious patterns found
        """
        # Check for SQL injection patterns in query params
        query_string = str(request.url.query)
        sql_patterns = [
            "union select",
            "drop table",
            "insert into",
            "delete from",
            "update set",
            "--",
            "/*",
            "*/",
            "xp_",
            "sp_",
        ]
        
        query_lower = query_string.lower()
        for pattern in sql_patterns:
            if pattern in query_lower:
                return f"Suspicious SQL pattern detected: {pattern}"
        
        # Check for XSS patterns in query params
        xss_patterns = [
            "<script",
            "javascript:",
            "onerror=",
            "onload=",
            "onclick=",
            "onmouseover=",
            "<iframe",
            "<object",
            "<embed",
        ]
        
        for pattern in xss_patterns:
            if pattern in query_lower:
                return f"Suspicious XSS pattern detected: {pattern}"
        
        # Check for path traversal
        path = str(request.url.path)
        if "../" in path or "..%2F" in path or "..%5C" in path:
            return "Path traversal attempt detected"
        
        return None
    
    def _validate_csrf(self, request: Request) -> Optional[str]:
        """
        Validate CSRF token.
        
        Args:
            request: Incoming request
            
        Returns:
            Error message if CSRF validation fails
        """
        # Get CSRF token from header or form data
        csrf_token = request.headers.get("X-CSRF-Token")
        
        if not csrf_token:
            return "Missing CSRF token"
        
        # Validate origin/referer
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        
        if origin:
            if not self._is_trusted_origin(origin):
                return f"Untrusted origin: {origin}"
        elif referer:
            referer_origin = urlparse(referer).netloc
            if not self._is_trusted_origin(f"https://{referer_origin}"):
                return f"Untrusted referer: {referer}"
        else:
            return "Missing origin and referer headers"
        
        # Additional CSRF token validation would go here
        # For now, we just check presence and origin
        
        return None
    
    def _is_trusted_origin(self, origin: str) -> bool:
        """
        Check if origin is trusted.
        
        Args:
            origin: Origin to check
            
        Returns:
            True if trusted
        """
        parsed_origin = urlparse(origin)
        origin_host = f"{parsed_origin.scheme}://{parsed_origin.netloc}"
        
        return origin_host in self.trusted_origins
    
    def _generate_request_id(self) -> str:
        """
        Generate unique request ID.
        
        Returns:
            Request ID
        """
        # Use timestamp + random for uniqueness
        timestamp = str(int(time.time() * 1000000))
        random_part = secrets.token_hex(8)
        
        # Create hash for shorter ID
        data = f"{timestamp}-{random_part}"
        hash_digest = hashlib.sha256(data.encode()).hexdigest()
        
        return hash_digest[:16]
    
    async def _log_security_event(
        self,
        request: Request,
        event: SecurityEvent,
        details: Optional[Dict] = None,
    ) -> None:
        """
        Log security event.
        
        Args:
            request: Request object
            event: Security event type
            details: Additional details
        """
        try:
            client_ip = request.client.host if request.client else "unknown"
            
            await self.audit_logger.log_event(
                event=event,
                user_id=getattr(request.state, "user_id", None),
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                details={
                    "path": str(request.url.path),
                    "method": request.method,
                    "request_id": getattr(request.state, "request_id", None),
                    **(details or {}),
                }
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    async def _log_response_event(
        self,
        request: Request,
        response: Response,
    ) -> None:
        """
        Log response-related security events.
        
        Args:
            request: Request object
            response: Response object
        """
        event_map = {
            401: SecurityEvent.UNAUTHORIZED_ACCESS,
            403: SecurityEvent.FORBIDDEN_ACCESS,
            429: SecurityEvent.RATE_LIMIT_EXCEEDED,
        }
        
        event = event_map.get(response.status_code)
        if event:
            await self._log_security_event(
                request,
                event,
                {"status_code": response.status_code}
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using the rate limiter service.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 100,
        default_window: int = 60,
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: FastAPI application
            default_limit: Default request limit
            default_window: Default window in seconds
        """
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get identifier (IP or user ID)
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)
        identifier = user_id or f"ip:{client_ip}"
        
        # Determine endpoint for specific limits
        endpoint = None
        if request.url.path.startswith("/api/v1/auth/"):
            endpoint = f"auth:{request.url.path.split('/')[-1]}"
        elif request.url.path.startswith("/api/v1/"):
            endpoint = "api:general"
        
        # Check rate limit
        result = await rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=endpoint,
        )
        
        # If rate limit exceeded
        if not result.allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": result.retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": result.reset_time.isoformat(),
                    "Retry-After": str(result.retry_after),
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = result.reset_time.isoformat()
        
        return response