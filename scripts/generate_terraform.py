#!/usr/bin/env python3
"""
SnowDDL to Terraform Generator

Converts SnowDDL YAML configurations into Terraform HCL files with import blocks
for seamless migration from SnowDDL to Terraform-managed infrastructure.

Usage:
    uv run generate-terraform                      # Output to stdout
    uv run generate-terraform --output terraform/  # Write to directory
    uv run generate-terraform --format json        # JSON format
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import argparse
import re
from dataclasses import dataclass, field
from typing import Any

import yaml


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def to_terraform_name(name: str) -> str:
    """Convert Snowflake name to valid Terraform resource name."""
    # Lowercase, replace non-alphanumeric with underscore
    tf_name = re.sub(r"[^a-zA-Z0-9]", "_", name.lower())
    # Remove leading numbers
    if tf_name and tf_name[0].isdigit():
        tf_name = "_" + tf_name
    return tf_name


def to_hcl_string(value: str) -> str:
    """Escape string for HCL."""
    if value is None:
        return '""'
    return f'"{value}"'


def to_hcl_list(items: list[str]) -> str:
    """Convert list to HCL list format."""
    if not items:
        return "[]"
    quoted = [f'"{item}"' for item in items]
    return f"[{', '.join(quoted)}]"


def to_hcl_bool(value: bool) -> str:
    """Convert bool to HCL."""
    return "true" if value else "false"


def indent(text: str, spaces: int = 2) -> str:
    """Indent each line of text."""
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.split("\n"))


# =============================================================================
# TRANSFORMER BASE CLASS
# =============================================================================


@dataclass
class TransformResult:
    """Result of a transformation."""

    resources: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


class BaseTransformer:
    """Base class for all transformers."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        """Transform config to Terraform resources and imports."""
        raise NotImplementedError


# =============================================================================
# WAREHOUSE TRANSFORMER
# =============================================================================


class WarehouseTransformer(BaseTransformer):
    """Transform warehouse.yaml to Terraform."""

    SIZE_MAPPING = {
        "X-Small": "XSMALL",
        "Small": "SMALL",
        "Medium": "MEDIUM",
        "Large": "LARGE",
        "X-Large": "XLARGE",
        "2X-Large": "XXLARGE",
        "3X-Large": "XXXLARGE",
        "4X-Large": "X4LARGE",
        "5X-Large": "X5LARGE",
        "6X-Large": "X6LARGE",
    }

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for name, wh_config in config.items():
            tf_name = to_terraform_name(name)
            size = self.SIZE_MAPPING.get(wh_config.get("size", "X-Small"), "XSMALL")

            resource = f'''resource "snowflake_warehouse" "{tf_name}" {{
  name           = "{name}"
  warehouse_size = "{size}"
  auto_suspend   = {wh_config.get("auto_suspend", 60)}
  auto_resume    = true'''

            if wh_config.get("comment"):
                resource += f'\n  comment        = {to_hcl_string(wh_config["comment"])}'

            if wh_config.get("min_cluster_count"):
                resource += f'\n  min_cluster_count = {wh_config["min_cluster_count"]}'

            if wh_config.get("max_cluster_count"):
                resource += f'\n  max_cluster_count = {wh_config["max_cluster_count"]}'

            if wh_config.get("resource_monitor"):
                monitor_ref = to_terraform_name(wh_config["resource_monitor"])
                resource += f'\n  resource_monitor = snowflake_resource_monitor.{monitor_ref}.name'

            resource += "\n}"
            result.resources.append(resource)

            # Import block
            import_block = f'''import {{
  to = snowflake_warehouse.{tf_name}
  id = "{name}"
}}'''
            result.imports.append(import_block)

        return result


# =============================================================================
# USER TRANSFORMER
# =============================================================================


class UserTransformer(BaseTransformer):
    """Transform user.yaml to Terraform."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for name, user_config in config.items():
            tf_name = to_terraform_name(name)

            resource = f'''resource "snowflake_user" "{tf_name}" {{
  name         = "{name}"'''

            if user_config.get("email"):
                resource += f'\n  email        = {to_hcl_string(user_config["email"])}'

            if user_config.get("first_name"):
                resource += f'\n  first_name   = {to_hcl_string(user_config["first_name"])}'

            if user_config.get("last_name"):
                resource += f'\n  last_name    = {to_hcl_string(user_config["last_name"])}'

            if user_config.get("default_role"):
                resource += f'\n  default_role = {to_hcl_string(user_config["default_role"])}'

            if user_config.get("comment"):
                resource += f'\n  comment      = {to_hcl_string(user_config["comment"])}'

            # Handle RSA public key (mark as sensitive)
            if user_config.get("rsa_public_key"):
                # Clean up the key - remove newlines for Terraform
                key = user_config["rsa_public_key"].strip()
                resource += f'\n  rsa_public_key = <<-EOT\n{key}\nEOT'

            # Note: We intentionally skip password - should be managed separately

            resource += "\n}"
            result.resources.append(resource)

            # Import block
            import_block = f'''import {{
  to = snowflake_user.{tf_name}
  id = "{name}"
}}'''
            result.imports.append(import_block)

        return result


# =============================================================================
# RESOURCE MONITOR TRANSFORMER
# =============================================================================


class ResourceMonitorTransformer(BaseTransformer):
    """Transform resource_monitor.yaml to Terraform."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for name, monitor_config in config.items():
            tf_name = to_terraform_name(name)

            resource = f'''resource "snowflake_resource_monitor" "{tf_name}" {{
  name = "{name}"'''

            if monitor_config.get("credit_quota"):
                resource += f'\n  credit_quota = {monitor_config["credit_quota"]}'

            if monitor_config.get("frequency"):
                resource += f'\n  frequency = "{monitor_config["frequency"].upper()}"'

            if monitor_config.get("start_timestamp"):
                resource += f'\n  start_timestamp = {to_hcl_string(monitor_config["start_timestamp"])}'

            # Notify triggers
            if monitor_config.get("notify_triggers"):
                triggers = monitor_config["notify_triggers"]
                if isinstance(triggers, list):
                    resource += f"\n  notify_triggers = {to_hcl_list([str(t) for t in triggers])}"

            # Suspend triggers
            if monitor_config.get("suspend_trigger"):
                resource += f'\n  suspend_trigger = {monitor_config["suspend_trigger"]}'

            if monitor_config.get("suspend_immediate_trigger"):
                resource += f'\n  suspend_immediate_trigger = {monitor_config["suspend_immediate_trigger"]}'

            resource += "\n}"
            result.resources.append(resource)

            # Import block
            import_block = f'''import {{
  to = snowflake_resource_monitor.{tf_name}
  id = "{name}"
}}'''
            result.imports.append(import_block)

        return result


# =============================================================================
# NETWORK POLICY TRANSFORMER
# =============================================================================


class NetworkPolicyTransformer(BaseTransformer):
    """Transform network_policy.yaml to Terraform."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for name, policy_config in config.items():
            tf_name = to_terraform_name(name)

            resource = f'''resource "snowflake_network_policy" "{tf_name}" {{
  name = "{name}"'''

            if policy_config.get("allowed_ip_list"):
                resource += f'\n  allowed_ip_list = {to_hcl_list(policy_config["allowed_ip_list"])}'

            if policy_config.get("blocked_ip_list"):
                resource += f'\n  blocked_ip_list = {to_hcl_list(policy_config["blocked_ip_list"])}'

            if policy_config.get("comment"):
                resource += f'\n  comment = {to_hcl_string(policy_config["comment"])}'

            resource += "\n}"
            result.resources.append(resource)

            # Import block
            import_block = f'''import {{
  to = snowflake_network_policy.{tf_name}
  id = "{name}"
}}'''
            result.imports.append(import_block)

        return result


# =============================================================================
# AUTHENTICATION POLICY TRANSFORMER
# =============================================================================


class AuthenticationPolicyTransformer(BaseTransformer):
    """Transform authentication_policy.yaml to Terraform."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for name, policy_config in config.items():
            tf_name = to_terraform_name(name)

            resource = f'''resource "snowflake_authentication_policy" "{tf_name}" {{
  name     = "{name}"
  database = "SNOWFLAKE"
  schema   = "CORE"'''

            if policy_config.get("mfa_authentication_methods"):
                methods = policy_config["mfa_authentication_methods"]
                resource += f'\n  mfa_authentication_methods = {to_hcl_list(methods)}'

            if policy_config.get("client_types"):
                resource += f'\n  client_types = {to_hcl_list(policy_config["client_types"])}'

            if policy_config.get("security_integrations"):
                resource += f'\n  security_integrations = {to_hcl_list(policy_config["security_integrations"])}'

            if policy_config.get("comment"):
                resource += f'\n  comment = {to_hcl_string(policy_config["comment"])}'

            resource += "\n}"
            result.resources.append(resource)

            # Import block
            import_block = f'''import {{
  to = snowflake_authentication_policy.{tf_name}
  id = "SNOWFLAKE|CORE|{name}"
}}'''
            result.imports.append(import_block)

        return result


# =============================================================================
# PASSWORD POLICY TRANSFORMER
# =============================================================================


class PasswordPolicyTransformer(BaseTransformer):
    """Transform password_policy.yaml to Terraform."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for name, policy_config in config.items():
            tf_name = to_terraform_name(name)

            resource = f'''resource "snowflake_password_policy" "{tf_name}" {{
  name     = "{name}"
  database = "SNOWFLAKE"
  schema   = "CORE"'''

            # Map all password policy attributes
            int_attrs = [
                "password_min_length",
                "password_max_length",
                "password_min_upper_case_chars",
                "password_min_lower_case_chars",
                "password_min_numeric_chars",
                "password_min_special_chars",
                "password_min_age_days",
                "password_max_age_days",
                "password_max_retries",
                "password_lockout_time_mins",
                "password_history",
            ]

            for attr in int_attrs:
                if attr in policy_config:
                    tf_attr = attr
                    resource += f"\n  {tf_attr} = {policy_config[attr]}"

            if policy_config.get("comment"):
                resource += f'\n  comment = {to_hcl_string(policy_config["comment"])}'

            resource += "\n}"
            result.resources.append(resource)

            # Import block
            import_block = f'''import {{
  to = snowflake_password_policy.{tf_name}
  id = "SNOWFLAKE|CORE|{name}"
}}'''
            result.imports.append(import_block)

        return result


# =============================================================================
# SESSION POLICY TRANSFORMER
# =============================================================================


class SessionPolicyTransformer(BaseTransformer):
    """Transform session_policy.yaml to Terraform."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for name, policy_config in config.items():
            tf_name = to_terraform_name(name)

            resource = f'''resource "snowflake_session_policy" "{tf_name}" {{
  name     = "{name}"
  database = "SNOWFLAKE"
  schema   = "CORE"'''

            if policy_config.get("session_idle_timeout_mins"):
                resource += f'\n  session_idle_timeout_mins = {policy_config["session_idle_timeout_mins"]}'

            if policy_config.get("session_ui_idle_timeout_mins"):
                resource += f'\n  session_ui_idle_timeout_mins = {policy_config["session_ui_idle_timeout_mins"]}'

            if policy_config.get("comment"):
                resource += f'\n  comment = {to_hcl_string(policy_config["comment"])}'

            resource += "\n}"
            result.resources.append(resource)

            # Import block
            import_block = f'''import {{
  to = snowflake_session_policy.{tf_name}
  id = "SNOWFLAKE|CORE|{name}"
}}'''
            result.imports.append(import_block)

        return result


# =============================================================================
# ROLE TRANSFORMER
# =============================================================================


class RoleTransformer(BaseTransformer):
    """Transform tech_role.yaml and business_role.yaml to Terraform."""

    def __init__(self, role_type: str = "tech"):
        self.role_type = role_type
        self.suffix = "__T_ROLE" if role_type == "tech" else "__B_ROLE"

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for name, role_config in config.items():
            # SnowDDL adds suffix automatically
            full_name = f"{name}{self.suffix}"
            tf_name = to_terraform_name(name)

            resource = f'''resource "snowflake_account_role" "{tf_name}" {{
  name = "{full_name}"'''

            if role_config.get("comment"):
                resource += f'\n  comment = {to_hcl_string(role_config["comment"])}'

            resource += "\n}"
            result.resources.append(resource)

            # Import block
            import_block = f'''import {{
  to = snowflake_account_role.{tf_name}
  id = "{full_name}"
}}'''
            result.imports.append(import_block)

        return result


# =============================================================================
# GRANT TRANSFORMER
# =============================================================================


class GrantTransformer(BaseTransformer):
    """Transform grants from tech_role.yaml to Terraform grant resources."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for role_name, role_config in config.items():
            role_tf_name = to_terraform_name(role_name)
            full_role_name = f"{role_name}__T_ROLE"

            # Process regular grants
            if role_config.get("grants"):
                self._process_grants(
                    result, role_tf_name, full_role_name, role_config["grants"], "grants"
                )

            # Process future grants
            if role_config.get("future_grants"):
                self._process_grants(
                    result,
                    role_tf_name,
                    full_role_name,
                    role_config["future_grants"],
                    "future_grants",
                )

        return result

    def _process_grants(
        self,
        result: TransformResult,
        role_tf_name: str,
        full_role_name: str,
        grants: dict,
        grant_type: str,
    ):
        """Process a grants or future_grants section."""
        for grant_spec, targets in grants.items():
            if not targets:
                continue

            # Parse grant spec: "OBJECT_TYPE:PRIVILEGE1,PRIVILEGE2"
            parts = grant_spec.split(":")
            if len(parts) != 2:
                continue

            object_type = parts[0].upper()
            privileges = [p.strip().upper() for p in parts[1].split(",")]

            for target in targets:
                # Generate unique resource name
                target_tf = to_terraform_name(target)
                prefix = "future_" if grant_type == "future_grants" else ""
                resource_name = f"{role_tf_name}_{prefix}{object_type.lower()}_{target_tf}"

                if object_type == "DATABASE":
                    resource = self._database_grant(
                        resource_name, full_role_name, privileges, target, grant_type
                    )
                elif object_type == "SCHEMA":
                    resource = self._schema_grant(
                        resource_name, full_role_name, privileges, target, grant_type
                    )
                elif object_type == "WAREHOUSE":
                    resource = self._warehouse_grant(
                        resource_name, full_role_name, privileges, target, grant_type
                    )
                elif object_type in ("TABLE", "VIEW", "STAGE", "FILE_FORMAT", "SEQUENCE"):
                    resource = self._schema_object_grant(
                        resource_name,
                        full_role_name,
                        privileges,
                        target,
                        object_type,
                        grant_type,
                    )
                else:
                    continue

                if resource:
                    result.resources.append(resource)

    def _database_grant(
        self,
        resource_name: str,
        role_name: str,
        privileges: list[str],
        database: str,
        grant_type: str,
    ) -> str:
        return f'''resource "snowflake_grant_privileges_to_account_role" "{resource_name}" {{
  account_role_name = "{role_name}"
  privileges        = {to_hcl_list(privileges)}
  on_account_object {{
    object_type = "DATABASE"
    object_name = "{database}"
  }}
}}'''

    def _schema_grant(
        self,
        resource_name: str,
        role_name: str,
        privileges: list[str],
        schema_fqn: str,
        grant_type: str,
    ) -> str:
        # Schema FQN is DATABASE.SCHEMA
        parts = schema_fqn.split(".")
        if len(parts) != 2:
            return ""
        database, schema = parts

        return f'''resource "snowflake_grant_privileges_to_account_role" "{resource_name}" {{
  account_role_name = "{role_name}"
  privileges        = {to_hcl_list(privileges)}
  on_schema {{
    schema_name = "{database}.{schema}"
  }}
}}'''

    def _warehouse_grant(
        self,
        resource_name: str,
        role_name: str,
        privileges: list[str],
        warehouse: str,
        grant_type: str,
    ) -> str:
        return f'''resource "snowflake_grant_privileges_to_account_role" "{resource_name}" {{
  account_role_name = "{role_name}"
  privileges        = {to_hcl_list(privileges)}
  on_account_object {{
    object_type = "WAREHOUSE"
    object_name = "{warehouse}"
  }}
}}'''

    def _schema_object_grant(
        self,
        resource_name: str,
        role_name: str,
        privileges: list[str],
        database: str,
        object_type: str,
        grant_type: str,
    ) -> str:
        if grant_type == "future_grants":
            return f'''resource "snowflake_grant_privileges_to_account_role" "{resource_name}" {{
  account_role_name = "{role_name}"
  privileges        = {to_hcl_list(privileges)}
  on_schema_object {{
    future {{
      object_type_plural = "{object_type}S"
      in_database        = "{database}"
    }}
  }}
}}'''
        else:
            return f'''resource "snowflake_grant_privileges_to_account_role" "{resource_name}" {{
  account_role_name = "{role_name}"
  privileges        = {to_hcl_list(privileges)}
  on_schema_object {{
    all {{
      object_type_plural = "{object_type}S"
      in_database        = "{database}"
    }}
  }}
}}'''


# =============================================================================
# BUSINESS ROLE GRANT TRANSFORMER
# =============================================================================


class BusinessRoleGrantTransformer(BaseTransformer):
    """Transform business_role.yaml role hierarchy to Terraform."""

    def transform(self, config: dict[str, Any]) -> TransformResult:
        result = TransformResult()

        for role_name, role_config in config.items():
            business_role = f"{role_name}__B_ROLE"
            role_tf_name = to_terraform_name(role_name)

            # Grant tech roles to business role
            if role_config.get("tech_roles"):
                for tech_role in role_config["tech_roles"]:
                    tech_role_full = f"{tech_role}__T_ROLE"
                    tech_tf_name = to_terraform_name(tech_role)
                    resource_name = f"{role_tf_name}_inherits_{tech_tf_name}"

                    resource = f'''resource "snowflake_grant_account_role" "{resource_name}" {{
  role_name        = "{tech_role_full}"
  parent_role_name = "{business_role}"
}}'''
                    result.resources.append(resource)

            # Grant warehouse usage
            if role_config.get("warehouse_usage"):
                for warehouse in role_config["warehouse_usage"]:
                    wh_tf_name = to_terraform_name(warehouse)
                    resource_name = f"{role_tf_name}_warehouse_{wh_tf_name}"

                    resource = f'''resource "snowflake_grant_privileges_to_account_role" "{resource_name}" {{
  account_role_name = "{business_role}"
  privileges        = ["USAGE"]
  on_account_object {{
    object_type = "WAREHOUSE"
    object_name = "{warehouse}"
  }}
}}'''
                    result.resources.append(resource)

        return result


# =============================================================================
# DATABASE TRANSFORMER
# =============================================================================


class DatabaseTransformer(BaseTransformer):
    """Transform database directories to Terraform."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir

    def transform(self, config: dict[str, Any] = None) -> TransformResult:
        result = TransformResult()

        # Scan for database directories (directories with params.yaml)
        snowddl_dir = self.config_dir
        for item in snowddl_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                params_file = item / "params.yaml"
                if params_file.exists():
                    db_name = item.name
                    self._process_database(result, db_name, params_file)

                    # Process schemas within database
                    for schema_dir in item.iterdir():
                        if schema_dir.is_dir():
                            schema_params = schema_dir / "params.yaml"
                            if schema_params.exists():
                                self._process_schema(
                                    result, db_name, schema_dir.name, schema_params
                                )

        return result

    def _process_database(
        self, result: TransformResult, db_name: str, params_file: Path
    ):
        tf_name = to_terraform_name(db_name)

        with open(params_file) as f:
            params = yaml.safe_load(f) or {}

        resource = f'''resource "snowflake_database" "{tf_name}" {{
  name = "{db_name}"'''

        if params.get("comment"):
            resource += f'\n  comment = {to_hcl_string(params["comment"])}'

        if params.get("is_sandbox"):
            resource += "\n  is_transient = true"

        resource += "\n}"
        result.resources.append(resource)

        # Import block
        import_block = f'''import {{
  to = snowflake_database.{tf_name}
  id = "{db_name}"
}}'''
        result.imports.append(import_block)

    def _process_schema(
        self, result: TransformResult, db_name: str, schema_name: str, params_file: Path
    ):
        tf_name = to_terraform_name(f"{db_name}_{schema_name}")

        with open(params_file) as f:
            params = yaml.safe_load(f) or {}

        db_tf_name = to_terraform_name(db_name)

        resource = f'''resource "snowflake_schema" "{tf_name}" {{
  name     = "{schema_name}"
  database = snowflake_database.{db_tf_name}.name'''

        if params.get("comment"):
            resource += f'\n  comment = {to_hcl_string(params["comment"])}'

        if params.get("is_sandbox"):
            resource += "\n  is_transient = true"

        resource += "\n}"
        result.resources.append(resource)

        # Import block
        import_block = f'''import {{
  to = snowflake_schema.{tf_name}
  id = "{db_name}|{schema_name}"
}}'''
        result.imports.append(import_block)


# =============================================================================
# TERRAFORM GENERATOR
# =============================================================================


class TerraformGenerator:
    """Main generator that coordinates all transformers."""

    PROVIDER_TEMPLATE = '''# =============================================================================
# Terraform Provider Configuration for Snowflake
# Generated by SnowTower - https://github.com/Database-Tycoon/SnowTower
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 2.0"
    }
  }
}

provider "snowflake" {
  organization_name = var.snowflake_organization
  account_name      = var.snowflake_account
  user              = var.snowflake_user
  role              = var.snowflake_role
  authenticator     = "SNOWFLAKE_JWT"
  private_key_path  = var.snowflake_private_key_path
}
'''

    VARIABLES_TEMPLATE = '''# =============================================================================
# Terraform Variables
# Generated by SnowTower
# =============================================================================

variable "snowflake_organization" {
  description = "Snowflake organization name"
  type        = string
}

variable "snowflake_account" {
  description = "Snowflake account name"
  type        = string
}

variable "snowflake_user" {
  description = "Snowflake user for Terraform"
  type        = string
}

variable "snowflake_role" {
  description = "Snowflake role for Terraform operations"
  type        = string
  default     = "ACCOUNTADMIN"
}

variable "snowflake_private_key_path" {
  description = "Path to RSA private key for authentication"
  type        = string
  default     = "~/.ssh/snowflake_terraform_key.p8"
}
'''

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir

    def generate_all(self) -> dict[str, str]:
        """Generate all Terraform files.

        Returns:
            dict mapping filename to file content
        """
        files = {}

        # Provider and variables
        files["main.tf"] = self.PROVIDER_TEMPLATE
        files["variables.tf"] = self.VARIABLES_TEMPLATE

        # Track all imports
        all_imports = []

        # Warehouses
        wh_file = self.config_dir / "warehouse.yaml"
        if wh_file.exists():
            with open(wh_file) as f:
                config = yaml.safe_load(f) or {}
            result = WarehouseTransformer().transform(config)
            if result.resources:
                files["warehouses.tf"] = self._file_header("Warehouses") + "\n\n".join(
                    result.resources
                )
                all_imports.extend(result.imports)

        # Users
        user_file = self.config_dir / "user.yaml"
        if user_file.exists():
            with open(user_file) as f:
                config = yaml.safe_load(f) or {}
            result = UserTransformer().transform(config)
            if result.resources:
                files["users.tf"] = self._file_header("Users") + "\n\n".join(
                    result.resources
                )
                all_imports.extend(result.imports)

        # Resource Monitors
        monitor_file = self.config_dir / "resource_monitor.yaml"
        if monitor_file.exists():
            with open(monitor_file) as f:
                config = yaml.safe_load(f) or {}
            result = ResourceMonitorTransformer().transform(config)
            if result.resources:
                files["monitors.tf"] = self._file_header(
                    "Resource Monitors"
                ) + "\n\n".join(result.resources)
                all_imports.extend(result.imports)

        # Policies
        policy_resources = []
        policy_imports = []

        # Network policies
        np_file = self.config_dir / "network_policy.yaml"
        if np_file.exists():
            with open(np_file) as f:
                config = yaml.safe_load(f) or {}
            result = NetworkPolicyTransformer().transform(config)
            policy_resources.extend(result.resources)
            policy_imports.extend(result.imports)

        # Authentication policies
        ap_file = self.config_dir / "authentication_policy.yaml"
        if ap_file.exists():
            with open(ap_file) as f:
                config = yaml.safe_load(f) or {}
            result = AuthenticationPolicyTransformer().transform(config)
            policy_resources.extend(result.resources)
            policy_imports.extend(result.imports)

        # Password policies
        pp_file = self.config_dir / "password_policy.yaml"
        if pp_file.exists():
            with open(pp_file) as f:
                config = yaml.safe_load(f) or {}
            result = PasswordPolicyTransformer().transform(config)
            policy_resources.extend(result.resources)
            policy_imports.extend(result.imports)

        # Session policies
        sp_file = self.config_dir / "session_policy.yaml"
        if sp_file.exists():
            with open(sp_file) as f:
                config = yaml.safe_load(f) or {}
            result = SessionPolicyTransformer().transform(config)
            policy_resources.extend(result.resources)
            policy_imports.extend(result.imports)

        if policy_resources:
            files["policies.tf"] = self._file_header("Policies") + "\n\n".join(
                policy_resources
            )
            all_imports.extend(policy_imports)

        # Roles
        role_resources = []
        role_imports = []

        # Tech roles
        tr_file = self.config_dir / "tech_role.yaml"
        if tr_file.exists():
            with open(tr_file) as f:
                config = yaml.safe_load(f) or {}
            result = RoleTransformer("tech").transform(config)
            role_resources.extend(result.resources)
            role_imports.extend(result.imports)

        # Business roles
        br_file = self.config_dir / "business_role.yaml"
        if br_file.exists():
            with open(br_file) as f:
                config = yaml.safe_load(f) or {}
            result = RoleTransformer("business").transform(config)
            role_resources.extend(result.resources)
            role_imports.extend(result.imports)

        if role_resources:
            files["roles.tf"] = self._file_header("Roles") + "\n\n".join(role_resources)
            all_imports.extend(role_imports)

        # Grants
        grant_resources = []

        # Tech role grants
        if tr_file.exists():
            with open(tr_file) as f:
                config = yaml.safe_load(f) or {}
            result = GrantTransformer().transform(config)
            grant_resources.extend(result.resources)

        # Business role grants (role hierarchy + warehouse usage)
        if br_file.exists():
            with open(br_file) as f:
                config = yaml.safe_load(f) or {}
            result = BusinessRoleGrantTransformer().transform(config)
            grant_resources.extend(result.resources)

        if grant_resources:
            files["grants.tf"] = self._file_header("Grants") + "\n\n".join(
                grant_resources
            )

        # Databases and Schemas
        result = DatabaseTransformer(self.config_dir).transform()
        if result.resources:
            files["databases.tf"] = self._file_header(
                "Databases and Schemas"
            ) + "\n\n".join(result.resources)
            all_imports.extend(result.imports)

        # Imports file
        if all_imports:
            files["imports.tf"] = self._file_header(
                "Import Blocks for Existing Resources"
            ) + "\n\n".join(all_imports)

        return files

    def _file_header(self, title: str) -> str:
        return f'''# =============================================================================
# {title}
# Generated by SnowTower - https://github.com/Database-Tycoon/SnowTower
# =============================================================================

'''


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Generate Terraform configuration from SnowDDL YAML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run generate-terraform                      # Print to stdout
  uv run generate-terraform --output terraform/  # Write to directory
  uv run generate-terraform --config-dir ./snowddl --output tf/
        """,
    )

    parser.add_argument(
        "--config-dir",
        "-c",
        type=Path,
        default=Path.cwd() / "snowddl",
        help="Path to SnowDDL configuration directory (default: ./snowddl)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output directory for Terraform files (default: stdout)",
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["hcl", "json"],
        default="hcl",
        help="Output format (default: hcl)",
    )

    args = parser.parse_args()

    # Validate config directory
    if not args.config_dir.exists():
        print(f"Error: Config directory not found: {args.config_dir}", file=sys.stderr)
        sys.exit(1)

    # Generate Terraform
    generator = TerraformGenerator(args.config_dir)
    files = generator.generate_all()

    if args.output:
        # Write to directory
        args.output.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            filepath = args.output / filename
            with open(filepath, "w") as f:
                f.write(content)
            print(f"  Created {filepath}")
        print(f"\n Terraform files generated in {args.output}/")
        print("\nNext steps:")
        print("  1. cd " + str(args.output))
        print("  2. terraform init")
        print("  3. terraform plan  # Review the import plan")
        print("  4. terraform apply # Import existing resources")
    else:
        # Print to stdout
        for filename, content in files.items():
            print(f"\n{'='*80}")
            print(f"# FILE: {filename}")
            print("=" * 80)
            print(content)


if __name__ == "__main__":
    main()
