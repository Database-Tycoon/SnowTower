#!/usr/bin/env python3
"""
GitHub Issue to SnowDDL Automation Script

Automates the complete workflow from GitHub issue to SnowDDL user deployment:
1. Parse GitHub issue containing access request
2. Extract and validate user data
3. Generate SnowDDL YAML configuration
4. Create git branch and pull request
5. Optional: Check S3 for Streamlit-generated configs

Usage:
    # Process issue by number (uses gh CLI)
    uv run github-to-snowddl --issue 123

    # Process issue from JSON file
    uv run github-to-snowddl --issue-file issue.json

    # Dry run (show what would be generated)
    uv run github-to-snowddl --issue 123 --dry-run

    # Skip PR creation (just generate config)
    uv run github-to-snowddl --issue 123 --no-pr

    # Check S3 for existing config
    uv run github-to-snowddl --issue 123 --check-s3

Environment Variables:
    SNOWFLAKE_CONFIG_FERNET_KEYS: Required for password encryption
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

# Load environment variables FIRST (MANDATORY)
from dotenv import load_dotenv

load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

# Import automation components
from automation.issue_parser import (
    GitHubIssueParser,
    IssueParsingError,
    ParsedIssueData,
)
from automation.yaml_generator import (
    SnowDDLYAMLGenerator,
    YAMLGenerationError,
    GeneratedUserConfig,
)
from automation.pr_creator import GitHubPRCreator, PRCreationError, PRResult
from automation.validator import UserConfigValidator, ValidationError

console = Console()


class AutomationError(Exception):
    """Base exception for automation errors"""

    pass


def check_s3_config(username: str) -> Optional[Dict[str, Any]]:
    """
    Check if user configuration exists in S3 (from Streamlit app).

    Args:
        username: Username to check for

    Returns:
        User configuration from S3 if found, None otherwise
    """
    try:
        import snowflake.connector
        from snowflake.connector import DictCursor

        # Connect to Snowflake
        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            private_key_path=os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "MAIN_WAREHOUSE"),
            database="SNOWTOWER_DB",
            schema="CONFIG",
        )

        cursor = conn.cursor(DictCursor)

        # Query S3 stage for config
        query = f"""
        SELECT $1 as config_data
        FROM @SNOWTOWER_DB.CONFIG.USER_CONFIGS_STAGE/{username.lower()}_config.yaml
        """

        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            config_yaml = result["config_data"]
            config = yaml.safe_load(config_yaml)
            console.print(
                f"[green]✓ Found existing config in S3 for {username}[/green]"
            )
            return config

        return None

    except Exception as e:
        console.print(f"[yellow]⚠ Could not check S3: {e}[/yellow]")
        return None
    finally:
        if "conn" in locals():
            conn.close()


def display_parsed_data(parsed_data: ParsedIssueData):
    """Display parsed issue data in a formatted table"""
    table = Table(title="Parsed Access Request Data")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Full Name", parsed_data.full_name)
    table.add_row("Email", parsed_data.email)
    table.add_row("Username", parsed_data.username or "[Generated]")
    table.add_row("User Type", parsed_data.user_type.value.upper())

    if parsed_data.role_type:
        table.add_row(
            "Role Type", parsed_data.role_type.value.replace("_", " ").title()
        )

    table.add_row("Workload Size", parsed_data.warehouse_size.value.upper())
    table.add_row("Project/Team", parsed_data.project_team or "N/A")
    table.add_row("Urgency", parsed_data.urgency)

    if parsed_data.manager_email:
        table.add_row("Manager Email", parsed_data.manager_email)

    table.add_row(
        "Data Handling Confirmed", "✓" if parsed_data.data_handling_confirmed else "✗"
    )

    console.print(table)

    # Show business justification separately
    console.print("\n[bold cyan]Business Justification:[/bold cyan]")
    console.print(Panel(parsed_data.business_justification, border_style="blue"))


def display_generated_config(config: GeneratedUserConfig):
    """Display generated user configuration"""
    table = Table(title=f"Generated Configuration: {config.username}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    user_data = config.yaml_config.get(config.username, {})

    table.add_row("Username", config.username)
    table.add_row("Type", user_data.get("type", "N/A"))
    table.add_row("Email", user_data.get("email", "N/A"))
    table.add_row("Display Name", user_data.get("display_name", "N/A"))
    table.add_row("Business Roles", ", ".join(user_data.get("business_roles", [])))
    table.add_row("Default Warehouse", user_data.get("default_warehouse", "N/A"))

    # Authentication
    auth_methods = []
    if user_data.get("password"):
        auth_methods.append("Password (encrypted)")
    if user_data.get("rsa_public_key"):
        auth_methods.append("RSA Key")

    table.add_row("Authentication", ", ".join(auth_methods) if auth_methods else "None")

    # Security policies
    if user_data.get("network_policy"):
        table.add_row("Network Policy", user_data["network_policy"])
    if user_data.get("authentication_policy"):
        table.add_row("Auth Policy", user_data["authentication_policy"])

    console.print(table)

    # Show credentials if generated
    if config.temp_password or config.private_key_path:
        console.print("\n[bold yellow]🔐 Generated Credentials[/bold yellow]")

        creds_table = Table(show_header=False)
        creds_table.add_column("Item", style="cyan")
        creds_table.add_column("Value", style="red")

        if config.temp_password:
            creds_table.add_row("Temporary Password", config.temp_password)
            creds_table.add_row(
                "", "[dim]Save this securely - will not be shown again[/dim]"
            )

        if config.private_key_path:
            creds_table.add_row("Private Key Path", str(config.private_key_path))
            creds_table.add_row("", "[dim]Deliver to user via secure channel[/dim]")

        console.print(creds_table)


def save_artifacts(config: GeneratedUserConfig, output_dir: Path):
    """Save generated artifacts to files"""
    output_dir.mkdir(parents=True, exist_ok=True)

    username = config.username

    # Save YAML config
    yaml_file = output_dir / f"{username}_user.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(config.yaml_config, f, default_flow_style=False, sort_keys=False)

    # Save credentials
    credentials_file = output_dir / f"{username}_credentials.json"
    credentials_data = {
        "username": username,
        "email": config.yaml_config[username].get("email"),
        "temporary_password": config.temp_password,
        "private_key_path": str(config.private_key_path)
        if config.private_key_path
        else None,
        "metadata": config.metadata,
    }

    with open(credentials_file, "w") as f:
        json.dump(credentials_data, f, indent=2)

    # Secure permissions
    credentials_file.chmod(0o600)

    # Copy private key if exists
    if config.private_key_path and config.private_key_path.exists():
        import shutil

        dest_key = output_dir / f"{username}_private_key.pem"
        shutil.copy2(config.private_key_path, dest_key)
        dest_key.chmod(0o600)

    console.print(f"\n[green]✓ Artifacts saved to: {output_dir}[/green]")
    console.print(f"  • {yaml_file.name}")
    console.print(f"  • {credentials_file.name}")
    if config.private_key_path:
        console.print(f"  • {username}_private_key.pem")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="GitHub Issue to SnowDDL Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input sources (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--issue", type=int, help="GitHub issue number to process")
    input_group.add_argument(
        "--issue-file", type=Path, help="Path to JSON file containing issue data"
    )

    # Options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "generated_users",
        help="Output directory for generated files (default: ./generated_users)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without creating PR",
    )
    parser.add_argument(
        "--no-pr", action="store_true", help="Generate config but skip PR creation"
    )
    parser.add_argument(
        "--check-s3",
        action="store_true",
        help="Check S3 for existing Streamlit-generated config",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip security validation (not recommended)",
    )
    parser.add_argument(
        "--base-branch", default="main", help="Base branch for PR (default: main)"
    )

    args = parser.parse_args()

    try:
        # Check for Fernet key
        if not os.getenv("SNOWFLAKE_CONFIG_FERNET_KEYS"):
            console.print(
                "[red]Error: SNOWFLAKE_CONFIG_FERNET_KEYS environment variable not set[/red]"
            )
            console.print("Run: [cyan]uv run util-generate-key[/cyan] to generate one")
            return 1

        console.print(
            Panel(
                "[bold blue]SnowTower GitHub Issue Automation[/bold blue]\n\n"
                "Processing access request and generating SnowDDL configuration",
                border_style="blue",
            )
        )

        # Step 1: Parse GitHub Issue
        console.print("\n[bold cyan]Step 1: Parsing GitHub Issue[/bold cyan]")
        parser_engine = GitHubIssueParser()

        if args.issue:
            parsed_data = parser_engine.parse_from_gh_api(args.issue)
        else:
            with open(args.issue_file, "r") as f:
                issue_data = json.load(f)
            parsed_data = parser_engine.parse_issue(issue_data.get("body", ""))

        display_parsed_data(parsed_data)

        # Step 2: Check S3 for existing config (if requested)
        if args.check_s3:
            console.print(
                "\n[bold cyan]Step 2: Checking S3 for Existing Config[/bold cyan]"
            )
            username = (
                parser_engine._generate_username(parsed_data)
                if not parsed_data.username
                else parsed_data.username
            )
            s3_config = check_s3_config(username)

            if s3_config:
                console.print(
                    "[yellow]Found existing config in S3. Merge or override?[/yellow]"
                )
                # Could implement merge logic here

        # Step 3: Generate YAML Configuration
        console.print(
            "\n[bold cyan]Step 3: Generating SnowDDL Configuration[/bold cyan]"
        )
        generator = SnowDDLYAMLGenerator()

        config = generator.generate_from_issue_data(
            parsed_data,
            generate_rsa_keys=True,
            generate_password=True,
            password_length=16,
        )

        display_generated_config(config)

        # Step 4: Validate Configuration
        if not args.skip_validation:
            console.print("\n[bold cyan]Step 4: Security Validation[/bold cyan]")
            validator = UserConfigValidator(strict_mode=True)

            validation_result = validator.validate_user_config(
                config.username, config.yaml_config[config.username]
            )

            validation_result.print_summary()

            if not validation_result.is_valid:
                console.print("\n[red]Validation failed! Cannot proceed.[/red]")
                return 1

            if validation_result.warnings and not args.dry_run:
                from rich.prompt import Confirm

                if not Confirm.ask("Warnings detected. Continue anyway?"):
                    console.print("[yellow]Cancelled by user[/yellow]")
                    return 0

        # Step 5: Save Artifacts
        console.print("\n[bold cyan]Step 5: Saving Artifacts[/bold cyan]")
        save_artifacts(config, args.output_dir)

        # Step 6: Create Pull Request (unless skipped)
        if not args.dry_run and not args.no_pr:
            console.print("\n[bold cyan]Step 6: Creating Pull Request[/bold cyan]")

            pr_creator = GitHubPRCreator()

            pr_result = pr_creator.create_user_deployment_pr(
                username=config.username,
                yaml_config=config.yaml_config,
                issue_number=parsed_data.issue_number,
                metadata=config.metadata,
                base_branch=args.base_branch,
            )

            console.print(f"\n[green]✓ Pull request created successfully![/green]")
            console.print(
                f"[green]  PR #{pr_result.pr_number}: {pr_result.pr_url}[/green]"
            )
            console.print(f"[green]  Branch: {pr_result.branch_name}[/green]")

        # Summary
        console.print("\n[bold green]🎉 Automation Complete![/bold green]")

        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        if args.dry_run:
            console.print(
                "  1. Review generated configuration in:", str(args.output_dir)
            )
            console.print("  2. Run without --dry-run to create PR")
        elif args.no_pr:
            console.print(
                "  1. Review generated configuration in:", str(args.output_dir)
            )
            console.print("  2. Manually merge into snowddl/user.yaml")
            console.print("  3. Run: [cyan]uv run snowddl-plan[/cyan]")
            console.print("  4. Run: [cyan]uv run snowddl-apply[/cyan]")
        else:
            console.print("  1. Review and approve the pull request")
            console.print("  2. Merge PR to trigger deployment")
            console.print("  3. Deliver credentials to user securely:")
            console.print(
                f"     • Password: {config.temp_password if config.temp_password else 'N/A'}"
            )
            if config.private_key_path:
                console.print(f"     • Private Key: {config.private_key_path}")
            console.print("  4. Verify user can authenticate to Snowflake")

        return 0

    except IssueParsingError as e:
        console.print(f"[red]Issue Parsing Error: {e}[/red]")
        return 1
    except YAMLGenerationError as e:
        console.print(f"[red]YAML Generation Error: {e}[/red]")
        return 1
    except PRCreationError as e:
        console.print(f"[red]PR Creation Error: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Unexpected Error: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
