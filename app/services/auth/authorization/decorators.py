"""
Authorization decorators for FastAPI endpoints.

Provides permission-based access control decorators for protecting API endpoints
with role, permission, and ownership checks.
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.schemas.auth import UserRead
from app.infrastructure.database.models import User
from app.services.auth.token_service import TokenService

from .api_keys import api_key_manager
from .permissions import PermissionAction, PermissionChecker, ResourceType
from .rbac import role_manager

logger = structlog.get_logger(__name__)

# Security schemes
bearer_scheme = HTTPBearer()
api_key_scheme = HTTPBearer(scheme_name="ApiKey")


class AuthorizationError(HTTPException):
    """Authorization-specific exception."""
    
    def __init__(
        self,
        detail: str = "Not authorized to access this resource",
        status_code: int = status.HTTP_403_FORBIDDEN,
    ):
        super().__init__(status_code=status_code, detail=detail)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    token_service: TokenService = Depends(lambda: TokenService()),
) -> UserRead:
    """Get current authenticated user from bearer token."""
    try:
        # Validate token
        payload = await token_service.validate_access_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        
        # Get user from token payload
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # In a real implementation, fetch user from database
        # For now, return a basic user object
        user = UserRead(
            id=UUID(user_id),
            email=payload.get("email", ""),
            full_name=payload.get("full_name", ""),
            is_active=True,
            roles=payload.get("roles", ["user"]),
        )
        
        return user
        
    except Exception as e:
        logger.error("authentication_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        lambda auth=Depends(bearer_scheme): auth if auth else None
    ),
    token_service: TokenService = Depends(lambda: TokenService()),
) -> Optional[UserRead]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, token_service)
    except HTTPException:
        return None


def require_roles(
    required_roles: Union[str, List[str]],
    require_all: bool = False,
) -> Callable:
    """
    Require user to have specific roles.
    
    Args:
        required_roles: Single role or list of roles required
        require_all: If True, user must have all roles. If False, any role is sufficient
    
    Usage:
        @router.get("/admin")
        @require_roles("admin")
        async def admin_endpoint(user: UserRead = Depends(get_current_user)):
            return {"message": "Admin access granted"}
        
        @router.get("/faculty")
        @require_roles(["faculty", "professor"], require_all=False)
        async def faculty_endpoint(user: UserRead = Depends(get_current_user)):
            return {"message": "Faculty access granted"}
    """
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    async def role_checker(user: UserRead = Depends(get_current_user)) -> UserRead:
        user_roles = set(user.roles)
        required_set = set(required_roles)
        
        if require_all:
            # User must have all required roles
            if not required_set.issubset(user_roles):
                missing = required_set - user_roles
                logger.warning(
                    "insufficient_roles",
                    user_id=str(user.id),
                    required=list(required_set),
                    missing=list(missing),
                )
                raise AuthorizationError(
                    detail=f"Missing required roles: {', '.join(missing)}"
                )
        else:
            # User must have at least one required role
            if not user_roles.intersection(required_set):
                logger.warning(
                    "no_matching_roles",
                    user_id=str(user.id),
                    required=list(required_set),
                    user_roles=list(user_roles),
                )
                raise AuthorizationError(
                    detail=f"Requires one of these roles: {', '.join(required_roles)}"
                )
        
        return user
    
    return role_checker


def require_permissions(
    permissions: Union[str, List[tuple[PermissionAction, ResourceType]]],
    require_all: bool = True,
    checker: Optional[PermissionChecker] = None,
) -> Callable:
    """
    Require user to have specific permissions.
    
    Args:
        permissions: Permission string(s) or list of (action, resource) tuples
        require_all: If True, user must have all permissions. If False, any permission is sufficient
        checker: Optional PermissionChecker instance
    
    Usage:
        @router.post("/presentations")
        @require_permissions("create:presentation")
        async def create_presentation(user: UserRead = Depends(get_current_user)):
            return {"message": "Can create presentations"}
        
        @router.delete("/presentations/{id}")
        @require_permissions([
            (PermissionAction.DELETE, ResourceType.PRESENTATION),
            (PermissionAction.MANAGE, ResourceType.PRESENTATION)
        ], require_all=False)
        async def delete_presentation(id: UUID, user: UserRead = Depends(get_current_user)):
            return {"message": "Can delete presentation"}
    """
    # Normalize permissions to list of tuples
    if isinstance(permissions, str):
        # Parse permission string (e.g., "create:presentation")
        parts = permissions.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid permission format: {permissions}")
        permissions = [(PermissionAction(parts[0]), ResourceType(parts[1]))]
    elif not isinstance(permissions, list):
        permissions = [permissions]
    
    async def permission_checker(
        user: UserRead = Depends(get_current_user),
        request: Request = None,
    ) -> UserRead:
        # Get user's effective permissions from roles
        user_permissions = role_manager.get_user_effective_permissions(user.roles)
        
        # Check permissions
        has_permissions = []
        for action, resource in permissions:
            perm_key = f"{action}:{resource}"
            has_perm = perm_key in user_permissions
            has_permissions.append(has_perm)
            
            if not has_perm:
                logger.debug(
                    "permission_check_failed",
                    user_id=str(user.id),
                    permission=perm_key,
                    user_permissions=list(user_permissions),
                )
        
        if require_all and not all(has_permissions):
            missing = [
                f"{action}:{resource}"
                for (action, resource), has_perm in zip(permissions, has_permissions)
                if not has_perm
            ]
            raise AuthorizationError(
                detail=f"Missing required permissions: {', '.join(missing)}"
            )
        elif not require_all and not any(has_permissions):
            required = [f"{action}:{resource}" for action, resource in permissions]
            raise AuthorizationError(
                detail=f"Requires one of these permissions: {', '.join(required)}"
            )
        
        return user
    
    return permission_checker


def require_api_key(
    required_scopes: Optional[List[str]] = None,
) -> Callable:
    """
    Require valid API key with optional scope requirements.
    
    Args:
        required_scopes: List of required API key scopes
    
    Usage:
        @router.get("/api/presentations")
        @require_api_key(["read:presentations"])
        async def list_presentations(request: Request):
            api_key = request.state.api_key
            return {"user_id": str(api_key.user_id)}
    """
    async def api_key_checker(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(api_key_scheme),
    ) -> Dict[str, Any]:
        # Get client info
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Authenticate API key
        success, api_key, error = await api_key_manager.authenticate_request(
            api_key=credentials.credentials,
            required_scopes=required_scopes or [],
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        if not success:
            error_msg = error.get("error", "API key authentication failed")
            logger.warning(
                "api_key_auth_failed",
                error=error_msg,
                ip_address=ip_address,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Store API key in request state for access in endpoint
        request.state.api_key = api_key
        
        return {"api_key": api_key, "user_id": api_key.user_id}
    
    return api_key_checker


def require_ownership(
    resource_type: ResourceType,
    get_resource_id: Optional[Callable] = None,
    allow_roles: Optional[List[str]] = None,
) -> Callable:
    """
    Require user to be owner of resource or have bypass roles.
    
    Args:
        resource_type: Type of resource being accessed
        get_resource_id: Function to extract resource ID from request
        allow_roles: Roles that bypass ownership check (e.g., admin)
    
    Usage:
        @router.put("/presentations/{presentation_id}")
        @require_ownership(
            ResourceType.PRESENTATION,
            allow_roles=["admin", "moderator"]
        )
        async def update_presentation(
            presentation_id: UUID,
            user: UserRead = Depends(get_current_user)
        ):
            return {"message": "Can update presentation"}
    """
    if allow_roles is None:
        allow_roles = ["admin", "institutional_admin"]
    
    async def ownership_checker(
        request: Request,
        user: UserRead = Depends(get_current_user),
    ) -> UserRead:
        # Check if user has bypass role
        if any(role in user.roles for role in allow_roles):
            logger.debug(
                "ownership_check_bypassed",
                user_id=str(user.id),
                roles=user.roles,
            )
            return user
        
        # Get resource ID
        if get_resource_id:
            resource_id = await get_resource_id(request)
        else:
            # Try to get from path parameters
            resource_id = request.path_params.get(f"{resource_type}_id")
            if not resource_id:
                resource_id = request.path_params.get("id")
        
        if not resource_id:
            raise ValueError(f"Could not determine {resource_type} ID")
        
        # In a real implementation, check ownership in database
        # For now, we'll simulate this check
        logger.info(
            "ownership_check",
            user_id=str(user.id),
            resource_type=resource_type,
            resource_id=str(resource_id),
        )
        
        # Simulated ownership check (would query database)
        # For demo, assume user owns their own resources
        is_owner = True  # This would be determined by database query
        
        if not is_owner:
            logger.warning(
                "ownership_check_failed",
                user_id=str(user.id),
                resource_type=resource_type,
                resource_id=str(resource_id),
            )
            raise AuthorizationError(
                detail=f"You do not have access to this {resource_type}"
            )
        
        return user
    
    return ownership_checker


def require_institutional_access(
    check_admin: bool = True,
    check_same_institution: bool = True,
) -> Callable:
    """
    Require user to have institutional access to resource.
    
    Args:
        check_admin: Allow institutional admins
        check_same_institution: Require same institution membership
    
    Usage:
        @router.get("/institutions/{institution_id}/analytics")
        @require_institutional_access()
        async def get_institution_analytics(
            institution_id: UUID,
            user: UserRead = Depends(get_current_user)
        ):
            return {"message": "Institution analytics"}
    """
    async def institutional_checker(
        request: Request,
        user: UserRead = Depends(get_current_user),
    ) -> UserRead:
        # Get institution ID from path
        institution_id = request.path_params.get("institution_id")
        if not institution_id:
            raise ValueError("No institution_id in path")
        
        # Check if user is institutional admin
        if check_admin and "institutional_admin" in user.roles:
            # In real implementation, verify admin is for THIS institution
            logger.debug(
                "institutional_admin_access",
                user_id=str(user.id),
                institution_id=str(institution_id),
            )
            return user
        
        # Check if user belongs to institution
        if check_same_institution:
            # In real implementation, check user's institution_id
            user_institution_id = getattr(user, "institution_id", None)
            if user_institution_id != institution_id:
                logger.warning(
                    "institutional_access_denied",
                    user_id=str(user.id),
                    user_institution=str(user_institution_id),
                    requested_institution=str(institution_id),
                )
                raise AuthorizationError(
                    detail="You do not have access to this institution"
                )
        
        return user
    
    return institutional_checker


# Composite decorators for common patterns
def require_admin() -> Callable:
    """Shortcut for requiring admin role."""
    return require_roles(["admin", "super_admin"], require_all=False)


def require_academic_staff() -> Callable:
    """Shortcut for requiring academic staff roles."""
    return require_roles(
        ["faculty", "professor", "researcher", "department_admin"],
        require_all=False
    )


def require_premium_features() -> Callable:
    """Shortcut for requiring premium user access."""
    return require_roles(
        ["premium_user", "researcher", "faculty", "professor"],
        require_all=False
    )


# Export all decorators
__all__ = [
    "get_current_user",
    "get_optional_user",
    "require_roles",
    "require_permissions",
    "require_api_key",
    "require_ownership",
    "require_institutional_access",
    "require_admin",
    "require_academic_staff",
    "require_premium_features",
    "AuthorizationError",
]