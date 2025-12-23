"""
Validation framework for SnowDDL objects.

This module provides a comprehensive validation system for SnowDDL configurations,
including validation rules, severity levels, and validation orchestration.
"""

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from snowddl_core.snowddl_types import ValidationSeverity

if TYPE_CHECKING:
    from snowddl_core.base import SnowDDLObject


class ValidationError:
    """
    Represents a validation error or warning.

    Attributes:
        message: Error message
        severity: Error severity (ERROR, WARNING, INFO)
        object_type: Type of object being validated
        object_name: Name of object being validated
        field: Specific field that failed validation
    """

    def __init__(
        self,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        object_type: Optional[str] = None,
        object_name: Optional[str] = None,
        field: Optional[str] = None,
    ):
        """
        Initialize a ValidationError.

        Args:
            message: Error message
            severity: Error severity (ERROR, WARNING, INFO)
            object_type: Type of object being validated
            object_name: Name of object being validated
            field: Specific field that failed validation
        """
        self.message = message
        self.severity = severity
        self.object_type = object_type
        self.object_name = object_name
        self.field = field

    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        if self.object_type and self.object_name:
            obj_str = f"{self.object_type} {self.object_name}"
            if self.field:
                obj_str += f".{self.field}"
            return f"{prefix} {obj_str}: {self.message}"
        return f"{prefix} {self.message}"


class ValidationContext:
    """
    Context for validation with object lookups.

    Attributes:
        repository: Repository for loading objects
    """

    def __init__(self, repository: "SnowDDLRepository"):  # type: ignore
        """
        Initialize ValidationContext.

        Args:
            repository: Repository for loading objects
        """
        self.repository = repository

    def object_exists(self, object_type: str, fqn: str) -> bool:
        """
        Check if an object exists.

        Args:
            object_type: Type of object
            fqn: Fully qualified name

        Returns:
            True if object exists
        """
        try:
            self.repository.get_object(object_type, fqn)
            return True
        except KeyError:
            return False


class ValidationRule(ABC):
    """Abstract base for validation rules"""

    @abstractmethod
    def validate(
        self, obj: "SnowDDLObject", context: ValidationContext
    ) -> list[ValidationError]:
        """
        Validate an object.

        Args:
            obj: Object to validate
            context: Validation context

        Returns:
            List of validation errors
        """
        pass


class RequiredFieldsRule(ValidationRule):
    """Validates required fields are present"""

    def validate(
        self, obj: "SnowDDLObject", context: ValidationContext
    ) -> list[ValidationError]:
        """Validate required fields"""
        errors: list[ValidationError] = []

        # Import here to avoid circular dependency
        from snowddl_core.account_objects import User

        if isinstance(obj, User):
            if not obj.login_name:
                errors.append(
                    ValidationError(
                        "login_name is required",
                        object_type="user",
                        object_name=obj.name,
                        field="login_name",
                    )
                )

        return errors


class NamingConventionRule(ValidationRule):
    """Validates object naming conventions"""

    def __init__(self, pattern: str = r"^[A-Z][A-Z0-9_]*$"):
        self.pattern = re.compile(pattern)

    def validate(
        self, obj: "SnowDDLObject", context: ValidationContext
    ) -> list[ValidationError]:
        """Validate naming convention"""
        errors: list[ValidationError] = []

        if not self.pattern.match(obj.name):
            errors.append(
                ValidationError(
                    f"Name '{obj.name}' doesn't match convention {self.pattern.pattern}",
                    severity=ValidationSeverity.WARNING,
                    object_type=obj.object_type,
                    object_name=obj.name,
                    field="name",
                )
            )

        return errors


class ReferenceIntegrityRule(ValidationRule):
    """Validates object references exist"""

    def validate(
        self, obj: "SnowDDLObject", context: ValidationContext
    ) -> list[ValidationError]:
        """Validate reference integrity"""
        errors: list[ValidationError] = []

        for dep_type, dep_fqn in obj.get_dependencies():
            if not context.object_exists(dep_type, dep_fqn):
                errors.append(
                    ValidationError(
                        f"Reference to {dep_type} '{dep_fqn}' not found",
                        object_type=obj.object_type,
                        object_name=obj.name,
                    )
                )

        return errors


class SecurityBestPracticesRule(ValidationRule):
    """Validates security best practices"""

    def validate(
        self, obj: "SnowDDLObject", context: ValidationContext
    ) -> list[ValidationError]:
        """Validate security best practices"""
        errors: list[ValidationError] = []

        # Import here to avoid circular dependency
        from snowddl_core.account_objects import User

        if isinstance(obj, User):
            # SERVICE accounts should use RSA keys
            if obj.type == "SERVICE" and not obj.rsa_public_key:
                errors.append(
                    ValidationError(
                        "SERVICE accounts should use RSA key authentication",
                        severity=ValidationSeverity.WARNING,
                        object_type="user",
                        object_name=obj.name,
                    )
                )

            # PERSON accounts should have MFA
            if obj.type == "PERSON" and not obj.authentication_policy:
                errors.append(
                    ValidationError(
                        "PERSON accounts should have an authentication policy with MFA",
                        severity=ValidationSeverity.WARNING,
                        object_type="user",
                        object_name=obj.name,
                    )
                )

        return errors


class Validator:
    """
    Orchestrates validation rules.

    Provides a framework for running multiple validation rules against
    SnowDDL objects.
    """

    def __init__(self):
        self.rules: list[ValidationRule] = []

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule"""
        self.rules.append(rule)

    def add_default_rules(self) -> None:
        """Add standard validation rules"""
        self.add_rule(RequiredFieldsRule())
        self.add_rule(NamingConventionRule())
        self.add_rule(ReferenceIntegrityRule())
        self.add_rule(SecurityBestPracticesRule())

    def validate(
        self, obj: "SnowDDLObject", context: ValidationContext
    ) -> list[ValidationError]:
        """
        Validate a single object.

        Args:
            obj: Object to validate
            context: Validation context

        Returns:
            List of validation errors
        """
        errors: list[ValidationError] = []

        # Run object's own validation
        errors.extend(obj.validate())

        # Run all registered rules
        for rule in self.rules:
            errors.extend(rule.validate(obj, context))

        return errors

    def validate_all(
        self, objects: list["SnowDDLObject"], context: ValidationContext
    ) -> list[ValidationError]:
        """
        Validate all objects.

        Args:
            objects: List of objects to validate
            context: Validation context

        Returns:
            List of all validation errors
        """
        all_errors: list[ValidationError] = []

        for obj in objects:
            all_errors.extend(self.validate(obj, context))

        return all_errors
