"""
Base classes for SnowDDL objects.

This module provides the abstract base classes that all SnowDDL objects inherit from.
It defines the core functionality for YAML serialization, validation, dependency
tracking, and identity management.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Optional

from snowddl_core.snowddl_types import DependencyTuple, FQN, ObjectType


class SnowDDLObject(ABC):
    """
    Abstract base class for all SnowDDL configuration objects.

    Provides common functionality for YAML serialization, validation,
    dependency tracking, and identity management.

    Attributes:
        name: Object name (must be unique within its scope)
        comment: Optional descriptive comment
        object_type: Class variable defining the object type (overridden in subclasses)
    """

    # Class variable defining the object type (overridden in subclasses)
    object_type: ClassVar[str] = "snowddl_object"

    def __init__(self, name: str, comment: Optional[str] = None):
        """
        Initialize a SnowDDL object.

        Args:
            name: Object name (must be unique within its scope)
            comment: Optional descriptive comment
        """
        self.name = name
        self.comment = comment

    @abstractmethod
    def to_yaml(self) -> dict[str, Any]:
        """
        Convert object to YAML-compatible dictionary.

        Returns:
            Dictionary suitable for YAML serialization
        """
        pass

    @classmethod
    @abstractmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> "SnowDDLObject":
        """
        Create object instance from YAML data.

        Args:
            name: Object name
            data: YAML dictionary

        Returns:
            Object instance
        """
        pass

    @abstractmethod
    def validate(self) -> list["ValidationError"]:
        """
        Validate object configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        pass

    @abstractmethod
    def get_dependencies(self) -> list[DependencyTuple]:
        """
        Get list of objects this object depends on.

        Returns:
            List of (object_type, object_name) tuples
        """
        pass

    @abstractmethod
    def get_file_path(self, config_dir: Path) -> Path:
        """
        Get the file path where this object should be stored.

        Args:
            config_dir: Root configuration directory

        Returns:
            Full path to YAML file
        """
        pass

    def get_fqn(self) -> FQN:
        """
        Get fully qualified name for this object.

        Returns:
            String representation (e.g., "DATABASE.SCHEMA.TABLE")
        """
        return self.name

    def __eq__(self, other: object) -> bool:
        """Equality based on type and FQN"""
        if not isinstance(other, SnowDDLObject):
            return False
        return (self.object_type, self.get_fqn()) == (
            other.object_type,
            other.get_fqn(),
        )

    def __hash__(self) -> int:
        """Hash based on type and FQN for use in sets/dicts"""
        return hash((self.object_type, self.get_fqn()))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


class AccountLevelObject(SnowDDLObject, ABC):
    """
    Base class for objects defined at the Snowflake account level.

    Account-level objects are stored in single YAML files at the root of
    the config directory (e.g., user.yaml, warehouse.yaml).

    Examples:
        - Users
        - Warehouses
        - Business Roles
        - Technical Roles
        - Policies
        - Resource Monitors
    """

    def get_file_path(self, config_dir: Path) -> Path:
        """
        Account-level objects are stored as <object_type>.yaml

        Example: user.yaml, warehouse.yaml, business_role.yaml

        Args:
            config_dir: Root configuration directory

        Returns:
            Path to YAML file
        """
        return config_dir / f"{self.object_type}.yaml"

    def get_dependencies(self) -> list[DependencyTuple]:
        """Default: no dependencies for account objects"""
        return []


class DatabaseLevelObject(SnowDDLObject, ABC):
    """
    Base class for objects within a specific database.

    Database-level objects are associated with a database but not a schema.
    Currently, the only database-level object is the Database itself.

    Attributes:
        database: Name of the database this object belongs to
    """

    def __init__(self, name: str, database: str = "", comment: Optional[str] = None):
        """
        Initialize a database-level object.

        Args:
            name: Object name
            database: Name of the database this object belongs to
            comment: Optional descriptive comment
        """
        super().__init__(name, comment)
        self.database = database

    def get_file_path(self, config_dir: Path) -> Path:
        """
        Database objects stored in <DATABASE>/params.yaml

        Args:
            config_dir: Root configuration directory

        Returns:
            Path to database params file
        """
        return config_dir / self.database / "params.yaml"

    def get_fqn(self) -> FQN:
        """FQN includes database name"""
        return f"{self.database}.{self.name}"

    def get_dependencies(self) -> list[DependencyTuple]:
        """Database objects have no dependencies by default"""
        return []


class SchemaLevelObject(DatabaseLevelObject, ABC):
    """
    Base class for objects within a database schema.

    Schema-level objects include tables, views, functions, procedures, etc.

    Attributes:
        schema: Name of the schema this object belongs to
        database: Name of the database (inherited from DatabaseLevelObject)
    """

    def __init__(
        self,
        name: str,
        database: str = "",
        schema: str = "",
        comment: Optional[str] = None,
    ):
        """
        Initialize a schema-level object.

        Args:
            name: Object name
            database: Name of the database
            schema: Name of the schema this object belongs to
            comment: Optional descriptive comment
        """
        super().__init__(name, database, comment)
        self.schema = schema

    def get_file_path(self, config_dir: Path) -> Path:
        """
        Schema objects stored in <DATABASE>/<SCHEMA>/<type>/<name>.yaml

        For functions/procedures, filename includes argument types.

        Args:
            config_dir: Root configuration directory

        Returns:
            Path to object's YAML file
        """
        return (
            config_dir
            / self.database
            / self.schema
            / self.object_type
            / f"{self.name}.yaml"
        )

    def get_fqn(self) -> FQN:
        """FQN includes database, schema, and object name"""
        return f"{self.database}.{self.schema}.{self.name}"

    def get_dependencies(self) -> list[DependencyTuple]:
        """Schema objects depend on their schema"""
        return [("schema", f"{self.database}.{self.schema}")]
