#!/usr/bin/env python3
"""
Validate that all roles with DATABASE:USAGE on SOURCE_STRIPE also have
corresponding SCHEMA:USAGE grants in apply_schema_grants.py.

This script prevents the ACCESS_LOSS incident from recurring by ensuring
role configurations are consistent between SnowDDL YAML and schema grants script.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the schema grants configuration
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from apply_schema_grants import SCHEMA_GRANTS


def extract_roles_with_database_usage(tech_role_yaml: Path) -> Set[str]:
    """
    Extract all role names that have DATABASE:USAGE grants on SOURCE_STRIPE.

    SnowDDL automatically appends __T_ROLE suffix to technical role names,
    so we need to add this suffix to match the actual Snowflake role names.

    Returns:
        Set of role names with __T_ROLE suffix that should have schema access
    """
    with open(tech_role_yaml, "r") as f:
        config = yaml.safe_load(f)

    roles_with_source_stripe = set()

    for role_name, role_config in config.items():
        if not isinstance(role_config, dict):
            continue

        grants = role_config.get("grants", {})
        db_usage_grants = []

        # DATABASE:USAGE can be standalone or combined (e.g., DATABASE:USAGE,CREATE SCHEMA)
        for grant_type, grant_values in grants.items():
            if "DATABASE:USAGE" in grant_type:
                db_usage_grants.extend(
                    grant_values if isinstance(grant_values, list) else [grant_values]
                )

        # Check if this role has SOURCE_STRIPE database access
        if "SOURCE_STRIPE" in db_usage_grants:
            # SnowDDL appends __T_ROLE suffix to technical role names
            full_role_name = f"{role_name}__T_ROLE"
            roles_with_source_stripe.add(full_role_name)

    return roles_with_source_stripe


def extract_roles_with_schema_grants(
    schema: str = "SOURCE_STRIPE.STRIPE_WHY",
) -> Set[str]:
    """
    Extract roles that have SCHEMA:USAGE grants configured in apply_schema_grants.py.

    Args:
        schema: The schema to check (default: SOURCE_STRIPE.STRIPE_WHY)

    Returns:
        Set of role names with schema grants (from both USAGE and ALL privilege sets)
    """
    schema_config = SCHEMA_GRANTS.get(schema, {})

    # Handle both old format (list) and new format (dict with privilege sets)
    if isinstance(schema_config, list):
        # Old format: simple list of roles
        return set(schema_config)
    elif isinstance(schema_config, dict):
        # New format: dict with privilege sets (USAGE, ALL, etc.)
        all_roles = set()
        for privilege_set, roles in schema_config.items():
            all_roles.update(roles)
        return all_roles
    else:
        return set()


def validate_consistency() -> bool:
    """
    Validate that roles with DATABASE:USAGE also have SCHEMA:USAGE grants.

    Returns:
        True if validation passes, False otherwise
    """
    print("🔍 Validating schema grants consistency...\n")

    # Find tech_role.yaml
    tech_role_yaml = Path("snowddl/tech_role.yaml")
    if not tech_role_yaml.exists():
        print(f"❌ ERROR: {tech_role_yaml} not found")
        return False

    # Extract roles from both sources
    roles_with_db_access = extract_roles_with_database_usage(tech_role_yaml)
    roles_with_schema_grants = extract_roles_with_schema_grants()

    print(f"📊 Roles with DATABASE:USAGE on SOURCE_STRIPE: {len(roles_with_db_access)}")
    for role in sorted(roles_with_db_access):
        print(f"   - {role}")

    print(
        f"\n📊 Roles with SCHEMA:USAGE on SOURCE_STRIPE.STRIPE_WHY: {len(roles_with_schema_grants)}"
    )
    for role in sorted(roles_with_schema_grants):
        print(f"   - {role}")

    # Find discrepancies
    missing_schema_grants = roles_with_db_access - roles_with_schema_grants
    extra_schema_grants = roles_with_schema_grants - roles_with_db_access

    has_errors = False

    if missing_schema_grants:
        print("\n❌ CRITICAL: Roles with DATABASE access but MISSING schema grants:")
        print(
            "   These roles can see SOURCE_STRIPE but cannot access STRIPE_WHY schema!"
        )
        for role in sorted(missing_schema_grants):
            print(f"   - {role}")
        print(
            "\n   🔧 Fix: Add these roles to SCHEMA_GRANTS in scripts/apply_schema_grants.py"
        )
        has_errors = True

    if extra_schema_grants:
        print("\n⚠️  WARNING: Roles with schema grants but NO DATABASE access:")
        print(
            "   These grants may be unnecessary or business roles that inherit access."
        )
        for role in sorted(extra_schema_grants):
            print(f"   - {role}")
        print("\n   Note: Business roles (ending with __B_ROLE) are expected here.")

    if not has_errors:
        print(
            "\n✅ Validation PASSED: All roles with database access have schema grants!"
        )
        print("   No action required.")
        return True
    else:
        print("\n❌ Validation FAILED: Schema grant configuration is incomplete!")
        print("   This will cause users to lose access after SnowDDL deployment.")
        return False


def main():
    """Main entry point."""
    print("=" * 70)
    print("Schema Grants Validation")
    print("=" * 70)
    print()

    success = validate_consistency()

    print()
    print("=" * 70)

    if not success:
        print("🚨 ACTION REQUIRED: Update scripts/apply_schema_grants.py")
        print("   See: docs/INCIDENT_STRIPE_WHY_ACCESS_LOSS.md")
        sys.exit(1)
    else:
        print("✅ All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
