#!/usr/bin/env python3
"""
Intelligent SnowDDL apply wrapper that detects what changes are needed
and only applies the necessary flags.
"""

import subprocess
import re
import sys
from pathlib import Path
from typing import Set, List, Dict
from rich.console import Console

console = Console()


def run_snowddl_plan(config_root: Path) -> str:
    """Run snowddl plan and return the output."""
    try:
        result = subprocess.run(
            ["snowddl", "-c", str(config_root), "plan"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout + result.stderr
    except Exception as e:
        console.print(f"❌ Error running plan: {e}")
        return ""


def detect_object_types(plan_output: str) -> Dict[str, bool]:
    """Detect which object types have changes based on plan output."""

    # Patterns to detect different object types in the plan
    patterns = {
        "resource_monitor": [
            r"CREATE RESOURCE MONITOR",
            r"ALTER RESOURCE MONITOR",
            r"DROP RESOURCE MONITOR",
            r"Resolved RESOURCE_MONITOR",
        ],
        "network_policy": [
            r"CREATE NETWORK POLICY",
            r"ALTER NETWORK POLICY",
            r"DROP NETWORK POLICY",
            r"Resolved NETWORK_POLICY",
        ],
        "authentication_policy": [
            r"CREATE AUTHENTICATION POLICY",
            r"ALTER AUTHENTICATION POLICY",
            r"Resolved AUTHENTICATION_POLICY",
        ],
        "password_policy": [
            r"CREATE PASSWORD POLICY",
            r"ALTER PASSWORD POLICY",
            r"Resolved PASSWORD_POLICY",
        ],
        "session_policy": [
            r"CREATE SESSION POLICY",
            r"ALTER SESSION POLICY",
            r"Resolved SESSION_POLICY",
        ],
        "masking_policy": [
            r"CREATE MASKING POLICY",
            r"ALTER MASKING POLICY",
            r"Resolved MASKING_POLICY",
        ],
        "row_access_policy": [
            r"CREATE ROW ACCESS POLICY",
            r"ALTER ROW ACCESS POLICY",
            r"Resolved ROW_ACCESS_POLICY",
        ],
        "aggregation_policy": [
            r"CREATE AGGREGATION POLICY",
            r"ALTER AGGREGATION POLICY",
            r"Resolved AGGREGATION_POLICY",
        ],
        "projection_policy": [
            r"CREATE PROJECTION POLICY",
            r"ALTER PROJECTION POLICY",
            r"Resolved PROJECTION_POLICY",
        ],
        "account_params": [r"ALTER ACCOUNT SET", r"Resolved ACCOUNT_PARAMS"],
        "outbound_share": [r"CREATE SHARE", r"ALTER SHARE", r"Resolved OUTBOUND_SHARE"],
        "unsafe_changes": [
            r"DROP ",
            r"REPLACE TABLE",
            r"ALTER COLUMN.*DROP",
            r"TRUNCATE",
        ],
        "user_passwords": [r"ALTER USER.*SET PASSWORD", r"password.*refresh"],
    }

    detected = {}
    for obj_type, pattern_list in patterns.items():
        detected[obj_type] = any(
            re.search(pattern, plan_output, re.IGNORECASE) for pattern in pattern_list
        )

    return detected


def build_apply_flags(detected_types: Dict[str, bool]) -> List[str]:
    """Build the list of apply flags based on detected changes."""
    flags = []

    # Map detected types to their corresponding flags
    flag_mapping = {
        "resource_monitor": "--apply-resource-monitor",
        "network_policy": "--apply-network-policy",
        "authentication_policy": "--apply-authentication-policy",
        "masking_policy": "--apply-masking-policy",
        "row_access_policy": "--apply-row-access-policy",
        "aggregation_policy": "--apply-aggregation-policy",
        "projection_policy": "--apply-projection-policy",
        "account_params": "--apply-account-params",
        "outbound_share": "--apply-outbound-share",
        "unsafe_changes": "--apply-unsafe",
        "user_passwords": "--refresh-user-passwords",
    }

    # Check if any policy type is detected
    policy_types = [
        "password_policy",
        "session_policy",
        "authentication_policy",
        "masking_policy",
        "row_access_policy",
        "aggregation_policy",
        "projection_policy",
    ]

    if any(detected_types.get(pt, False) for pt in policy_types):
        flags.append("--apply-all-policy")

    # Add specific flags for detected types
    for obj_type, flag in flag_mapping.items():
        if detected_types.get(obj_type, False) and flag not in flags:
            flags.append(flag)

    return flags


def intelligent_apply(config_root: Path, force_flags: List[str] = None):
    """
    Intelligently apply SnowDDL changes by detecting what needs to be applied.

    Args:
        config_root: Path to the SnowDDL configuration directory
        force_flags: Optional list of flags to force inclusion
    """
    console.print("🧠 [bold blue]Running Intelligent SnowDDL Apply[/bold blue]")
    console.print("=" * 50)

    # Step 1: Run plan to detect changes
    console.print("📋 Analyzing changes needed...")
    plan_output = run_snowddl_plan(config_root)

    if not plan_output:
        console.print("❌ Could not get plan output")
        return False

    # Step 2: Detect object types with changes
    detected = detect_object_types(plan_output)

    # Step 3: Report what was detected
    console.print("\n🔍 [bold]Detected Changes:[/bold]")
    changes_found = False
    for obj_type, has_changes in detected.items():
        if has_changes:
            changes_found = True
            console.print(f"  ✓ {obj_type.replace('_', ' ').title()}")

    if not changes_found:
        console.print("  ℹ️  No special object types detected (standard objects only)")

    # Step 4: Build appropriate flags
    flags = build_apply_flags(detected)

    # Add any forced flags
    if force_flags:
        for flag in force_flags:
            if flag not in flags:
                flags.append(flag)

    # Step 5: Build the command
    role = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
    cmd = [
        "snowddl",
        "-c",
        str(config_root),
        "-r",
        role,
        "--exclude-object-types",
        "PIPE,STREAM,TASK",  # SCHEMA now managed by SnowDDL
    ]

    # Add detected flags
    cmd.extend(flags)
    cmd.append("apply")

    # Step 6: Show what will be run
    console.print("\n🚀 [bold]Apply Command:[/bold]")
    console.print(f"  [cyan]{' '.join(cmd)}[/cyan]")

    console.print("\n📝 [bold]Flags Applied:[/bold]")
    if flags:
        for flag in flags:
            console.print(f"  • {flag}")
    else:
        console.print("  • (none - standard objects only)")

    # Step 7: Ask for confirmation
    if not force_flags or "--yes" not in force_flags:
        response = input("\n❓ Proceed with apply? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            console.print("❌ Apply cancelled")
            return False

    # Step 8: Execute the command
    console.print("\n⚙️  Executing apply...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.stdout:
            console.print("\n📄 Output:")
            print(result.stdout)

        if result.stderr:
            console.print("\n⚠️  Warnings/Errors:")
            print(result.stderr)

        if result.returncode == 0:
            console.print("\n✅ [green]Apply completed successfully![/green]")
            return True
        else:
            console.print(f"\n❌ Apply failed with return code {result.returncode}")
            return False

    except Exception as e:
        console.print(f"\n❌ Error executing apply: {e}")
        return False


def main():
    """Main entry point for intelligent apply."""
    import os

    # Get config root
    current_dir = Path.cwd()
    config_dir = current_dir / "snowddl"

    if not config_dir.exists():
        console.print(f"❌ SnowDDL configuration directory not found at {config_dir}")
        sys.exit(1)

    # Check for force flags from command line
    force_flags = []
    if "--apply-unsafe" in sys.argv:
        force_flags.append("--apply-unsafe")
    if "--yes" in sys.argv or "-y" in sys.argv:
        force_flags.append("--yes")

    # Run intelligent apply
    success = intelligent_apply(config_dir, force_flags)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
