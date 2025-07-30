# SlideGenie Authorization System

This module implements a comprehensive authorization and RBAC (Role-Based Access Control) system for SlideGenie, focusing on academic presentation management with institutional access controls.

## Components

### 1. **RBAC (rbac.py)**
- **RoleManager**: Manages roles, role hierarchy, and role assignments
- **Role**: Individual role with permissions and metadata
- **RoleHierarchy**: Manages role inheritance relationships
- **RoleType**: Enum of built-in role types

#### Built-in Roles (Hierarchical):
1. **user** (Level 1): Basic user with presentation creation capabilities
2. **premium_user** (Level 2): Enhanced features, inherits from user
3. **student** (Level 2): Academic student, inherits from user
4. **researcher** (Level 3): Academic researcher, inherits from premium_user
5. **faculty** (Level 4): Faculty member, inherits from researcher
6. **professor** (Level 5): Professor with full academic privileges
7. **department_admin** (Level 6): Department management capabilities
8. **institutional_admin** (Level 7): Full institutional access
9. **moderator** (Level 8): Content management capabilities
10. **admin** (Level 9): System administrator
11. **super_admin** (Level 10): Unrestricted access
12. **api_user** (Level 1): Programmatic API access
13. **api_admin** (Level 8): Administrative API access

### 2. **Permissions (permissions.py)**
- **PermissionChecker**: Service for checking user permissions
- **Permission**: Individual permission model
- **ResourcePermission**: Resource-specific permission with metadata
- **PermissionRegistry**: Registry of all available permissions

#### Resource Types:
- Core: presentation, slide, template, reference
- User: user, profile, api_key
- System: system, analytics, audit_log
- Institutional: institution, department, group
- Generation: generation_job, ai_model
- Collaboration: comment, share, collaboration

#### Permission Actions:
- CRUD: create, read, update, delete
- Extended: execute, manage, share, export, import, admin

### 3. **API Keys (api_keys.py)**
- **APIKeyService**: Service for managing API keys
- **APIKeyManager**: High-level API key interface
- **APIKey**: API key model with validation
- **APIKeyTier**: Tiers with different rate limits

#### API Key Tiers:
- **FREE**: 100/hour, 1000/day, 5000/month
- **ACADEMIC**: 500/hour, 5000/day, 25000/month
- **PROFESSIONAL**: 2000/hour, 20000/day, 100000/month
- **ENTERPRISE**: 10000/hour, 100000/day, unlimited/month

### 4. **Decorators (decorators.py)**
FastAPI decorators for endpoint protection:
- `@require_roles()`: Require specific user roles
- `@require_permissions()`: Require specific permissions
- `@require_api_key()`: Require valid API key with scopes
- `@require_ownership()`: Require resource ownership
- `@require_institutional_access()`: Require institutional membership

### 5. **Policies (policies.py)**
- **PolicyEngine**: Evaluates complex authorization rules
- **PolicyRule**: Individual policy with conditions
- **PolicyBuilder**: Fluent interface for creating policies

#### Built-in Policies:
- Time-based access restrictions
- IP whitelist for admin actions
- Academic resource sharing within institutions
- Student submission deadline enforcement
- Premium feature restrictions

### 6. **Authorization Service (authorization.py)**
- **AuthorizationService**: Main service coordinating all components
- **AuthorizationContext**: Context for authorization decisions
- **AuthorizationResult**: Result with decision and metadata

## Usage Examples

### Basic Authorization Check
```python
from app.services.auth.authorization import (
    AuthorizationService,
    AuthorizationContext,
    PermissionAction,
    ResourceType
)

# Create context
context = AuthorizationContext(
    user_id=user_id,
    user_email="professor@university.edu",
    user_roles=["professor"],
    institution_id=institution_id,
)

# Check authorization
auth_service = AuthorizationService()
result = await auth_service.authorize(
    context,
    PermissionAction.CREATE,
    ResourceType.PRESENTATION
)

if result.allowed:
    # Proceed with action
    pass
```

### Protecting Endpoints
```python
from fastapi import APIRouter, Depends
from app.services.auth.authorization.decorators import (
    require_roles,
    require_permissions,
    get_current_user
)

router = APIRouter()

@router.post("/presentations")
async def create_presentation(
    user: UserRead = Depends(require_permissions("create:presentation"))
):
    return {"message": "Presentation created"}

@router.delete("/presentations/{id}")
async def delete_presentation(
    id: UUID,
    user: UserRead = Depends(require_ownership(ResourceType.PRESENTATION))
):
    return {"message": "Presentation deleted"}

@router.get("/admin/analytics")
async def get_analytics(
    user: UserRead = Depends(require_roles(["admin", "institutional_admin"]))
):
    return {"analytics": "..."}
```

### API Key Authentication
```python
@router.get("/api/presentations")
async def list_presentations(
    api_key_info: dict = Depends(require_api_key(["read:presentations"]))
):
    return {"presentations": "..."}
```

### Creating Custom Policies
```python
from app.services.auth.authorization.policies import PolicyBuilder

policy = (
    PolicyBuilder()
    .with_id("course_access")
    .with_name("Course Material Access")
    .allow()
    .for_actions("read:presentation", "read:slide")
    .for_resources("presentation:*")
    .when("user_attributes.course_ids", "contains", "resource_attributes.course_id")
    .with_priority(20)
    .build()
)

policy_engine.add_policy(policy)
```

## Integration Points

1. **TokenService**: Used for JWT token validation in decorators
2. **User Model**: Database model for user information
3. **APIKey Model**: Database model for API key storage
4. **Redis**: Used for API key rate limiting
5. **FastAPI Dependencies**: Decorators integrate as FastAPI dependencies

## Security Considerations

1. **Role Hierarchy**: Higher-level roles inherit permissions from lower levels
2. **Explicit Deny**: Deny policies take precedence over allow policies
3. **Rate Limiting**: API keys are rate-limited by tier
4. **IP Whitelisting**: Optional IP restrictions for API keys
5. **Ownership Checks**: Users can only modify their own resources
6. **Institutional Boundaries**: Access restricted within institutions

## Academic Focus

The system includes special considerations for academic environments:
- Student submission deadlines
- Faculty access to course materials
- Institutional resource sharing
- Department-level management
- Research collaboration features