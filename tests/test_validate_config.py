"""
Test Suite for SnowDDL YAML Configuration Validator.

Tests the validate_config.py script including:
- ValidationResult dataclass
- YAML loading helpers
- Per-file validators (user, business_role, tech_role, warehouse, network_policy, resource_monitor)
- Cross-reference integrity checks
- End-to-end run_validation orchestrator
"""

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
import yaml

from validate_config import (
    ValidationResult,
    _load_yaml,
    validate_user_yaml,
    validate_business_role_yaml,
    validate_tech_role_yaml,
    validate_warehouse_yaml,
    validate_network_policy_yaml,
    validate_resource_monitor_yaml,
    run_validation,
    _cross_reference_checks,
)


# ---------------------------------------------------------------------------
# ValidationResult dataclass
# ---------------------------------------------------------------------------


class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_initial_state(self):
        """A fresh result has empty lists and no errors/warnings."""
        result = ValidationResult()
        assert result.errors == []
        assert result.warnings == []
        assert result.info == []
        assert result.has_errors is False
        assert result.has_warnings is False

    def test_error_method(self):
        """error() appends to the errors list."""
        result = ValidationResult()
        result.error("something broke")
        assert result.errors == ["something broke"]
        assert result.has_errors is True
        assert result.has_warnings is False

    def test_warning_method(self):
        """warning() appends to the warnings list."""
        result = ValidationResult()
        result.warning("heads up")
        assert result.warnings == ["heads up"]
        assert result.has_warnings is True
        assert result.has_errors is False

    def test_ok_method(self):
        """ok() appends to the info list."""
        result = ValidationResult()
        result.ok("all good")
        assert result.info == ["all good"]
        assert result.has_errors is False
        assert result.has_warnings is False

    def test_multiple_messages(self):
        """Multiple messages accumulate correctly."""
        result = ValidationResult()
        result.error("err1")
        result.error("err2")
        result.warning("warn1")
        result.ok("info1")
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert len(result.info) == 1


# ---------------------------------------------------------------------------
# _load_yaml helper
# ---------------------------------------------------------------------------


class TestLoadYaml:
    """Tests for the _load_yaml helper function."""

    def test_valid_yaml(self, tmp_path):
        """Loading a valid YAML mapping returns (data, None)."""
        p = tmp_path / "good.yaml"
        p.write_text(yaml.dump({"KEY": {"type": "PERSON"}}))
        data, err = _load_yaml(p)
        assert err is None
        assert data == {"KEY": {"type": "PERSON"}}

    def test_invalid_yaml_syntax(self, tmp_path):
        """Loading broken YAML returns (None, error_message)."""
        p = tmp_path / "bad.yaml"
        p.write_text("key: [unterminated")
        data, err = _load_yaml(p)
        assert data is None
        assert "YAML syntax error" in err

    def test_missing_file(self, tmp_path):
        """Loading a non-existent file returns (None, error_message)."""
        p = tmp_path / "nonexistent.yaml"
        data, err = _load_yaml(p)
        assert data is None
        assert "File not found" in err

    def test_non_dict_yaml(self, tmp_path):
        """Loading a YAML file whose root is a list returns (None, error)."""
        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2\n")
        data, err = _load_yaml(p)
        assert data is None
        assert "Expected a YAML mapping" in err

    def test_empty_yaml(self, tmp_path):
        """Loading an empty YAML file returns ({}, None)."""
        p = tmp_path / "empty.yaml"
        p.write_text("")
        data, err = _load_yaml(p)
        assert err is None
        assert data == {}


# ---------------------------------------------------------------------------
# validate_user_yaml
# ---------------------------------------------------------------------------


class TestValidateUserYaml:
    """Tests for validate_user_yaml."""

    def test_valid_person_user(self):
        """A correctly defined PERSON user produces no errors."""
        data = {
            "ALICE": {
                "type": "PERSON",
                "email": "alice@example.com",
                "default_role": "SYSADMIN",
            }
        }
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert not result.has_errors
        assert not result.has_warnings

    def test_valid_service_user(self):
        """A correctly defined SERVICE user with RSA key produces no errors."""
        data = {
            "SVC_PIPELINE": {
                "type": "SERVICE",
                "rsa_public_key": "MIIBIjANBgkqhkiG9w0BAQE...",
            }
        }
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert not result.has_errors
        assert not result.has_warnings

    def test_missing_type_field(self):
        """A user without the 'type' field produces an error."""
        data = {"BOB": {"email": "bob@example.com"}}
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert result.has_errors
        assert any("missing required 'type'" in e for e in result.errors)

    def test_invalid_type_field(self):
        """A user with an invalid 'type' value produces an error."""
        data = {"CARL": {"type": "ROBOT"}}
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert result.has_errors
        assert any("invalid type 'ROBOT'" in e for e in result.errors)

    def test_person_without_email(self):
        """A PERSON user without email produces a warning."""
        data = {"DIANE": {"type": "PERSON"}}
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert not result.has_errors
        assert result.has_warnings
        assert any("should have 'email'" in w for w in result.warnings)

    def test_service_without_rsa_key(self):
        """A SERVICE user without rsa_public_key produces a warning."""
        data = {"SVC_NO_KEY": {"type": "SERVICE"}}
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert result.has_warnings
        assert any("should have 'rsa_public_key'" in w for w in result.warnings)

    def test_service_with_placeholder_rsa_key(self):
        """A SERVICE user with a placeholder RSA key produces a warning."""
        data = {
            "SVC_PLACEHOLDER": {
                "type": "SERVICE",
                "rsa_public_key": "replace-this-with-real-key",
            }
        }
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert result.has_warnings
        assert any("placeholder" in w for w in result.warnings)

    def test_service_with_example_rsa_key(self):
        """A SERVICE user with 'example' in RSA key produces a warning."""
        data = {
            "SVC_EXAMPLE": {
                "type": "SERVICE",
                "rsa_public_key": "example-public-key-data",
            }
        }
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert result.has_warnings
        assert any("placeholder" in w for w in result.warnings)

    def test_duplicate_users(self):
        """Duplicate user names (case-insensitive) produce an error."""
        data = {
            "admin_user": {"type": "PERSON", "email": "a@b.com"},
            "ADMIN_USER": {"type": "PERSON", "email": "a@b.com"},
        }
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert result.has_errors
        assert any("duplicate user name" in e for e in result.errors)

    def test_default_role_cross_reference_valid_system_role(self):
        """A default_role pointing at a system role produces no error."""
        data = {"EVE": {"type": "PERSON", "email": "e@b.com", "default_role": "SYSADMIN"}}
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles={"ANALYST"})
        assert not result.has_errors

    def test_default_role_cross_reference_valid_business_role(self):
        """A default_role matching a defined business role produces no error."""
        data = {"FRANK": {"type": "PERSON", "email": "f@b.com", "default_role": "ANALYST"}}
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles={"ANALYST"})
        assert not result.has_errors

    def test_default_role_cross_reference_with_suffix(self):
        """A default_role using __B_ROLE suffix resolves correctly."""
        data = {
            "GINA": {
                "type": "PERSON",
                "email": "g@b.com",
                "default_role": "ANALYST__B_ROLE",
            }
        }
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles={"ANALYST"})
        assert not result.has_errors

    def test_default_role_cross_reference_invalid(self):
        """A default_role not matching any role produces an error."""
        data = {
            "HANK": {"type": "PERSON", "email": "h@b.com", "default_role": "NONEXISTENT"}
        }
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles={"ANALYST"})
        assert result.has_errors
        assert any("does not match" in e for e in result.errors)

    def test_non_dict_user_entry(self):
        """A user whose config is not a dict produces an error."""
        data = {"BAD_USER": "just a string"}
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert result.has_errors
        assert any("expected a mapping" in e for e in result.errors)

    def test_info_message_count(self):
        """After validation, an info message reports the user count."""
        data = {
            "U1": {"type": "PERSON", "email": "u1@b.com"},
            "U2": {"type": "SERVICE", "rsa_public_key": "MIIBIj..."},
        }
        result = ValidationResult()
        validate_user_yaml(data, result, business_roles=set())
        assert any("2 users validated" in i for i in result.info)


# ---------------------------------------------------------------------------
# validate_business_role_yaml
# ---------------------------------------------------------------------------


class TestValidateBusinessRoleYaml:
    """Tests for validate_business_role_yaml."""

    def test_valid_role(self):
        """A valid business role with known tech_roles and warehouses passes."""
        data = {
            "ANALYST": {
                "tech_roles": ["READ_ROLE"],
                "warehouse_usage": ["COMPUTE_WH"],
                "schema_owner": ["MY_DB.MY_SCHEMA"],
            }
        }
        result = ValidationResult()
        validate_business_role_yaml(
            data, result, tech_roles={"READ_ROLE"}, warehouses={"COMPUTE_WH"}
        )
        assert not result.has_errors

    def test_missing_tech_role_reference(self):
        """Referencing a nonexistent tech_role produces an error."""
        data = {"ANALYST": {"tech_roles": ["GHOST_ROLE"]}}
        result = ValidationResult()
        validate_business_role_yaml(
            data, result, tech_roles={"READ_ROLE"}, warehouses=set()
        )
        assert result.has_errors
        assert any("GHOST_ROLE" in e for e in result.errors)

    def test_missing_warehouse_reference(self):
        """Referencing a nonexistent warehouse produces an error."""
        data = {"ANALYST": {"warehouse_usage": ["GHOST_WH"]}}
        result = ValidationResult()
        validate_business_role_yaml(
            data, result, tech_roles=set(), warehouses={"COMPUTE_WH"}
        )
        assert result.has_errors
        assert any("GHOST_WH" in e for e in result.errors)

    def test_invalid_schema_owner_format(self):
        """A schema_owner not in DB.SCHEMA format produces an error."""
        data = {"ANALYST": {"schema_owner": ["JUST_A_DB"]}}
        result = ValidationResult()
        validate_business_role_yaml(data, result, tech_roles=set(), warehouses=set())
        assert result.has_errors
        assert any("DB.SCHEMA format" in e for e in result.errors)

    def test_valid_schema_owner_format(self):
        """A schema_owner in proper DB.SCHEMA format passes."""
        data = {"ANALYST": {"schema_owner": ["PROD_DB.ANALYTICS"]}}
        result = ValidationResult()
        validate_business_role_yaml(data, result, tech_roles=set(), warehouses=set())
        assert not result.has_errors

    def test_schema_owner_with_special_chars(self):
        """A schema_owner with hyphens is invalid (only underscores allowed)."""
        data = {"ANALYST": {"schema_owner": ["PROD-DB.ANALYTICS"]}}
        result = ValidationResult()
        validate_business_role_yaml(data, result, tech_roles=set(), warehouses=set())
        assert result.has_errors

    def test_non_dict_role_entry(self):
        """A role whose config is not a dict produces an error."""
        data = {"BAD_ROLE": "not a dict"}
        result = ValidationResult()
        validate_business_role_yaml(data, result, tech_roles=set(), warehouses=set())
        assert result.has_errors
        assert any("expected a mapping" in e for e in result.errors)

    def test_duplicate_role_names(self):
        """Duplicate business role names produce an error."""
        data = {
            "analyst": {"tech_roles": []},
            "ANALYST": {"tech_roles": []},
        }
        result = ValidationResult()
        validate_business_role_yaml(data, result, tech_roles=set(), warehouses=set())
        assert result.has_errors
        assert any("duplicate role name" in e for e in result.errors)

    def test_empty_tech_roles_no_cross_ref(self):
        """When tech_roles set is empty, no cross-reference errors are raised."""
        data = {"ANALYST": {"tech_roles": ["ANY_ROLE"]}}
        result = ValidationResult()
        validate_business_role_yaml(
            data, result, tech_roles=set(), warehouses=set()
        )
        assert not result.has_errors


# ---------------------------------------------------------------------------
# validate_tech_role_yaml
# ---------------------------------------------------------------------------


class TestValidateTechRoleYaml:
    """Tests for validate_tech_role_yaml."""

    def test_valid_grant_keys(self):
        """Properly formatted grant keys pass validation."""
        data = {
            "READ_ROLE": {
                "grants": {
                    "DATABASE:USAGE": ["MY_DB"],
                    "SCHEMA:USAGE": ["MY_DB.PUBLIC"],
                },
            }
        }
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses=set())
        assert not result.has_errors

    def test_invalid_grant_key_no_colon(self):
        """A grant key without a colon produces an error."""
        data = {"BAD_ROLE": {"grants": {"DATABASE_USAGE": ["MY_DB"]}}}
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses=set())
        assert result.has_errors
        assert any("OBJECT_TYPE:PRIVILEGE" in e for e in result.errors)

    def test_invalid_grant_key_empty_privilege(self):
        """A grant key with empty privilege after colon produces an error."""
        data = {"BAD_ROLE": {"grants": {"DATABASE:": ["MY_DB"]}}}
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses=set())
        assert result.has_errors

    def test_invalid_object_type(self):
        """An unrecognised object type in grant key produces an error."""
        data = {"BAD_ROLE": {"grants": {"BANANA:USAGE": ["MY_DB"]}}}
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses=set())
        assert result.has_errors
        assert any("invalid object type" in e for e in result.errors)

    def test_warehouse_cross_reference_valid(self):
        """WAREHOUSE grants referencing valid warehouses pass."""
        data = {
            "WH_ROLE": {
                "grants": {"WAREHOUSE:USAGE": ["COMPUTE_WH"]},
            }
        }
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses={"COMPUTE_WH"})
        assert not result.has_errors

    def test_warehouse_cross_reference_invalid(self):
        """WAREHOUSE grants referencing unknown warehouses produce an error."""
        data = {
            "WH_ROLE": {
                "grants": {"WAREHOUSE:USAGE": ["GHOST_WH"]},
            }
        }
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses={"COMPUTE_WH"})
        assert result.has_errors
        assert any("GHOST_WH" in e for e in result.errors)

    def test_future_grants_validated_too(self):
        """future_grants section is validated the same as grants."""
        data = {
            "FG_ROLE": {
                "future_grants": {"INVALID_OBJ:SELECT": ["MY_DB"]},
            }
        }
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses=set())
        assert result.has_errors

    def test_non_dict_role_entry(self):
        """A tech role whose config is not a dict produces an error."""
        data = {"BAD": 42}
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses=set())
        assert result.has_errors

    def test_duplicate_tech_role_names(self):
        """Duplicate tech role names produce an error."""
        data = {
            "read_role": {"grants": {}},
            "READ_ROLE": {"grants": {}},
        }
        result = ValidationResult()
        validate_tech_role_yaml(data, result, warehouses=set())
        assert result.has_errors
        assert any("duplicate role name" in e for e in result.errors)


# ---------------------------------------------------------------------------
# validate_warehouse_yaml
# ---------------------------------------------------------------------------


class TestValidateWarehouseYaml:
    """Tests for validate_warehouse_yaml."""

    def test_valid_warehouse(self):
        """A warehouse with valid size and auto_suspend passes."""
        data = {
            "COMPUTE_WH": {
                "size": "X-Small",
                "auto_suspend": 120,
            }
        }
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors=set())
        assert not result.has_errors

    def test_valid_warehouse_sizes(self):
        """All valid warehouse sizes pass validation."""
        for size in ["X-Small", "Small", "Medium", "Large", "X-Large", "2X-Large"]:
            data = {"WH": {"size": size}}
            result = ValidationResult()
            validate_warehouse_yaml(data, result, resource_monitors=set())
            assert not result.has_errors, f"Size '{size}' should be valid"

    def test_invalid_warehouse_size(self):
        """An invalid warehouse size produces an error."""
        data = {"WH": {"size": "Mega"}}
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors=set())
        assert result.has_errors
        assert any("invalid size" in e for e in result.errors)

    def test_auto_suspend_valid(self):
        """A valid auto_suspend integer passes."""
        data = {"WH": {"auto_suspend": 60}}
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors=set())
        assert not result.has_errors

    def test_auto_suspend_negative(self):
        """A negative auto_suspend produces an error."""
        data = {"WH": {"auto_suspend": -1}}
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors=set())
        assert result.has_errors
        assert any("positive integer" in e for e in result.errors)

    def test_auto_suspend_non_integer(self):
        """A non-integer auto_suspend produces an error."""
        data = {"WH": {"auto_suspend": "fast"}}
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors=set())
        assert result.has_errors
        assert any("must be an integer" in e for e in result.errors)

    def test_auto_suspend_zero(self):
        """auto_suspend of 0 is valid (means never auto-suspend)."""
        data = {"WH": {"auto_suspend": 0}}
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors=set())
        assert not result.has_errors

    def test_resource_monitor_cross_reference_valid(self):
        """A valid resource_monitor reference passes."""
        data = {"WH": {"resource_monitor": "MY_MONITOR"}}
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors={"MY_MONITOR"})
        assert not result.has_errors

    def test_resource_monitor_cross_reference_invalid(self):
        """An unknown resource_monitor reference produces an error."""
        data = {"WH": {"resource_monitor": "GHOST_MONITOR"}}
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors={"MY_MONITOR"})
        assert result.has_errors
        assert any("GHOST_MONITOR" in e for e in result.errors)

    def test_non_dict_warehouse_entry(self):
        """A warehouse whose config is not a dict produces an error."""
        data = {"WH": "string-value"}
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors=set())
        assert result.has_errors

    def test_duplicate_warehouse_names(self):
        """Duplicate warehouse names produce an error."""
        data = {
            "compute_wh": {"size": "Small"},
            "COMPUTE_WH": {"size": "Small"},
        }
        result = ValidationResult()
        validate_warehouse_yaml(data, result, resource_monitors=set())
        assert result.has_errors
        assert any("duplicate warehouse name" in e for e in result.errors)


# ---------------------------------------------------------------------------
# validate_network_policy_yaml
# ---------------------------------------------------------------------------


class TestValidateNetworkPolicyYaml:
    """Tests for validate_network_policy_yaml."""

    def test_valid_cidr(self):
        """Valid CIDR notation in allowed_ip_list passes."""
        data = {
            "MY_POLICY": {
                "allowed_ip_list": ["10.0.0.0/8", "192.168.1.0/24", "88.216.232.26/32"]
            }
        }
        result = ValidationResult()
        validate_network_policy_yaml(data, result)
        assert not result.has_errors

    def test_invalid_cidr(self):
        """Invalid CIDR notation produces an error."""
        data = {"MY_POLICY": {"allowed_ip_list": ["not-an-ip"]}}
        result = ValidationResult()
        validate_network_policy_yaml(data, result)
        assert result.has_errors
        assert any("not valid CIDR" in e for e in result.errors)

    def test_blocked_ip_list_valid(self):
        """Valid CIDR in blocked_ip_list passes."""
        data = {"MY_POLICY": {"blocked_ip_list": ["10.0.0.1/32"]}}
        result = ValidationResult()
        validate_network_policy_yaml(data, result)
        assert not result.has_errors

    def test_blocked_ip_list_invalid(self):
        """Invalid CIDR in blocked_ip_list produces an error."""
        data = {"MY_POLICY": {"blocked_ip_list": ["garbage"]}}
        result = ValidationResult()
        validate_network_policy_yaml(data, result)
        assert result.has_errors
        assert any("blocked IP" in e for e in result.errors)

    def test_non_dict_policy_entry(self):
        """A policy whose config is not a dict produces an error."""
        data = {"BAD": 123}
        result = ValidationResult()
        validate_network_policy_yaml(data, result)
        assert result.has_errors

    def test_single_ip_no_cidr_suffix(self):
        """A bare IP address (no /mask) is valid CIDR for ip_network(strict=False)."""
        data = {"MY_POLICY": {"allowed_ip_list": ["192.168.1.1"]}}
        result = ValidationResult()
        validate_network_policy_yaml(data, result)
        assert not result.has_errors

    def test_duplicate_policy_names(self):
        """Duplicate policy names produce an error."""
        data = {
            "policy_a": {"allowed_ip_list": ["10.0.0.0/8"]},
            "POLICY_A": {"allowed_ip_list": ["10.0.0.0/8"]},
        }
        result = ValidationResult()
        validate_network_policy_yaml(data, result)
        assert result.has_errors


# ---------------------------------------------------------------------------
# validate_resource_monitor_yaml
# ---------------------------------------------------------------------------


class TestValidateResourceMonitorYaml:
    """Tests for validate_resource_monitor_yaml."""

    def test_valid_credit_quota(self):
        """A positive integer credit_quota passes."""
        data = {"MY_MONITOR": {"credit_quota": 100}}
        result = ValidationResult()
        validate_resource_monitor_yaml(data, result)
        assert not result.has_errors

    def test_invalid_credit_quota_zero(self):
        """A credit_quota of 0 produces an error (must be positive)."""
        data = {"MY_MONITOR": {"credit_quota": 0}}
        result = ValidationResult()
        validate_resource_monitor_yaml(data, result)
        assert result.has_errors
        assert any("must be positive" in e for e in result.errors)

    def test_invalid_credit_quota_negative(self):
        """A negative credit_quota produces an error."""
        data = {"MY_MONITOR": {"credit_quota": -50}}
        result = ValidationResult()
        validate_resource_monitor_yaml(data, result)
        assert result.has_errors

    def test_invalid_credit_quota_string(self):
        """A non-integer credit_quota produces an error."""
        data = {"MY_MONITOR": {"credit_quota": "lots"}}
        result = ValidationResult()
        validate_resource_monitor_yaml(data, result)
        assert result.has_errors
        assert any("must be an integer" in e for e in result.errors)

    def test_no_credit_quota_is_fine(self):
        """A monitor without credit_quota is acceptable."""
        data = {"MY_MONITOR": {"frequency": "MONTHLY"}}
        result = ValidationResult()
        validate_resource_monitor_yaml(data, result)
        assert not result.has_errors

    def test_non_dict_monitor_entry(self):
        """A monitor whose config is not a dict produces an error."""
        data = {"BAD": "nope"}
        result = ValidationResult()
        validate_resource_monitor_yaml(data, result)
        assert result.has_errors


# ---------------------------------------------------------------------------
# _cross_reference_checks
# ---------------------------------------------------------------------------


class TestCrossReferenceChecks:
    """Tests for _cross_reference_checks."""

    def _make_loaded(self, **overrides):
        """Build a loaded dict with defaults and optional overrides."""
        loaded = {
            "user.yaml": {},
            "business_role.yaml": {},
            "tech_role.yaml": {},
            "warehouse.yaml": {},
            "network_policy.yaml": {},
            "resource_monitor.yaml": {},
        }
        loaded.update(overrides)
        business_roles = {k.upper() for k in loaded["business_role.yaml"]}
        tech_roles = {k.upper() for k in loaded["tech_role.yaml"]}
        warehouses = {k.upper() for k in loaded["warehouse.yaml"]}
        resource_monitors = {k.upper() for k in loaded["resource_monitor.yaml"]}
        return loaded, business_roles, tech_roles, warehouses, resource_monitors

    def test_all_valid_cross_refs(self):
        """All cross-references resolve -- only ok messages."""
        loaded, br, tr, wh, rm = self._make_loaded(
            **{
                "user.yaml": {"ALICE": {"type": "PERSON", "default_role": "ANALYST"}},
                "business_role.yaml": {
                    "ANALYST": {
                        "tech_roles": ["READ_ROLE"],
                        "warehouse_usage": ["COMPUTE_WH"],
                    }
                },
                "tech_role.yaml": {
                    "READ_ROLE": {
                        "grants": {"WAREHOUSE:USAGE": ["COMPUTE_WH"]},
                    }
                },
                "warehouse.yaml": {"COMPUTE_WH": {"size": "Small"}},
                "resource_monitor.yaml": {},
            }
        )
        result = ValidationResult()
        _cross_reference_checks(loaded, result, br, tr, wh, rm)
        assert not result.has_errors

    def test_bad_user_default_role(self):
        """User default_role pointing to unknown role is caught."""
        loaded, br, tr, wh, rm = self._make_loaded(
            **{
                "user.yaml": {"ALICE": {"type": "PERSON", "default_role": "GHOST"}},
                "business_role.yaml": {"ANALYST": {}},
            }
        )
        result = ValidationResult()
        _cross_reference_checks(loaded, result, br, tr, wh, rm)
        assert result.has_errors
        assert any("GHOST" in e for e in result.errors)

    def test_bad_business_role_tech_role_ref(self):
        """Business role referencing non-existent tech role is caught."""
        loaded, br, tr, wh, rm = self._make_loaded(
            **{
                "business_role.yaml": {"ANALYST": {"tech_roles": ["MISSING"]}},
            }
        )
        result = ValidationResult()
        _cross_reference_checks(loaded, result, br, tr, wh, rm)
        assert result.has_errors
        assert any("MISSING" in e for e in result.errors)

    def test_bad_business_role_warehouse_ref(self):
        """Business role referencing non-existent warehouse is caught."""
        loaded, br, tr, wh, rm = self._make_loaded(
            **{
                "business_role.yaml": {"ANALYST": {"warehouse_usage": ["MISSING_WH"]}},
            }
        )
        result = ValidationResult()
        _cross_reference_checks(loaded, result, br, tr, wh, rm)
        assert result.has_errors
        assert any("MISSING_WH" in e for e in result.errors)

    def test_bad_warehouse_resource_monitor_ref(self):
        """Warehouse referencing non-existent resource monitor is caught."""
        loaded, br, tr, wh, rm = self._make_loaded(
            **{
                "warehouse.yaml": {"WH": {"resource_monitor": "MISSING_MON"}},
            }
        )
        result = ValidationResult()
        _cross_reference_checks(loaded, result, br, tr, wh, rm)
        assert result.has_errors
        assert any("MISSING_MON" in e for e in result.errors)

    def test_bad_tech_role_warehouse_grant(self):
        """Tech role WAREHOUSE grant referencing unknown warehouse is caught."""
        loaded, br, tr, wh, rm = self._make_loaded(
            **{
                "tech_role.yaml": {
                    "ROLE_X": {"grants": {"WAREHOUSE:USAGE": ["NOPE_WH"]}},
                },
            }
        )
        result = ValidationResult()
        _cross_reference_checks(loaded, result, br, tr, wh, rm)
        assert result.has_errors
        assert any("NOPE_WH" in e for e in result.errors)

    def test_system_role_as_default_role(self):
        """System roles like SYSADMIN are accepted as user default_role."""
        loaded, br, tr, wh, rm = self._make_loaded(
            **{
                "user.yaml": {"ADMIN": {"type": "PERSON", "default_role": "ACCOUNTADMIN"}},
            }
        )
        result = ValidationResult()
        _cross_reference_checks(loaded, result, br, tr, wh, rm)
        assert not result.has_errors


# ---------------------------------------------------------------------------
# run_validation (end-to-end)
# ---------------------------------------------------------------------------


class TestRunValidation:
    """End-to-end tests for run_validation using temporary config directories."""

    def _write_yaml(self, path, data):
        path.write_text(yaml.dump(data, default_flow_style=False))

    def test_valid_config_returns_zero(self, tmp_path):
        """A fully valid config directory returns exit code 0."""
        self._write_yaml(
            tmp_path / "user.yaml",
            {
                "ALICE": {
                    "type": "PERSON",
                    "email": "a@b.com",
                    "default_role": "ANALYST",
                }
            },
        )
        self._write_yaml(
            tmp_path / "business_role.yaml",
            {
                "ANALYST": {
                    "tech_roles": ["READ_ROLE"],
                    "warehouse_usage": ["COMPUTE_WH"],
                }
            },
        )
        self._write_yaml(
            tmp_path / "tech_role.yaml",
            {"READ_ROLE": {"grants": {"DATABASE:USAGE": ["MY_DB"]}}},
        )
        self._write_yaml(
            tmp_path / "warehouse.yaml",
            {"COMPUTE_WH": {"size": "Small", "auto_suspend": 120}},
        )
        self._write_yaml(
            tmp_path / "network_policy.yaml",
            {"OFFICE_POLICY": {"allowed_ip_list": ["10.0.0.0/8"]}},
        )
        self._write_yaml(
            tmp_path / "resource_monitor.yaml",
            {"DAILY_MONITOR": {"credit_quota": 50}},
        )

        exit_code = run_validation(tmp_path, target_files=None, strict=False, quiet=True)
        assert exit_code == 0

    def test_invalid_config_returns_one(self, tmp_path):
        """A config with errors returns exit code 1."""
        self._write_yaml(
            tmp_path / "user.yaml",
            {"BAD_USER": {"email": "no-type@x.com"}},  # missing type
        )
        exit_code = run_validation(tmp_path, target_files=None, strict=False, quiet=True)
        assert exit_code == 1

    def test_warnings_only_returns_zero_without_strict(self, tmp_path):
        """Warnings without --strict return exit code 0."""
        self._write_yaml(
            tmp_path / "user.yaml",
            {"SVC": {"type": "SERVICE"}},  # missing rsa key = warning
        )
        exit_code = run_validation(tmp_path, target_files=None, strict=False, quiet=True)
        assert exit_code == 0

    def test_warnings_with_strict_returns_one(self, tmp_path):
        """Warnings with --strict return exit code 1."""
        self._write_yaml(
            tmp_path / "user.yaml",
            {"SVC": {"type": "SERVICE"}},  # missing rsa key = warning
        )
        exit_code = run_validation(tmp_path, target_files=None, strict=True, quiet=True)
        assert exit_code == 1

    def test_missing_config_dir_returns_one(self, tmp_path):
        """A non-existent config directory returns exit code 1."""
        exit_code = run_validation(
            tmp_path / "nonexistent", target_files=None, strict=False, quiet=True
        )
        assert exit_code == 1

    def test_target_specific_file(self, tmp_path):
        """Validating a specific target file works."""
        self._write_yaml(
            tmp_path / "user.yaml",
            {"ALICE": {"type": "PERSON", "email": "a@b.com"}},
        )
        self._write_yaml(
            tmp_path / "warehouse.yaml",
            {"WH": {"size": "Mega"}},  # invalid size = error
        )
        # Only validate user.yaml -- should pass despite warehouse errors
        exit_code = run_validation(
            tmp_path,
            target_files=[str(tmp_path / "user.yaml")],
            strict=False,
            quiet=True,
        )
        assert exit_code == 0

    def test_empty_config_dir_returns_zero(self, tmp_path):
        """An empty config directory (no files) returns 0."""
        exit_code = run_validation(tmp_path, target_files=None, strict=False, quiet=True)
        assert exit_code == 0

    def test_yaml_syntax_error_returns_one(self, tmp_path):
        """A file with YAML syntax errors returns exit code 1."""
        (tmp_path / "user.yaml").write_text("key: [broken")
        exit_code = run_validation(tmp_path, target_files=None, strict=False, quiet=True)
        assert exit_code == 1
