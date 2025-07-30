"""
Structured logging configuration using structlog.
"""
import logging
import sys
from typing import Any, Dict

import structlog
from structlog.contextvars import merge_contextvars

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )
    
    # Processors for development
    dev_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ]
    
    # Processors for production
    prod_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]
    
    # Choose processors based on environment
    processors = dev_processors if settings.is_development else prod_processors
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__ of the module)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


def log_request_details(
    request_id: str,
    method: str,
    path: str,
    client_ip: str | None = None,
    user_id: str | None = None,
) -> Dict[str, Any]:
    """
    Create a context dict for request logging.
    
    Args:
        request_id: Unique request identifier
        method: HTTP method
        path: Request path
        client_ip: Client IP address
        user_id: Authenticated user ID
        
    Returns:
        Context dictionary for logging
    """
    context = {
        "request_id": request_id,
        "method": method,
        "path": path,
    }
    
    if client_ip:
        context["client_ip"] = client_ip
    
    if user_id:
        context["user_id"] = user_id
    
    return context


def log_error_details(
    error: Exception,
    request_id: str | None = None,
    user_id: str | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Create a context dict for error logging.
    
    Args:
        error: Exception instance
        request_id: Request ID if available
        user_id: User ID if available
        **kwargs: Additional context
        
    Returns:
        Context dictionary for logging
    """
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **kwargs,
    }
    
    if request_id:
        context["request_id"] = request_id
    
    if user_id:
        context["user_id"] = user_id
    
    return context


def log_performance_metrics(
    operation: str,
    duration_ms: float,
    success: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Create a context dict for performance logging.
    
    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds
        success: Whether operation succeeded
        **kwargs: Additional metrics
        
    Returns:
        Context dictionary for logging
    """
    return {
        "operation": operation,
        "duration_ms": duration_ms,
        "success": success,
        **kwargs,
    }


# Export commonly used logger
logger = get_logger(__name__)