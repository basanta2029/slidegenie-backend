"""
Role-Based Access Control (RBAC) system for SlideGenie.

Manages roles, role hierarchies, and role-permission mappings with academic
focus and institutional management capabilities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import structlog
from pydantic import BaseModel, Field

from .permissions import Permission, PermissionAction, ResourceType, permission_registry

logger = structlog.get_logger(__name__)


class RoleType(str, Enum):
    """Built-in role types for SlideGenie."""
    # Basic user roles
    USER = "user"
    PREMIUM_USER = "premium_user"
    
    # Academic roles
    STUDENT = "student"
    RESEARCHER = "researcher" 
    FACULTY = "faculty"
    PROFESSOR = "professor"
    
    # Institutional roles
    DEPARTMENT_ADMIN = "department_admin"
    INSTITUTIONAL_ADMIN = "institutional_admin"
    
    # System roles
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    
    # API roles
    API_USER = "api_user"
    API_ADMIN = "api_admin"


class Role(BaseModel):
    """Role model with permissions and metadata."""
    name: str
    display_name: str
    description: Optional[str] = None
    role_type: RoleType
    permissions: Set[str] = Field(default_factory=set)  # Permission keys
    is_system_role: bool = True
    is_assignable: bool = True
    level: int = 0  # Hierarchy level (higher = more privileges)
    parent_roles: Set[str] = Field(default_factory=set)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_permission(self, permission_key: str) -> None:
        """Add permission to role."""
        self.permissions.add(permission_key)
        logger.debug("permission_added_to_role", role=self.name, permission=permission_key)
    
    def remove_permission(self, permission_key: str) -> None:
        """Remove permission from role."""
        self.permissions.discard(permission_key)
        logger.debug("permission_removed_from_role", role=self.name, permission=permission_key)
    
    def has_permission(self, permission_key: str) -> bool:
        """Check if role has specific permission."""
        return permission_key in self.permissions
    
    def inherits_from(self, parent_role: str) -> bool:
        """Check if role inherits from parent role."""
        return parent_role in self.parent_roles
    
    def get_all_permissions(self, role_manager: RoleManager) -> Set[str]:
        """Get all permissions including inherited ones."""
        all_permissions = self.permissions.copy()
        
        # Add permissions from parent roles
        for parent_name in self.parent_roles:
            parent_role = role_manager.get_role(parent_name)
            if parent_role:
                all_permissions.update(parent_role.get_all_permissions(role_manager))
        
        return all_permissions


class RoleHierarchy:
    """Manages role hierarchy and inheritance."""
    
    def __init__(self):
        self._hierarchy: Dict[str, Set[str]] = {}  # role -> parent roles
        self._reverse_hierarchy: Dict[str, Set[str]] = {}  # role -> child roles
    
    def add_inheritance(self, child_role: str, parent_role: str) -> None:
        """Add inheritance relationship."""
        if child_role not in self._hierarchy:
            self._hierarchy[child_role] = set()
        self._hierarchy[child_role].add(parent_role)
        
        if parent_role not in self._reverse_hierarchy:
            self._reverse_hierarchy[parent_role] = set()
        self._reverse_hierarchy[parent_role].add(child_role)
        
        logger.debug("role_inheritance_added", child=child_role, parent=parent_role)
    
    def remove_inheritance(self, child_role: str, parent_role: str) -> None:
        """Remove inheritance relationship."""
        if child_role in self._hierarchy:
            self._hierarchy[child_role].discard(parent_role)
        
        if parent_role in self._reverse_hierarchy:
            self._reverse_hierarchy[parent_role].discard(child_role)
        
        logger.debug("role_inheritance_removed", child=child_role, parent=parent_role)
    
    def get_parent_roles(self, role: str) -> Set[str]:
        """Get direct parent roles."""
        return self._hierarchy.get(role, set()).copy()
    
    def get_child_roles(self, role: str) -> Set[str]:
        """Get direct child roles."""
        return self._reverse_hierarchy.get(role, set()).copy()
    
    def get_all_parent_roles(self, role: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """Get all parent roles (including inherited)."""
        if visited is None:
            visited = set()
        
        if role in visited:  # Prevent infinite recursion
            return set()
        
        visited.add(role)
        all_parents = self._hierarchy.get(role, set()).copy()
        
        # Recursively get parents of parents
        for parent in list(all_parents):
            all_parents.update(self.get_all_parent_roles(parent, visited))
        
        return all_parents
    
    def get_all_child_roles(self, role: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """Get all child roles (including inherited)."""
        if visited is None:
            visited = set()
        
        if role in visited:  # Prevent infinite recursion
            return set()
        
        visited.add(role)
        all_children = self._reverse_hierarchy.get(role, set()).copy()
        
        # Recursively get children of children
        for child in list(all_children):
            all_children.update(self.get_all_child_roles(child, visited))
        
        return all_children
    
    def has_circular_dependency(self, child_role: str, parent_role: str) -> bool:
        """Check if adding inheritance would create circular dependency."""
        # If parent_role is already a child of child_role, it would create a cycle
        return child_role in self.get_all_parent_roles(parent_role)


class RoleManager:
    """Manages roles, permissions, and role assignments."""
    
    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._hierarchy = RoleHierarchy()
        self._initialize_default_roles()
    
    def _initialize_default_roles(self) -> None:
        """Initialize system default roles."""
        # Basic user role
        user_role = Role(
            name="user",
            display_name="User",
            description="Basic user with presentation creation capabilities",
            role_type=RoleType.USER,
            level=1,
            permissions={
                "create:presentation", "read:presentation", "update:presentation", 
                "delete:presentation", "export:presentation", "share:presentation",
                "create:slide", "read:slide", "update:slide", "delete:slide",
                "read:template", "update:profile", "manage:api_key",
                "create:generation_job", "read:generation_job", "execute:ai_model",
                "create:comment", "read:comment",
            }
        )
        
        # Premium user role
        premium_user_role = Role(
            name="premium_user",
            display_name="Premium User", 
            description="Premium user with additional features",
            role_type=RoleType.PREMIUM_USER,
            level=2,
            parent_roles={"user"},
            permissions={
                "create:template", "update:template", "import:presentation",
                "manage:collaboration",
            }
        )
        
        # Student role
        student_role = Role(
            name="student",
            display_name="Student",
            description="Academic student with basic presentation features",
            role_type=RoleType.STUDENT,
            level=2,
            parent_roles={"user"},
            permissions=set()  # Inherits from user
        )
        
        # Researcher role
        researcher_role = Role(
            name="researcher",
            display_name="Researcher",
            description="Academic researcher with advanced features",
            role_type=RoleType.RESEARCHER,
            level=3,
            parent_roles={"premium_user"},
            permissions={
                "read:analytics", "manage:template",
            }
        )
        
        # Faculty role
        faculty_role = Role(
            name="faculty",
            display_name="Faculty",
            description="Faculty member with teaching and research capabilities",
            role_type=RoleType.FACULTY,
            level=4,
            parent_roles={"researcher"},
            permissions={
                "read:department", "manage:collaboration",
            }
        )
        
        # Professor role
        professor_role = Role(
            name="professor",
            display_name="Professor",
            description="Professor with full academic privileges",
            role_type=RoleType.PROFESSOR,
            level=5,
            parent_roles={"faculty"},
            permissions={
                "manage:department",
            }
        )
        
        # Department admin role
        dept_admin_role = Role(
            name="department_admin",
            display_name="Department Administrator",
            description="Department administrator with management capabilities",
            role_type=RoleType.DEPARTMENT_ADMIN,
            level=6,
            parent_roles={"professor"},
            permissions={
                "read:user", "manage:department", "read:analytics",
            }
        )
        
        # Institutional admin role
        institutional_admin_role = Role(
            name="institutional_admin",
            display_name="Institutional Administrator",
            description="Institution administrator with full institutional access",
            role_type=RoleType.INSTITUTIONAL_ADMIN,
            level=7,
            parent_roles={"department_admin"},
            permissions={
                "read:institution", "manage:institution", "read:audit_log",
            }
        )
        
        # Moderator role
        moderator_role = Role(
            name="moderator",
            display_name="Moderator",
            description="System moderator with content management capabilities",
            role_type=RoleType.MODERATOR,
            level=8,
            parent_roles={"institutional_admin"},
            permissions={
                "delete:comment", "update:comment", "read:audit_log",
            }
        )
        
        # Admin role
        admin_role = Role(
            name="admin",
            display_name="Administrator",
            description="System administrator with full system access",
            role_type=RoleType.ADMIN,
            level=9,
            parent_roles={"moderator"},
            permissions={
                "admin:system", "read:analytics", "manage:template",
                "delete:presentation", "delete:template",
            }
        )
        
        # Super admin role
        super_admin_role = Role(
            name="super_admin",
            display_name="Super Administrator",
            description="Super administrator with unrestricted access",
            role_type=RoleType.SUPER_ADMIN,
            level=10,
            parent_roles={"admin"},
            permissions={
                "admin:system", "manage:institution", "delete:user",
            }
        )
        
        # API roles
        api_user_role = Role(
            name="api_user",
            display_name="API User",
            description="API access for programmatic usage",
            role_type=RoleType.API_USER,
            level=1,
            permissions={
                "read:presentation", "create:presentation", "update:presentation",
                "read:template", "create:generation_job",
            }
        )
        
        api_admin_role = Role(
            name="api_admin",
            display_name="API Administrator",
            description="Administrative API access",
            role_type=RoleType.API_ADMIN,
            level=8,
            parent_roles={"api_user"},
            permissions={
                "delete:presentation", "manage:template", "read:analytics",
                "admin:system",
            }
        )
        
        # Register all roles
        roles = [
            user_role, premium_user_role, student_role, researcher_role,
            faculty_role, professor_role, dept_admin_role, institutional_admin_role,
            moderator_role, admin_role, super_admin_role, api_user_role, api_admin_role,
        ]
        
        for role in roles:
            self.create_role(role)
    
    def create_role(self, role: Role) -> None:
        """Create a new role."""
        self._roles[role.name] = role
        
        # Set up inheritance
        for parent_name in role.parent_roles:
            self._hierarchy.add_inheritance(role.name, parent_name)
        
        logger.info("role_created", name=role.name, level=role.level)
    
    def get_role(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return self._roles.get(name)
    
    def get_all_roles(self) -> List[Role]:
        """Get all roles."""
        return list(self._roles.values())
    
    def get_assignable_roles(self) -> List[Role]:
        """Get roles that can be assigned to users."""
        return [role for role in self._roles.values() if role.is_assignable]
    
    def delete_role(self, name: str) -> bool:
        """Delete a role."""
        if name not in self._roles:
            return False
        
        role = self._roles[name]
        if role.is_system_role:
            logger.warning("attempted_to_delete_system_role", name=name)
            return False
        
        # Remove from hierarchy
        for parent in role.parent_roles:
            self._hierarchy.remove_inheritance(name, parent)
        
        for child in self._hierarchy.get_child_roles(name):
            self._hierarchy.remove_inheritance(child, name)
        
        del self._roles[name]
        logger.info("role_deleted", name=name)
        return True
    
    def add_permission_to_role(self, role_name: str, permission_key: str) -> bool:
        """Add permission to role."""
        role = self.get_role(role_name)
        if not role:
            return False
        
        # Verify permission exists
        if not permission_registry.get_permission(permission_key):
            logger.warning("unknown_permission", key=permission_key)
            return False
        
        role.add_permission(permission_key)
        return True
    
    def remove_permission_from_role(self, role_name: str, permission_key: str) -> bool:
        """Remove permission from role."""
        role = self.get_role(role_name)
        if not role:
            return False
        
        role.remove_permission(permission_key)
        return True
    
    def get_user_effective_permissions(self, user_roles: List[str]) -> Set[str]:
        """Get all effective permissions for user based on their roles."""
        all_permissions = set()
        
        for role_name in user_roles:
            role = self.get_role(role_name)
            if role:
                all_permissions.update(role.get_all_permissions(self))
        
        return all_permissions
    
    def user_has_permission(self, user_roles: List[str], permission_key: str) -> bool:
        """Check if user has specific permission based on roles."""
        effective_permissions = self.get_user_effective_permissions(user_roles)
        return permission_key in effective_permissions
    
    def get_role_hierarchy(self) -> Dict[str, Any]:
        """Get role hierarchy structure."""
        hierarchy = {}
        
        for role_name, role in self._roles.items():
            hierarchy[role_name] = {
                "level": role.level,
                "parents": list(role.parent_roles),
                "children": list(self._hierarchy.get_child_roles(role_name)),
                "permissions": len(role.permissions),
                "effective_permissions": len(role.get_all_permissions(self)),
            }
        
        return hierarchy
    
    def validate_role_assignment(
        self, 
        user_roles: List[str], 
        assigner_roles: List[str]
    ) -> bool:
        """Validate if assigner can assign roles to user."""
        # Get maximum level of assigner
        max_assigner_level = 0
        for role_name in assigner_roles:
            role = self.get_role(role_name)
            if role:
                max_assigner_level = max(max_assigner_level, role.level)
        
        # Check if all user roles are at or below assigner level
        for role_name in user_roles:
            role = self.get_role(role_name)
            if role and role.level >= max_assigner_level:
                return False
        
        return True
    
    def suggest_roles_for_academic_position(self, position: str, institution_type: str) -> List[str]:
        """Suggest appropriate roles based on academic position."""
        position_lower = position.lower()
        suggestions = []
        
        if "student" in position_lower:
            suggestions.append("student")
        elif any(term in position_lower for term in ["professor", "prof"]):
            suggestions.append("professor")
        elif any(term in position_lower for term in ["faculty", "instructor", "lecturer"]):
            suggestions.append("faculty")
        elif any(term in position_lower for term in ["researcher", "scientist", "postdoc"]):
            suggestions.append("researcher")
        elif "admin" in position_lower:
            if "department" in position_lower:
                suggestions.append("department_admin")
            else:
                suggestions.append("institutional_admin")
        else:
            suggestions.append("user")
        
        # Add premium for non-students at universities
        if "university" in institution_type.lower() and "student" not in suggestions:
            suggestions.append("premium_user")
        
        return suggestions


# Global role manager instance
role_manager = RoleManager()