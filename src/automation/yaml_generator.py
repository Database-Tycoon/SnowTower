"""
SnowDDL YAML Generator for User Configurations

Generates valid SnowDDL YAML configurations from parsed GitHub issue data.
Handles user creation with encryption, role mapping, and security policies.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from rich.console import Console

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from user_management.manager import UserManager
from user_management.encryption import FernetEncryption
from user_management.rsa_keys import RSAKeyManager
from user_management.password_generator import PasswordGenerator
from .issue_parser import ParsedIssueData, RoleTypeSelection, WorkloadSize

console = Console()


class YAMLGenerationError(Exception):
    """Raised when YAML generation fails"""

    pass


@dataclass
class GeneratedUserConfig:
    """Complete user configuration with credentials and metadata"""

    username: str
    yaml_config: Dict[str, Any]
    private_key_path: Optional[Path] = None
    temp_password: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "username": self.username,
            "yaml_config": self.yaml_config,
            "private_key_path": (
                str(self.private_key_path) if self.private_key_path else None
            ),
            "temp_password": self.temp_password,
            "metadata": self.metadata or {},
        }


class SnowDDLYAMLGenerator:
    """
    Generates SnowDDL-compliant YAML configurations from parsed issue data.

    Integrates with existing user management infrastructure for:
    - Password encryption
    - RSA key generation
    - Role mapping
    - Security policy assignment
    """

    # Role mapping from issue selections to Snowflake business roles
    ROLE_MAPPING = {
        RoleTypeSelection.DATA_ANALYST: ["COMPANY_USERS"],
        RoleTypeSelection.BI_DEVELOPER: ["BI_DEVELOPER_ROLE"],
        RoleTypeSelection.DATA_ENGINEER: ["COMPANY_USERS", "DATA_ENGINEER_ROLE"],
        RoleTypeSelection.TRAINING: ["TRAINING_ROLE"],
        RoleTypeSelection.INTEGRATION_SERVICE: ["DATA_INTEGRATION_ROLE"],
        RoleTypeSelection.AI_ML_SERVICE: ["AI_ML_ROLE"],
    }

    # Warehouse mapping from workload sizes
    WAREHOUSE_MAPPING = {
        WorkloadSize.LIGHT: "MAIN_WAREHOUSE",
        WorkloadSize.MEDIUM: "TRANSFORMING",
        WorkloadSize.HEAVY: "MAIN_WAREHOUSE",  # Requires admin review
        WorkloadSize.DEVELOPMENT: "DEV_WH",
    }

    def __init__(self):
        """Initialize the YAML generator with user management components"""
        self.user_manager = UserManager()
        self.encryption = FernetEncryption()
        self.rsa_manager = RSAKeyManager()
        self.password_generator = PasswordGenerator(self.encryption)

    def generate_from_issue_data(
        self,
        parsed_data: ParsedIssueData,
        generate_rsa_keys: bool = True,
        generate_password: bool = True,
        password_length: int = 16,
    ) -> GeneratedUserConfig:
        """
        Generate complete user configuration from parsed issue data.

        Args:
            parsed_data: ParsedIssueData from GitHubIssueParser
            generate_rsa_keys: Whether to generate RSA key pair
            generate_password: Whether to generate temporary password
            password_length: Length of generated password

        Returns:
            GeneratedUserConfig with complete user setup

        Raises:
            YAMLGenerationError: If generation fails
        """
        try:
            # Generate username if not provided
            username = self._generate_username(parsed_data)

            # Validate username doesn't already exist
            if self.user_manager.get_user(username):
                raise YAMLGenerationError(
                    f"User {username} already exists in configuration"
                )

            # Split full name
            first_name, last_name = self._split_name(parsed_data.full_name)

            # Map roles and warehouse
            business_roles = self._map_roles(parsed_data)
            default_warehouse = self._map_warehouse(parsed_data.warehouse_size)

            # Build base user configuration
            user_config = {
                "type": (
                    "SERVICE" if parsed_data.user_type.value == "service" else "PERSON"
                ),
                "first_name": first_name,
                "last_name": last_name,
                "login_name": username,
                "display_name": parsed_data.full_name,
                "email": parsed_data.email,
                "business_roles": business_roles,
                "default_warehouse": default_warehouse,
                "comment": self._generate_comment(parsed_data),
                "disabled": False,
            }

            private_key_path = None
            temp_password = None

            # Generate RSA keys if requested
            if generate_rsa_keys:
                try:
                    # Use provided RSA key if available
                    if parsed_data.rsa_public_key:
                        console.print(
                            f"[cyan]Using RSA public key provided in issue[/cyan]"
                        )
                        user_config["rsa_public_key"] = self._format_rsa_key(
                            parsed_data.rsa_public_key
                        )
                    else:
                        # Generate new RSA keys
                        (
                            private_key_path,
                            public_key_path,
                        ) = self.rsa_manager.generate_key_pair(username)
                        public_key_content = (
                            self.rsa_manager.extract_public_key_for_snowflake(
                                private_key_path
                            )
                        )
                        user_config["rsa_public_key"] = public_key_content
                        console.print(
                            f"[green]✓ Generated RSA key pair for {username}[/green]"
                        )

                except Exception as e:
                    console.print(f"[yellow]⚠ RSA key generation failed: {e}[/yellow]")
                    console.print("[yellow]Continuing without RSA keys...[/yellow]")

            # Generate password if requested
            if generate_password:
                try:
                    password_info = self.password_generator.generate_user_password(
                        username=username,
                        user_type=user_config["type"],
                        length=password_length,
                    )

                    user_config["password"] = password_info["yaml_value"]
                    temp_password = password_info["plain_password"]
                    console.print(
                        f"[green]✓ Generated encrypted password for {username}[/green]"
                    )

                except Exception as e:
                    console.print(f"[yellow]⚠ Password generation failed: {e}[/yellow]")
                    console.print(
                        "[yellow]User will be created without password[/yellow]"
                    )

            # Add security policies for PERSON users
            if user_config["type"] == "PERSON":
                user_config["network_policy"] = "company_network_policy"
                # MFA policy will be inherited from account settings

            # Build metadata
            metadata = {
                "username": username,
                "email": parsed_data.email,
                "manager_email": parsed_data.manager_email,
                "business_justification": parsed_data.business_justification,
                "urgency": parsed_data.urgency,
                "project_team": parsed_data.project_team,
                "request_date": datetime.now().isoformat(),
                "issue_number": parsed_data.issue_number,
                "issue_url": parsed_data.issue_url,
            }

            return GeneratedUserConfig(
                username=username,
                yaml_config={username: user_config},
                private_key_path=private_key_path,
                temp_password=temp_password,
                metadata=metadata,
            )

        except Exception as e:
            raise YAMLGenerationError(f"Failed to generate user configuration: {e}")

    def _generate_username(self, parsed_data: ParsedIssueData) -> str:
        """Generate username from parsed data"""
        if parsed_data.username:
            return parsed_data.username.strip().upper()

        # Generate from full name
        parts = parsed_data.full_name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[-1]}".upper()
        else:
            return parts[0].upper()

    def _split_name(self, full_name: str) -> Tuple[str, str]:
        """Split full name into first and last name"""
        parts = full_name.strip().split()
        if len(parts) == 0:
            return "", ""
        elif len(parts) == 1:
            return parts[0], ""
        else:
            return parts[0], parts[-1]

    def _map_roles(self, parsed_data: ParsedIssueData) -> List[str]:
        """Map issue role selection to Snowflake business roles"""
        if parsed_data.role_type and parsed_data.role_type in self.ROLE_MAPPING:
            return self.ROLE_MAPPING[parsed_data.role_type]

        # Default role based on user type
        if parsed_data.user_type.value == "service":
            return ["SERVICE_ROLE"]
        else:
            return ["COMPANY_USERS"]

    def _map_warehouse(self, workload_size: WorkloadSize) -> str:
        """Map workload size to warehouse"""
        return self.WAREHOUSE_MAPPING.get(workload_size, "MAIN_WAREHOUSE")

    def _generate_comment(self, parsed_data: ParsedIssueData) -> str:
        """Generate descriptive comment for user"""
        comment_parts = []

        # Role information
        if parsed_data.role_type:
            role_name = parsed_data.role_type.value.replace("_", " ").title()
            comment_parts.append(f"{role_name}")

        # Source
        if parsed_data.issue_number:
            comment_parts.append(f"GitHub Issue #{parsed_data.issue_number}")
        else:
            comment_parts.append("Generated from access request")

        # Project/Team
        if parsed_data.project_team:
            comment_parts.append(f"Team: {parsed_data.project_team}")

        # Date
        comment_parts.append(f"Created: {datetime.now().strftime('%Y-%m-%d')}")

        # Security note
        if parsed_data.user_type.value == "person":
            comment_parts.append("MFA enforced")

        return " - ".join(comment_parts)

    def _format_rsa_key(self, rsa_key: str) -> str:
        """Format RSA public key for Snowflake"""
        # Remove any SSH or PEM headers/footers
        key = rsa_key.strip()
        key = key.replace("-----BEGIN PUBLIC KEY-----", "")
        key = key.replace("-----END PUBLIC KEY-----", "")
        key = key.replace("-----BEGIN RSA PUBLIC KEY-----", "")
        key = key.replace("-----END RSA PUBLIC KEY-----", "")
        key = key.replace("ssh-rsa ", "")

        # Remove whitespace and newlines
        key = "".join(key.split())

        return key

    def validate_generated_config(
        self, config: GeneratedUserConfig
    ) -> Tuple[bool, List[str]]:
        """
        Validate generated configuration.

        Args:
            config: GeneratedUserConfig to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        yaml_config = config.yaml_config.get(config.username, {})

        # Required fields
        required_fields = ["type", "login_name", "email"]
        for field in required_fields:
            if not yaml_config.get(field):
                errors.append(f"Missing required field: {field}")

        # Type-specific validation
        if yaml_config.get("type") == "PERSON":
            person_required = ["first_name", "last_name"]
            for field in person_required:
                if not yaml_config.get(field):
                    errors.append(f"PERSON user missing required field: {field}")

        # Authentication validation
        has_password = bool(yaml_config.get("password"))
        has_rsa_key = bool(yaml_config.get("rsa_public_key"))

        if not has_password and not has_rsa_key:
            errors.append(
                "User must have at least one authentication method (password or RSA key)"
            )

        # Business roles validation
        if not yaml_config.get("business_roles"):
            errors.append("User must have at least one business role assigned")

        # Warehouse validation
        if not yaml_config.get("default_warehouse"):
            errors.append("User must have a default warehouse assigned")

        is_valid = len(errors) == 0
        return is_valid, errors
