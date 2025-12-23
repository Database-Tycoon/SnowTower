#!/usr/bin/env python3
"""
Diagnose dbt permissions issues in Snowflake
Checks schema ownership, role privileges, and future grants
"""
from dotenv import load_dotenv

load_dotenv()

import sys
import os
from pathlib import Path
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


def check_schema_existence(cursor, database, schema):
    """Check if schema exists and get its owner"""
    cursor.execute(f"USE DATABASE {database}")
    cursor.execute(f"SHOW SCHEMAS LIKE '{schema}'")
    result = cursor.fetchone()

    if result:
        return {
            "exists": True,
            "name": result[1],
            "created": result[0],
            "owner": result[5],
            "database": result[4],
        }
    return {"exists": False}


def check_role_grants(cursor, role, database, schema=None):
    """Check what grants a role has on database/schema"""
    grants = []

    # Database-level grants
    cursor.execute(f"SHOW GRANTS ON DATABASE {database}")
    for row in cursor.fetchall():
        if row[1] == role:
            grants.append(
                {
                    "object_type": "DATABASE",
                    "object_name": database,
                    "privilege": row[0],
                    "granted_to": row[1],
                }
            )

    # Schema-level grants (if schema specified)
    if schema:
        try:
            cursor.execute(f"SHOW GRANTS ON SCHEMA {database}.{schema}")
            for row in cursor.fetchall():
                if row[1] == role:
                    grants.append(
                        {
                            "object_type": "SCHEMA",
                            "object_name": f"{database}.{schema}",
                            "privilege": row[0],
                            "granted_to": row[1],
                        }
                    )
        except:
            pass

    return grants


def check_future_grants(cursor, database, schema, role):
    """Check future grants for a role in a schema"""
    future_grants = []

    try:
        cursor.execute(f"SHOW FUTURE GRANTS IN SCHEMA {database}.{schema}")
        for row in cursor.fetchall():
            # Row format: created_on, privilege, grant_on, name, grant_to, grantee_name, grant_option
            if row[5] == role:
                future_grants.append(
                    {"privilege": row[1], "grant_on": row[2], "grantee": row[5]}
                )
    except Exception as e:
        print(f"⚠️  Could not check future grants: {e}")

    return future_grants


def check_object_ownership(cursor, database, schema):
    """Check ownership of all objects in schema"""
    cursor.execute(f"USE DATABASE {database}")
    cursor.execute(f"USE SCHEMA {schema}")

    # Check tables
    cursor.execute(
        f"""
        SELECT table_schema, table_name, table_owner, table_type
        FROM {database}.information_schema.tables
        WHERE table_schema = '{schema}'
        ORDER BY table_type, table_name
    """
    )

    objects = []
    for row in cursor.fetchall():
        objects.append(
            {"schema": row[0], "name": row[1], "owner": row[2], "type": row[3]}
        )

    return objects


def generate_fix_sql(database, schema, role, objects):
    """Generate SQL to fix permissions issues"""
    sql_commands = []

    sql_commands.append(f"-- Fix permissions for {database}.{schema}")
    sql_commands.append(f"USE ROLE ACCOUNTADMIN;")
    sql_commands.append(f"USE DATABASE {database};")
    sql_commands.append("")

    # Transfer existing object ownership
    sql_commands.append("-- Transfer ownership of existing objects")
    sql_commands.append(f"GRANT OWNERSHIP ON ALL TABLES IN SCHEMA {schema}")
    sql_commands.append(f"TO ROLE {role} COPY CURRENT GRANTS;")
    sql_commands.append("")
    sql_commands.append(f"GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA {schema}")
    sql_commands.append(f"TO ROLE {role} COPY CURRENT GRANTS;")
    sql_commands.append("")

    # Configure future ownership
    sql_commands.append("-- Configure future object ownership")
    sql_commands.append(f"GRANT OWNERSHIP ON FUTURE TABLES IN SCHEMA {schema}")
    sql_commands.append(f"TO ROLE {role};")
    sql_commands.append("")
    sql_commands.append(f"GRANT OWNERSHIP ON FUTURE VIEWS IN SCHEMA {schema}")
    sql_commands.append(f"TO ROLE {role};")
    sql_commands.append("")

    # Grant schema privileges if needed
    sql_commands.append("-- Ensure schema-level privileges")
    sql_commands.append(f"GRANT USAGE ON SCHEMA {schema} TO ROLE {role};")
    sql_commands.append(f"GRANT CREATE TABLE ON SCHEMA {schema} TO ROLE {role};")
    sql_commands.append(f"GRANT CREATE VIEW ON SCHEMA {schema} TO ROLE {role};")
    sql_commands.append("")

    # Verification queries
    sql_commands.append("-- Verify ownership transfer")
    sql_commands.append(f"SELECT table_schema, table_name, table_owner, table_type")
    sql_commands.append(f"FROM {database}.information_schema.tables")
    sql_commands.append(f"WHERE table_schema = '{schema}'")
    sql_commands.append(f"ORDER BY table_type, table_name;")
    sql_commands.append("")
    sql_commands.append(f"SHOW FUTURE GRANTS IN SCHEMA {schema};")

    return "\n".join(sql_commands)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Diagnose dbt permissions issues")
    parser.add_argument("--database", default="SOURCE_STRIPE", help="Database name")
    parser.add_argument("--schema", default="STRIPE_WHY", help="Schema name")
    parser.add_argument(
        "--role", default="DBT_STRIPE_ROLE__T_ROLE", help="dbt role name"
    )
    parser.add_argument("--fix", action="store_true", help="Generate fix SQL")
    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"dbt Permissions Diagnostic Tool")
    print(f"{'='*80}\n")

    print(f"📊 Analyzing: {args.database}.{args.schema}")
    print(f"🔑 Role: {args.role}\n")

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        # 1. Check schema existence
        print(f"1️⃣  Checking schema existence...")
        schema_info = check_schema_existence(cursor, args.database, args.schema)

        if not schema_info["exists"]:
            print(f"❌ Schema {args.database}.{args.schema} does not exist!")
            print(f"   The schema must be created before dbt can use it.")
            return 1

        print(f"✅ Schema exists")
        print(f"   Owner: {schema_info['owner']}")
        print(f"   Created: {schema_info['created']}\n")

        # 2. Check role grants
        print(f"2️⃣  Checking role grants on database and schema...")
        grants = check_role_grants(cursor, args.role, args.database, args.schema)

        if grants:
            print(f"✅ Found {len(grants)} grants for role {args.role}")
            grant_table = [
                [g["object_type"], g["object_name"], g["privilege"]] for g in grants
            ]
            print(
                tabulate(
                    grant_table,
                    headers=["Object Type", "Object", "Privilege"],
                    tablefmt="simple",
                )
            )
        else:
            print(f"❌ No grants found for role {args.role} on {args.database}")
            print(f"   The role needs DATABASE USAGE and CREATE SCHEMA privileges.\n")
        print()

        # 3. Check future grants
        print(f"3️⃣  Checking future grants...")
        future_grants = check_future_grants(
            cursor, args.database, args.schema, args.role
        )

        if future_grants:
            print(f"✅ Found {len(future_grants)} future grants")
            fg_table = [[fg["grant_on"], fg["privilege"]] for fg in future_grants]
            print(
                tabulate(
                    fg_table, headers=["Object Type", "Privilege"], tablefmt="simple"
                )
            )
        else:
            print(f"⚠️  No future grants found for {args.role}")
            print(
                f"   Future grants ensure new objects are owned by the correct role.\n"
            )
        print()

        # 4. Check object ownership
        print(f"4️⃣  Checking object ownership in schema...")
        objects = check_object_ownership(cursor, args.database, args.schema)

        if objects:
            print(f"📦 Found {len(objects)} objects in schema")

            # Group by owner
            ownership_summary = {}
            for obj in objects:
                owner = obj["owner"]
                if owner not in ownership_summary:
                    ownership_summary[owner] = {"TABLES": 0, "VIEWS": 0}
                if obj["type"] == "BASE TABLE":
                    ownership_summary[owner]["TABLES"] += 1
                elif obj["type"] == "VIEW":
                    ownership_summary[owner]["VIEWS"] += 1

            print("\nOwnership Summary:")
            summary_table = [
                [owner, counts["TABLES"], counts["VIEWS"]]
                for owner, counts in ownership_summary.items()
            ]
            print(
                tabulate(
                    summary_table,
                    headers=["Owner", "Tables", "Views"],
                    tablefmt="simple",
                )
            )

            # Check if dbt role owns all objects
            dbt_owns_all = all(obj["owner"] == args.role for obj in objects)

            if dbt_owns_all:
                print(f"\n✅ All objects owned by {args.role}")
            else:
                print(f"\n⚠️  Objects owned by multiple roles!")
                print(f"   This will cause 'insufficient privileges' errors.")
                print(
                    f"   dbt needs OWNERSHIP (not just permissions) to DROP/REPLACE objects.\n"
                )

                # Show first few objects with wrong owner
                wrong_owner = [obj for obj in objects if obj["owner"] != args.role][:5]
                print("Sample objects with incorrect owner:")
                wo_table = [
                    [obj["type"], obj["name"], obj["owner"]] for obj in wrong_owner
                ]
                print(
                    tabulate(
                        wo_table, headers=["Type", "Name", "Owner"], tablefmt="simple"
                    )
                )
                if len(wrong_owner) > 5:
                    print(f"   ... and {len(wrong_owner) - 5} more")
        else:
            print(f"✅ No objects in schema yet")

        print()

        # 5. Summary and recommendations
        print(f"{'='*80}")
        print(f"DIAGNOSIS SUMMARY")
        print(f"{'='*80}\n")

        issues = []

        # Check for missing database grants
        db_grants = [g for g in grants if g["object_type"] == "DATABASE"]
        if not any("USAGE" in g["privilege"] for g in db_grants):
            issues.append("❌ Missing DATABASE USAGE grant")
        if not any("CREATE SCHEMA" in g["privilege"] for g in db_grants):
            issues.append("⚠️  Missing CREATE SCHEMA grant (needed for new schemas)")

        # Check for future grants
        if not future_grants:
            issues.append(
                "⚠️  Missing future grants (new objects won't have correct ownership)"
            )

        # Check object ownership
        if objects and not all(obj["owner"] == args.role for obj in objects):
            issues.append(
                f"❌ Objects owned by wrong role (causing 'insufficient privileges' errors)"
            )

        if issues:
            print("🔴 Issues Found:\n")
            for issue in issues:
                print(f"   {issue}")
            print()

            if args.fix:
                print(f"\n{'='*80}")
                print(f"FIX SQL COMMANDS")
                print(f"{'='*80}\n")

                fix_sql = generate_fix_sql(
                    args.database, args.schema, args.role, objects
                )
                print(fix_sql)

                # Save to file
                fix_file = Path(
                    f"fix_dbt_permissions_{args.database}_{args.schema}.sql"
                )
                fix_file.write_text(fix_sql)
                print(f"\n💾 SQL commands saved to: {fix_file}")
                print(f"\nTo apply the fix:")
                print(f"   1. Review the SQL file")
                print(f"   2. Execute it in Snowflake using ACCOUNTADMIN role")
                print(f"   3. Re-run this diagnostic to verify")
        else:
            print("✅ No issues found! Permissions are correctly configured.\n")

        cursor.close()
        conn.close()

        return 0 if not issues else 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
