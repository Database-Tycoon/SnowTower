#!/usr/bin/env python3
"""
User Authentication Health Check Script

Evaluates Snowflake user authentication compliance against 2025-2026 MFA requirements.

Usage:
    uv run health-check                    # Check all users
    uv run health-check --user ALICE     # Check specific user
    uv run health-check --issues-only      # Show only users with issues
    uv run health-check --export health.json  # Export results to JSON

Examples:
    # Quick check of all users
    uv run health-check

    # Focus on problems only
    uv run health-check --issues-only

    # Check yourself
    uv run health-check --user $USER

    # Export for external analysis
    uv run health-check --export compliance_report.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Load environment variables FIRST
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import snowflake.connector
from rich.console import Console

from user_management.health_check import (
    UserHealthChecker,
    HealthCheckResult,
    ComplianceSummary,
)

console = Console()


def get_snowflake_connection():
    """Create Snowflake connection using environment variables"""
    import os
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    try:
        conn_params = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "ADMIN"),
        }

        # Try RSA key first
        private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
        if private_key_path and Path(private_key_path).exists():
            # Read and parse the private key
            with open(private_key_path, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(), password=None, backend=default_backend()
                )

            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            conn_params["private_key"] = private_key_bytes
        else:
            # Fall back to password
            password = os.getenv("SNOWFLAKE_PASSWORD")
            if password:
                conn_params["password"] = password
            else:
                console.print("[red]Error: No authentication method configured[/red]")
                console.print("Set SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PASSWORD")
                sys.exit(1)

        return snowflake.connector.connect(**conn_params)

    except Exception as e:
        console.print(f"[red]Connection Error: {e}[/red]")
        sys.exit(1)


def fetch_users(conn, username: Optional[str] = None) -> list:
    """Fetch user data from Snowflake"""
    try:
        cursor = conn.cursor(snowflake.connector.DictCursor)

        if username:
            query = f"SHOW USERS LIKE '{username.upper()}'"
        else:
            query = "SHOW USERS"

        cursor.execute(query)
        users = cursor.fetchall()

        if not users:
            if username:
                console.print(f"[yellow]User '{username}' not found[/yellow]")
            else:
                console.print("[yellow]No users found[/yellow]")
            sys.exit(1)

        return users

    except Exception as e:
        console.print(f"[red]Query Error: {e}[/red]")
        sys.exit(1)


def export_results(
    results: list[HealthCheckResult], summary: ComplianceSummary, filename: str
):
    """Export results to JSON file"""
    data = {
        "summary": {
            "total_users": summary.total_users,
            "compliant_count": summary.compliant_count,
            "warning_count": summary.warning_count,
            "critical_count": summary.critical_count,
            "compliance_percentage": summary.compliance_percentage,
            "average_score": summary.average_score,
            "ready_for_2026": summary.ready_for_2026,
            "person_users": summary.person_users,
            "service_users": summary.service_users,
            "legacy_service_users": summary.legacy_service_users,
        },
        "users": [
            {
                "username": r.username,
                "user_type": r.user_type,
                "health_score": r.health_score,
                "status": r.status.value,
                "auth_methods": [m.value for m in r.auth_methods],
                "issues": r.issues,
                "recommendations": r.recommendations,
                "disabled": r.disabled,
                "last_login": r.last_login.isoformat() if r.last_login else None,
            }
            for r in results
        ],
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    console.print(f"\n✅ Results exported to: [cyan]{filename}[/cyan]")


def main():
    parser = argparse.ArgumentParser(
        description="Check Snowflake user authentication health and compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--user", help="Check specific user only")
    parser.add_argument(
        "--issues-only",
        action="store_true",
        help="Show only users with issues (hide compliant users)",
    )
    parser.add_argument("--export", metavar="FILE", help="Export results to JSON file")
    parser.add_argument(
        "--no-recommendations", action="store_true", help="Skip recommendations section"
    )

    args = parser.parse_args()

    # Connect to Snowflake
    console.print("[dim]Connecting to Snowflake...[/dim]")
    conn = get_snowflake_connection()

    # Fetch users
    console.print("[dim]Fetching user data...[/dim]\n")
    users_data = fetch_users(conn, args.user)
    conn.close()

    # Run health checks
    checker = UserHealthChecker()

    if args.user:
        # Single user mode
        result = checker.check_user(users_data[0])

        console.print(f"\n[bold]Health Check: {result.username}[/bold]\n")
        console.print(f"User Type: {result.user_type}")
        console.print(
            f"Health Score: [{('green' if result.health_score >= 85 else 'yellow' if result.health_score >= 50 else 'red')}]{result.health_score}/100[/]"
        )
        console.print(f"Status: {result.status_emoji} {result.status_text}")
        console.print(f"Authentication: {result.auth_icons}")

        if result.issues:
            console.print(f"\n[bold red]Issues:[/bold red]")
            for issue in result.issues:
                console.print(f"  • {issue}")

        if result.recommendations and not args.no_recommendations:
            console.print(f"\n[bold yellow]Recommendations:[/bold yellow]")
            for rec in result.recommendations:
                console.print(f"  • {rec}")

        if result.last_login:
            console.print(
                f"\nLast Login: {result.last_login.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            console.print(f"\nLast Login: [yellow]Never[/yellow]")

        results = [result]
        summary = ComplianceSummary(
            total_users=1,
            compliant_count=1 if result.status.value == "compliant" else 0,
            warning_count=1 if result.status.value == "warning" else 0,
            critical_count=1 if result.status.value == "critical" else 0,
            person_users=1 if result.user_type == "PERSON" else 0,
            service_users=1 if result.user_type == "SERVICE" else 0,
            legacy_service_users=1 if result.user_type == "LEGACY_SERVICE" else 0,
            average_score=float(result.health_score),
            ready_for_2026=result.status.value == "compliant",
        )

    else:
        # All users mode
        results, summary = checker.check_all_users(users_data)

        # Print summary
        checker.print_summary(summary)
        console.print()

        # Print user table
        checker.print_user_table(results, show_all=not args.issues_only)

        # Print recommendations
        if not args.no_recommendations:
            checker.print_recommendations(results)

    # Export if requested
    if args.export:
        export_results(results, summary, args.export)

    # Exit code based on compliance
    if summary.critical_count > 0:
        sys.exit(2)  # Critical issues
    elif summary.warning_count > 0:
        sys.exit(1)  # Warnings
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    main()
