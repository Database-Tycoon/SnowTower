#!/usr/bin/env python3
"""
Query all schemas in Snowflake and list their contents with last update times
"""
from dotenv import load_dotenv

load_dotenv()

import os
import sys
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def get_snowflake_connection():
    """Get Snowflake connection using environment variables"""
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


def query_all_schemas():
    """Query all schemas across all databases and list their contents"""
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    print(f"\n{'='*120}")
    print(f"Snowflake Schema and Table Inventory")
    print(f"{'='*120}\n")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Account: {os.getenv('SNOWFLAKE_ACCOUNT')}")
    print(f"User: {os.getenv('SNOWFLAKE_USER')}")
    print(f"Role: ACCOUNTADMIN\n")

    # Get all databases
    cursor.execute("SHOW DATABASES")
    databases = [row[1] for row in cursor.fetchall()]

    databases_of_interest = [
        "SOURCE_STRIPE",
        "PROJ_STRIPE",
        "ANALYTICS_TOOL",
        "BI_TOOL",
        "DEV_ALICE",
        "DEV_CAROL",
        "DEV_DAVE",
        "DEV_EVE",
        "DEV_GRACE",
        "DEV_BOB",
        "DEV_FRANK",
    ]

    for database in databases:
        if database not in databases_of_interest:
            continue

        print(f"\n{'='*120}")
        print(f"📊 DATABASE: {database}")
        print(f"{'='*120}\n")

        try:
            cursor.execute(f"USE DATABASE {database}")
            cursor.execute("SHOW SCHEMAS")
            schemas = cursor.fetchall()

            if not schemas:
                print(f"  No schemas found in {database}\n")
                continue

            for schema_row in schemas:
                schema_name = schema_row[1]
                schema_owner = schema_row[5]
                schema_created = schema_row[0]

                # Skip system schemas
                if schema_name in ("INFORMATION_SCHEMA", "PUBLIC"):
                    continue

                print(f"\n  📁 SCHEMA: {database}.{schema_name}")
                print(f"     Owner: {schema_owner}")
                print(f"     Created: {schema_created}\n")

                # Query tables and views in this schema
                try:
                    query = f"""
                    SELECT
                        table_schema,
                        table_name,
                        table_type,
                        table_owner,
                        row_count,
                        bytes,
                        created,
                        last_altered
                    FROM {database}.information_schema.tables
                    WHERE table_schema = '{schema_name}'
                    ORDER BY table_type, last_altered DESC, table_name
                    """
                    cursor.execute(query)
                    tables = cursor.fetchall()

                    if tables:
                        table_data = []
                        for table in tables:
                            table_data.append(
                                [
                                    table[1],  # name
                                    table[2],  # type
                                    table[3],  # owner
                                    f"{table[4]:,}" if table[4] else "0",  # row_count
                                    f"{table[5]:,}" if table[5] else "0",  # bytes
                                    (
                                        table[6].strftime("%Y-%m-%d %H:%M")
                                        if table[6]
                                        else "N/A"
                                    ),  # created
                                    (
                                        table[7].strftime("%Y-%m-%d %H:%M")
                                        if table[7]
                                        else "N/A"
                                    ),  # last_altered
                                ]
                            )

                        print(
                            tabulate(
                                table_data,
                                headers=[
                                    "Object Name",
                                    "Type",
                                    "Owner",
                                    "Rows",
                                    "Bytes",
                                    "Created",
                                    "Last Altered",
                                ],
                                tablefmt="simple",
                            )
                        )
                        print(f"\n     Total objects: {len(tables)}\n")
                    else:
                        print(f"     No tables or views in this schema\n")

                except Exception as e:
                    print(f"     ⚠️  Error querying schema contents: {e}\n")

        except Exception as e:
            print(f"  ⚠️  Error accessing database {database}: {e}\n")

    cursor.close()
    conn.close()

    print(f"\n{'='*120}")
    print("Query Complete")
    print(f"{'='*120}\n")


if __name__ == "__main__":
    try:
        query_all_schemas()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
