"""
Standardized Error Message Catalog for SlideGenie.

Centralizes all error messages for consistency, internationalization,
and security (avoiding information leakage).
"""
from enum import Enum
from typing import Dict, Optional


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""
    
    # Authentication Errors (AUTH_*)
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_USER_NOT_FOUND = "AUTH_002"
    AUTH_USER_ALREADY_EXISTS = "AUTH_003"
    AUTH_EMAIL_NOT_VERIFIED = "AUTH_004"
    AUTH_INVALID_TOKEN = "AUTH_005"
    AUTH_TOKEN_EXPIRED = "AUTH_006"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_007"
    AUTH_SESSION_EXPIRED = "AUTH_008"
    AUTH_INVALID_REFRESH_TOKEN = "AUTH_009"
    AUTH_ACCOUNT_LOCKED = "AUTH_010"
    AUTH_ACCOUNT_DISABLED = "AUTH_011"
    AUTH_INVALID_API_KEY = "AUTH_012"
    AUTH_API_KEY_EXPIRED = "AUTH_013"
    AUTH_OAUTH_ERROR = "AUTH_014"
    AUTH_OAUTH_STATE_MISMATCH = "AUTH_015"
    
    # Validation Errors (VAL_*)
    VAL_INVALID_EMAIL_FORMAT = "VAL_001"
    VAL_WEAK_PASSWORD = "VAL_002"
    VAL_INVALID_INPUT = "VAL_003"
    VAL_MISSING_REQUIRED_FIELD = "VAL_004"
    VAL_INVALID_FIELD_TYPE = "VAL_005"
    VAL_FIELD_TOO_LONG = "VAL_006"
    VAL_FIELD_TOO_SHORT = "VAL_007"
    VAL_INVALID_DATE_FORMAT = "VAL_008"
    VAL_INVALID_UUID = "VAL_009"
    VAL_INVALID_ENUM_VALUE = "VAL_010"
    
    # Security Errors (SEC_*)
    SEC_RATE_LIMIT_EXCEEDED = "SEC_001"
    SEC_SUSPICIOUS_ACTIVITY = "SEC_002"
    SEC_CSRF_TOKEN_INVALID = "SEC_003"
    SEC_UNAUTHORIZED_ACCESS = "SEC_004"
    SEC_FORBIDDEN_RESOURCE = "SEC_005"
    SEC_INVALID_ORIGIN = "SEC_006"
    SEC_IP_BLOCKED = "SEC_007"
    
    # Business Logic Errors (BUS_*)
    BUS_RESOURCE_NOT_FOUND = "BUS_001"
    BUS_RESOURCE_ALREADY_EXISTS = "BUS_002"
    BUS_INVALID_OPERATION = "BUS_003"
    BUS_QUOTA_EXCEEDED = "BUS_004"
    BUS_SUBSCRIPTION_REQUIRED = "BUS_005"
    BUS_FEATURE_NOT_AVAILABLE = "BUS_006"
    BUS_INVALID_STATE_TRANSITION = "BUS_007"
    
    # System Errors (SYS_*)
    SYS_INTERNAL_ERROR = "SYS_001"
    SYS_DATABASE_ERROR = "SYS_002"
    SYS_EXTERNAL_SERVICE_ERROR = "SYS_003"
    SYS_CONFIGURATION_ERROR = "SYS_004"
    SYS_MAINTENANCE_MODE = "SYS_005"


class ErrorMessages:
    """Centralized error message definitions."""
    
    # Default messages for each error code
    _messages: Dict[ErrorCode, str] = {
        # Authentication Errors
        ErrorCode.AUTH_INVALID_CREDENTIALS: "Invalid email or password",
        ErrorCode.AUTH_USER_NOT_FOUND: "User not found",
        ErrorCode.AUTH_USER_ALREADY_EXISTS: "An account with this email already exists",
        ErrorCode.AUTH_EMAIL_NOT_VERIFIED: "Please verify your email address before logging in",
        ErrorCode.AUTH_INVALID_TOKEN: "Invalid or expired authentication token",
        ErrorCode.AUTH_TOKEN_EXPIRED: "Your session has expired. Please log in again",
        ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: "You don't have permission to perform this action",
        ErrorCode.AUTH_SESSION_EXPIRED: "Your session has expired",
        ErrorCode.AUTH_INVALID_REFRESH_TOKEN: "Invalid refresh token",
        ErrorCode.AUTH_ACCOUNT_LOCKED: "Account is temporarily locked due to multiple failed login attempts",
        ErrorCode.AUTH_ACCOUNT_DISABLED: "This account has been disabled",
        ErrorCode.AUTH_INVALID_API_KEY: "Invalid API key",
        ErrorCode.AUTH_API_KEY_EXPIRED: "API key has expired",
        ErrorCode.AUTH_OAUTH_ERROR: "OAuth authentication failed",
        ErrorCode.AUTH_OAUTH_STATE_MISMATCH: "OAuth state verification failed",
        
        # Validation Errors
        ErrorCode.VAL_INVALID_EMAIL_FORMAT: "Please enter a valid email address",
        ErrorCode.VAL_WEAK_PASSWORD: "Password does not meet security requirements",
        ErrorCode.VAL_INVALID_INPUT: "Invalid input provided",
        ErrorCode.VAL_MISSING_REQUIRED_FIELD: "Required field is missing",
        ErrorCode.VAL_INVALID_FIELD_TYPE: "Invalid field type",
        ErrorCode.VAL_FIELD_TOO_LONG: "Field value exceeds maximum length",
        ErrorCode.VAL_FIELD_TOO_SHORT: "Field value is below minimum length",
        ErrorCode.VAL_INVALID_DATE_FORMAT: "Invalid date format",
        ErrorCode.VAL_INVALID_UUID: "Invalid identifier format",
        ErrorCode.VAL_INVALID_ENUM_VALUE: "Invalid value for field",
        
        # Security Errors
        ErrorCode.SEC_RATE_LIMIT_EXCEEDED: "Too many requests. Please try again later",
        ErrorCode.SEC_SUSPICIOUS_ACTIVITY: "Suspicious activity detected",
        ErrorCode.SEC_CSRF_TOKEN_INVALID: "Security validation failed",
        ErrorCode.SEC_UNAUTHORIZED_ACCESS: "Unauthorized access",
        ErrorCode.SEC_FORBIDDEN_RESOURCE: "Access to this resource is forbidden",
        ErrorCode.SEC_INVALID_ORIGIN: "Request origin not allowed",
        ErrorCode.SEC_IP_BLOCKED: "Access from your IP address has been blocked",
        
        # Business Logic Errors
        ErrorCode.BUS_RESOURCE_NOT_FOUND: "Requested resource not found",
        ErrorCode.BUS_RESOURCE_ALREADY_EXISTS: "Resource already exists",
        ErrorCode.BUS_INVALID_OPERATION: "This operation is not allowed",
        ErrorCode.BUS_QUOTA_EXCEEDED: "You have exceeded your usage quota",
        ErrorCode.BUS_SUBSCRIPTION_REQUIRED: "This feature requires a premium subscription",
        ErrorCode.BUS_FEATURE_NOT_AVAILABLE: "This feature is not available",
        ErrorCode.BUS_INVALID_STATE_TRANSITION: "Invalid state transition",
        
        # System Errors
        ErrorCode.SYS_INTERNAL_ERROR: "An internal error occurred. Please try again later",
        ErrorCode.SYS_DATABASE_ERROR: "A database error occurred",
        ErrorCode.SYS_EXTERNAL_SERVICE_ERROR: "External service is temporarily unavailable",
        ErrorCode.SYS_CONFIGURATION_ERROR: "System configuration error",
        ErrorCode.SYS_MAINTENANCE_MODE: "System is under maintenance. Please try again later",
    }
    
    # User-friendly messages for specific scenarios
    _user_messages: Dict[str, str] = {
        "password_too_short": "Password must be at least 12 characters long",
        "password_no_uppercase": "Password must contain at least one uppercase letter",
        "password_no_lowercase": "Password must contain at least one lowercase letter",
        "password_no_number": "Password must contain at least one number",
        "password_no_special": "Password must contain at least one special character",
        "email_not_academic": "Please use your academic email address",
        "email_domain_not_allowed": "Email domain is not recognized as an academic institution",
        "oauth_email_unverified": "Please verify your email with the OAuth provider",
        "lockout_remaining_attempts": "Incorrect password. {} attempts remaining",
        "api_key_rate_limit": "API rate limit exceeded. Limit: {} requests per {}",
        "subscription_upgrade_required": "Please upgrade to {} plan to access this feature",
        "role_assignment_forbidden": "You cannot assign roles higher than your own",
        "file_size_exceeded": "File size exceeds maximum allowed size of {} MB",
        "presentation_limit_reached": "You have reached the maximum number of presentations for your plan",
    }
    
    @classmethod
    def get(cls, code: ErrorCode, **kwargs) -> str:
        """
        Get error message for a given error code.
        
        Args:
            code: Error code
            **kwargs: Additional context for formatting
            
        Returns:
            Formatted error message
        """
        base_message = cls._messages.get(code, "An error occurred")
        
        # Format message with provided context
        if kwargs:
            try:
                return base_message.format(**kwargs)
            except KeyError:
                return base_message
        
        return base_message
    
    @classmethod
    def get_user_message(cls, key: str, **kwargs) -> str:
        """
        Get user-friendly message for specific scenarios.
        
        Args:
            key: Message key
            **kwargs: Additional context for formatting
            
        Returns:
            Formatted user message
        """
        message = cls._user_messages.get(key, "An error occurred")
        
        if kwargs:
            try:
                return message.format(**kwargs)
            except KeyError:
                return message
        
        return message


class ErrorResponse:
    """Standardized error response structure."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict] = None,
        field: Optional[str] = None,
    ):
        self.code = code
        self.message = message or ErrorMessages.get(code)
        self.details = details or {}
        self.field = field
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        response = {
            "error": {
                "code": self.code.value,
                "message": self.message,
            }
        }
        
        if self.field:
            response["error"]["field"] = self.field
        
        if self.details:
            response["error"]["details"] = self.details
        
        return response
    
    @classmethod
    def validation_error(
        cls,
        field: str,
        message: str,
        code: ErrorCode = ErrorCode.VAL_INVALID_INPUT
    ) -> "ErrorResponse":
        """Create validation error response."""
        return cls(
            code=code,
            message=message,
            field=field,
        )
    
    @classmethod
    def authentication_error(
        cls,
        code: ErrorCode = ErrorCode.AUTH_INVALID_CREDENTIALS,
        message: Optional[str] = None,
    ) -> "ErrorResponse":
        """Create authentication error response."""
        return cls(code=code, message=message)
    
    @classmethod
    def authorization_error(
        cls,
        resource: Optional[str] = None,
        action: Optional[str] = None,
    ) -> "ErrorResponse":
        """Create authorization error response."""
        details = {}
        if resource:
            details["resource"] = resource
        if action:
            details["action"] = action
        
        return cls(
            code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            details=details,
        )
    
    @classmethod
    def rate_limit_error(
        cls,
        limit: int,
        window: str,
        retry_after: Optional[int] = None,
    ) -> "ErrorResponse":
        """Create rate limit error response."""
        details = {
            "limit": limit,
            "window": window,
        }
        if retry_after:
            details["retry_after"] = retry_after
        
        return cls(
            code=ErrorCode.SEC_RATE_LIMIT_EXCEEDED,
            details=details,
        )


# Validation error messages for common fields
VALIDATION_MESSAGES = {
    "email": {
        "required": "Email address is required",
        "invalid": "Please enter a valid email address",
        "too_long": "Email address is too long",
        "academic_required": "Academic email address is required",
    },
    "password": {
        "required": "Password is required",
        "too_short": ErrorMessages.get_user_message("password_too_short"),
        "too_weak": "Password is too weak. Please use a stronger password",
        "mismatch": "Passwords do not match",
    },
    "name": {
        "required": "Name is required",
        "too_short": "Name must be at least 2 characters",
        "too_long": "Name must not exceed 100 characters",
        "invalid_characters": "Name contains invalid characters",
    },
    "institution": {
        "required": "Institution is required",
        "not_found": "Institution not found in our database",
        "not_verified": "Institution is not verified",
    },
    "role": {
        "invalid": "Invalid role specified",
        "not_assignable": "This role cannot be assigned",
        "insufficient_level": "You cannot assign this role level",
    },
}


def get_validation_message(field: str, error_type: str) -> str:
    """
    Get validation message for a specific field and error type.
    
    Args:
        field: Field name
        error_type: Type of validation error
        
    Returns:
        Validation error message
    """
    field_messages = VALIDATION_MESSAGES.get(field, {})
    return field_messages.get(error_type, f"Invalid {field}")


# Security-conscious error messages that don't leak information
SECURE_ERROR_MESSAGES = {
    "login_failed": "Invalid email or password",  # Don't reveal if email exists
    "account_not_found": "Invalid email or password",  # Same as above
    "token_invalid": "Authentication failed",  # Don't reveal token details
    "permission_denied": "Access denied",  # Don't reveal what resource
    "resource_not_found": "Not found",  # Don't reveal if it exists for others
}