#!/usr/bin/env python3
"""
Manage Streamlit Viewer Role - Create and configure read-only infrastructure access

This script manages the STREAMLIT_VIEWER role which provides minimal metadata access
for users of the SnowTower Streamlit application without requiring ACCOUNTADMIN privileges.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional
import snowflake.connector
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class StreamlitViewerManager:
    """Manages the Streamlit Viewer role for infrastructure metadata access"""

    def __init__(self):
        """Initialize connection parameters from environment"""
        self.account = os.getenv("SNOWFLAKE_ACCOUNT")
        self.user = os.getenv("SNOWFLAKE_USER")
        self.password = os.getenv("SNOWFLAKE_PASSWORD")
        self.role = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
        self.warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "ADMIN")
        self.conn = None

    def connect(self) -> snowflake.connector.SnowflakeConnection:
        """Establish connection to Snowflake"""
        if not self.conn:
            self.conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                role=self.role,
                warehouse=self.warehouse,
            )
        return self.conn

    def execute_query(self, query: str) -> List[Dict]:
        """Execute a query and return results"""
        conn = self.connect()
        cursor = conn.cursor(snowflake.connector.DictCursor)
        try:
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()

    def execute_command(self, command: str) -> bool:
        """Execute a command and return success status"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(command)
            return True
        except Exception as e:
            print(f"Error executing command: {e}")
            return False
        finally:
            cursor.close()

    def create_role(self, dry_run: bool = False) -> bool:
        """Create the STREAMLIT_VIEWER role with all necessary permissions"""

        commands = [
            # Create role
            """CREATE ROLE IF NOT EXISTS STREAMLIT_VIEWER
               COMMENT = 'Read-only infrastructure viewer role for Streamlit app users'""",
            # Grant to SYSADMIN
            "GRANT ROLE STREAMLIT_VIEWER TO ROLE SYSADMIN",
            # Create warehouse
            """CREATE WAREHOUSE IF NOT EXISTS STREAMLIT_VIEWER_WH
               WITH WAREHOUSE_SIZE = 'XSMALL'
               AUTO_SUSPEND = 60
               AUTO_RESUME = TRUE
               MIN_CLUSTER_COUNT = 1
               MAX_CLUSTER_COUNT = 1
               INITIALLY_SUSPENDED = FALSE
               COMMENT = 'Dedicated warehouse for Streamlit viewer metadata queries'""",
            # Grant warehouse usage
            "GRANT USAGE ON WAREHOUSE STREAMLIT_VIEWER_WH TO ROLE STREAMLIT_VIEWER",
            # Grant metadata access
            "GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE STREAMLIT_VIEWER",
            "GRANT MONITOR USAGE ON ACCOUNT TO ROLE STREAMLIT_VIEWER",
            "GRANT USAGE ON ALL DATABASES IN ACCOUNT TO ROLE STREAMLIT_VIEWER",
            "GRANT USAGE ON ALL SCHEMAS IN ACCOUNT TO ROLE STREAMLIT_VIEWER",
            "GRANT USAGE ON FUTURE DATABASES IN ACCOUNT TO ROLE STREAMLIT_VIEWER",
            "GRANT USAGE ON FUTURE SCHEMAS IN ACCOUNT TO ROLE STREAMLIT_VIEWER",
            "GRANT MONITOR ON ALL WAREHOUSES IN ACCOUNT TO ROLE STREAMLIT_VIEWER",
        ]

        if dry_run:
            print("DRY RUN - Commands that would be executed:")
            for cmd in commands:
                print(f"  {cmd.replace(chr(10), ' ')[:100]}...")
            return True

        print("Creating STREAMLIT_VIEWER role...")
        for cmd in commands:
            desc = (
                cmd.split()[0] + " " + cmd.split()[1]
                if len(cmd.split()) > 1
                else cmd[:50]
            )
            print(f"  Executing: {desc}...")
            if not self.execute_command(cmd):
                return False

        print("✅ STREAMLIT_VIEWER role created successfully")
        return True

    def grant_to_business_roles(
        self, roles: List[str] = None, dry_run: bool = False
    ) -> bool:
        """Grant STREAMLIT_VIEWER to business roles"""

        if roles is None:
            roles = ["COMPANY_USERS", "ADMIN_ROLE", "BI_DEVELOPER_ROLE"]

        commands = [f"GRANT ROLE STREAMLIT_VIEWER TO ROLE {role}" for role in roles]

        if dry_run:
            print("DRY RUN - Commands that would be executed:")
            for cmd in commands:
                print(f"  {cmd}")
            return True

        print("Granting STREAMLIT_VIEWER to business roles...")
        for cmd in commands:
            role_name = cmd.split()[-1]
            print(f"  Granting to {role_name}...")
            if not self.execute_command(cmd):
                print(f"    Warning: Could not grant to {role_name}")

        print("✅ Role grants completed")
        return True

    def verify_role(self) -> Dict:
        """Verify the STREAMLIT_VIEWER role configuration"""

        print("Verifying STREAMLIT_VIEWER role configuration...")

        results = {
            "role_exists": False,
            "warehouse_exists": False,
            "warehouse_grants": [],
            "database_grants": [],
            "account_grants": [],
            "granted_to_roles": [],
            "test_queries": {},
        }

        # Check role exists
        roles = self.execute_query("SHOW ROLES LIKE 'STREAMLIT_VIEWER'")
        results["role_exists"] = len(roles) > 0
        print(f"  Role exists: {results['role_exists']}")

        if not results["role_exists"]:
            return results

        # Check warehouse exists
        warehouses = self.execute_query("SHOW WAREHOUSES LIKE 'STREAMLIT_VIEWER_WH'")
        results["warehouse_exists"] = len(warehouses) > 0
        print(f"  Warehouse exists: {results['warehouse_exists']}")

        # Check grants
        grants = self.execute_query("SHOW GRANTS TO ROLE STREAMLIT_VIEWER")
        for grant in grants:
            privilege = grant.get("privilege", "")
            on_type = grant.get("granted_on", "")
            on_name = grant.get("name", "")

            if on_type == "WAREHOUSE":
                results["warehouse_grants"].append(f"{privilege} on {on_name}")
            elif on_type == "DATABASE":
                results["database_grants"].append(f"{privilege} on {on_name}")
            elif on_type == "ACCOUNT":
                results["account_grants"].append(privilege)

        print(f"  Warehouse grants: {len(results['warehouse_grants'])}")
        print(f"  Database grants: {len(results['database_grants'])}")
        print(f"  Account grants: {len(results['account_grants'])}")

        # Check role grants
        role_grants = self.execute_query("SHOW GRANTS OF ROLE STREAMLIT_VIEWER")
        for grant in role_grants:
            grantee = grant.get("grantee_name", "")
            if grantee and grantee != "STREAMLIT_VIEWER":
                results["granted_to_roles"].append(grantee)

        print(f"  Granted to roles: {results['granted_to_roles']}")

        # Test queries
        print("  Testing metadata queries...")
        self.execute_command("USE ROLE STREAMLIT_VIEWER")
        self.execute_command("USE WAREHOUSE STREAMLIT_VIEWER_WH")

        test_queries = [
            ("SHOW USERS", "show_users"),
            ("SHOW ROLES", "show_roles"),
            ("SHOW WAREHOUSES", "show_warehouses"),
            ("SHOW DATABASES", "show_databases"),
            (
                "SELECT COUNT(*) as cnt FROM SNOWFLAKE.ACCOUNT_USAGE.USERS",
                "account_usage_access",
            ),
        ]

        for query, key in test_queries:
            try:
                result = self.execute_query(query)
                results["test_queries"][key] = (
                    len(result) if key != "account_usage_access" else result[0]["CNT"]
                )
                print(f"    {key}: ✅ ({results['test_queries'][key]} records)")
            except Exception as e:
                results["test_queries"][key] = f"Failed: {str(e)}"
                print(f"    {key}: ❌")

        # Switch back to ACCOUNTADMIN
        self.execute_command(f"USE ROLE {self.role}")

        return results

    def drop_role(self, dry_run: bool = False) -> bool:
        """Drop the STREAMLIT_VIEWER role and associated objects"""

        commands = [
            # Revoke from business roles
            "REVOKE ROLE STREAMLIT_VIEWER FROM ROLE COMPANY_USERS",
            "REVOKE ROLE STREAMLIT_VIEWER FROM ROLE ADMIN_ROLE",
            "REVOKE ROLE STREAMLIT_VIEWER FROM ROLE BI_DEVELOPER_ROLE",
            # Drop warehouse
            "DROP WAREHOUSE IF EXISTS STREAMLIT_VIEWER_WH",
            # Drop role
            "DROP ROLE IF EXISTS STREAMLIT_VIEWER",
        ]

        if dry_run:
            print("DRY RUN - Commands that would be executed:")
            for cmd in commands:
                print(f"  {cmd}")
            return True

        print("Dropping STREAMLIT_VIEWER role...")
        for cmd in commands:
            desc = (
                cmd.split()[0] + " " + cmd.split()[1]
                if len(cmd.split()) > 1
                else cmd[:50]
            )
            print(f"  Executing: {desc}...")
            self.execute_command(cmd)  # Don't fail on revoke errors

        print("✅ STREAMLIT_VIEWER role dropped")
        return True

    def show_usage(self, days: int = 7) -> None:
        """Show usage statistics for the STREAMLIT_VIEWER role"""

        print(f"\nStreamlit Viewer Role Usage (last {days} days):")

        query = f"""
        SELECT
            USER_NAME,
            COUNT(*) as QUERY_COUNT,
            COUNT(DISTINCT DATE(START_TIME)) as ACTIVE_DAYS,
            SUM(CREDITS_USED_CLOUD_SERVICES) as CREDITS_USED,
            MIN(START_TIME) as FIRST_QUERY,
            MAX(START_TIME) as LAST_QUERY
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE ROLE_NAME = 'STREAMLIT_VIEWER'
          AND START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
        GROUP BY USER_NAME
        ORDER BY QUERY_COUNT DESC
        """

        try:
            results = self.execute_query(query)

            if not results:
                print("  No usage found in the specified period")
                return

            print(
                f"\n{'User':<20} {'Queries':<10} {'Days':<10} {'Credits':<10} {'Last Query':<20}"
            )
            print("-" * 70)

            for row in results:
                print(
                    f"{row['USER_NAME']:<20} {row['QUERY_COUNT']:<10} "
                    f"{row['ACTIVE_DAYS']:<10} {row['CREDITS_USED']:<10.4f} "
                    f"{str(row['LAST_QUERY']):<20}"
                )

            # Summary
            total_queries = sum(row["QUERY_COUNT"] for row in results)
            total_credits = sum(row["CREDITS_USED"] for row in results)
            unique_users = len(results)

            print("-" * 70)
            print(
                f"Total: {unique_users} users, {total_queries} queries, {total_credits:.4f} credits"
            )

        except Exception as e:
            print(f"  Error retrieving usage data: {e}")

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description="Manage Streamlit Viewer Role for infrastructure metadata access",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create the role with all permissions
  %(prog)s create

  # Verify role configuration
  %(prog)s verify

  # Grant to specific business roles
  %(prog)s grant --roles COMPANY_USERS ADMIN_ROLE

  # Show usage statistics
  %(prog)s usage --days 30

  # Drop the role (cleanup)
  %(prog)s drop

  # Dry run to see what would be executed
  %(prog)s create --dry-run
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create STREAMLIT_VIEWER role")
    create_parser.add_argument(
        "--dry-run", action="store_true", help="Show commands without executing"
    )

    # Grant command
    grant_parser = subparsers.add_parser("grant", help="Grant role to business roles")
    grant_parser.add_argument(
        "--roles",
        nargs="+",
        help="Business roles to grant to (default: COMPANY_USERS ADMIN_ROLE BI_DEVELOPER_ROLE)",
    )
    grant_parser.add_argument(
        "--dry-run", action="store_true", help="Show commands without executing"
    )

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify role configuration")

    # Drop command
    drop_parser = subparsers.add_parser("drop", help="Drop STREAMLIT_VIEWER role")
    drop_parser.add_argument(
        "--dry-run", action="store_true", help="Show commands without executing"
    )

    # Usage command
    usage_parser = subparsers.add_parser("usage", help="Show usage statistics")
    usage_parser.add_argument(
        "--days", type=int, default=7, help="Number of days to look back (default: 7)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize manager
    manager = StreamlitViewerManager()

    try:
        if args.command == "create":
            success = manager.create_role(dry_run=args.dry_run)
            if success and not args.dry_run:
                manager.grant_to_business_roles()
                manager.verify_role()

        elif args.command == "grant":
            manager.grant_to_business_roles(roles=args.roles, dry_run=args.dry_run)

        elif args.command == "verify":
            results = manager.verify_role()

            print("\n📊 Verification Summary:")
            print(f"  Role exists: {'✅' if results['role_exists'] else '❌'}")
            print(f"  Warehouse exists: {'✅' if results['warehouse_exists'] else '❌'}")
            print(
                f"  Permissions granted: {len(results['warehouse_grants']) + len(results['database_grants']) + len(results['account_grants'])}"
            )
            print(f"  Business roles with access: {len(results['granted_to_roles'])}")

            working_queries = sum(
                1
                for v in results["test_queries"].values()
                if not isinstance(v, str) or not v.startswith("Failed")
            )
            print(
                f"  Test queries passed: {working_queries}/{len(results['test_queries'])}"
            )

        elif args.command == "drop":
            manager.drop_role(dry_run=args.dry_run)

        elif args.command == "usage":
            manager.show_usage(days=args.days)

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1

    finally:
        manager.close()


if __name__ == "__main__":
    sys.exit(main())
