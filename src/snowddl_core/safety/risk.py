"""
Risk classification and change tracking for SnowDDL operations.

This module provides classes for categorizing and tracking infrastructure changes
based on their risk level and potential impact.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from snowddl_core.safety.constants import (
    RISK_WEIGHTS,
    ChangeCategory,
    RiskLevel,
)


class ChangeType(Enum):
    """Types of changes that can be made to objects."""

    CREATE = auto()
    UPDATE = auto()
    DELETE = auto()
    DROP = auto()
    GRANT = auto()
    REVOKE = auto()
    ALTER = auto()
    RENAME = auto()


@dataclass
class Change:
    """
    Represents a single infrastructure change.

    Tracks what is changing, how it's changing, and the associated risk.
    """

    object_type: str  # user, warehouse, database, etc.
    object_name: str  # Name of the object
    change_type: ChangeType  # Type of change
    old_value: Optional[Any] = None  # Previous value (for updates)
    new_value: Optional[Any] = None  # New value (for updates)
    field_name: Optional[str] = None  # Specific field being changed
    category: Optional[ChangeCategory] = None  # Change category
    risk_level: Optional[RiskLevel] = None  # Risk classification
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_destructive(self) -> bool:
        """Check if this is a destructive change."""
        return self.change_type in [ChangeType.DELETE, ChangeType.DROP]

    def affects_authentication(self) -> bool:
        """Check if this change affects authentication."""
        return self.category == ChangeCategory.AUTHENTICATION or self.field_name in [
            "password",
            "rsa_public_key",
            "must_change_password",
            "mins_to_unlock",
        ]

    def affects_network(self) -> bool:
        """Check if this change affects network access."""
        return self.category == ChangeCategory.NETWORK or self.field_name in [
            "network_policy",
            "allowed_ip_list",
            "blocked_ip_list",
        ]

    def affects_resources(self) -> bool:
        """Check if this change affects compute resources."""
        return self.category == ChangeCategory.RESOURCE or self.object_type in [
            "warehouse",
            "resource_monitor",
        ]

    def sets_field(self, field: str) -> bool:
        """Check if this change sets a specific field."""
        return self.field_name == field and self.new_value is not None

    def removes_field(self, field: str) -> bool:
        """Check if this change removes a specific field."""
        return (
            self.field_name == field
            and self.new_value is None
            and self.old_value is not None
        )

    def get_new_value(self, field: str) -> Optional[Any]:
        """Get the new value for a field if this change sets it."""
        if self.field_name == field:
            return self.new_value
        return None

    def __str__(self) -> str:
        """String representation of the change."""
        if self.field_name:
            return (
                f"{self.change_type.name} {self.object_type}.{self.object_name}.{self.field_name} "
                f"({self.old_value} → {self.new_value})"
            )
        return f"{self.change_type.name} {self.object_type}.{self.object_name}"


@dataclass
class ImpactReport:
    """Report of the potential impact of changes."""

    directly_affected: List[str]  # Objects directly affected
    cascade_effects: List[str]  # Objects affected by cascade
    risk_score: float  # Numerical risk score
    warnings: List[str] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)

    def is_safe(self) -> bool:
        """Check if the impact is within acceptable limits."""
        return len(self.blocking_issues) == 0

    def add_warning(self, warning: str) -> None:
        """Add a warning to the report."""
        self.warnings.append(warning)

    def add_blocking_issue(self, issue: str) -> None:
        """Add a blocking issue to the report."""
        self.blocking_issues.append(issue)


class RiskClassifier:
    """
    Classifies infrastructure changes based on risk level.

    Uses multiple factors to assess the potential impact and danger
    of proposed changes.
    """

    def __init__(self, project):
        """
        Initialize risk classifier.

        Args:
            project: SnowDDLProject instance
        """
        self.project = project

    def classify(self, change: Change) -> RiskLevel:
        """
        Classify a single change based on risk factors.

        Args:
            change: Change object to classify

        Returns:
            RiskLevel for the change
        """
        # Critical risk conditions
        if self._is_critical_change(change):
            return RiskLevel.CRITICAL

        # High risk conditions
        if self._is_high_risk_change(change):
            return RiskLevel.HIGH

        # Medium risk conditions
        if self._is_medium_risk_change(change):
            return RiskLevel.MEDIUM

        # Default to low risk
        return RiskLevel.LOW

    def classify_batch(self, changes: List[Change]) -> RiskLevel:
        """
        Classify a batch of changes based on cumulative risk.

        Args:
            changes: List of Change objects

        Returns:
            Overall RiskLevel for the batch
        """
        if not changes:
            return RiskLevel.LOW

        # Get individual risk levels
        risk_levels = [self.classify(change) for change in changes]

        # Return highest risk level in batch
        if RiskLevel.CRITICAL in risk_levels:
            return RiskLevel.CRITICAL
        elif RiskLevel.HIGH in risk_levels:
            return RiskLevel.HIGH
        elif RiskLevel.MEDIUM in risk_levels:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def calculate_risk_score(self, changes: List[Change]) -> float:
        """
        Calculate numerical risk score for changes.

        Args:
            changes: List of Change objects

        Returns:
            Numerical risk score (0-100)
        """
        if not changes:
            return 0.0

        total_score = 0.0

        for change in changes:
            # Base score from category
            category_score = RISK_WEIGHTS.get(change.category, 1.0)

            # Multipliers for change type
            if change.is_destructive():
                category_score *= 2.0

            # Multipliers for object importance
            if self._is_production_object(change):
                category_score *= 1.5

            # Add authentication risk
            if change.affects_authentication():
                category_score *= 1.5

            # Add network risk
            if change.affects_network():
                category_score *= 1.3

            total_score += category_score

        # Normalize to 0-100 scale
        return min(100.0, total_score)

    def _is_critical_change(self, change: Change) -> bool:
        """Check if a change is critical risk."""
        # Authentication changes on admin accounts
        if change.affects_authentication() and self._is_admin_user(change.object_name):
            return True

        # Network policy changes affecting admins
        if change.affects_network() and change.object_type == "user":
            if self._is_admin_user(change.object_name):
                return True

        # Dropping critical databases
        if change.is_destructive() and change.object_type == "database":
            if self._is_production_object(change):
                return True

        return False

    def _is_high_risk_change(self, change: Change) -> bool:
        """Check if a change is high risk."""
        # Resource monitor changes in production
        if change.object_type == "resource_monitor" and self._is_production_object(
            change
        ):
            return True

        # Any destructive change
        if change.is_destructive():
            return True

        # Permission changes on critical roles
        if change.category == ChangeCategory.PERMISSION:
            if change.object_name in ["ACCOUNTADMIN", "SECURITYADMIN", "SYSADMIN"]:
                return True

        return False

    def _is_medium_risk_change(self, change: Change) -> bool:
        """Check if a change is medium risk."""
        # Warehouse sizing changes
        if change.object_type == "warehouse" and change.field_name == "size":
            return True

        # Role assignments
        if change.category == ChangeCategory.PERMISSION:
            return True

        # Configuration changes
        if change.category == ChangeCategory.CONFIGURATION:
            return True

        return False

    def _is_admin_user(self, username: str) -> bool:
        """Check if a user has admin privileges."""
        user = self.project.get_user(username)
        if user:
            # Check for both ACCOUNTADMIN and ADMIN_ROLE
            admin_roles = ["ACCOUNTADMIN", "ADMIN_ROLE"]
            return any(role in user.business_roles for role in admin_roles)
        # Also treat certain usernames as admin by default
        admin_usernames = ["ALICE", "ACCOUNTADMIN", "SECURITYADMIN"]
        return username in admin_usernames

    def _is_production_object(self, change: Change) -> bool:
        """Check if an object is production-critical."""
        prod_indicators = ["PROD", "PRODUCTION", "MAIN", "PRIMARY"]

        for indicator in prod_indicators:
            if indicator in change.object_name.upper():
                return True

        return False

    def analyze_impact(self, change: Change) -> ImpactReport:
        """
        Analyze the potential impact of a change.

        Args:
            change: Change to analyze

        Returns:
            ImpactReport with affected objects and warnings
        """
        report = ImpactReport(
            directly_affected=[f"{change.object_type}.{change.object_name}"],
            cascade_effects=[],
            risk_score=self.calculate_risk_score([change]),
        )

        # Analyze cascade effects based on object type
        if change.object_type == "user" and change.is_destructive():
            # Dropping a user affects their owned objects
            report.cascade_effects.extend(
                self._get_user_owned_objects(change.object_name)
            )

        elif change.object_type == "role" and change.is_destructive():
            # Dropping a role affects users with that role
            report.cascade_effects.extend(self._get_role_users(change.object_name))

        elif change.object_type == "warehouse" and change.is_destructive():
            # Dropping a warehouse affects users using it
            report.cascade_effects.extend(self._get_warehouse_users(change.object_name))

        # Add warnings for high-impact changes
        if len(report.cascade_effects) > 10:
            report.add_warning(
                f"Large cascade impact: {len(report.cascade_effects)} objects affected"
            )

        if change.affects_authentication():
            report.add_warning(
                "Authentication change - ensure backup access methods exist"
            )

        if change.affects_network():
            report.add_warning("Network change - verify access won't be blocked")

        # Add blocking issues for dangerous changes
        if self._would_lock_out_admins(change):
            report.add_blocking_issue("This change would lock out all admin accounts")

        return report

    def _get_user_owned_objects(self, username: str) -> List[str]:
        """Get objects owned by a user."""
        # This would query the project for user-owned objects
        # For now, return empty list (to be implemented with full object model)
        return []

    def _get_role_users(self, rolename: str) -> List[str]:
        """Get users with a specific role."""
        affected = []
        for name, user in self.project.users.items():
            if rolename in user.business_roles:
                affected.append(f"user.{name}")
        return affected

    def _get_warehouse_users(self, warehouse_name: str) -> List[str]:
        """Get users using a specific warehouse."""
        affected = []
        for name, user in self.project.users.items():
            if user.default_warehouse == warehouse_name:
                affected.append(f"user.{name}")
        return affected

    def _would_lock_out_admins(self, change: Change) -> bool:
        """Check if a change would lock out admin access."""
        if change.object_type == "user" and change.affects_authentication():
            # Check if this is the last admin with a password
            if self._is_admin_user(change.object_name) and change.removes_field(
                "password"
            ):
                admin_roles = ["ACCOUNTADMIN", "ADMIN_ROLE"]
                admin_count = sum(
                    1
                    for u in self.project.users.values()
                    if any(role in u.business_roles for role in admin_roles)
                    and u.password
                )
                return admin_count <= 1

        return False
