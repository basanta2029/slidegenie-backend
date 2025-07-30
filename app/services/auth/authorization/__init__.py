"""
Authorization and RBAC system for SlideGenie.

This module provides role-based access control (RBAC) and resource-based 
permissions for the SlideGenie platform, focusing on academic presentation
management and institutional access controls.
"""

from .api_keys import APIKeyService, APIKeyManager
from .authorization import AuthorizationService, AuthorizationContext, AuthorizationResult
from .decorators import (
    require_permissions,
    require_roles,
    require_api_key,
    require_ownership,
    require_institutional_access,
)
from .permissions import (
    Permission,
    PermissionChecker,
    ResourcePermission,
    PermissionRegistry,
)
from .policies import PolicyEngine, PolicyRule, PolicyContext
from .rbac import RoleManager, Role, RoleHierarchy

__all__ = [
    # Core services
    "AuthorizationService",
    "RoleManager", 
    "PermissionChecker",
    "APIKeyService",
    "APIKeyManager",
    "PolicyEngine",
    
    # Models
    "Role",
    "Permission",
    "ResourcePermission",
    "PolicyRule",
    "PolicyContext",
    "RoleHierarchy",
    "PermissionRegistry",
    "AuthorizationContext",
    "AuthorizationResult",
    
    # Decorators
    "require_permissions",
    "require_roles",
    "require_api_key",
    "require_ownership",
    "require_institutional_access",
]