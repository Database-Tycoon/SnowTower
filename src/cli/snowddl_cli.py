#!/usr/bin/env python3
"""
Consolidated SnowDDL infrastructure CLI.

Usage:
    uv run snowddl plan              # Preview changes
    uv run snowddl apply             # Apply changes
    uv run snowddl apply --safe      # Apply with schema grants
    uv run snowddl validate          # Validate YAML
    uv run snowddl diff              # Show differences
"""

import sys
from pathlib import Path

# Add src and scripts directories to path
src_dir = Path(__file__).parent.parent
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(scripts_dir))


def show_help():
    """Show snowddl command help."""
    print(
        """
SnowDDL - Infrastructure Operations

Usage: uv run snowddl <subcommand> [options]

Subcommands:
    plan        Preview infrastructure changes (always run first!)
    apply       Apply infrastructure changes to Snowflake
    validate    Validate YAML configuration files
    diff        Show differences between local and Snowflake

Options for 'apply':
    --safe      Apply changes AND restore schema grants (recommended)
                Equivalent to old 'deploy-safe' command

Examples:
    uv run snowddl plan              # Preview changes
    uv run snowddl apply             # Apply changes
    uv run snowddl apply --safe      # Apply + restore schema grants
    uv run snowddl validate          # Validate config
    uv run snowddl diff              # Show differences

IMPORTANT: Always run 'plan' before 'apply' to review changes!

For detailed help on a subcommand:
    uv run snowddl <subcommand> --help
"""
    )


def main():
    """Route to appropriate snowddl subcommand."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    subcommand = sys.argv[1].lower()

    # Check for --safe flag on apply
    safe_mode = "--safe" in sys.argv

    # Remove the subcommand (and --safe if present) from argv
    remaining_args = [arg for arg in sys.argv[2:] if arg != "--safe"]
    sys.argv = [sys.argv[0]] + remaining_args

    if subcommand == "plan":
        from snowtower_snowddl.cli import plan

        plan()
    elif subcommand == "apply":
        if safe_mode:
            # Safe mode: apply then restore schema grants
            from deploy_safe import main as deploy_safe_main

            deploy_safe_main()
        else:
            from snowtower_snowddl.cli import apply

            apply()
    elif subcommand == "validate":
        from snowtower_snowddl.cli import validate_config

        validate_config()
    elif subcommand == "diff":
        from snowtower_snowddl.cli import diff

        diff()
    elif subcommand in ("--help", "-h", "help"):
        show_help()
    else:
        print(f"Unknown subcommand: {subcommand}")
        print("Run 'uv run snowddl --help' for available subcommands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
