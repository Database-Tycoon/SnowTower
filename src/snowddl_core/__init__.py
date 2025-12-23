"""
SnowDDL Core - Object-Oriented Framework for SnowDDL Configuration Management

This package provides a comprehensive, type-safe Python API for programmatically
managing SnowDDL configurations while maintaining 100% backward compatibility
with existing YAML files.

Key Features:
- Intuitive, Pythonic API for creating and manipulating Snowflake objects
- Type-safe with full type hints (Python 3.10+)
- Testable through dependency injection
- Extensible for future Snowflake features
- Comprehensive validation framework
- Dependency graph management
"""

from snowddl_core.base import (
    SnowDDLObject,
    AccountLevelObject,
    DatabaseLevelObject,
    SchemaLevelObject,
)
from snowddl_core.mixins import (
    PolicyReferenceMixin,
    TableLikeMixin,
    TransientMixin,
    EncryptedFieldMixin,
)
from snowddl_core.snowddl_types import (
    WarehouseSize,
    UserType,
    ObjectType,
    ValidationSeverity,
)
from snowddl_core.exceptions import (
    SnowDDLError,
    DependencyError,
    SerializationError,
    EncryptionError,
    CircularDependencyError,
    ConfigurationError,
    ObjectNotFoundError,
)
from snowddl_core.validation import (
    Validator,
    ValidationContext,
    ValidationRule,
    ValidationError,
)
from snowddl_core.account_objects import (
    User,
    BusinessRole,
    TechnicalRole,
    Warehouse,
    ResourceMonitor,
)
from snowddl_core.project import SnowDDLProject

__version__ = "1.0.0"

__all__ = [
    # Base classes
    "SnowDDLObject",
    "AccountLevelObject",
    "DatabaseLevelObject",
    "SchemaLevelObject",
    # Mixins
    "PolicyReferenceMixin",
    "TableLikeMixin",
    "TransientMixin",
    "EncryptedFieldMixin",
    # Types
    "WarehouseSize",
    "UserType",
    "ObjectType",
    "ValidationSeverity",
    # Exceptions
    "SnowDDLError",
    "ValidationError",
    "DependencyError",
    "SerializationError",
    "EncryptionError",
    "CircularDependencyError",
    "ConfigurationError",
    "ObjectNotFoundError",
    # Validation
    "Validator",
    "ValidationContext",
    "ValidationRule",
    # Account Objects
    "User",
    "BusinessRole",
    "TechnicalRole",
    "Warehouse",
    "ResourceMonitor",
    # Project Management
    "SnowDDLProject",
]
