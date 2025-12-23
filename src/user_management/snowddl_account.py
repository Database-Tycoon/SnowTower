"""
SnowDDL Service Account Management

Special handling for the SNOWDDL service account that is intentionally
kept OUTSIDE of SnowDDL configuration to prevent bootstrap issues.

This account is critical for SnowDDL operations and requires special
management procedures.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()


class SnowDDLAccountError(Exception):
    """Base exception for SnowDDL account operations"""

    pass


class SnowDDLConnectionError(SnowDDLAccountError):
    """Raised when connection to Snowflake fails"""

    pass


class SnowDDLPermissionError(SnowDDLAccountError):
    """Raised when SnowDDL account lacks required permissions"""

    pass


class SnowDDLAccountManager:
    """
    Manages the SNOWDDL service account outside of SnowDDL configuration.

    This account is intentionally kept separate from regular SnowDDL
    management to prevent bootstrap issues and ensure reliable access
    for infrastructure operations.
    """

    def __init__(self):
        """Initialize SnowDDL account manager with default configuration"""
        self.account = os.environ.get("SNOWFLAKE_ACCOUNT")
        if not self.account:
            raise ValueError("SNOWFLAKE_ACCOUNT environment variable must be set")
        self.snowddl_user = "SNOWDDL"
        self.admin_role = "ACCOUNTADMIN"
        self.admin_warehouse = "ADMIN"

        # SnowDDL service account key path
        self.snowddl_key_path = (
            Path.home() / ".snowflake" / "keys" / "snowflake_key_pkcs8.pem"
        )

        # Backup admin credentials for emergency operations
        self.backup_user = "ALICE"
        self.backup_key_path = Path.home() / ".ssh" / "snowflake_stephen.p8"

        # Required roles for SnowDDL operations
        self.required_roles = ["ACCOUNTADMIN", "SYSADMIN", "USERADMIN", "SECURITYADMIN"]

    def _run_snow_command(
        self, query: str, user: str = None, key_path: str = None, timeout: int = 30
    ) -> Tuple[int, str, str]:
        """Execute a snow SQL command and return results"""
        user = user or self.snowddl_user
        key_path = key_path or str(self.snowddl_key_path)

        cmd = [
            "snow",
            "sql",
            "--account",
            self.account,
            "--user",
            user,
            "--role",
            self.admin_role,
            "--warehouse",
            self.admin_warehouse,
            "--private-key-path",
            key_path,
            "-q",
            query,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -1, "", str(e)

    def test_connection(self, detailed: bool = False) -> bool:
        """
        Test SnowDDL service account connectivity.

        Args:
            detailed: Whether to show detailed connection information

        Returns:
            True if connection is successful, False otherwise
        """
        console.print(
            "🔍 [bold blue]Testing SnowDDL Service Account Connection...[/bold blue]"
        )

        # Check if key file exists
        if not self.snowddl_key_path.exists():
            console.print(f"❌ [red]RSA key not found at {self.snowddl_key_path}[/red]")
            console.print("To fix this:")
            console.print(
                "1. Generate RSA keys: [cyan]uv run user generate-keys SNOWDDL[/cyan]"
            )
            console.print("2. Upload public key to Snowflake")
            return False

        console.print(f"✅ [green]RSA key found at {self.snowddl_key_path}[/green]")

        # Test basic connection
        query = "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_TIMESTAMP();"
        returncode, stdout, stderr = self._run_snow_command(query)

        if returncode == 0:
            console.print("✅ [green]Connection successful![/green]")

            if detailed and stdout:
                lines = stdout.strip().split("\n")
                if len(lines) >= 2:  # Header + data
                    data_line = lines[1].split("|")
                    if len(data_line) >= 4:
                        console.print(f"   User: [cyan]{data_line[0].strip()}[/cyan]")
                        console.print(f"   Role: [cyan]{data_line[1].strip()}[/cyan]")
                        console.print(
                            f"   Warehouse: [cyan]{data_line[2].strip()}[/cyan]"
                        )
                        console.print(
                            f"   Timestamp: [cyan]{data_line[3].strip()}[/cyan]"
                        )

            return True
        else:
            console.print("❌ [red]Connection failed![/red]")
            if stderr:
                console.print(f"Error: [red]{stderr}[/red]")
            return False

    def check_permissions(self) -> Dict[str, Any]:
        """
        Check SnowDDL account permissions and roles.

        Returns:
            Dictionary with permission status information
        """
        console.print(
            "🔒 [bold blue]Checking SnowDDL Account Permissions...[/bold blue]"
        )

        # Test connection first
        if not self.test_connection():
            return {
                "has_connection": False,
                "roles": [],
                "missing_roles": self.required_roles,
                "can_manage_users": False,
                "can_manage_roles": False,
                "can_apply_policies": False,
            }

        # Check assigned roles
        query = f"SHOW GRANTS TO USER {self.snowddl_user};"
        returncode, stdout, stderr = self._run_snow_command(query)

        assigned_roles = []
        if returncode == 0 and stdout:
            for line in stdout.split("\n")[1:]:  # Skip header
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) > 1 and "ROLE" in parts[1]:
                        role_name = parts[2].strip() if len(parts) > 2 else ""
                        if role_name:
                            assigned_roles.append(role_name)

        missing_roles = [
            role for role in self.required_roles if role not in assigned_roles
        ]

        # Test specific capabilities
        capabilities = {
            "can_manage_users": self._test_user_management(),
            "can_manage_roles": self._test_role_management(),
            "can_apply_policies": self._test_policy_management(),
        }

        result = {
            "has_connection": True,
            "roles": assigned_roles,
            "missing_roles": missing_roles,
            **capabilities,
        }

        # Display results
        self._display_permission_results(result)
        return result

    def _test_user_management(self) -> bool:
        """Test user management capabilities"""
        query = "SHOW USERS LIMIT 1;"
        returncode, stdout, stderr = self._run_snow_command(query)
        return returncode == 0

    def _test_role_management(self) -> bool:
        """Test role management capabilities"""
        query = "SHOW ROLES LIMIT 1;"
        returncode, stdout, stderr = self._run_snow_command(query)
        return returncode == 0

    def _test_policy_management(self) -> bool:
        """Test policy management capabilities"""
        query = "SHOW NETWORK POLICIES;"
        returncode, stdout, stderr = self._run_snow_command(query)
        return returncode == 0

    def _display_permission_results(self, result: Dict[str, Any]) -> None:
        """Display permission check results in a table"""
        table = Table(title="SnowDDL Account Permissions")
        table.add_column("Permission", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")

        # Connection status
        conn_status = "✅ Connected" if result["has_connection"] else "❌ Failed"
        table.add_row("Connection", conn_status, f"Account: {self.account}")

        # Roles
        role_count = len(result["roles"])
        missing_count = len(result["missing_roles"])
        role_status = (
            "✅ Complete" if missing_count == 0 else f"⚠️ Missing {missing_count}"
        )
        role_details = f"{role_count}/{len(self.required_roles)} required roles"
        table.add_row("Required Roles", role_status, role_details)

        # Capabilities
        capabilities = [
            ("User Management", result["can_manage_users"], "CREATE/ALTER/DROP USERS"),
            ("Role Management", result["can_manage_roles"], "CREATE/ALTER/DROP ROLES"),
            (
                "Policy Management",
                result["can_apply_policies"],
                "CREATE/ALTER/DROP POLICIES",
            ),
        ]

        for cap_name, has_capability, description in capabilities:
            cap_status = "✅ Available" if has_capability else "❌ Limited"
            table.add_row(cap_name, cap_status, description)

        console.print(table)

        # Show missing roles if any
        if result["missing_roles"]:
            console.print("\n⚠️ [yellow]Missing roles:[/yellow]")
            for role in result["missing_roles"]:
                console.print(f"  • [red]{role}[/red]")
            console.print("\nTo grant missing roles:")
            console.print(
                f"[cyan]GRANT {', '.join(result['missing_roles'])} TO USER {self.snowddl_user};[/cyan]"
            )

    def grant_required_roles(self) -> bool:
        """
        Grant all required roles to the SnowDDL service account.

        Returns:
            True if all roles were granted successfully, False otherwise
        """
        console.print(
            "🔑 [bold blue]Granting Required Roles to SnowDDL Account...[/bold blue]"
        )

        # Check current permissions first
        perm_result = self.check_permissions()

        if not perm_result["missing_roles"]:
            console.print("✅ [green]All required roles already granted![/green]")
            return True

        if not Confirm.ask(
            f"Grant missing roles {perm_result['missing_roles']} to {self.snowddl_user}?"
        ):
            console.print("❌ [yellow]Role granting cancelled[/yellow]")
            return False

        success_count = 0
        for role in perm_result["missing_roles"]:
            query = f"GRANT ROLE {role} TO USER {self.snowddl_user};"
            returncode, stdout, stderr = self._run_snow_command(query)

            if returncode == 0:
                console.print(f"✅ [green]Granted {role}[/green]")
                success_count += 1
            else:
                console.print(f"❌ [red]Failed to grant {role}: {stderr}[/red]")

        if success_count == len(perm_result["missing_roles"]):
            console.print("🎉 [green]All required roles granted successfully![/green]")
            return True
        else:
            console.print(
                f"⚠️ [yellow]Granted {success_count}/{len(perm_result['missing_roles'])} roles[/yellow]"
            )
            return False

    def unlock_account(self) -> bool:
        """
        Unlock the SnowDDL account if it's locked.

        Returns:
            True if unlock was successful, False otherwise
        """
        console.print("🔓 [bold blue]Unlocking SnowDDL Account...[/bold blue]")

        query = f"ALTER USER {self.snowddl_user} SET MINS_TO_UNLOCK = 0;"
        returncode, stdout, stderr = self._run_snow_command(query)

        if returncode == 0:
            console.print("✅ [green]SnowDDL account unlocked successfully![/green]")
            return True
        else:
            console.print(f"❌ [red]Failed to unlock account: {stderr}[/red]")
            return False

    def rotate_credentials(self) -> bool:
        """
        Rotate RSA credentials for the SnowDDL account.

        Returns:
            True if rotation was successful, False otherwise
        """
        console.print(
            "🔄 [bold blue]Rotating SnowDDL Account Credentials...[/bold blue]"
        )

        # Import RSAKeyManager here to avoid circular imports
        from .rsa_keys import RSAKeyManager

        try:
            key_manager = RSAKeyManager()

            # Generate new key pair
            private_key, public_key = key_manager.generate_key_pair(self.snowddl_user)

            # Extract public key for Snowflake
            public_key_content = key_manager.extract_public_key_for_snowflake(
                private_key
            )

            # Update Snowflake with new public key
            query = f"ALTER USER {self.snowddl_user} SET RSA_PUBLIC_KEY = '{public_key_content}';"
            returncode, stdout, stderr = self._run_snow_command(query)

            if returncode == 0:
                console.print("✅ [green]Credentials rotated successfully![/green]")
                console.print(f"New private key: [cyan]{private_key}[/cyan]")
                console.print(
                    "\n⚠️ [yellow]Important:[/yellow] Update your environment to use the new key:"
                )
                console.print(f"1. Copy key to: [cyan]{self.snowddl_key_path}[/cyan]")
                console.print("2. Update SNOWFLAKE_PRIVATE_KEY_PATH in .env")
                console.print(
                    "3. Test connection: [cyan]uv run snowddl-account test[/cyan]"
                )

                return True
            else:
                console.print(
                    f"❌ [red]Failed to update public key in Snowflake: {stderr}[/red]"
                )
                return False

        except Exception as e:
            console.print(f"❌ [red]Credential rotation failed: {e}[/red]")
            return False

    def emergency_reset(self) -> bool:
        """
        Emergency reset of SnowDDL account using backup admin credentials.

        Returns:
            True if reset was successful, False otherwise
        """
        console.print("🚨 [bold red]Emergency SnowDDL Account Reset...[/bold red]")

        if not self.backup_key_path.exists():
            console.print(
                f"❌ [red]Backup key not found at {self.backup_key_path}[/red]"
            )
            return False

        if not Confirm.ask("This will reset the SnowDDL account. Continue?"):
            console.print("❌ [yellow]Emergency reset cancelled[/yellow]")
            return False

        # Use backup credentials
        console.print(f"Using backup credentials: {self.backup_user}")

        # Unlock account
        query = f"ALTER USER {self.snowddl_user} SET MINS_TO_UNLOCK = 0;"
        returncode, stdout, stderr = self._run_snow_command(
            query, user=self.backup_user, key_path=str(self.backup_key_path)
        )

        if returncode != 0:
            console.print(f"❌ [red]Failed to unlock account: {stderr}[/red]")
            return False

        # Grant required roles
        success_count = 0
        for role in self.required_roles:
            query = f"GRANT ROLE {role} TO USER {self.snowddl_user};"
            returncode, stdout, stderr = self._run_snow_command(
                query, user=self.backup_user, key_path=str(self.backup_key_path)
            )

            if returncode == 0:
                success_count += 1

        console.print(
            f"✅ [green]Emergency reset completed! Granted {success_count}/{len(self.required_roles)} roles[/green]"
        )

        # Test connection with SnowDDL account
        if self.test_connection():
            console.print("🎉 [green]SnowDDL account is now operational![/green]")
            return True
        else:
            console.print(
                "⚠️ [yellow]Reset completed but connection test failed[/yellow]"
            )
            return False

    def get_account_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the SnowDDL account.

        Returns:
            Dictionary with account status information
        """
        status = {
            "account_name": self.snowddl_user,
            "snowflake_account": self.account,
            "key_file_exists": self.snowddl_key_path.exists(),
            "key_file_path": str(self.snowddl_key_path),
            "connection_working": False,
            "permissions_complete": False,
            "last_checked": datetime.now().isoformat(),
            "issues": [],
        }

        # Test connection
        if self.test_connection():
            status["connection_working"] = True

            # Check permissions
            perm_result = self.check_permissions()
            status["permissions_complete"] = len(perm_result["missing_roles"]) == 0
            status["assigned_roles"] = perm_result["roles"]
            status["missing_roles"] = perm_result["missing_roles"]

            # Check capabilities
            if not perm_result["can_manage_users"]:
                status["issues"].append("Cannot manage users - check USERADMIN role")
            if not perm_result["can_manage_roles"]:
                status["issues"].append("Cannot manage roles - check SYSADMIN role")
            if not perm_result["can_apply_policies"]:
                status["issues"].append(
                    "Cannot manage policies - check SECURITYADMIN role"
                )

        else:
            status["issues"].append("Connection test failed")
            if not status["key_file_exists"]:
                status["issues"].append(
                    f"RSA key file missing: {self.snowddl_key_path}"
                )

        return status
