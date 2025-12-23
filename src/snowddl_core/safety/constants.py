"""
Safety constants and configuration for SnowDDL operations.

This module defines critical safety rules, protected accounts, and risk levels
that govern all infrastructure changes.
"""

from enum import Enum, auto
from typing import Final, List


# Sacred accounts that must NEVER be modified by automated systems
SACRED_ACCOUNTS: Final[List[str]] = [
    "STEPHEN_RECOVERY",  # Emergency recovery account with no restrictions
    "SNOWDDL",  # SnowDDL service account for infrastructure management
]


# Golden Rules that must never be violated
GOLDEN_RULES: Final[List[str]] = [
    "NEVER modify STEPHEN_RECOVERY account",
    "NEVER remove all ACCOUNTADMIN passwords",
    "NEVER apply network policy without testing",
    "NEVER drop a database without backup verification",
    "NEVER change resource monitor to 100% suspend in PROD",
    "ALWAYS maintain at least 2 authentication methods per admin",
    "ALWAYS test password changes in DEV first",
    "ALWAYS create checkpoint before CRITICAL changes",
    "ALWAYS verify backup access before authentication changes",
    "ALWAYS validate MFA compliance for human users",
]


class RiskLevel(Enum):
    """Risk classification for infrastructure changes."""

    CRITICAL = auto()  # Can lock out ACCOUNTADMIN (passwords, network policies)
    HIGH = auto()  # Can break production (DROP DATABASE, resource monitors)
    MEDIUM = auto()  # Can impact operations (warehouse resizing, role changes)
    LOW = auto()  # Minimal impact (comments, descriptions)


class ChangeCategory(Enum):
    """Categories of infrastructure changes."""

    AUTHENTICATION = auto()  # Password, RSA key, MFA changes
    NETWORK = auto()  # Network policy modifications
    DESTRUCTIVE = auto()  # DROP operations
    PERMISSION = auto()  # Role and grant changes
    RESOURCE = auto()  # Warehouse and resource monitor changes
    CONFIGURATION = auto()  # Settings and parameters
    METADATA = auto()  # Comments, descriptions, tags


# Risk scoring weights
RISK_WEIGHTS = {
    ChangeCategory.AUTHENTICATION: 10.0,
    ChangeCategory.NETWORK: 9.0,
    ChangeCategory.DESTRUCTIVE: 8.0,
    ChangeCategory.PERMISSION: 5.0,
    ChangeCategory.RESOURCE: 4.0,
    ChangeCategory.CONFIGURATION: 2.0,
    ChangeCategory.METADATA: 1.0,
}


# Objects that require special handling
HIGH_RISK_OBJECTS = {
    "users": ["ALICE", "ACCOUNTADMIN", "SECURITYADMIN"],
    "databases": ["PRODUCTION", "PROD", "MAIN"],
    "warehouses": ["PRODUCTION_WH", "PROD_WH", "CRITICAL_WH"],
    "resource_monitors": ["PROD_MONITOR", "PRODUCTION_MONITOR"],
}


# Validation thresholds
THRESHOLDS = {
    "max_concurrent_critical_changes": 1,
    "max_users_modified_per_batch": 5,
    "max_warehouses_suspended": 2,
    "min_admin_accounts_with_password": 2,
    "resource_monitor_safe_threshold": 95,  # Percent
    "checkpoint_retention_days": 30,
}


# Staging configuration
STAGING_CONFIG = {
    "critical_changes_delay_seconds": 10,
    "high_risk_delay_seconds": 5,
    "medium_risk_delay_seconds": 2,
    "batch_size_by_risk": {
        RiskLevel.CRITICAL: 1,
        RiskLevel.HIGH: 3,
        RiskLevel.MEDIUM: 10,
        RiskLevel.LOW: 50,
    },
}
