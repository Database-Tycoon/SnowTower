"""
Mixin classes for SnowDDL objects.

This module provides mixin classes that add specific functionality to SnowDDL
objects through multiple inheritance.
"""

import os
from typing import Optional

from cryptography.fernet import Fernet

from snowddl_core.exceptions import EncryptionError
from snowddl_core.snowddl_types import DependencyTuple


class PolicyReferenceMixin:
    """
    Mixin for objects that can reference account-level policies.

    Used by: User, Table, View

    Attributes:
        authentication_policy: Name of authentication policy
        network_policy: Name of network policy
    """

    def _get_policy_dependencies(self) -> list[DependencyTuple]:
        """Get dependencies on policies"""
        deps: list[DependencyTuple] = []
        if self.authentication_policy:
            deps.append(("authentication_policy", self.authentication_policy))
        if self.network_policy:
            deps.append(("network_policy", self.network_policy))
        return deps


class TableLikeMixin:
    """
    Mixin for objects that support data governance policies.

    Used by: Table, View, MaterializedView

    Attributes:
        masking_policies: Column-level masking policies {column: policy}
        row_access_policy: Row-level access policy
        aggregation_policy: Aggregation policy for privacy
        projection_policies: Column-level projection policies {column: policy}
    """

    def apply_masking_policy(self, column: str, policy: str) -> None:
        """
        Apply masking policy to a column

        Args:
            column: Column name
            policy: Policy name
        """
        self.masking_policies[column] = policy

    def apply_projection_policy(self, column: str, policy: str) -> None:
        """
        Apply projection policy to a column

        Args:
            column: Column name
            policy: Policy name
        """
        self.projection_policies[column] = policy

    def _get_policy_dependencies(self) -> list[DependencyTuple]:
        """Get dependencies on all applied policies"""
        deps: list[DependencyTuple] = []

        for policy in self.masking_policies.values():
            deps.append(("masking_policy", policy))

        for policy in self.projection_policies.values():
            deps.append(("projection_policy", policy))

        if self.row_access_policy:
            deps.append(("row_access_policy", self.row_access_policy))

        if self.aggregation_policy:
            deps.append(("aggregation_policy", self.aggregation_policy))

        return deps


class TransientMixin:
    """
    Mixin for objects supporting transient and retention settings.

    Used by: Database, Schema, Table, DynamicTable

    Attributes:
        is_transient: Whether object is transient (no Fail-safe period)
        retention_time: Time-travel retention period in days (0-90)
    """

    def set_retention(self, days: int) -> None:
        """
        Set time-travel retention period

        Args:
            days: Retention period (0-90 days)

        Raises:
            ValueError: If days not in valid range
        """
        if days < 0 or days > 90:
            raise ValueError("Retention time must be between 0 and 90 days")
        self.retention_time = days


class EncryptedFieldMixin:
    """
    Mixin for objects with encrypted fields (passwords).

    Provides Fernet encryption/decryption for sensitive fields.

    Attributes:
        password: Encrypted password (stored with !decrypt tag)
    """

    def set_password(self, password: str, fernet_key: Optional[str] = None) -> None:
        """
        Set encrypted password using Fernet encryption.

        Args:
            password: Plain text password
            fernet_key: Fernet encryption key (or env SNOWFLAKE_CONFIG_FERNET_KEYS)

        Raises:
            EncryptionError: If encryption fails
        """
        if not fernet_key:
            fernet_key = os.getenv("SNOWFLAKE_CONFIG_FERNET_KEYS")

        if not fernet_key:
            raise EncryptionError(
                "Fernet key required for password encryption. "
                "Set SNOWFLAKE_CONFIG_FERNET_KEYS environment variable."
            )

        try:
            fernet = Fernet(fernet_key.encode())
            encrypted = fernet.encrypt(password.encode()).decode()
            self.password = f"!decrypt {encrypted}"
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt password: {e}")

    def get_plain_password(self, fernet_key: Optional[str] = None) -> Optional[str]:
        """
        Decrypt password for authentication.

        Args:
            fernet_key: Fernet encryption key (or env SNOWFLAKE_CONFIG_FERNET_KEYS)

        Returns:
            Decrypted password or None

        Raises:
            EncryptionError: If decryption fails
        """
        if not self.password:
            return None

        # If not encrypted, return as-is
        if not self.password.startswith("!decrypt "):
            return self.password

        if not fernet_key:
            fernet_key = os.getenv("SNOWFLAKE_CONFIG_FERNET_KEYS")

        if not fernet_key:
            raise EncryptionError(
                "Fernet key required for password decryption. "
                "Set SNOWFLAKE_CONFIG_FERNET_KEYS environment variable."
            )

        try:
            encrypted = self.password.replace("!decrypt ", "")
            fernet = Fernet(fernet_key.encode())
            return fernet.decrypt(encrypted.encode()).decode()
        except Exception as e:
            raise EncryptionError(f"Failed to decrypt password: {e}")
