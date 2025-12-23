#!/usr/bin/env python3
"""
Simple Password Encryption Script for SnowTower User Management

This script provides a quick way to encrypt passwords for YAML configuration files.
It uses the existing FernetEncryption class and reads the Fernet key from environment.

Usage:
    uv run python src/encrypt_password.py "MyPassword123"
    uv run python src/encrypt_password.py --interactive
    uv run python src/encrypt_password.py --help

Examples:
    # Encrypt a specific password
    uv run python src/encrypt_password.py "HeatherSecure2024!@#"

    # Interactive mode with secure prompt
    uv run python src/encrypt_password.py --interactive

    # Generate new Fernet key
    uv run python src/encrypt_password.py --generate-key
"""

import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from user_management.encryption import FernetEncryption, FernetEncryptionError
from env_loader import validate_auth, EnvironmentError
from rich.console import Console
from rich.prompt import Prompt

console = Console()


def encrypt_password(password: str) -> str:
    """
    Encrypt a password using the Fernet key from environment.

    Args:
        password: Plain text password to encrypt

    Returns:
        Encrypted password ready for YAML: !decrypt encrypted_string
    """
    try:
        encryption = FernetEncryption()
        encrypted = encryption.encrypt_password(password)
        return f"!decrypt {encrypted}"
    except FernetEncryptionError as e:
        console.print(f"❌ [red]Encryption failed: {e}[/red]")
        sys.exit(1)


def interactive_encrypt() -> str:
    """Interactive password encryption with prompts."""
    try:
        encryption = FernetEncryption()
        encrypted = encryption.interactive_encrypt()
        return f"!decrypt {encrypted}" if encrypted else ""
    except FernetEncryptionError as e:
        console.print(f"❌ [red]Encryption failed: {e}[/red]")
        sys.exit(1)


def generate_key() -> str:
    """Generate a new Fernet encryption key."""
    key = FernetEncryption.generate_key()
    console.print(f"🔑 [green]New Fernet Key Generated:[/green]")
    console.print(f"[cyan]{key}[/cyan]")
    console.print("\n📝 [yellow]Add this to your .env file:[/yellow]")
    console.print(f"[cyan]SNOWFLAKE_CONFIG_FERNET_KEYS={key}[/cyan]")
    return key


def main():
    # Validate environment configuration (particularly Fernet keys)
    try:
        from env_loader import load_snowflake_env

        load_snowflake_env(validate_auth=False)  # Only validate required vars, not auth
        console.print("✓ [green]Environment configuration validated[/green]")
    except EnvironmentError as e:
        if "SNOWFLAKE_CONFIG_FERNET_KEYS" in str(e):
            console.print(
                "❌ [red]Missing SNOWFLAKE_CONFIG_FERNET_KEYS environment variable[/red]"
            )
            console.print(
                "💡 [yellow]Run with --generate-key to create a new key[/yellow]"
            )
        else:
            console.print(f"⚠️ [yellow]Environment validation warning: {e}[/yellow]")
    except Exception as e:
        console.print(f"⚠️ [yellow]Environment check failed: {e}[/yellow]")

    parser = argparse.ArgumentParser(
        description="Encrypt passwords for SnowTower YAML configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python src/encrypt_password.py "MyPassword123"
  uv run python src/encrypt_password.py --interactive
  uv run python src/encrypt_password.py --generate-key
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "password",
        nargs="?",
        help="Password to encrypt (use quotes for special characters)",
    )
    group.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode with secure password prompt",
    )
    group.add_argument(
        "--generate-key",
        "-g",
        action="store_true",
        help="Generate a new Fernet encryption key",
    )

    args = parser.parse_args()

    if args.generate_key:
        generate_key()
    elif args.interactive:
        result = interactive_encrypt()
        if result:
            console.print(f"\n📋 [green]Copy this to your YAML file:[/green]")
            console.print(f"[cyan]password: {result}[/cyan]")
    elif args.password:
        result = encrypt_password(args.password)
        console.print(f"🔐 [green]Encrypted password:[/green]")
        console.print(f"[cyan]{result}[/cyan]")
        console.print(f"\n📋 [green]Copy this to your YAML file:[/green]")
        console.print(f"[cyan]password: {result}[/cyan]")


if __name__ == "__main__":
    main()
