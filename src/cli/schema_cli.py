#!/usr/bin/env python3
"""
Consolidated schema management CLI.

Usage:
    uv run schema apply      # Apply schema-level USAGE grants
    uv run schema validate   # Validate schema grants configuration
    uv run schema test       # Test schema management
"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def show_help():
    """Show schema command help."""
    print(
        """
Schema - Schema Grant Management

Usage: uv run schema <subcommand>

Subcommands:
    apply       Apply schema-level USAGE grants that SnowDDL cannot manage
    validate    Validate schema grants consistency with tech_role.yaml
    test        Test schema management without exclusions

Examples:
    uv run schema apply
    uv run schema validate
    uv run schema test

Note: SnowDDL excludes SCHEMA objects to avoid conflicts with dbt.
      These commands manage schema grants separately.
      See docs/SCHEMA_GRANTS_WORKAROUND.md for details.

For detailed help on a subcommand:
    uv run schema <subcommand> --help
"""
    )


def main():
    """Route to appropriate schema subcommand."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    subcommand = sys.argv[1].lower()

    # Remove the subcommand from argv so the underlying script sees correct args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if subcommand == "apply":
        from apply_schema_grants import main as apply_main

        apply_main()
    elif subcommand == "validate":
        from validate_schema_grants import main as validate_main

        validate_main()
    elif subcommand == "test":
        from test_schema_management import main as test_main

        test_main()
    elif subcommand in ("--help", "-h", "help"):
        show_help()
    else:
        print(f"Unknown subcommand: {subcommand}")
        print("Run 'uv run schema --help' for available subcommands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
