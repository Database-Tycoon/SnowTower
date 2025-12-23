"""
RSA Key Management for SnowTower User Management

Handles RSA key pair generation, validation, and management for Snowflake authentication.
Provides secure key-pair authentication setup for SnowDDL users.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

console = Console()


class RSAKeyError(Exception):
    """Base exception for RSA key operations"""

    pass


class RSAKeyGenerationError(RSAKeyError):
    """Raised when RSA key generation fails"""

    pass


class RSAKeyValidationError(RSAKeyError):
    """Raised when RSA key validation fails"""

    pass


class RSAKeyManager:
    """
    RSA Key pair management for SnowTower users.

    Handles generation, validation, and management of RSA key pairs
    used for Snowflake authentication.
    """

    def __init__(self, keys_directory: Optional[Path] = None):
        """
        Initialize RSA key manager.

        Args:
            keys_directory: Directory to store keys. Defaults to ./keys/
        """
        self.keys_dir = keys_directory or Path.cwd() / "keys"
        self.keys_dir.mkdir(exist_ok=True, mode=0o700)  # Secure directory permissions

        # Check for required tools
        self._check_openssl_available()

    def _check_openssl_available(self) -> None:
        """Check if OpenSSL is available"""
        if not shutil.which("openssl"):
            raise RSAKeyError(
                "OpenSSL is not available. Please install OpenSSL to use RSA key features.\n"
                "macOS: brew install openssl\n"
                "Ubuntu: apt-get install openssl\n"
                "Windows: Download from https://slproweb.com/products/Win32OpenSSL.html"
            )

    def generate_key_pair(
        self, username: str, key_size: int = 2048
    ) -> Tuple[Path, Path]:
        """
        Generate RSA key pair for a user.

        Args:
            username: Username for key pair
            key_size: RSA key size in bits (default: 2048)

        Returns:
            Tuple of (private_key_path, public_key_path)

        Raises:
            RSAKeyGenerationError: If key generation fails

        Example:
            >>> key_manager = RSAKeyManager()
            >>> private_key, public_key = key_manager.generate_key_pair("JOHN_DOE")
        """
        if key_size < 2048:
            raise RSAKeyGenerationError(
                "RSA key size must be at least 2048 bits for security"
            )

        username_lower = username.lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Key file paths
        private_key_path = self.keys_dir / f"{username_lower}_rsa_key_{timestamp}.p8"
        public_key_path = self.keys_dir / f"{username_lower}_rsa_key_{timestamp}.pub"
        temp_private_path = self.keys_dir / f"{username_lower}_temp_rsa.pem"

        console.print(
            f"🔑 [blue]Generating {key_size}-bit RSA key pair for {username}...[/blue]"
        )

        try:
            # Step 1: Generate private key in PEM format
            result = subprocess.run(
                ["openssl", "genrsa", "-out", str(temp_private_path), str(key_size)],
                capture_output=True,
                text=True,
                check=True,
            )

            # Step 2: Convert to PKCS#8 format (required by Snowflake)
            subprocess.run(
                [
                    "openssl",
                    "pkcs8",
                    "-topk8",
                    "-inform",
                    "PEM",
                    "-outform",
                    "PEM",
                    "-nocrypt",
                    "-in",
                    str(temp_private_path),
                    "-out",
                    str(private_key_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Step 3: Generate public key
            subprocess.run(
                [
                    "openssl",
                    "rsa",
                    "-in",
                    str(private_key_path),
                    "-pubout",
                    "-out",
                    str(public_key_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Step 4: Set secure permissions
            private_key_path.chmod(0o600)  # Read/write for owner only
            public_key_path.chmod(0o644)  # Read for all, write for owner

            # Step 5: Clean up temporary file
            if temp_private_path.exists():
                temp_private_path.unlink()

            console.print(f"✅ [green]RSA key pair generated successfully![/green]")
            console.print(f"Private key: [cyan]{private_key_path}[/cyan]")
            console.print(f"Public key: [cyan]{public_key_path}[/cyan]")

            return private_key_path, public_key_path

        except subprocess.CalledProcessError as e:
            # Clean up any partial files
            for path in [private_key_path, public_key_path, temp_private_path]:
                if path.exists():
                    path.unlink()

            raise RSAKeyGenerationError(
                f"Failed to generate RSA key pair: {e.stderr or e.stdout or 'Unknown error'}"
            )
        except Exception as e:
            raise RSAKeyGenerationError(f"Unexpected error during key generation: {e}")

    def validate_key_pair(self, private_key_path: Path, public_key_path: Path) -> bool:
        """
        Validate that a private and public key form a valid pair.

        Args:
            private_key_path: Path to private key file
            public_key_path: Path to public key file

        Returns:
            True if key pair is valid, False otherwise

        Raises:
            RSAKeyValidationError: If validation fails due to file issues
        """
        if not private_key_path.exists():
            raise RSAKeyValidationError(
                f"Private key file not found: {private_key_path}"
            )

        if not public_key_path.exists():
            raise RSAKeyValidationError(f"Public key file not found: {public_key_path}")

        try:
            # Extract public key from private key
            result_private = subprocess.run(
                ["openssl", "rsa", "-in", str(private_key_path), "-pubout"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Read stored public key
            with open(public_key_path, "r") as f:
                stored_public_key = f.read().strip()

            extracted_public_key = result_private.stdout.strip()

            # Compare keys
            return extracted_public_key == stored_public_key

        except subprocess.CalledProcessError as e:
            raise RSAKeyValidationError(f"Failed to validate key pair: {e.stderr}")
        except Exception as e:
            raise RSAKeyValidationError(f"Unexpected validation error: {e}")

    def extract_public_key_for_snowflake(self, private_key_path: Path) -> str:
        """
        Extract public key from private key in Snowflake-compatible format.

        Args:
            private_key_path: Path to private key file

        Returns:
            Public key string without headers/footers for Snowflake

        Raises:
            RSAKeyError: If extraction fails
        """
        if not private_key_path.exists():
            raise RSAKeyError(f"Private key file not found: {private_key_path}")

        try:
            # Extract public key
            result = subprocess.run(
                ["openssl", "rsa", "-in", str(private_key_path), "-pubout"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Remove headers and format for Snowflake
            public_key_lines = result.stdout.strip().split("\n")
            # Remove first and last lines (headers)
            key_content = "".join(public_key_lines[1:-1])

            return key_content

        except subprocess.CalledProcessError as e:
            raise RSAKeyError(f"Failed to extract public key: {e.stderr}")

    def rotate_keys(self, username: str, keep_previous: int = 1) -> Tuple[Path, Path]:
        """
        Generate new RSA key pair and optionally keep previous keys.

        Args:
            username: Username for key rotation
            keep_previous: Number of previous key pairs to keep (default: 1)

        Returns:
            Tuple of (new_private_key_path, new_public_key_path)
        """
        console.print(f"🔄 [blue]Rotating RSA keys for {username}...[/blue]")

        # Generate new key pair
        new_private, new_public = self.generate_key_pair(username)

        # Archive old keys if requested
        if keep_previous > 0:
            self._archive_old_keys(username, keep_previous)

        console.print(f"✅ [green]Key rotation completed for {username}[/green]")
        return new_private, new_public

    def _archive_old_keys(self, username: str, keep_count: int) -> None:
        """Archive old keys for a user, keeping only the specified number"""
        username_lower = username.lower()

        # Find all key files for this user
        private_keys = list(self.keys_dir.glob(f"{username_lower}_rsa_key_*.p8"))
        public_keys = list(self.keys_dir.glob(f"{username_lower}_rsa_key_*.pub"))

        # Sort by modification time (newest first)
        private_keys.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        public_keys.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Keep only the specified number of key pairs
        for old_key in private_keys[keep_count:]:
            console.print(
                f"🗑️ [yellow]Archiving old private key: {old_key.name}[/yellow]"
            )
            old_key.unlink()

        for old_key in public_keys[keep_count:]:
            console.print(
                f"🗑️ [yellow]Archiving old public key: {old_key.name}[/yellow]"
            )
            old_key.unlink()

    def list_keys(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all RSA keys, optionally filtered by username.

        Args:
            username: Optional username to filter keys

        Returns:
            List of key information dictionaries
        """
        pattern = f"{username.lower()}_rsa_key_*.p8" if username else "*_rsa_key_*.p8"
        private_keys = list(self.keys_dir.glob(pattern))

        keys_info = []
        for private_key in private_keys:
            # Extract username from filename
            parts = private_key.stem.split("_")
            key_username = parts[0].upper()
            timestamp = "_".join(parts[3:])  # Everything after 'rsa_key_'

            # Find corresponding public key
            public_key = private_key.with_suffix(".pub")

            # Get file stats
            stat = private_key.stat()

            key_info = {
                "username": key_username,
                "timestamp": timestamp,
                "private_key_path": private_key,
                "public_key_path": public_key,
                "has_public_key": public_key.exists(),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "size_bytes": stat.st_size,
                "permissions": oct(stat.st_mode)[-3:],
            }

            # Validate key pair if both files exist
            if key_info["has_public_key"]:
                try:
                    key_info["is_valid_pair"] = self.validate_key_pair(
                        private_key, public_key
                    )
                except RSAKeyValidationError:
                    key_info["is_valid_pair"] = False
            else:
                key_info["is_valid_pair"] = False

            keys_info.append(key_info)

        # Sort by creation time (newest first)
        keys_info.sort(key=lambda x: x["created"], reverse=True)
        return keys_info

    def display_keys_table(self, username: Optional[str] = None) -> None:
        """Display RSA keys in a formatted table"""
        keys = self.list_keys(username)

        if not keys:
            filter_msg = f" for {username}" if username else ""
            console.print(f"📭 [yellow]No RSA keys found{filter_msg}[/yellow]")
            return

        table = Table(title=f"RSA Keys{f' for {username}' if username else ''}")
        table.add_column("Username", style="cyan")
        table.add_column("Created", style="blue")
        table.add_column("Valid Pair", style="green")
        table.add_column("Permissions", style="yellow")
        table.add_column("Private Key Path", style="dim")

        for key_info in keys:
            valid_icon = "✅" if key_info["is_valid_pair"] else "❌"
            table.add_row(
                key_info["username"],
                key_info["created"].strftime("%Y-%m-%d %H:%M:%S"),
                valid_icon,
                key_info["permissions"],
                str(key_info["private_key_path"].name),
            )

        console.print(table)

    def cleanup_old_keys(self, username: str, keep_last: int = 1) -> int:
        """
        Clean up old keys for a user, keeping only the most recent ones.

        Args:
            username: Username to clean up keys for
            keep_last: Number of most recent key pairs to keep

        Returns:
            Number of key pairs removed
        """
        if keep_last < 1:
            raise ValueError("Must keep at least 1 key pair")

        keys = self.list_keys(username)

        if len(keys) <= keep_last:
            console.print(
                f"📝 [blue]No cleanup needed for {username} (have {len(keys)} keys)[/blue]"
            )
            return 0

        keys_to_remove = keys[keep_last:]

        console.print(
            f"🧹 [yellow]Cleaning up {len(keys_to_remove)} old key pairs for {username}...[/yellow]"
        )

        removed_count = 0
        for key_info in keys_to_remove:
            try:
                # Remove private key
                if key_info["private_key_path"].exists():
                    key_info["private_key_path"].unlink()
                    removed_count += 1

                # Remove public key
                if key_info["public_key_path"].exists():
                    key_info["public_key_path"].unlink()

                console.print(f"  🗑️ Removed: {key_info['private_key_path'].name}")

            except Exception as e:
                console.print(
                    f"  ❌ [red]Failed to remove {key_info['private_key_path'].name}: {e}[/red]"
                )

        console.print(
            f"✅ [green]Cleanup completed: removed {removed_count} key pairs[/green]"
        )
        return removed_count

    def get_latest_key_pair(self, username: str) -> Optional[Tuple[Path, Path]]:
        """
        Get the most recent key pair for a user.

        Args:
            username: Username to get keys for

        Returns:
            Tuple of (private_key_path, public_key_path) or None if no keys found
        """
        keys = self.list_keys(username)

        if not keys:
            return None

        # Keys are already sorted by creation time (newest first)
        latest_key = keys[0]

        if latest_key["is_valid_pair"]:
            return latest_key["private_key_path"], latest_key["public_key_path"]

        # If the latest isn't valid, try to find a valid one
        for key_info in keys:
            if key_info["is_valid_pair"]:
                return key_info["private_key_path"], key_info["public_key_path"]

        return None
