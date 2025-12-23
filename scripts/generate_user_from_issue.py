#!/usr/bin/env python3
"""
Generate User from GitHub Issue Script

Automatically generates a user YAML entry from a GitHub issue access request.
This script is designed to be called by GitHub Actions workflows.

Features:
- Parses GitHub issue data (JSON format)
- Generates secure RSA key pairs automatically
- Creates encrypted temporary passwords
- Maps roles based on user selections
- Validates user data before generation
- Creates proper YAML formatting for SnowDDL

Usage:
    python generate_user_from_issue.py --issue-data issue.json --output user_entry.yaml
    python generate_user_from_issue.py --issue-json '{"title": "...", "body": "..."}' --username JOHN_SMITH

Environment Variables:
    SNOWFLAKE_CONFIG_FERNET_KEYS: Required for password encryption
"""

import argparse
import json
import os
import re
import sys
import tempfile
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import our user management system
from user_management.manager import UserManager
from user_management.password_generator import PasswordGenerator
from user_management.rsa_keys import RSAKeyManager
from user_management.encryption import FernetEncryption

console = Console()


class IssueParsingError(Exception):
    """Raised when issue data cannot be parsed"""

    pass


class UserGenerationError(Exception):
    """Raised when user generation fails"""

    pass


# Initialize our user management components
def get_user_manager() -> UserManager:
    """Get UserManager instance for user creation"""
    return UserManager()


def get_rsa_manager() -> RSAKeyManager:
    """Get RSA key manager for key generation"""
    return RSAKeyManager()


def get_password_generator() -> PasswordGenerator:
    """Get password generator for secure password creation"""
    return PasswordGenerator()


def parse_issue_body(body: str) -> Dict[str, Any]:
    """
    Parse GitHub issue body and extract form data

    Args:
        body: Raw issue body text

    Returns:
        Dictionary with parsed form data
    """
    data = {}

    # Define patterns for each field (supports both old and new simplified format)
    patterns = {
        "full_name": r"### Full Name\s*\n\s*(.+)",
        "email": r"### Email Address\s*\n\s*(.+)",
        "username": r"### Preferred Username\s*\n\s*(.+)",
        "user_type": r"### (?:Account Type|What type of user are you\?)\s*\n\s*(.+)",
        "role_type": r"### Primary Role\s*\n\s*(.+)",
        "warehouse_size": r"### Expected Workload\s*\n\s*(.+)",
        "business_justification": r"### (?:Business Justification|Why do you need access\?)\s*\n\s*((?:.|\n)*?)(?=\n### |$)",
        "manager_email": r"### (?:Manager/Sponsor Email|Manager Email)\s*\n\s*(.+)",
        "project_team": r"### Project/Team\s*\n\s*(.+)",
        "urgency": r"### Urgency Level\s*\n\s*(.+)",
        "urgency_justification": r"### Urgency Justification\s*\n\s*((?:.|\n)*?)(?=\n### |$)",
        "additional_comments": r"### Additional Comments\s*\n\s*((?:.|\n)*?)(?=\n### |$)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Clean up common form artifacts
            if value and value not in ["_No response_", "No response", ""]:
                data[field] = value

    # Parse checkboxes
    data["data_handling_confirmed"] = bool(
        re.search(
            r"\[x\].*I understand that I will have access to sensitive business data",
            body,
            re.IGNORECASE,
        )
    )

    return data


def map_role_to_business_role(role_selection: str) -> List[str]:
    """Map role selection to actual business role names"""
    role_mapping = {
        "data analyst": ["COMPANY_USERS"],
        "bi developer": ["BI_DEVELOPER_ROLE"],
        "data engineer": ["COMPANY_USERS"],
        "training": ["TRAINING_ROLE"],
        "training user": ["TRAINING_ROLE"],
        "learning": ["TRAINING_ROLE"],
        "integration service": ["DATA_INTEGRATION_ROLE"],
        "ai/ml service": ["AI_ML_ROLE"],
        "service account": ["COMPANY_USERS"],  # Default for service accounts
    }

    # Default to COMPANY_USERS if no match
    for key, roles in role_mapping.items():
        if key in role_selection.lower():
            return roles

    return ["COMPANY_USERS"]


def map_workload_to_warehouse(workload: str) -> str:
    """Map workload selection to warehouse name"""
    workload_mapping = {
        "light": "MAIN_WAREHOUSE",
        "medium": "TRANSFORMING",
        "heavy": "MAIN_WAREHOUSE",  # Will require admin review
        "development": "DEV_WH",
    }

    for key, warehouse in workload_mapping.items():
        if key in workload.lower():
            return warehouse

    return "MAIN_WAREHOUSE"


def generate_username(full_name: str, preferred_username: Optional[str] = None) -> str:
    """Generate username from full name or use preferred"""
    if preferred_username and preferred_username.strip():
        return preferred_username.strip().upper()

    # Generate from full name
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[-1]}".upper()
    else:
        return parts[0].upper()


def validate_user_data(data: Dict[str, Any]) -> List[str]:
    """Validate user data and return list of errors"""
    errors = []

    required_fields = [
        "full_name",
        "email",
        "user_type",
        "role_type",
        "business_justification",
    ]
    for field in required_fields:
        if not data.get(field):
            errors.append(f"Missing required field: {field}")

    # Validate email format
    email = data.get("email", "")
    if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        errors.append(f"Invalid email format: {email}")

    # Validate data handling confirmation
    if not data.get("data_handling_confirmed"):
        errors.append("Data handling acknowledgment not confirmed")

    return errors


def generate_user_yaml(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate user YAML entry from parsed issue data using integrated user management

    Args:
        data: Parsed issue data

    Returns:
        Dictionary representing user YAML entry
    """
    # Validate data first
    errors = validate_user_data(data)
    if errors:
        raise UserGenerationError(f"Validation errors: {', '.join(errors)}")

    # Generate username
    username = generate_username(data["full_name"], data.get("username"))

    # Split full name
    name_parts = data["full_name"].strip().split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""

    # Determine user type
    user_type = "SERVICE" if "service" in data["user_type"].lower() else "PERSON"

    # Use our integrated user management system
    rsa_manager = get_rsa_manager()
    password_generator = get_password_generator()

    try:
        # Generate RSA keys using our system
        private_key_path, public_key_path = rsa_manager.generate_key_pair(username)
        public_key_content = rsa_manager.extract_public_key_for_snowflake(
            private_key_path
        )

        # Generate secure password using our system
        password_info = password_generator.generate_user_password(
            username=username, user_type=user_type, length=16
        )

        # Map roles and warehouse
        business_roles = map_role_to_business_role(data["role_type"])
        default_warehouse = map_workload_to_warehouse(data.get("warehouse_size", ""))

        # Create comment
        comment_parts = [
            f"{data['role_type']} - Generated from access request",
            f"Project: {data.get('project_team', 'Unspecified')}",
            f"Request date: {datetime.now().strftime('%Y-%m-%d')}",
            "RSA key authentication enabled - MFA enforced",
        ]
        comment = " - ".join(comment_parts)

        # Build user entry
        user_entry = {
            "type": user_type,
            "first_name": first_name,
            "last_name": last_name,
            "login_name": username,
            "display_name": data["full_name"],
            "comment": comment,
            "email": data["email"],
            "business_roles": business_roles,
            "default_warehouse": default_warehouse,
            "rsa_public_key": public_key_content,
            "password": password_info["yaml_value"],
        }

        # Add network policy for PERSON type
        if user_type == "PERSON":
            user_entry["network_policy"] = "company_network_policy"

        # Return both user entry and credentials for secure delivery
        return {
            "user_entry": {username: user_entry},
            "private_key_path": str(private_key_path),
            "temp_password": password_info["plain_password"],
            "metadata": {
                "username": username,
                "email": data["email"],
                "manager_email": data.get("manager_email"),
                "business_justification": data["business_justification"],
                "urgency": data.get("urgency", "Standard"),
                "project_team": data.get("project_team", "Unspecified"),
                "request_date": datetime.now().isoformat(),
            },
        }

    except Exception as e:
        raise UserGenerationError(f"Failed to generate credentials for {username}: {e}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Generate User from GitHub Issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--issue-data", type=Path, help="Path to JSON file containing GitHub issue data"
    )
    input_group.add_argument(
        "--issue-json", type=str, help="JSON string containing GitHub issue data"
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Output directory for generated files (default: current directory)",
    )
    parser.add_argument(
        "--username", type=str, help="Override username (useful for testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without creating files",
    )

    args = parser.parse_args()

    try:
        # Check for Fernet key
        if not os.getenv("SNOWFLAKE_CONFIG_FERNET_KEYS"):
            console.print(
                "[red]Error: SNOWFLAKE_CONFIG_FERNET_KEYS environment variable not set[/red]"
            )
            return 1

        # Load issue data
        if args.issue_data:
            if not args.issue_data.exists():
                raise IssueParsingError(f"Issue data file not found: {args.issue_data}")
            with open(args.issue_data, "r") as f:
                issue_data = json.load(f)
        else:
            issue_data = json.loads(args.issue_json)

        # Parse issue body
        console.print("[cyan]Parsing GitHub issue data...[/cyan]")
        parsed_data = parse_issue_body(issue_data.get("body", ""))

        # Override username if provided
        if args.username:
            parsed_data["username"] = args.username

        # Display parsed data
        console.print("\n[green]Parsed Issue Data:[/green]")
        table = Table(title="Access Request Details")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        for key, value in parsed_data.items():
            if key != "business_justification":  # Too long for table
                table.add_row(key.replace("_", " ").title(), str(value)[:80])

        console.print(table)

        # Generate user configuration
        console.print("\n[cyan]Generating user configuration...[/cyan]")
        result = generate_user_yaml(parsed_data)

        user_yaml = result["user_entry"]
        private_key_path = result["private_key_path"]
        temp_password = result["temp_password"]
        metadata = result["metadata"]

        username = metadata["username"]

        if args.dry_run:
            console.print("\n[yellow]DRY RUN - Files would be created:[/yellow]")
            console.print(f"  • {args.output_dir / f'{username}_user.yaml'}")
            console.print(f"  • {args.output_dir / f'{username}_credentials.json'}")
            console.print(f"  • RSA keys already generated in: {private_key_path}")

            console.print("\n[yellow]Generated User YAML:[/yellow]")
            console.print(
                yaml.dump(user_yaml, default_flow_style=False, sort_keys=False)
            )

            return 0

        # Create output directory
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Write user YAML
        user_yaml_file = args.output_dir / f"{username}_user.yaml"
        with open(user_yaml_file, "w") as f:
            yaml.dump(user_yaml, f, default_flow_style=False, sort_keys=False)

        # Copy private key to output directory (the key was already generated by RSA manager)
        import shutil

        output_private_key_file = args.output_dir / f"{username}_private_key.pem"
        shutil.copy2(private_key_path, output_private_key_file)
        output_private_key_file.chmod(0o600)  # Secure permissions

        # Write credentials and metadata
        credentials_file = args.output_dir / f"{username}_credentials.json"
        credentials_data = {
            "username": username,
            "email": metadata["email"],
            "temporary_password": temp_password,
            "private_key_file": str(output_private_key_file),
            "setup_instructions": "Use RSA key for authentication. Password is for emergency use only.",
            "metadata": metadata,
        }
        with open(credentials_file, "w") as f:
            json.dump(credentials_data, f, indent=2)
        credentials_file.chmod(0o600)  # Secure permissions

        # Display success message
        console.print(f"\n[green]✓ User configuration generated successfully![/green]")
        console.print(f"[green]✓ Username: {username}[/green]")
        console.print(f"[green]✓ Files created in: {args.output_dir}[/green]")

        # Display next steps
        console.print("\n[bold]Generated Files:[/bold]")
        console.print(
            f"  • [cyan]{user_yaml_file}[/cyan] - Add this to snowddl/user.yaml"
        )
        console.print(
            f"  • [cyan]{output_private_key_file}[/cyan] - Deliver securely to user"
        )
        console.print(
            f"  • [cyan]{credentials_file}[/cyan] - Complete credential package"
        )

        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Review the generated user configuration")
        console.print("  2. Add the YAML content to snowddl/user.yaml")
        console.print("  3. Run: [cyan]uv run snowddl-plan[/cyan] to preview changes")
        console.print("  4. Run: [cyan]uv run snowddl-apply[/cyan] to create the user")
        console.print("  5. Securely deliver credentials to the user")

        return 0

    except (IssueParsingError, UserGenerationError) as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
