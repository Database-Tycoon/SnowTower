#!/usr/bin/env python3
"""
Password Verification Script for SnowTower User Management

This script provides verification capabilities for encrypted passwords in YAML files.
It uses the existing FernetEncryption class and reads the Fernet key from environment.

Usage:
    uv run python src/verify_password.py "gAAAAABexampleEncryptedPasswordHere......"
    uv run python src/verify_password.py --interactive
    uv run python src/verify_password.py --yaml-file snowddl/user.yaml
    uv run python src/verify_password.py --all-yaml
    uv run python src/verify_password.py --help

Examples:
    # Verify a specific encrypted password
    uv run python src/verify_password.py "gAAAAABexample_encrypted_password_here..."

    # Interactive mode with secure prompts
    uv run python src/verify_password.py --interactive

    # Verify all passwords in a YAML file
    uv run python src/verify_password.py --yaml-file snowddl/user.yaml

    # Verify all encrypted passwords in all YAML files
    uv run python src/verify_password.py --all-yaml

    # Show decrypted password (with security warnings)
    uv run python src/verify_password.py "encrypted_string" --show-decrypted

    # Test round-trip encryption/decryption
    uv run python src/verify_password.py --test-roundtrip "TestPassword123!"
"""

import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from user_management.encryption import (
    FernetEncryption,
    FernetEncryptionError,
    FernetKeyMissingError,
    InvalidEncryptedDataError,
)
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def verify_password(
    encrypted_password: str, show_decrypted: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """
    Verify an encrypted password can be decrypted.

    Args:
        encrypted_password: Encrypted password string (with or without !decrypt prefix)
        show_decrypted: Whether to return the decrypted password

    Returns:
        Tuple of (is_valid, status_message, decrypted_password)
    """
    try:
        encryption = FernetEncryption()

        # Clean the password string (remove !decrypt prefix if present)
        clean_password = encrypted_password.strip()
        if clean_password.startswith("!decrypt "):
            clean_password = clean_password.replace("!decrypt ", "", 1)

        # Attempt to decrypt
        decrypted = encryption.decrypt_password(clean_password)

        if show_decrypted:
            return True, "✅ Password verification successful", decrypted
        else:
            return True, "✅ Password verification successful", None

    except FernetKeyMissingError as e:
        return False, f"❌ Missing Fernet key: {e}", None
    except InvalidEncryptedDataError as e:
        return False, f"❌ Invalid encrypted data: {e}", None
    except FernetEncryptionError as e:
        return False, f"❌ Verification failed: {e}", None


def interactive_verify() -> bool:
    """Interactive password verification with prompts."""
    try:
        encryption = FernetEncryption()

        encrypted_password = Prompt.ask("Enter encrypted password to verify")

        if not encrypted_password:
            console.print("❌ [red]Encrypted password cannot be empty[/red]")
            return False

        is_valid, message, decrypted = verify_password(
            encrypted_password, show_decrypted=False
        )
        console.print(message)

        if is_valid and Confirm.ask(
            "Show decrypted password? [red](WARNING: Will display in plain text)[/red]"
        ):
            console.print(
                f"\n⚠️  [yellow]SECURITY WARNING: Displaying password in plain text[/yellow]"
            )
            _, _, decrypted = verify_password(encrypted_password, show_decrypted=True)
            console.print(f"[cyan]Decrypted password: {decrypted}[/cyan]")

        return is_valid

    except FernetKeyMissingError:
        console.print("❌ [red]No Fernet key available![/red]")
        console.print("\nTo set up encryption:")
        console.print(
            "1. Generate a key: [cyan]uv run python src/encrypt_password.py --generate-key[/cyan]"
        )
        console.print(
            "2. Set environment variable: [cyan]export SNOWFLAKE_CONFIG_FERNET_KEYS='your-key'[/cyan]"
        )

        # Check for .env files
        env_files = [Path(".env"), Path("../.env")]
        existing_env = [f for f in env_files if f.exists()]
        if existing_env:
            console.print(
                f"3. Or load existing .env file: [cyan]source {existing_env[0]}[/cyan]"
            )

        return False


def find_yaml_files(directory: Path) -> List[Path]:
    """Find all YAML files in the directory and subdirectories."""
    yaml_files = []
    for pattern in ["*.yaml", "*.yml"]:
        yaml_files.extend(directory.rglob(pattern))
    return sorted(yaml_files)


def extract_encrypted_passwords(yaml_content: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract encrypted passwords from YAML content.

    Args:
        yaml_content: Parsed YAML dictionary

    Returns:
        Dictionary mapping user/key paths to encrypted passwords
    """
    encrypted_passwords = {}

    def extract_recursive(obj: Any, path: str = ""):
        """Recursively extract !decrypt values from nested dictionaries."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key

                if key == "password" and isinstance(value, str):
                    # Check if it's an encrypted password (contains !decrypt)
                    if value.strip().startswith("!decrypt "):
                        encrypted_passwords[current_path] = value.strip()
                    elif "gAAAAA" in value:  # Looks like a Fernet token
                        encrypted_passwords[current_path] = value.strip()
                else:
                    extract_recursive(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                extract_recursive(item, f"{path}[{i}]")

    extract_recursive(yaml_content)
    return encrypted_passwords


def verify_yaml_file(
    file_path: Path, show_decrypted: bool = False
) -> Tuple[int, int, Dict[str, Tuple[bool, str, Optional[str]]]]:
    """
    Verify all encrypted passwords in a YAML file.

    Args:
        file_path: Path to YAML file
        show_decrypted: Whether to include decrypted passwords in results

    Returns:
        Tuple of (total_count, success_count, results_dict)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_content = yaml.safe_load(f)

        if not yaml_content:
            return 0, 0, {}

        encrypted_passwords = extract_encrypted_passwords(yaml_content)
        results = {}
        success_count = 0

        for key_path, encrypted_password in encrypted_passwords.items():
            is_valid, message, decrypted = verify_password(
                encrypted_password, show_decrypted
            )
            results[key_path] = (is_valid, message, decrypted)
            if is_valid:
                success_count += 1

        return len(encrypted_passwords), success_count, results

    except Exception as e:
        console.print(f"❌ [red]Error reading YAML file {file_path}: {e}[/red]")
        return 0, 0, {}


def verify_all_yaml(directory: Path, show_decrypted: bool = False) -> None:
    """Verify encrypted passwords in all YAML files in directory."""
    yaml_files = find_yaml_files(directory)

    if not yaml_files:
        console.print(f"[yellow]No YAML files found in {directory}[/yellow]")
        return

    console.print(
        f"\n🔍 [blue]Scanning {len(yaml_files)} YAML files for encrypted passwords...[/blue]\n"
    )

    total_files = 0
    total_passwords = 0
    total_successes = 0
    file_results = []

    for yaml_file in yaml_files:
        password_count, success_count, results = verify_yaml_file(
            yaml_file, show_decrypted
        )

        if password_count > 0:
            total_files += 1
            total_passwords += password_count
            total_successes += success_count
            file_results.append((yaml_file, password_count, success_count, results))

    # Display results table
    if file_results:
        table = Table(title="Password Verification Results", box=box.ROUNDED)
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Passwords", justify="center")
        table.add_column("Valid", justify="center", style="green")
        table.add_column("Invalid", justify="center", style="red")
        table.add_column("Status", justify="center")

        for yaml_file, password_count, success_count, results in file_results:
            rel_path = yaml_file.relative_to(directory)
            failed_count = password_count - success_count
            status = "✅" if failed_count == 0 else "❌"

            table.add_row(
                str(rel_path),
                str(password_count),
                str(success_count),
                str(failed_count),
                status,
            )

        console.print(table)
        console.print()

        # Summary
        if total_successes == total_passwords:
            console.print(
                f"🎉 [green]All {total_passwords} encrypted passwords verified successfully across {total_files} files![/green]"
            )
        else:
            failed_count = total_passwords - total_successes
            console.print(
                f"⚠️  [yellow]{total_successes}/{total_passwords} passwords verified successfully. {failed_count} failed.[/yellow]"
            )

        # Show detailed failures if any
        if total_successes < total_passwords:
            console.print("\n📝 [red]Failed password details:[/red]")
            for yaml_file, _, _, results in file_results:
                rel_path = yaml_file.relative_to(directory)
                for key_path, (is_valid, message, _) in results.items():
                    if not is_valid:
                        console.print(
                            f"  • [cyan]{rel_path}[/cyan] → [yellow]{key_path}[/yellow]: {message}"
                        )

        # Show decrypted passwords if requested
        if show_decrypted and Confirm.ask(
            "\n⚠️  [yellow]Show all decrypted passwords? (SECURITY WARNING: Will display in plain text)[/yellow]"
        ):
            console.print("\n🔓 [red]DECRYPTED PASSWORDS (HANDLE WITH CARE):[/red]")
            for yaml_file, _, _, results in file_results:
                rel_path = yaml_file.relative_to(directory)
                for key_path, (is_valid, _, decrypted) in results.items():
                    if is_valid and decrypted:
                        console.print(
                            f"  • [cyan]{rel_path}[/cyan] → [yellow]{key_path}[/yellow]: [magenta]{decrypted}[/magenta]"
                        )
    else:
        console.print(
            "[yellow]No encrypted passwords found in any YAML files.[/yellow]"
        )


def test_roundtrip(plain_password: str) -> bool:
    """Test round-trip encryption and decryption."""
    try:
        encryption = FernetEncryption()

        # Encrypt
        encrypted = encryption.encrypt_password(plain_password)
        console.print(f"🔐 [blue]Encrypted:[/blue] [cyan]{encrypted}[/cyan]")

        # Decrypt
        decrypted = encryption.decrypt_password(encrypted)
        console.print(f"🔓 [blue]Decrypted:[/blue] [cyan]{decrypted}[/cyan]")

        # Verify they match
        if plain_password == decrypted:
            console.print("✅ [green]Round-trip test successful![/green]")
            return True
        else:
            console.print(
                "❌ [red]Round-trip test failed! Passwords don't match.[/red]"
            )
            return False

    except Exception as e:
        console.print(f"❌ [red]Round-trip test failed: {e}[/red]")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify encrypted passwords for SnowTower YAML configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python src/verify_password.py "gAAAAABexampleEncryptedPasswordHere......"
  uv run python src/verify_password.py --interactive
  uv run python src/verify_password.py --yaml-file snowddl/user.yaml
  uv run python src/verify_password.py --all-yaml
  uv run python src/verify_password.py "encrypted_string" --show-decrypted
  uv run python src/verify_password.py --test-roundtrip "TestPassword123!"
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "encrypted_password",
        nargs="?",
        help="Encrypted password to verify (with or without !decrypt prefix)",
    )
    group.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode with secure password prompts",
    )
    group.add_argument(
        "--yaml-file",
        "-f",
        type=str,
        help="Verify all encrypted passwords in specific YAML file",
    )
    group.add_argument(
        "--all-yaml",
        "-a",
        action="store_true",
        help="Verify all encrypted passwords in all YAML files in snowddl/ directory",
    )
    group.add_argument(
        "--test-roundtrip",
        "-t",
        type=str,
        help="Test round-trip encryption/decryption with given plain text password",
    )

    parser.add_argument(
        "--show-decrypted",
        "-s",
        action="store_true",
        help="Show decrypted passwords (WARNING: Displays in plain text)",
    )

    args = parser.parse_args()

    # Security warning for --show-decrypted
    if args.show_decrypted:
        console.print(
            Panel(
                Text(
                    "SECURITY WARNING: You have enabled --show-decrypted.\nDecrypted passwords will be displayed in plain text!",
                    style="bold red",
                ),
                title="⚠️  Security Warning",
                border_style="red",
            )
        )
        if not Confirm.ask("Do you want to continue?"):
            console.print("Operation cancelled.")
            sys.exit(0)

    if args.test_roundtrip:
        success = test_roundtrip(args.test_roundtrip)
        sys.exit(0 if success else 1)
    elif args.interactive:
        success = interactive_verify()
        sys.exit(0 if success else 1)
    elif args.yaml_file:
        yaml_path = Path(args.yaml_file)
        if not yaml_path.exists():
            console.print(f"❌ [red]YAML file not found: {yaml_path}[/red]")
            sys.exit(1)

        console.print(
            f"🔍 [blue]Verifying encrypted passwords in {yaml_path}...[/blue]\n"
        )
        total_count, success_count, results = verify_yaml_file(
            yaml_path, args.show_decrypted
        )

        if total_count == 0:
            console.print("[yellow]No encrypted passwords found in file.[/yellow]")
        else:
            console.print(
                f"📊 [blue]Results: {success_count}/{total_count} passwords verified successfully[/blue]\n"
            )

            for key_path, (is_valid, message, decrypted) in results.items():
                status_color = "green" if is_valid else "red"
                console.print(
                    f"• [yellow]{key_path}[/yellow]: [{status_color}]{message}[/{status_color}]"
                )

                if args.show_decrypted and is_valid and decrypted:
                    console.print(f"  [magenta]Decrypted: {decrypted}[/magenta]")

        sys.exit(0 if success_count == total_count else 1)
    elif args.all_yaml:
        project_root = Path(__file__).parent.parent
        snowddl_dir = project_root / "snowddl"

        if not snowddl_dir.exists():
            console.print(f"❌ [red]SnowDDL directory not found: {snowddl_dir}[/red]")
            sys.exit(1)

        verify_all_yaml(snowddl_dir, args.show_decrypted)
    elif args.encrypted_password:
        is_valid, message, decrypted = verify_password(
            args.encrypted_password, args.show_decrypted
        )
        console.print(message)

        if args.show_decrypted and is_valid and decrypted:
            console.print(
                f"\n🔓 [yellow]Decrypted password:[/yellow] [magenta]{decrypted}[/magenta]"
            )

        sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
