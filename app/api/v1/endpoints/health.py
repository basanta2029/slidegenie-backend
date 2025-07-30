"""
Health check endpoints.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.cache.redis import get_redis
from app.infrastructure.database.base import get_db

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "slidegenie-api",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Readiness check including database and cache.
    
    Returns:
        Readiness status with component health
    """
    components = {
        "api": "healthy",
        "database": "unknown",
        "cache": "unknown",
    }
    
    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        components["database"] = "healthy"
    except Exception:
        components["database"] = "unhealthy"
    
    # Check Redis
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        components["cache"] = "healthy"
    except Exception:
        components["cache"] = "unhealthy"
    
    # Overall status
    all_healthy = all(status == "healthy" for status in components.values())
    
    return {
        "status": "ready" if all_healthy else "not ready",
        "components": components,
    }