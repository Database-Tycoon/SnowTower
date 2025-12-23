#!/usr/bin/env python3
"""
Authentication Diagnostics Script for SnowTower SnowDDL

This script diagnoses authentication issues with Snowflake connections
and provides specific remediation steps.

Usage:
    python diagnose_auth.py
    uv run diagnose-auth
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

try:
    from env_loader import (
        load_snowflake_env,
        get_connection_info,
        EnvironmentError,
        AuthenticationError,
    )
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError as e:
    print(f"ERROR: Missing required dependencies: {e}")
    print("Please run: uv sync")
    exit(1)


def load_environment() -> Dict[str, Any]:
    """Load and validate environment configuration using env_loader utility."""
    try:
        # Use the reliable env_loader utility
        env_vars = load_snowflake_env(validate_auth=True)
        return {
            "account": env_vars.get("SNOWFLAKE_ACCOUNT"),
            "user": env_vars.get("SNOWFLAKE_USER"),
            "role": env_vars.get("SNOWFLAKE_ROLE"),
            "warehouse": env_vars.get("SNOWFLAKE_WAREHOUSE"),
            "private_key_path": env_vars.get("SNOWFLAKE_PRIVATE_KEY_PATH"),
            "password": env_vars.get("SNOWFLAKE_PASSWORD"),
            "passphrase": env_vars.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"),
        }
    except (EnvironmentError, AuthenticationError) as e:
        console = Console()
        console.print(f"[red]Environment configuration error: {str(e)}[/red]")
        console.print("[yellow]Run 'uv run test-env' for detailed diagnostics[/yellow]")
        return {}
    except Exception as e:
        console = Console()
        console.print(f"[red]Unexpected error loading environment: {str(e)}[/red]")
        return {}


def check_snow_cli_auth() -> Tuple[bool, str, str]:
    """Check snow CLI authentication status."""
    try:
        result = subprocess.run(
            ["snow", "connection", "list"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_private_key_file(key_path: str) -> Dict[str, Any]:
    """Check private key file validity."""
    if not key_path:
        return {"exists": False, "error": "No private key path specified"}

    key_file = Path(key_path)
    if not key_file.exists():
        return {"exists": False, "error": f"Private key file not found: {key_path}"}

    if not key_file.is_file():
        return {"exists": False, "error": f"Private key path is not a file: {key_path}"}

    # Check file permissions
    stat_info = key_file.stat()
    permissions = oct(stat_info.st_mode)[-3:]

    result = {
        "exists": True,
        "readable": os.access(key_file, os.R_OK),
        "permissions": permissions,
        "size": stat_info.st_size,
    }

    # Check if permissions are secure
    if permissions not in ["600", "400"]:
        result["warning"] = f"Insecure permissions {permissions} - should be 600 or 400"

    return result


def suggest_fixes(
    env_config: Dict[str, Any],
    auth_status: Tuple[bool, str, str],
    key_check: Dict[str, Any],
) -> List[str]:
    """Generate specific fix suggestions based on diagnostics."""
    fixes = []

    # Check authentication method
    has_private_key = env_config["private_key_path"] and key_check.get("exists", False)
    has_password = bool(env_config["password"])

    if not has_private_key and not has_password:
        fixes.append("🔧 **CRITICAL**: No authentication method configured")
        fixes.append(
            "   → Add SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PASSWORD to .env"
        )

    # Private key issues
    if env_config["private_key_path"] and not key_check.get("exists", False):
        fixes.append(
            f"🔧 **Private Key Issue**: {key_check.get('error', 'Unknown error')}"
        )
        fixes.append("   → Check the path in SNOWFLAKE_PRIVATE_KEY_PATH")
        fixes.append("   → Ensure the file exists and is readable")

    if key_check.get("warning"):
        fixes.append(f"🔧 **Security Warning**: {key_check['warning']}")
        fixes.append(f"   → Run: chmod 600 {env_config['private_key_path']}")

    # Snow CLI connection issues
    auth_success, auth_stdout, auth_stderr = auth_status
    if not auth_success:
        fixes.append("🔧 **Snow CLI Authentication Issue**")
        fixes.append("   → Run: snow connection add")
        fixes.append("   → Ensure snow CLI is configured for the same account/user")
        fixes.append("   → Test with: snow sql -q 'SELECT CURRENT_USER()'")

    # JWT token specific issues
    if "JWT token is invalid" in (auth_stderr or ""):
        fixes.append(
            "🔧 **JWT Token Issue** - Likely private key authentication problem"
        )
        fixes.append("   → Verify the private key matches the public key in Snowflake")
        fixes.append(
            "   → Check if passphrase is required (add SNOWFLAKE_PRIVATE_KEY_PASSPHRASE)"
        )
        fixes.append("   → Regenerate key pair if needed")

    # Role and permissions
    if env_config["role"] != "ACCOUNTADMIN":
        fixes.append("🔧 **Role Issue**: SnowDDL requires ACCOUNTADMIN role")
        fixes.append(f"   → Current role: {env_config['role']}")
        fixes.append("   → Change SNOWFLAKE_ROLE=ACCOUNTADMIN in .env")

    return fixes


def main():
    """Main diagnostic function."""
    console = Console()

    console.print(
        Panel(
            "Authentication Diagnostics for SnowTower SnowDDL",
            title="🔍 Auth Diagnostics",
            border_style="blue",
        )
    )

    # Load environment
    console.print("[bold blue]Loading Environment Configuration...[/bold blue]")
    env_config = load_environment()

    # Display environment summary
    env_table = Table(title="Environment Configuration")
    env_table.add_column("Setting", style="bold")
    env_table.add_column("Value")
    env_table.add_column("Status")

    env_table.add_row(
        "Account",
        env_config["account"] or "❌ Missing",
        "✓" if env_config["account"] else "❌",
    )
    env_table.add_row(
        "User", env_config["user"] or "❌ Missing", "✓" if env_config["user"] else "❌"
    )
    env_table.add_row(
        "Role", env_config["role"] or "❌ Missing", "✓" if env_config["role"] else "❌"
    )
    env_table.add_row(
        "Warehouse",
        env_config["warehouse"] or "❌ Missing",
        "✓" if env_config["warehouse"] else "❌",
    )
    env_table.add_row(
        "Private Key",
        env_config["private_key_path"] or "❌ Not set",
        "🔍 Checking..." if env_config["private_key_path"] else "❌",
    )
    env_table.add_row(
        "Password",
        "***" if env_config["password"] else "❌ Not set",
        "✓" if env_config["password"] else "❌",
    )

    console.print(env_table)

    # Check private key if specified
    key_check = {}
    if env_config["private_key_path"]:
        console.print("\n[bold blue]Checking Private Key File...[/bold blue]")
        key_check = check_private_key_file(env_config["private_key_path"])

        key_table = Table(title="Private Key Analysis")
        key_table.add_column("Check", style="bold")
        key_table.add_column("Result")

        key_table.add_row("File Exists", "✓" if key_check.get("exists") else "❌")
        if key_check.get("exists"):
            key_table.add_row("Readable", "✓" if key_check.get("readable") else "❌")
            key_table.add_row(
                "Permissions",
                f"{key_check.get('permissions', 'unknown')} {'⚠️' if key_check.get('warning') else '✓'}",
            )
            key_table.add_row("Size", f"{key_check.get('size', 0)} bytes")

        console.print(key_table)

    # Check snow CLI authentication
    console.print("\n[bold blue]Checking Snow CLI Authentication...[/bold blue]")
    auth_status = check_snow_cli_auth()
    auth_success, auth_stdout, auth_stderr = auth_status

    if auth_success:
        console.print("[green]✓[/green] Snow CLI authentication working")
        if auth_stdout.strip():
            console.print("Connections:")
            console.print(auth_stdout)
    else:
        console.print("[red]❌[/red] Snow CLI authentication failed")
        if auth_stderr:
            console.print(f"Error: {auth_stderr}")

    # Generate and display fixes
    console.print("\n[bold blue]Recommended Fixes...[/bold blue]")
    fixes = suggest_fixes(env_config, auth_status, key_check)

    if fixes:
        fix_content = "\n".join(fixes)
        console.print(
            Panel(fix_content, title="🔧 Remediation Steps", border_style="yellow")
        )
    else:
        console.print(
            "[green]✓ No issues detected - configuration appears correct[/green]"
        )

    # Test command suggestions
    console.print("\n[bold blue]Test Commands[/bold blue]")
    test_commands = [
        "# Test basic connectivity:",
        "uv run investigate-monitors --mode connectivity",
        "",
        "# Test snow CLI directly:",
        "snow sql -q 'SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_ACCOUNT()'",
        "",
        "# Test SnowDDL plan (safe - no changes):",
        "uv run snowddl-plan",
    ]

    console.print(
        Panel("\n".join(test_commands), title="🧪 Next Steps", border_style="green")
    )


if __name__ == "__main__":
    main()
