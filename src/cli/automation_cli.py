#!/usr/bin/env python3
"""
Consolidated automation CLI.

Usage:
    uv run automation github-issue      # Convert GitHub issue to SnowDDL PR
    uv run automation access-request    # Process user access request
"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def show_help():
    """Show automation command help."""
    print(
        """
Automation - GitHub Integration & Workflows

Usage: uv run automation <subcommand>

Subcommands:
    github-issue      Convert GitHub issue to SnowDDL user PR
    access-request    Process user access request from GitHub issue

Examples:
    uv run automation github-issue
    uv run automation access-request

These commands automate the workflow of processing GitHub issues
for user access requests and converting them to SnowDDL configuration PRs.

For detailed help on a subcommand:
    uv run automation <subcommand> --help
"""
    )


def main():
    """Route to appropriate automation subcommand."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    subcommand = sys.argv[1].lower().replace("_", "-")

    # Remove the subcommand from argv so the underlying script sees correct args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if subcommand == "github-issue":
        from github_issue_to_snowddl import main as github_main

        github_main()
    elif subcommand == "access-request":
        from generate_user_from_issue import main as access_main

        access_main()
    elif subcommand in ("--help", "-h", "help"):
        show_help()
    else:
        print(f"Unknown subcommand: {subcommand}")
        print("Run 'uv run automation --help' for available subcommands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
