#!/usr/bin/env python3
"""
User Management Script using SnowDDL OOP Framework

A practical command-line tool for managing Snowflake users through SnowDDL.
Supports creating, updating, disabling users, role assignments, and reporting.

Usage Examples:
    # Add a new user with password authentication
    python manage_users.py add --name JOHN_DOE --email john.doe@company.com --password "SecurePass123!"

    # Add a service account with RSA key
    python manage_users.py add --name ETL_SERVICE --type SERVICE --rsa-key-file ~/.ssh/etl_rsa.pub

    # Bulk update user emails from CSV
    python manage_users.py bulk-update --file users.csv --update-type email

    # Assign role to user
    python manage_users.py assign-role --user JOHN_DOE --role ANALYST_ROLE

    # Disable user
    python manage_users.py disable --name JOHN_DOE

    # Generate user report
    python manage_users.py report --format table

    # Show user details
    python manage_users.py show --name JOHN_DOE
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.project import SnowDDLProject
from snowddl_core.account_objects import User
from snowddl_core.exceptions import EncryptionError

console = Console()


class UserManagementError(Exception):
    """Base exception for user management operations"""

    pass


class UserManager:
    """Main user management orchestrator using SnowDDL OOP framework"""

    def __init__(self, config_dir: Path):
        """
        Initialize user manager

        Args:
            config_dir: Path to SnowDDL configuration directory
        """
        self.config_dir = config_dir
        self.project = SnowDDLProject(config_dir)
        console.print(f"[green]✓[/green] Loaded SnowDDL project from {config_dir}")

    def add_user(
        self,
        name: str,
        email: Optional[str] = None,
        user_type: str = "PERSON",
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        password: Optional[str] = None,
        rsa_key_file: Optional[Path] = None,
        roles: Optional[List[str]] = None,
        default_warehouse: Optional[str] = None,
        comment: Optional[str] = None,
        disabled: bool = False,
    ) -> User:
        """
        Add a new user to the project

        Args:
            name: User name (uppercase, e.g., JOHN_DOE)
            email: Email address (required for PERSON type)
            user_type: PERSON or SERVICE
            first_name: First name
            last_name: Last name
            password: Plain text password (will be encrypted)
            rsa_key_file: Path to RSA public key file
            roles: List of business role names
            default_warehouse: Default warehouse name
            comment: Descriptive comment
            disabled: Whether user should be disabled

        Returns:
            Created User object

        Raises:
            UserManagementError: If user creation fails
        """
        # Validate user doesn't already exist
        if self.project.get_user(name):
            raise UserManagementError(f"User {name} already exists")

        # Validate email for PERSON type
        if user_type == "PERSON" and not email:
            raise UserManagementError("Email is required for PERSON type users")

        # Create login name if not provided
        login_name = name.lower()

        # Create user object
        user = User(
            name=name,
            login_name=login_name,
            type=user_type,
            first_name=first_name,
            last_name=last_name,
            email=email,
            disabled=disabled,
            business_roles=roles or [],
            default_warehouse=default_warehouse,
            comment=comment or f"{user_type} user - {name}",
        )

        # Set password if provided
        if password:
            try:
                user.set_password(password)
                console.print(f"[green]✓[/green] Password encrypted successfully")
            except EncryptionError as e:
                raise UserManagementError(f"Password encryption failed: {e}")

        # Set RSA key if provided
        if rsa_key_file:
            if not rsa_key_file.exists():
                raise UserManagementError(f"RSA key file not found: {rsa_key_file}")

            with open(rsa_key_file, "r") as f:
                public_key = f.read()

            user.set_rsa_key(public_key)
            console.print(f"[green]✓[/green] RSA public key configured")

        # Add to project
        self.project.add_user(user)
        console.print(f"[green]✓[/green] User {name} added to project")

        return user

    def bulk_update(
        self, csv_file: Path, update_type: str, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Bulk update users from CSV file

        CSV format depends on update_type:
        - email: name,email
        - warehouse: name,warehouse
        - comment: name,comment
        - roles: name,role1|role2|role3

        Args:
            csv_file: Path to CSV file
            update_type: Type of update (email, warehouse, comment, roles)
            dry_run: Preview changes without applying

        Returns:
            Dictionary with update statistics
        """
        if not csv_file.exists():
            raise UserManagementError(f"CSV file not found: {csv_file}")

        updates = {"success": 0, "failed": 0, "skipped": 0}

        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row.get("name", "").upper()
                if not name:
                    continue

                user = self.project.get_user(name)
                if not user:
                    console.print(f"[yellow]⚠[/yellow] User {name} not found, skipping")
                    updates["skipped"] += 1
                    continue

                try:
                    if update_type == "email":
                        new_email = row.get("email")
                        if new_email:
                            if not dry_run:
                                user.email = new_email
                            console.print(
                                f"[green]✓[/green] {name}: email → {new_email}"
                            )

                    elif update_type == "warehouse":
                        new_warehouse = row.get("warehouse")
                        if new_warehouse:
                            if not dry_run:
                                user.default_warehouse = new_warehouse
                            console.print(
                                f"[green]✓[/green] {name}: warehouse → {new_warehouse}"
                            )

                    elif update_type == "comment":
                        new_comment = row.get("comment")
                        if new_comment:
                            if not dry_run:
                                user.comment = new_comment
                            console.print(
                                f"[green]✓[/green] {name}: comment → {new_comment}"
                            )

                    elif update_type == "roles":
                        roles_str = row.get("roles", "")
                        if roles_str:
                            new_roles = [r.strip() for r in roles_str.split("|")]
                            if not dry_run:
                                user.business_roles = new_roles
                            console.print(
                                f"[green]✓[/green] {name}: roles → {', '.join(new_roles)}"
                            )

                    else:
                        raise UserManagementError(f"Unknown update type: {update_type}")

                    updates["success"] += 1

                except Exception as e:
                    console.print(f"[red]✗[/red] {name}: {e}")
                    updates["failed"] += 1

        return updates

    def assign_role(self, user_name: str, role_name: str) -> None:
        """
        Assign a business role to a user

        Args:
            user_name: User name
            role_name: Business role name
        """
        user = self.project.get_user(user_name)
        if not user:
            raise UserManagementError(f"User {user_name} not found")

        # Verify role exists
        role = self.project.get_business_role(role_name)
        if not role:
            console.print(
                f"[yellow]⚠[/yellow] Warning: Role {role_name} not found in configuration"
            )

        user.add_role(role_name)
        console.print(f"[green]✓[/green] Role {role_name} assigned to {user_name}")

    def remove_role(self, user_name: str, role_name: str) -> None:
        """
        Remove a business role from a user

        Args:
            user_name: User name
            role_name: Business role name
        """
        user = self.project.get_user(user_name)
        if not user:
            raise UserManagementError(f"User {user_name} not found")

        user.remove_role(role_name)
        console.print(f"[green]✓[/green] Role {role_name} removed from {user_name}")

    def disable_user(self, user_name: str) -> None:
        """
        Disable a user account

        Args:
            user_name: User name
        """
        user = self.project.get_user(user_name)
        if not user:
            raise UserManagementError(f"User {user_name} not found")

        user.disabled = True
        console.print(f"[green]✓[/green] User {user_name} disabled")

    def enable_user(self, user_name: str) -> None:
        """
        Enable a user account

        Args:
            user_name: User name
        """
        user = self.project.get_user(user_name)
        if not user:
            raise UserManagementError(f"User {user_name} not found")

        user.disabled = False
        console.print(f"[green]✓[/green] User {user_name} enabled")

    def update_password(self, user_name: str, new_password: str) -> None:
        """
        Update user password

        Args:
            user_name: User name
            new_password: New plain text password (will be encrypted)
        """
        user = self.project.get_user(user_name)
        if not user:
            raise UserManagementError(f"User {user_name} not found")

        try:
            user.set_password(new_password)
            console.print(f"[green]✓[/green] Password updated for {user_name}")
        except EncryptionError as e:
            raise UserManagementError(f"Password encryption failed: {e}")

    def show_user(self, user_name: str, show_password: bool = False) -> None:
        """
        Display detailed user information

        Args:
            user_name: User name
            show_password: Whether to show encrypted password
        """
        user = self.project.get_user(user_name)
        if not user:
            raise UserManagementError(f"User {user_name} not found")

        table = Table(title=f"User Details: {user_name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Name", user.name)
        table.add_row("Login Name", user.login_name)
        table.add_row("Type", user.type)
        table.add_row("Email", user.email or "N/A")
        table.add_row("First Name", user.first_name or "N/A")
        table.add_row("Last Name", user.last_name or "N/A")
        table.add_row("Disabled", "Yes" if user.disabled else "No")
        table.add_row("Business Roles", ", ".join(user.business_roles) or "None")
        table.add_row("Default Warehouse", user.default_warehouse or "N/A")
        table.add_row("Default Namespace", user.default_namespace or "N/A")
        table.add_row("Has Password", "Yes" if user.password else "No")
        table.add_row("Has RSA Key", "Yes" if user.rsa_public_key else "No")
        table.add_row("Has RSA Key 2", "Yes" if user.rsa_public_key_2 else "No")
        table.add_row("Auth Policy", user.authentication_policy or "N/A")
        table.add_row("Network Policy", user.network_policy or "N/A")
        table.add_row("Comment", user.comment or "N/A")

        if show_password and user.password:
            table.add_row("Encrypted Password", user.password)

        console.print(table)

    def generate_report(
        self,
        format: str = "table",
        output_file: Optional[Path] = None,
        filter_type: Optional[str] = None,
        filter_disabled: Optional[bool] = None,
    ) -> None:
        """
        Generate user configuration report

        Args:
            format: Output format (table, json, csv, yaml)
            output_file: Optional output file path
            filter_type: Filter by user type (PERSON, SERVICE)
            filter_disabled: Filter by disabled status
        """
        users = list(self.project.users.values())

        # Apply filters
        if filter_type:
            users = [u for u in users if u.type == filter_type]

        if filter_disabled is not None:
            users = [u for u in users if u.disabled == filter_disabled]

        if format == "table":
            self._report_table(users)
        elif format == "json":
            self._report_json(users, output_file)
        elif format == "csv":
            self._report_csv(users, output_file)
        elif format == "yaml":
            self._report_yaml(users, output_file)
        else:
            raise UserManagementError(f"Unknown report format: {format}")

    def _report_table(self, users: List[User]) -> None:
        """Generate table format report"""
        table = Table(title=f"User Configuration Report ({len(users)} users)")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Email", style="green")
        table.add_column("Roles", style="magenta")
        table.add_column("Auth", style="blue")
        table.add_column("Status", style="red")

        for user in sorted(users, key=lambda u: u.name):
            auth = []
            if user.password:
                auth.append("PWD")
            if user.rsa_public_key:
                auth.append("RSA")

            status = "DISABLED" if user.disabled else "ACTIVE"

            table.add_row(
                user.name,
                user.type,
                user.email or "N/A",
                ", ".join(user.business_roles[:2])
                + ("..." if len(user.business_roles) > 2 else ""),
                "+".join(auth) or "NONE",
                status,
            )

        console.print(table)

    def _report_json(self, users: List[User], output_file: Optional[Path]) -> None:
        """Generate JSON format report"""
        data = [
            {
                "name": u.name,
                "type": u.type,
                "email": u.email,
                "roles": u.business_roles,
                "disabled": u.disabled,
                "has_password": bool(u.password),
                "has_rsa_key": bool(u.rsa_public_key),
            }
            for u in users
        ]

        json_str = json.dumps(data, indent=2)

        if output_file:
            output_file.write_text(json_str)
            console.print(f"[green]✓[/green] Report saved to {output_file}")
        else:
            console.print(json_str)

    def _report_csv(self, users: List[User], output_file: Optional[Path]) -> None:
        """Generate CSV format report"""
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Name",
                "Type",
                "Email",
                "Roles",
                "Disabled",
                "Has Password",
                "Has RSA Key",
            ]
        )

        for user in users:
            writer.writerow(
                [
                    user.name,
                    user.type,
                    user.email or "",
                    "|".join(user.business_roles),
                    user.disabled,
                    bool(user.password),
                    bool(user.rsa_public_key),
                ]
            )

        csv_str = output.getvalue()

        if output_file:
            output_file.write_text(csv_str)
            console.print(f"[green]✓[/green] Report saved to {output_file}")
        else:
            console.print(csv_str)

    def _report_yaml(self, users: List[User], output_file: Optional[Path]) -> None:
        """Generate YAML format report"""
        import yaml

        data = {u.name: u.to_yaml() for u in users}
        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)

        if output_file:
            output_file.write_text(yaml_str)
            console.print(f"[green]✓[/green] Report saved to {output_file}")
        else:
            console.print(yaml_str)

    def save_changes(self, dry_run: bool = False) -> None:
        """
        Save all changes to YAML files

        Args:
            dry_run: Preview changes without saving
        """
        if dry_run:
            console.print("[yellow]DRY RUN: Changes would be saved to:[/yellow]")
            console.print(f"  • {self.config_dir / 'user.yaml'}")
        else:
            # Validate before saving
            errors = self.project.validate()
            if errors:
                console.print(f"[red]Validation errors found ({len(errors)}):[/red]")
                for error in errors[:5]:
                    console.print(f"  • {error.message}")

                if not Confirm.ask("Save anyway?"):
                    console.print("[yellow]Save cancelled[/yellow]")
                    return

            self.project.save_all()
            console.print("[green]✓[/green] Changes saved successfully")
            console.print("\n[bold]Next steps:[/bold]")
            console.print(
                "  1. Run: [cyan]uv run snowddl-plan[/cyan] to preview Snowflake changes"
            )
            console.print(
                "  2. Run: [cyan]uv run snowddl-apply[/cyan] to apply changes"
            )


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="User Management Script using SnowDDL OOP Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path.cwd() / "snowddl",
        help="Path to SnowDDL configuration directory (default: ./snowddl)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add user command
    add_parser = subparsers.add_parser("add", help="Add a new user")
    add_parser.add_argument("--name", required=True, help="User name (uppercase)")
    add_parser.add_argument("--email", help="Email address")
    add_parser.add_argument(
        "--type", default="PERSON", choices=["PERSON", "SERVICE"], help="User type"
    )
    add_parser.add_argument("--first-name", help="First name")
    add_parser.add_argument("--last-name", help="Last name")
    add_parser.add_argument(
        "--password", help="Plain text password (will be encrypted)"
    )
    add_parser.add_argument(
        "--rsa-key-file", type=Path, help="Path to RSA public key file"
    )
    add_parser.add_argument("--roles", nargs="+", help="Business role names")
    add_parser.add_argument("--warehouse", help="Default warehouse")
    add_parser.add_argument("--comment", help="Descriptive comment")
    add_parser.add_argument(
        "--disabled", action="store_true", help="Create user as disabled"
    )
    add_parser.add_argument(
        "--save", action="store_true", help="Save changes immediately"
    )

    # Bulk update command
    bulk_parser = subparsers.add_parser(
        "bulk-update", help="Bulk update users from CSV"
    )
    bulk_parser.add_argument(
        "--file", type=Path, required=True, help="Path to CSV file"
    )
    bulk_parser.add_argument(
        "--update-type",
        required=True,
        choices=["email", "warehouse", "comment", "roles"],
        help="Type of update to perform",
    )
    bulk_parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )
    bulk_parser.add_argument(
        "--save", action="store_true", help="Save changes after update"
    )

    # Assign role command
    assign_parser = subparsers.add_parser("assign-role", help="Assign role to user")
    assign_parser.add_argument("--user", required=True, help="User name")
    assign_parser.add_argument("--role", required=True, help="Business role name")
    assign_parser.add_argument(
        "--save", action="store_true", help="Save changes immediately"
    )

    # Remove role command
    remove_parser = subparsers.add_parser("remove-role", help="Remove role from user")
    remove_parser.add_argument("--user", required=True, help="User name")
    remove_parser.add_argument("--role", required=True, help="Business role name")
    remove_parser.add_argument(
        "--save", action="store_true", help="Save changes immediately"
    )

    # Disable user command
    disable_parser = subparsers.add_parser("disable", help="Disable user account")
    disable_parser.add_argument("--name", required=True, help="User name")
    disable_parser.add_argument(
        "--save", action="store_true", help="Save changes immediately"
    )

    # Enable user command
    enable_parser = subparsers.add_parser("enable", help="Enable user account")
    enable_parser.add_argument("--name", required=True, help="User name")
    enable_parser.add_argument(
        "--save", action="store_true", help="Save changes immediately"
    )

    # Update password command
    password_parser = subparsers.add_parser(
        "update-password", help="Update user password"
    )
    password_parser.add_argument("--user", required=True, help="User name")
    password_parser.add_argument("--password", required=True, help="New password")
    password_parser.add_argument(
        "--save", action="store_true", help="Save changes immediately"
    )

    # Show user command
    show_parser = subparsers.add_parser("show", help="Show user details")
    show_parser.add_argument("--name", required=True, help="User name")
    show_parser.add_argument(
        "--show-password", action="store_true", help="Show encrypted password"
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate user report")
    report_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json", "csv", "yaml"],
        help="Report format",
    )
    report_parser.add_argument("--output", type=Path, help="Output file path")
    report_parser.add_argument(
        "--filter-type", choices=["PERSON", "SERVICE"], help="Filter by user type"
    )
    report_parser.add_argument(
        "--filter-disabled",
        type=lambda x: x.lower() == "true",
        help="Filter by disabled status (true/false)",
    )

    # Save command
    save_parser = subparsers.add_parser("save", help="Save all pending changes")
    save_parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without saving"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Check for Fernet key
    if not os.getenv("SNOWFLAKE_CONFIG_FERNET_KEYS"):
        console.print(
            "[red]Error: SNOWFLAKE_CONFIG_FERNET_KEYS environment variable not set[/red]"
        )
        console.print(
            "Run: [cyan]export SNOWFLAKE_CONFIG_FERNET_KEYS=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'[/cyan]"
        )
        return 1

    try:
        manager = UserManager(args.config_dir)

        if args.command == "add":
            manager.add_user(
                name=args.name.upper(),
                email=args.email,
                user_type=args.type,
                first_name=args.first_name,
                last_name=args.last_name,
                password=args.password,
                rsa_key_file=args.rsa_key_file,
                roles=args.roles,
                default_warehouse=args.warehouse,
                comment=args.comment,
                disabled=args.disabled,
            )
            if args.save:
                manager.save_changes()

        elif args.command == "bulk-update":
            stats = manager.bulk_update(args.file, args.update_type, args.dry_run)
            console.print(f"\n[bold]Update Summary:[/bold]")
            console.print(f"  Success: {stats['success']}")
            console.print(f"  Failed: {stats['failed']}")
            console.print(f"  Skipped: {stats['skipped']}")
            if args.save and not args.dry_run:
                manager.save_changes()

        elif args.command == "assign-role":
            manager.assign_role(args.user, args.role)
            if args.save:
                manager.save_changes()

        elif args.command == "remove-role":
            manager.remove_role(args.user, args.role)
            if args.save:
                manager.save_changes()

        elif args.command == "disable":
            manager.disable_user(args.name)
            if args.save:
                manager.save_changes()

        elif args.command == "enable":
            manager.enable_user(args.name)
            if args.save:
                manager.save_changes()

        elif args.command == "update-password":
            manager.update_password(args.user, args.password)
            if args.save:
                manager.save_changes()

        elif args.command == "show":
            manager.show_user(args.name, args.show_password)

        elif args.command == "report":
            manager.generate_report(
                format=args.format,
                output_file=args.output,
                filter_type=args.filter_type,
                filter_disabled=args.filter_disabled,
            )

        elif args.command == "save":
            manager.save_changes(dry_run=args.dry_run)

        console.print("\n[green]✓ Operation completed successfully[/green]")
        return 0

    except UserManagementError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
