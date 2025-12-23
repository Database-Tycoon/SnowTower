"""
Main User Management System for SnowTower SnowDDL

Unified user management orchestrator that coordinates all user operations
through a single, cohesive interface. Integrates encryption, RSA keys,
YAML handling, and SnowDDL account management.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from enum import Enum
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .encryption import FernetEncryption, FernetEncryptionError
from .rsa_keys import RSAKeyManager, RSAKeyError
from .yaml_handler import YAMLHandler, YAMLError
from .snowddl_account import SnowDDLAccountManager
from .password_generator import PasswordGenerator, PasswordGenerationError

# Import monitoring components
try:
    from snowtower_core.logging import (
        get_logger,
        correlation_context,
        log_operation_start,
        log_operation_success,
        log_operation_failure,
    )
    from snowtower_core.audit import get_audit_logger, AuditAction
    from snowtower_core.metrics import get_metrics, track_operation

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

    # Fallback no-op implementations
    def get_logger(name):
        import logging

        return logging.getLogger(name)

    def correlation_context():
        from contextlib import contextmanager

        @contextmanager
        def _noop():
            yield None

        return _noop()

    def log_operation_start(logger, op, **kw):
        pass

    def log_operation_success(logger, op, **kw):
        pass

    def log_operation_failure(logger, op, err, **kw):
        pass

    def get_audit_logger():
        return None

    def get_metrics():
        return None

    def track_operation(op):
        from contextlib import contextmanager

        @contextmanager
        def _noop():
            yield

        return _noop()

    AuditAction = None

console = Console()
logger = get_logger(__name__)


class UserType(str, Enum):
    """User types for SnowTower users"""

    PERSON = "PERSON"
    SERVICE = "SERVICE"


class UserValidationError(Exception):
    """Raised when user validation fails"""

    pass


class UserCreationError(Exception):
    """Raised when user creation fails"""

    pass


class UserManager:
    """
    Central user management orchestrator for SnowTower SnowDDL.

    Provides a unified interface for all user operations including:
    - Interactive user creation
    - User updates and deletions
    - Password encryption management
    - RSA key generation and rotation
    - YAML configuration handling
    - SnowDDL service account management
    """

    def __init__(self, config_directory: Optional[Path] = None):
        """
        Initialize the user management system.

        Args:
            config_directory: Directory containing SnowDDL configurations.
                            Defaults to ./snowddl/
        """
        self.config_dir = config_directory or Path.cwd() / "snowddl"

        # Initialize component managers
        self.encryption = FernetEncryption()
        self.rsa_manager = RSAKeyManager()
        self.yaml_handler = YAMLHandler(self.config_dir)
        self.snowddl_manager = SnowDDLAccountManager()
        self.password_generator = PasswordGenerator(self.encryption)

        # Initialize monitoring (if available)
        self.audit_logger = get_audit_logger() if MONITORING_AVAILABLE else None
        self.metrics = get_metrics() if MONITORING_AVAILABLE else None

        console.print(
            f"🏗️ [blue]UserManager initialized with config: {self.config_dir}[/blue]"
        )
        logger.info(
            "UserManager initialized", extra={"config_dir": str(self.config_dir)}
        )

    def create_user(self, interactive: bool = True, **user_data) -> Dict[str, Any]:
        """
        Create a new user with full configuration.

        Args:
            interactive: Whether to use interactive prompts
            **user_data: User configuration data (for non-interactive mode)

        Returns:
            Dictionary containing created user configuration

        Raises:
            UserCreationError: If user creation fails

        Example:
            >>> manager = UserManager()
            >>> user = manager.create_user()  # Interactive mode
            >>>
            >>> # Or non-interactive:
            >>> user = manager.create_user(
            ...     interactive=False,
            ...     first_name="John",
            ...     last_name="Doe",
            ...     email="john.doe@company.com",
            ...     user_type=UserType.PERSON
            ... )
        """
        # Use correlation context for tracking this operation
        with correlation_context():
            log_operation_start(logger, "user_creation", interactive=interactive)

            try:
                with track_operation("user_creation", self.metrics):
                    if interactive:
                        result = self._create_user_interactive()
                    else:
                        result = self._create_user_programmatic(**user_data)

                    log_operation_success(logger, "user_creation")
                    return result

            except Exception as e:
                log_operation_failure(logger, "user_creation", e)
                raise UserCreationError(f"Failed to create user: {e}")

    def _create_user_interactive(self) -> Dict[str, Any]:
        """Interactive user creation with prompts"""
        console.print(
            Panel(
                Text("SnowTower User Creation Wizard", style="bold blue")
                + "\n\n"
                + "This wizard will guide you through creating a new user for Snowflake.\n"
                + "You'll be able to configure authentication, roles, and security settings.",
                title="👤 User Creation",
                border_style="blue",
            )
        )

        # Step 1: Basic Information
        console.print("\n[bold cyan]Step 1: Basic Information[/bold cyan]")

        first_name = Prompt.ask("First name")
        last_name = Prompt.ask("Last name")
        email = Prompt.ask("Email address")

        # Generate username from name
        username_suggestion = f"{first_name}_{last_name}".upper().replace(" ", "_")
        username = Prompt.ask("Username", default=username_suggestion)

        # Step 2: User Type
        console.print("\n[bold cyan]Step 2: User Type[/bold cyan]")
        console.print(
            "• [green]PERSON[/green]: Human user (subject to MFA requirements)"
        )
        console.print(
            "• [yellow]SERVICE[/yellow]: Service account (RSA key authentication recommended)"
        )

        user_type_input = Prompt.ask(
            "User type", choices=["PERSON", "SERVICE"], default="PERSON"
        )
        user_type = UserType(user_type_input)

        # Step 3: Authentication Setup
        console.print("\n[bold cyan]Step 3: Authentication Setup[/bold cyan]")

        setup_rsa = Confirm.ask("Generate RSA key pair?", default=True)
        setup_password = True
        auto_generate_password = True

        if user_type == UserType.SERVICE:
            setup_password = Confirm.ask(
                "Set password for service account? (RSA keys recommended)",
                default=False,
            )

        if setup_password:
            auto_generate_password = Confirm.ask(
                "Automatically generate secure password?", default=True
            )

        # Step 4: Role Assignment
        console.print("\n[bold cyan]Step 4: Role Assignment[/bold cyan]")

        if user_type == UserType.PERSON:
            default_role = f"{username}__U_ROLE"
        else:
            default_role = "SERVICE_ROLE"

        default_role = Prompt.ask("Default role", default=default_role)
        default_warehouse = Prompt.ask("Default warehouse", default="COMPUTE_WH")

        # Step 5: Security Policies
        console.print("\n[bold cyan]Step 5: Security Policies[/bold cyan]")

        policies = {}
        if user_type == UserType.PERSON:
            policies["authentication_policy"] = Prompt.ask(
                "Authentication policy", default="mfa_required_policy"
            )
            policies["network_policy"] = Prompt.ask(
                "Network policy", default="office_network_policy"
            )

        # Build user configuration
        user_config = {
            "type": user_type.value,
            "login_name": username,
            "display_name": f"{first_name} {last_name}",
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "default_role": default_role,
            "default_warehouse": default_warehouse,
            "comment": f"Created by SnowTower User Manager on {self._get_timestamp()}",
            "disabled": False,
            **policies,
        }

        # Step 6: Generate Authentication
        console.print("\n[bold cyan]Step 6: Setting up Authentication[/bold cyan]")

        if setup_rsa:
            try:
                private_key, public_key = self.rsa_manager.generate_key_pair(username)
                public_key_content = self.rsa_manager.extract_public_key_for_snowflake(
                    private_key
                )
                user_config["rsa_public_key"] = public_key_content

                console.print(f"✅ [green]Generated RSA key pair[/green]")
                console.print(f"   Private key: [cyan]{private_key}[/cyan]")

            except RSAKeyError as e:
                console.print(f"⚠️ [yellow]RSA key generation failed: {e}[/yellow]")
                console.print("Continuing without RSA key...")

        if setup_password:
            try:
                if auto_generate_password:
                    # Automatically generate secure password
                    password_info = self.password_generator.generate_user_password(
                        username=username, user_type=user_type.value, length=16
                    )

                    user_config["password"] = password_info["yaml_value"]

                    # Display generated password information
                    console.print(
                        "✅ [green]Secure password generated automatically![/green]"
                    )
                    console.print(
                        f"🔑 [yellow]Generated password: [red]{password_info['plain_password']}[/red][/yellow]"
                    )
                    console.print(
                        "📋 [dim]Please save this password securely for the user[/dim]"
                    )

                    # Store password info for later display in next steps
                    user_config["_generated_password"] = password_info["plain_password"]

                else:
                    # Manual password entry (existing behavior)
                    encrypted_password = self.encryption.interactive_encrypt()
                    if encrypted_password:
                        user_config["password"] = f"!decrypt {encrypted_password}"
                        console.print("✅ [green]Password encrypted and added[/green]")

            except (FernetEncryptionError, PasswordGenerationError) as e:
                console.print(f"⚠️ [yellow]Password setup failed: {e}[/yellow]")
                console.print("User will be created without password.")

        # Step 7: Review and Confirm
        console.print("\n[bold cyan]Step 7: Review Configuration[/bold cyan]")
        self._display_user_summary(username, user_config)

        if not Confirm.ask("Create this user?"):
            console.print("❌ [yellow]User creation cancelled[/yellow]")
            return {}

        # Step 8: Save Configuration
        try:
            self.yaml_handler.merge_user(username, user_config)

            # Log to audit trail
            if self.audit_logger:
                self.audit_logger.log_user_creation(username, user_config)

            # Update metrics
            if self.metrics:
                self.metrics.increment(
                    "snowtower_users_created_total",
                    labels={"user_type": user_config.get("type", "UNKNOWN")},
                )

            console.print(f"✅ [green]User {username} created successfully![/green]")
            logger.info(
                f"User created successfully",
                extra={"username": username, "user_type": user_config.get("type")},
            )

            # Show next steps
            self._show_next_steps(username, user_config)

            return {username: user_config}

        except YAMLError as e:
            raise UserCreationError(f"Failed to save user configuration: {e}")

    def _create_user_programmatic(self, **user_data) -> Dict[str, Any]:
        """Create user with provided data (non-interactive)"""
        required_fields = ["first_name", "last_name", "email"]
        for field in required_fields:
            if field not in user_data:
                raise UserCreationError(f"Required field missing: {field}")

        # Generate username if not provided
        if "username" not in user_data:
            user_data[
                "username"
            ] = f"{user_data['first_name']}_{user_data['last_name']}".upper().replace(
                " ", "_"
            )

        username = user_data["username"]
        user_type = user_data.get("user_type", UserType.PERSON)
        auto_generate_password = user_data.get("auto_generate_password", True)

        # Build configuration
        user_config = {
            "type": user_type.value,
            "login_name": username,
            "display_name": f"{user_data['first_name']} {user_data['last_name']}",
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "email": user_data["email"],
            "default_role": user_data.get("default_role", f"{username}__U_ROLE"),
            "default_warehouse": user_data.get("default_warehouse", "COMPUTE_WH"),
            "comment": f"Created programmatically on {self._get_timestamp()}",
            "disabled": False,
        }

        # Automatic password generation (unless explicitly disabled or password provided)
        if auto_generate_password and "password" not in user_data:
            try:
                password_info = self.password_generator.generate_user_password(
                    username=username,
                    user_type=user_type.value,
                    length=user_data.get("password_length", 16),
                )

                user_config["password"] = password_info["yaml_value"]
                user_config["_generated_password"] = password_info[
                    "plain_password"
                ]  # Store for output

                console.print(
                    f"🔑 [green]Generated secure password for {username}[/green]"
                )

            except PasswordGenerationError as e:
                console.print(
                    f"⚠️ [yellow]Password generation failed for {username}: {e}[/yellow]"
                )

        # Add optional fields
        optional_fields = [
            "authentication_policy",
            "network_policy",
            "password_policy",
            "session_policy",
            "password",
            "rsa_public_key",
        ]
        for field in optional_fields:
            if field in user_data:
                user_config[field] = user_data[field]

        # Save configuration
        self.yaml_handler.merge_user(username, user_config)
        console.print(f"✅ [green]User {username} created programmatically[/green]")

        return {username: user_config}

    def update_user(self, username: str, **updates) -> bool:
        """
        Update an existing user's configuration.

        Args:
            username: Username to update
            **updates: Fields to update

        Returns:
            True if update was successful, False otherwise
        """
        # Load existing user
        existing_config = self.yaml_handler.get_user(username)
        if not existing_config:
            console.print(f"❌ [red]User {username} not found[/red]")
            return False

        # Apply updates
        updated_config = existing_config.copy()
        updated_config.update(updates)
        updated_config["comment"] = f"Updated on {self._get_timestamp()}"

        try:
            self.yaml_handler.merge_user(username, updated_config)
            console.print(f"✅ [green]User {username} updated successfully[/green]")
            return True
        except YAMLError as e:
            console.print(f"❌ [red]Failed to update user: {e}[/red]")
            return False

    def delete_user(self, username: str, confirm: bool = True) -> bool:
        """
        Delete a user from the configuration.

        Args:
            username: Username to delete
            confirm: Whether to ask for confirmation

        Returns:
            True if deletion was successful, False otherwise
        """
        return self.yaml_handler.remove_user(username, backup=True)

    def list_users(self, format: str = "table") -> Union[str, List[Dict[str, Any]]]:
        """
        List all configured users.

        Args:
            format: Output format ('table', 'json', 'yaml', 'list')

        Returns:
            Formatted user list
        """
        try:
            users = self.yaml_handler.load_users()

            if format == "list":
                return [
                    {"username": username, **config}
                    for username, config in users.items()
                ]
            elif format == "table":
                self._display_users_table(users)
                return ""
            elif format == "json":
                import json

                return json.dumps(users, indent=2)
            elif format == "yaml":
                import yaml

                return yaml.dump(users, default_flow_style=False, sort_keys=True)
            else:
                console.print(f"❌ [red]Unknown format: {format}[/red]")
                return ""

        except Exception as e:
            console.print(f"❌ [red]Failed to list users: {e}[/red]")
            return []

    def _display_users_table(self, users: Dict[str, Any]) -> None:
        """Display users in a formatted table"""
        if not users:
            console.print("📭 [yellow]No users configured[/yellow]")
            return

        table = Table(title=f"SnowTower Users ({len(users)} total)")
        table.add_column("Username", style="cyan", width=15)
        table.add_column("Type", style="blue", width=8)
        table.add_column("Name", style="white", width=20)
        table.add_column("Email", style="dim", width=25)
        table.add_column("Auth", style="green", width=10)
        table.add_column("Status", style="bold", width=8)

        for username, config in sorted(users.items()):
            user_type = config.get("type", "UNKNOWN")
            name = config.get(
                "display_name",
                f"{config.get('first_name', '')} {config.get('last_name', '')}",
            )
            email = config.get("email", "N/A")

            # Authentication methods
            auth_methods = []
            if config.get("password"):
                auth_methods.append("PWD")
            if config.get("rsa_public_key"):
                auth_methods.append("RSA")
            auth_str = "+".join(auth_methods) if auth_methods else "None"

            # Status
            status = "Disabled" if config.get("disabled", False) else "Active"
            status_style = "red" if status == "Disabled" else "green"

            table.add_row(
                username,
                user_type,
                name[:19] + "..." if len(name) > 20 else name,
                email[:24] + "..." if len(email) > 25 else email,
                auth_str,
                f"[{status_style}]{status}[/{status_style}]",
            )

        console.print(table)

    def validate_user(self, username: str) -> Dict[str, Any]:
        """
        Validate a user's configuration.

        Args:
            username: Username to validate

        Returns:
            Validation result dictionary
        """
        user_config = self.yaml_handler.get_user(username)
        if not user_config:
            return {
                "is_valid": False,
                "errors": [f"User {username} not found"],
                "warnings": [],
            }

        result = {"is_valid": True, "errors": [], "warnings": []}

        # Validate required fields based on type
        user_type = user_config.get("type")
        if user_type == "PERSON":
            required = ["first_name", "last_name", "email"]
            for field in required:
                if not user_config.get(field):
                    result["errors"].append(
                        f"PERSON user missing required field: {field}"
                    )
                    result["is_valid"] = False

        # Validate authentication
        has_password = bool(user_config.get("password"))
        has_rsa = bool(user_config.get("rsa_public_key"))

        if not has_password and not has_rsa:
            result["errors"].append("User has no authentication method")
            result["is_valid"] = False

        # MFA compliance check
        if user_type == "PERSON":
            has_mfa_policy = bool(user_config.get("authentication_policy"))
            has_dual_auth = has_password and has_rsa

            if not has_mfa_policy and not has_dual_auth:
                result["warnings"].append(
                    "PERSON user may not be MFA compliant by March 2026"
                )

        return result

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific user"""
        return self.yaml_handler.get_user(username)

    def encrypt_password(self, password: Optional[str] = None) -> str:
        """
        Encrypt a password for use in user configuration.

        Args:
            password: Password to encrypt. If None, prompts interactively.

        Returns:
            Encrypted password string
        """
        if password:
            return self.encryption.encrypt_password(password)
        else:
            return self.encryption.interactive_encrypt()

    def generate_password(
        self, username: str, user_type: str = "PERSON", length: int = 16, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a secure password for a user with automatic encryption.

        Args:
            username: Username for the password
            user_type: User type (PERSON or SERVICE)
            length: Password length (minimum 12, recommended 16+)
            **kwargs: Additional arguments for password generation

        Returns:
            Dictionary containing password information and metadata

        Example:
            >>> manager = UserManager()
            >>> result = manager.generate_password("JOHN_DOE")
            >>> print(result['plain_password'])  # For secure delivery
            >>> print(result['yaml_value'])     # For YAML configuration
        """
        return self.password_generator.generate_user_password(
            username=username, user_type=user_type, length=length
        )

    def generate_passwords_bulk(
        self, usernames: list, **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate passwords for multiple users.

        Args:
            usernames: List of usernames
            **kwargs: Arguments passed to generate_password

        Returns:
            Dictionary mapping username to password information

        Example:
            >>> manager = UserManager()
            >>> passwords = manager.generate_passwords_bulk(["USER1", "USER2"])
            >>> for username, info in passwords.items():
            ...     print(f"{username}: {info['plain_password']}")
        """
        return self.password_generator.generate_multiple_passwords(usernames, **kwargs)

    def regenerate_user_password(self, username: str, length: int = 16) -> bool:
        """
        Regenerate password for an existing user.

        Args:
            username: Username to regenerate password for
            length: New password length

        Returns:
            True if password was regenerated successfully

        Example:
            >>> manager = UserManager()
            >>> success = manager.regenerate_user_password("JOHN_DOE")
        """
        try:
            # Get existing user
            user_config = self.get_user(username)
            if not user_config:
                console.print(f"❌ [red]User {username} not found[/red]")
                return False

            # Generate new password
            password_info = self.generate_password(
                username=username,
                user_type=user_config.get("type", "PERSON"),
                length=length,
            )

            # Update user configuration
            success = self.update_user(username, password=password_info["yaml_value"])

            if success:
                console.print(f"🔑 [green]Password regenerated for {username}[/green]")
                console.print(
                    f"🔑 [yellow]New password: [red]{password_info['plain_password']}[/red][/yellow]"
                )
                console.print("📋 [dim]Please save this password securely[/dim]")

            return success

        except Exception as e:
            console.print(
                f"❌ [red]Failed to regenerate password for {username}: {e}[/red]"
            )
            return False

    def generate_rsa_keys(self, username: str) -> Tuple[Path, Path]:
        """
        Generate RSA key pair for a user.

        Args:
            username: Username for key generation

        Returns:
            Tuple of (private_key_path, public_key_path)
        """
        return self.rsa_manager.generate_key_pair(username)

    def rotate_user_keys(self, username: str) -> bool:
        """
        Rotate RSA keys for a user and update configuration.

        Args:
            username: Username to rotate keys for

        Returns:
            True if rotation was successful, False otherwise
        """
        try:
            # Generate new keys
            private_key, public_key = self.rsa_manager.rotate_keys(username)

            # Extract public key for Snowflake
            public_key_content = self.rsa_manager.extract_public_key_for_snowflake(
                private_key
            )

            # Update user configuration
            success = self.update_user(username, rsa_public_key=public_key_content)

            if success:
                console.print(
                    f"🔄 [green]Keys rotated successfully for {username}[/green]"
                )
                console.print(f"   New private key: [cyan]{private_key}[/cyan]")

            return success

        except Exception as e:
            console.print(f"❌ [red]Key rotation failed: {e}[/red]")
            return False

    def bulk_import(self, csv_file: Path) -> List[Dict[str, Any]]:
        """
        Import multiple users from CSV file.

        Args:
            csv_file: Path to CSV file with user data

        Returns:
            List of created user configurations
        """
        import csv

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        created_users = []

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    user = self._create_user_programmatic(**row)
                    created_users.append(user)
                except Exception as e:
                    console.print(
                        f"⚠️ [yellow]Failed to create user from row {row}: {e}[/yellow]"
                    )

        console.print(
            f"✅ [green]Bulk import completed: {len(created_users)} users created[/green]"
        )
        return created_users

    def backup_configuration(self, description: Optional[str] = None) -> Path:
        """Create backup of user configuration"""
        return self.yaml_handler.backup_config(description)

    def _display_user_summary(self, username: str, config: Dict[str, Any]) -> None:
        """Display user configuration summary"""
        table = Table(title=f"User Configuration Summary: {username}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        # Basic info
        table.add_row("Username", username)
        table.add_row("Type", config.get("type", "N/A"))
        table.add_row("Display Name", config.get("display_name", "N/A"))
        table.add_row("Email", config.get("email", "N/A"))
        table.add_row("Default Role", config.get("default_role", "N/A"))

        # Authentication
        auth_methods = []
        if config.get("password"):
            auth_methods.append("Password (encrypted)")
        if config.get("rsa_public_key"):
            auth_methods.append("RSA Key")
        table.add_row(
            "Authentication", ", ".join(auth_methods) if auth_methods else "None"
        )

        # Policies
        policies = []
        for policy_type in [
            "authentication_policy",
            "network_policy",
            "password_policy",
            "session_policy",
        ]:
            if config.get(policy_type):
                policies.append(f"{policy_type}: {config[policy_type]}")

        if policies:
            table.add_row("Security Policies", "\n".join(policies))

        console.print(table)

    def _show_next_steps(self, username: str, config: Dict[str, Any]) -> None:
        """Show next steps after user creation"""
        console.print("\n[bold green]🎉 User Created Successfully![/bold green]")
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")

        console.print("1. [yellow]Deploy to Snowflake:[/yellow]")
        console.print("   [cyan]uv run snowddl-plan[/cyan]  # Review changes")
        console.print("   [cyan]uv run snowddl-apply[/cyan] # Deploy to Snowflake")

        if config.get("rsa_public_key"):
            console.print("\n2. [yellow]RSA Key Setup:[/yellow]")
            console.print(
                f"   • Private key generated in: [cyan]keys/{username.lower()}_rsa_key_*.p8[/cyan]"
            )
            console.print("   • Share private key securely with user")
            console.print("   • User should set SNOWFLAKE_PRIVATE_KEY_PATH")

        if config.get("password"):
            console.print("\n3. [yellow]Password Information:[/yellow]")
            if config.get("_generated_password"):
                console.print(
                    f"   • [red]Generated Password: {config['_generated_password']}[/red]"
                )
                console.print(
                    "   • [bold]IMPORTANT: Save this password securely for the user[/bold]"
                )
                console.print(
                    "   • Password is automatically encrypted in configuration"
                )
            else:
                console.print("   • Password is encrypted in configuration")
                console.print("   • User will need the actual password for login")
            console.print("   • Consider setting up MFA for additional security")

        console.print("\n4. [yellow]Verification:[/yellow]")
        console.print("   [cyan]uv run show users[/cyan]  # Verify user in CLI")
        console.print("   • Test user login to Snowflake")
        console.print("   • Verify role assignments and permissions")

    def _get_timestamp(self) -> str:
        """Get current timestamp for comments"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # SnowDDL Account Management (delegation to SnowDDLAccountManager)
    def manage_snowddl_account(self) -> SnowDDLAccountManager:
        """Get SnowDDL account manager for service account operations"""
        return self.snowddl_manager
