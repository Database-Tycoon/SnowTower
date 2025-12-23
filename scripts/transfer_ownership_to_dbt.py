#!/usr/bin/env python3
"""
Transfer ownership of all tables and views in PROJ_STRIPE.PROJ_STRIPE to DBT_STRIPE_ROLE__T_ROLE.

This is necessary because dbt needs to OWN objects to fully manage them (replace views, drop/recreate, etc.).
Granting privileges alone is not enough.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("❌ snowflake-connector-python not installed")
    print("   Install with: uv pip install snowflake-connector-python")
    sys.exit(1)


def get_snowflake_connection():
    """Get Snowflake connection using environment variables or RSA key."""
    try:
        conn_params = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "role": "ACCOUNTADMIN",  # Required for transferring ownership
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "ADMIN"),
        }

        # Check for SNOWFLAKE_PRIVATE_KEY (base64 encoded from GitHub secrets)
        private_key_env = os.getenv("SNOWFLAKE_PRIVATE_KEY")
        private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")

        if private_key_env:
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


def main():
    """Transfer ownership of all objects in PROJ_STRIPE.PROJ_STRIPE to dbt role."""
    print("🔐 Transferring ownership of all objects to DBT_STRIPE_ROLE__T_ROLE...\n")

    conn = get_snowflake_connection()
    if not conn:
        print("\n❌ Failed to connect to Snowflake")
        sys.exit(1)

    try:
        cursor = conn.cursor()

        # Set context
        print("📍 Setting context...")
        cursor.execute("USE ROLE ACCOUNTADMIN")
        cursor.execute("USE DATABASE PROJ_STRIPE")
        cursor.execute("USE SCHEMA PROJ_STRIPE")
        print("✅ Context set to ACCOUNTADMIN, PROJ_STRIPE.PROJ_STRIPE\n")

        # Transfer ownership of ALL tables
        print("🔧 Transferring ownership of ALL TABLES...")
        cursor.execute(
            "GRANT OWNERSHIP ON ALL TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE COPY CURRENT GRANTS"
        )
        print("✅ Table ownership transferred\n")

        # Transfer ownership of ALL views
        print("🔧 Transferring ownership of ALL VIEWS...")
        cursor.execute(
            "GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE COPY CURRENT GRANTS"
        )
        print("✅ View ownership transferred\n")

        # Set up future ownership for tables
        print("🔧 Setting up FUTURE OWNERSHIP for tables...")
        cursor.execute(
            "GRANT OWNERSHIP ON FUTURE TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        print("✅ Future table ownership configured\n")

        # Set up future ownership for views
        print("🔧 Setting up FUTURE OWNERSHIP for views...")
        cursor.execute(
            "GRANT OWNERSHIP ON FUTURE VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        print("✅ Future view ownership configured\n")

        # Verify by listing objects
        print("📊 Checking object ownership...")
        cursor.execute(
            """
            SELECT
                table_catalog,
                table_schema,
                table_name,
                table_type,
                table_owner
            FROM PROJ_STRIPE.INFORMATION_SCHEMA.TABLES
            WHERE table_schema = 'PROJ_STRIPE'
              AND table_type IN ('BASE TABLE', 'VIEW')
            ORDER BY table_type, table_name
            """
        )

        rows = cursor.fetchall()
        print(f"\nFound {len(rows)} tables/views in PROJ_STRIPE.PROJ_STRIPE:\n")
        dbt_owned = 0
        for row in rows:
            owner_display = "✅ DBT" if "DBT" in row[4] else f"❌ {row[4]}"
            if "DBT" in row[4]:
                dbt_owned += 1
            print(f"  {row[3]:12} | {row[2]:40} | {owner_display}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("🎉 Ownership transfer completed successfully!")
        print("=" * 60)
        print(
            f"\n✅ {dbt_owned}/{len(rows)} objects now owned by DBT_STRIPE_ROLE__T_ROLE"
        )
        print("\n🚀 dbt can now fully manage all tables and views!")
        print("   - Create/replace views")
        print("   - Drop/recreate tables")
        print("   - Full DDL operations")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
