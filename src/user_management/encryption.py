"""
Fernet Encryption Utilities for SnowTower User Management

Handles password encryption/decryption using Fernet symmetric encryption.
Provides secure password storage for SnowDDL YAML configurations.
"""

import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


class FernetEncryptionError(Exception):
    """Base exception for Fernet encryption operations"""

    pass


class FernetKeyMissingError(FernetEncryptionError):
    """Raised when Fernet encryption key is missing"""

    pass


class InvalidEncryptedDataError(FernetEncryptionError):
    """Raised when encrypted data is invalid or corrupted"""

    pass


class FernetEncryption:
    """
    Fernet encryption handler for SnowTower user passwords.

    Provides secure encryption/decryption of passwords for storage in
    SnowDDL YAML configuration files.
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize Fernet encryption handler.

        Args:
            key: Optional Fernet key. If not provided, will attempt to load
                from environment variable SNOWFLAKE_CONFIG_FERNET_KEYS
        """
        self.key = key or self._load_key_from_env()
        self._fernet = None

        if self.key:
            try:
                self._fernet = Fernet(self.key.encode())
            except Exception as e:
                raise FernetEncryptionError(f"Invalid Fernet key: {e}")

    def _load_key_from_env(self) -> Optional[str]:
        """Load Fernet key from environment variable"""
        return os.environ.get("SNOWFLAKE_CONFIG_FERNET_KEYS")

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded Fernet key as string

        Example:
            >>> encryption = FernetEncryption()
            >>> new_key = encryption.generate_key()
            >>> print(f"New key: {new_key}")
        """
        key = Fernet.generate_key()
        return key.decode("utf-8")

    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password using Fernet encryption.

        Args:
            password: Plain text password to encrypt

        Returns:
            Encrypted password as base64 string

        Raises:
            FernetKeyMissingError: If no Fernet key is available
            FernetEncryptionError: If encryption fails

        Example:
            >>> encryption = FernetEncryption()
            >>> encrypted = encryption.encrypt_password("mypassword")
            >>> print(f"Encrypted: {encrypted}")
        """
        if not self._fernet:
            raise FernetKeyMissingError(
                "No Fernet key available. Set SNOWFLAKE_CONFIG_FERNET_KEYS "
                "environment variable or provide key in constructor."
            )

        try:
            encrypted_bytes = self._fernet.encrypt(password.encode("utf-8"))
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            raise FernetEncryptionError(f"Failed to encrypt password: {e}")

    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt a Fernet-encrypted password.

        Args:
            encrypted_password: Base64-encoded encrypted password

        Returns:
            Decrypted plain text password

        Raises:
            FernetKeyMissingError: If no Fernet key is available
            InvalidEncryptedDataError: If encrypted data is invalid
            FernetEncryptionError: If decryption fails

        Example:
            >>> encryption = FernetEncryption()
            >>> decrypted = encryption.decrypt_password(encrypted)
            >>> print(f"Decrypted: {decrypted}")
        """
        if not self._fernet:
            raise FernetKeyMissingError(
                "No Fernet key available. Set SNOWFLAKE_CONFIG_FERNET_KEYS "
                "environment variable or provide key in constructor."
            )

        try:
            encrypted_bytes = encrypted_password.encode("utf-8")
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            raise InvalidEncryptedDataError(
                "Invalid encrypted password. May be corrupted or encrypted "
                "with a different key."
            )
        except Exception as e:
            raise FernetEncryptionError(f"Failed to decrypt password: {e}")

    def validate_encryption(self, encrypted_password: str) -> bool:
        """
        Validate that an encrypted password can be decrypted.

        Args:
            encrypted_password: Encrypted password to validate

        Returns:
            True if password can be decrypted, False otherwise
        """
        try:
            self.decrypt_password(encrypted_password)
            return True
        except (
            FernetKeyMissingError,
            InvalidEncryptedDataError,
            FernetEncryptionError,
        ):
            return False

    def rotate_keys(
        self, old_key: str, new_key: str, passwords: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Rotate encryption keys for a set of encrypted passwords.

        Args:
            old_key: Current Fernet key
            new_key: New Fernet key
            passwords: Dictionary of {user: encrypted_password}

        Returns:
            Dictionary of {user: re_encrypted_password} with new key

        Raises:
            FernetEncryptionError: If key rotation fails

        Example:
            >>> encryption = FernetEncryption()
            >>> old_passwords = {"user1": "encrypted_with_old_key"}
            >>> new_passwords = encryption.rotate_keys(old_key, new_key, old_passwords)
        """
        old_fernet = Fernet(old_key.encode())
        new_fernet = Fernet(new_key.encode())

        rotated_passwords = {}
        failed_users = []

        for user, encrypted_password in passwords.items():
            try:
                # Decrypt with old key
                decrypted = old_fernet.decrypt(encrypted_password.encode("utf-8"))
                # Re-encrypt with new key
                re_encrypted = new_fernet.encrypt(decrypted)
                rotated_passwords[user] = re_encrypted.decode("utf-8")

            except Exception as e:
                failed_users.append(user)
                console.print(
                    f"⚠️ [yellow]Failed to rotate key for {user}: {e}[/yellow]"
                )

        if failed_users:
            raise FernetEncryptionError(
                f"Key rotation failed for users: {', '.join(failed_users)}"
            )

        console.print(
            f"✅ [green]Successfully rotated keys for {len(rotated_passwords)} users[/green]"
        )
        return rotated_passwords

    def interactive_encrypt(self) -> str:
        """
        Interactive password encryption with user prompts.

        Returns:
            Encrypted password string
        """
        if not self._fernet:
            console.print("❌ [red]No Fernet key available![/red]")
            console.print("\nTo set up encryption:")
            console.print(
                "1. Generate a key: [cyan]uv run user generate-fernet-key[/cyan]"
            )
            console.print(
                "2. Set environment variable: [cyan]export SNOWFLAKE_CONFIG_FERNET_KEYS='your-key'[/cyan]"
            )
            raise FernetKeyMissingError("No Fernet key available")

        # Get password securely
        password = Prompt.ask("Enter password to encrypt", password=True)

        if not password:
            console.print("❌ [red]Password cannot be empty[/red]")
            return ""

        # Confirm password
        confirm_password = Prompt.ask("Confirm password", password=True)

        if password != confirm_password:
            console.print("❌ [red]Passwords do not match[/red]")
            return ""

        try:
            encrypted = self.encrypt_password(password)
            console.print(f"✅ [green]Password encrypted successfully![/green]")
            console.print(f"Encrypted password: [cyan]{encrypted}[/cyan]")

            # Offer to verify
            if Confirm.ask("Verify encryption by decrypting?"):
                decrypted = self.decrypt_password(encrypted)
                if decrypted == password:
                    console.print("✅ [green]Verification successful![/green]")
                else:
                    console.print("❌ [red]Verification failed![/red]")

            return encrypted

        except Exception as e:
            console.print(f"❌ [red]Encryption failed: {e}[/red]")
            return ""

    def export_key_info(self) -> Dict[str, Any]:
        """
        Export key information for backup/recovery.

        Returns:
            Dictionary with key metadata (not the actual key)
        """
        return {
            "has_key": self._fernet is not None,
            "key_source": "environment" if self._load_key_from_env() else "constructor",
            "algorithm": "Fernet (AES-128 in CBC mode with HMAC-SHA256)",
            "key_length": 44 if self.key else 0,  # Base64 length
        }
