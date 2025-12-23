#!/usr/bin/env python3
"""
Apply dbt read access fix to SOURCE_STRIPE database
Grants read-only access (USAGE + SELECT) to DBT_STRIPE_ROLE__T_ROLE
"""
from dotenv import load_dotenv

load_dotenv()

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def get_snowflake_connection():
    """Get Snowflake connection using ACCOUNTADMIN role"""
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    role = "ACCOUNTADMIN"

    # Try private key first
    private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    if private_key_path and Path(private_key_path).exists():
        with open(private_key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend()
            )

            pkb = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "MAIN_WAREHOUSE")
            return snowflake.connector.connect(
                account=account,
                user=user,
                private_key=pkb,
                role=role,
                warehouse=warehouse,
            )

    # Fallback to password
    password = os.getenv("SNOWFLAKE_PASSWORD")
    if password:
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "MAIN_WAREHOUSE")
        return snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            role=role,
            warehouse=warehouse,
        )

    raise Exception("No authentication method available")


def execute_sql(cursor, sql, description=""):
    """Execute SQL and print results"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"SQL: {sql}\n")

    try:
        cursor.execute(sql)
        result = cursor.fetchall()

        if result:
            print(f"✅ Success - {len(result)} rows affected")
            for row in result[:5]:  # Show first 5 rows
                print(f"   {row}")
            if len(result) > 5:
                print(f"   ... and {len(result) - 5} more")
        else:
            print(f"✅ Success - Statement executed successfully")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print(f"\n{'='*80}")
    print(f"Apply dbt Read Access Fix to SOURCE_STRIPE")
    print(f"{'='*80}\n")

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        # Step 1: Database-level access
        print("\n📋 STEP 1: Database-Level Access")
        execute_sql(
            cursor,
            "GRANT USAGE ON DATABASE SOURCE_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant USAGE on SOURCE_STRIPE database",
        )

        # Step 2: Schema-level access for STRIPE_WHY
        print("\n📋 STEP 2: Schema-Level Access (STRIPE_WHY)")
        execute_sql(
            cursor,
            "GRANT USAGE ON SCHEMA SOURCE_STRIPE.STRIPE_WHY TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant USAGE on STRIPE_WHY schema",
        )

        # Step 3: SELECT on existing objects
        print("\n📋 STEP 3: SELECT on Existing Objects")
        execute_sql(
            cursor,
            "GRANT SELECT ON ALL TABLES IN SCHEMA SOURCE_STRIPE.STRIPE_WHY TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant SELECT on all existing tables",
        )

        execute_sql(
            cursor,
            "GRANT SELECT ON ALL VIEWS IN SCHEMA SOURCE_STRIPE.STRIPE_WHY TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant SELECT on all existing views",
        )

        # Step 4: Future grants for STRIPE_WHY schema
        print("\n📋 STEP 4: Future Grants (Schema-Level)")
        execute_sql(
            cursor,
            "GRANT SELECT ON FUTURE TABLES IN SCHEMA SOURCE_STRIPE.STRIPE_WHY TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant SELECT on future tables in STRIPE_WHY",
        )

        execute_sql(
            cursor,
            "GRANT SELECT ON FUTURE VIEWS IN SCHEMA SOURCE_STRIPE.STRIPE_WHY TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant SELECT on future views in STRIPE_WHY",
        )

        # Step 5: Database-level future grants (for new schemas)
        print("\n📋 STEP 5: Database-Level Future Grants (For New Schemas)")
        execute_sql(
            cursor,
            "GRANT USAGE ON FUTURE SCHEMAS IN DATABASE SOURCE_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant USAGE on future schemas",
        )

        execute_sql(
            cursor,
            "GRANT SELECT ON FUTURE TABLES IN DATABASE SOURCE_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant SELECT on future tables (database-level)",
        )

        execute_sql(
            cursor,
            "GRANT SELECT ON FUTURE VIEWS IN DATABASE SOURCE_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE",
            "Grant SELECT on future views (database-level)",
        )

        # Step 6: Verify grants
        print("\n📋 STEP 6: Verification")

        print("\n--- Database-Level Grants ---")
        cursor.execute("SHOW GRANTS ON DATABASE SOURCE_STRIPE")
        db_grants = [
            row for row in cursor.fetchall() if "DBT_STRIPE_ROLE__T_ROLE" in str(row)
        ]
        for grant in db_grants:
            print(f"   ✓ {grant[1]} - {grant[0]}")

        print("\n--- Schema-Level Grants ---")
        cursor.execute("SHOW GRANTS ON SCHEMA SOURCE_STRIPE.STRIPE_WHY")
        schema_grants = [
            row for row in cursor.fetchall() if "DBT_STRIPE_ROLE__T_ROLE" in str(row)
        ]
        for grant in schema_grants:
            print(f"   ✓ {grant[1]} - {grant[0]}")

        print("\n--- Future Grants in Schema ---")
        cursor.execute("SHOW FUTURE GRANTS IN SCHEMA SOURCE_STRIPE.STRIPE_WHY")
        future_grants = [
            row for row in cursor.fetchall() if "DBT_STRIPE_ROLE__T_ROLE" in str(row)
        ]
        for grant in future_grants:
            print(f"   ✓ {grant[5]} - {grant[1]} on {grant[2]}")

        print("\n--- Database-Level Future Grants ---")
        cursor.execute("SHOW FUTURE GRANTS IN DATABASE SOURCE_STRIPE")
        db_future_grants = [
            row for row in cursor.fetchall() if "DBT_STRIPE_ROLE__T_ROLE" in str(row)
        ]
        for grant in db_future_grants:
            print(f"   ✓ {grant[5]} - {grant[1]} on {grant[2]}")

        print("\n--- Verify Ownership (Should Still Be DLT__U_ROLE) ---")
        cursor.execute(
            """
            SELECT table_owner, COUNT(*) as count
            FROM SOURCE_STRIPE.information_schema.tables
            WHERE table_schema = 'STRIPE_WHY'
            GROUP BY table_owner
        """
        )
        ownership = cursor.fetchall()
        for row in ownership:
            if row[0] == "DLT__U_ROLE":
                print(f"   ✅ {row[0]}: {row[1]} objects (correct)")
            else:
                print(f"   ⚠️  {row[0]}: {row[1]} objects (unexpected)")

        print(f"\n{'='*80}")
        print(f"✅ FIX APPLIED SUCCESSFULLY")
        print(f"{'='*80}\n")
        print("Next steps:")
        print("  1. Run diagnostic: uv run python scripts/diagnose_dbt_permissions.py")
        print("  2. Test dbt GitHub Action")
        print("  3. Verify DLT can still load data\n")

        cursor.close()
        conn.close()

        return 0

    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
