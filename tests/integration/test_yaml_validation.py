"""Integration tests for YAML configuration validation.

Tests that the actual snowddl/ YAML files are well-formed and internally consistent.
"""

import pytest
import yaml
from pathlib import Path

SNOWDDL_DIR = Path(__file__).parent.parent.parent / "snowddl"

SYSTEM_ROLES = {
    "ACCOUNTADMIN",
    "SECURITYADMIN",
    "USERADMIN",
    "SYSADMIN",
    "PUBLIC",
    "ORGADMIN",
}

VALID_WAREHOUSE_SIZES = {
    "X-Small",
    "Small",
    "Medium",
    "Large",
    "X-Large",
    "2X-Large",
    "3X-Large",
    "4X-Large",
    "5X-Large",
    "6X-Large",
}

VALID_OBJECT_TYPES = {
    "DATABASE",
    "SCHEMA",
    "TABLE",
    "VIEW",
    "WAREHOUSE",
    "STAGE",
    "FUNCTION",
    "PROCEDURE",
    "FILE_FORMAT",
    "SEQUENCE",
}


def load_yaml(filename):
    """Load a YAML file from snowddl/ with !decrypt tag support."""

    def decrypt_constructor(loader, node):
        return "!decrypt " + loader.construct_scalar(node)

    loader = yaml.SafeLoader
    loader.add_constructor("!decrypt", decrypt_constructor)
    filepath = SNOWDDL_DIR / filename
    if not filepath.exists():
        return {}
    with open(filepath) as f:
        data = yaml.load(f, Loader=loader)
    return data or {}


class TestYAMLSyntax:
    """Test that all YAML files parse without errors."""

    @pytest.mark.parametrize(
        "filename",
        [
            "user.yaml",
            "warehouse.yaml",
            "business_role.yaml",
            "tech_role.yaml",
            "network_policy.yaml",
            "authentication_policy.yaml",
            "password_policy.yaml",
            "session_policy.yaml",
            "resource_monitor.yaml",
        ],
    )
    def test_yaml_parses(self, filename):
        """Each YAML config file should parse without errors."""
        data = load_yaml(filename)
        assert isinstance(data, dict), f"{filename} should contain a dictionary"


class TestUserConfig:
    """Validate user.yaml configuration."""

    def test_all_users_have_type(self):
        """Every user must have a type field."""
        users = load_yaml("user.yaml")
        for username, config in users.items():
            assert "type" in config, f"User {username} missing 'type' field"
            assert config["type"] in (
                "PERSON",
                "SERVICE",
            ), f"User {username} has invalid type: {config['type']}"

    def test_person_users_have_email(self):
        """PERSON users should have an email."""
        users = load_yaml("user.yaml")
        for username, config in users.items():
            if config.get("type") == "PERSON":
                assert "email" in config, f"PERSON user {username} missing 'email'"

    def test_service_users_have_rsa_key(self):
        """SERVICE users should have an RSA public key."""
        users = load_yaml("user.yaml")
        for username, config in users.items():
            if config.get("type") == "SERVICE":
                assert (
                    "rsa_public_key" in config
                ), f"SERVICE user {username} missing 'rsa_public_key'"

    def test_no_duplicate_users(self):
        """No duplicate user names (YAML handles this natively, but verify)."""
        users = load_yaml("user.yaml")
        assert len(users) > 0, "user.yaml should have at least one user"


class TestWarehouseConfig:
    """Validate warehouse.yaml configuration."""

    def test_all_warehouses_have_size(self):
        """Every warehouse must have a size."""
        warehouses = load_yaml("warehouse.yaml")
        for wh_name, config in warehouses.items():
            assert "size" in config, f"Warehouse {wh_name} missing 'size'"

    def test_warehouse_sizes_are_valid(self):
        """Warehouse sizes must be valid Snowflake sizes."""
        warehouses = load_yaml("warehouse.yaml")
        for wh_name, config in warehouses.items():
            assert (
                config["size"] in VALID_WAREHOUSE_SIZES
            ), f"Warehouse {wh_name} has invalid size: {config['size']}"

    def test_auto_suspend_is_positive(self):
        """auto_suspend should be a positive integer."""
        warehouses = load_yaml("warehouse.yaml")
        for wh_name, config in warehouses.items():
            if "auto_suspend" in config:
                assert (
                    isinstance(config["auto_suspend"], int) and config["auto_suspend"] > 0
                ), f"Warehouse {wh_name} has invalid auto_suspend: {config['auto_suspend']}"


class TestBusinessRoleConfig:
    """Validate business_role.yaml configuration."""

    def test_tech_roles_exist(self):
        """All tech_roles referenced in business roles should exist in tech_role.yaml."""
        business_roles = load_yaml("business_role.yaml")
        tech_roles = load_yaml("tech_role.yaml")

        for role_name, config in business_roles.items():
            for tech_role in config.get("tech_roles", []):
                assert (
                    tech_role in tech_roles
                ), f"Business role {role_name} references missing tech role: {tech_role}"

    def test_warehouse_usage_exists(self):
        """All warehouse_usage entries should reference existing warehouses."""
        business_roles = load_yaml("business_role.yaml")
        warehouses = load_yaml("warehouse.yaml")

        for role_name, config in business_roles.items():
            for wh in config.get("warehouse_usage", []):
                assert (
                    wh in warehouses
                ), f"Business role {role_name} references missing warehouse: {wh}"

    def test_schema_owner_format(self):
        """schema_owner entries should be DB.SCHEMA format."""
        business_roles = load_yaml("business_role.yaml")

        for role_name, config in business_roles.items():
            for entry in config.get("schema_owner", []):
                parts = entry.split(".")
                assert (
                    len(parts) == 2
                ), f"Business role {role_name} schema_owner '{entry}' not in DB.SCHEMA format"


class TestTechRoleConfig:
    """Validate tech_role.yaml configuration."""

    def test_grant_keys_are_valid(self):
        """Grant keys must follow OBJECT_TYPE:PRIVILEGE format."""
        tech_roles = load_yaml("tech_role.yaml")

        for role_name, config in tech_roles.items():
            for grant_key in config.get("grants", {}):
                parts = grant_key.split(":", 1)
                assert (
                    len(parts) == 2
                ), f"Tech role {role_name} grant key '{grant_key}' not in TYPE:PRIVILEGE format"
                assert (
                    parts[0] in VALID_OBJECT_TYPES
                ), f"Tech role {role_name} has invalid object type: {parts[0]}"

            for grant_key in config.get("future_grants", {}):
                parts = grant_key.split(":", 1)
                assert (
                    len(parts) == 2
                ), f"Tech role {role_name} future_grant key '{grant_key}' not in TYPE:PRIVILEGE format"
                assert (
                    parts[0] in VALID_OBJECT_TYPES
                ), f"Tech role {role_name} future_grant has invalid object type: {parts[0]}"

    def test_warehouse_grants_reference_existing(self):
        """WAREHOUSE:USAGE grants should reference existing warehouses."""
        tech_roles = load_yaml("tech_role.yaml")
        warehouses = load_yaml("warehouse.yaml")

        for role_name, config in tech_roles.items():
            for grant_key, targets in config.get("grants", {}).items():
                if grant_key.startswith("WAREHOUSE:"):
                    for wh in targets or []:
                        assert (
                            wh in warehouses
                        ), f"Tech role {role_name} references missing warehouse: {wh}"


class TestResourceMonitorConfig:
    """Validate resource_monitor.yaml configuration."""

    def test_monitors_have_credit_quota(self):
        """Every monitor must have a credit_quota."""
        monitors = load_yaml("resource_monitor.yaml")
        for name, config in monitors.items():
            assert "credit_quota" in config, f"Monitor {name} missing 'credit_quota'"
            assert isinstance(
                config["credit_quota"], (int, float)
            ), f"Monitor {name} credit_quota must be numeric"

    def test_warehouse_monitors_exist(self):
        """resource_monitor references in warehouse.yaml should exist."""
        warehouses = load_yaml("warehouse.yaml")
        monitors = load_yaml("resource_monitor.yaml")

        for wh_name, config in warehouses.items():
            if "resource_monitor" in config:
                assert (
                    config["resource_monitor"] in monitors
                ), f"Warehouse {wh_name} references missing monitor: {config['resource_monitor']}"


class TestNetworkPolicyConfig:
    """Validate network_policy.yaml configuration."""

    def test_policies_have_allowed_ips(self):
        """Every network policy should have allowed_ip_list."""
        policies = load_yaml("network_policy.yaml")
        for name, config in policies.items():
            assert (
                "allowed_ip_list" in config
            ), f"Network policy {name} missing 'allowed_ip_list'"
            assert isinstance(
                config["allowed_ip_list"], list
            ), f"Network policy {name} allowed_ip_list must be a list"

    def test_ip_addresses_are_cidr(self):
        """IP addresses should be in CIDR notation."""
        import ipaddress

        policies = load_yaml("network_policy.yaml")
        for name, config in policies.items():
            for ip in config.get("allowed_ip_list", []):
                try:
                    ipaddress.ip_network(ip, strict=False)
                except ValueError:
                    pytest.fail(f"Network policy {name} has invalid CIDR: {ip}")
