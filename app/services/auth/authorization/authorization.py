"""
Main authorization service for SlideGenie.

Coordinates RBAC, permissions, policies, and API key management to provide
a unified authorization interface.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

import structlog
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User
from app.services.auth.token_service import TokenService

from .api_keys import APIKeyService, APIKeyTier
from .permissions import (
    PermissionAction,
    PermissionChecker,
    ResourcePermission,
    ResourceType,
)
from .rbac import RoleManager, RoleType

logger = structlog.get_logger(__name__)


class AuthorizationContext(BaseModel):
    """Context for authorization decisions."""
    user_id: UUID
    user_roles: List[str] = Field(default_factory=list)
    user_email: str
    institution_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    resource_type: Optional[ResourceType] = None
    resource_owner_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    api_key_id: Optional[UUID] = None
    request_metadata: Dict[str, Any] = Field(default_factory=dict)


class AuthorizationResult(BaseModel):
    """Result of authorization check."""
    allowed: bool
    reason: Optional[str] = None
    context: Optional[AuthorizationContext] = None
    applied_policies: List[str] = Field(default_factory=list)
    effective_permissions: Set[str] = Field(default_factory=set)
    
    @property
    def denied(self) -> bool:
        """Check if authorization was denied."""
        return not self.allowed


class AuthorizationService:
    """
    Main authorization service coordinating all authorization components.
    
    This service provides a unified interface for:
    - Role-based access control (RBAC)
    - Resource-based permissions
    - Policy evaluation
    - API key management
    - Audit logging
    """
    
    def __init__(
        self,
        role_manager: Optional[RoleManager] = None,
        permission_checker: Optional[PermissionChecker] = None,
        api_key_service: Optional[APIKeyService] = None,
        token_service: Optional[TokenService] = None,
    ):
        self.role_manager = role_manager or RoleManager()
        self.permission_checker = permission_checker or PermissionChecker()
        self.api_key_service = api_key_service or APIKeyService()
        self.token_service = token_service or TokenService()
    
    async def authorize(
        self,
        context: AuthorizationContext,
        action: PermissionAction,
        resource: ResourceType,
        db: Optional[AsyncSession] = None,
    ) -> AuthorizationResult:
        """
        Main authorization method.
        
        Args:
            context: Authorization context with user and request info
            action: Action to perform
            resource: Resource type
            db: Optional database session
        
        Returns:
            AuthorizationResult with decision and metadata
        """
        # Start with basic result
        result = AuthorizationResult(
            allowed=False,
            context=context,
        )
        
        try:
            # 1. Check if user is active
            if not await self._check_user_active(context.user_id, db):
                result.reason = "User account is not active"
                return result
            
            # 2. Get effective permissions from roles
            effective_permissions = self.role_manager.get_user_effective_permissions(
                context.user_roles
            )
            result.effective_permissions = effective_permissions
            
            # 3. Check basic permission
            permission_key = f"{action}:{resource}"
            if permission_key in effective_permissions:
                result.allowed = True
                result.reason = f"User has {permission_key} permission from roles"
                result.applied_policies.append("role_based_permission")
                return result
            
            # 4. Check ownership-based permissions
            if await self._check_ownership_permission(context, action, resource):
                result.allowed = True
                result.reason = "User is resource owner"
                result.applied_policies.append("ownership_permission")
                return result
            
            # 5. Check institutional permissions
            if await self._check_institutional_permission(context, action, resource):
                result.allowed = True
                result.reason = "User has institutional access"
                result.applied_policies.append("institutional_permission")
                return result
            
            # 6. Check department permissions
            if await self._check_department_permission(context, action, resource):
                result.allowed = True
                result.reason = "User has department access"
                result.applied_policies.append("department_permission")
                return result
            
            # 7. Apply special policies for academic users
            if await self._check_academic_policies(context, action, resource):
                result.allowed = True
                result.reason = "Academic policy grants access"
                result.applied_policies.append("academic_policy")
                return result
            
            # Default deny
            result.reason = f"No permission for {permission_key}"
            
        except Exception as e:
            logger.error(
                "authorization_error",
                error=str(e),
                user_id=str(context.user_id),
                action=action,
                resource=resource,
            )
            result.reason = "Authorization check failed"
        
        finally:
            # Log authorization decision
            logger.info(
                "authorization_decision",
                user_id=str(context.user_id),
                action=action,
                resource=resource,
                allowed=result.allowed,
                reason=result.reason,
                policies=result.applied_policies,
            )
        
        return result
    
    async def authorize_batch(
        self,
        context: AuthorizationContext,
        permissions: List[tuple[PermissionAction, ResourceType]],
        require_all: bool = True,
        db: Optional[AsyncSession] = None,
    ) -> AuthorizationResult:
        """
        Authorize multiple permissions at once.
        
        Args:
            context: Authorization context
            permissions: List of (action, resource) tuples
            require_all: If True, all permissions must be allowed
            db: Optional database session
        
        Returns:
            AuthorizationResult with combined decision
        """
        results = []
        
        for action, resource in permissions:
            result = await self.authorize(context, action, resource, db)
            results.append(result)
        
        if require_all:
            allowed = all(r.allowed for r in results)
            reason = "All permissions granted" if allowed else "Some permissions denied"
        else:
            allowed = any(r.allowed for r in results)
            reason = "At least one permission granted" if allowed else "No permissions granted"
        
        # Combine results
        combined_result = AuthorizationResult(
            allowed=allowed,
            reason=reason,
            context=context,
            applied_policies=list(set(
                policy for r in results for policy in r.applied_policies
            )),
            effective_permissions=set.union(
                *[r.effective_permissions for r in results]
            ),
        )
        
        return combined_result
    
    async def assign_role_to_user(
        self,
        user_id: UUID,
        role_name: str,
        assigner_id: UUID,
        assigner_roles: List[str],
        db: AsyncSession,
    ) -> bool:
        """
        Assign role to user with validation.
        
        Args:
            user_id: User to assign role to
            role_name: Role to assign
            assigner_id: User assigning the role
            assigner_roles: Roles of the assigner
            db: Database session
        
        Returns:
            True if role was assigned successfully
        """
        # Validate role exists
        role = self.role_manager.get_role(role_name)
        if not role:
            logger.warning("invalid_role_assignment", role=role_name)
            return False
        
        # Check if role is assignable
        if not role.is_assignable:
            logger.warning("non_assignable_role", role=role_name)
            return False
        
        # Validate assigner can assign this role
        if not self.role_manager.validate_role_assignment([role_name], assigner_roles):
            logger.warning(
                "insufficient_privileges_for_role_assignment",
                assigner_id=str(assigner_id),
                role=role_name,
            )
            return False
        
        # In real implementation, update user roles in database
        logger.info(
            "role_assigned",
            user_id=str(user_id),
            role=role_name,
            assigner_id=str(assigner_id),
        )
        
        return True
    
    async def revoke_role_from_user(
        self,
        user_id: UUID,
        role_name: str,
        revoker_id: UUID,
        revoker_roles: List[str],
        db: AsyncSession,
    ) -> bool:
        """
        Revoke role from user with validation.
        
        Args:
            user_id: User to revoke role from
            role_name: Role to revoke
            revoker_id: User revoking the role
            revoker_roles: Roles of the revoker
            db: Database session
        
        Returns:
            True if role was revoked successfully
        """
        # Validate revoker can revoke this role
        if not self.role_manager.validate_role_assignment([role_name], revoker_roles):
            logger.warning(
                "insufficient_privileges_for_role_revocation",
                revoker_id=str(revoker_id),
                role=role_name,
            )
            return False
        
        # In real implementation, update user roles in database
        logger.info(
            "role_revoked",
            user_id=str(user_id),
            role=role_name,
            revoker_id=str(revoker_id),
        )
        
        return True
    
    async def get_user_permissions(
        self,
        user_id: UUID,
        user_roles: List[str],
        resource_type: Optional[ResourceType] = None,
    ) -> Dict[str, Any]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User ID
            user_roles: User's roles
            resource_type: Optional filter by resource type
        
        Returns:
            Dictionary with permission information
        """
        # Get role-based permissions
        role_permissions = self.role_manager.get_user_effective_permissions(user_roles)
        
        # Filter by resource type if specified
        if resource_type:
            filtered_permissions = {
                perm for perm in role_permissions
                if perm.endswith(f":{resource_type}")
            }
        else:
            filtered_permissions = role_permissions
        
        # Get resource-specific permissions
        resource_permissions = await self.permission_checker.get_user_permissions(
            user_id, resource_type
        )
        
        return {
            "user_id": str(user_id),
            "roles": user_roles,
            "role_permissions": list(filtered_permissions),
            "resource_permissions": [
                {
                    "permission": rp.permission.key,
                    "resource_id": str(rp.resource_id) if rp.resource_id else None,
                    "expires_at": rp.expires_at.isoformat() if rp.expires_at else None,
                }
                for rp in resource_permissions
            ],
            "total_permissions": len(filtered_permissions) + len(resource_permissions),
        }
    
    async def suggest_roles_for_user(
        self,
        user_email: str,
        institution_domain: Optional[str] = None,
        academic_position: Optional[str] = None,
    ) -> List[str]:
        """
        Suggest appropriate roles based on user information.
        
        Args:
            user_email: User's email
            institution_domain: Institution email domain
            academic_position: User's academic position
        
        Returns:
            List of suggested role names
        """
        suggestions = []
        
        # Check if academic email
        if institution_domain and user_email.endswith(f"@{institution_domain}"):
            # Academic user
            if academic_position:
                suggestions.extend(
                    self.role_manager.suggest_roles_for_academic_position(
                        academic_position,
                        "university"
                    )
                )
            else:
                # Default academic user
                suggestions.append("student")
        else:
            # Non-academic user
            suggestions.append("user")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for role in suggestions:
            if role not in seen:
                seen.add(role)
                unique_suggestions.append(role)
        
        return unique_suggestions
    
    async def _check_user_active(
        self,
        user_id: UUID,
        db: Optional[AsyncSession]
    ) -> bool:
        """Check if user account is active."""
        # In real implementation, query database
        # For now, assume all users are active
        return True
    
    async def _check_ownership_permission(
        self,
        context: AuthorizationContext,
        action: PermissionAction,
        resource: ResourceType,
    ) -> bool:
        """Check ownership-based permissions."""
        # Owner can perform most actions on their resources
        if context.resource_owner_id == context.user_id:
            allowed_owner_actions = [
                PermissionAction.READ,
                PermissionAction.UPDATE,
                PermissionAction.DELETE,
                PermissionAction.SHARE,
                PermissionAction.EXPORT,
            ]
            return action in allowed_owner_actions
        
        return False
    
    async def _check_institutional_permission(
        self,
        context: AuthorizationContext,
        action: PermissionAction,
        resource: ResourceType,
    ) -> bool:
        """Check institutional-level permissions."""
        if "institutional_admin" not in context.user_roles:
            return False
        
        # Institutional admins can manage resources within their institution
        if context.institution_id == context.request_metadata.get("resource_institution_id"):
            allowed_actions = [
                PermissionAction.READ,
                PermissionAction.UPDATE,
                PermissionAction.DELETE,
                PermissionAction.MANAGE,
            ]
            return action in allowed_actions
        
        return False
    
    async def _check_department_permission(
        self,
        context: AuthorizationContext,
        action: PermissionAction,
        resource: ResourceType,
    ) -> bool:
        """Check department-level permissions."""
        if "department_admin" not in context.user_roles:
            return False
        
        # Department admins can manage resources within their department
        if context.department_id == context.request_metadata.get("resource_department_id"):
            allowed_actions = [
                PermissionAction.READ,
                PermissionAction.UPDATE,
                PermissionAction.MANAGE,
            ]
            return action in allowed_actions
        
        return False
    
    async def _check_academic_policies(
        self,
        context: AuthorizationContext,
        action: PermissionAction,
        resource: ResourceType,
    ) -> bool:
        """Apply special academic policies."""
        # Faculty can read student presentations in their courses
        if ("faculty" in context.user_roles or "professor" in context.user_roles):
            if (resource == ResourceType.PRESENTATION and 
                action == PermissionAction.READ and
                context.request_metadata.get("is_course_presentation")):
                return True
        
        # Researchers can access public academic resources
        if "researcher" in context.user_roles:
            if (action == PermissionAction.READ and
                context.request_metadata.get("is_public_academic")):
                return True
        
        return False
    
    def clear_permission_cache(self, user_id: Optional[UUID] = None) -> None:
        """Clear permission cache for user or all users."""
        self.permission_checker.clear_cache(user_id)
        logger.info("permission_cache_cleared", user_id=str(user_id) if user_id else "all")


# Global authorization service instance
authorization_service = AuthorizationService()