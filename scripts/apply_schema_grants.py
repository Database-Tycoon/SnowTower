#!/usr/bin/env python3
"""
Apply schema-level USAGE grants that SnowDDL cannot manage.

SnowDDL excludes SCHEMA objects from management, which means schema-level
USAGE grants must be applied separately. This script ensures the correct
roles have USAGE permissions on schemas.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Snowflake connector imports
try:
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    print("❌ snowflake-connector-python not installed")
    print("   Install with: uv pip install snowflake-connector-python")
    sys.exit(1)

# Schema grants configuration
# Format: "DATABASE.SCHEMA": {"privilege_set": ["ROLE1", "ROLE2"]}
# privilege_set can be: "USAGE", "ALL" (includes CREATE TABLE, CREATE VIEW, etc.)

SCHEMA_GRANTS = {
    "SOURCE_STRIPE.STRIPE_WHY": {
        "USAGE": [
            # Business Roles (via tech roles)
            "COMPANY_USERS__B_ROLE",  # Engineers need access to view source data
            # Technical Roles with SOURCE_STRIPE READ access
            "STRIPE__T_ROLE",  # Stripe data access role
            "DLT_LOADER_ROLE__T_ROLE",  # DLT data loading operations
            "FIVETRAN_ROLE__T_ROLE",  # Fivetran integration service
            "MATILLION_ROLE__T_ROLE",  # Matillion ETL processing
            "STREAMLIT_TOWERAPP_ROLE__T_ROLE",  # SnowTower Streamlit apps
            "BI_WRITER_TECH_ROLE__T_ROLE",  # BI developers reading source data
            "LIGHTDASH_TECH_ROLE__T_ROLE",  # LightDash BI platform
        ],
        "ALL": [
            # Roles that need WRITE access (CREATE TABLE, CREATE VIEW, etc.)
            "DBT_STRIPE_ROLE__T_ROLE",  # dbt needs to create objects for transformations
            "DLT_STRIPE_TECH_ROLE__T_ROLE",  # DLT Stripe pipeline (owner of schema)
        ],
    },
    "PROJ_STRIPE.PROJ_STRIPE": {
        "ALL": [
            # dbt needs full write access to create transformed models
            "DBT_STRIPE_ROLE__T_ROLE",  # dbt Stripe transformations
            "DBT_ANALYTICS_ROLE__B_ROLE",  # dbt Analytics business role (inherits DBT_STRIPE_ROLE__T_ROLE)
        ],
    },
    "DEV_ALICE.STRIPE_WHY": {
        "ALL": [
            "COMPANY_USERS__B_ROLE",  # Engineers have full access to dev databases
        ],
    },
}


def get_snowflake_connection():
    """Get Snowflake connection using environment variables or RSA key."""
    try:
        conn_params = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "ADMIN"),
        }

        # Check for SNOWFLAKE_PRIVATE_KEY (base64 encoded from GitHub secrets)
        private_key_env = os.getenv("SNOWFLAKE_PRIVATE_KEY")
        private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")

        if private_key_env:
            # CI/CD environment with base64-encoded key
            import base64

            private_key_bytes = base64.b64decode(private_key_env)
            private_key = serialization.load_pem_private_key(
                private_key_bytes, password=None, backend=default_backend()
            )

            private_key_der = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            conn_params["private_key"] = private_key_der
        elif private_key_path and Path(private_key_path).exists():
            # Local environment with key file
            with open(private_key_path, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(), password=None, backend=default_backend()
                )

            private_key_der = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            conn_params["private_key"] = private_key_der
        else:
            # Fall back to password
            password = os.getenv("SNOWFLAKE_PASSWORD")
            if password:
                conn_params["password"] = password
            else:
                print("❌ No authentication method available")
                print("   Set SNOWFLAKE_PRIVATE_KEY or SNOWFLAKE_PASSWORD")
                return None

        return snowflake.connector.connect(**conn_params)
    except Exception as e:
        print(f"❌ Failed to connect to Snowflake: {e}")
        return None


def apply_grant(conn, schema, role, privilege_set="USAGE"):
    """Apply grants on schema to role.

    Args:
        conn: Snowflake connection
        schema: Schema in format DATABASE.SCHEMA
        role: Role name
        privilege_set: Either "USAGE" or "ALL" (includes CREATE TABLE, CREATE VIEW, etc.)
    """
    print(f"  Granting {privilege_set} on {schema} to {role}...")

    try:
        cursor = conn.cursor()
        cursor.execute(f"GRANT {privilege_set} ON SCHEMA {schema} TO ROLE {role};")
        cursor.close()
        print(f"    ✅ Success")
        return True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        return False


def main():
    """Apply all schema grants."""
    print("🔐 Applying schema-level USAGE grants...")
    print("Note: These grants cannot be managed by SnowDDL due to SCHEMA exclusion\n")

    # Connect to Snowflake
    conn = get_snowflake_connection()
    if not conn:
        print("\n❌ Failed to connect to Snowflake")
        sys.exit(1)

    success_count = 0
    fail_count = 0

    try:
        for schema, privilege_dict in SCHEMA_GRANTS.items():
            print(f"\n📂 Schema: {schema}")

            # Handle both old format (list) and new format (dict with privilege sets)
            if isinstance(privilege_dict, list):
                # Old format: just USAGE grants
                for role in privilege_dict:
                    if apply_grant(conn, schema, role, "USAGE"):
                        success_count += 1
                    else:
                        fail_count += 1
            else:
                # New format: dict with privilege sets
                for privilege_set, roles in privilege_dict.items():
                    print(f"  Privilege Set: {privilege_set}")
                    for role in roles:
                        if apply_grant(conn, schema, role, privilege_set):
                            success_count += 1
                        else:
                            fail_count += 1
    finally:
        conn.close()

    print(f"\n{'='*60}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")

    if fail_count > 0:
        print("\n⚠️  Some grants failed. Please review errors above.")
        sys.exit(1)
    else:
        print("\n🎉 All schema grants applied successfully!")
        print("\nNote: Run this script after any SnowDDL deployment that includes")
        print(
            "      new schemas or if you see 'REVOKE USAGE ON SCHEMA' in plan output."
        )


if __name__ == "__main__":
    main()
