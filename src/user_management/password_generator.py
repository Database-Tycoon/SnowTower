"""
Secure Password Generator for SnowTower User Management

Provides cryptographically secure password generation with automatic Fernet encryption
for seamless integration with SnowDDL user configuration files.
"""

import secrets
import string
from typing import Dict, Any, Optional, Tuple
from cryptography.fernet import Fernet
from rich.console import Console

from .encryption import FernetEncryption, FernetEncryptionError

console = Console()


class PasswordGenerationError(Exception):
    """Raised when password generation fails"""

    pass


class PasswordGenerator:
    """
    Secure password generator with automatic encryption capabilities.

    Generates cryptographically secure passwords and automatically encrypts them
    using Fernet encryption for storage in SnowDDL YAML configurations.
    """

    def __init__(self, encryption: Optional[FernetEncryption] = None):
        """
        Initialize password generator.

        Args:
            encryption: Optional FernetEncryption instance. If not provided,
                       will create a new instance using environment variables.
        """
        self.encryption = encryption or FernetEncryption()

    def generate_secure_password(
        self,
        length: int = 16,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_symbols: bool = True,
        exclude_ambiguous: bool = True,
    ) -> str:
        """
        Generate a cryptographically secure password.

        Args:
            length: Password length (minimum 12, recommended 16+)
            include_uppercase: Include uppercase letters (A-Z)
            include_lowercase: Include lowercase letters (a-z)
            include_digits: Include digits (0-9)
            include_symbols: Include symbols (!@#$%^&*)
            exclude_ambiguous: Exclude ambiguous characters (0, O, l, I, etc.)

        Returns:
            Secure random password string

        Raises:
            PasswordGenerationError: If password generation fails or parameters are invalid

        Example:
            >>> generator = PasswordGenerator()
            >>> password = generator.generate_secure_password(length=20)
            >>> print(f"Generated: {password}")
        """
        if length < 12:
            raise PasswordGenerationError(
                "Password length must be at least 12 characters"
            )

        # Build character set
        charset = ""

        if include_lowercase:
            chars = string.ascii_lowercase
            if exclude_ambiguous:
                chars = chars.replace("l", "").replace("o", "")
            charset += chars

        if include_uppercase:
            chars = string.ascii_uppercase
            if exclude_ambiguous:
                chars = chars.replace("I", "").replace("O", "")
            charset += chars

        if include_digits:
            chars = string.digits
            if exclude_ambiguous:
                chars = chars.replace("0", "").replace("1", "")
            charset += chars

        if include_symbols:
            # Use safe symbols that work well in YAML and shell
            symbols = "!@#$%^&*"
            charset += symbols

        if not charset:
            raise PasswordGenerationError(
                "No character types selected for password generation"
            )

        # Generate password ensuring we have at least one character from each selected type
        password_chars = []

        # Ensure minimum complexity
        if include_lowercase:
            safe_lower = string.ascii_lowercase
            if exclude_ambiguous:
                safe_lower = safe_lower.replace("l", "").replace("o", "")
            password_chars.append(secrets.choice(safe_lower))

        if include_uppercase:
            safe_upper = string.ascii_uppercase
            if exclude_ambiguous:
                safe_upper = safe_upper.replace("I", "").replace("O", "")
            password_chars.append(secrets.choice(safe_upper))

        if include_digits:
            safe_digits = string.digits
            if exclude_ambiguous:
                safe_digits = safe_digits.replace("0", "").replace("1", "")
            password_chars.append(secrets.choice(safe_digits))

        if include_symbols:
            password_chars.append(secrets.choice("!@#$%^&*"))

        # Fill remaining length with random characters from full charset
        remaining_length = length - len(password_chars)
        for _ in range(remaining_length):
            password_chars.append(secrets.choice(charset))

        # Shuffle the password characters
        secrets.SystemRandom().shuffle(password_chars)

        return "".join(password_chars)

    def generate_encrypted_password(
        self, length: int = 16, **kwargs
    ) -> Tuple[str, str]:
        """
        Generate a secure password and return both plain and encrypted versions.

        Args:
            length: Password length
            **kwargs: Additional arguments passed to generate_secure_password()

        Returns:
            Tuple of (plain_password, encrypted_password_for_yaml)

        Raises:
            PasswordGenerationError: If generation or encryption fails

        Example:
            >>> generator = PasswordGenerator()
            >>> plain, encrypted = generator.generate_encrypted_password()
            >>> print(f"Plain: {plain}")
            >>> print(f"For YAML: !decrypt {encrypted}")
        """
        try:
            # Generate secure password
            plain_password = self.generate_secure_password(length=length, **kwargs)

            # Encrypt for storage
            encrypted_password = self.encryption.encrypt_password(plain_password)

            return plain_password, encrypted_password

        except Exception as e:
            raise PasswordGenerationError(f"Failed to generate encrypted password: {e}")

    def generate_user_password(
        self, username: str, user_type: str = "PERSON", length: int = 16
    ) -> Dict[str, Any]:
        """
        Generate a complete password package for a user with metadata.

        Args:
            username: Username for the password
            user_type: User type (PERSON or SERVICE)
            length: Password length

        Returns:
            Dictionary containing password information and metadata

        Example:
            >>> generator = PasswordGenerator()
            >>> result = generator.generate_user_password("JOHN_DOE")
            >>> print(result['yaml_value'])  # For YAML config
            >>> print(result['plain_password'])  # For secure delivery
        """
        try:
            plain_password, encrypted_password = self.generate_encrypted_password(
                length=length
            )

            return {
                "username": username,
                "user_type": user_type,
                "plain_password": plain_password,
                "encrypted_password": encrypted_password,
                "yaml_value": f"!decrypt {encrypted_password}",
                "length": length,
                "generated_at": self._get_timestamp(),
                "encryption_valid": self.encryption.validate_encryption(
                    encrypted_password
                ),
                "security_note": "Password generated with cryptographically secure random generator",
                "usage_instructions": {
                    "yaml_config": f"password: !decrypt {encrypted_password}",
                    "user_delivery": "Share plain_password securely with user",
                    "verification": "Test encryption validity before deployment",
                },
            }

        except Exception as e:
            raise PasswordGenerationError(
                f"Failed to generate user password for {username}: {e}"
            )

    def generate_multiple_passwords(
        self, usernames: list, user_type: str = "PERSON", length: int = 16
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate passwords for multiple users.

        Args:
            usernames: List of usernames
            user_type: Default user type for all users
            length: Password length

        Returns:
            Dictionary mapping username to password package

        Raises:
            PasswordGenerationError: If any password generation fails
        """
        results = {}
        failed_users = []

        for username in usernames:
            try:
                results[username] = self.generate_user_password(
                    username=username, user_type=user_type, length=length
                )

            except Exception as e:
                failed_users.append(username)
                console.print(
                    f"⚠️ [yellow]Failed to generate password for {username}: {e}[/yellow]"
                )

        if failed_users:
            raise PasswordGenerationError(
                f"Password generation failed for users: {', '.join(failed_users)}"
            )

        console.print(f"✅ [green]Generated passwords for {len(results)} users[/green]")
        return results

    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validate password strength and provide feedback.

        Args:
            password: Password to validate

        Returns:
            Dictionary with validation results and recommendations
        """
        result = {"is_strong": True, "score": 0, "issues": [], "recommendations": []}

        # Length check
        if len(password) < 12:
            result["issues"].append("Password too short (minimum 12 characters)")
            result["is_strong"] = False
        elif len(password) >= 16:
            result["score"] += 2
        else:
            result["score"] += 1

        # Character type checks
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        char_types = sum([has_lower, has_upper, has_digit, has_symbol])

        if char_types < 3:
            result["issues"].append("Password needs at least 3 character types")
            result["is_strong"] = False
        else:
            result["score"] += char_types

        # Common patterns check (basic)
        if password.lower() in ["password", "admin", "user", "test", "123456"]:
            result["issues"].append("Password is too common")
            result["is_strong"] = False

        # Recommendations
        if not has_symbol:
            result["recommendations"].append(
                "Add symbols (!@#$%^&*) for stronger security"
            )
        if len(password) < 16:
            result["recommendations"].append("Use 16+ characters for better security")

        # Final scoring
        if result["score"] >= 6:
            result["strength_level"] = "Strong"
        elif result["score"] >= 4:
            result["strength_level"] = "Medium"
        else:
            result["strength_level"] = "Weak"
            result["is_strong"] = False

        return result

    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    def display_password_info(self, password_info: Dict[str, Any]) -> None:
        """Display password information in a formatted way"""
        from rich.table import Table
        from rich.panel import Panel

        username = password_info["username"]

        # Create info table
        table = Table(title=f"Generated Password for {username}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Username", username)
        table.add_row("User Type", password_info["user_type"])
        table.add_row("Length", str(password_info["length"]))
        table.add_row("Generated At", password_info["generated_at"])
        table.add_row(
            "Encryption Valid",
            "✅ Yes" if password_info["encryption_valid"] else "❌ No",
        )

        console.print(table)

        # Security information
        console.print(
            Panel(
                f"[bold green]Password Generated Successfully![/bold green]\n\n"
                f"[yellow]For YAML Configuration:[/yellow]\n"
                f"[cyan]{password_info['usage_instructions']['yaml_config']}[/cyan]\n\n"
                f"[yellow]For User Delivery:[/yellow]\n"
                f"[red]Plain Password: {password_info['plain_password']}[/red]\n"
                f"[dim](Share this securely with the user)[/dim]\n\n"
                f"[yellow]Security Note:[/yellow]\n"
                f"{password_info['security_note']}",
                title="🔐 Password Information",
                border_style="green",
            )
        )
