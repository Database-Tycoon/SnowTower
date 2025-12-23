#!/usr/bin/env python3
"""
Standalone Password Generation Script

Generate secure passwords for SnowFlake users with automatic Fernet encryption.
This script can be used independently or integrated into other workflows.

Features:
- Cryptographically secure password generation
- Automatic Fernet encryption for SnowDDL YAML files
- Bulk password generation for multiple users
- Password strength validation
- Rich terminal output with formatted results

Usage:
    python generate_passwords.py --username JOHN_DOE
    python generate_passwords.py --bulk --usernames "USER1,USER2,USER3"
    python generate_passwords.py --csv-file users.csv

Environment Variables:
    SNOWFLAKE_CONFIG_FERNET_KEYS: Required for password encryption
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from user_management.password_generator import (
    PasswordGenerator,
    PasswordGenerationError,
)
from user_management.encryption import FernetEncryption

console = Console()


def generate_single_password(
    username: str, user_type: str = "PERSON", length: int = 16, **kwargs
) -> Dict[str, Any]:
    """Generate password for a single user"""
    try:
        generator = PasswordGenerator()
        password_info = generator.generate_user_password(
            username=username, user_type=user_type, length=length
        )

        console.print(f"✅ [green]Password generated for {username}[/green]")
        return password_info

    except PasswordGenerationError as e:
        console.print(f"❌ [red]Failed to generate password for {username}: {e}[/red]")
        return {}


def generate_bulk_passwords(
    usernames: List[str], user_type: str = "PERSON", length: int = 16
) -> Dict[str, Dict[str, Any]]:
    """Generate passwords for multiple users"""
    try:
        generator = PasswordGenerator()
        passwords = generator.generate_multiple_passwords(
            usernames=usernames, user_type=user_type, length=length
        )

        console.print(
            f"✅ [green]Generated passwords for {len(passwords)} users[/green]"
        )
        return passwords

    except PasswordGenerationError as e:
        console.print(f"❌ [red]Bulk password generation failed: {e}[/red]")
        return {}


def display_password_table(passwords: Dict[str, Dict[str, Any]]) -> None:
    """Display passwords in a formatted table"""
    if not passwords:
        console.print("❌ [red]No passwords to display[/red]")
        return

    table = Table(title=f"Generated Passwords ({len(passwords)} users)")
    table.add_column("Username", style="cyan", width=15)
    table.add_column("User Type", style="blue", width=8)
    table.add_column("Plain Password", style="red", width=20)
    table.add_column("YAML Value", style="dim", width=50)
    table.add_column("Length", style="green", width=6)

    for username, info in passwords.items():
        yaml_value = info["yaml_value"]
        if len(yaml_value) > 47:
            yaml_value = yaml_value[:47] + "..."

        table.add_row(
            username,
            info["user_type"],
            info["plain_password"],
            yaml_value,
            str(info["length"]),
        )

    console.print(table)


def export_passwords_to_file(
    passwords: Dict[str, Dict[str, Any]], output_file: Path, format: str = "json"
) -> None:
    """Export passwords to file"""
    try:
        if format.lower() == "json":
            with open(output_file, "w") as f:
                json.dump(passwords, f, indent=2)
        elif format.lower() == "csv":
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Username",
                        "User Type",
                        "Plain Password",
                        "YAML Value",
                        "Generated At",
                    ]
                )

                for username, info in passwords.items():
                    writer.writerow(
                        [
                            username,
                            info["user_type"],
                            info["plain_password"],
                            info["yaml_value"],
                            info["generated_at"],
                        ]
                    )
        else:
            raise ValueError(f"Unsupported export format: {format}")

        console.print(f"✅ [green]Passwords exported to {output_file}[/green]")

    except Exception as e:
        console.print(f"❌ [red]Failed to export passwords: {e}[/red]")


def load_usernames_from_csv(csv_file: Path) -> List[str]:
    """Load usernames from CSV file"""
    usernames = []

    try:
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():  # Skip empty rows
                    usernames.append(row[0].strip())

        console.print(
            f"📄 [blue]Loaded {len(usernames)} usernames from {csv_file}[/blue]"
        )
        return usernames

    except Exception as e:
        console.print(f"❌ [red]Failed to load usernames from CSV: {e}[/red]")
        return []


def validate_fernet_key() -> bool:
    """Validate that Fernet encryption is available"""
    try:
        encryption = FernetEncryption()
        if encryption._fernet is None:
            console.print("❌ [red]No Fernet encryption key available![/red]")
            console.print("\nTo set up encryption:")
            console.print("1. Generate a key: [cyan]uv run util-generate-key[/cyan]")
            console.print(
                "2. Set environment variable: [cyan]export SNOWFLAKE_CONFIG_FERNET_KEYS='your-key'[/cyan]"
            )
            return False
        return True
    except Exception as e:
        console.print(f"❌ [red]Encryption validation failed: {e}[/red]")
        return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Generate secure passwords for SnowFlake users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # User specification
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument(
        "--username", "-u", help="Single username to generate password for"
    )
    user_group.add_argument(
        "--usernames",
        "-U",
        help="Comma-separated list of usernames for bulk generation",
    )
    user_group.add_argument(
        "--csv-file",
        "-f",
        type=Path,
        help="CSV file containing usernames (one per line)",
    )

    # Password options
    parser.add_argument(
        "--length",
        "-l",
        type=int,
        default=16,
        help="Password length (minimum 12, default 16)",
    )
    parser.add_argument(
        "--user-type",
        "-t",
        choices=["PERSON", "SERVICE"],
        default="PERSON",
        help="User type for all generated passwords",
    )
    parser.add_argument(
        "--no-symbols", action="store_true", help="Exclude symbols from passwords"
    )
    parser.add_argument(
        "--no-ambiguous",
        action="store_true",
        help="Exclude ambiguous characters (0, O, l, I, etc.)",
    )

    # Output options
    parser.add_argument(
        "--export",
        "-e",
        type=Path,
        help="Export passwords to file (JSON or CSV based on extension)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Export format (default: json)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Quiet mode - minimal output"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.length < 12:
        console.print("❌ [red]Password length must be at least 12 characters[/red]")
        return 1

    # Validate Fernet encryption
    if not validate_fernet_key():
        return 1

    # Determine usernames
    usernames = []

    if args.username:
        usernames = [args.username]
    elif args.usernames:
        usernames = [u.strip() for u in args.usernames.split(",")]
    elif args.csv_file:
        if not args.csv_file.exists():
            console.print(f"❌ [red]CSV file not found: {args.csv_file}[/red]")
            return 1
        usernames = load_usernames_from_csv(args.csv_file)

    if not usernames:
        console.print("❌ [red]No usernames specified[/red]")
        return 1

    if not args.quiet:
        console.print(
            f"🔐 [blue]Generating passwords for {len(usernames)} user(s)[/blue]"
        )
        console.print(f"📏 [dim]Length: {args.length} characters[/dim]")
        console.print(f"👤 [dim]User type: {args.user_type}[/dim]")
        console.print()

    # Generate passwords
    if len(usernames) == 1:
        password_info = generate_single_password(
            username=usernames[0],
            user_type=args.user_type,
            length=args.length,
            include_symbols=not args.no_symbols,
            exclude_ambiguous=args.no_ambiguous,
        )

        if not password_info:
            return 1

        passwords = {usernames[0]: password_info}
    else:
        passwords = generate_bulk_passwords(
            usernames=usernames, user_type=args.user_type, length=args.length
        )

        if not passwords:
            return 1

    # Display results
    if not args.quiet:
        console.print()
        display_password_table(passwords)

        # Security warning
        console.print(
            Panel(
                "[yellow]⚠️  SECURITY NOTICE[/yellow]\n\n"
                "• Plain passwords are displayed above for immediate use\n"
                "• Share these passwords securely with users\n"
                "• Use the YAML values in your SnowDDL configuration\n"
                "• Consider clearing your terminal history after use",
                title="🔒 Security Notice",
                border_style="yellow",
            )
        )

    # Export if requested
    if args.export:
        export_format = args.format
        if not export_format:
            # Detect format from file extension
            if args.export.suffix.lower() == ".csv":
                export_format = "csv"
            else:
                export_format = "json"

        export_passwords_to_file(passwords, args.export, export_format)

    # Summary
    if not args.quiet:
        console.print(
            f"\n✅ [green]Generated {len(passwords)} passwords successfully![/green]"
        )
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("1. Copy YAML values to your SnowDDL user configuration")
        console.print("2. Share plain passwords securely with users")
        console.print(
            "3. Run [cyan]uv run snowddl-plan[/cyan] and [cyan]uv run snowddl-apply[/cyan]"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
