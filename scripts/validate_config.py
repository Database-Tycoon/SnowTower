#!/usr/bin/env python3
"""
SnowDDL YAML Configuration Validator.

Validates all SnowDDL YAML configuration files before deployment.
Performs syntax checking, field validation, and cross-reference integrity checks.

Usage:
    uv run validate-config                    # Validate all configs
    uv run validate-config --strict           # Fail on warnings too
    uv run validate-config --quiet            # Only show errors
    uv run validate-config snowddl/user.yaml  # Validate specific file(s)
"""

from dotenv import load_dotenv

load_dotenv()

import argparse
import ipaddress
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_WAREHOUSE_SIZES: Set[str] = {
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

# Also accept uppercased/alternative forms that Snowflake recognises
VALID_WAREHOUSE_SIZES_NORMALISED: Set[str] = {
    s.upper().replace("-", "") for s in VALID_WAREHOUSE_SIZES
}

VALID_GRANT_OBJECT_TYPES: Set[str] = {
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

SYSTEM_ROLES: Set[str] = {
    "ACCOUNTADMIN",
    "SYSADMIN",
    "USERADMIN",
    "SECURITYADMIN",
    "ORGADMIN",
    "PUBLIC",
}

VALID_USER_TYPES: Set[str] = {"PERSON", "SERVICE"}

# SnowDDL appends __B_ROLE to business role names
BUSINESS_ROLE_SUFFIX = "__B_ROLE"


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Accumulates errors and warnings across all checks."""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def ok(self, message: str) -> None:
        self.info.append(message)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------


def _find_project_root() -> Path:
    """Walk upwards from this script to find the project root (contains pyproject.toml)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback: assume scripts/ is one level below root
    return Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Load and parse a YAML file. Returns (data, error_message)."""
    if not path.exists():
        return None, f"File not found: {path}"
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return None, f"Expected a YAML mapping at top level, got {type(data).__name__}"
        return data, None
    except yaml.YAMLError as exc:
        return None, f"YAML syntax error: {exc}"


# ---------------------------------------------------------------------------
# Per-file validators
# ---------------------------------------------------------------------------


def validate_user_yaml(
    data: Dict[str, Any],
    result: ValidationResult,
    business_roles: Set[str],
) -> None:
    """Validate user.yaml entries."""
    names_seen: Set[str] = set()

    for user_name, user_cfg in data.items():
        if not isinstance(user_cfg, dict):
            result.error(f"User {user_name}: expected a mapping, got {type(user_cfg).__name__}")
            continue

        # Duplicate check
        upper_name = user_name.upper()
        if upper_name in names_seen:
            result.error(f"User {user_name}: duplicate user name")
        names_seen.add(upper_name)

        # Type field
        user_type = user_cfg.get("type")
        if user_type is None:
            result.error(f"User {user_name}: missing required 'type' field (PERSON or SERVICE)")
        elif str(user_type).upper() not in VALID_USER_TYPES:
            result.error(
                f"User {user_name}: invalid type '{user_type}' (must be PERSON or SERVICE)"
            )
        else:
            user_type = str(user_type).upper()

            # PERSON-specific checks
            if user_type == "PERSON":
                if "email" not in user_cfg:
                    result.warning(f"User {user_name}: PERSON user should have 'email' field")

            # SERVICE-specific checks
            if user_type == "SERVICE":
                rsa_key = user_cfg.get("rsa_public_key", "")
                if not rsa_key:
                    result.warning(
                        f"User {user_name}: SERVICE user should have 'rsa_public_key' field"
                    )
                elif "example" in str(rsa_key).lower() or "replace" in str(rsa_key).lower():
                    result.warning(f"User {user_name}: RSA key appears to be a placeholder")

        # default_role cross-reference (deferred to cross-ref if business_roles provided)
        default_role = user_cfg.get("default_role")
        if default_role and business_roles:
            role_upper = str(default_role).upper()
            # Accept system roles, raw business role names, and names with __B_ROLE suffix
            is_system = role_upper in SYSTEM_ROLES
            is_business_raw = role_upper in business_roles
            is_business_suffixed = role_upper.replace(BUSINESS_ROLE_SUFFIX, "") in business_roles
            if not (is_system or is_business_raw or is_business_suffixed):
                result.error(
                    f"User {user_name}: default_role '{default_role}' does not match any "
                    f"system role or business role in business_role.yaml"
                )

    count = len(data)
    result.ok(f"{count} user{'s' if count != 1 else ''} validated")


def validate_business_role_yaml(
    data: Dict[str, Any],
    result: ValidationResult,
    tech_roles: Set[str],
    warehouses: Set[str],
) -> None:
    """Validate business_role.yaml entries."""
    names_seen: Set[str] = set()

    for role_name, role_cfg in data.items():
        if not isinstance(role_cfg, dict):
            result.error(
                f"Business role {role_name}: expected a mapping, got {type(role_cfg).__name__}"
            )
            continue

        upper_name = role_name.upper()
        if upper_name in names_seen:
            result.error(f"Business role {role_name}: duplicate role name")
        names_seen.add(upper_name)

        # tech_roles references
        for tr in role_cfg.get("tech_roles", []):
            if tech_roles and str(tr).upper() not in tech_roles:
                result.error(
                    f"Business role {role_name}: tech_role '{tr}' not found in tech_role.yaml"
                )

        # warehouse_usage references
        for wh in role_cfg.get("warehouse_usage", []):
            if warehouses and str(wh).upper() not in warehouses:
                result.error(
                    f"Business role {role_name}: warehouse '{wh}' not found in warehouse.yaml"
                )

        # schema_owner format (DB.SCHEMA)
        for so in role_cfg.get("schema_owner", []):
            if not re.match(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$", str(so)):
                result.error(
                    f"Business role {role_name}: schema_owner '{so}' is not valid "
                    f"DB.SCHEMA format"
                )

    count = len(data)
    result.ok(f"{count} business role{'s' if count != 1 else ''} validated")


def validate_tech_role_yaml(
    data: Dict[str, Any],
    result: ValidationResult,
    warehouses: Set[str],
) -> None:
    """Validate tech_role.yaml entries."""
    names_seen: Set[str] = set()

    for role_name, role_cfg in data.items():
        if not isinstance(role_cfg, dict):
            result.error(
                f"Tech role {role_name}: expected a mapping, got {type(role_cfg).__name__}"
            )
            continue

        upper_name = role_name.upper()
        if upper_name in names_seen:
            result.error(f"Tech role {role_name}: duplicate role name")
        names_seen.add(upper_name)

        # Validate grant keys in both 'grants' and 'future_grants'
        for section_name in ("grants", "future_grants"):
            section = role_cfg.get(section_name, {})
            if not isinstance(section, dict):
                continue

            for grant_key, targets in section.items():
                # Grant key format: OBJECT_TYPE:PRIVILEGE(S)
                parts = str(grant_key).split(":", 1)
                if len(parts) != 2 or not parts[1]:
                    result.error(
                        f"Tech role {role_name}: grant key '{grant_key}' in {section_name} "
                        f"must follow OBJECT_TYPE:PRIVILEGE format"
                    )
                    continue

                obj_type = parts[0].upper()
                if obj_type not in VALID_GRANT_OBJECT_TYPES:
                    result.error(
                        f"Tech role {role_name}: invalid object type '{parts[0]}' in "
                        f"grant key '{grant_key}' (valid: {', '.join(sorted(VALID_GRANT_OBJECT_TYPES))})"
                    )

                # WAREHOUSE:USAGE cross-reference
                if obj_type == "WAREHOUSE" and warehouses and isinstance(targets, list):
                    for wh in targets:
                        if str(wh).upper() not in warehouses:
                            result.error(
                                f"Tech role {role_name}: warehouse '{wh}' in "
                                f"{section_name} not found in warehouse.yaml"
                            )

    count = len(data)
    result.ok(f"{count} technical role{'s' if count != 1 else ''} validated")


def validate_warehouse_yaml(
    data: Dict[str, Any],
    result: ValidationResult,
    resource_monitors: Set[str],
) -> None:
    """Validate warehouse.yaml entries."""
    names_seen: Set[str] = set()

    for wh_name, wh_cfg in data.items():
        if not isinstance(wh_cfg, dict):
            result.error(
                f"Warehouse {wh_name}: expected a mapping, got {type(wh_cfg).__name__}"
            )
            continue

        upper_name = wh_name.upper()
        if upper_name in names_seen:
            result.error(f"Warehouse {wh_name}: duplicate warehouse name")
        names_seen.add(upper_name)

        # Size validation
        size = wh_cfg.get("size")
        if size is not None:
            normalised = str(size).upper().replace("-", "")
            if normalised not in VALID_WAREHOUSE_SIZES_NORMALISED:
                result.error(
                    f"Warehouse {wh_name}: invalid size '{size}' "
                    f"(valid: {', '.join(sorted(VALID_WAREHOUSE_SIZES))})"
                )

        # auto_suspend validation
        auto_suspend = wh_cfg.get("auto_suspend")
        if auto_suspend is not None:
            try:
                val = int(auto_suspend)
                if val < 0:
                    result.error(
                        f"Warehouse {wh_name}: auto_suspend must be a positive integer, got {val}"
                    )
            except (ValueError, TypeError):
                result.error(
                    f"Warehouse {wh_name}: auto_suspend must be an integer, got '{auto_suspend}'"
                )

        # resource_monitor cross-reference
        monitor = wh_cfg.get("resource_monitor")
        if monitor and resource_monitors:
            if str(monitor).upper() not in resource_monitors:
                result.error(
                    f"Warehouse {wh_name}: resource_monitor '{monitor}' "
                    f"not found in resource_monitor.yaml"
                )

    count = len(data)
    result.ok(f"{count} warehouse{'s' if count != 1 else ''} validated")


def validate_network_policy_yaml(
    data: Dict[str, Any],
    result: ValidationResult,
) -> None:
    """Validate network_policy.yaml entries."""
    names_seen: Set[str] = set()

    for policy_name, policy_cfg in data.items():
        if not isinstance(policy_cfg, dict):
            result.error(
                f"Network policy {policy_name}: expected a mapping, got {type(policy_cfg).__name__}"
            )
            continue

        upper_name = policy_name.upper()
        if upper_name in names_seen:
            result.error(f"Network policy {policy_name}: duplicate policy name")
        names_seen.add(upper_name)

        # Validate CIDR entries in allowed_ip_list
        for ip_entry in policy_cfg.get("allowed_ip_list", []):
            try:
                ipaddress.ip_network(str(ip_entry), strict=False)
            except ValueError:
                result.error(
                    f"Network policy {policy_name}: '{ip_entry}' is not valid CIDR notation"
                )

        # Also check blocked_ip_list if present
        for ip_entry in policy_cfg.get("blocked_ip_list", []):
            try:
                ipaddress.ip_network(str(ip_entry), strict=False)
            except ValueError:
                result.error(
                    f"Network policy {policy_name}: blocked IP '{ip_entry}' is not valid CIDR notation"
                )

    count = len(data)
    result.ok(f"{count} network polic{'ies' if count != 1 else 'y'} validated")


def validate_resource_monitor_yaml(
    data: Dict[str, Any],
    result: ValidationResult,
) -> None:
    """Validate resource_monitor.yaml entries (basic structure check)."""
    for monitor_name, monitor_cfg in data.items():
        if not isinstance(monitor_cfg, dict):
            result.error(
                f"Resource monitor {monitor_name}: expected a mapping, got {type(monitor_cfg).__name__}"
            )
            continue

        credit_quota = monitor_cfg.get("credit_quota")
        if credit_quota is not None:
            try:
                val = int(credit_quota)
                if val <= 0:
                    result.error(
                        f"Resource monitor {monitor_name}: credit_quota must be positive, got {val}"
                    )
            except (ValueError, TypeError):
                result.error(
                    f"Resource monitor {monitor_name}: credit_quota must be an integer"
                )

    count = len(data)
    result.ok(f"{count} resource monitor{'s' if count != 1 else ''} validated")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

# ANSI colour helpers for terminal output
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


def _print_file_results(
    filename: str,
    file_result: ValidationResult,
    quiet: bool,
) -> None:
    """Print validation results for a single file."""
    has_output = False

    if not quiet:
        print(f"\n{_BOLD}{filename}{_RESET}")
        has_output = True

    # Print info (success messages)
    if not quiet:
        for msg in file_result.info:
            print(f"  {_GREEN}\u2713{_RESET} {msg}")

    # Print warnings
    if not quiet:
        for msg in file_result.warnings:
            print(f"  {_YELLOW}\u26a0 WARNING:{_RESET} {msg}")

    # Print errors (always shown)
    for msg in file_result.errors:
        if not has_output:
            print(f"\n{_BOLD}{filename}{_RESET}")
            has_output = True
        print(f"  {_RED}\u2717 ERROR:{_RESET} {msg}")


# ---------------------------------------------------------------------------
# Main validation orchestrator
# ---------------------------------------------------------------------------


def run_validation(config_dir: Path, target_files: Optional[List[str]], strict: bool, quiet: bool) -> int:
    """
    Run all validation checks and return exit code.

    Returns:
        0 on success (or warnings-only without --strict)
        1 on errors (or warnings with --strict)
    """
    if not config_dir.is_dir():
        print(f"{_RED}Error:{_RESET} Config directory not found: {config_dir}")
        return 1

    if not quiet:
        print(f"Validating {config_dir}/ configuration...")

    # -----------------------------------------------------------------------
    # 1. Load all YAML files (needed for cross-references even if targeting specific files)
    # -----------------------------------------------------------------------

    yaml_files = {
        "user.yaml": config_dir / "user.yaml",
        "business_role.yaml": config_dir / "business_role.yaml",
        "tech_role.yaml": config_dir / "tech_role.yaml",
        "warehouse.yaml": config_dir / "warehouse.yaml",
        "network_policy.yaml": config_dir / "network_policy.yaml",
        "resource_monitor.yaml": config_dir / "resource_monitor.yaml",
    }

    loaded: Dict[str, Dict[str, Any]] = {}
    syntax_result = ValidationResult()

    for name, path in yaml_files.items():
        if not path.exists():
            # Not every project will have all files; skip missing ones silently
            loaded[name] = {}
            continue
        data, err = _load_yaml(path)
        if err:
            syntax_result.error(f"{name}: {err}")
            loaded[name] = {}
        else:
            loaded[name] = data  # type: ignore[assignment]

    # Print syntax errors first
    if syntax_result.has_errors:
        _print_file_results("YAML Syntax", syntax_result, quiet)

    # -----------------------------------------------------------------------
    # 2. Build cross-reference sets
    # -----------------------------------------------------------------------

    business_roles: Set[str] = {k.upper() for k in loaded.get("business_role.yaml", {})}
    tech_roles: Set[str] = {k.upper() for k in loaded.get("tech_role.yaml", {})}
    warehouses: Set[str] = {k.upper() for k in loaded.get("warehouse.yaml", {})}
    resource_monitors: Set[str] = {k.upper() for k in loaded.get("resource_monitor.yaml", {})}

    # -----------------------------------------------------------------------
    # 3. Determine which files to validate
    # -----------------------------------------------------------------------

    if target_files:
        # Resolve target files to their canonical names
        files_to_validate: Set[str] = set()
        for tf in target_files:
            tf_path = Path(tf)
            basename = tf_path.name
            if basename in yaml_files:
                files_to_validate.add(basename)
            else:
                # Try to match by stem
                for known_name in yaml_files:
                    if known_name.startswith(tf_path.stem):
                        files_to_validate.add(known_name)
                        break
                else:
                    print(f"{_YELLOW}\u26a0 WARNING:{_RESET} Unknown config file: {tf} (skipping)")
    else:
        files_to_validate = set(yaml_files.keys())

    # -----------------------------------------------------------------------
    # 4. Run per-file validators
    # -----------------------------------------------------------------------

    all_results: List[Tuple[str, ValidationResult]] = []

    validators = {
        "user.yaml": lambda r: validate_user_yaml(loaded["user.yaml"], r, business_roles),
        "business_role.yaml": lambda r: validate_business_role_yaml(
            loaded["business_role.yaml"], r, tech_roles, warehouses
        ),
        "tech_role.yaml": lambda r: validate_tech_role_yaml(
            loaded["tech_role.yaml"], r, warehouses
        ),
        "warehouse.yaml": lambda r: validate_warehouse_yaml(
            loaded["warehouse.yaml"], r, resource_monitors
        ),
        "network_policy.yaml": lambda r: validate_network_policy_yaml(
            loaded["network_policy.yaml"], r
        ),
        "resource_monitor.yaml": lambda r: validate_resource_monitor_yaml(
            loaded["resource_monitor.yaml"], r
        ),
    }

    for filename in sorted(files_to_validate):
        if filename not in validators:
            continue
        if not loaded.get(filename):
            continue

        file_result = ValidationResult()
        validators[filename](file_result)
        all_results.append((filename, file_result))
        _print_file_results(filename, file_result, quiet)

    # -----------------------------------------------------------------------
    # 5. Cross-reference validation (only when validating all files)
    # -----------------------------------------------------------------------

    if not target_files:
        xref_result = ValidationResult()
        _cross_reference_checks(loaded, xref_result, business_roles, tech_roles, warehouses, resource_monitors)
        if xref_result.errors or xref_result.warnings or xref_result.info:
            if not quiet or xref_result.errors:
                print(f"\n{_BOLD}Cross-reference checks:{_RESET}")
                for msg in xref_result.info:
                    if not quiet:
                        print(f"  {_GREEN}\u2713{_RESET} {msg}")
                for msg in xref_result.warnings:
                    if not quiet:
                        print(f"  {_YELLOW}\u26a0 WARNING:{_RESET} {msg}")
                for msg in xref_result.errors:
                    print(f"  {_RED}\u2717 ERROR:{_RESET} {msg}")
            all_results.append(("cross-references", xref_result))

    # -----------------------------------------------------------------------
    # 6. Summary
    # -----------------------------------------------------------------------

    total_errors = syntax_result.errors[:]
    total_warnings = syntax_result.warnings[:]
    for _, fr in all_results:
        total_errors.extend(fr.errors)
        total_warnings.extend(fr.warnings)

    error_count = len(total_errors)
    warning_count = len(total_warnings)

    print(f"\n{_BOLD}Summary:{_RESET} ", end="")
    parts = []
    if error_count:
        parts.append(f"{_RED}{error_count} error{'s' if error_count != 1 else ''}{_RESET}")
    if warning_count:
        parts.append(f"{_YELLOW}{warning_count} warning{'s' if warning_count != 1 else ''}{_RESET}")
    if not parts:
        parts.append(f"{_GREEN}All checks passed{_RESET}")
    print(", ".join(parts))

    # Exit code
    if error_count > 0:
        return 1
    if warning_count > 0 and strict:
        return 1
    return 0


def _cross_reference_checks(
    loaded: Dict[str, Dict[str, Any]],
    result: ValidationResult,
    business_roles: Set[str],
    tech_roles: Set[str],
    warehouses: Set[str],
    resource_monitors: Set[str],
) -> None:
    """Run cross-file reference integrity checks."""

    # 1. Users' default_role -> valid roles
    users = loaded.get("user.yaml", {})
    bad_default_roles = []
    for user_name, user_cfg in users.items():
        if not isinstance(user_cfg, dict):
            continue
        default_role = user_cfg.get("default_role")
        if not default_role:
            continue
        role_upper = str(default_role).upper()
        is_system = role_upper in SYSTEM_ROLES
        is_business_raw = role_upper in business_roles
        is_business_suffixed = role_upper.replace(BUSINESS_ROLE_SUFFIX, "") in business_roles
        if not (is_system or is_business_raw or is_business_suffixed):
            bad_default_roles.append((user_name, default_role))

    if bad_default_roles:
        for user_name, role in bad_default_roles:
            result.error(f"User {user_name}: default_role '{role}' not defined as a business or system role")
    else:
        result.ok("All user default_roles reference valid roles")

    # 2. Business roles' tech_roles -> valid tech roles
    br_data = loaded.get("business_role.yaml", {})
    bad_tech_refs = []
    for role_name, role_cfg in br_data.items():
        if not isinstance(role_cfg, dict):
            continue
        for tr in role_cfg.get("tech_roles", []):
            if str(tr).upper() not in tech_roles:
                bad_tech_refs.append((role_name, tr))

    if bad_tech_refs:
        for role_name, tr in bad_tech_refs:
            result.error(f"Business role {role_name}: tech_role '{tr}' not defined in tech_role.yaml")
    else:
        result.ok("All business role tech_roles exist")

    # 3. Business roles' warehouse_usage -> valid warehouses
    bad_wh_refs = []
    for role_name, role_cfg in br_data.items():
        if not isinstance(role_cfg, dict):
            continue
        for wh in role_cfg.get("warehouse_usage", []):
            if str(wh).upper() not in warehouses:
                bad_wh_refs.append((role_name, wh))

    if bad_wh_refs:
        for role_name, wh in bad_wh_refs:
            result.error(f"Business role {role_name}: warehouse '{wh}' not defined in warehouse.yaml")
    else:
        result.ok("All business role warehouse_usage references exist")

    # 4. Warehouses' resource_monitor -> valid monitors
    wh_data = loaded.get("warehouse.yaml", {})
    bad_monitor_refs = []
    for wh_name, wh_cfg in wh_data.items():
        if not isinstance(wh_cfg, dict):
            continue
        monitor = wh_cfg.get("resource_monitor")
        if monitor and str(monitor).upper() not in resource_monitors:
            bad_monitor_refs.append((wh_name, monitor))

    if bad_monitor_refs:
        for wh_name, monitor in bad_monitor_refs:
            result.error(f"Warehouse {wh_name}: resource_monitor '{monitor}' not defined in resource_monitor.yaml")
    else:
        result.ok("All warehouse resource_monitors reference valid monitors")

    # 5. Tech roles' WAREHOUSE:USAGE -> valid warehouses
    tr_data = loaded.get("tech_role.yaml", {})
    bad_wh_grants = []
    for role_name, role_cfg in tr_data.items():
        if not isinstance(role_cfg, dict):
            continue
        for section_name in ("grants", "future_grants"):
            section = role_cfg.get(section_name, {})
            if not isinstance(section, dict):
                continue
            for grant_key, targets in section.items():
                parts = str(grant_key).split(":", 1)
                if len(parts) == 2 and parts[0].upper() == "WAREHOUSE" and isinstance(targets, list):
                    for wh in targets:
                        if str(wh).upper() not in warehouses:
                            bad_wh_grants.append((role_name, wh))

    if bad_wh_grants:
        for role_name, wh in bad_wh_grants:
            result.error(f"Tech role {role_name}: warehouse '{wh}' in grants not defined in warehouse.yaml")
    else:
        result.ok("All tech role warehouse grants reference valid warehouses")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the validate-config command."""
    parser = argparse.ArgumentParser(
        description="Validate SnowDDL YAML configuration files before deployment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run validate-config                        # Validate all configs\n"
            "  uv run validate-config --strict               # Fail on warnings too\n"
            "  uv run validate-config --quiet                # Only show errors\n"
            "  uv run validate-config snowddl/user.yaml      # Validate specific file\n"
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Optional file path(s) to validate (default: all configs in snowddl/)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit code 1 for warnings)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show errors, suppress informational and warning output",
    )
    parser.add_argument(
        "--config-dir",
        type=str,
        default=None,
        help="Path to the snowddl config directory (auto-detected by default)",
    )

    args = parser.parse_args()

    # Determine config directory
    if args.config_dir:
        config_dir = Path(args.config_dir)
    else:
        project_root = _find_project_root()
        config_dir = project_root / "snowddl"

    target_files = args.files if args.files else None

    exit_code = run_validation(config_dir, target_files, args.strict, args.quiet)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
