"""
SnowDDL Project orchestration and YAML management.

This module provides the main SnowDDLProject class for loading, managing,
and persisting SnowDDL configurations from YAML files.
"""

from pathlib import Path
from typing import Any, Optional

import yaml

from snowddl_core.account_objects import (
    BusinessRole,
    ResourceMonitor,
    TechnicalRole,
    User,
    Warehouse,
)
from snowddl_core.base import SnowDDLObject
from snowddl_core.validation import ValidationContext, ValidationError, Validator


def decrypt_constructor(loader, node):
    """YAML constructor for !decrypt tags (encrypted passwords)"""
    return f"!decrypt {loader.construct_scalar(node)}"


# Register the !decrypt constructor for safe YAML loading
yaml.SafeLoader.add_constructor("!decrypt", decrypt_constructor)


class SnowDDLProject:
    """
    Main project orchestrator for SnowDDL configurations.

    Provides high-level API for loading, managing, and saving SnowDDL
    configurations from YAML files.

    Attributes:
        config_dir: Root configuration directory
        users: Dictionary of User objects by name
        warehouses: Dictionary of Warehouse objects by name
        business_roles: Dictionary of BusinessRole objects by name
        technical_roles: Dictionary of TechnicalRole objects by name
        resource_monitors: Dictionary of ResourceMonitor objects by name
    """

    def __init__(self, config_dir: str | Path, auto_load: bool = True):
        """
        Initialize SnowDDL project.

        Args:
            config_dir: Root configuration directory path
            auto_load: Automatically load all configurations (default: True)
        """
        self.config_dir = Path(config_dir)
        self.users: dict[str, User] = {}
        self.warehouses: dict[str, Warehouse] = {}
        self.business_roles: dict[str, BusinessRole] = {}
        self.technical_roles: dict[str, TechnicalRole] = {}
        self.resource_monitors: dict[str, ResourceMonitor] = {}

        if auto_load:
            self.load_all()

    def load_all(self) -> None:
        """Load all configurations from YAML files."""
        self.load_users()
        self.load_warehouses()
        self.load_business_roles()
        self.load_technical_roles()
        self.load_resource_monitors()

    def load_users(self) -> None:
        """Load user configurations from user.yaml."""
        user_file = self.config_dir / "user.yaml"
        if not user_file.exists():
            return

        with open(user_file, "r") as f:
            data = yaml.safe_load(f) or {}

        for name, user_data in data.items():
            if isinstance(user_data, dict):
                self.users[name] = User.from_yaml(name, user_data)

    def load_warehouses(self) -> None:
        """Load warehouse configurations from warehouse.yaml."""
        warehouse_file = self.config_dir / "warehouse.yaml"
        if not warehouse_file.exists():
            return

        with open(warehouse_file, "r") as f:
            data = yaml.safe_load(f) or {}

        for name, warehouse_data in data.items():
            if isinstance(warehouse_data, dict):
                self.warehouses[name] = Warehouse.from_yaml(name, warehouse_data)

    def load_business_roles(self) -> None:
        """Load business role configurations from business_role.yaml."""
        role_file = self.config_dir / "business_role.yaml"
        if not role_file.exists():
            return

        with open(role_file, "r") as f:
            data = yaml.safe_load(f) or {}

        for name, role_data in data.items():
            if isinstance(role_data, dict):
                self.business_roles[name] = BusinessRole.from_yaml(name, role_data)

    def load_technical_roles(self) -> None:
        """Load technical role configurations from tech_role.yaml."""
        role_file = self.config_dir / "tech_role.yaml"
        if not role_file.exists():
            return

        with open(role_file, "r") as f:
            data = yaml.safe_load(f) or {}

        for name, role_data in data.items():
            if isinstance(role_data, dict):
                self.technical_roles[name] = TechnicalRole.from_yaml(name, role_data)

    def load_resource_monitors(self) -> None:
        """Load resource monitor configurations from resource_monitor.yaml."""
        rm_file = self.config_dir / "resource_monitor.yaml"
        if not rm_file.exists():
            return

        with open(rm_file, "r") as f:
            data = yaml.safe_load(f) or {}

        for name, rm_data in data.items():
            if isinstance(rm_data, dict):
                self.resource_monitors[name] = ResourceMonitor.from_yaml(name, rm_data)

    def save_all(self) -> None:
        """Save all configurations to YAML files."""
        self.save_users()
        self.save_warehouses()
        self.save_business_roles()
        self.save_technical_roles()
        self.save_resource_monitors()

    def save_users(self) -> None:
        """Save user configurations to user.yaml."""
        if not self.users:
            return

        user_file = self.config_dir / "user.yaml"
        data = {name: user.to_yaml() for name, user in self.users.items()}

        with open(user_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def save_warehouses(self) -> None:
        """Save warehouse configurations to warehouse.yaml."""
        if not self.warehouses:
            return

        warehouse_file = self.config_dir / "warehouse.yaml"
        data = {name: wh.to_yaml() for name, wh in self.warehouses.items()}

        with open(warehouse_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def save_business_roles(self) -> None:
        """Save business role configurations to business_role.yaml."""
        if not self.business_roles:
            return

        role_file = self.config_dir / "business_role.yaml"
        data = {name: role.to_yaml() for name, role in self.business_roles.items()}

        with open(role_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def save_technical_roles(self) -> None:
        """Save technical role configurations to tech_role.yaml."""
        if not self.technical_roles:
            return

        role_file = self.config_dir / "tech_role.yaml"
        data = {name: role.to_yaml() for name, role in self.technical_roles.items()}

        with open(role_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def save_resource_monitors(self) -> None:
        """Save resource monitor configurations to resource_monitor.yaml."""
        if not self.resource_monitors:
            return

        rm_file = self.config_dir / "resource_monitor.yaml"
        data = {name: rm.to_yaml() for name, rm in self.resource_monitors.items()}

        with open(rm_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def add_user(self, user: User) -> None:
        """
        Add a user to the project.

        Args:
            user: User object to add
        """
        self.users[user.name] = user

    def add_warehouse(self, warehouse: Warehouse) -> None:
        """
        Add a warehouse to the project.

        Args:
            warehouse: Warehouse object to add
        """
        self.warehouses[warehouse.name] = warehouse

    def add_business_role(self, role: BusinessRole) -> None:
        """
        Add a business role to the project.

        Args:
            role: BusinessRole object to add
        """
        self.business_roles[role.name] = role

    def add_technical_role(self, role: TechnicalRole) -> None:
        """
        Add a technical role to the project.

        Args:
            role: TechnicalRole object to add
        """
        self.technical_roles[role.name] = role

    def add_resource_monitor(self, monitor: ResourceMonitor) -> None:
        """
        Add a resource monitor to the project.

        Args:
            monitor: ResourceMonitor object to add
        """
        self.resource_monitors[monitor.name] = monitor

    def get_user(self, name: str) -> Optional[User]:
        """
        Get a user by name.

        Args:
            name: User name

        Returns:
            User object or None if not found
        """
        return self.users.get(name)

    def get_warehouse(self, name: str) -> Optional[Warehouse]:
        """
        Get a warehouse by name.

        Args:
            name: Warehouse name

        Returns:
            Warehouse object or None if not found
        """
        return self.warehouses.get(name)

    def get_business_role(self, name: str) -> Optional[BusinessRole]:
        """
        Get a business role by name.

        Args:
            name: Business role name

        Returns:
            BusinessRole object or None if not found
        """
        return self.business_roles.get(name)

    def get_resource_monitor(self, name: str) -> Optional[ResourceMonitor]:
        """
        Get a resource monitor by name.

        Args:
            name: Resource monitor name

        Returns:
            ResourceMonitor object or None if not found
        """
        return self.resource_monitors.get(name)

    def get_all_objects(self) -> list[SnowDDLObject]:
        """
        Get all objects in the project.

        Returns:
            List of all SnowDDL objects
        """
        objects: list[SnowDDLObject] = []
        objects.extend(self.users.values())
        objects.extend(self.warehouses.values())
        objects.extend(self.business_roles.values())
        objects.extend(self.technical_roles.values())
        objects.extend(self.resource_monitors.values())
        return objects

    def validate(self) -> list[ValidationError]:
        """
        Validate all objects in the project.

        Returns:
            List of validation errors
        """
        # Create validator with default rules
        validator = Validator()
        validator.add_default_rules()

        # Create validation context (requires repository implementation)
        # For now, we'll skip context-based validation
        errors: list[ValidationError] = []

        # Validate all objects
        for obj in self.get_all_objects():
            errors.extend(obj.validate())

        return errors

    def object_exists(self, object_type: str, name: str) -> bool:
        """
        Check if an object exists in the project.

        Args:
            object_type: Type of object (e.g., 'business_role', 'warehouse')
            name: Object name

        Returns:
            True if object exists, False otherwise
        """
        type_map = {
            "user": self.users,
            "warehouse": self.warehouses,
            "business_role": self.business_roles,
            "technical_role": self.technical_roles,
            "resource_monitor": self.resource_monitors,
        }

        collection = type_map.get(object_type)
        if collection is None:
            return False

        return name in collection

    def summary(self) -> dict[str, int]:
        """
        Get summary statistics for the project.

        Returns:
            Dictionary with counts of each object type
        """
        return {
            "users": len(self.users),
            "warehouses": len(self.warehouses),
            "business_roles": len(self.business_roles),
            "technical_roles": len(self.technical_roles),
            "resource_monitors": len(self.resource_monitors),
        }

    def __repr__(self) -> str:
        """String representation of the project."""
        stats = self.summary()
        return (
            f"SnowDDLProject(config_dir={self.config_dir}, "
            f"users={stats['users']}, "
            f"warehouses={stats['warehouses']}, "
            f"roles={stats['business_roles'] + stats['technical_roles']})"
        )
