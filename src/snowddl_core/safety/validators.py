"""
Safety validators for SnowDDL operations.

This module provides validation classes that ensure all infrastructure changes
are safe before execution.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from snowddl_core.safety.constants import (
    GOLDEN_RULES,
    HIGH_RISK_OBJECTS,
    SACRED_ACCOUNTS,
    THRESHOLDS,
    RiskLevel,
)


@dataclass
class ValidationResult:
    """Result of a safety validation check."""

    is_safe: bool
    reason: Optional[str] = None
    warnings: List[str] = None
    risk_level: RiskLevel = RiskLevel.LOW

    def __post_init__(self):
        """Initialize warnings list if not provided."""
        if self.warnings is None:
            self.warnings = []

    @classmethod
    def safe(cls, warnings: Optional[List[str]] = None) -> "ValidationResult":
        """Create a safe validation result."""
        return cls(is_safe=True, warnings=warnings or [])

    @classmethod
    def unsafe(
        cls, reason: str, risk_level: RiskLevel = RiskLevel.HIGH
    ) -> "ValidationResult":
        """Create an unsafe validation result."""
        return cls(is_safe=False, reason=reason, risk_level=risk_level)


class SafetyValidator:
    """
    Core safety validator for all infrastructure changes.

    Ensures changes don't violate golden rules or create dangerous conditions.
    """

    def __init__(self, project):
        """
        Initialize safety validator.

        Args:
            project: SnowDDLProject instance
        """
        self.project = project
        self.violations = []

    def validate_changes(self, changes: List["Change"]) -> ValidationResult:
        """
        Validate a list of changes for safety.

        Args:
            changes: List of Change objects to validate

        Returns:
            ValidationResult indicating if changes are safe
        """
        # Run all validation checks
        checks = [
            self._check_no_admin_lockout,
            self._check_backup_access_preserved,
            self._check_no_production_drops,
            self._check_password_policy_compliance,
            self._check_network_policy_safety,
            self._check_resource_monitor_thresholds,
            self._check_sacred_accounts,
            self._check_change_volume,
        ]

        for check in checks:
            result = check(changes)
            if not result.is_safe:
                return result

        # All checks passed
        warnings = []
        for check_result in [check(changes) for check in checks]:
            warnings.extend(check_result.warnings)

        return ValidationResult.safe(warnings=warnings)

    def _check_sacred_accounts(self, changes: List["Change"]) -> ValidationResult:
        """Ensure sacred accounts are never modified."""
        for change in changes:
            if change.object_type == "user" and change.object_name in SACRED_ACCOUNTS:
                return ValidationResult.unsafe(
                    f"Attempted to modify sacred account: {change.object_name}. "
                    f"Sacred accounts {SACRED_ACCOUNTS} must never be modified.",
                    RiskLevel.CRITICAL,
                )
        return ValidationResult.safe()

    def _check_no_admin_lockout(self, changes: List["Change"]) -> ValidationResult:
        """Ensure changes won't lock out admin access."""
        admin_users_affected = []
        password_removals = []
        network_policy_changes = []

        for change in changes:
            if change.object_type == "user":
                user = self.project.get_user(change.object_name)
                # Check for both ACCOUNTADMIN and ADMIN_ROLE
                admin_roles = ["ACCOUNTADMIN", "ADMIN_ROLE"]
                if user and any(role in user.business_roles for role in admin_roles):
                    admin_users_affected.append(change.object_name)

                    # Check for password removal
                    if change.removes_field("password"):
                        password_removals.append(change.object_name)

                    # Check for restrictive network policy
                    if change.sets_field("network_policy"):
                        network_policy_changes.append(change.object_name)

        # Validate admin access will be preserved
        remaining_admin_passwords = self._count_admin_passwords(
            exclude=password_removals
        )

        if remaining_admin_passwords < THRESHOLDS["min_admin_accounts_with_password"]:
            return ValidationResult.unsafe(
                f"Changes would leave only {remaining_admin_passwords} admin account(s) with passwords. "
                f"Minimum required: {THRESHOLDS['min_admin_accounts_with_password']}",
                RiskLevel.CRITICAL,
            )

        # Warn about network policy changes on admins
        warnings = []
        if network_policy_changes:
            warnings.append(
                f"Network policy changes affect admin users: {network_policy_changes}"
            )

        return ValidationResult.safe(warnings=warnings)

    def _check_backup_access_preserved(
        self, changes: List["Change"]
    ) -> ValidationResult:
        """Ensure backup access methods remain available."""
        # Check that STEPHEN_RECOVERY exists and is not being modified
        recovery_account = self.project.get_user("STEPHEN_RECOVERY")

        if not recovery_account:
            return ValidationResult.unsafe(
                "Recovery account STEPHEN_RECOVERY not found. "
                "This account must exist before making critical changes.",
                RiskLevel.CRITICAL,
            )

        # Ensure recovery account has no network policy
        if recovery_account.network_policy:
            return ValidationResult.unsafe(
                "Recovery account STEPHEN_RECOVERY has network policy restrictions. "
                "This account must have unrestricted access for emergency recovery.",
                RiskLevel.CRITICAL,
            )

        return ValidationResult.safe()

    def _check_no_production_drops(self, changes: List["Change"]) -> ValidationResult:
        """Prevent dropping production databases without confirmation."""
        for change in changes:
            if change.is_destructive():
                obj_type = change.object_type
                obj_name = change.object_name

                # Check if it's a high-risk object
                if obj_type in HIGH_RISK_OBJECTS:
                    if obj_name in HIGH_RISK_OBJECTS[obj_type]:
                        return ValidationResult.unsafe(
                            f"Attempted to drop production {obj_type}: {obj_name}. "
                            "Production drops require explicit confirmation and backup verification.",
                            RiskLevel.HIGH,
                        )

        return ValidationResult.safe()

    def _check_password_policy_compliance(
        self, changes: List["Change"]
    ) -> ValidationResult:
        """Ensure password changes comply with policies."""
        warnings = []

        for change in changes:
            if change.object_type == "user" and change.sets_field("password"):
                # Check if user is human (TYPE=PERSON)
                user = self.project.get_user(change.object_name)
                if user and user.type == "PERSON":
                    # Ensure RSA key is also set up
                    if not user.rsa_public_key:
                        warnings.append(
                            f"User {change.object_name} should have RSA key authentication "
                            "in addition to password for enhanced security."
                        )

        return ValidationResult.safe(warnings=warnings)

    def _check_network_policy_safety(self, changes: List["Change"]) -> ValidationResult:
        """Ensure network policy changes won't block access."""
        for change in changes:
            if change.object_type == "network_policy":
                # Ensure at least one admin has no network policy
                admins_without_policy = self._count_admins_without_network_policy()

                if admins_without_policy == 0:
                    return ValidationResult.unsafe(
                        "Network policy change would restrict all admin accounts. "
                        "At least one admin must have unrestricted network access.",
                        RiskLevel.CRITICAL,
                    )

        return ValidationResult.safe()

    def _check_resource_monitor_thresholds(
        self, changes: List["Change"]
    ) -> ValidationResult:
        """Prevent setting resource monitors to dangerous thresholds."""
        for change in changes:
            if change.object_type == "resource_monitor":
                if change.sets_field("suspend_at"):
                    threshold = change.get_new_value("suspend_at")

                    # Check if it's a production monitor
                    if change.object_name in HIGH_RISK_OBJECTS.get(
                        "resource_monitors", []
                    ):
                        if threshold >= THRESHOLDS["resource_monitor_safe_threshold"]:
                            return ValidationResult.unsafe(
                                f"Resource monitor {change.object_name} suspend threshold "
                                f"set to {threshold}%. This could halt production. "
                                f"Maximum safe threshold: {THRESHOLDS['resource_monitor_safe_threshold']}%",
                                RiskLevel.HIGH,
                            )

        return ValidationResult.safe()

    def _check_change_volume(self, changes: List["Change"]) -> ValidationResult:
        """Ensure change volume is within safe limits."""
        critical_count = sum(1 for c in changes if c.risk_level == RiskLevel.CRITICAL)

        if critical_count > THRESHOLDS["max_concurrent_critical_changes"]:
            return ValidationResult.unsafe(
                f"Too many critical changes ({critical_count}) in single batch. "
                f"Maximum allowed: {THRESHOLDS['max_concurrent_critical_changes']}. "
                "Split critical changes into separate operations.",
                RiskLevel.HIGH,
            )

        # Check user modifications
        user_changes = sum(1 for c in changes if c.object_type == "user")
        if user_changes > THRESHOLDS["max_users_modified_per_batch"]:
            warnings = [
                f"Large number of user changes ({user_changes}) in single batch. "
                f"Consider splitting into smaller batches."
            ]
            return ValidationResult.safe(warnings=warnings)

        return ValidationResult.safe()

    def _count_admin_passwords(self, exclude: Optional[List[str]] = None) -> int:
        """Count admin users with passwords, excluding specified users."""
        exclude = exclude or []
        count = 0

        for name, user in self.project.users.items():
            if name not in exclude:
                # Check for both ACCOUNTADMIN and ADMIN_ROLE (our business role)
                admin_roles = ["ACCOUNTADMIN", "ADMIN_ROLE"]
                if (
                    any(role in user.business_roles for role in admin_roles)
                    and user.password
                ):
                    count += 1

        return count

    def _count_admins_without_network_policy(self) -> int:
        """Count admin users without network policy restrictions."""
        count = 0

        for user in self.project.users.values():
            # Check for both ACCOUNTADMIN and ADMIN_ROLE
            admin_roles = ["ACCOUNTADMIN", "ADMIN_ROLE"]
            if (
                any(role in user.business_roles for role in admin_roles)
                and not user.network_policy
            ):
                count += 1

        return count


class BackupVerifier:
    """
    Verifies backup access methods are preserved.

    Ensures recovery accounts and alternative authentication methods
    remain available.
    """

    def __init__(self, project):
        """
        Initialize backup verifier.

        Args:
            project: SnowDDLProject instance
        """
        self.project = project

    def verify_backup_access(self, changes: List["Change"]) -> ValidationResult:
        """
        Verify backup access will be preserved after changes.

        Args:
            changes: List of Change objects to validate

        Returns:
            ValidationResult indicating if backup access is preserved
        """
        # Check sacred accounts exist and are untouched
        for account in SACRED_ACCOUNTS:
            user = self.project.get_user(account)

            if not user:
                return ValidationResult.unsafe(
                    f"Sacred account {account} not found. "
                    "All sacred accounts must exist before making critical changes.",
                    RiskLevel.CRITICAL,
                )

            # Ensure no changes affect sacred accounts
            for change in changes:
                if change.object_type == "user" and change.object_name == account:
                    return ValidationResult.unsafe(
                        f"Attempted to modify sacred account {account}. "
                        "Sacred accounts must never be modified by automated systems.",
                        RiskLevel.CRITICAL,
                    )

        # Ensure multiple authentication methods exist
        admin_auth_methods = self._count_admin_auth_methods()

        if admin_auth_methods < 2:
            return ValidationResult.unsafe(
                f"Insufficient authentication methods for admin accounts ({admin_auth_methods}). "
                "At least 2 different authentication methods required.",
                RiskLevel.CRITICAL,
            )

        return ValidationResult.safe()

    def _count_admin_auth_methods(self) -> int:
        """Count distinct authentication methods available for admin users."""
        methods = set()

        for user in self.project.users.values():
            # Check for both ACCOUNTADMIN and ADMIN_ROLE
            admin_roles = ["ACCOUNTADMIN", "ADMIN_ROLE"]
            if any(role in user.business_roles for role in admin_roles):
                if user.password:
                    methods.add("password")
                if user.rsa_public_key:
                    methods.add("rsa_key")

        return len(methods)
