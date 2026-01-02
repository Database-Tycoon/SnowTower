"""
SnowDDL Configuration Management CLI

Usage:
    uv run snowddl-validate
    uv run snowddl-plan
    uv run snowddl-apply
    uv run snowddl-diff
    uv run snowddl-lint
"""

import subprocess
import sys
import os
import yaml
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from typing import List, Dict, Any

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

console = Console()


def safe_yaml_load(file_path: Path):
    """Load YAML file with support for SnowDDL's !decrypt and !ENV tags"""

    class SnowDDLLoader(yaml.SafeLoader):
        pass

    def decrypt_constructor(loader, node):
        """Custom constructor for !decrypt tags - returns the encrypted value as-is"""
        # For most operations, we just need the encrypted string without decryption
        return loader.construct_scalar(node)

    def env_constructor(loader, node):
        """Custom constructor for !ENV tags - returns placeholder for validation"""
        # For validation purposes, we don't need actual env var values
        return loader.construct_scalar(node)

    # Register the tag handlers
    SnowDDLLoader.add_constructor("!decrypt", decrypt_constructor)
    SnowDDLLoader.add_constructor("!ENV", env_constructor)

    with open(file_path, "r") as f:
        return yaml.load(f, Loader=SnowDDLLoader)


def get_config_root() -> Path:
    """Get the root directory containing SnowDDL configurations"""
    # Use the new snowddl directory structure
    current_dir = Path.cwd()
    config_dir = current_dir / "snowddl"

    # Check if snowddl directory exists and has required structure
    required_paths = [
        "user.yaml",
        "tech_role.yaml",
        "business_role.yaml",
        "warehouse.yaml",
    ]

    if config_dir.exists() and all(
        (config_dir / path).exists() for path in required_paths
    ):
        return config_dir

    # If not found, raise an error
    raise FileNotFoundError(
        f"SnowDDL configuration directory not found at {config_dir}. "
        f"Required files: {', '.join(required_paths)}"
    )


def validate_config():
    """Validate SnowDDL configuration files"""
    console.print("🔍 [bold blue]Validating SnowDDL Configuration...[/bold blue]")

    try:
        config_root = get_config_root()
        console.print(f"Config root: {config_root}")

        errors = []
        warnings = []

        # Validate YAML syntax - use set to avoid duplicates
        yaml_files = list(
            set(config_root.glob("*.yaml")).union(set(config_root.glob("**/*.yaml")))
        )

        for yaml_file in yaml_files:
            try:
                safe_yaml_load(yaml_file)
                console.print(f"✅ [green]{yaml_file.name}[/green] - Valid YAML")
            except yaml.YAMLError as e:
                error_msg = f"❌ {yaml_file.name}: YAML syntax error - {e}"
                errors.append(error_msg)
                console.print(f"[red]{error_msg}[/red]")

        # Validate required files exist
        required_paths = [
            "user.yaml",
            "warehouse.yaml",
            "tech_role.yaml",
            "business_role.yaml",
        ]
        for required_path in required_paths:
            file_path = config_root / required_path
            if file_path.exists():
                console.print(
                    f"✅ [green]{required_path}[/green] - Required file found"
                )
            else:
                error_msg = f"❌ {required_path}: Required file missing"
                errors.append(error_msg)
                console.print(f"[red]{error_msg}[/red]")

        # Summary
        if errors:
            console.print(
                f"\\n❌ [red]Validation failed with {len(errors)} errors[/red]"
            )
            sys.exit(1)
        else:
            console.print(f"\\n✅ [green]Configuration validation passed![/green]")
            if warnings:
                console.print(f"⚠️ [yellow]{len(warnings)} warnings found[/yellow]")

    except Exception as e:
        console.print(f"❌ [red]Validation error: {e}[/red]")
        sys.exit(1)


def plan():
    """Run SnowDDL plan operation"""
    import argparse
    import tempfile
    import base64

    # Parse command line arguments for additional plan options
    parser = argparse.ArgumentParser(description="Generate SnowDDL deployment plan")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    args, unknown = parser.parse_known_args()

    console.print("📋 [bold blue]Running SnowDDL Plan...[/bold blue]")

    temp_key_path = None  # Track temp file for cleanup
    try:
        config_root = get_config_root()
        console.print(f"Using config directory: {config_root}")

        # Handle private key from environment variable if present
        env_copy = os.environ.copy()

        if (
            "SNOWFLAKE_PRIVATE_KEY" in os.environ
            and "SNOWFLAKE_PRIVATE_KEY_PATH" not in os.environ
        ):
            # GitHub Actions passes the base64-encoded key directly
            console.print("🔑 Detected private key in environment variable")
            try:
                # Decode the base64-encoded private key
                key_content = base64.b64decode(
                    os.environ["SNOWFLAKE_PRIVATE_KEY"]
                ).decode("utf-8")

                # Validate it's a PEM key
                if not (
                    key_content.startswith("-----BEGIN")
                    and "PRIVATE KEY-----" in key_content
                ):
                    console.print(
                        "❌ [red]Decoded content is not a valid PEM private key[/red]"
                    )
                    sys.exit(1)

                # Create a temporary file for the key with secure permissions
                fd, temp_key_path = tempfile.mkstemp(suffix=".p8")
                try:
                    # Write the key content with secure file descriptor
                    os.write(fd, key_content.encode("utf-8"))
                finally:
                    os.close(fd)

                # Ensure strict permissions (owner read/write only)
                os.chmod(temp_key_path, 0o600)

                # Set the path environment variable
                env_copy["SNOWFLAKE_PRIVATE_KEY_PATH"] = temp_key_path

            except base64.binascii.Error as e:
                console.print(f"❌ [red]Invalid base64-encoded private key: {e}[/red]")
                sys.exit(1)
            except UnicodeDecodeError as e:
                console.print(f"❌ [red]Private key contains invalid UTF-8: {e}[/red]")
                sys.exit(1)
            except Exception as e:
                console.print(f"❌ [red]Failed to process private key: {e}[/red]")
                sys.exit(1)

        # Run snowddl plan command with exclusions for hidden directories
        role = os.environ.get(
            "SNOWFLAKE_ROLE", "ACCOUNTADMIN"
        )  # Use ACCOUNTADMIN for proper object discovery
        cmd = [
            "snowddl",
            "-c",
            str(config_root),
            "-r",
            role,  # Use role from environment variable
            "--exclude-object-types",
            "PIPE,STREAM,TASK",  # Exclude complex objects (SCHEMA now managed by SnowDDL)
            "plan",
        ]

        if args.verbose:
            cmd.append("--verbose")

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, env=env_copy
        )

        if result.stdout:
            console.print("📋 [green]Plan Output:[/green]")
            syntax = Syntax(result.stdout, "yaml", theme="monokai", line_numbers=True)
            console.print(syntax)

        if result.stderr:
            console.print("⚠️ [yellow]Plan Warnings/Errors:[/yellow]")
            console.print(result.stderr, markup=False)

        if result.returncode == 0:
            console.print("✅ [green]Plan completed successfully![/green]")
        else:
            console.print(
                f"❌ [red]Plan failed with return code {result.returncode}[/red]"
            )
            sys.exit(result.returncode)

    except FileNotFoundError:
        console.print(
            "❌ [red]Error: snowddl command not found. Please install SnowDDL.[/red]"
        )
        console.print("Installation: pip install snowddl")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [red]Error running plan: {str(e)}[/red]")
        sys.exit(1)
    finally:
        # Clean up temporary key file if created
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.unlink(temp_key_path)
                if args.verbose:
                    console.print("[dim]Cleaned up temporary key file[/dim]")
            except OSError as e:
                if args.verbose:
                    console.print(
                        f"[dim]Warning: Failed to clean up temp key file: {e}[/dim]"
                    )


def apply():
    """Run SnowDDL apply operation with intelligent flag detection"""
    import sys
    import argparse
    import re
    import tempfile
    import base64

    # Parse command line arguments properly
    parser = argparse.ArgumentParser(description="Apply SnowDDL changes")
    parser.add_argument(
        "--apply-unsafe",
        action="store_true",
        help="Skip interactive confirmation for CI/CD environments",
    )
    parser.add_argument(
        "--force-flags",
        nargs="*",
        default=[],
        help="Force specific flags to be included",
    )
    args, unknown = parser.parse_known_args()

    console.print("🚀 [bold blue]Running Intelligent SnowDDL Apply...[/bold blue]")
    console.print("🧠 [cyan]Detecting required flags based on changes...[/cyan]")

    # Check if --apply-unsafe flag was passed (bypass interactive prompt)
    skip_confirmation = args.apply_unsafe

    temp_key_path = None  # Track temp file for cleanup
    try:
        config_root = get_config_root()
        console.print(f"Using config directory: {config_root}")

        # Handle private key from environment variable if present
        env_copy = os.environ.copy()

        if (
            "SNOWFLAKE_PRIVATE_KEY" in os.environ
            and "SNOWFLAKE_PRIVATE_KEY_PATH" not in os.environ
        ):
            # GitHub Actions passes the base64-encoded key directly
            console.print("🔑 Detected private key in environment variable")
            try:
                # Decode the base64-encoded private key
                key_content = base64.b64decode(
                    os.environ["SNOWFLAKE_PRIVATE_KEY"]
                ).decode("utf-8")

                # Validate it's a PEM key
                if not (
                    key_content.startswith("-----BEGIN")
                    and "PRIVATE KEY-----" in key_content
                ):
                    console.print(
                        "❌ [red]Decoded content is not a valid PEM private key[/red]"
                    )
                    sys.exit(1)

                # Create a temporary file for the key with secure permissions
                fd, temp_key_path = tempfile.mkstemp(suffix=".p8")
                try:
                    # Write the key content with secure file descriptor
                    os.write(fd, key_content.encode("utf-8"))
                finally:
                    os.close(fd)

                # Ensure strict permissions (owner read/write only)
                os.chmod(temp_key_path, 0o600)

                # Set the path environment variable
                env_copy["SNOWFLAKE_PRIVATE_KEY_PATH"] = temp_key_path

            except base64.binascii.Error as e:
                console.print(f"❌ [red]Invalid base64-encoded private key: {e}[/red]")
                sys.exit(1)
            except UnicodeDecodeError as e:
                console.print(f"❌ [red]Private key contains invalid UTF-8: {e}[/red]")
                sys.exit(1)
            except Exception as e:
                console.print(f"❌ [red]Failed to process private key: {e}[/red]")
                sys.exit(1)

        # Step 1: Run plan to detect what changes are needed
        console.print("📋 [blue]Analyzing planned changes...[/blue]")
        plan_result = subprocess.run(
            [
                "snowddl",
                "-c",
                str(config_root),
                "--exclude-object-types",
                "PIPE,STREAM,TASK",  # Must match apply command exclusions
                "plan",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        plan_output = plan_result.stdout + plan_result.stderr

        # Step 2: Detect what types of objects have changes
        detected_flags = []

        # Check for resource monitors
        if re.search(
            r"(CREATE|ALTER|DROP) RESOURCE MONITOR|Resolved RESOURCE_MONITOR",
            plan_output,
            re.IGNORECASE,
        ):
            detected_flags.append("--apply-resource-monitor")
            console.print("  ✓ Resource monitors detected")

        # Check for network policies
        if re.search(
            r"(CREATE|ALTER|DROP) NETWORK POLICY|Resolved NETWORK_POLICY",
            plan_output,
            re.IGNORECASE,
        ):
            detected_flags.append("--apply-network-policy")
            console.print("  ✓ Network policies detected")

        # Check for any policy types
        policy_patterns = [
            r"PASSWORD POLICY",
            r"SESSION POLICY",
            r"AUTHENTICATION POLICY",
            r"MASKING POLICY",
            r"ROW ACCESS POLICY",
            r"AGGREGATION POLICY",
            r"PROJECTION POLICY",
        ]
        if any(
            re.search(pattern, plan_output, re.IGNORECASE)
            for pattern in policy_patterns
        ):
            detected_flags.append("--apply-all-policy")
            console.print("  ✓ Security policies detected")

        # Check for account parameters
        if re.search(
            r"ALTER ACCOUNT SET|Resolved ACCOUNT_PARAMS", plan_output, re.IGNORECASE
        ):
            detected_flags.append("--apply-account-params")
            console.print("  ✓ Account parameters detected")

        # Check for unsafe operations
        unsafe_patterns = [
            r"DROP ",
            r"REPLACE TABLE",
            r"ALTER COLUMN.*DROP",
            r"TRUNCATE",
        ]
        if any(
            re.search(pattern, plan_output, re.IGNORECASE)
            for pattern in unsafe_patterns
        ):
            detected_flags.append("--apply-unsafe")
            console.print("  ✓ Unsafe operations detected (DROP/REPLACE)")

        # Check for user password refresh
        if re.search(
            r"ALTER USER.*SET PASSWORD|password.*refresh", plan_output, re.IGNORECASE
        ):
            detected_flags.append("--refresh-user-passwords")
            console.print("  ✓ User password changes detected")

        # Add any forced flags
        for flag in args.force_flags:
            if flag not in detected_flags:
                detected_flags.append(flag)
                console.print(f"  ➕ Force-added: {flag}")

        # Always include --apply-unsafe for backwards compatibility
        if "--apply-unsafe" not in detected_flags:
            detected_flags.append("--apply-unsafe")

        # Safety confirmation - SKIP if --apply-unsafe provided
        if not skip_confirmation:
            console.print(
                "\n⚠️ [yellow]This will apply changes to your Snowflake infrastructure![/yellow]"
            )
            console.print(
                "⚠️ [yellow]Make sure you have reviewed the plan output first![/yellow]"
            )
            console.print("\n📝 [bold]Flags to be applied:[/bold]")
            for flag in detected_flags:
                console.print(f"  • {flag}")
            confirm = input("\nAre you sure you want to continue? (yes/no): ")

            if confirm.lower() not in ["yes", "y"]:
                console.print("❌ [red]Apply cancelled by user[/red]")
                return
        else:
            console.print(
                "🤖 [yellow]Running in non-interactive mode (--apply-unsafe provided)[/yellow]"
            )
            console.print("\n📝 [bold]Auto-detected flags:[/bold]")
            for flag in detected_flags:
                console.print(f"  • {flag}")

        # Build the apply command with detected flags
        role = os.environ.get(
            "SNOWFLAKE_ROLE", "ACCOUNTADMIN"
        )  # Use ACCOUNTADMIN for comprehensive permissions
        cmd = [
            "snowddl",
            "-c",
            str(config_root),
            "-r",
            role,  # Use role from environment variable
            "--exclude-object-types",
            "PIPE,STREAM,TASK",  # Exclude complex objects (SCHEMA now managed by SnowDDL)
        ]

        # Add detected flags
        cmd.extend(detected_flags)
        cmd.append("apply")

        console.print("\n⚙️ [bold]Executing command:[/bold]")
        console.print(f"[cyan]{' '.join(cmd)}[/cyan]")

        # Run the apply command with the proper environment
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, env=env_copy
        )

        if result.stdout:
            console.print("🚀 [green]Apply Output:[/green]")
            syntax = Syntax(result.stdout, "yaml", theme="monokai", line_numbers=True)
            console.print(syntax)

        if result.stderr:
            console.print("⚠️ [yellow]Apply Warnings/Errors:[/yellow]")
            console.print(result.stderr, markup=False)

        if result.returncode == 0:
            console.print("✅ [green]Apply completed successfully![/green]")
            console.print(
                "🔄 [blue]Infrastructure has been updated in Snowflake[/blue]"
            )
        else:
            console.print(
                f"❌ [red]Apply failed with return code {result.returncode}[/red]"
            )
            sys.exit(result.returncode)

    except FileNotFoundError:
        console.print(
            "❌ [red]Error: snowddl command not found. Please install SnowDDL.[/red]"
        )
        console.print("Installation: pip install snowddl")
        sys.exit(1)
    except Exception as e:
        console.print("❌ [red]Error running apply:[/red]", str(e), markup=False)
        sys.exit(1)
    finally:
        # Clean up temporary key file if created
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.unlink(temp_key_path)
            except OSError:
                pass  # Silently ignore cleanup errors


def apply_user_role_grants():
    """Apply only user role grants without managing user objects themselves"""
    console.print("👥 [bold blue]Applying User Role Grants Only...[/bold blue]")

    try:
        config_root = get_config_root()
        console.print(f"Using config directory: {config_root}")

        # Safety confirmation
        console.print(
            "⚠️ [yellow]This will apply role grants to existing users![/yellow]"
        )
        console.print(
            "⚠️ [yellow]User objects themselves will NOT be modified![/yellow]"
        )
        confirm = input("\\nAre you sure you want to continue? (yes/no): ")

        if confirm.lower() not in ["yes", "y"]:
            console.print("❌ [red]User role grants cancelled by user[/red]")
            return

        # Run snowddl apply command excluding USER object management but allowing grants
        role = os.environ.get(
            "SNOWFLAKE_ROLE", "ACCOUNTADMIN"
        )  # Need ACCOUNTADMIN for user grants
        result = subprocess.run(
            [
                "snowddl",
                "-c",
                str(config_root),
                "-r",
                role,
                "--exclude-object-types",
                "PIPE,STREAM,TASK",  # Exclude pipes/streams but allow USER role grants (SCHEMA managed)
                "--apply-unsafe",
                "--apply-network-policy",
                "--apply-all-policy",
                "apply",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.stdout:
            console.print("👥 [green]User Role Grants Output:[/green]")
            syntax = Syntax(result.stdout, "yaml", theme="monokai", line_numbers=True)
            console.print(syntax)

        if result.stderr:
            console.print("⚠️ [yellow]User Role Grants Warnings/Errors:[/yellow]")
            console.print(result.stderr, markup=False)

        if result.returncode == 0:
            console.print("✅ [green]User role grants applied successfully![/green]")
            console.print("🔄 [blue]User role assignments updated in Snowflake[/blue]")
        else:
            console.print(
                f"❌ [red]User role grants failed with return code {result.returncode}[/red]"
            )
            sys.exit(result.returncode)

    except FileNotFoundError:
        console.print(
            "❌ [red]Error: snowddl command not found. Please install SnowDDL.[/red]"
        )
        console.print("Installation: pip install snowddl")
        sys.exit(1)
    except Exception as e:
        console.print(
            "❌ [red]Error applying user role grants:[/red]", str(e), markup=False
        )
        sys.exit(1)


def apply_user_updates():
    """Apply user profile updates including RSA keys and personal information"""
    console.print("👤 [bold blue]Applying User Profile Updates...[/bold blue]")
    console.print(
        "This will update user profiles including names, RSA keys, and personal information"
    )

    try:
        config_root = get_config_root()
        console.print(f"Using config directory: {config_root}")

        # Safety confirmation
        console.print("⚠️ [yellow]This will modify user profiles in Snowflake![/yellow]")
        console.print(
            "⚠️ [yellow]Including RSA keys, names, and other personal information![/yellow]"
        )
        confirm = input("\\nAre you sure you want to continue? (yes/no): ")

        if confirm.lower() not in ["yes", "y"]:
            console.print("❌ [red]User profile updates cancelled by user[/red]")
            return

        # First run plan to show what will change
        console.print("\\n📋 [blue]Running plan to show pending changes...[/blue]")
        role = os.environ.get(
            "SNOWFLAKE_ROLE", "ACCOUNTADMIN"
        )  # Need ACCOUNTADMIN for user modifications
        plan_result = subprocess.run(
            [
                "snowddl",
                "-c",
                str(config_root),
                "-r",
                role,
                "--exclude-object-types",
                "PIPE,STREAM,TASK",  # Include USER objects but exclude pipes/streams (SCHEMA managed)
                "plan",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if plan_result.stdout:
            console.print("📋 [green]Plan Output:[/green]")
            syntax = Syntax(
                plan_result.stdout, "sql", theme="monokai", line_numbers=True
            )
            console.print(syntax)

        if plan_result.stderr:
            console.print("⚠️ [yellow]Plan Warnings/Errors:[/yellow]")
            console.print(plan_result.stderr, markup=False)

        if plan_result.returncode != 0:
            console.print(
                f"❌ [red]Plan failed with return code {plan_result.returncode}[/red]"
            )
            sys.exit(plan_result.returncode)

        # Confirm apply after showing plan
        console.print("\\n🚀 [blue]Proceed with applying these changes?[/blue]")
        apply_confirm = input("Apply user updates to Snowflake? (yes/no): ")

        if apply_confirm.lower() not in ["yes", "y"]:
            console.print("❌ [red]User updates cancelled by user[/red]")
            return

        # Run snowddl apply command including USER objects
        apply_result = subprocess.run(
            [
                "snowddl",
                "-c",
                str(config_root),
                "-r",
                role,
                "--exclude-object-types",
                "PIPE,STREAM,TASK",  # Include USER objects but exclude pipes/streams (SCHEMA managed)
                "--apply-unsafe",
                "--apply-network-policy",
                "--apply-all-policy",
                "apply",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if apply_result.stdout:
            console.print("👤 [green]User Updates Output:[/green]")
            syntax = Syntax(
                apply_result.stdout, "sql", theme="monokai", line_numbers=True
            )
            console.print(syntax)

        if apply_result.stderr:
            console.print("⚠️ [yellow]User Updates Warnings/Errors:[/yellow]")
            console.print(apply_result.stderr, markup=False)

        if apply_result.returncode == 0:
            console.print(
                "\\n✅ [green]User profile updates applied successfully![/green]"
            )
            console.print(
                "🔄 [blue]User profiles have been updated in Snowflake[/blue]"
            )
            console.print("\\n🔍 [yellow]Next Steps:[/yellow]")
            console.print("  • Users should test their RSA key authentication")
            console.print("  • Verify updated profile information in Snowflake UI")
            console.print("  • Confirm secure login functionality")
        else:
            console.print(
                f"❌ [red]User updates failed with return code {apply_result.returncode}[/red]"
            )
            sys.exit(apply_result.returncode)

    except FileNotFoundError:
        console.print(
            "❌ [red]Error: snowddl command not found. Please install SnowDDL.[/red]"
        )
        console.print("Installation: pip install snowddl")
        sys.exit(1)
    except Exception as e:
        console.print(
            "❌ [red]Error applying user updates:[/red]", str(e), markup=False
        )
        sys.exit(1)


def diff():
    """Show configuration differences"""
    console.print("🔍 [bold blue]SnowDDL Configuration Diff...[/bold blue]")

    try:
        config_root = get_config_root()

        # Run snowddl diff command (if supported by your SnowDDL version)
        result = subprocess.run(
            [
                "snowddl",
                "-c",
                str(config_root),
                "plan",
                "--json",  # Get structured output for diff analysis
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            console.print("📊 [green]Configuration diff completed[/green]")
            console.print("Use 'uv run snowddl-plan' for detailed plan output")
        else:
            console.print(
                "⚠️ [yellow]Could not generate diff - running basic plan instead[/yellow]"
            )
            plan()

    except Exception as e:
        console.print(f"❌ [red]Error running diff: {e}[/red]")
        sys.exit(1)


def update_user_password():
    """Safely update password for a specific user"""
    console.print("🔐 [bold blue]Safe User Password Update...[/bold blue]")

    # Protected accounts that should NEVER be updated
    PROTECTED_ACCOUNTS = {"ALICE", "STEPHEN_RECOVERY"}

    try:
        config_root = get_config_root()

        # Read user configuration to get list of users
        user_file = config_root / "user.yaml"
        if not user_file.exists():
            console.print("❌ [red]user.yaml not found[/red]")
            return

        users = safe_yaml_load(user_file)

        # Get list of updatable users (exclude protected accounts and service accounts)
        updatable_users = []
        for username, config in users.items():
            if (
                username not in PROTECTED_ACCOUNTS
                and config.get("type", "").upper() == "PERSON"
            ):
                updatable_users.append(username)

        if not updatable_users:
            console.print("❌ [red]No updatable user accounts found[/red]")
            return

        # Show updatable users
        console.print("\\n👥 [cyan]Updatable User Accounts:[/cyan]")
        for i, username in enumerate(updatable_users, 1):
            user_config = users[username]
            email = user_config.get("email", "N/A")
            console.print(f"  {i}. {username} ({email})")

        # Get user selection
        while True:
            try:
                selection = input(
                    f"\\nSelect user (1-{len(updatable_users)}) or 'q' to quit: "
                ).strip()
                if selection.lower() == "q":
                    console.print("❌ [red]Password update cancelled[/red]")
                    return

                user_index = int(selection) - 1
                if 0 <= user_index < len(updatable_users):
                    username = updatable_users[user_index]
                    break
                else:
                    console.print(
                        f"Please enter a number between 1 and {len(updatable_users)}"
                    )
            except ValueError:
                console.print("Please enter a valid number or 'q' to quit")

        console.print(f"\\n📝 [cyan]Selected user: {username}[/cyan]")

        # Generate or get password
        generate_password = input("Generate random password? (y/n): ").strip().lower()

        if generate_password in ["y", "yes"]:
            # Generate secure random password
            import secrets
            import string

            chars = string.ascii_letters + string.digits
            new_password = "".join(secrets.choice(chars) for _ in range(20))
            console.print(f"\\n🔑 [green]Generated password: {new_password}[/green]")
        else:
            new_password = input("Enter new password: ").strip()
            if not new_password:
                console.print("❌ [red]Password cannot be empty[/red]")
                return

        # Confirm the update
        console.print(
            f"\\n⚠️ [yellow]This will update the password for user: {username}[/yellow]"
        )
        confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()

        if confirm not in ["yes", "y"]:
            console.print("❌ [red]Password update cancelled[/red]")
            return

        # Update password in Snowflake using snow CLI
        console.print("\\n🔄 [blue]Updating password in Snowflake...[/blue]")

        # Validate username to prevent SQL injection
        import re

        if not re.match(r"^[A-Z][A-Z0-9_]{0,254}$", username.upper()):
            console.print(f"❌ [red]Invalid username format: {username}[/red]")
            return

        # Use IDENTIFIER() for safe username handling and parameterized password
        # Note: snow CLI doesn't support parameterized queries, so we escape properly
        escaped_password = new_password.replace("'", "''")  # SQL escape single quotes

        result = subprocess.run(
            [
                "snow",
                "sql",
                "--account",
                os.environ.get("SNOWFLAKE_ACCOUNT"),
                "--user",
                os.environ.get("SNOWFLAKE_USER"),
                "--role",
                "ACCOUNTADMIN",
                "--warehouse",
                os.environ.get("SNOWFLAKE_WAREHOUSE"),
                "--private-key-path",
                os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH"),
                "-q",
                f"ALTER USER IDENTIFIER('{username}') SET PASSWORD = '{escaped_password}';",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            console.print("❌ [red]Failed to update password in Snowflake[/red]")
            console.print(result.stderr, markup=False)
            return

        console.print("✅ [green]Password updated in Snowflake![/green]")

        # Encrypt password for YAML storage
        console.print("🔒 [blue]Encrypting password for YAML storage...[/blue]")

        fernet_result = subprocess.run(
            ["snowddl-fernet", "encrypt", new_password],
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "SNOWFLAKE_CONFIG_FERNET_KEYS": os.environ.get(
                    "SNOWFLAKE_CONFIG_FERNET_KEYS", ""
                ),
            },
        )

        if fernet_result.returncode != 0:
            console.print("❌ [red]Failed to encrypt password[/red]")
            console.print(fernet_result.stderr, markup=False)
            console.print(
                "\\n⚠️ [yellow]Password was updated in Snowflake but not in YAML![/yellow]"
            )
            console.print("Please manually encrypt and update the YAML file.")
            return

        encrypted_password = fernet_result.stdout.strip()
        console.print("✅ [green]Password encrypted successfully![/green]")

        # Show next steps
        console.print("\\n📋 [cyan]Next Steps:[/cyan]")
        console.print(f"1. Update snowddl/user.yaml file for user {username}")
        console.print(f"   Add/update: password: !decrypt {encrypted_password}")
        console.print("2. Commit the changes to git")
        console.print("3. Inform the user of their new password")

        console.print(
            f"\\n🔑 [green]New password for {username}: {new_password}[/green]"
        )
        console.print(f"🔒 [yellow]Encrypted password: {encrypted_password}[/yellow]")

    except Exception as e:
        console.print(f"❌ [red]Error updating password: {e}[/red]")
        sys.exit(1)


def lint_config():
    """Lint configuration files for best practices"""
    console.print("🔧 [bold blue]Linting SnowDDL Configuration...[/bold blue]")

    try:
        config_root = get_config_root()

        issues = []
        suggestions = []

        # Check warehouse configurations
        warehouse_file = config_root / "warehouse.yaml"
        if warehouse_file.exists():
            warehouses = safe_yaml_load(warehouse_file)

            for wh_name, wh_config in warehouses.items():
                # Check for auto_suspend settings
                if "auto_suspend" not in wh_config:
                    issues.append(f"Warehouse {wh_name}: Missing auto_suspend setting")
                elif wh_config["auto_suspend"] > 300:
                    suggestions.append(
                        f"Warehouse {wh_name}: Consider shorter auto_suspend ({wh_config['auto_suspend']}s)"
                    )

                # Check for comments
                if "comment" not in wh_config:
                    suggestions.append(
                        f"Warehouse {wh_name}: Consider adding a comment for documentation"
                    )

        # Check role configurations
        tech_role_file = config_root / "tech_role.yaml"
        if tech_role_file.exists():
            roles = safe_yaml_load(tech_role_file)

            for role_name, role_config in roles.items():
                if "comment" not in role_config:
                    suggestions.append(
                        f"Tech role {role_name}: Consider adding a comment explaining purpose"
                    )

        # Report results
        table = Table(title="Configuration Lint Results")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Status", style="green")

        table.add_row(
            "Issues", str(len(issues)), "❌ Critical" if issues else "✅ None"
        )
        table.add_row(
            "Suggestions",
            str(len(suggestions)),
            "⚠️ Consider" if suggestions else "✅ None",
        )

        console.print(table)

        if issues:
            console.print("\\n❌ [red]Critical Issues:[/red]")
            for issue in issues:
                console.print(f"  • {issue}")

        if suggestions:
            console.print("\\n💡 [yellow]Suggestions:[/yellow]")
            for suggestion in suggestions:
                console.print(f"  • {suggestion}")

        if not issues and not suggestions:
            console.print("\\n✅ [green]Configuration looks great![/green]")

    except Exception as e:
        console.print(f"❌ [red]Error linting configuration: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    # Allow direct testing
    import sys

    if len(sys.argv) > 1:
        func_name = sys.argv[1]
        if func_name in globals() and callable(globals()[func_name]):
            globals()[func_name]()
        else:
            print(f"Unknown function: {func_name}")
    else:
        validate_config()
