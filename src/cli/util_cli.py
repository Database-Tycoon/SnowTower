#!/usr/bin/env python3
"""
Consolidated utilities CLI.

Usage:
    uv run util generate-key     # Generate Fernet encryption key
    uv run util diagnose-auth    # Diagnose authentication issues
    uv run util fix-auth         # Fix authentication problems
    uv run util generate-rsa     # Batch RSA key generation
    uv run util setup-github     # Set up GitHub token
"""

import sys
from pathlib import Path

# Add scripts and src directories to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(src_dir))


def show_help():
    """Show util command help."""
    print(
        """
Util - Utility Commands

Usage: uv run util <subcommand>

Subcommands:
    generate-key     Generate a new Fernet encryption key
    diagnose-auth    Diagnose Snowflake authentication issues
    fix-auth         Fix authentication problems automatically
    generate-rsa     Batch generate RSA keys for multiple users
    setup-github     Set up GitHub token for automation

Examples:
    uv run util generate-key
    uv run util diagnose-auth
    uv run util fix-auth
    uv run util generate-rsa
    uv run util setup-github

For detailed help on a subcommand:
    uv run util <subcommand> --help
"""
    )


def main():
    """Route to appropriate utility subcommand."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    subcommand = sys.argv[1].lower().replace("_", "-")

    # Remove the subcommand from argv so the underlying script sees correct args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if subcommand == "generate-key":
        from user_management.cli import generate_fernet_key

        generate_fernet_key()
    elif subcommand == "diagnose-auth":
        from diagnose_auth import main as diagnose_main

        diagnose_main()
    elif subcommand == "fix-auth":
        from fix_auth import main as fix_main

        fix_main()
    elif subcommand == "generate-rsa":
        from generate_rsa_keys_batch import main as rsa_main

        rsa_main()
    elif subcommand == "setup-github":
        from setup_github_token import main as github_main

        github_main()
    elif subcommand in ("--help", "-h", "help"):
        show_help()
    else:
        print(f"Unknown subcommand: {subcommand}")
        print("Run 'uv run util --help' for available subcommands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
