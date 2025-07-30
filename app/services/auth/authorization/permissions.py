"""
Permission system for SlideGenie RBAC.

Defines permissions, resource-based access controls, and permission checking
logic for academic presentation management.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class PermissionAction(str, Enum):
    """Standard CRUD+ actions for permissions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"
    SHARE = "share"
    EXPORT = "export"
    IMPORT = "import"
    ADMIN = "admin"


class ResourceType(str, Enum):
    """Resource types in SlideGenie."""
    # Core resources
    PRESENTATION = "presentation"
    SLIDE = "slide"
    TEMPLATE = "template"
    REFERENCE = "reference"
    
    # User management
    USER = "user"
    PROFILE = "profile"
    API_KEY = "api_key"
    
    # System resources
    SYSTEM = "system"
    ANALYTICS = "analytics"
    AUDIT_LOG = "audit_log"
    
    # Institutional resources
    INSTITUTION = "institution"
    DEPARTMENT = "department"
    GROUP = "group"
    
    # Generation resources
    GENERATION_JOB = "generation_job"
    AI_MODEL = "ai_model"
    
    # Collaboration
    COMMENT = "comment"
    SHARE = "share"
    COLLABORATION = "collaboration"


class Permission(BaseModel):
    """Individual permission model."""
    action: PermissionAction
    resource: ResourceType
    scope: Optional[str] = None  # Global, institution, department, user
    conditions: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def key(self) -> str:
        """Generate unique permission key."""
        base = f"{self.action}:{self.resource}"
        if self.scope:
            base += f":{self.scope}"
        return base
    
    @property
    def hash(self) -> str:
        """Generate permission hash for caching."""
        content = f"{self.key}:{sorted(self.conditions.items())}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def matches(self, action: str, resource: str, scope: Optional[str] = None) -> bool:
        """Check if permission matches given criteria."""
        return (
            self.action == action and
            self.resource == resource and
            (self.scope is None or self.scope == scope)
        )
    
    def __str__(self) -> str:
        return self.key


class ResourcePermission(BaseModel):
    """Resource-specific permission with metadata."""
    permission: Permission
    resource_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    institution_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    granted_by: Optional[UUID] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if permission has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def can_access_resource(self, resource_id: UUID, context: Dict[str, Any]) -> bool:
        """Check if permission allows access to specific resource."""
        if self.is_expired:
            return False
        
        # Global permissions allow access to all resources
        if not self.resource_id:
            return True
        
        # Specific resource permission
        if self.resource_id == resource_id:
            return True
        
        # Check ownership
        if self.owner_id and self.owner_id == context.get("user_id"):
            return True
        
        # Check institutional access
        if (self.institution_id and 
            self.institution_id == context.get("institution_id")):
            return True
        
        return False


class PermissionRegistry:
    """Registry of all available permissions in the system."""
    
    def __init__(self):
        self._permissions: Dict[str, Permission] = {}
        self._resource_permissions: Dict[ResourceType, List[Permission]] = {}
        self._initialize_default_permissions()
    
    def _initialize_default_permissions(self):
        """Initialize system default permissions."""
        # Presentation permissions
        self.register_permissions([
            # Presentation management
            Permission(action=PermissionAction.CREATE, resource=ResourceType.PRESENTATION),
            Permission(action=PermissionAction.READ, resource=ResourceType.PRESENTATION),
            Permission(action=PermissionAction.UPDATE, resource=ResourceType.PRESENTATION),
            Permission(action=PermissionAction.DELETE, resource=ResourceType.PRESENTATION),
            Permission(action=PermissionAction.SHARE, resource=ResourceType.PRESENTATION),
            Permission(action=PermissionAction.EXPORT, resource=ResourceType.PRESENTATION),
            
            # Slide management
            Permission(action=PermissionAction.CREATE, resource=ResourceType.SLIDE),
            Permission(action=PermissionAction.READ, resource=ResourceType.SLIDE),
            Permission(action=PermissionAction.UPDATE, resource=ResourceType.SLIDE),
            Permission(action=PermissionAction.DELETE, resource=ResourceType.SLIDE),
            
            # Template management
            Permission(action=PermissionAction.CREATE, resource=ResourceType.TEMPLATE),
            Permission(action=PermissionAction.READ, resource=ResourceType.TEMPLATE),
            Permission(action=PermissionAction.UPDATE, resource=ResourceType.TEMPLATE),
            Permission(action=PermissionAction.DELETE, resource=ResourceType.TEMPLATE),
            Permission(action=PermissionAction.MANAGE, resource=ResourceType.TEMPLATE),
            
            # User management
            Permission(action=PermissionAction.READ, resource=ResourceType.USER),
            Permission(action=PermissionAction.UPDATE, resource=ResourceType.PROFILE),
            Permission(action=PermissionAction.MANAGE, resource=ResourceType.API_KEY),
            
            # Institutional permissions
            Permission(action=PermissionAction.READ, resource=ResourceType.INSTITUTION),
            Permission(action=PermissionAction.MANAGE, resource=ResourceType.INSTITUTION),
            Permission(action=PermissionAction.READ, resource=ResourceType.DEPARTMENT),
            Permission(action=PermissionAction.MANAGE, resource=ResourceType.DEPARTMENT),
            
            # Generation permissions
            Permission(action=PermissionAction.CREATE, resource=ResourceType.GENERATION_JOB),
            Permission(action=PermissionAction.READ, resource=ResourceType.GENERATION_JOB),
            Permission(action=PermissionAction.EXECUTE, resource=ResourceType.AI_MODEL),
            
            # System permissions
            Permission(action=PermissionAction.READ, resource=ResourceType.ANALYTICS),
            Permission(action=PermissionAction.READ, resource=ResourceType.AUDIT_LOG),
            Permission(action=PermissionAction.ADMIN, resource=ResourceType.SYSTEM),
            
            # Collaboration permissions
            Permission(action=PermissionAction.CREATE, resource=ResourceType.COMMENT),
            Permission(action=PermissionAction.READ, resource=ResourceType.COMMENT),
            Permission(action=PermissionAction.UPDATE, resource=ResourceType.COMMENT),
            Permission(action=PermissionAction.DELETE, resource=ResourceType.COMMENT),
            Permission(action=PermissionAction.MANAGE, resource=ResourceType.COLLABORATION),
        ])
    
    def register_permission(self, permission: Permission) -> None:
        """Register a single permission."""
        self._permissions[permission.key] = permission
        
        if permission.resource not in self._resource_permissions:
            self._resource_permissions[permission.resource] = []
        self._resource_permissions[permission.resource].append(permission)
        
        logger.debug("permission_registered", key=permission.key)
    
    def register_permissions(self, permissions: List[Permission]) -> None:
        """Register multiple permissions."""
        for permission in permissions:
            self.register_permission(permission)
    
    def get_permission(self, key: str) -> Optional[Permission]:
        """Get permission by key."""
        return self._permissions.get(key)
    
    def get_permissions_for_resource(self, resource: ResourceType) -> List[Permission]:
        """Get all permissions for a resource type."""
        return self._resource_permissions.get(resource, [])
    
    def get_all_permissions(self) -> List[Permission]:
        """Get all registered permissions."""
        return list(self._permissions.values())
    
    def permission_exists(self, action: str, resource: str) -> bool:
        """Check if permission exists."""
        key = f"{action}:{resource}"
        return key in self._permissions


class PermissionChecker:
    """Service for checking user permissions."""
    
    def __init__(self, registry: Optional[PermissionRegistry] = None):
        self.registry = registry or PermissionRegistry()
        self._cache: Dict[str, bool] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def has_permission(
        self,
        user_id: UUID,
        action: PermissionAction,
        resource: ResourceType,
        resource_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if user has specific permission."""
        context = context or {}
        context["user_id"] = user_id
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            user_id, action, resource, resource_id, context
        )
        
        # Check cache first
        if cache_key in self._cache:
            logger.debug("permission_cache_hit", cache_key=cache_key)
            return self._cache[cache_key]
        
        # Perform permission check
        result = await self._check_permission(
            user_id, action, resource, resource_id, context
        )
        
        # Cache result
        self._cache[cache_key] = result
        
        logger.info(
            "permission_checked",
            user_id=str(user_id),
            action=action,
            resource=resource,
            resource_id=str(resource_id) if resource_id else None,
            result=result,
        )
        
        return result
    
    async def has_any_permission(
        self,
        user_id: UUID,
        permissions: List[tuple[PermissionAction, ResourceType]],
        resource_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if user has any of the specified permissions."""
        for action, resource in permissions:
            if await self.has_permission(user_id, action, resource, resource_id, context):
                return True
        return False
    
    async def has_all_permissions(
        self,
        user_id: UUID,
        permissions: List[tuple[PermissionAction, ResourceType]],
        resource_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if user has all specified permissions."""
        for action, resource in permissions:
            if not await self.has_permission(user_id, action, resource, resource_id, context):
                return False
        return True
    
    async def get_user_permissions(
        self,
        user_id: UUID,
        resource_type: Optional[ResourceType] = None,
    ) -> List[ResourcePermission]:
        """Get all permissions for a user."""
        # This would typically query the database for user permissions
        # For now, return empty list as placeholder
        logger.info("get_user_permissions_called", user_id=str(user_id))
        return []
    
    async def _check_permission(
        self,
        user_id: UUID,
        action: PermissionAction,
        resource: ResourceType,
        resource_id: Optional[UUID],
        context: Dict[str, Any],
    ) -> bool:
        """Internal permission checking logic."""
        # This is where the actual permission checking logic would be implemented
        # It would typically:
        # 1. Get user roles from database
        # 2. Get role permissions
        # 3. Check resource-specific permissions
        # 4. Apply policy rules
        # 5. Check ownership and institutional access
        
        # For now, return a basic implementation
        user_roles = context.get("user_roles", ["user"])
        
        # Basic role-based checks
        if "admin" in user_roles:
            return True
        
        if "institutional_admin" in user_roles:
            # Institutional admins can manage resources within their institution
            if context.get("institution_id") == context.get("user_institution_id"):
                return True
        
        # Ownership checks
        if resource_id and context.get("resource_owner_id") == user_id:
            return True
        
        # Default user permissions for their own resources
        if resource == ResourceType.PRESENTATION and action in [
            PermissionAction.CREATE, PermissionAction.READ, 
            PermissionAction.UPDATE, PermissionAction.EXPORT
        ]:
            return True
        
        if resource == ResourceType.SLIDE and action in [
            PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE
        ]:
            return True
        
        if resource == ResourceType.PROFILE and action == PermissionAction.UPDATE:
            return context.get("resource_owner_id") == user_id
        
        return False
    
    def _generate_cache_key(
        self,
        user_id: UUID,
        action: PermissionAction,
        resource: ResourceType,
        resource_id: Optional[UUID],
        context: Dict[str, Any],
    ) -> str:
        """Generate cache key for permission check."""
        base = f"perm:{user_id}:{action}:{resource}"
        if resource_id:
            base += f":{resource_id}"
        
        # Include relevant context in cache key
        context_items = sorted([
            (k, v) for k, v in context.items()
            if k in ["user_roles", "institution_id", "resource_owner_id"]
        ])
        if context_items:
            context_hash = hashlib.md5(str(context_items).encode()).hexdigest()[:8]
            base += f":{context_hash}"
        
        return base
    
    def clear_cache(self, user_id: Optional[UUID] = None) -> None:
        """Clear permission cache."""
        if user_id:
            # Clear cache for specific user
            keys_to_remove = [
                key for key in self._cache.keys()
                if key.startswith(f"perm:{user_id}:")
            ]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info("user_permission_cache_cleared", user_id=str(user_id))
        else:
            # Clear entire cache
            self._cache.clear()
            logger.info("permission_cache_cleared")


# Global permission registry instance
permission_registry = PermissionRegistry()