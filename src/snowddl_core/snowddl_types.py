"""
Type definitions and enums for SnowDDL objects.

This module provides type aliases, enums, and custom types used throughout
the SnowDDL framework.
"""

from enum import Enum
from typing import Literal, TypeAlias

# User Types
UserType: TypeAlias = Literal["PERSON", "SERVICE", "LEGACY_SERVICE"]


# Warehouse Sizes
class WarehouseSize(str, Enum):
    """Valid Snowflake warehouse sizes"""

    XSMALL = "X-Small"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    XLARGE = "X-Large"
    XXLARGE = "2X-Large"
    XXXLARGE = "3X-Large"
    XXXXLARGE = "4X-Large"
    XXXXXLARGE = "5X-Large"
    XXXXXXLARGE = "6X-Large"

    @classmethod
    def is_valid(cls, size: str) -> bool:
        """Check if a size string is valid"""
        return size in [s.value for s in cls]


# Warehouse Types
class WarehouseType(str, Enum):
    """Snowflake warehouse types"""

    STANDARD = "STANDARD"
    SNOWPARK_OPTIMIZED = "SNOWPARK-OPTIMIZED"


# Scaling Policies
class ScalingPolicy(str, Enum):
    """Multi-cluster warehouse scaling policies"""

    STANDARD = "STANDARD"
    ECONOMY = "ECONOMY"


# Object Types
class ObjectType(str, Enum):
    """All supported SnowDDL object types"""

    # Account-level objects
    USER = "user"
    BUSINESS_ROLE = "business_role"
    TECHNICAL_ROLE = "tech_role"
    WAREHOUSE = "warehouse"
    RESOURCE_MONITOR = "resource_monitor"
    AUTHENTICATION_POLICY = "authentication_policy"
    NETWORK_POLICY = "network_policy"
    PASSWORD_POLICY = "password_policy"
    SESSION_POLICY = "session_policy"

    # Database-level objects
    DATABASE = "database"

    # Schema-level objects
    SCHEMA = "schema"
    TABLE = "table"
    VIEW = "view"
    MATERIALIZED_VIEW = "materialized_view"
    DYNAMIC_TABLE = "dynamic_table"
    EXTERNAL_TABLE = "external_table"
    HYBRID_TABLE = "hybrid_table"
    ICEBERG_TABLE = "iceberg_table"
    EVENT_TABLE = "event_table"
    SEQUENCE = "sequence"
    STREAM = "stream"
    STAGE = "stage"
    FILE_FORMAT = "file_format"
    PIPE = "pipe"
    FUNCTION = "function"
    PROCEDURE = "procedure"
    TASK = "task"
    ALERT = "alert"
    MASKING_POLICY = "masking_policy"
    ROW_ACCESS_POLICY = "row_access_policy"
    AGGREGATION_POLICY = "aggregation_policy"
    PROJECTION_POLICY = "projection_policy"


# Validation Severity
class ValidationSeverity(str, Enum):
    """Severity levels for validation errors"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# Permission Levels
class PermissionLevel(str, Enum):
    """Database/schema permission levels"""

    OWNER = "owner"
    WRITE = "write"
    READ = "read"


# Database Permission Model
class PermissionModel(str, Enum):
    """Database permission models"""

    SCHEMA = "schema"
    SCHEMA_OWNER_WRITE = "schema_owner_write"
    SCHEMA_OWNER_READ = "schema_owner_read"


# Access Control Types
AccessLevel: TypeAlias = Literal["owner", "write", "read"]

# FQN (Fully Qualified Name) types
FQN: TypeAlias = (
    str  # Format: "DATABASE.SCHEMA.OBJECT" or "DATABASE.OBJECT" or "OBJECT"
)
DatabaseFQN: TypeAlias = str  # Format: "DATABASE"
SchemaFQN: TypeAlias = str  # Format: "DATABASE.SCHEMA"
ObjectFQN: TypeAlias = str  # Format: "DATABASE.SCHEMA.OBJECT"

# Dependency tuple type
DependencyTuple: TypeAlias = tuple[str, str]  # (object_type, fqn)
