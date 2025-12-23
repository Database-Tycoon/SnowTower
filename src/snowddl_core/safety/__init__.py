"""
SnowDDL Safety Framework.

This module provides multi-layered safety mechanisms to prevent catastrophic
failures when applying infrastructure changes to Snowflake.

Core components:
- SafetyValidator: Pre-execution validation of all changes
- BootstrapValidator: Validation for initial infrastructure creation
- RiskClassifier: Risk assessment and categorization
- CheckpointManager: State preservation and rollback capabilities
- Change tracking and audit trail
"""

from snowddl_core.safety.bootstrap import BootstrapValidator
from snowddl_core.safety.constants import (
    GOLDEN_RULES,
    SACRED_ACCOUNTS,
    RiskLevel,
)
from snowddl_core.safety.checkpoint import CheckpointManager
from snowddl_core.safety.risk import Change, ChangeType, RiskClassifier
from snowddl_core.safety.validators import (
    BackupVerifier,
    SafetyValidator,
    ValidationResult,
)

__all__ = [
    "SafetyValidator",
    "BootstrapValidator",
    "BackupVerifier",
    "CheckpointManager",
    "RiskClassifier",
    "ValidationResult",
    "Change",
    "ChangeType",
    "RiskLevel",
    "SACRED_ACCOUNTS",
    "GOLDEN_RULES",
]
