#!/usr/bin/env python3
"""
Investigate who created objects in PROJ_STRIPE.PROJ_STRIPE by querying Snowflake history.

This script will:
1. Check who currently owns each object
2. Query SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY to see who created them
3. Identify the root cause of why objects are owned by ACCOUNTADMIN
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
            "role": "ACCOUNTADMIN",  # Required for querying ACCOUNT_USAGE
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
    """Investigate object ownership and creation history."""
    print("🔍 INVESTIGATING OBJECT OWNERSHIP IN PROJ_STRIPE.PROJ_STRIPE\n")
    print("=" * 80)

    conn = get_snowflake_connection()
    if not conn:
        print("\n❌ Failed to connect to Snowflake")
        sys.exit(1)

    try:
        cursor = conn.cursor()

        # Step 1: Get current object ownership
        print("\n📊 STEP 1: Current Object Ownership")
        print("=" * 80)
        cursor.execute(
            """
            SELECT
                table_name,
                table_type,
                table_owner,
                created
            FROM PROJ_STRIPE.INFORMATION_SCHEMA.TABLES
            WHERE table_schema = 'PROJ_STRIPE'
              AND table_type IN ('BASE TABLE', 'VIEW')
            ORDER BY created DESC, table_name
            """
        )

        objects = cursor.fetchall()
        print(f"\nFound {len(objects)} objects:\n")
        for obj in objects:
            owner_flag = "❌ ACCOUNTADMIN" if obj[2] == "ACCOUNTADMIN" else f"✅ {obj[2]}"
            print(f"  {obj[1]:12} | {obj[0]:40} | {owner_flag} | Created: {obj[3]}")

        # Step 2: Check who created these objects (last 7 days)
        print("\n\n📜 STEP 2: Query History - Who Created These Objects?")
        print("=" * 80)

        # Get object names for query
        object_names = [obj[0] for obj in objects]

        for obj_name in object_names:
            print(f"\n🔎 Investigating: {obj_name}")
            print("-" * 80)

            cursor.execute(
                f"""
                SELECT
                    query_text,
                    user_name,
                    role_name,
                    start_time,
                    execution_status
                FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
                WHERE query_text ILIKE '%CREATE%{obj_name}%'
                  AND database_name = 'PROJ_STRIPE'
                  AND schema_name = 'PROJ_STRIPE'
                  AND start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
                ORDER BY start_time DESC
                LIMIT 5
                """
            )

            history = cursor.fetchall()
            if history:
                for row in history:
                    user = row[1]
                    role = row[2]
                    timestamp = row[3]
                    status = row[4]

                    role_flag = "❌" if role == "ACCOUNTADMIN" else "✅"
                    print(
                        f"  {role_flag} User: {user:20} | Role: {role:30} | {timestamp} | Status: {status}"
                    )
                    print(f"     Query: {row[0][:100]}...")
            else:
                print("  ⚠️  No recent CREATE queries found (may be older than 7 days)")

        # Step 3: Check schema ownership
        print("\n\n🗂️  STEP 3: Schema Ownership")
        print("=" * 80)
        cursor.execute(
            """
            SELECT
                catalog_name,
                schema_name,
                schema_owner,
                created
            FROM PROJ_STRIPE.INFORMATION_SCHEMA.SCHEMATA
            WHERE schema_name = 'PROJ_STRIPE'
            """
        )

        schema_info = cursor.fetchone()
        if schema_info:
            owner_flag = (
                "❌ WRONG OWNER"
                if schema_info[2] == "ACCOUNTADMIN"
                else "✅ CORRECT OWNER"
            )
            print(f"\nSchema: {schema_info[0]}.{schema_info[1]}")
            print(f"Owner: {schema_info[2]} {owner_flag}")
            print(f"Created: {schema_info[3]}")

        # Step 4: Check for FUTURE GRANTS
        print("\n\n🔮 STEP 4: Future Grants Configuration")
        print("=" * 80)
        cursor.execute(
            """
            SHOW FUTURE GRANTS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
            """
        )

        future_grants = cursor.fetchall()
        print(f"\nFound {len(future_grants)} future grant rules:\n")

        dbt_future_grants = [g for g in future_grants if "DBT_STRIPE_ROLE" in str(g)]

        if dbt_future_grants:
            print("✅ DBT Future Grants Found:")
            for grant in dbt_future_grants:
                print(f"   {grant}")
        else:
            print("❌ NO DBT FUTURE GRANTS CONFIGURED!")
            print("   This means new objects won't automatically be owned by dbt role")

        # Step 5: Summary and Root Cause
        print("\n\n" + "=" * 80)
        print("📋 ROOT CAUSE ANALYSIS")
        print("=" * 80)

        accountadmin_owned = sum(1 for obj in objects if obj[2] == "ACCOUNTADMIN")

        print(f"\n📊 Summary:")
        print(f"   - Total objects: {len(objects)}")
        print(f"   - Owned by ACCOUNTADMIN: {accountadmin_owned}")
        print(f"   - Owned by dbt role: {len(objects) - accountadmin_owned}")

        print(f"\n🔍 Root Cause:")
        if accountadmin_owned > 0:
            print("   ❌ Objects are owned by ACCOUNTADMIN because:")
            print(
                "      1. They were created by a user/process running with ACCOUNTADMIN role"
            )
            print("      2. This typically happens when:")
            print("         - dbt is configured to use ACCOUNTADMIN role (WRONG!)")
            print("         - Manual DDL was run with ACCOUNTADMIN")
            print("         - A script/process used ACCOUNTADMIN instead of dbt role")

        if not dbt_future_grants:
            print("\n   ❌ FUTURE GRANTS not configured:")
            print("      - New objects will continue to be owned by creator's role")
            print("      - This needs to be fixed to prevent recurring issues")

        print(f"\n💡 Recommendations:")
        print(
            "   1. Verify dbt profiles.yml uses role: DBT_ANALYTICS_ROLE__B_ROLE (or DBT_STRIPE_ROLE__T_ROLE)"
        )
        print("   2. Transfer ownership of existing objects to dbt role")
        print("   3. Set up FUTURE OWNERSHIP grants on the schema")
        print("   4. Never run dbt with ACCOUNTADMIN role!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
