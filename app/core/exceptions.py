"""
Custom exceptions for the application.
"""
from typing import Any, Dict, Optional


class SlideGenieException(Exception):
    """Base exception for all SlideGenie exceptions."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(SlideGenieException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, resource_id: Any):
        message = f"{resource} with ID {resource_id} not found"
        super().__init__(message, status_code=404)


class ValidationError(SlideGenieException):
    """Validation error exception."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, status_code=422, details=details)


class AuthenticationError(SlideGenieException):
    """Authentication error exception."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationError(SlideGenieException):
    """Authorization error exception."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class RateLimitError(SlideGenieException):
    """Rate limit exceeded exception."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, status_code=429, details=details)


class ExternalServiceError(SlideGenieException):
    """External service error exception."""
    
    def __init__(self, service: str, message: str):
        full_message = f"External service error ({service}): {message}"
        super().__init__(full_message, status_code=503)


class GenerationError(SlideGenieException):
    """Presentation generation error exception."""
    
    def __init__(self, message: str, job_id: Optional[str] = None):
        details = {"job_id": job_id} if job_id else {}
        super().__init__(message, status_code=500, details=details)


class StorageError(SlideGenieException):
    """Storage operation error exception."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {"operation": operation} if operation else {}
        super().__init__(message, status_code=500, details=details)


class QuotaExceededError(SlideGenieException):
    """User quota exceeded exception."""
    
    def __init__(
        self,
        resource: str,
        limit: int,
        current: int,
    ):
        message = f"Quota exceeded for {resource}: {current}/{limit}"
        details = {
            "resource": resource,
            "limit": limit,
            "current": current,
        }
        super().__init__(message, status_code=402, details=details)


class InvalidCredentialsError(SlideGenieException):
    """Invalid credentials exception."""
    
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)


class UserAlreadyExistsError(SlideGenieException):
    """User already exists exception."""
    
    def __init__(self, message: str = "User already exists"):
        super().__init__(message, status_code=409)


class UserNotFoundError(SlideGenieException):
    """User not found exception."""
    
    def __init__(self, message: str = "User not found"):
        super().__init__(message, status_code=404)


class EmailNotVerifiedError(SlideGenieException):
    """Email not verified exception."""
    
    def __init__(self, message: str = "Email address not verified"):
        super().__init__(message, status_code=403)


class InvalidTokenError(SlideGenieException):
    """Invalid token exception."""
    
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, status_code=401)


class TokenExpiredError(SlideGenieException):
    """Token expired exception."""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, status_code=401)


class EmailDeliveryError(SlideGenieException):
    """Email delivery error exception."""
    
    def __init__(self, message: str = "Failed to deliver email"):
        super().__init__(message, status_code=503)