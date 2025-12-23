"""
Configuration validation CLI for SnowTower SnowDDL
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

try:
    from snowtower_schemas import ConfigurationValidator, ValidationResult

    SCHEMAS_AVAILABLE = True
except ImportError:
    SCHEMAS_AVAILABLE = False
    ConfigurationValidator = None
    ValidationResult = None


@click.group()
def validate():
    """Configuration validation commands for SnowDDL"""
    if not SCHEMAS_AVAILABLE:
        click.echo("❌ Configuration validation not available.")
        click.echo("Ensure SnowTower CLI project is available for shared schemas.")
        sys.exit(1)


@validate.command("config")
@click.option("--users", is_flag=True, help="Validate user configurations only")
@click.option(
    "--warehouses", is_flag=True, help="Validate warehouse configurations only"
)
@click.option("--security", is_flag=True, help="Validate security policies only")
@click.option("--mfa", is_flag=True, help="Check MFA compliance only")
@click.option("--cross-refs", is_flag=True, help="Validate cross-references only")
@click.option("--strict", is_flag=True, default=True, help="Use strict validation mode")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.option("--detailed", is_flag=True, help="Show detailed validation results")
def validate_config(
    users: bool,
    warehouses: bool,
    security: bool,
    mfa: bool,
    cross_refs: bool,
    strict: bool,
    output_format: str,
    detailed: bool,
):
    """
    Validate SnowDDL YAML configurations

    This command validates user configurations, warehouses, security policies,
    MFA compliance, and cross-references to ensure everything is properly
    configured and follows SnowTower standards.
    """
    if not SCHEMAS_AVAILABLE:
        click.echo("❌ Configuration validation not available.")
        sys.exit(1)

    console = Console()

    try:
        # Initialize validator with current directory
        validator = ConfigurationValidator(
            config_path=Path.cwd(), strict_mode=strict, test_connections=False
        )

        # Determine what to validate
        if users:
            result = validator._validate_users()
        elif warehouses:
            result = validator._validate_warehouses()
        elif security:
            result = validator.validate_security_policies()
        elif mfa:
            result = validator.validate_mfa_compliance()
        elif cross_refs:
            result = validator.validate_cross_references()
        else:
            # Validate SnowDDL-specific configurations
            result = validator.validate_snowddl_config()

            # Also validate cross-references
            cross_result = validator.validate_cross_references()
            result.merge(cross_result)

        # Output results
        if output_format == "json":
            click.echo(json.dumps(result.to_dict(), indent=2))
        elif output_format == "yaml":
            import yaml

            click.echo(yaml.dump(result.to_dict(), default_flow_style=False))
        else:
            result.print_summary(console, detailed=detailed)

        # Exit with appropriate code
        sys.exit(0 if result.is_valid() else 1)

    except Exception as e:
        console.print(f"❌ [red]Validation failed: {e}[/red]")
        sys.exit(1)


@validate.command("users")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.option("--show-details", is_flag=True, help="Show detailed user information")
def validate_users(output_format: str, show_details: bool):
    """
    Validate user configurations in user.yaml

    This validates all user entries for proper structure,
    security compliance, and MFA requirements.
    """
    if not SCHEMAS_AVAILABLE:
        click.echo("❌ Configuration validation not available.")
        sys.exit(1)

    console = Console()

    try:
        validator = ConfigurationValidator(config_path=Path.cwd())
        result = validator._validate_users()

        if output_format == "json":
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            result.print_summary(console, detailed=True)

            if show_details and result.is_valid():
                _show_user_details(console, validator)

        sys.exit(0 if result.is_valid() else 1)

    except Exception as e:
        console.print(f"❌ [red]User validation failed: {e}[/red]")
        sys.exit(1)


@validate.command("mfa")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.option(
    "--show-non-compliant", is_flag=True, help="Show details of non-compliant users"
)
def validate_mfa_compliance(output_format: str, show_non_compliant: bool):
    """
    Check MFA compliance for all users

    This validates that all PERSON users meet MFA requirements
    according to SnowTower security policies. SERVICE accounts
    are exempt from MFA requirements.
    """
    if not SCHEMAS_AVAILABLE:
        click.echo("❌ Configuration validation not available.")
        sys.exit(1)

    console = Console()

    try:
        validator = ConfigurationValidator(config_path=Path.cwd())
        result = validator.validate_mfa_compliance()

        if output_format == "json":
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            result.print_summary(console, detailed=True)

            if show_non_compliant:
                _show_mfa_compliance_details(console, validator)

        sys.exit(0 if result.is_valid() else 1)

    except Exception as e:
        console.print(f"❌ [red]MFA compliance check failed: {e}[/red]")
        sys.exit(1)


@validate.command("policies")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def validate_security_policies(output_format: str):
    """
    Validate security policies

    This validates network policies, authentication policies,
    password policies, and session policies for consistency
    and security best practices.
    """
    if not SCHEMAS_AVAILABLE:
        click.echo("❌ Configuration validation not available.")
        sys.exit(1)

    console = Console()

    try:
        validator = ConfigurationValidator(config_path=Path.cwd())
        result = validator.validate_security_policies()

        if output_format == "json":
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            result.print_summary(console, detailed=True)

        sys.exit(0 if result.is_valid() else 1)

    except Exception as e:
        console.print(f"❌ [red]Security policy validation failed: {e}[/red]")
        sys.exit(1)


@validate.command("cross-refs")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def validate_cross_references(output_format: str):
    """
    Validate cross-references between configurations

    This ensures that all policy references in user configurations
    point to valid, existing policies.
    """
    if not SCHEMAS_AVAILABLE:
        click.echo("❌ Configuration validation not available.")
        sys.exit(1)

    console = Console()

    try:
        validator = ConfigurationValidator(config_path=Path.cwd())
        result = validator.validate_cross_references()

        if output_format == "json":
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            result.print_summary(console, detailed=True)

        sys.exit(0 if result.is_valid() else 1)

    except Exception as e:
        console.print(f"❌ [red]Cross-reference validation failed: {e}[/red]")
        sys.exit(1)


def _show_user_details(console: Console, validator: ConfigurationValidator):
    """Show user configuration details"""
    try:
        from rich.table import Table
        from snowtower_schemas import SnowDDLUserConfig

        users = validator._load_users()

        table = Table(title="User Configuration Details")
        table.add_column("User", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Authentication", style="green")
        table.add_column("MFA Status", style="yellow")
        table.add_column("Network Policy", style="magenta")

        for username, user_config in users.items():
            try:
                user = SnowDDLUserConfig(**user_config)

                # Authentication methods
                auth_methods = user.get_authentication_methods()
                auth_str = ", ".join(auth_methods) if auth_methods else "None"

                # MFA status
                if user.is_mfa_compliant():
                    mfa_status = "✅ Compliant"
                else:
                    mfa_status = "❌ Non-compliant"

                # Network policy
                network_policy = user.network_policy or "None"

                table.add_row(
                    username, user.type.value, auth_str, mfa_status, network_policy
                )

            except Exception as e:
                table.add_row(username, "Error", f"❌ {e}", "Unknown", "Unknown")

        console.print(table)

    except Exception as e:
        console.print(f"⚠️ Could not show user details: {e}")


def _show_mfa_compliance_details(console: Console, validator: ConfigurationValidator):
    """Show MFA compliance details"""
    try:
        from rich.table import Table
        from snowtower_schemas import SnowDDLUserConfig

        users = validator._load_users()

        table = Table(title="MFA Compliance Status")
        table.add_column("User", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("MFA Compliant", style="yellow")
        table.add_column("Reason", style="green")

        for username, user_config in users.items():
            try:
                user = SnowDDLUserConfig(**user_config)

                if user.type.value == "SERVICE":
                    table.add_row(
                        username, user.type.value, "✅ N/A", "Service accounts exempt"
                    )
                elif user.is_mfa_compliant():
                    reason = []
                    if user.authentication_policy:
                        reason.append("Auth policy")
                    if user.rsa_public_key and user.password:
                        reason.append("Dual auth")

                    table.add_row(
                        username,
                        user.type.value,
                        "✅ Yes",
                        ", ".join(reason) or "Unknown",
                    )
                else:
                    table.add_row(
                        username,
                        user.type.value,
                        "❌ No",
                        "Missing auth policy or dual authentication",
                    )

            except Exception as e:
                table.add_row(username, "Error", "❌ Error", str(e))

        console.print(table)

    except Exception as e:
        console.print(f"⚠️ Could not show MFA compliance details: {e}")


if __name__ == "__main__":
    validate()
