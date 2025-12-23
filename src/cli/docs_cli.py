#!/usr/bin/env python3
"""
Consolidated documentation CLI.

Usage:
    uv run docs serve        # Serve docs locally
    uv run docs build        # Build documentation
    uv run docs api          # Generate API docs
    uv run docs serve-api    # Serve API docs
"""

import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))


def show_help():
    """Show docs command help."""
    print(
        """
Docs - Documentation Management

Usage: uv run docs <subcommand>

Subcommands:
    serve       Serve documentation locally (MkDocs)
    build       Build documentation for deployment
    api         Generate API documentation
    serve-api   Serve API documentation locally

Examples:
    uv run docs serve
    uv run docs build
    uv run docs api

For detailed help on a subcommand:
    uv run docs <subcommand> --help
"""
    )


def main():
    """Route to appropriate documentation subcommand."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    subcommand = sys.argv[1].lower()

    # Remove the subcommand from argv so the underlying script sees correct args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if subcommand == "serve":
        from docs_commands import serve_docs

        serve_docs()
    elif subcommand == "build":
        from docs_commands import build_docs

        build_docs()
    elif subcommand == "api":
        from docs_commands import generate_api_docs

        generate_api_docs()
    elif subcommand == "serve-api":
        from docs_commands import serve_api_docs

        serve_api_docs()
    elif subcommand in ("--help", "-h", "help"):
        show_help()
    else:
        print(f"Unknown subcommand: {subcommand}")
        print("Run 'uv run docs --help' for available subcommands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
