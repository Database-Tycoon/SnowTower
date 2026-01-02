"""
Account-level object implementations.

This module provides concrete implementations for account-level Snowflake objects
including Users, Roles, Warehouses, and Resource Monitors.
"""

from typing import Any, ClassVar, Optional

from snowddl_core.base import AccountLevelObject
from snowddl_core.mixins import EncryptedFieldMixin, PolicyReferenceMixin
from snowddl_core.snowddl_types import (
    AccessLevel,
    DependencyTuple,
    UserType,
    WarehouseSize,
    WarehouseType,
    ScalingPolicy,
)
from snowddl_core.validation import ValidationError


class User(PolicyReferenceMixin, EncryptedFieldMixin, AccountLevelObject):
    """
    Snowflake user account with authentication and authorization.

    Supports dual authentication (password + RSA keys) and MFA compliance.

    Attributes:
        login_name: Login name for authentication
        type: User type (PERSON, SERVICE, LEGACY_SERVICE)
        display_name: Display name
        first_name: First name
        last_name: Last name
        email: Email address (required for PERSON type)
        disabled: Whether user is disabled
        rsa_public_key: Primary RSA public key
        rsa_public_key_2: Secondary RSA public key
        business_roles: List of business role names
        default_warehouse: Default warehouse name
        default_namespace: Default database.schema
        session_params: Session parameters
    """

    object_type: ClassVar[str] = "user"

    def __init__(
        self,
        name: str,
        login_name: str,
        type: UserType = "PERSON",
        display_name: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        disabled: bool = False,
        password: Optional[str] = None,
        rsa_public_key: Optional[str] = None,
        rsa_public_key_2: Optional[str] = None,
        business_roles: Optional[list[str]] = None,
        default_warehouse: Optional[str] = None,
        default_namespace: Optional[str] = None,
        authentication_policy: Optional[str] = None,
        network_policy: Optional[str] = None,
        session_params: Optional[dict[str, Any]] = None,
        comment: Optional[str] = None,
    ):
        """
        Initialize a User object.

        Args:
            name: User name
            login_name: Login name for authentication
            type: User type (PERSON, SERVICE, LEGACY_SERVICE)
            display_name: Display name
            first_name: First name
            last_name: Last name
            email: Email address (required for PERSON type)
            disabled: Whether user is disabled
            password: Encrypted password
            rsa_public_key: Primary RSA public key
            rsa_public_key_2: Secondary RSA public key
            business_roles: List of business role names
            default_warehouse: Default warehouse name
            default_namespace: Default database.schema
            authentication_policy: Authentication policy name
            network_policy: Network policy name
            session_params: Session parameters
            comment: Optional descriptive comment
        """
        # Initialize base class
        super().__init__(name=name, comment=comment)

        # Set mixin attributes directly
        self.authentication_policy = authentication_policy
        self.network_policy = network_policy
        self.password = password

        # Set User-specific attributes
        self.login_name = login_name
        self.type = type
        self.display_name = display_name
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.disabled = disabled
        self.rsa_public_key = rsa_public_key
        self.rsa_public_key_2 = rsa_public_key_2
        self.business_roles = business_roles or []
        self.default_warehouse = default_warehouse
        self.default_namespace = default_namespace
        self.session_params = session_params or {}

    def set_rsa_key(self, public_key: str) -> None:
        """
        Set RSA public key for key-pair authentication

        Args:
            public_key: RSA public key (PEM format or raw)
        """
        # Remove headers and whitespace
        key = public_key.replace("-----BEGIN PUBLIC KEY-----", "")
        key = key.replace("-----END PUBLIC KEY-----", "")
        key = "".join(key.split())
        self.rsa_public_key = key

    def add_role(self, role_name: str) -> None:
        """Add a business role to this user"""
        if role_name not in self.business_roles:
            self.business_roles.append(role_name)

    def remove_role(self, role_name: str) -> None:
        """Remove a business role from this user"""
        if role_name in self.business_roles:
            self.business_roles.remove(role_name)

    def to_yaml(self) -> dict[str, Any]:
        """Convert to YAML format"""
        data: dict[str, Any] = {}

        # Basic identity
        if self.type != "PERSON":
            data["type"] = self.type
        if self.first_name:
            data["first_name"] = self.first_name
        if self.last_name:
            data["last_name"] = self.last_name
        if self.login_name:
            data["login_name"] = self.login_name
        if self.display_name:
            data["display_name"] = self.display_name
        if self.comment:
            data["comment"] = self.comment
        if self.email:
            data["email"] = self.email

        # Authentication
        if self.rsa_public_key:
            data["rsa_public_key"] = self.rsa_public_key
        if self.rsa_public_key_2:
            data["rsa_public_key_2"] = self.rsa_public_key_2
        if self.password:
            data["password"] = self.password

        # Authorization
        if self.business_roles:
            data["business_roles"] = self.business_roles
        if self.default_warehouse:
            data["default_warehouse"] = self.default_warehouse
        if self.default_namespace:
            data["default_namespace"] = self.default_namespace

        # Policies
        if self.authentication_policy:
            data["authentication_policy"] = self.authentication_policy
        if self.network_policy:
            data["network_policy"] = self.network_policy

        # State
        if self.disabled:
            data["disabled"] = self.disabled

        # Session
        if self.session_params:
            data["session_params"] = self.session_params

        return data

    @classmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> "User":
        """Create User from YAML data"""
        return cls(
            name=name,
            login_name=data.get("login_name", name),
            type=data.get("type", "PERSON"),
            display_name=data.get("display_name"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            disabled=data.get("disabled", False),
            password=data.get("password"),
            rsa_public_key=data.get("rsa_public_key"),
            rsa_public_key_2=data.get("rsa_public_key_2"),
            business_roles=data.get("business_roles", []),
            default_warehouse=data.get("default_warehouse"),
            default_namespace=data.get("default_namespace"),
            authentication_policy=data.get("authentication_policy"),
            network_policy=data.get("network_policy"),
            session_params=data.get("session_params", {}),
            comment=data.get("comment"),
        )

    def validate(self) -> list[ValidationError]:
        """Validate user configuration"""
        errors: list[ValidationError] = []

        # Type-specific validation
        if self.type == "PERSON":
            if not self.email:
                errors.append(
                    ValidationError(f"User {self.name}: PERSON type requires email")
                )
            if (
                not self.authentication_policy
                and not self.password
                and not self.rsa_public_key
            ):
                errors.append(
                    ValidationError(
                        f"User {self.name}: PERSON type requires authentication"
                    )
                )

        if self.type == "SERVICE":
            if not self.rsa_public_key:
                errors.append(
                    ValidationError(
                        f"User {self.name}: SERVICE type should use RSA key authentication"
                    )
                )

        # Validate email format
        if self.email and "@" not in self.email:
            errors.append(ValidationError(f"User {self.name}: Invalid email format"))

        return errors

    def get_dependencies(self) -> list[DependencyTuple]:
        """Get user dependencies"""
        deps: list[DependencyTuple] = []

        # Role dependencies
        for role in self.business_roles:
            deps.append(("business_role", role))

        # Warehouse dependency
        if self.default_warehouse:
            deps.append(("warehouse", self.default_warehouse))

        # Policy dependencies
        deps.extend(self._get_policy_dependencies())

        return deps


class BusinessRole(AccountLevelObject):
    """
    High-level role combining technical roles and warehouse access.

    Provides database/schema-level permissions and warehouse usage.

    Attributes:
        database_owner: Databases with owner access
        database_write: Databases with write access
        database_read: Databases with read access
        schema_owner: Schemas with owner access (DATABASE.SCHEMA format)
        schema_write: Schemas with write access
        schema_read: Schemas with read access
        share_read: Shares with read access
        warehouse_usage: Warehouses with usage permission
        warehouse_monitor: Warehouses with monitor permission
        tech_roles: Technical roles granted to this business role
        global_roles: Global Snowflake roles
    """

    object_type: ClassVar[str] = "business_role"

    def __init__(
        self,
        name: str,
        database_owner: Optional[list[str]] = None,
        database_write: Optional[list[str]] = None,
        database_read: Optional[list[str]] = None,
        schema_owner: Optional[list[str]] = None,
        schema_write: Optional[list[str]] = None,
        schema_read: Optional[list[str]] = None,
        share_read: Optional[list[str]] = None,
        warehouse_usage: Optional[list[str]] = None,
        warehouse_monitor: Optional[list[str]] = None,
        tech_roles: Optional[list[str]] = None,
        global_roles: Optional[list[str]] = None,
        comment: Optional[str] = None,
    ):
        """
        Initialize a BusinessRole object.

        Args:
            name: Role name
            database_owner: Databases with owner access
            database_write: Databases with write access
            database_read: Databases with read access
            schema_owner: Schemas with owner access (DATABASE.SCHEMA format)
            schema_write: Schemas with write access
            schema_read: Schemas with read access
            share_read: Shares with read access
            warehouse_usage: Warehouses with usage permission
            warehouse_monitor: Warehouses with monitor permission
            tech_roles: Technical roles granted to this business role
            global_roles: Global Snowflake roles
            comment: Optional descriptive comment
        """
        super().__init__(name=name, comment=comment)
        self.database_owner = database_owner or []
        self.database_write = database_write or []
        self.database_read = database_read or []
        self.schema_owner = schema_owner or []
        self.schema_write = schema_write or []
        self.schema_read = schema_read or []
        self.share_read = share_read or []
        self.warehouse_usage = warehouse_usage or []
        self.warehouse_monitor = warehouse_monitor or []
        self.tech_roles = tech_roles or []
        self.global_roles = global_roles or []

    def grant_database_access(self, database: str, level: AccessLevel) -> None:
        """Grant database-level access"""
        if level == "owner" and database not in self.database_owner:
            self.database_owner.append(database)
        elif level == "write" and database not in self.database_write:
            self.database_write.append(database)
        elif level == "read" and database not in self.database_read:
            self.database_read.append(database)

    def grant_schema_access(self, schema_fqn: str, level: AccessLevel) -> None:
        """Grant schema-level access (schema_fqn = DATABASE.SCHEMA)"""
        if level == "owner" and schema_fqn not in self.schema_owner:
            self.schema_owner.append(schema_fqn)
        elif level == "write" and schema_fqn not in self.schema_write:
            self.schema_write.append(schema_fqn)
        elif level == "read" and schema_fqn not in self.schema_read:
            self.schema_read.append(schema_fqn)

    def add_warehouse_usage(self, warehouse: str) -> None:
        """Grant USAGE on warehouse"""
        if warehouse not in self.warehouse_usage:
            self.warehouse_usage.append(warehouse)

    def add_tech_role(self, role: str) -> None:
        """Add technical role to this business role"""
        if role not in self.tech_roles:
            self.tech_roles.append(role)

    def to_yaml(self) -> dict[str, Any]:
        """Convert to YAML format"""
        data: dict[str, Any] = {}

        if self.database_owner:
            data["database_owner"] = self.database_owner
        if self.database_write:
            data["database_write"] = self.database_write
        if self.database_read:
            data["database_read"] = self.database_read
        if self.schema_owner:
            data["schema_owner"] = self.schema_owner
        if self.schema_write:
            data["schema_write"] = self.schema_write
        if self.schema_read:
            data["schema_read"] = self.schema_read
        if self.share_read:
            data["share_read"] = self.share_read
        if self.warehouse_usage:
            data["warehouse_usage"] = self.warehouse_usage
        if self.warehouse_monitor:
            data["warehouse_monitor"] = self.warehouse_monitor
        if self.tech_roles:
            data["tech_roles"] = self.tech_roles
        if self.global_roles:
            data["global_roles"] = self.global_roles
        if self.comment:
            data["comment"] = self.comment

        return data

    @classmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> "BusinessRole":
        """Create BusinessRole from YAML"""
        return cls(
            name=name,
            database_owner=data.get("database_owner", []),
            database_write=data.get("database_write", []),
            database_read=data.get("database_read", []),
            schema_owner=data.get("schema_owner", []),
            schema_write=data.get("schema_write", []),
            schema_read=data.get("schema_read", []),
            share_read=data.get("share_read", []),
            warehouse_usage=data.get("warehouse_usage", []),
            warehouse_monitor=data.get("warehouse_monitor", []),
            tech_roles=data.get("tech_roles", []),
            global_roles=data.get("global_roles", []),
            comment=data.get("comment"),
        )

    def validate(self) -> list[ValidationError]:
        """Validate business role configuration"""
        errors: list[ValidationError] = []

        # Validate schema FQN format
        for schema in self.schema_owner + self.schema_write + self.schema_read:
            if "." not in schema:
                errors.append(
                    ValidationError(
                        f"BusinessRole {self.name}: Schema '{schema}' must be "
                        f"fully qualified (DATABASE.SCHEMA)"
                    )
                )

        return errors

    def get_dependencies(self) -> list[DependencyTuple]:
        """Get business role dependencies"""
        deps: list[DependencyTuple] = []

        # Database dependencies
        for db in self.database_owner + self.database_write + self.database_read:
            deps.append(("database", db))

        # Warehouse dependencies
        for wh in self.warehouse_usage + self.warehouse_monitor:
            deps.append(("warehouse", wh))

        # Technical role dependencies
        for role in self.tech_roles:
            deps.append(("tech_role", role))

        return deps


class TechnicalRole(AccountLevelObject):
    """
    Technical role for specific object permissions.

    Attributes:
        comment: Role description
    """

    object_type: ClassVar[str] = "tech_role"

    def to_yaml(self) -> dict[str, Any]:
        """Convert to YAML format"""
        data: dict[str, Any] = {}
        if self.comment:
            data["comment"] = self.comment
        return data

    @classmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> "TechnicalRole":
        """Create TechnicalRole from YAML"""
        return cls(
            name=name,
            comment=data.get("comment"),
        )

    def validate(self) -> list[ValidationError]:
        """Validate technical role configuration"""
        return []


class Warehouse(AccountLevelObject):
    """
    Snowflake compute warehouse for query execution.

    Attributes:
        size: Warehouse size (X-Small to 6X-Large)
        type: Warehouse type (STANDARD, SNOWPARK-OPTIMIZED)
        min_cluster_count: Minimum cluster count
        max_cluster_count: Maximum cluster count
        scaling_policy: Scaling policy (STANDARD, ECONOMY)
        auto_suspend: Auto-suspend timeout in seconds
        resource_monitor: Resource monitor name
        global_resource_monitor: Global resource monitor name
        enable_query_acceleration: Enable query acceleration
        query_acceleration_max_scale_factor: Max scale factor
        resource_constraint: Resource constraint (Snowpark)
        warehouse_params: Additional warehouse parameters
    """

    object_type: ClassVar[str] = "warehouse"

    def __init__(
        self,
        name: str,
        size: str = "X-Small",
        type: str = "STANDARD",
        min_cluster_count: int = 1,
        max_cluster_count: int = 1,
        scaling_policy: str = "STANDARD",
        auto_suspend: int = 60,
        resource_monitor: Optional[str] = None,
        global_resource_monitor: Optional[str] = None,
        enable_query_acceleration: bool = False,
        query_acceleration_max_scale_factor: int = 8,
        resource_constraint: Optional[str] = None,
        warehouse_params: Optional[dict[str, Any]] = None,
        comment: Optional[str] = None,
    ):
        """
        Initialize a Warehouse object.

        Args:
            name: Warehouse name
            size: Warehouse size (X-Small to 6X-Large)
            type: Warehouse type (STANDARD, SNOWPARK-OPTIMIZED)
            min_cluster_count: Minimum cluster count
            max_cluster_count: Maximum cluster count
            scaling_policy: Scaling policy (STANDARD, ECONOMY)
            auto_suspend: Auto-suspend timeout in seconds
            resource_monitor: Resource monitor name
            global_resource_monitor: Global resource monitor name
            enable_query_acceleration: Enable query acceleration
            query_acceleration_max_scale_factor: Max scale factor
            resource_constraint: Resource constraint (Snowpark)
            warehouse_params: Additional warehouse parameters
            comment: Optional descriptive comment
        """
        super().__init__(name=name, comment=comment)
        self.size = size
        self.type = type
        self.min_cluster_count = min_cluster_count
        self.max_cluster_count = max_cluster_count
        self.scaling_policy = scaling_policy
        self.auto_suspend = auto_suspend
        self.resource_monitor = resource_monitor
        self.global_resource_monitor = global_resource_monitor
        self.enable_query_acceleration = enable_query_acceleration
        self.query_acceleration_max_scale_factor = query_acceleration_max_scale_factor
        self.resource_constraint = resource_constraint
        self.warehouse_params = warehouse_params or {}

    def set_size(self, size: str) -> None:
        """Set warehouse size"""
        if not WarehouseSize.is_valid(size):
            raise ValueError(f"Invalid warehouse size: {size}")
        self.size = size

    def enable_multi_cluster(
        self, min_count: int = 1, max_count: int = 10, policy: str = "STANDARD"
    ) -> None:
        """Enable multi-cluster warehouse"""
        self.min_cluster_count = min_count
        self.max_cluster_count = max_count
        self.scaling_policy = policy

    def to_yaml(self) -> dict[str, Any]:
        """Convert to YAML format"""
        data: dict[str, Any] = {}

        if self.size != "X-Small":
            data["size"] = self.size
        if self.type != "STANDARD":
            data["type"] = self.type
        if self.auto_suspend != 60:
            data["auto_suspend"] = self.auto_suspend
        if self.min_cluster_count != 1:
            data["min_cluster_count"] = self.min_cluster_count
        if self.max_cluster_count != 1:
            data["max_cluster_count"] = self.max_cluster_count
        if self.scaling_policy != "STANDARD":
            data["scaling_policy"] = self.scaling_policy
        if self.resource_monitor:
            data["resource_monitor"] = self.resource_monitor
        if self.global_resource_monitor:
            data["global_resource_monitor"] = self.global_resource_monitor
        if self.enable_query_acceleration:
            data["enable_query_acceleration"] = self.enable_query_acceleration
        if self.query_acceleration_max_scale_factor != 8:
            data["query_acceleration_max_scale_factor"] = (
                self.query_acceleration_max_scale_factor
            )
        if self.resource_constraint:
            data["resource_constraint"] = self.resource_constraint
        if self.warehouse_params:
            data["warehouse_params"] = self.warehouse_params
        if self.comment:
            data["comment"] = self.comment

        return data

    @classmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> "Warehouse":
        """Create Warehouse from YAML"""
        return cls(
            name=name,
            size=data.get("size", "X-Small"),
            type=data.get("type", "STANDARD"),
            min_cluster_count=data.get("min_cluster_count", 1),
            max_cluster_count=data.get("max_cluster_count", 1),
            scaling_policy=data.get("scaling_policy", "STANDARD"),
            auto_suspend=data.get("auto_suspend", 60),
            resource_monitor=data.get("resource_monitor"),
            global_resource_monitor=data.get("global_resource_monitor"),
            enable_query_acceleration=data.get("enable_query_acceleration", False),
            query_acceleration_max_scale_factor=data.get(
                "query_acceleration_max_scale_factor", 8
            ),
            resource_constraint=data.get("resource_constraint"),
            warehouse_params=data.get("warehouse_params", {}),
            comment=data.get("comment"),
        )

    def validate(self) -> list[ValidationError]:
        """Validate warehouse configuration"""
        errors: list[ValidationError] = []

        if self.auto_suspend < 0:
            errors.append(
                ValidationError(f"Warehouse {self.name}: auto_suspend must be >= 0")
            )

        if self.min_cluster_count > self.max_cluster_count:
            errors.append(
                ValidationError(
                    f"Warehouse {self.name}: min_cluster_count cannot exceed max_cluster_count"
                )
            )

        return errors

    def get_dependencies(self) -> list[DependencyTuple]:
        """Get warehouse dependencies"""
        deps: list[DependencyTuple] = []
        if self.resource_monitor:
            deps.append(("resource_monitor", self.resource_monitor))
        return deps


class ResourceMonitor(AccountLevelObject):
    """
    Resource monitor for controlling warehouse costs.

    Attributes:
        credit_quota: Credit quota for monitoring period
        frequency: Monitoring frequency (MONTHLY, DAILY, WEEKLY, YEARLY, NEVER)
        start_timestamp: Start time for monitoring
        end_timestamp: End time for monitoring
        notify_at: Notify threshold percentages
        suspend_at: Suspend threshold percentage
        suspend_immediately_at: Immediate suspend threshold percentage
    """

    object_type: ClassVar[str] = "resource_monitor"

    def __init__(
        self,
        name: str,
        credit_quota: Optional[int] = None,
        frequency: str = "MONTHLY",
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
        notify_at: Optional[list[int]] = None,
        suspend_at: Optional[int] = None,
        suspend_immediately_at: Optional[int] = None,
        comment: Optional[str] = None,
    ):
        """
        Initialize a ResourceMonitor object.

        Args:
            name: Resource monitor name
            credit_quota: Credit quota for monitoring period
            frequency: Monitoring frequency (MONTHLY, DAILY, WEEKLY, YEARLY, NEVER)
            start_timestamp: Start time for monitoring
            end_timestamp: End time for monitoring
            notify_at: Notify threshold percentages
            suspend_at: Suspend threshold percentage
            suspend_immediately_at: Immediate suspend threshold percentage
            comment: Optional descriptive comment
        """
        super().__init__(name=name, comment=comment)
        self.credit_quota = credit_quota
        self.frequency = frequency
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.notify_at = notify_at or []
        self.suspend_at = suspend_at
        self.suspend_immediately_at = suspend_immediately_at

    def to_yaml(self) -> dict[str, Any]:
        """Convert to YAML format"""
        data: dict[str, Any] = {}

        if self.credit_quota:
            data["credit_quota"] = self.credit_quota
        if self.frequency != "MONTHLY":
            data["frequency"] = self.frequency
        if self.start_timestamp:
            data["start_timestamp"] = self.start_timestamp
        if self.end_timestamp:
            data["end_timestamp"] = self.end_timestamp
        if self.notify_at:
            data["notify_at"] = self.notify_at
        if self.suspend_at:
            data["suspend_at"] = self.suspend_at
        if self.suspend_immediately_at:
            data["suspend_immediately_at"] = self.suspend_immediately_at
        if self.comment:
            data["comment"] = self.comment

        return data

    @classmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> "ResourceMonitor":
        """Create ResourceMonitor from YAML"""
        return cls(
            name=name,
            credit_quota=data.get("credit_quota"),
            frequency=data.get("frequency", "MONTHLY"),
            start_timestamp=data.get("start_timestamp"),
            end_timestamp=data.get("end_timestamp"),
            notify_at=data.get("notify_at", []),
            suspend_at=data.get("suspend_at"),
            suspend_immediately_at=data.get("suspend_immediately_at"),
            comment=data.get("comment"),
        )

    def validate(self) -> list[ValidationError]:
        """Validate resource monitor configuration"""
        errors: list[ValidationError] = []

        if self.suspend_at and self.suspend_at > 100:
            errors.append(
                ValidationError(
                    f"ResourceMonitor {self.name}: suspend_at cannot exceed 100%"
                )
            )

        if self.suspend_immediately_at and self.suspend_immediately_at > 100:
            errors.append(
                ValidationError(
                    f"ResourceMonitor {self.name}: suspend_immediately_at cannot exceed 100%"
                )
            )

        return errors
