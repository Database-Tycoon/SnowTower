"""
Command Line Interface for SnowTower User Management

Provides unified CLI commands for all user management operations.
Integrates with the UserManager to provide a consistent interface.
"""

from dotenv import load_dotenv

load_dotenv()  # Load .env before any other imports that need env vars

import sys
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.traceback import install

# Install rich tracebacks for better error display
install()
console = Console()

# Import managers
from .manager import UserManager, UserType
from .encryption import FernetEncryption
from .rsa_keys import RSAKeyManager
from .yaml_handler import YAMLHandler
from .snowddl_account import SnowDDLAccountManager


def get_user_manager(config_dir: Optional[str] = None) -> UserManager:
    """Get UserManager instance with optional config directory"""
    config_path = Path(config_dir) if config_dir else None
    return UserManager(config_path)


@click.group()
@click.option("--config-dir", "-c", help="SnowDDL configuration directory")
@click.pass_context
def user(ctx, config_dir):
    """SnowTower User Management System"""
    ctx.ensure_object(dict)
    ctx.obj["config_dir"] = config_dir


@user.command()
@click.option("--first-name", "-f", help="First name")
@click.option("--last-name", "-l", help="Last name")
@click.option("--email", "-e", help="Email address")
@click.option("--username", "-u", help="Username (auto-generated if not provided)")
@click.option(
    "--user-type",
    "-t",
    type=click.Choice(["PERSON", "SERVICE"]),
    default="PERSON",
    help="User type",
)
@click.option("--default-role", "-r", help="Default role")
@click.option(
    "--default-warehouse", "-w", default="COMPUTE_WH", help="Default warehouse"
)
@click.option(
    "--generate-rsa", "--rsa", is_flag=True, default=True, help="Generate RSA key pair"
)
@click.option("--set-password", "--pwd", is_flag=True, help="Set encrypted password")
@click.option(
    "--auto-generate-password",
    "--auto-pwd",
    is_flag=True,
    default=True,
    help="Automatically generate secure password",
)
@click.option(
    "--password-length",
    "--pwd-len",
    default=16,
    help="Password length for auto-generation",
)
@click.option("--non-interactive", "--batch", is_flag=True, help="Non-interactive mode")
@click.pass_context
def create(
    ctx,
    first_name,
    last_name,
    email,
    username,
    user_type,
    default_role,
    default_warehouse,
    generate_rsa,
    set_password,
    auto_generate_password,
    password_length,
    non_interactive,
):
    """Create a new user"""
    manager = get_user_manager(ctx.obj["config_dir"])

    try:
        if non_interactive:
            # Validate required fields for non-interactive mode
            if not all([first_name, last_name, email]):
                console.print(
                    "❌ [red]Non-interactive mode requires --first-name, --last-name, and --email[/red]"
                )
                sys.exit(1)

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "user_type": UserType(user_type),
                "default_warehouse": default_warehouse,
                "auto_generate_password": auto_generate_password,
                "password_length": password_length,
            }

            if username:
                user_data["username"] = username
            if default_role:
                user_data["default_role"] = default_role

            result = manager.create_user(interactive=False, **user_data)
            console.print(f"✅ [green]User created successfully![/green]")

        else:
            # Interactive mode
            result = manager.create_user(interactive=True)

    except Exception as e:
        console.print(f"❌ [red]User creation failed: {e}[/red]")
        sys.exit(1)


@user.command()
@click.argument("username")
@click.option("--first-name", help="Update first name")
@click.option("--last-name", help="Update last name")
@click.option("--email", help="Update email address")
@click.option("--default-role", help="Update default role")
@click.option("--default-warehouse", help="Update default warehouse")
@click.option("--disable", is_flag=True, help="Disable user")
@click.option("--enable", is_flag=True, help="Enable user")
@click.pass_context
def update(
    ctx,
    username,
    first_name,
    last_name,
    email,
    default_role,
    default_warehouse,
    disable,
    enable,
):
    """Update an existing user"""
    manager = get_user_manager(ctx.obj["config_dir"])

    updates = {}

    if first_name:
        updates["first_name"] = first_name
    if last_name:
        updates["last_name"] = last_name
    if email:
        updates["email"] = email
    if default_role:
        updates["default_role"] = default_role
    if default_warehouse:
        updates["default_warehouse"] = default_warehouse
    if disable:
        updates["disabled"] = True
    if enable:
        updates["disabled"] = False

    # Update display name if first or last name changed
    if first_name or last_name:
        user_config = manager.get_user(username)
        if user_config:
            fname = first_name or user_config.get("first_name", "")
            lname = last_name or user_config.get("last_name", "")
            updates["display_name"] = f"{fname} {lname}"

    if not updates:
        console.print("❌ [yellow]No updates specified[/yellow]")
        return

    if manager.update_user(username, **updates):
        console.print(f"✅ [green]User {username} updated successfully![/green]")
    else:
        console.print(f"❌ [red]Failed to update user {username}[/red]")
        sys.exit(1)


@user.command()
@click.argument("username")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx, username, force):
    """Delete a user"""
    manager = get_user_manager(ctx.obj["config_dir"])

    if manager.delete_user(username, confirm=not force):
        console.print(f"✅ [green]User {username} deleted successfully![/green]")
    else:
        console.print(f"❌ [red]Failed to delete user {username}[/red]")
        sys.exit(1)


@user.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.option(
    "--user-type",
    "-t",
    type=click.Choice(["PERSON", "SERVICE"]),
    help="Filter by user type",
)
@click.pass_context
def list(ctx, format, user_type):
    """List all users"""
    manager = get_user_manager(ctx.obj["config_dir"])

    try:
        result = manager.list_users(format=format)

        if format != "table" and result:
            # Filter by user type if specified
            if user_type and format in ["json", "yaml"]:
                import yaml as yaml_lib

                if format == "json":
                    data = json.loads(result)
                else:
                    data = yaml_lib.safe_load(result)

                filtered_data = {
                    username: config
                    for username, config in data.items()
                    if config.get("type") == user_type
                }

                if format == "json":
                    result = json.dumps(filtered_data, indent=2)
                else:
                    result = yaml_lib.dump(filtered_data, default_flow_style=False)

            console.print(result)

    except Exception as e:
        console.print(f"❌ [red]Failed to list users: {e}[/red]")
        sys.exit(1)


@user.command()
@click.argument("username")
@click.pass_context
def show(ctx, username):
    """Show detailed information about a specific user"""
    manager = get_user_manager(ctx.obj["config_dir"])

    user_config = manager.get_user(username)
    if not user_config:
        console.print(f"❌ [red]User {username} not found[/red]")
        sys.exit(1)

    # Display user information in a nice format
    from rich.table import Table

    table = Table(title=f"User Details: {username}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    # Basic information
    basic_fields = [
        ("Username", username),
        ("Type", user_config.get("type", "N/A")),
        ("Display Name", user_config.get("display_name", "N/A")),
        ("First Name", user_config.get("first_name", "N/A")),
        ("Last Name", user_config.get("last_name", "N/A")),
        ("Email", user_config.get("email", "N/A")),
        ("Default Role", user_config.get("default_role", "N/A")),
        ("Default Warehouse", user_config.get("default_warehouse", "N/A")),
        ("Disabled", "Yes" if user_config.get("disabled", False) else "No"),
    ]

    for prop, value in basic_fields:
        table.add_row(prop, str(value))

    # Authentication methods
    auth_methods = []
    if user_config.get("password"):
        auth_methods.append("Password (encrypted)")
    if user_config.get("rsa_public_key"):
        auth_methods.append("RSA Public Key")
    if user_config.get("rsa_public_key_2"):
        auth_methods.append("RSA Public Key 2")

    table.add_row(
        "Authentication", ", ".join(auth_methods) if auth_methods else "None configured"
    )

    # Security policies
    policies = []
    policy_fields = [
        "authentication_policy",
        "network_policy",
        "password_policy",
        "session_policy",
    ]
    for field in policy_fields:
        if user_config.get(field):
            policies.append(f"{field}: {user_config[field]}")

    if policies:
        table.add_row("Security Policies", "\n".join(policies))

    # Comment
    if user_config.get("comment"):
        table.add_row("Comment", user_config["comment"])

    console.print(table)


@user.command()
@click.argument("username")
@click.pass_context
def validate(ctx, username):
    """Validate a user's configuration"""
    manager = get_user_manager(ctx.obj["config_dir"])

    result = manager.validate_user(username)

    if result["is_valid"]:
        console.print(f"✅ [green]User {username} configuration is valid[/green]")
    else:
        console.print(f"❌ [red]User {username} configuration has errors:[/red]")
        for error in result["errors"]:
            console.print(f"   • [red]{error}[/red]")

    if result["warnings"]:
        console.print(f"⚠️ [yellow]Warnings:[/yellow]")
        for warning in result["warnings"]:
            console.print(f"   • [yellow]{warning}[/yellow]")


@user.command("validate-all")
@click.pass_context
def validate_all(ctx):
    """Validate all user configurations"""
    manager = get_user_manager(ctx.obj["config_dir"])

    try:
        users = manager.yaml_handler.load_users()
    except Exception as e:
        console.print(f"❌ [red]Failed to load users: {e}[/red]")
        sys.exit(1)

    if not users:
        console.print("📭 [yellow]No users to validate[/yellow]")
        return

    valid_count = 0
    error_count = 0
    warning_count = 0

    for username in users:
        result = manager.validate_user(username)

        if result["is_valid"]:
            valid_count += 1
            console.print(f"✅ [green]{username}[/green]")
        else:
            error_count += 1
            console.print(f"❌ [red]{username}[/red]")
            for error in result["errors"]:
                console.print(f"    • {error}")

        warning_count += len(result["warnings"])
        for warning in result["warnings"]:
            console.print(f"    ⚠️ [yellow]{warning}[/yellow]")

    console.print(
        f"\n📊 Summary: {valid_count} valid, {error_count} with errors, {warning_count} warnings"
    )


@user.command("encrypt-password")
@click.option(
    "--password", "-p", help="Password to encrypt (will prompt if not provided)"
)
@click.pass_context
def encrypt_password(ctx, password):
    """Encrypt a password for use in configuration"""
    manager = get_user_manager(ctx.obj["config_dir"])

    try:
        encrypted = manager.encrypt_password(password)
        if encrypted:
            console.print(f"Encrypted password: [cyan]{encrypted}[/cyan]")
            console.print(
                f"\nUse in YAML as: [cyan]password: !decrypt {encrypted}[/cyan]"
            )
    except Exception as e:
        console.print(f"❌ [red]Encryption failed: {e}[/red]")
        sys.exit(1)


@user.command("generate-password")
@click.argument("username")
@click.option("--length", "-l", default=16, help="Password length (minimum 12)")
@click.option(
    "--user-type",
    "-t",
    type=click.Choice(["PERSON", "SERVICE"]),
    default="PERSON",
    help="User type",
)
@click.option("--no-symbols", is_flag=True, help="Exclude symbols from password")
@click.option("--no-ambiguous", is_flag=True, help="Exclude ambiguous characters")
@click.pass_context
def generate_password(ctx, username, length, user_type, no_symbols, no_ambiguous):
    """Generate a secure password for a user"""
    manager = get_user_manager(ctx.obj["config_dir"])

    if length < 12:
        console.print("❌ [red]Password length must be at least 12 characters[/red]")
        sys.exit(1)

    try:
        password_info = manager.generate_password(
            username=username,
            user_type=user_type,
            length=length,
            include_symbols=not no_symbols,
            exclude_ambiguous=not no_ambiguous,
        )

        # Display password information
        from rich.panel import Panel

        console.print(
            Panel(
                f"[green]Password generated successfully for {username}![/green]\n\n"
                f"[yellow]Plain Password:[/yellow]\n"
                f"[red]{password_info['plain_password']}[/red]\n\n"
                f"[yellow]For YAML Configuration:[/yellow]\n"
                f"[cyan]{password_info['yaml_value']}[/cyan]\n\n"
                f"[dim]Password length: {password_info['length']} characters[/dim]\n"
                f"[dim]Generated: {password_info['generated_at']}[/dim]",
                title="🔐 Generated Password",
                border_style="green",
            )
        )

        console.print("\n[bold]Next Steps:[/bold]")
        console.print("1. Copy the YAML value to your user configuration")
        console.print("2. Share the plain password securely with the user")
        console.print(
            "3. Run [cyan]uv run snowddl-plan[/cyan] and [cyan]uv run snowddl-apply[/cyan]"
        )

    except Exception as e:
        console.print(f"❌ [red]Password generation failed: {e}[/red]")
        sys.exit(1)


@user.command("regenerate-password")
@click.argument("username")
@click.option("--length", "-l", default=16, help="Password length (minimum 12)")
@click.option("--confirm", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def regenerate_password(ctx, username, length, confirm):
    """Regenerate password for an existing user"""
    manager = get_user_manager(ctx.obj["config_dir"])

    if length < 12:
        console.print("❌ [red]Password length must be at least 12 characters[/red]")
        sys.exit(1)

    # Check if user exists
    if not manager.get_user(username):
        console.print(f"❌ [red]User {username} not found[/red]")
        sys.exit(1)

    # Confirmation
    if not confirm:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Regenerate password for {username}?"):
            console.print("❌ [yellow]Password regeneration cancelled[/yellow]")
            return

    if not manager.regenerate_user_password(username, length):
        sys.exit(1)


@user.command("bulk-generate-passwords")
@click.option("--usernames", "-u", help="Comma-separated list of usernames")
@click.option(
    "--csv-file", type=click.Path(exists=True), help="CSV file with usernames"
)
@click.option("--length", "-l", default=16, help="Password length (minimum 12)")
@click.option(
    "--user-type",
    "-t",
    type=click.Choice(["PERSON", "SERVICE"]),
    default="PERSON",
    help="User type",
)
@click.pass_context
def bulk_generate_passwords(ctx, usernames, csv_file, length, user_type):
    """Generate passwords for multiple users"""
    manager = get_user_manager(ctx.obj["config_dir"])

    if length < 12:
        console.print("❌ [red]Password length must be at least 12 characters[/red]")
        sys.exit(1)

    # Get usernames list
    user_list = []

    if usernames:
        user_list = [u.strip() for u in usernames.split(",")]
    elif csv_file:
        import csv

        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:  # Skip empty rows
                    user_list.append(row[0].strip())
    else:
        console.print("❌ [red]Must provide either --usernames or --csv-file[/red]")
        sys.exit(1)

    if not user_list:
        console.print("❌ [red]No usernames provided[/red]")
        sys.exit(1)

    try:
        passwords = manager.generate_passwords_bulk(
            user_list, user_type=user_type, length=length
        )

        # Display results in table
        from rich.table import Table

        table = Table(title=f"Generated Passwords ({len(passwords)} users)")
        table.add_column("Username", style="cyan")
        table.add_column("Plain Password", style="red")
        table.add_column("YAML Value", style="dim")

        for username, info in passwords.items():
            yaml_value = (
                info["yaml_value"][:50] + "..."
                if len(info["yaml_value"]) > 50
                else info["yaml_value"]
            )
            table.add_row(username, info["plain_password"], yaml_value)

        console.print(table)

        console.print(
            f"\n✅ [green]Generated passwords for {len(passwords)} users[/green]"
        )
        console.print(
            "[bold]Important:[/bold] Save these passwords securely before proceeding!"
        )

    except Exception as e:
        console.print(f"❌ [red]Bulk password generation failed: {e}[/red]")
        sys.exit(1)


@user.command("generate-keys")
@click.argument("username")
@click.option("--key-size", "-s", default=2048, help="RSA key size in bits")
@click.pass_context
def generate_keys(ctx, username, key_size):
    """Generate RSA key pair for a user"""
    manager = get_user_manager(ctx.obj["config_dir"])

    try:
        private_key, public_key = manager.generate_rsa_keys(username)
        console.print(f"✅ [green]RSA key pair generated for {username}[/green]")
        console.print(f"Private key: [cyan]{private_key}[/cyan]")
        console.print(f"Public key: [cyan]{public_key}[/cyan]")

        # Extract public key content for Snowflake
        public_key_content = manager.rsa_manager.extract_public_key_for_snowflake(
            private_key
        )
        console.print(f"\nFor SnowDDL configuration:")
        console.print(f"[cyan]rsa_public_key: {public_key_content}[/cyan]")

    except Exception as e:
        console.print(f"❌ [red]Key generation failed: {e}[/red]")
        sys.exit(1)


@user.command("rotate-keys")
@click.argument("username")
@click.pass_context
def rotate_keys(ctx, username):
    """Rotate RSA keys for a user and update configuration"""
    manager = get_user_manager(ctx.obj["config_dir"])

    if not manager.rotate_user_keys(username):
        sys.exit(1)


@user.command("list-keys")
@click.option("--username", "-u", help="Filter by username")
@click.pass_context
def list_keys(ctx, username):
    """List RSA keys"""
    manager = get_user_manager(ctx.obj["config_dir"])
    manager.rsa_manager.display_keys_table(username)


@user.command("backup")
@click.option("--description", "-d", help="Backup description")
@click.pass_context
def backup(ctx, description):
    """Create backup of user configuration"""
    manager = get_user_manager(ctx.obj["config_dir"])

    try:
        backup_path = manager.backup_configuration(description)
        console.print(f"✅ [green]Backup created: {backup_path}[/green]")
    except Exception as e:
        console.print(f"❌ [red]Backup failed: {e}[/red]")
        sys.exit(1)


@user.command("import-csv")
@click.argument("csv_file", type=click.Path(exists=True))
@click.pass_context
def import_csv(ctx, csv_file):
    """Import users from CSV file"""
    manager = get_user_manager(ctx.obj["config_dir"])

    try:
        created_users = manager.bulk_import(Path(csv_file))
        console.print(
            f"✅ [green]Imported {len(created_users)} users from {csv_file}[/green]"
        )
    except Exception as e:
        console.print(f"❌ [red]Import failed: {e}[/red]")
        sys.exit(1)


# SnowDDL Account Management Commands
@click.group()
def snowddl_account():
    """Manage SnowDDL service account (bootstrap-safe operations)"""
    pass


@snowddl_account.command()
@click.option(
    "--detailed", "-d", is_flag=True, help="Show detailed connection information"
)
def test(detailed):
    """Test SnowDDL service account connection"""
    manager = SnowDDLAccountManager()

    if not manager.test_connection(detailed=detailed):
        sys.exit(1)


@snowddl_account.command()
def status():
    """Show SnowDDL account status"""
    manager = SnowDDLAccountManager()

    status = manager.get_account_status()

    from rich.table import Table

    table = Table(title="SnowDDL Service Account Status")
    table.add_column("Property", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    # Connection status
    conn_status = "✅ Connected" if status["connection_working"] else "❌ Failed"
    table.add_row("Connection", conn_status, status["snowflake_account"])

    # Key file
    key_status = "✅ Found" if status["key_file_exists"] else "❌ Missing"
    table.add_row("RSA Key File", key_status, status["key_file_path"])

    # Permissions
    perm_status = "✅ Complete" if status["permissions_complete"] else "⚠️ Incomplete"
    table.add_row(
        "Permissions",
        perm_status,
        f"{len(status.get('assigned_roles', []))} roles assigned",
    )

    console.print(table)

    # Show issues if any
    if status["issues"]:
        console.print(f"\n⚠️ [yellow]Issues found:[/yellow]")
        for issue in status["issues"]:
            console.print(f"  • [yellow]{issue}[/yellow]")


@snowddl_account.command()
def permissions():
    """Check SnowDDL account permissions"""
    manager = SnowDDLAccountManager()

    result = manager.check_permissions()
    if not result["has_connection"]:
        sys.exit(1)


@snowddl_account.command()
def grant_roles():
    """Grant required roles to SnowDDL account"""
    manager = SnowDDLAccountManager()

    if not manager.grant_required_roles():
        sys.exit(1)


@snowddl_account.command()
def unlock():
    """Unlock SnowDDL account if locked"""
    manager = SnowDDLAccountManager()

    if not manager.unlock_account():
        sys.exit(1)


@snowddl_account.command()
def rotate_credentials():
    """Rotate SnowDDL account RSA credentials"""
    manager = SnowDDLAccountManager()

    if not manager.rotate_credentials():
        sys.exit(1)


@snowddl_account.command()
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def emergency_reset(confirm):
    """Emergency reset of SnowDDL account using backup credentials"""
    manager = SnowDDLAccountManager()

    if not confirm:
        from rich.prompt import Confirm

        if not Confirm.ask("⚠️ This will perform an emergency reset. Continue?"):
            console.print("❌ [yellow]Emergency reset cancelled[/yellow]")
            return

    if not manager.emergency_reset():
        sys.exit(1)


# Utility Commands
@click.command()
def generate_fernet_key():
    """Generate a new Fernet encryption key"""
    encryption = FernetEncryption()
    key = encryption.generate_key()

    console.print("🔑 [green]New Fernet encryption key generated:[/green]")
    console.print(f"[cyan]{key}[/cyan]")
    console.print("\n📝 [yellow]Important:[/yellow]")
    console.print("1. Store this key securely")
    console.print(
        "2. Set environment variable: [cyan]export SNOWFLAKE_CONFIG_FERNET_KEYS='{key}'[/cyan]"
    )
    console.print(
        "3. Add to .env file: [cyan]SNOWFLAKE_CONFIG_FERNET_KEYS={key}[/cyan]"
    )
    console.print("4. Never commit this key to version control")


# Main CLI group combining all commands
@click.group()
def main():
    """SnowTower User Management CLI"""
    pass


# Add all command groups
main.add_command(user)
main.add_command(snowddl_account, name="snowddl-account")
main.add_command(generate_fernet_key, name="generate-fernet-key")


if __name__ == "__main__":
    main()
