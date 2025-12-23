"""
Bootstrap-aware validation for initial infrastructure creation.

This module provides validation that's appropriate when building infrastructure
from scratch, where certain checks (like existing admin passwords) don't apply.
"""

from typing import List

from snowddl_core.safety.constants import SACRED_ACCOUNTS, RiskLevel
from snowddl_core.safety.risk import Change
from snowddl_core.safety.validators import ValidationResult


class BootstrapValidator:
    """
    Validator for bootstrap/initial creation scenarios.

    Only validates changes that are relevant during infrastructure creation,
    skipping checks that assume existing infrastructure.
    """

    def __init__(self, project):
        """
        Initialize bootstrap validator.

        Args:
            project: SnowDDLProject instance
        """
        self.project = project

    def validate_changes(self, changes: List[Change]) -> ValidationResult:
        """
        Validate changes in bootstrap context.

        Only checks:
        - Sacred accounts are not modified
        - Resource monitors don't have dangerous thresholds
        - No destructive operations during creation

        Skips:
        - Admin password requirements (no users exist yet)
        - Network policy restrictions (being set up)
        - Backup access verification (being created)

        Args:
            changes: List of changes to validate

        Returns:
            ValidationResult
        """
        # Check for sacred account modifications
        for change in changes:
            if change.object_type == "user" and change.object_name in SACRED_ACCOUNTS:
                return ValidationResult.unsafe(
                    f"Cannot modify sacred account {change.object_name} even in bootstrap",
                    RiskLevel.CRITICAL,
                )

        # Check for destructive operations (shouldn't happen during creation)
        for change in changes:
            if change.is_destructive():
                return ValidationResult.unsafe(
                    f"Destructive operation {change.change_type.name} not allowed during bootstrap",
                    RiskLevel.HIGH,
                )

        # Resource monitor specific checks
        for change in changes:
            if change.object_type == "resource_monitor":
                if change.sets_field("suspend_at"):
                    threshold = change.get_new_value("suspend_at")
                    if threshold and threshold >= 100:
                        return ValidationResult.unsafe(
                            f"Resource monitor {change.object_name} has dangerous 100% threshold",
                            RiskLevel.HIGH,
                        )

        # Warn about high-risk changes but don't block
        warnings = []
        for change in changes:
            if change.risk_level == RiskLevel.CRITICAL:
                warnings.append(f"Critical change during bootstrap: {change}")
            elif change.risk_level == RiskLevel.HIGH:
                warnings.append(f"High-risk change during bootstrap: {change}")

        return ValidationResult.safe(warnings=warnings)

    def validate_final_state(self) -> ValidationResult:
        """
        Validate the final state after bootstrap completion.

        Ensures:
        - At least one admin exists with password
        - Sacred accounts were not created (they should exist separately)
        - Basic infrastructure is in place

        Returns:
            ValidationResult
        """
        issues = []
        warnings = []

        # Check for admin users
        admin_count = 0
        admin_with_password = 0

        for user in self.project.users.values():
            if (
                "ACCOUNTADMIN" in user.business_roles
                or "ADMIN_ROLE" in user.business_roles
            ):
                admin_count += 1
                if user.password:
                    admin_with_password += 1

        if admin_count == 0:
            issues.append("No admin users created during bootstrap")
        elif admin_with_password == 0:
            issues.append("No admin users have passwords set")
        elif admin_with_password < 2:
            warnings.append(
                f"Only {admin_with_password} admin(s) with passwords (recommend 2+)"
            )

        # Check infrastructure minimums
        if len(self.project.warehouses) == 0:
            warnings.append("No warehouses created")

        if len(self.project.business_roles) == 0:
            warnings.append("No business roles created")

        # Check for sacred accounts (they should be pre-existing)
        for sacred in SACRED_ACCOUNTS:
            if sacred not in self.project.users:
                warnings.append(
                    f"Sacred account {sacred} not found - ensure it exists in Snowflake"
                )

        if issues:
            return ValidationResult.unsafe("; ".join(issues), RiskLevel.HIGH)

        return ValidationResult.safe(warnings=warnings)
