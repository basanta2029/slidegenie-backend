"""
Policy engine for complex authorization rules.

Implements a flexible policy system for fine-grained access control
beyond simple RBAC, supporting academic and institutional policies.
"""

from abc import ABC, abstractmethod
from datetime import datetime, time, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class PolicyEffect(str, Enum):
    """Policy effect - whether to allow or deny."""
    ALLOW = "allow"
    DENY = "deny"


class PolicyConditionOperator(str, Enum):
    """Operators for policy conditions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"
    REGEX = "regex"


class PolicyContext(BaseModel):
    """Context for policy evaluation."""
    user_id: UUID
    user_email: str
    user_roles: List[str] = Field(default_factory=list)
    user_attributes: Dict[str, Any] = Field(default_factory=dict)
    
    resource_type: str
    resource_id: Optional[UUID] = None
    resource_attributes: Dict[str, Any] = Field(default_factory=dict)
    
    action: str
    environment: Dict[str, Any] = Field(default_factory=dict)
    
    request_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_ip: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None


class PolicyCondition(BaseModel):
    """Individual condition for policy evaluation."""
    attribute: str  # Dot notation path (e.g., "user.department", "resource.tags")
    operator: PolicyConditionOperator
    value: Any
    case_sensitive: bool = True
    
    def evaluate(self, context: PolicyContext) -> bool:
        """Evaluate condition against context."""
        # Get attribute value from context
        attr_value = self._get_attribute_value(context, self.attribute)
        
        if attr_value is None:
            return False
        
        # Apply operator
        try:
            if self.operator == PolicyConditionOperator.EQUALS:
                return self._compare_values(attr_value, self.value, self.case_sensitive)
            
            elif self.operator == PolicyConditionOperator.NOT_EQUALS:
                return not self._compare_values(attr_value, self.value, self.case_sensitive)
            
            elif self.operator == PolicyConditionOperator.IN:
                if not isinstance(self.value, list):
                    return False
                return any(
                    self._compare_values(attr_value, v, self.case_sensitive)
                    for v in self.value
                )
            
            elif self.operator == PolicyConditionOperator.NOT_IN:
                if not isinstance(self.value, list):
                    return True
                return not any(
                    self._compare_values(attr_value, v, self.case_sensitive)
                    for v in self.value
                )
            
            elif self.operator == PolicyConditionOperator.CONTAINS:
                return str(self.value) in str(attr_value)
            
            elif self.operator == PolicyConditionOperator.STARTS_WITH:
                return str(attr_value).startswith(str(self.value))
            
            elif self.operator == PolicyConditionOperator.ENDS_WITH:
                return str(attr_value).endswith(str(self.value))
            
            elif self.operator == PolicyConditionOperator.GREATER_THAN:
                return float(attr_value) > float(self.value)
            
            elif self.operator == PolicyConditionOperator.LESS_THAN:
                return float(attr_value) < float(self.value)
            
            elif self.operator == PolicyConditionOperator.BETWEEN:
                if not isinstance(self.value, list) or len(self.value) != 2:
                    return False
                val = float(attr_value)
                return float(self.value[0]) <= val <= float(self.value[1])
            
            elif self.operator == PolicyConditionOperator.REGEX:
                import re
                return bool(re.match(str(self.value), str(attr_value)))
            
            else:
                logger.warning("unknown_policy_operator", operator=self.operator)
                return False
                
        except Exception as e:
            logger.error(
                "policy_condition_evaluation_error",
                attribute=self.attribute,
                operator=self.operator,
                error=str(e),
            )
            return False
    
    def _get_attribute_value(self, context: PolicyContext, path: str) -> Any:
        """Get attribute value from context using dot notation."""
        parts = path.split(".")
        current = context
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, BaseModel):
                current = getattr(current, part, None)
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def _compare_values(self, val1: Any, val2: Any, case_sensitive: bool) -> bool:
        """Compare two values with case sensitivity option."""
        if isinstance(val1, str) and isinstance(val2, str) and not case_sensitive:
            return val1.lower() == val2.lower()
        return val1 == val2


class PolicyRule(BaseModel):
    """Individual policy rule."""
    id: str
    name: str
    description: Optional[str] = None
    effect: PolicyEffect
    
    # What this policy applies to
    actions: List[str]  # Can use wildcards (e.g., "read:*")
    resources: List[str]  # Can use wildcards (e.g., "presentation:*")
    
    # Conditions that must be met
    conditions: List[PolicyCondition] = Field(default_factory=list)
    condition_logic: str = "all"  # "all" or "any"
    
    # Priority for conflict resolution (higher = more priority)
    priority: int = 0
    
    # Metadata
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    def matches_action(self, action: str) -> bool:
        """Check if policy matches the action."""
        for pattern in self.actions:
            if self._matches_pattern(action, pattern):
                return True
        return False
    
    def matches_resource(self, resource: str) -> bool:
        """Check if policy matches the resource."""
        for pattern in self.resources:
            if self._matches_pattern(resource, pattern):
                return True
        return False
    
    def evaluate_conditions(self, context: PolicyContext) -> bool:
        """Evaluate all conditions against context."""
        if not self.conditions:
            return True
        
        results = [cond.evaluate(context) for cond in self.conditions]
        
        if self.condition_logic == "all":
            return all(results)
        elif self.condition_logic == "any":
            return any(results)
        else:
            logger.warning("unknown_condition_logic", logic=self.condition_logic)
            return False
    
    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern (supports wildcards)."""
        if pattern == "*":
            return True
        
        if "*" in pattern:
            # Simple wildcard matching
            parts = pattern.split("*")
            if len(parts) == 2:
                # Pattern like "prefix*" or "*suffix"
                if parts[0] == "":
                    return value.endswith(parts[1])
                elif parts[1] == "":
                    return value.startswith(parts[0])
                else:
                    # Pattern like "prefix*suffix"
                    return value.startswith(parts[0]) and value.endswith(parts[1])
        
        return value == pattern


class PolicyEngine:
    """Engine for evaluating policies."""
    
    def __init__(self):
        self._policies: Dict[str, PolicyRule] = {}
        self._policy_sets: Dict[str, List[str]] = {}  # Group policies
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default system policies."""
        # Time-based access policy
        self.add_policy(PolicyRule(
            id="time_based_access",
            name="Business Hours Access",
            description="Restrict certain operations to business hours",
            effect=PolicyEffect.DENY,
            actions=["delete:*", "admin:*"],
            resources=["*"],
            conditions=[
                PolicyCondition(
                    attribute="request_time",
                    operator=PolicyConditionOperator.BETWEEN,
                    value=[time(9, 0), time(17, 0)],
                )
            ],
            priority=10,
        ))
        
        # IP-based access policy
        self.add_policy(PolicyRule(
            id="ip_whitelist",
            name="IP Whitelist for Admin",
            description="Admin actions only from whitelisted IPs",
            effect=PolicyEffect.DENY,
            actions=["admin:*"],
            resources=["*"],
            conditions=[
                PolicyCondition(
                    attribute="request_ip",
                    operator=PolicyConditionOperator.NOT_IN,
                    value=["10.0.0.0/8", "192.168.0.0/16"],  # Example internal IPs
                )
            ],
            priority=20,
        ))
        
        # Academic sharing policy
        self.add_policy(PolicyRule(
            id="academic_sharing",
            name="Academic Resource Sharing",
            description="Allow sharing within same institution",
            effect=PolicyEffect.ALLOW,
            actions=["share:presentation", "read:presentation"],
            resources=["presentation:*"],
            conditions=[
                PolicyCondition(
                    attribute="user_attributes.institution_id",
                    operator=PolicyConditionOperator.EQUALS,
                    value="resource_attributes.institution_id",
                )
            ],
            priority=15,
        ))
        
        # Student submission policy
        self.add_policy(PolicyRule(
            id="student_submission",
            name="Student Submission Deadline",
            description="Students cannot modify after submission deadline",
            effect=PolicyEffect.DENY,
            actions=["update:presentation", "delete:presentation"],
            resources=["presentation:*"],
            conditions=[
                PolicyCondition(
                    attribute="user_roles",
                    operator=PolicyConditionOperator.CONTAINS,
                    value="student",
                ),
                PolicyCondition(
                    attribute="resource_attributes.submission_deadline",
                    operator=PolicyConditionOperator.LESS_THAN,
                    value="request_time",
                ),
            ],
            condition_logic="all",
            priority=25,
        ))
        
        # Premium feature policy
        self.add_policy(PolicyRule(
            id="premium_features",
            name="Premium Feature Access",
            description="Restrict advanced features to premium users",
            effect=PolicyEffect.DENY,
            actions=["execute:ai_model", "export:presentation"],
            resources=["*"],
            conditions=[
                PolicyCondition(
                    attribute="user_roles",
                    operator=PolicyConditionOperator.NOT_IN,
                    value=["premium_user", "researcher", "faculty", "professor"],
                )
            ],
            priority=5,
        ))
    
    def add_policy(self, policy: PolicyRule) -> None:
        """Add a policy to the engine."""
        self._policies[policy.id] = policy
        logger.info("policy_added", policy_id=policy.id, name=policy.name)
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy from the engine."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            logger.info("policy_removed", policy_id=policy_id)
            return True
        return False
    
    def get_policy(self, policy_id: str) -> Optional[PolicyRule]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    def evaluate(
        self,
        context: PolicyContext,
        action: str,
        resource: str,
    ) -> tuple[PolicyEffect, List[PolicyRule]]:
        """
        Evaluate policies for given context.
        
        Returns:
            Tuple of (final effect, list of applied policies)
        """
        # Update context with action and resource
        context.action = action
        context.resource_type = resource
        
        # Find applicable policies
        applicable_policies = []
        
        for policy in self._policies.values():
            # Skip inactive or expired policies
            if not policy.is_active:
                continue
            
            if policy.expires_at and policy.expires_at < datetime.now(timezone.utc):
                continue
            
            # Check if policy matches action and resource
            if not policy.matches_action(action):
                continue
            
            if not policy.matches_resource(resource):
                continue
            
            # Evaluate conditions
            if policy.evaluate_conditions(context):
                applicable_policies.append(policy)
        
        # Sort by priority (highest first)
        applicable_policies.sort(key=lambda p: p.priority, reverse=True)
        
        # Apply policies in order
        final_effect = PolicyEffect.ALLOW  # Default allow
        applied_policies = []
        
        for policy in applicable_policies:
            applied_policies.append(policy)
            
            # Explicit deny takes precedence
            if policy.effect == PolicyEffect.DENY:
                final_effect = PolicyEffect.DENY
                break
            
            # Continue checking other policies
        
        logger.info(
            "policy_evaluation_complete",
            action=action,
            resource=resource,
            effect=final_effect,
            applied_count=len(applied_policies),
            applied_policies=[p.id for p in applied_policies],
        )
        
        return final_effect, applied_policies
    
    def create_policy_set(self, name: str, policy_ids: List[str]) -> None:
        """Create a named set of policies."""
        self._policy_sets[name] = policy_ids
        logger.info("policy_set_created", name=name, policies=policy_ids)
    
    def apply_policy_set(self, name: str) -> int:
        """Apply all policies in a set."""
        if name not in self._policy_sets:
            return 0
        
        count = 0
        for policy_id in self._policy_sets[name]:
            if policy_id in self._policies:
                self._policies[policy_id].is_active = True
                count += 1
        
        logger.info("policy_set_applied", name=name, count=count)
        return count
    
    def disable_policy_set(self, name: str) -> int:
        """Disable all policies in a set."""
        if name not in self._policy_sets:
            return 0
        
        count = 0
        for policy_id in self._policy_sets[name]:
            if policy_id in self._policies:
                self._policies[policy_id].is_active = False
                count += 1
        
        logger.info("policy_set_disabled", name=name, count=count)
        return count


class PolicyBuilder:
    """Builder for creating policies with fluent interface."""
    
    def __init__(self):
        self._policy = PolicyRule(
            id="",
            name="",
            effect=PolicyEffect.ALLOW,
            actions=[],
            resources=[],
        )
    
    def with_id(self, policy_id: str) -> 'PolicyBuilder':
        """Set policy ID."""
        self._policy.id = policy_id
        return self
    
    def with_name(self, name: str) -> 'PolicyBuilder':
        """Set policy name."""
        self._policy.name = name
        return self
    
    def with_description(self, description: str) -> 'PolicyBuilder':
        """Set policy description."""
        self._policy.description = description
        return self
    
    def allow(self) -> 'PolicyBuilder':
        """Set effect to allow."""
        self._policy.effect = PolicyEffect.ALLOW
        return self
    
    def deny(self) -> 'PolicyBuilder':
        """Set effect to deny."""
        self._policy.effect = PolicyEffect.DENY
        return self
    
    def for_actions(self, *actions: str) -> 'PolicyBuilder':
        """Set actions."""
        self._policy.actions = list(actions)
        return self
    
    def for_resources(self, *resources: str) -> 'PolicyBuilder':
        """Set resources."""
        self._policy.resources = list(resources)
        return self
    
    def when(
        self,
        attribute: str,
        operator: PolicyConditionOperator,
        value: Any,
    ) -> 'PolicyBuilder':
        """Add a condition."""
        condition = PolicyCondition(
            attribute=attribute,
            operator=operator,
            value=value,
        )
        self._policy.conditions.append(condition)
        return self
    
    def with_priority(self, priority: int) -> 'PolicyBuilder':
        """Set priority."""
        self._policy.priority = priority
        return self
    
    def with_all_conditions(self) -> 'PolicyBuilder':
        """Require all conditions to be met."""
        self._policy.condition_logic = "all"
        return self
    
    def with_any_condition(self) -> 'PolicyBuilder':
        """Require any condition to be met."""
        self._policy.condition_logic = "any"
        return self
    
    def expires_at(self, expires: datetime) -> 'PolicyBuilder':
        """Set expiration date."""
        self._policy.expires_at = expires
        return self
    
    def build(self) -> PolicyRule:
        """Build the policy."""
        if not self._policy.id or not self._policy.name:
            raise ValueError("Policy must have ID and name")
        
        if not self._policy.actions or not self._policy.resources:
            raise ValueError("Policy must have actions and resources")
        
        return self._policy


# Example of creating a policy using the builder
def create_department_policy(department_id: UUID) -> PolicyRule:
    """Create a policy for department-level access."""
    return (
        PolicyBuilder()
        .with_id(f"dept_access_{department_id}")
        .with_name(f"Department {department_id} Access")
        .with_description("Allow department members to access department resources")
        .allow()
        .for_actions("read:*", "update:*")
        .for_resources("presentation:*", "template:*")
        .when("user_attributes.department_id", PolicyConditionOperator.EQUALS, str(department_id))
        .when("resource_attributes.department_id", PolicyConditionOperator.EQUALS, str(department_id))
        .with_all_conditions()
        .with_priority(10)
        .build()
    )


# Global policy engine instance
policy_engine = PolicyEngine()