"""
SlideGenie API - Main application entry point.
"""
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, log_request_details, setup_logging
from app.infrastructure.database.base import engine

# Setup logging
setup_logging()
logger = get_logger(__name__)


# Initialize Sentry if configured
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            SqlalchemyIntegration(),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    # Startup
    logger.info(
        "Starting SlideGenie API",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    
    # Initialize database
    # Note: In production, use Alembic migrations instead
    if settings.is_development:
        from app.infrastructure.database.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown
    logger.info("Shutting down SlideGenie API")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if not settings.is_production else None,
    docs_url=f"{settings.API_V1_PREFIX}/docs" if not settings.is_production else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request."""
    request_id = request.headers.get("X-Request-ID", str(time.time_ns()))
    
    # Bind request ID to logging context
    clear_contextvars()
    bind_contextvars(request_id=request_id)
    
    # Add to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        **log_request_details(
            request_id=request.headers.get("X-Request-ID", ""),
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        ),
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log response
    logger.info(
        "Request completed",
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )
    
    return response


# Add Sentry middleware if configured
if settings.SENTRY_DSN:
    app.add_middleware(SentryAsgiMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        path=request.url.path,
        method=request.method,
    )
    
    # Don't expose internal errors in production
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred"},
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Health status and application info
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs" if not settings.is_production else "Disabled in production",
    }