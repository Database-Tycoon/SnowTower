#!/usr/bin/env python3
"""
Query Snowflake to find schema owner using SnowDDL's Snowflake connection
"""
from dotenv import load_dotenv

load_dotenv()

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Try direct Snowflake connection
try:
    import snowflake.connector
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    def get_snowflake_connection():
        """Get Snowflake connection using environment variables"""
        account = os.getenv("SNOWFLAKE_ACCOUNT")
        user = os.getenv("SNOWFLAKE_USER")
        role = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")

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

        raise Exception(
            "No authentication method available. Set SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PASSWORD"
        )

    def find_schema_owner(database: str, schema: str):
        """Find the owner of a specific schema"""
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        try:
            # Try ACCOUNT_USAGE first (most reliable)
            print(f"Querying for {database}.{schema} owner...")
            cursor.execute(
                f"""
                SELECT CATALOG_NAME, SCHEMA_NAME, SCHEMA_OWNER, CREATED
                FROM SNOWFLAKE.ACCOUNT_USAGE.SCHEMATA
                WHERE CATALOG_NAME = '{database}'
                AND SCHEMA_NAME = '{schema}'
                ORDER BY CREATED DESC
                LIMIT 1
            """
            )

            result = cursor.fetchone()
            if result:
                print(f"\n✓ Schema found in ACCOUNT_USAGE:")
                print(f"  Database: {result[0]}")
                print(f"  Schema: {result[1]}")
                print(f"  Owner: {result[2]}")
                print(f"  Created: {result[3]}")
                return result[2]

            # Fallback to SHOW SCHEMAS
            print(f"\nSchema not found in ACCOUNT_USAGE, trying SHOW SCHEMAS...")
            cursor.execute(f"USE DATABASE {database}")
            cursor.execute(f"SHOW SCHEMAS LIKE '{schema}'")
            result = cursor.fetchone()

            if result:
                print(f"\n✓ Schema found:")
                print(f"  Name: {result[1]}")
                print(f"  Owner: {result[3]}")
                return result[3]
            else:
                print(f"\n✗ Schema {schema} not found in database {database}")
                return None

        finally:
            cursor.close()
            conn.close()

    if __name__ == "__main__":
        database = sys.argv[1] if len(sys.argv) > 1 else "SOURCE_STRIPE"
        schema = sys.argv[2] if len(sys.argv) > 2 else "STRIPE_WHY"

        owner = find_schema_owner(database, schema)
        if owner:
            print(f"\n✓ Owner: {owner}")
            sys.exit(0)
        else:
            sys.exit(1)

except ImportError as e:
    print(f"Error: Required packages not available: {e}")
    print("\nPlease ensure snowflake-connector-python and cryptography are installed")
    sys.exit(1)
