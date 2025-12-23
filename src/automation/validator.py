"""
Security and Configuration Validator for User Deployments

Validates user configurations against security policies and best practices.
Includes checks for RSA keys, email domains, usernames, and role assignments.
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from rich.console import Console

console = Console()


class ValidationError(Exception):
    """Raised when validation fails"""

    pass


class ValidationSeverity(str, Enum):
    """Severity levels for validation findings"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationFinding:
    """A single validation finding"""

    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    recommendation: Optional[str] = None

    def __str__(self) -> str:
        """String representation"""
        prefix = {
            ValidationSeverity.ERROR: "❌",
            ValidationSeverity.WARNING: "⚠️",
            ValidationSeverity.INFO: "ℹ️",
        }[self.severity]

        msg = f"{prefix} [{self.severity.value.upper()}] {self.message}"
        if self.field:
            msg = f"{msg} (field: {self.field})"
        if self.recommendation:
            msg = f"{msg}\n  → Recommendation: {self.recommendation}"

        return msg


@dataclass
class ValidationResult:
    """Complete validation result"""

    is_valid: bool
    findings: List[ValidationFinding] = field(default_factory=list)

    def add_error(
        self,
        message: str,
        field: Optional[str] = None,
        recommendation: Optional[str] = None,
    ):
        """Add an error finding"""
        self.findings.append(
            ValidationFinding(
                severity=ValidationSeverity.ERROR,
                message=message,
                field=field,
                recommendation=recommendation,
            )
        )
        self.is_valid = False

    def add_warning(
        self,
        message: str,
        field: Optional[str] = None,
        recommendation: Optional[str] = None,
    ):
        """Add a warning finding"""
        self.findings.append(
            ValidationFinding(
                severity=ValidationSeverity.WARNING,
                message=message,
                field=field,
                recommendation=recommendation,
            )
        )

    def add_info(self, message: str, field: Optional[str] = None):
        """Add an info finding"""
        self.findings.append(
            ValidationFinding(
                severity=ValidationSeverity.INFO, message=message, field=field
            )
        )

    @property
    def errors(self) -> List[ValidationFinding]:
        """Get all error findings"""
        return [f for f in self.findings if f.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationFinding]:
        """Get all warning findings"""
        return [f for f in self.findings if f.severity == ValidationSeverity.WARNING]

    @property
    def infos(self) -> List[ValidationFinding]:
        """Get all info findings"""
        return [f for f in self.findings if f.severity == ValidationSeverity.INFO]

    def print_summary(self):
        """Print validation summary"""
        if self.is_valid:
            console.print("[green]✓ Validation passed![/green]")
        else:
            console.print(
                f"[red]✗ Validation failed with {len(self.errors)} error(s)[/red]"
            )

        if self.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for finding in self.errors:
                console.print(f"  {finding}")

        if self.warnings:
            console.print(
                f"\n[bold yellow]Warnings ({len(self.warnings)}):[/bold yellow]"
            )
            for finding in self.warnings:
                console.print(f"  {finding}")

        if self.infos:
            console.print(f"\n[bold blue]Info ({len(self.infos)}):[/bold blue]")
            for finding in self.infos:
                console.print(f"  {finding}")


class UserConfigValidator:
    """
    Validates user configurations for security and compliance.

    Performs comprehensive validation including:
    - Username format and SQL injection prevention
    - Email domain allowlisting
    - RSA public key format
    - Role assignment validation
    - Security policy compliance
    - MFA requirements
    """

    # Allowed email domains (configurable)
    ALLOWED_EMAIL_DOMAINS = [
        "databasetycoon.com",
        "company.com",
        "example.com",
        # Add your organization's domains here
    ]

    # Username validation pattern (alphanumeric and underscore only)
    USERNAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")

    # Email validation pattern
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # SQL injection patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"['\";\-\-]",  # Common SQL characters
        r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|TRUNCATE)\s+",  # SQL keywords with following space
        r"(\bOR\b|\bAND\b)\s+[0-9]+\s*=\s*[0-9]+",  # OR 1=1 style
        r"[\x00-\x1F\x7F]",  # Control characters
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize validator.

        Args:
            strict_mode: Enable strict validation (recommended for production)
        """
        self.strict_mode = strict_mode

    def validate_user_config(
        self, username: str, user_config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate complete user configuration.

        Args:
            username: Username to validate
            user_config: User configuration dictionary

        Returns:
            ValidationResult with all findings
        """
        result = ValidationResult(is_valid=True)

        # Validate username
        self._validate_username(username, result)

        # Validate email
        email = user_config.get("email")
        if email:
            self._validate_email(email, result)

        # Validate authentication
        self._validate_authentication(user_config, result)

        # Validate RSA key if present
        rsa_key = user_config.get("rsa_public_key")
        if rsa_key:
            self._validate_rsa_key(rsa_key, result)

        # Validate user type specific requirements
        user_type = user_config.get("type", "PERSON")
        self._validate_user_type_requirements(user_type, user_config, result)

        # Validate roles
        self._validate_roles(user_config, result)

        # Validate security policies
        self._validate_security_policies(user_type, user_config, result)

        # Check for SQL injection attempts
        self._check_sql_injection(user_config, result)

        # Additional security checks
        self._validate_security_best_practices(user_config, result)

        return result

    def _validate_username(self, username: str, result: ValidationResult):
        """Validate username format and security"""
        if not username:
            result.add_error("Username is required", field="username")
            return

        # Check pattern
        if not self.USERNAME_PATTERN.match(username):
            result.add_error(
                f"Username '{username}' does not match required pattern",
                field="username",
                recommendation="Use uppercase letters, numbers, and underscores only (3-64 chars)",
            )

        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, username, re.IGNORECASE):
                result.add_error(
                    f"Username contains potentially dangerous characters or SQL keywords",
                    field="username",
                    recommendation="Remove special characters and SQL keywords",
                )
                break

        # Length check
        if len(username) < 3:
            result.add_error(
                "Username too short (minimum 3 characters)", field="username"
            )
        elif len(username) > 64:
            result.add_error(
                "Username too long (maximum 64 characters)", field="username"
            )

        # Reserved keywords check
        reserved_keywords = ["ADMIN", "ROOT", "SYSTEM", "SNOWFLAKE", "PUBLIC"]
        if username.upper() in reserved_keywords:
            result.add_warning(
                f"Username '{username}' is a reserved keyword",
                field="username",
                recommendation="Consider using a different username",
            )

    def _validate_email(self, email: str, result: ValidationResult):
        """Validate email address"""
        if not email:
            result.add_error("Email is required for PERSON users", field="email")
            return

        # Basic format check
        if not self.EMAIL_PATTERN.match(email):
            result.add_error(
                f"Invalid email format: {email}",
                field="email",
                recommendation="Provide a valid email address",
            )
            return

        # Domain allowlist check (if configured)
        if self.ALLOWED_EMAIL_DOMAINS:
            domain = email.split("@")[-1].lower()
            if domain not in self.ALLOWED_EMAIL_DOMAINS:
                if self.strict_mode:
                    result.add_error(
                        f"Email domain '{domain}' not in allowlist",
                        field="email",
                        recommendation=f"Use email from: {', '.join(self.ALLOWED_EMAIL_DOMAINS)}",
                    )
                else:
                    result.add_warning(
                        f"Email domain '{domain}' not in standard allowlist",
                        field="email",
                    )

    def _validate_authentication(
        self, user_config: Dict[str, Any], result: ValidationResult
    ):
        """Validate authentication configuration"""
        has_password = bool(user_config.get("password"))
        has_rsa_key = bool(user_config.get("rsa_public_key"))

        if not has_password and not has_rsa_key:
            result.add_error(
                "User must have at least one authentication method",
                recommendation="Configure password or RSA key",
            )

        # Check password format if present
        if has_password:
            password_value = user_config.get("password", "")

            # Should be Fernet encrypted (starts with gAAAAA) or !decrypt tag
            if not (
                password_value.startswith("gAAAAA")
                or password_value.startswith("!decrypt")
            ):
                result.add_error(
                    "Password must be Fernet encrypted",
                    field="password",
                    recommendation="Use PasswordGenerator to create encrypted passwords",
                )

        # Recommend RSA keys for service accounts
        user_type = user_config.get("type", "PERSON")
        if user_type == "SERVICE" and not has_rsa_key:
            result.add_warning(
                "Service accounts should use RSA key authentication",
                recommendation="Generate RSA key pair for service account",
            )

    def _validate_rsa_key(self, rsa_key: str, result: ValidationResult):
        """Validate RSA public key format"""
        if not rsa_key or rsa_key.strip() == "":
            result.add_error("RSA public key is empty", field="rsa_public_key")
            return

        # Remove whitespace for validation
        key_clean = "".join(rsa_key.split())

        # Should be base64 encoded
        if not re.match(r"^[A-Za-z0-9+/=]+$", key_clean):
            result.add_error(
                "RSA public key is not valid base64",
                field="rsa_public_key",
                recommendation="Ensure key is properly formatted base64",
            )

        # Minimum length check (RSA 2048 public key is ~392 base64 chars)
        if len(key_clean) < 200:
            result.add_warning(
                "RSA public key seems too short",
                field="rsa_public_key",
                recommendation="Verify key is complete and uses at least 2048-bit RSA",
            )

    def _validate_user_type_requirements(
        self, user_type: str, user_config: Dict[str, Any], result: ValidationResult
    ):
        """Validate type-specific requirements"""
        if user_type == "PERSON":
            # PERSON users require personal information
            required_fields = ["first_name", "last_name", "email"]
            for field in required_fields:
                if not user_config.get(field):
                    result.add_error(
                        f"PERSON user missing required field: {field}", field=field
                    )

        elif user_type == "SERVICE":
            # SERVICE accounts should have descriptive comments
            comment = user_config.get("comment", "")
            if not comment or len(comment) < 10:
                result.add_warning(
                    "Service account should have descriptive comment",
                    field="comment",
                    recommendation="Add purpose and ownership information",
                )

    def _validate_roles(self, user_config: Dict[str, Any], result: ValidationResult):
        """Validate role assignments"""
        business_roles = user_config.get("business_roles", [])

        if not business_roles:
            result.add_error(
                "User must have at least one business role",
                field="business_roles",
                recommendation="Assign appropriate business roles",
            )

        # Check for overly permissive roles
        dangerous_roles = ["ACCOUNTADMIN", "SECURITYADMIN", "SYSADMIN"]
        assigned_dangerous = [r for r in business_roles if r in dangerous_roles]

        if assigned_dangerous:
            result.add_warning(
                f"User assigned high-privilege roles: {', '.join(assigned_dangerous)}",
                field="business_roles",
                recommendation="Verify this level of access is required",
            )

    def _validate_security_policies(
        self, user_type: str, user_config: Dict[str, Any], result: ValidationResult
    ):
        """Validate security policy assignments"""
        if user_type == "PERSON":
            # PERSON users should have network policy
            if not user_config.get("network_policy"):
                result.add_warning(
                    "PERSON user should have network policy assigned",
                    field="network_policy",
                    recommendation="Assign network policy for IP restriction",
                )

            # MFA compliance check
            has_mfa_policy = bool(user_config.get("authentication_policy"))
            has_dual_auth = bool(user_config.get("password")) and bool(
                user_config.get("rsa_public_key")
            )

            if not has_mfa_policy and not has_dual_auth:
                result.add_warning(
                    "PERSON user may not be MFA compliant",
                    recommendation="Set authentication_policy or configure dual authentication",
                )

    def _check_sql_injection(
        self, user_config: Dict[str, Any], result: ValidationResult
    ):
        """Check all string fields for SQL injection attempts"""
        # Critical fields that must be strictly validated
        critical_fields = [
            "first_name",
            "last_name",
            "email",
            "display_name",
            "default_warehouse",
            "default_role",
        ]

        # Non-critical fields - only check for dangerous characters, not SQL keywords
        informational_fields = ["comment"]

        for field in critical_fields:
            value = user_config.get(field)
            if value and isinstance(value, str):
                for pattern in self.SQL_INJECTION_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        result.add_error(
                            f"Field '{field}' contains potentially dangerous SQL content",
                            field=field,
                            recommendation="Remove SQL keywords and special characters",
                        )
                        break

        # For comment field, only check for dangerous characters
        for field in informational_fields:
            value = user_config.get(field)
            if value and isinstance(value, str):
                # Only check for truly dangerous characters (quotes, semicolons, control chars)
                # Allow dashes since they're common in comments
                if re.search(r"['\";]", value) or re.search(r"[\x00-\x1F\x7F]", value):
                    result.add_warning(
                        f"Field '{field}' contains potentially dangerous characters",
                        field=field,
                        recommendation="Review for security concerns",
                    )

    def _validate_security_best_practices(
        self, user_config: Dict[str, Any], result: ValidationResult
    ):
        """Additional security best practice checks"""
        # Disabled users should not have authentication
        if user_config.get("disabled", False):
            if user_config.get("password") or user_config.get("rsa_public_key"):
                result.add_info(
                    "Disabled user still has authentication configured",
                    recommendation="Consider removing authentication from disabled users",
                )

        # Default warehouse check
        if not user_config.get("default_warehouse"):
            result.add_warning(
                "No default warehouse assigned",
                field="default_warehouse",
                recommendation="Assign appropriate default warehouse",
            )

        # Comment field recommended
        if not user_config.get("comment"):
            result.add_info(
                "No comment/description provided",
                field="comment",
                recommendation="Add descriptive comment for auditability",
            )

    def validate_batch(
        self, configs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple user configurations.

        Args:
            configs: Dictionary mapping usernames to configurations

        Returns:
            Dictionary mapping usernames to ValidationResults
        """
        results = {}

        for username, user_config in configs.items():
            results[username] = self.validate_user_config(username, user_config)

        return results
