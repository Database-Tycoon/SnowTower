#!/usr/bin/env python3
"""
Unified User Creation Script for SnowTower SnowDDL

This is the consolidated, primary command for creating new Snowflake users.
It replaces multiple scattered scripts with a single, consistent interface.

Usage:
    # Interactive mode (recommended)
    uv run user-create

    # Non-interactive mode
    uv run user-create --first-name John --last-name Doe --email john.doe@company.com

    # With all options
    uv run user-create \\
        --first-name John \\
        --last-name Doe \\
        --email john.doe@company.com \\
        --username JOHN_DOE \\
        --user-type PERSON \\
        --default-role ANALYST_ROLE \\
        --default-warehouse COMPUTE_WH \\
        --generate-rsa \\
        --auto-password

Environment Variables:
    SNOWFLAKE_CONFIG_FERNET_KEYS: Required for password encryption
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Load environment variables FIRST
from dotenv import load_dotenv

load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.panel import Panel

from user_management.manager import UserManager, UserType, UserCreationError
from user_management.encryption import FernetEncryption

console = Console()


def validate_environment() -> bool:
    """Validate that required environment variables are set"""
    try:
        encryption = FernetEncryption()
        if encryption._fernet is None:
            console.print(
                "[red]Error: SNOWFLAKE_CONFIG_FERNET_KEYS environment variable not set[/red]"
            )
            console.print("\nTo set up encryption:")
            console.print("1. Generate a key: [cyan]uv run util-generate-key[/cyan]")
            console.print(
                "2. Set environment variable: [cyan]export SNOWFLAKE_CONFIG_FERNET_KEYS='your-key'[/cyan]"
            )
            console.print(
                "3. Or add to .env file: [cyan]SNOWFLAKE_CONFIG_FERNET_KEYS=your-key[/cyan]"
            )
            return False
        return True
    except Exception as e:
        console.print(f"[red]Environment validation failed: {e}[/red]")
        return False


def main():
    """Main entry point for unified user creation"""
    parser = argparse.ArgumentParser(
        description="Unified User Creation for SnowTower SnowDDL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Basic user information
    parser.add_argument("--first-name", "-f", help="User's first name")
    parser.add_argument("--last-name", "-l", help="User's last name")
    parser.add_argument("--email", "-e", help="User's email address")
    parser.add_argument(
        "--username", "-u", help="Username (auto-generated from name if not provided)"
    )

    # User type and roles
    parser.add_argument(
        "--user-type",
        "-t",
        choices=["PERSON", "SERVICE"],
        default="PERSON",
        help="User type (default: PERSON)",
    )
    parser.add_argument("--default-role", "-r", help="Default role for the user")
    parser.add_argument(
        "--default-warehouse",
        "-w",
        default="COMPUTE_WH",
        help="Default warehouse (default: COMPUTE_WH)",
    )

    # Authentication options
    parser.add_argument(
        "--generate-rsa",
        "--rsa",
        action="store_true",
        default=True,
        help="Generate RSA key pair (default: True)",
    )
    parser.add_argument("--no-rsa", action="store_true", help="Skip RSA key generation")
    parser.add_argument(
        "--auto-password",
        "--auto-pwd",
        action="store_true",
        default=True,
        help="Automatically generate secure password (default: True)",
    )
    parser.add_argument(
        "--no-password", action="store_true", help="Skip password generation (RSA only)"
    )
    parser.add_argument(
        "--password-length",
        type=int,
        default=16,
        help="Password length for auto-generation (default: 16)",
    )

    # Mode selection
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Force interactive mode (default if no arguments provided)",
    )
    parser.add_argument(
        "--batch",
        "--non-interactive",
        action="store_true",
        help="Force non-interactive mode",
    )

    # Configuration
    parser.add_argument(
        "--config-dir",
        "-c",
        type=Path,
        help="SnowDDL configuration directory (default: ./snowddl)",
    )

    args = parser.parse_args()

    # Display banner
    console.print(
        Panel(
            "[bold blue]SnowTower User Creation Tool[/bold blue]\n\n"
            "Unified command for creating Snowflake users with secure authentication",
            border_style="blue",
        )
    )

    # Validate environment
    if not validate_environment():
        return 1

    try:
        # Initialize UserManager
        manager = UserManager(args.config_dir)

        # Determine mode: interactive if no user details provided
        interactive = args.interactive or (
            not args.batch and not all([args.first_name, args.last_name, args.email])
        )

        if interactive:
            # Interactive mode
            console.print("\n[cyan]Starting interactive user creation...[/cyan]\n")
            result = manager.create_user(interactive=True)

            if not result:
                console.print("[yellow]User creation cancelled[/yellow]")
                return 0

        else:
            # Non-interactive mode
            if not all([args.first_name, args.last_name, args.email]):
                console.print(
                    "[red]Error: --first-name, --last-name, and --email are required for non-interactive mode[/red]"
                )
                console.print("Tip: Run without arguments for interactive mode")
                return 1

            # Prepare user data
            user_data = {
                "first_name": args.first_name,
                "last_name": args.last_name,
                "email": args.email,
                "user_type": UserType(args.user_type),
                "default_warehouse": args.default_warehouse,
                "auto_generate_password": args.auto_password and not args.no_password,
                "password_length": args.password_length,
            }

            if args.username:
                user_data["username"] = args.username
            if args.default_role:
                user_data["default_role"] = args.default_role

            # Handle RSA key generation flag
            if args.no_rsa:
                user_data["generate_rsa"] = False

            console.print("\n[cyan]Creating user in non-interactive mode...[/cyan]\n")
            result = manager.create_user(interactive=False, **user_data)

        # Success!
        console.print(
            "\n[bold green]User creation completed successfully![/bold green]"
        )

        # Show next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("1. Review the configuration: [cyan]snowddl/user.yaml[/cyan]")
        console.print("2. Plan deployment: [cyan]uv run snowddl-plan[/cyan]")
        console.print("3. Apply changes: [cyan]uv run snowddl-apply[/cyan]")
        console.print("4. Verify user: [cyan]uv run user-manage list[/cyan]")

        return 0

    except UserCreationError as e:
        console.print(f"\n[red]User creation failed: {e}[/red]")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]User creation cancelled by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
