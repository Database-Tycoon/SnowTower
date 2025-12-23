#!/usr/bin/env python3
"""
Test script for SnowDDL schema management without exclusion.

This script tests whether SnowDDL can successfully manage SCHEMA objects
when --exclude-object-types SCHEMA is removed.

Usage:
    uv run test-schema-mgmt
"""

import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def run_snowddl_plan(exclude_schema: bool = True) -> tuple[int, str, str]:
    """
    Run SnowDDL plan command with or without SCHEMA exclusion.

    Args:
        exclude_schema: If True, excludes SCHEMA objects (current behavior)
                       If False, includes SCHEMA objects (testing new behavior)

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    config_path = Path("snowddl")

    # Build command - options go BEFORE action in snowddl CLI
    # Must use -r ACCOUNTADMIN to see all grants across roles/schemas
    # NOTE: Do NOT use --env-prefix as it prefixes object names, not env var names
    cmd = [
        "snowddl",
        "-c",
        str(config_path),
        "-r",
        "ACCOUNTADMIN",
    ]

    # Add exclusions
    if exclude_schema:
        cmd.extend(["--exclude-object-types", "PIPE,STREAM,TASK,SCHEMA"])
        print("🔍 Testing WITH schema exclusion (current behavior)...")
    else:
        cmd.extend(["--exclude-object-types", "PIPE,STREAM,TASK"])
        print("🔍 Testing WITHOUT schema exclusion (new behavior)...")

    # Action comes last
    cmd.append("plan")

    # Run command - pass environment so dotenv vars are available
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, env=os.environ
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out after 60 seconds"
    except Exception as e:
        return -1, "", str(e)


def analyze_plan_output(stdout: str, stderr: str, exclude_schema: bool) -> dict:
    """
    Analyze SnowDDL plan output for key indicators.

    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "success": False,
        "schema_creates": 0,
        "schema_drops": 0,
        "schema_grants": 0,
        "schema_revokes": 0,
        "errors": [],
        "warnings": [],
    }

    combined = stdout + "\n" + stderr
    lines = combined.split("\n")

    for line in lines:
        line_upper = line.upper()

        # Count schema operations
        if "CREATE SCHEMA" in line_upper:
            analysis["schema_creates"] += 1
        if "DROP SCHEMA" in line_upper:
            analysis["schema_drops"] += 1
        if "GRANT" in line_upper and "SCHEMA" in line_upper:
            analysis["schema_grants"] += 1
        if "REVOKE" in line_upper and "SCHEMA" in line_upper:
            analysis["schema_revokes"] += 1

        # Detect errors
        if "ERROR" in line_upper or "FAILED" in line_upper:
            analysis["errors"].append(line.strip())

        # Detect warnings
        if "WARNING" in line_upper or "WARN" in line_upper:
            analysis["warnings"].append(line.strip())

    # Success if no errors
    analysis["success"] = len(analysis["errors"]) == 0

    return analysis


def print_analysis(analysis: dict, exclude_schema: bool):
    """Print analysis results in a readable format."""
    mode = "WITH exclusion" if exclude_schema else "WITHOUT exclusion"

    print(f"\n{'='*60}")
    print(f"Analysis: {mode}")
    print(f"{'='*60}")

    if analysis["success"]:
        print("✅ Command executed successfully")
    else:
        print("❌ Command failed with errors")

    print(f"\n📊 Schema Operations Detected:")
    print(f"  - CREATE SCHEMA: {analysis['schema_creates']}")
    print(f"  - DROP SCHEMA: {analysis['schema_drops']}")
    print(f"  - GRANT on SCHEMA: {analysis['schema_grants']}")
    print(f"  - REVOKE on SCHEMA: {analysis['schema_revokes']}")

    if analysis["errors"]:
        print(f"\n❌ Errors ({len(analysis['errors'])}):")
        for error in analysis["errors"][:5]:  # Show first 5
            print(f"  - {error}")
        if len(analysis["errors"]) > 5:
            print(f"  ... and {len(analysis['errors']) - 5} more")

    if analysis["warnings"]:
        print(f"\n⚠️  Warnings ({len(analysis['warnings'])}):")
        for warning in analysis["warnings"][:5]:  # Show first 5
            print(f"  - {warning}")
        if len(analysis["warnings"]) > 5:
            print(f"  ... and {len(analysis['warnings']) - 5} more")


def main():
    """Main test execution."""
    print("🧪 SnowDDL Schema Management Test")
    print("=" * 60)
    print("\nThis test compares SnowDDL behavior with and without")
    print("SCHEMA object exclusion to validate the migration plan.\n")

    # Test 1: Current behavior (with exclusion)
    print("\n" + "=" * 60)
    print("TEST 1: Current Behavior (--exclude-object-types SCHEMA)")
    print("=" * 60)

    code1, stdout1, stderr1 = run_snowddl_plan(exclude_schema=True)
    analysis1 = analyze_plan_output(stdout1, stderr1, exclude_schema=True)
    print_analysis(analysis1, exclude_schema=True)

    # Test 2: New behavior (without exclusion)
    print("\n" + "=" * 60)
    print("TEST 2: New Behavior (SCHEMA objects managed)")
    print("=" * 60)

    code2, stdout2, stderr2 = run_snowddl_plan(exclude_schema=False)
    analysis2 = analyze_plan_output(stdout2, stderr2, exclude_schema=False)
    print_analysis(analysis2, exclude_schema=False)

    # Comparison
    print("\n" + "=" * 60)
    print("COMPARISON: Key Differences")
    print("=" * 60)

    print(f"\n📈 Schema Creates:")
    print(f"  - With exclusion: {analysis1['schema_creates']}")
    print(f"  - Without exclusion: {analysis2['schema_creates']}")
    delta_creates = analysis2["schema_creates"] - analysis1["schema_creates"]
    if delta_creates > 0:
        print(f"  ✅ {delta_creates} schemas would be created by SnowDDL")

    print(f"\n📉 Schema Revokes (drift warnings):")
    print(f"  - With exclusion: {analysis1['schema_revokes']}")
    print(f"  - Without exclusion: {analysis2['schema_revokes']}")
    delta_revokes = analysis1["schema_revokes"] - analysis2["schema_revokes"]
    if delta_revokes > 0:
        print(f"  ✅ {delta_revokes} fewer drift warnings!")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    if analysis2["success"] and analysis2["schema_creates"] > 0:
        print("\n✅ SnowDDL CAN manage SCHEMA objects successfully!")
        print("   - Schemas are created from YAML definitions")
        print("   - Ready to proceed with migration plan")
    else:
        print("\n⚠️  Issues detected with schema management:")
        if analysis2["errors"]:
            print("   - Errors occurred (see above)")
        if analysis2["schema_creates"] == 0:
            print("   - No schemas created (check YAML configuration)")

    if delta_revokes > 0:
        print(
            f"\n🎉 Removing SCHEMA exclusion eliminates {delta_revokes} drift warnings!"
        )

    # Save detailed output for review
    output_dir = Path("test-output")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "plan_with_exclusion.txt", "w") as f:
        f.write(f"STDOUT:\n{stdout1}\n\nSTDERR:\n{stderr1}")

    with open(output_dir / "plan_without_exclusion.txt", "w") as f:
        f.write(f"STDOUT:\n{stdout2}\n\nSTDERR:\n{stderr2}")

    print(f"\n📁 Detailed output saved to:")
    print(f"   - {output_dir}/plan_with_exclusion.txt")
    print(f"   - {output_dir}/plan_without_exclusion.txt")

    # Exit code
    if analysis2["success"]:
        print("\n✅ Test completed successfully")
        return 0
    else:
        print("\n❌ Test failed - review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
