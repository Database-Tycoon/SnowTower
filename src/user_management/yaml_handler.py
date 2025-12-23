"""
YAML Configuration Handler for SnowTower User Management

Handles loading, saving, and manipulating SnowDDL YAML configuration files.
Provides safe YAML operations with backup and validation.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import yaml
from rich.console import Console
from rich.prompt import Confirm


def decrypt_constructor(loader, node):
    """YAML constructor for !decrypt tags (encrypted passwords)"""
    return f"!decrypt {loader.construct_scalar(node)}"


# Register the !decrypt constructor
yaml.SafeLoader.add_constructor("!decrypt", decrypt_constructor)

console = Console()


class YAMLError(Exception):
    """Base exception for YAML operations"""

    pass


class YAMLFileNotFoundError(YAMLError):
    """Raised when YAML file is not found"""

    pass


class YAMLValidationError(YAMLError):
    """Raised when YAML validation fails"""

    pass


class YAMLBackupError(YAMLError):
    """Raised when YAML backup operations fail"""

    pass


class YAMLHandler:
    """
    YAML configuration file handler for SnowDDL user management.

    Provides safe operations for loading, saving, and manipulating
    user configuration YAML files with backup and validation support.
    """

    def __init__(self, config_directory: Optional[Path] = None):
        """
        Initialize YAML handler.

        Args:
            config_directory: Directory containing SnowDDL YAML files.
                            Defaults to ./snowddl/
        """
        self.config_dir = config_directory or Path.cwd() / "snowddl"
        self.user_yaml = self.config_dir / "user.yaml"
        self.backup_dir = self.config_dir / ".backups"

        # Create backup directory if it doesn't exist (including parents)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def load_users(self) -> Dict[str, Any]:
        """
        Load users from user.yaml file.

        Returns:
            Dictionary of user configurations

        Raises:
            YAMLFileNotFoundError: If user.yaml file is not found
            YAMLError: If YAML parsing fails

        Example:
            >>> handler = YAMLHandler()
            >>> users = handler.load_users()
            >>> print(f"Found {len(users)} users")
        """
        if not self.user_yaml.exists():
            raise YAMLFileNotFoundError(
                f"User configuration file not found: {self.user_yaml}"
            )

        try:
            with open(self.user_yaml, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            # Handle empty file
            if content is None:
                return {}

            # Validate structure
            if not isinstance(content, dict):
                raise YAMLValidationError(
                    "User YAML must contain a dictionary of users"
                )

            console.print(
                f"📋 [blue]Loaded {len(content)} users from {self.user_yaml.name}[/blue]"
            )
            return content

        except yaml.YAMLError as e:
            raise YAMLError(f"Failed to parse YAML file: {e}")
        except YAMLValidationError:
            raise  # Re-raise validation errors as-is
        except Exception as e:
            raise YAMLError(f"Unexpected error loading users: {e}")

    def save_users(self, users: Dict[str, Any], backup: bool = True) -> None:
        """
        Save users to user.yaml file.

        Args:
            users: Dictionary of user configurations
            backup: Whether to create a backup before saving (default: True)

        Raises:
            YAMLError: If saving fails
        """
        if backup and self.user_yaml.exists():
            self.backup_config()

        try:
            # Create directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Write YAML with nice formatting
            with open(self.user_yaml, "w", encoding="utf-8") as f:
                yaml.dump(
                    users,
                    f,
                    default_flow_style=False,
                    sort_keys=True,
                    indent=2,
                    allow_unicode=True,
                )

            console.print(
                f"💾 [green]Saved {len(users)} users to {self.user_yaml.name}[/green]"
            )

        except Exception as e:
            raise YAMLError(f"Failed to save users: {e}")

    def merge_user(
        self, username: str, user_data: Dict[str, Any], backup: bool = True
    ) -> None:
        """
        Merge a single user into the existing user configuration.

        Args:
            username: Username to add or update
            user_data: User configuration dictionary
            backup: Whether to create a backup before saving

        Raises:
            YAMLError: If merge operation fails
        """
        # Load existing users or start with empty dict
        try:
            existing_users = self.load_users()
        except YAMLFileNotFoundError:
            existing_users = {}

        # Check if user already exists
        if username in existing_users:
            if not Confirm.ask(f"User {username} already exists. Overwrite?"):
                console.print(f"❌ [yellow]User {username} not updated[/yellow]")
                return

        # Merge user data
        existing_users[username] = user_data

        # Save updated configuration
        self.save_users(existing_users, backup=backup)

        action = "Updated" if username in existing_users else "Added"
        console.print(f"✅ [green]{action} user {username}[/green]")

    def remove_user(self, username: str, backup: bool = True) -> bool:
        """
        Remove a user from the configuration.

        Args:
            username: Username to remove
            backup: Whether to create a backup before saving

        Returns:
            True if user was removed, False if user didn't exist

        Raises:
            YAMLError: If removal fails
        """
        try:
            users = self.load_users()
        except YAMLFileNotFoundError:
            console.print(f"📭 [yellow]No user configuration file found[/yellow]")
            return False

        if username not in users:
            console.print(f"❌ [yellow]User {username} not found[/yellow]")
            return False

        # Confirm removal
        if not Confirm.ask(f"Remove user {username} from configuration?"):
            console.print(f"❌ [yellow]User {username} not removed[/yellow]")
            return False

        # Remove user and save
        del users[username]
        self.save_users(users, backup=backup)

        console.print(f"🗑️ [green]Removed user {username}[/green]")
        return True

    def backup_config(self, description: Optional[str] = None) -> Path:
        """
        Create a backup of the current user configuration.

        Args:
            description: Optional description for the backup

        Returns:
            Path to the backup file

        Raises:
            YAMLBackupError: If backup creation fails
        """
        if not self.user_yaml.exists():
            raise YAMLBackupError(f"Cannot backup non-existent file: {self.user_yaml}")

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"user_backup_{timestamp}.yaml"
        backup_path = self.backup_dir / backup_name

        try:
            # Copy the file
            shutil.copy2(self.user_yaml, backup_path)

            # Add metadata comment if description provided
            if description:
                self._add_backup_metadata(backup_path, description)

            console.print(f"💾 [blue]Created backup: {backup_name}[/blue]")
            return backup_path

        except Exception as e:
            raise YAMLBackupError(f"Failed to create backup: {e}")

    def _add_backup_metadata(self, backup_path: Path, description: str) -> None:
        """Add metadata comment to backup file"""
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                content = f.read()

            metadata = f"# Backup created: {datetime.now().isoformat()}\n"
            metadata += f"# Description: {description}\n"
            metadata += "# Original file: user.yaml\n\n"

            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(metadata + content)

        except Exception as e:
            # Don't fail backup for metadata issues
            console.print(f"⚠️ [yellow]Could not add metadata to backup: {e}[/yellow]")

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backup files.

        Returns:
            List of backup information dictionaries
        """
        if not self.backup_dir.exists():
            return []

        backups = []
        for backup_file in self.backup_dir.glob("user_backup_*.yaml"):
            stat = backup_file.stat()

            # Extract timestamp from filename
            try:
                timestamp_str = backup_file.stem.split("_", 2)[
                    2
                ]  # user_backup_TIMESTAMP
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            except (IndexError, ValueError):
                timestamp = datetime.fromtimestamp(stat.st_ctime)

            backup_info = {
                "path": backup_file,
                "name": backup_file.name,
                "timestamp": timestamp,
                "size_bytes": stat.st_size,
                "description": self._extract_backup_description(backup_file),
            }
            backups.append(backup_info)

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups

    def _extract_backup_description(self, backup_path: Path) -> Optional[str]:
        """Extract description from backup file metadata"""
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                # Read first few lines looking for description
                for line in f:
                    if line.startswith("# Description:"):
                        return line.replace("# Description:", "").strip()
                    if not line.startswith("#"):
                        break  # Stop at first non-comment line
        except Exception:
            pass
        return None

    def restore_backup(self, backup_name: str, confirm: bool = True) -> bool:
        """
        Restore user configuration from a backup.

        Args:
            backup_name: Name of the backup file to restore
            confirm: Whether to ask for confirmation

        Returns:
            True if restore was successful, False otherwise

        Raises:
            YAMLBackupError: If restore fails
        """
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            raise YAMLBackupError(f"Backup file not found: {backup_name}")

        if confirm and not Confirm.ask(
            f"Restore from backup {backup_name}? This will overwrite current configuration."
        ):
            console.print("❌ [yellow]Restore cancelled[/yellow]")
            return False

        try:
            # Create backup of current file before restore
            if self.user_yaml.exists():
                self.backup_config("Before restore operation")

            # Copy backup to main file
            shutil.copy2(backup_path, self.user_yaml)

            console.print(f"✅ [green]Restored configuration from {backup_name}[/green]")
            return True

        except Exception as e:
            raise YAMLBackupError(f"Failed to restore backup: {e}")

    def validate_yaml(self, file_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Validate YAML file structure and content.

        Args:
            file_path: Path to YAML file to validate. Defaults to user.yaml

        Returns:
            Validation result dictionary

        Example:
            >>> handler = YAMLHandler()
            >>> result = handler.validate_yaml()
            >>> if result['is_valid']:
            ...     print("YAML is valid!")
        """
        target_file = file_path or self.user_yaml

        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "user_count": 0,
            "issues": [],
        }

        if not target_file.exists():
            result["is_valid"] = False
            result["errors"].append(f"File not found: {target_file}")
            return result

        try:
            # Load and parse YAML
            with open(target_file, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if content is None:
                result["warnings"].append("YAML file is empty")
                return result

            if not isinstance(content, dict):
                result["is_valid"] = False
                result["errors"].append("YAML root must be a dictionary")
                return result

            result["user_count"] = len(content)

            # Validate each user
            for username, user_config in content.items():
                user_issues = self._validate_user_config(username, user_config)
                if user_issues:
                    result["issues"].extend(user_issues)
                    if any(issue["level"] == "error" for issue in user_issues):
                        result["is_valid"] = False

        except yaml.YAMLError as e:
            result["is_valid"] = False
            result["errors"].append(f"YAML parsing error: {e}")
        except Exception as e:
            result["is_valid"] = False
            result["errors"].append(f"Validation error: {e}")

        return result

    def _validate_user_config(self, username: str, config: Any) -> List[Dict[str, Any]]:
        """Validate individual user configuration"""
        issues = []

        if not isinstance(config, dict):
            issues.append(
                {
                    "level": "error",
                    "user": username,
                    "message": f"User {username} configuration must be a dictionary",
                }
            )
            return issues

        # Check required fields based on user type
        user_type = config.get("type")
        if user_type == "PERSON":
            required_fields = ["first_name", "last_name", "email"]
            for field in required_fields:
                if not config.get(field):
                    issues.append(
                        {
                            "level": "warning",
                            "user": username,
                            "message": f"PERSON user {username} missing {field}",
                        }
                    )

        # Check authentication methods
        has_password = bool(config.get("password"))
        has_rsa_key = bool(config.get("rsa_public_key"))

        if not has_password and not has_rsa_key:
            issues.append(
                {
                    "level": "error",
                    "user": username,
                    "message": f"User {username} has no authentication method (password or RSA key)",
                }
            )

        # Check encrypted password format
        if has_password and not config["password"].startswith("gAAAAA"):
            issues.append(
                {
                    "level": "warning",
                    "user": username,
                    "message": f"User {username} password doesn't appear to be Fernet encrypted",
                }
            )

        return issues

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific user.

        Args:
            username: Username to retrieve

        Returns:
            User configuration dictionary or None if not found
        """
        try:
            users = self.load_users()
            return users.get(username)
        except YAMLFileNotFoundError:
            return None

    def user_exists(self, username: str) -> bool:
        """
        Check if a user exists in the configuration.

        Args:
            username: Username to check

        Returns:
            True if user exists, False otherwise
        """
        return self.get_user(username) is not None

    def list_usernames(self) -> List[str]:
        """
        Get list of all configured usernames.

        Returns:
            List of usernames
        """
        try:
            users = self.load_users()
            return list(users.keys())
        except YAMLFileNotFoundError:
            return []
