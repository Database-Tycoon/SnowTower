#!/usr/bin/env python3
"""
Safe SnowDDL deployment wrapper.

This script ensures schema grants are ALWAYS applied after SnowDDL deployment,
preventing the common issue where dbt loses permissions due to SnowDDL's
SCHEMA object exclusion.

Usage:
    uv run deploy-safe                    # Deploy with all safety checks
    uv run deploy-safe --plan-only        # Preview changes only
    uv run deploy-safe --skip-plan        # Skip plan step (not recommended)
    uv run deploy-safe --network-policy   # Include network policy changes
"""

import argparse
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status.

    Args:
        cmd: Command to run as list of strings
        description: Human-readable description of the command

    Returns:
        True if command succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ {description} completed successfully\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}\n")
        return False
    except Exception as e:
        print(f"\n❌ {description} failed with error: {e}\n")
        return False


def main():
    """Execute safe SnowDDL deployment with automatic schema grants."""
    parser = argparse.ArgumentParser(
        description="Safe SnowDDL deployment with automatic schema grants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run deploy-safe                    # Full safe deployment
  uv run deploy-safe --plan-only        # Preview changes only
  uv run deploy-safe --network-policy   # Include network policy changes

Why use this instead of snowddl-apply?
  - Automatically applies schema grants after deployment
  - Prevents dbt permission loss
  - Follows enterprise deployment best practices
  - Matches CI/CD production workflow
        """,
    )

    parser.add_argument(
        "--plan-only", action="store_true", help="Only run plan, do not apply changes"
    )

    parser.add_argument(
        "--skip-plan",
        action="store_true",
        help="Skip plan step (not recommended - use only if you've already reviewed plan)",
    )

    parser.add_argument(
        "--network-policy",
        action="store_true",
        help="Include network policy changes (use with caution)",
    )

    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="Apply unsafe changes (destructive operations)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🛡️  SNOWTOWER SAFE DEPLOYMENT")
    print("=" * 60)
    print("\nThis wrapper ensures schema grants are applied after SnowDDL,")
    print("preventing dbt permission loss due to SCHEMA object exclusion.\n")

    # Step 1: Run plan (unless skipped)
    if not args.skip_plan:
        plan_cmd = ["uv", "run", "snowddl-plan"]
        if not run_command(plan_cmd, "Step 1/3: Generate deployment plan"):
            print("\n⚠️  Plan generation failed. Aborting deployment.\n")
            sys.exit(1)

        if args.plan_only:
            print(
                "\n✅ Plan-only mode: Review the plan above and run without --plan-only to apply.\n"
            )
            return

        # Ask for confirmation
        print("\n" + "=" * 60)
        print("⚠️  DEPLOYMENT CONFIRMATION REQUIRED")
        print("=" * 60)
        response = input("\nReview the plan above. Proceed with deployment? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("\n❌ Deployment cancelled by user.\n")
            sys.exit(0)

    # Step 2: Apply SnowDDL changes
    apply_cmd = ["uv", "run", "snowddl-apply"]

    if args.unsafe:
        apply_cmd.append("--apply-unsafe")

    if args.network_policy:
        apply_cmd.append("--apply-network-policy")
        print("\n⚠️  WARNING: Network policy changes will be applied!")
        print("   This can lock users out if misconfigured!\n")

    # Always apply all other policies
    apply_cmd.append("--apply-all-policy")

    if not run_command(apply_cmd, "Step 2/3: Apply SnowDDL infrastructure changes"):
        print("\n❌ SnowDDL deployment failed. Aborting schema grants.\n")
        print("⚠️  CRITICAL: Your infrastructure may be in an inconsistent state!")
        print("   Run `uv run snowddl-plan` to check current state.\n")
        sys.exit(1)

    # Step 3: Apply schema grants (CRITICAL)
    schema_grants_cmd = ["uv", "run", "apply-schema-grants"]

    if not run_command(schema_grants_cmd, "Step 3/3: Apply schema grants (CRITICAL)"):
        print("\n❌ Schema grants failed!")
        print("\n⚠️  CRITICAL: dbt and other services may have lost schema access!")
        print("   Try running manually: uv run apply-schema-grants\n")
        sys.exit(1)

    # Success!
    print("\n" + "=" * 60)
    print("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\n✅ All steps completed:")
    print("   1. ✅ SnowDDL plan generated and reviewed")
    print("   2. ✅ Infrastructure changes applied")
    print("   3. ✅ Schema grants restored")
    print("\n📊 Your Snowflake infrastructure is now in sync!")
    print("🔐 dbt and all services have correct schema permissions.\n")


if __name__ == "__main__":
    main()
