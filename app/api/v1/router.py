"""
API v1 router configuration.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    academic,
    auth,
    generation,
    health,
    oauth,
    presentations,
    templates,
    users,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(academic.router, prefix="/academic", tags=["academic"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(presentations.router, prefix="/presentations", tags=["presentations"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])