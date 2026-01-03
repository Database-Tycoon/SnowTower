"""
Tests for the SnowDDL to Terraform generator.
"""

import tempfile
from pathlib import Path

import pytest
import yaml


# Add scripts to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_terraform import (
    TerraformGenerator,
    WarehouseTransformer,
    UserTransformer,
    ResourceMonitorTransformer,
    NetworkPolicyTransformer,
    RoleTransformer,
    GrantTransformer,
    to_terraform_name,
    to_hcl_string,
    to_hcl_list,
)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_to_terraform_name_basic(self):
        assert to_terraform_name("MAIN_WAREHOUSE") == "main_warehouse"

    def test_to_terraform_name_with_numbers(self):
        assert to_terraform_name("123_WAREHOUSE") == "_123_warehouse"

    def test_to_terraform_name_special_chars(self):
        assert to_terraform_name("MY-WAREHOUSE.TEST") == "my_warehouse_test"

    def test_to_hcl_string(self):
        assert to_hcl_string("hello") == '"hello"'
        assert to_hcl_string(None) == '""'

    def test_to_hcl_list(self):
        assert to_hcl_list(["a", "b"]) == '["a", "b"]'
        assert to_hcl_list([]) == "[]"


class TestWarehouseTransformer:
    """Test warehouse transformer."""

    def test_transform_basic_warehouse(self):
        config = {
            "MAIN_WAREHOUSE": {
                "size": "X-Small",
                "auto_suspend": 60,
                "comment": "Test warehouse",
            }
        }
        result = WarehouseTransformer().transform(config)

        assert len(result.resources) == 1
        assert len(result.imports) == 1
        assert "MAIN_WAREHOUSE" in result.resources[0]
        assert 'warehouse_size = "XSMALL"' in result.resources[0]
        assert "auto_suspend   = 60" in result.resources[0]

    def test_transform_warehouse_with_resource_monitor(self):
        config = {
            "ANALYST_WH": {
                "size": "Small",
                "auto_suspend": 120,
                "resource_monitor": "DEV_MONITOR",
            }
        }
        result = WarehouseTransformer().transform(config)

        assert "snowflake_resource_monitor.dev_monitor.name" in result.resources[0]

    def test_transform_warehouse_size_mapping(self):
        """Test all size mappings."""
        sizes = {
            "X-Small": "XSMALL",
            "Small": "SMALL",
            "Medium": "MEDIUM",
            "Large": "LARGE",
            "X-Large": "XLARGE",
            "2X-Large": "XXLARGE",
        }
        for snowddl_size, tf_size in sizes.items():
            config = {"TEST_WH": {"size": snowddl_size}}
            result = WarehouseTransformer().transform(config)
            assert f'warehouse_size = "{tf_size}"' in result.resources[0]


class TestUserTransformer:
    """Test user transformer."""

    def test_transform_human_user(self):
        config = {
            "ALICE_ADMIN": {
                "type": "PERSON",
                "email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Admin",
                "default_role": "SYSADMIN",
                "comment": "Admin user",
            }
        }
        result = UserTransformer().transform(config)

        assert len(result.resources) == 1
        assert '"alice@example.com"' in result.resources[0]
        assert '"Alice"' in result.resources[0]
        assert '"Admin"' in result.resources[0]

    def test_transform_service_account_with_rsa_key(self):
        config = {
            "DBT_SERVICE": {
                "type": "SERVICE",
                "rsa_public_key": "MIIBIjAN...",
                "default_role": "DBT_ROLE__B_ROLE",
            }
        }
        result = UserTransformer().transform(config)

        assert "rsa_public_key" in result.resources[0]
        assert "<<-EOT" in result.resources[0]


class TestResourceMonitorTransformer:
    """Test resource monitor transformer."""

    def test_transform_basic_monitor(self):
        config = {
            "DEV_MONITOR": {
                "credit_quota": 100,
                "frequency": "monthly",
                "notify_triggers": [75, 90],
                "suspend_trigger": 100,
            }
        }
        result = ResourceMonitorTransformer().transform(config)

        assert len(result.resources) == 1
        assert "credit_quota = 100" in result.resources[0]
        assert 'frequency = "MONTHLY"' in result.resources[0]


class TestNetworkPolicyTransformer:
    """Test network policy transformer."""

    def test_transform_network_policy(self):
        config = {
            "company_policy": {
                "allowed_ip_list": ["10.0.0.1/32", "10.0.0.2/32"],
                "comment": "Company IPs",
            }
        }
        result = NetworkPolicyTransformer().transform(config)

        assert len(result.resources) == 1
        assert "10.0.0.1/32" in result.resources[0]
        assert "10.0.0.2/32" in result.resources[0]


class TestRoleTransformer:
    """Test role transformer."""

    def test_transform_tech_role(self):
        config = {"DBT_ROLE": {"comment": "dbt technical role"}}
        result = RoleTransformer("tech").transform(config)

        assert len(result.resources) == 1
        assert "DBT_ROLE__T_ROLE" in result.resources[0]
        assert '"dbt technical role"' in result.resources[0]

    def test_transform_business_role(self):
        config = {"ANALYST_ROLE": {"comment": "Analyst business role"}}
        result = RoleTransformer("business").transform(config)

        assert "ANALYST_ROLE__B_ROLE" in result.resources[0]


class TestGrantTransformer:
    """Test grant transformer."""

    def test_transform_database_grant(self):
        config = {
            "DBT_ROLE": {
                "grants": {"DATABASE:USAGE,CREATE SCHEMA": ["SOURCE_DB", "PROJ_DB"]}
            }
        }
        result = GrantTransformer().transform(config)

        # Should create 2 grants (one per database)
        assert len(result.resources) == 2
        assert "SOURCE_DB" in result.resources[0]
        assert "PROJ_DB" in result.resources[1]
        assert '["USAGE", "CREATE SCHEMA"]' in result.resources[0]

    def test_transform_warehouse_grant(self):
        config = {"TEST_ROLE": {"grants": {"WAREHOUSE:USAGE": ["MAIN_WH"]}}}
        result = GrantTransformer().transform(config)

        assert len(result.resources) == 1
        assert 'object_type = "WAREHOUSE"' in result.resources[0]

    def test_transform_future_grants(self):
        config = {"TEST_ROLE": {"future_grants": {"TABLE:SELECT": ["SOURCE_DB"]}}}
        result = GrantTransformer().transform(config)

        assert "future {" in result.resources[0]
        assert 'object_type_plural = "TABLES"' in result.resources[0]


class TestTerraformGenerator:
    """Test the main generator."""

    def test_generate_with_minimal_config(self):
        """Test generation with minimal YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create minimal warehouse.yaml
            with open(config_dir / "warehouse.yaml", "w") as f:
                yaml.dump({"TEST_WH": {"size": "X-Small", "auto_suspend": 60}}, f)

            generator = TerraformGenerator(config_dir)
            files = generator.generate_all()

            assert "main.tf" in files
            assert "variables.tf" in files
            assert "warehouses.tf" in files
            assert "imports.tf" in files

    def test_provider_template(self):
        """Test that provider template is correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TerraformGenerator(Path(tmpdir))
            files = generator.generate_all()

            assert 'source  = "snowflakedb/snowflake"' in files["main.tf"]
            assert 'version = "~> 2.0"' in files["main.tf"]

    def test_variables_template(self):
        """Test that variables template is correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TerraformGenerator(Path(tmpdir))
            files = generator.generate_all()

            assert "snowflake_organization" in files["variables.tf"]
            assert "snowflake_account" in files["variables.tf"]
            assert "snowflake_private_key_path" in files["variables.tf"]


class TestImportBlocks:
    """Test import block generation."""

    def test_warehouse_import_block(self):
        config = {"MAIN_WH": {"size": "Small"}}
        result = WarehouseTransformer().transform(config)

        assert "import {" in result.imports[0]
        assert 'id = "MAIN_WH"' in result.imports[0]
        assert "to = snowflake_warehouse.main_wh" in result.imports[0]

    def test_user_import_block(self):
        config = {"TEST_USER": {"email": "test@example.com"}}
        result = UserTransformer().transform(config)

        assert 'id = "TEST_USER"' in result.imports[0]
        assert "to = snowflake_user.test_user" in result.imports[0]
