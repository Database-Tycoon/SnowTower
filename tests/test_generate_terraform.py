"""
Test Suite for Terraform HCL Generator from SnowDDL YAML.

Tests the generate_terraform.py script including:
- Name conversion helpers (to_tf_name, hcl_value, hcl_block)
- YAML loading with !decrypt tag handling
- Individual generators (users, warehouses, roles, policies, etc.)
- End-to-end generate_all and write_to_directory
- Output rendering helpers
"""

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
import yaml

from generate_terraform import (
    to_tf_name,
    hcl_value,
    hcl_block,
    load_yaml,
    generate_users,
    generate_warehouses,
    generate_business_roles,
    generate_tech_roles,
    generate_network_policies,
    generate_resource_monitors,
    generate_databases,
    generate_all,
    write_to_directory,
    render_section,
    TerraformOutput,
    HEADER,
)


# ---------------------------------------------------------------------------
# to_tf_name
# ---------------------------------------------------------------------------


class TestToTfName:
    """Tests for the to_tf_name name conversion helper."""

    def test_uppercase_to_lowercase(self):
        assert to_tf_name("MY_WAREHOUSE") == "my_warehouse"

    def test_hyphens_to_underscores(self):
        assert to_tf_name("my-warehouse") == "my_warehouse"

    def test_special_characters_replaced(self):
        assert to_tf_name("WH@#$NAME") == "wh_name"

    def test_consecutive_underscores_collapsed(self):
        assert to_tf_name("WH___NAME") == "wh_name"

    def test_leading_trailing_underscores_stripped(self):
        assert to_tf_name("__WH__") == "wh"

    def test_dots_replaced(self):
        assert to_tf_name("DB.SCHEMA") == "db_schema"

    def test_mixed_case_and_special(self):
        assert to_tf_name("My-Cool_Role__B_ROLE") == "my_cool_role_b_role"

    def test_already_valid(self):
        assert to_tf_name("simple_name") == "simple_name"

    def test_single_char(self):
        assert to_tf_name("X") == "x"

    def test_numbers_preserved(self):
        assert to_tf_name("WH_2X_LARGE") == "wh_2x_large"


# ---------------------------------------------------------------------------
# hcl_value
# ---------------------------------------------------------------------------


class TestHclValue:
    """Tests for the hcl_value formatting function."""

    def test_bool_true(self):
        assert hcl_value(True) == "true"

    def test_bool_false(self):
        assert hcl_value(False) == "false"

    def test_int(self):
        assert hcl_value(42) == "42"

    def test_float(self):
        assert hcl_value(3.14) == "3.14"

    def test_string(self):
        assert hcl_value("hello") == '"hello"'

    def test_string_with_quotes(self):
        assert hcl_value('say "hi"') == '"say \\"hi\\""'

    def test_string_with_backslash(self):
        assert hcl_value("back\\slash") == '"back\\\\slash"'

    def test_list_of_strings(self):
        assert hcl_value(["a", "b"]) == '["a", "b"]'

    def test_list_of_ints(self):
        assert hcl_value([1, 2, 3]) == "[1, 2, 3]"

    def test_empty_list(self):
        assert hcl_value([]) == "[]"

    def test_fallback_type(self):
        """Non-standard types are stringified."""
        result = hcl_value(None)
        assert result == '"None"'


# ---------------------------------------------------------------------------
# hcl_block
# ---------------------------------------------------------------------------


class TestHclBlock:
    """Tests for the hcl_block rendering function."""

    def test_basic_block(self):
        result = hcl_block("snowflake_user", "alice", {"name": "ALICE"})
        assert 'resource "snowflake_user" "alice"' in result
        assert 'name = "ALICE"' in result
        assert result.endswith("}")

    def test_block_with_import_id(self):
        result = hcl_block("snowflake_user", "alice", {"name": "ALICE"}, import_id="ALICE")
        assert "import {" in result
        assert "to = snowflake_user.alice" in result
        assert 'id = "ALICE"' in result

    def test_block_without_import_id(self):
        result = hcl_block("snowflake_user", "alice", {"name": "ALICE"})
        assert "import" not in result

    def test_nested_block(self):
        """Nested dict values render as HCL sub-blocks."""
        attrs = {
            "name": "WH",
            "on_account_object": {"object_type": "WAREHOUSE", "object_name": "WH"},
        }
        result = hcl_block("snowflake_grant", "g", attrs)
        assert "on_account_object {" in result
        assert "object_type" in result

    def test_bool_and_int_values(self):
        attrs = {"auto_resume": True, "auto_suspend": 120}
        result = hcl_block("snowflake_warehouse", "wh", attrs)
        assert "true" in result
        assert "120" in result

    def test_empty_attrs(self):
        """A block with no attributes still renders valid HCL."""
        result = hcl_block("snowflake_user", "empty", {})
        assert 'resource "snowflake_user" "empty" {' in result
        assert result.strip().endswith("}")


# ---------------------------------------------------------------------------
# load_yaml
# ---------------------------------------------------------------------------


class TestLoadYaml:
    """Tests for the load_yaml helper."""

    def test_valid_file(self, tmp_path):
        p = tmp_path / "test.yaml"
        p.write_text(yaml.dump({"KEY": "value"}))
        data = load_yaml(p)
        assert data == {"KEY": "value"}

    def test_missing_file(self, tmp_path):
        data = load_yaml(tmp_path / "missing.yaml")
        assert data is None

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.yaml"
        p.write_text("")
        data = load_yaml(p)
        assert data is None  # None because safe_load returns None, not dict

    def test_non_dict_file(self, tmp_path):
        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2\n")
        data = load_yaml(p)
        assert data is None  # list is not dict

    def test_decrypt_tag_handled(self, tmp_path):
        """The !decrypt tag should not raise an error and returns a placeholder."""
        p = tmp_path / "encrypted.yaml"
        p.write_text('USER:\n  password: !decrypt "gAAAAABf..."\n')
        data = load_yaml(p)
        assert data is not None
        assert data["USER"]["password"] == "<ENCRYPTED>"


# ---------------------------------------------------------------------------
# generate_users
# ---------------------------------------------------------------------------


class TestGenerateUsers:
    """Tests for generate_users."""

    def test_generates_user_blocks(self, tmp_path):
        data = {
            "ALICE": {
                "type": "PERSON",
                "email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Smith",
                "default_role": "ANALYST",
                "comment": "Test user",
            }
        }
        (tmp_path / "user.yaml").write_text(yaml.dump(data))
        blocks = generate_users(tmp_path)
        assert len(blocks) == 1
        assert "snowflake_user" in blocks[0]
        assert '"ALICE"' in blocks[0]
        assert '"alice@example.com"' in blocks[0]
        assert "user_type" in blocks[0]  # 'type' maps to 'user_type'

    def test_rsa_key_included(self, tmp_path):
        data = {
            "SVC": {
                "type": "SERVICE",
                "rsa_public_key": "MIIBIjANBg...",
            }
        }
        (tmp_path / "user.yaml").write_text(yaml.dump(data))
        blocks = generate_users(tmp_path)
        assert len(blocks) == 1
        assert "rsa_public_key" in blocks[0]

    def test_empty_user_yaml(self, tmp_path):
        (tmp_path / "user.yaml").write_text("")
        blocks = generate_users(tmp_path)
        assert blocks == []

    def test_no_user_yaml(self, tmp_path):
        blocks = generate_users(tmp_path)
        assert blocks == []

    def test_multiple_users_sorted(self, tmp_path):
        data = {
            "ZARA": {"type": "PERSON"},
            "ALICE": {"type": "PERSON"},
        }
        (tmp_path / "user.yaml").write_text(yaml.dump(data))
        blocks = generate_users(tmp_path)
        assert len(blocks) == 2
        # ALICE should come first (sorted)
        assert "ALICE" in blocks[0]
        assert "ZARA" in blocks[1]

    def test_import_block_present(self, tmp_path):
        data = {"BOB": {"type": "PERSON"}}
        (tmp_path / "user.yaml").write_text(yaml.dump(data))
        blocks = generate_users(tmp_path)
        assert "import {" in blocks[0]
        assert 'id = "BOB"' in blocks[0]


# ---------------------------------------------------------------------------
# generate_warehouses
# ---------------------------------------------------------------------------


class TestGenerateWarehouses:
    """Tests for generate_warehouses."""

    def test_generates_warehouse_block(self, tmp_path):
        data = {
            "COMPUTE_WH": {
                "size": "X-Small",
                "auto_suspend": 120,
                "auto_resume": True,
                "comment": "Main warehouse",
            }
        }
        (tmp_path / "warehouse.yaml").write_text(yaml.dump(data))
        blocks = generate_warehouses(tmp_path)
        assert len(blocks) == 1
        assert "snowflake_warehouse" in blocks[0]
        assert '"COMPUTE_WH"' in blocks[0]
        assert "XSMALL" in blocks[0]  # size mapped
        assert "120" in blocks[0]

    def test_size_mapping(self, tmp_path):
        """Various size formats are correctly mapped."""
        for yaml_size, expected_tf in [("Small", "SMALL"), ("X-Large", "XLARGE"), ("2X-Large", "XXLARGE")]:
            data = {"WH": {"size": yaml_size}}
            (tmp_path / "warehouse.yaml").write_text(yaml.dump(data))
            blocks = generate_warehouses(tmp_path)
            assert expected_tf in blocks[0], f"Expected {expected_tf} for size {yaml_size}"

    def test_default_auto_resume(self, tmp_path):
        """auto_resume defaults to True if not specified."""
        data = {"WH": {"size": "Small"}}
        (tmp_path / "warehouse.yaml").write_text(yaml.dump(data))
        blocks = generate_warehouses(tmp_path)
        assert "auto_resume" in blocks[0]
        assert "true" in blocks[0]

    def test_empty_warehouse_yaml(self, tmp_path):
        (tmp_path / "warehouse.yaml").write_text("")
        blocks = generate_warehouses(tmp_path)
        assert blocks == []

    def test_resource_monitor_included(self, tmp_path):
        data = {"WH": {"size": "Small", "resource_monitor": "MY_MON"}}
        (tmp_path / "warehouse.yaml").write_text(yaml.dump(data))
        blocks = generate_warehouses(tmp_path)
        assert "resource_monitor" in blocks[0]
        assert "MY_MON" in blocks[0]


# ---------------------------------------------------------------------------
# generate_business_roles
# ---------------------------------------------------------------------------


class TestGenerateBusinessRoles:
    """Tests for generate_business_roles."""

    def test_generates_role_and_grant_blocks(self, tmp_path):
        data = {
            "ANALYST": {
                "tech_roles": ["READ_ROLE"],
                "warehouse_usage": ["COMPUTE_WH"],
                "comment": "Analyst role",
            }
        }
        (tmp_path / "business_role.yaml").write_text(yaml.dump(data))
        role_blocks, grant_blocks = generate_business_roles(tmp_path)
        assert len(role_blocks) == 1
        assert "ANALYST__B_ROLE" in role_blocks[0]
        # tech role inheritance grant + warehouse usage grant
        assert len(grant_blocks) == 2

    def test_schema_owner_grant(self, tmp_path):
        data = {
            "ANALYST": {
                "schema_owner": ["MY_DB.MY_SCHEMA"],
            }
        }
        (tmp_path / "business_role.yaml").write_text(yaml.dump(data))
        role_blocks, grant_blocks = generate_business_roles(tmp_path)
        assert len(grant_blocks) == 1
        assert "OWNER__S_ROLE" in grant_blocks[0]

    def test_empty_business_role_yaml(self, tmp_path):
        (tmp_path / "business_role.yaml").write_text("")
        role_blocks, grant_blocks = generate_business_roles(tmp_path)
        assert role_blocks == []
        assert grant_blocks == []

    def test_no_file(self, tmp_path):
        role_blocks, grant_blocks = generate_business_roles(tmp_path)
        assert role_blocks == []
        assert grant_blocks == []

    def test_role_import_block(self, tmp_path):
        data = {"ANALYST": {"comment": "test"}}
        (tmp_path / "business_role.yaml").write_text(yaml.dump(data))
        role_blocks, _ = generate_business_roles(tmp_path)
        assert "import {" in role_blocks[0]
        assert "ANALYST__B_ROLE" in role_blocks[0]


# ---------------------------------------------------------------------------
# generate_tech_roles
# ---------------------------------------------------------------------------


class TestGenerateTechRoles:
    """Tests for generate_tech_roles."""

    def test_generates_role_and_grants(self, tmp_path):
        data = {
            "READ_ROLE": {
                "grants": {
                    "DATABASE:USAGE": ["MY_DB"],
                    "SCHEMA:USAGE": ["MY_DB.PUBLIC"],
                },
            }
        }
        (tmp_path / "tech_role.yaml").write_text(yaml.dump(data))
        role_blocks, grant_blocks = generate_tech_roles(tmp_path)
        assert len(role_blocks) == 1
        assert "READ_ROLE__T_ROLE" in role_blocks[0]
        assert len(grant_blocks) == 2  # one for DATABASE, one for SCHEMA

    def test_future_grants(self, tmp_path):
        data = {
            "READ_ROLE": {
                "future_grants": {
                    "TABLE:SELECT": ["MY_DB"],
                },
            }
        }
        (tmp_path / "tech_role.yaml").write_text(yaml.dump(data))
        role_blocks, grant_blocks = generate_tech_roles(tmp_path)
        assert len(grant_blocks) == 1
        assert "future" in grant_blocks[0].lower() or "TABLES" in grant_blocks[0]

    def test_schema_grant_has_on_schema(self, tmp_path):
        data = {
            "ROLE": {
                "grants": {"SCHEMA:USAGE": ["DB.SCHEMA"]},
            }
        }
        (tmp_path / "tech_role.yaml").write_text(yaml.dump(data))
        _, grant_blocks = generate_tech_roles(tmp_path)
        assert "on_schema" in grant_blocks[0]

    def test_warehouse_grant_has_on_account_object(self, tmp_path):
        data = {
            "ROLE": {
                "grants": {"WAREHOUSE:USAGE": ["WH"]},
            }
        }
        (tmp_path / "tech_role.yaml").write_text(yaml.dump(data))
        _, grant_blocks = generate_tech_roles(tmp_path)
        assert "on_account_object" in grant_blocks[0]

    def test_empty_tech_role_yaml(self, tmp_path):
        (tmp_path / "tech_role.yaml").write_text("")
        role_blocks, grant_blocks = generate_tech_roles(tmp_path)
        assert role_blocks == []
        assert grant_blocks == []

    def test_empty_targets_skipped(self, tmp_path):
        data = {
            "ROLE": {
                "grants": {"DATABASE:USAGE": []},
            }
        }
        (tmp_path / "tech_role.yaml").write_text(yaml.dump(data))
        _, grant_blocks = generate_tech_roles(tmp_path)
        assert grant_blocks == []


# ---------------------------------------------------------------------------
# generate_network_policies
# ---------------------------------------------------------------------------


class TestGenerateNetworkPolicies:
    """Tests for generate_network_policies."""

    def test_generates_policy_block(self, tmp_path):
        data = {
            "office_policy": {
                "allowed_ip_list": ["10.0.0.0/8"],
                "comment": "Office access",
            }
        }
        (tmp_path / "network_policy.yaml").write_text(yaml.dump(data))
        blocks = generate_network_policies(tmp_path)
        assert len(blocks) == 1
        assert "snowflake_network_policy" in blocks[0]
        assert "OFFICE_POLICY" in blocks[0]  # uppercased
        assert "10.0.0.0/8" in blocks[0]

    def test_empty_returns_empty(self, tmp_path):
        (tmp_path / "network_policy.yaml").write_text("")
        assert generate_network_policies(tmp_path) == []

    def test_no_file_returns_empty(self, tmp_path):
        assert generate_network_policies(tmp_path) == []


# ---------------------------------------------------------------------------
# generate_resource_monitors
# ---------------------------------------------------------------------------


class TestGenerateResourceMonitors:
    """Tests for generate_resource_monitors."""

    def test_generates_monitor_block(self, tmp_path):
        data = {
            "DAILY_MON": {
                "credit_quota": 100,
                "frequency": "DAILY",
                "triggers": {
                    80: "NOTIFY",
                    95: "SUSPEND",
                    100: "SUSPEND_IMMEDIATE",
                },
            }
        }
        (tmp_path / "resource_monitor.yaml").write_text(yaml.dump(data))
        blocks = generate_resource_monitors(tmp_path)
        assert len(blocks) == 1
        assert "snowflake_resource_monitor" in blocks[0]
        assert "100" in blocks[0]  # credit_quota
        assert "notify_triggers" in blocks[0]
        assert "suspend_triggers" in blocks[0]
        assert "suspend_immediate_triggers" in blocks[0]

    def test_no_triggers(self, tmp_path):
        data = {"MON": {"credit_quota": 50}}
        (tmp_path / "resource_monitor.yaml").write_text(yaml.dump(data))
        blocks = generate_resource_monitors(tmp_path)
        assert len(blocks) == 1
        assert "notify_triggers" not in blocks[0]

    def test_empty_returns_empty(self, tmp_path):
        (tmp_path / "resource_monitor.yaml").write_text("")
        assert generate_resource_monitors(tmp_path) == []


# ---------------------------------------------------------------------------
# generate_databases
# ---------------------------------------------------------------------------


class TestGenerateDatabases:
    """Tests for generate_databases."""

    def test_generates_database_block(self, tmp_path):
        db_dir = tmp_path / "MY_DB"
        db_dir.mkdir()
        (db_dir / "params.yaml").write_text(yaml.dump({"comment": "Production DB"}))
        blocks = generate_databases(tmp_path)
        assert len(blocks) == 1
        assert "snowflake_database" in blocks[0]
        assert '"MY_DB"' in blocks[0]
        assert "Production DB" in blocks[0]

    def test_sandbox_database(self, tmp_path):
        db_dir = tmp_path / "SANDBOX_DB"
        db_dir.mkdir()
        (db_dir / "params.yaml").write_text(yaml.dump({"is_sandbox": True}))
        blocks = generate_databases(tmp_path)
        assert len(blocks) == 1
        assert "Sandbox" in blocks[0] or "sandbox" in blocks[0].lower()

    def test_no_databases(self, tmp_path):
        blocks = generate_databases(tmp_path)
        assert blocks == []

    def test_multiple_databases_sorted(self, tmp_path):
        for name in ["ZOO_DB", "ALPHA_DB"]:
            d = tmp_path / name
            d.mkdir()
            (d / "params.yaml").write_text(yaml.dump({"comment": name}))
        blocks = generate_databases(tmp_path)
        assert len(blocks) == 2
        assert "ALPHA_DB" in blocks[0]
        assert "ZOO_DB" in blocks[1]


# ---------------------------------------------------------------------------
# render_section
# ---------------------------------------------------------------------------


class TestRenderSection:
    """Tests for the render_section helper."""

    def test_non_empty_blocks(self):
        result = render_section("Users", ['resource "snowflake_user" "a" {\n}'])
        assert "# Users" in result
        assert HEADER in result
        assert "snowflake_user" in result

    def test_empty_blocks(self):
        """Empty block list returns empty string."""
        result = render_section("Users", [])
        assert result == ""

    def test_multiple_blocks_joined(self):
        blocks = ["block_a", "block_b"]
        result = render_section("Section", blocks)
        assert "block_a" in result
        assert "block_b" in result


# ---------------------------------------------------------------------------
# generate_all (end-to-end)
# ---------------------------------------------------------------------------


class TestGenerateAll:
    """End-to-end tests for generate_all."""

    def _write_yaml(self, path, data):
        path.write_text(yaml.dump(data, default_flow_style=False))

    def test_full_generation(self, tmp_path):
        """generate_all with a complete config set produces all sections."""
        self._write_yaml(
            tmp_path / "user.yaml",
            {"ALICE": {"type": "PERSON", "email": "a@b.com"}},
        )
        self._write_yaml(
            tmp_path / "warehouse.yaml",
            {"WH": {"size": "Small"}},
        )
        self._write_yaml(
            tmp_path / "business_role.yaml",
            {"ANALYST": {"tech_roles": ["READ_ROLE"]}},
        )
        self._write_yaml(
            tmp_path / "tech_role.yaml",
            {"READ_ROLE": {"grants": {"DATABASE:USAGE": ["DB"]}}},
        )
        self._write_yaml(
            tmp_path / "network_policy.yaml",
            {"POL": {"allowed_ip_list": ["10.0.0.0/8"]}},
        )
        self._write_yaml(
            tmp_path / "resource_monitor.yaml",
            {"MON": {"credit_quota": 50}},
        )

        output = generate_all(tmp_path)
        assert isinstance(output, TerraformOutput)
        assert len(output.users) == 1
        assert len(output.warehouses) == 1
        assert len(output.roles) == 2  # 1 business + 1 tech
        assert len(output.grants) >= 1
        assert len(output.policies) >= 1
        assert len(output.resource_monitors) == 1
        assert "terraform" in output.main.lower()

    def test_empty_directory(self, tmp_path):
        """generate_all with an empty directory returns empty lists."""
        output = generate_all(tmp_path)
        assert output.users == []
        assert output.warehouses == []
        assert output.roles == []
        assert output.grants == []
        assert output.resource_monitors == []
        assert output.databases == []


# ---------------------------------------------------------------------------
# write_to_directory
# ---------------------------------------------------------------------------


class TestWriteToDirectory:
    """Tests for write_to_directory."""

    def test_creates_files(self, tmp_path):
        """write_to_directory creates .tf files in the output directory."""
        output = TerraformOutput()
        output.main = "terraform {}"
        output.users = ['resource "snowflake_user" "alice" {\n  name = "ALICE"\n}']
        output.warehouses = ['resource "snowflake_warehouse" "wh" {\n  name = "WH"\n}']

        out_dir = tmp_path / "terraform_out"
        write_to_directory(output, out_dir)

        assert out_dir.is_dir()
        assert (out_dir / "main.tf").exists()
        assert (out_dir / "users.tf").exists()
        assert (out_dir / "warehouses.tf").exists()

        # main.tf should contain the provider block
        main_content = (out_dir / "main.tf").read_text()
        assert "terraform" in main_content

    def test_skips_empty_sections(self, tmp_path):
        """Empty sections do not create files."""
        output = TerraformOutput()
        output.main = "terraform {}"
        # Everything else empty

        out_dir = tmp_path / "terraform_out"
        write_to_directory(output, out_dir)

        assert (out_dir / "main.tf").exists()
        assert not (out_dir / "users.tf").exists()
        assert not (out_dir / "warehouses.tf").exists()

    def test_creates_parent_directories(self, tmp_path):
        """write_to_directory creates parent directories if needed."""
        output = TerraformOutput()
        output.main = "terraform {}"

        out_dir = tmp_path / "deep" / "nested" / "dir"
        write_to_directory(output, out_dir)
        assert out_dir.is_dir()
        assert (out_dir / "main.tf").exists()
