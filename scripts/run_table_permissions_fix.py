#!/usr/bin/env python3
"""
Run the table permissions fix using Snowflake connector.

This script applies grants on all existing and future tables/views in PROJ_STRIPE.PROJ_STRIPE
to the DBT_STRIPE_ROLE__T_ROLE.
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
            "role": "ACCOUNTADMIN",  # Required for granting permissions
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
    """Apply table-level permissions for all tables/views in PROJ_STRIPE.PROJ_STRIPE."""
    print("🔐 Fixing table permissions in PROJ_STRIPE.PROJ_STRIPE...\n")

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

        # Grant on all existing tables
        print("🔧 Granting ALL privileges on ALL EXISTING tables...")
        cursor.execute(
            "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        print("✅ Existing tables granted\n")

        # Grant on all existing views
        print("🔧 Granting ALL privileges on ALL EXISTING views...")
        cursor.execute(
            "GRANT ALL PRIVILEGES ON ALL VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        print("✅ Existing views granted\n")

        # Set up future grants for tables
        print("🔧 Setting up FUTURE GRANTS for tables...")
        cursor.execute(
            "GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        print("✅ Future table grants configured\n")

        # Set up future grants for views
        print("🔧 Setting up FUTURE GRANTS for views...")
        cursor.execute(
            "GRANT ALL PRIVILEGES ON FUTURE VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        print("✅ Future view grants configured\n")

        # Verify by listing tables
        print("📊 Checking table ownership...")
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
        for row in rows:
            print(f"  {row[3]:12} | {row[2]:40} | Owner: {row[4]}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("🎉 Table permissions fixed successfully!")
        print("=" * 60)
        print("\n✅ DBT_STRIPE_ROLE__T_ROLE now has ALL privileges on:")
        print("   - All existing tables and views")
        print("   - All future tables and views")
        print("\n🚀 You can now run dbt seed/run without permission errors!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
