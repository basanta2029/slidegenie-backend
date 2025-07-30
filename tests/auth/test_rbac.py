"""
Comprehensive tests for Role-Based Access Control (RBAC) system.

Tests role management, permission inheritance, role hierarchies,
and academic-specific role assignments.
"""
import pytest
from typing import List, Set

from app.services.auth.authorization.rbac import (
    Role,
    RoleType,
    RoleHierarchy,
    RoleManager,
    role_manager,
)
from app.services.auth.authorization.permissions import (
    Permission,
    PermissionAction,
    ResourceType,
    permission_registry,
)


class TestRole:
    """Test Role model functionality."""
    
    def test_role_creation(self):
        """Test basic role creation."""
        # Arrange & Act
        role = Role(
            name="test_role",
            display_name="Test Role",
            description="A test role",
            role_type=RoleType.USER,
            permissions={"read:presentation", "create:presentation"},
            level=1,
        )
        
        # Assert
        assert role.name == "test_role"
        assert role.display_name == "Test Role"
        assert role.role_type == RoleType.USER
        assert len(role.permissions) == 2
        assert "read:presentation" in role.permissions
        assert role.level == 1
        assert role.is_system_role is True
        assert role.is_assignable is True
    
    def test_add_permission(self):
        """Test adding permission to role."""
        # Arrange
        role = Role(
            name="test_role",
            display_name="Test Role",
            role_type=RoleType.USER,
        )
        
        # Act
        role.add_permission("update:presentation")
        
        # Assert
        assert "update:presentation" in role.permissions
        assert len(role.permissions) == 1
    
    def test_remove_permission(self):
        """Test removing permission from role."""
        # Arrange
        role = Role(
            name="test_role",
            display_name="Test Role",
            role_type=RoleType.USER,
            permissions={"read:presentation", "update:presentation"},
        )
        
        # Act
        role.remove_permission("update:presentation")
        
        # Assert
        assert "update:presentation" not in role.permissions
        assert "read:presentation" in role.permissions
        assert len(role.permissions) == 1
    
    def test_has_permission(self):
        """Test checking if role has permission."""
        # Arrange
        role = Role(
            name="test_role",
            display_name="Test Role",
            role_type=RoleType.USER,
            permissions={"read:presentation"},
        )
        
        # Assert
        assert role.has_permission("read:presentation") is True
        assert role.has_permission("delete:presentation") is False
    
    def test_role_inheritance(self):
        """Test role parent relationship."""
        # Arrange
        role = Role(
            name="child_role",
            display_name="Child Role",
            role_type=RoleType.RESEARCHER,
            parent_roles={"user", "premium_user"},
        )
        
        # Assert
        assert role.inherits_from("user") is True
        assert role.inherits_from("premium_user") is True
        assert role.inherits_from("admin") is False


class TestRoleHierarchy:
    """Test RoleHierarchy functionality."""
    
    def test_add_inheritance(self):
        """Test adding inheritance relationship."""
        # Arrange
        hierarchy = RoleHierarchy()
        
        # Act
        hierarchy.add_inheritance("student", "user")
        hierarchy.add_inheritance("researcher", "premium_user")
        
        # Assert
        assert "user" in hierarchy.get_parent_roles("student")
        assert "premium_user" in hierarchy.get_parent_roles("researcher")
        assert "student" in hierarchy.get_child_roles("user")
    
    def test_remove_inheritance(self):
        """Test removing inheritance relationship."""
        # Arrange
        hierarchy = RoleHierarchy()
        hierarchy.add_inheritance("student", "user")
        
        # Act
        hierarchy.remove_inheritance("student", "user")
        
        # Assert
        assert "user" not in hierarchy.get_parent_roles("student")
        assert "student" not in hierarchy.get_child_roles("user")
    
    def test_get_all_parent_roles(self):
        """Test getting all parent roles including inherited."""
        # Arrange
        hierarchy = RoleHierarchy()
        hierarchy.add_inheritance("professor", "faculty")
        hierarchy.add_inheritance("faculty", "researcher")
        hierarchy.add_inheritance("researcher", "user")
        
        # Act
        all_parents = hierarchy.get_all_parent_roles("professor")
        
        # Assert
        assert "faculty" in all_parents
        assert "researcher" in all_parents
        assert "user" in all_parents
        assert len(all_parents) == 3
    
    def test_get_all_child_roles(self):
        """Test getting all child roles including inherited."""
        # Arrange
        hierarchy = RoleHierarchy()
        hierarchy.add_inheritance("student", "user")
        hierarchy.add_inheritance("researcher", "user")
        hierarchy.add_inheritance("faculty", "researcher")
        
        # Act
        all_children = hierarchy.get_all_child_roles("user")
        
        # Assert
        assert "student" in all_children
        assert "researcher" in all_children
        assert "faculty" in all_children
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        # Arrange
        hierarchy = RoleHierarchy()
        hierarchy.add_inheritance("role_a", "role_b")
        hierarchy.add_inheritance("role_b", "role_c")
        
        # Act & Assert
        # This would create a cycle: role_c -> role_a -> role_b -> role_c
        assert hierarchy.has_circular_dependency("role_c", "role_a") is True
        assert hierarchy.has_circular_dependency("role_d", "role_e") is False


class TestRoleManager:
    """Test RoleManager functionality."""
    
    @pytest.fixture
    def role_manager_instance(self):
        """Create a fresh RoleManager instance."""
        return RoleManager()
    
    def test_default_roles_initialization(self, role_manager_instance):
        """Test that default roles are properly initialized."""
        # Assert all expected roles exist
        expected_roles = [
            "user", "premium_user", "student", "researcher",
            "faculty", "professor", "department_admin",
            "institutional_admin", "moderator", "admin",
            "super_admin", "api_user", "api_admin",
        ]
        
        for role_name in expected_roles:
            role = role_manager_instance.get_role(role_name)
            assert role is not None
            assert role.name == role_name
    
    def test_role_hierarchy_levels(self, role_manager_instance):
        """Test that role levels follow expected hierarchy."""
        # Get roles
        user = role_manager_instance.get_role("user")
        student = role_manager_instance.get_role("student")
        researcher = role_manager_instance.get_role("researcher")
        faculty = role_manager_instance.get_role("faculty")
        admin = role_manager_instance.get_role("admin")
        super_admin = role_manager_instance.get_role("super_admin")
        
        # Assert hierarchy levels
        assert user.level < student.level
        assert student.level < researcher.level
        assert researcher.level < faculty.level
        assert faculty.level < admin.level
        assert admin.level < super_admin.level
    
    def test_create_custom_role(self, role_manager_instance):
        """Test creating a custom role."""
        # Arrange
        custom_role = Role(
            name="custom_reviewer",
            display_name="Custom Reviewer",
            description="Can review presentations",
            role_type=RoleType.USER,
            permissions={"read:presentation", "create:comment"},
            level=2,
            is_system_role=False,
        )
        
        # Act
        role_manager_instance.create_role(custom_role)
        
        # Assert
        retrieved_role = role_manager_instance.get_role("custom_reviewer")
        assert retrieved_role is not None
        assert retrieved_role.name == "custom_reviewer"
        assert retrieved_role.is_system_role is False
    
    def test_delete_custom_role(self, role_manager_instance):
        """Test deleting a custom role."""
        # Arrange
        custom_role = Role(
            name="temp_role",
            display_name="Temporary Role",
            role_type=RoleType.USER,
            is_system_role=False,
        )
        role_manager_instance.create_role(custom_role)
        
        # Act
        result = role_manager_instance.delete_role("temp_role")
        
        # Assert
        assert result is True
        assert role_manager_instance.get_role("temp_role") is None
    
    def test_cannot_delete_system_role(self, role_manager_instance):
        """Test that system roles cannot be deleted."""
        # Act
        result = role_manager_instance.delete_role("admin")
        
        # Assert
        assert result is False
        assert role_manager_instance.get_role("admin") is not None
    
    def test_add_permission_to_role(self, role_manager_instance):
        """Test adding permission to existing role."""
        # Create a custom role
        custom_role = Role(
            name="test_role",
            display_name="Test Role",
            role_type=RoleType.USER,
            is_system_role=False,
        )
        role_manager_instance.create_role(custom_role)
        
        # Act
        result = role_manager_instance.add_permission_to_role(
            "test_role",
            "read:presentation"
        )
        
        # Assert
        assert result is True
        role = role_manager_instance.get_role("test_role")
        assert "read:presentation" in role.permissions
    
    def test_get_user_effective_permissions(self, role_manager_instance):
        """Test getting all effective permissions for user roles."""
        # Act
        permissions = role_manager_instance.get_user_effective_permissions(
            ["student", "researcher"]
        )
        
        # Assert
        # Student inherits from user, researcher inherits from premium_user
        assert "create:presentation" in permissions  # From user role
        assert "read:presentation" in permissions    # From user role
        assert "create:template" in permissions      # From premium_user via researcher
        assert "read:analytics" in permissions       # From researcher role
    
    def test_user_has_permission(self, role_manager_instance):
        """Test checking if user has specific permission."""
        # Assert
        assert role_manager_instance.user_has_permission(
            ["faculty"], "manage:collaboration"
        ) is True
        
        assert role_manager_instance.user_has_permission(
            ["student"], "admin:system"
        ) is False
    
    def test_validate_role_assignment(self, role_manager_instance):
        """Test role assignment validation."""
        # Admin can assign lower-level roles
        assert role_manager_instance.validate_role_assignment(
            ["faculty"],  # Target user roles
            ["admin"]     # Assigner roles
        ) is True
        
        # Faculty cannot assign admin roles
        assert role_manager_instance.validate_role_assignment(
            ["admin"],    # Target user roles
            ["faculty"]   # Assigner roles
        ) is False
        
        # User cannot assign any roles to others at same or higher level
        assert role_manager_instance.validate_role_assignment(
            ["user"],     # Target user roles
            ["user"]      # Assigner roles
        ) is False
    
    def test_suggest_roles_for_academic_position(self, role_manager_instance):
        """Test role suggestions based on academic position."""
        # Test student positions
        suggestions = role_manager_instance.suggest_roles_for_academic_position(
            "PhD Student", "university"
        )
        assert "student" in suggestions
        
        # Test professor positions
        suggestions = role_manager_instance.suggest_roles_for_academic_position(
            "Associate Professor", "university"
        )
        assert "professor" in suggestions
        assert "premium_user" in suggestions  # Non-students at universities
        
        # Test researcher positions
        suggestions = role_manager_instance.suggest_roles_for_academic_position(
            "Postdoctoral Researcher", "research institute"
        )
        assert "researcher" in suggestions
        
        # Test admin positions
        suggestions = role_manager_instance.suggest_roles_for_academic_position(
            "Department Administrator", "college"
        )
        assert "department_admin" in suggestions
    
    def test_get_role_hierarchy(self, role_manager_instance):
        """Test getting complete role hierarchy structure."""
        # Act
        hierarchy = role_manager_instance.get_role_hierarchy()
        
        # Assert
        assert "user" in hierarchy
        assert "admin" in hierarchy
        
        # Check user role details
        user_info = hierarchy["user"]
        assert user_info["level"] == 1
        assert isinstance(user_info["permissions"], int)
        assert isinstance(user_info["effective_permissions"], int)
        
        # Check admin inherits from moderator
        admin_info = hierarchy["admin"]
        assert "moderator" in admin_info["parents"]
    
    def test_permission_inheritance(self, role_manager_instance):
        """Test that permissions are properly inherited."""
        # Get professor role (inherits from faculty -> researcher -> premium_user -> user)
        professor = role_manager_instance.get_role("professor")
        all_permissions = professor.get_all_permissions(role_manager_instance)
        
        # Should have permissions from all parent roles
        assert "create:presentation" in all_permissions  # From user
        assert "create:template" in all_permissions      # From premium_user
        assert "read:analytics" in all_permissions       # From researcher
        assert "manage:collaboration" in all_permissions # From faculty
        assert "manage:department" in all_permissions    # From professor itself


class TestAcademicRoleScenarios:
    """Test academic-specific role scenarios."""
    
    def test_student_permissions(self):
        """Test that students have appropriate permissions."""
        student = role_manager.get_role("student")
        permissions = student.get_all_permissions(role_manager)
        
        # Students should be able to create presentations
        assert "create:presentation" in permissions
        assert "read:presentation" in permissions
        
        # But not administrative tasks
        assert "admin:system" not in permissions
        assert "manage:institution" not in permissions
    
    def test_faculty_department_access(self):
        """Test faculty access to department resources."""
        faculty = role_manager.get_role("faculty")
        permissions = faculty.get_all_permissions(role_manager)
        
        # Faculty should read department info but not manage
        assert "read:department" in permissions
        assert "manage:department" not in permissions
        
        # Can manage collaborations
        assert "manage:collaboration" in permissions
    
    def test_institutional_admin_permissions(self):
        """Test institutional admin has proper access."""
        inst_admin = role_manager.get_role("institutional_admin")
        permissions = inst_admin.get_all_permissions(role_manager)
        
        # Should manage institution
        assert "manage:institution" in permissions
        assert "read:institution" in permissions
        
        # Should see audit logs
        assert "read:audit_log" in permissions
        
        # Should manage departments
        assert "manage:department" in permissions
    
    def test_api_role_separation(self):
        """Test API roles are separate from user roles."""
        api_user = role_manager.get_role("api_user")
        api_admin = role_manager.get_role("api_admin")
        
        # API roles should not inherit from regular user roles
        assert "user" not in api_user.parent_roles
        
        # But API admin inherits from API user
        assert "api_user" in api_admin.parent_roles
        
        # API admin should have system access
        api_admin_perms = api_admin.get_all_permissions(role_manager)
        assert "admin:system" in api_admin_perms


class TestRoleManagerEdgeCases:
    """Test edge cases and error handling."""
    
    def test_get_nonexistent_role(self):
        """Test getting a role that doesn't exist."""
        result = role_manager.get_role("nonexistent_role")
        assert result is None
    
    def test_add_permission_to_nonexistent_role(self):
        """Test adding permission to non-existent role."""
        result = role_manager.add_permission_to_role(
            "nonexistent_role",
            "read:presentation"
        )
        assert result is False
    
    def test_add_nonexistent_permission(self):
        """Test adding a permission that doesn't exist in registry."""
        # Create a test role
        test_role = Role(
            name="test_role",
            display_name="Test Role",
            role_type=RoleType.USER,
            is_system_role=False,
        )
        role_manager.create_role(test_role)
        
        # Try to add non-existent permission
        result = role_manager.add_permission_to_role(
            "test_role",
            "nonexistent:permission"
        )
        assert result is False
    
    def test_empty_user_roles(self):
        """Test getting permissions for user with no roles."""
        permissions = role_manager.get_user_effective_permissions([])
        assert len(permissions) == 0
    
    def test_duplicate_role_creation(self):
        """Test creating a role that already exists."""
        # Try to create a role with existing name
        duplicate_role = Role(
            name="admin",  # Already exists
            display_name="Duplicate Admin",
            role_type=RoleType.ADMIN,
        )
        
        # This should overwrite the existing role
        role_manager.create_role(duplicate_role)
        
        # Check that it was overwritten
        role = role_manager.get_role("admin")
        assert role.display_name == "Duplicate Admin"