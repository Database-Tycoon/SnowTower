#!/usr/bin/env python3
"""
Apply ownership fix for PROJ_STRIPE.PROJ_STRIPE schema
Transfers ownership to DBT_STRIPE_ROLE__T_ROLE
"""
from dotenv import load_dotenv

load_dotenv()

import os
import sys
from pathlib import Path
from tabulate import tabulate

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def get_snowflake_connection():
    """Get Snowflake connection using ACCOUNTADMIN role"""
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    role = "ACCOUNTADMIN"  # Must use ACCOUNTADMIN for ownership transfer

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


def apply_fix():
    """Apply the ownership fix"""
    print(f"\n{'='*100}")
    print(f"PROJ_STRIPE Ownership Fix - Applying Changes")
    print(f"{'='*100}\n")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Query current state
        print("Step 1: Checking current ownership...\n")
        cursor.execute(
            """
            SELECT table_schema, table_name, table_owner, table_type
            FROM PROJ_STRIPE.information_schema.tables
            WHERE table_schema = 'PROJ_STRIPE'
            ORDER BY table_type, table_name
        """
        )
        before_results = cursor.fetchall()

        print("Current ownership:")
        print(
            tabulate(
                [[r[1], r[3], r[2]] for r in before_results],
                headers=["Object", "Type", "Owner"],
                tablefmt="simple",
            )
        )
        print(f"\nTotal objects: {len(before_results)}\n")

        # Step 2: Transfer table ownership
        print("Step 2: Transferring table ownership...\n")
        cursor.execute(
            """
            GRANT OWNERSHIP ON ALL TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
            TO ROLE DBT_STRIPE_ROLE__T_ROLE COPY CURRENT GRANTS
        """
        )
        print("✅ Table ownership transferred\n")

        # Step 3: Transfer view ownership
        print("Step 3: Transferring view ownership...\n")
        cursor.execute(
            """
            GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
            TO ROLE DBT_STRIPE_ROLE__T_ROLE COPY CURRENT GRANTS
        """
        )
        print("✅ View ownership transferred\n")

        # Step 4: Configure future ownership
        print("Step 4: Configuring future ownership...\n")
        cursor.execute(
            """
            GRANT OWNERSHIP ON FUTURE TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
            TO ROLE DBT_STRIPE_ROLE__T_ROLE
        """
        )
        cursor.execute(
            """
            GRANT OWNERSHIP ON FUTURE VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
            TO ROLE DBT_STRIPE_ROLE__T_ROLE
        """
        )
        print("✅ Future ownership configured\n")

        # Step 5: Grant schema privileges
        print("Step 5: Granting schema privileges...\n")
        cursor.execute(
            "GRANT USAGE ON SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        cursor.execute(
            "GRANT CREATE TABLE ON SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        cursor.execute(
            "GRANT CREATE VIEW ON SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE"
        )
        print("✅ Schema privileges granted\n")

        # Step 6: Grant SELECT on SOURCE_STRIPE
        print("Step 6: Granting SELECT on SOURCE_STRIPE...\n")
        cursor.execute(
            """
            GRANT SELECT ON ALL TABLES IN SCHEMA SOURCE_STRIPE.STRIPE_WHY
            TO ROLE DBT_STRIPE_ROLE__T_ROLE
        """
        )
        cursor.execute(
            """
            GRANT SELECT ON FUTURE TABLES IN SCHEMA SOURCE_STRIPE.STRIPE_WHY
            TO ROLE DBT_STRIPE_ROLE__T_ROLE
        """
        )
        print("✅ Source data access granted\n")

        # Step 7: Verify changes
        print("Step 7: Verifying ownership changes...\n")
        cursor.execute(
            """
            SELECT table_schema, table_name, table_owner, table_type
            FROM PROJ_STRIPE.information_schema.tables
            WHERE table_schema = 'PROJ_STRIPE'
            ORDER BY table_type, table_name
        """
        )
        after_results = cursor.fetchall()

        print("New ownership:")
        print(
            tabulate(
                [[r[1], r[3], r[2]] for r in after_results],
                headers=["Object", "Type", "Owner"],
                tablefmt="simple",
            )
        )

        # Verify all objects owned by dbt role
        dbt_owned = sum(1 for r in after_results if r[2] == "DBT_STRIPE_ROLE__T_ROLE")
        print(
            f"\n✅ {dbt_owned}/{len(after_results)} objects now owned by DBT_STRIPE_ROLE__T_ROLE\n"
        )

        # Step 8: Verify future grants
        print("Step 8: Verifying future grants...\n")
        cursor.execute("SHOW FUTURE GRANTS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE")
        future_grants = cursor.fetchall()

        dbt_future_grants = [
            fg for fg in future_grants if "DBT_STRIPE_ROLE__T_ROLE" in str(fg)
        ]
        print(
            f"✅ {len(dbt_future_grants)} future grant(s) configured for DBT_STRIPE_ROLE__T_ROLE\n"
        )

        print(f"{'='*100}")
        print("SUCCESS: Ownership fix applied successfully!")
        print(f"{'='*100}\n")

        cursor.close()
        conn.close()

        return 0

    except Exception as e:
        print(f"\n❌ Error applying fix: {e}")
        import traceback

        traceback.print_exc()
        cursor.close()
        conn.close()
        return 1


if __name__ == "__main__":
    sys.exit(apply_fix())
