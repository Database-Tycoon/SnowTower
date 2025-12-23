"""
Shared schemas for SnowTower configuration validation

This module provides access to the unified configuration schemas
from the SnowTower CLI project. This allows both repositories to
use the same validation logic and ensures consistency.
"""

import sys
from pathlib import Path

# Add the CLI schemas to the Python path
cli_schemas_path = Path(__file__).parent.parent.parent.parent / "snowtower-cli" / "src"
if cli_schemas_path.exists():
    sys.path.insert(0, str(cli_schemas_path))

try:
    # Import all schemas from the CLI project
    from snowtower.schemas import *

    # Re-export everything for convenience
    __all__ = [
        # Enums and base classes
        "UserType",
        "AuthenticationMethod",
        "BaseSnowflakeConfig",
        # Connection schemas
        "SnowflakeConnectionConfig",
        # SnowDDL schemas
        "SnowDDLUserConfig",
        "SnowDDLWarehouseConfig",
        "SnowDDLDatabaseConfig",
        "SnowDDLRoleConfig",
        # Security schemas
        "NetworkPolicyConfig",
        "AuthenticationPolicyConfig",
        "PasswordPolicyConfig",
        "SessionPolicyConfig",
        # Validation system
        "ConfigurationValidator",
        "ValidationResult",
        "ConfigValidationError",
        "ValidationWarning",
    ]

except ImportError as e:
    # Fallback if CLI schemas aren't available
    import warnings

    warnings.warn(
        f"Cannot import SnowTower CLI schemas: {e}. "
        f"Configuration validation may not be available."
    )

    # Provide minimal fallback classes
    class ConfigurationValidator:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "SnowTower CLI schemas not available. "
                "Ensure the CLI project is available for shared schema validation."
            )

    class ValidationResult:
        pass

    ConfigValidationError = Exception
    ValidationWarning = Warning
