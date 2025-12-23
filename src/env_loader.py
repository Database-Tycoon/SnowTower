#!/usr/bin/env python3
"""
Environment Variable Loader for SnowTower SnowDDL

This module provides a reliable utility for loading and validating environment variables
from .env files for all SnowTower SnowDDL scripts. It eliminates the common authentication
failures and script execution problems caused by inconsistent environment variable loading.

Features:
- Auto-detects .env file location (project root)
- Validates required Snowflake environment variables
- Ensures at least one authentication method is available (RSA key OR password)
- Provides clear error messages for missing variables
- Supports both dict return and direct environment loading
- Comprehensive logging for troubleshooting

Usage:
    from env_loader import load_snowflake_env, validate_auth

    # Load and validate all environment variables
    env_vars = load_snowflake_env()

    # Quick validation check
    is_valid = validate_auth()

    # Test environment from command line
    uv run test-env
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnvironmentError(Exception):
    """Custom exception for environment variable issues."""

    pass


class AuthenticationError(EnvironmentError):
    """Custom exception for authentication configuration issues."""

    pass


# Required environment variables for Snowflake connection
REQUIRED_VARS = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_CONFIG_FERNET_KEYS",
]

# Optional variables that may be needed based on configuration
OPTIONAL_VARS = [
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_PRIVATE_KEY_PATH",
    "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE",
    "SNOWFLAKE_REGION",
    "SNOWFLAKE_CONNECT_TIMEOUT",
    "SNOWFLAKE_NETWORK_TIMEOUT",
]

# Authentication methods (at least one required)
AUTH_VARS = ["SNOWFLAKE_PRIVATE_KEY_PATH", "SNOWFLAKE_PASSWORD"]


def find_env_file() -> Optional[Path]:
    """
    Find the .env file in the project hierarchy.

    Searches from current directory up to project root.

    Returns:
        Path to .env file if found, None otherwise
    """
    current_dir = Path.cwd()

    # First try current directory
    env_path = current_dir / ".env"
    if env_path.exists():
        logger.debug(f"Found .env file at: {env_path}")
        return env_path

    # Try to find project root indicators
    project_indicators = ["pyproject.toml", "setup.py", ".git", "uv.lock"]

    # Walk up the directory tree
    for parent in [current_dir] + list(current_dir.parents):
        # Check if this looks like project root
        if any((parent / indicator).exists() for indicator in project_indicators):
            env_path = parent / ".env"
            if env_path.exists():
                logger.debug(f"Found .env file at project root: {env_path}")
                return env_path

    # Allow environment variable override for custom .env location
    env_override = os.environ.get("SNOWTOWER_ENV_PATH")
    if env_override:
        override_path = Path(env_override)
        if override_path.exists():
            logger.debug(f"Found .env file at environment override: {override_path}")
            return override_path
        else:
            logger.warning(
                f"SNOWTOWER_ENV_PATH points to non-existent file: {override_path}"
            )

    return None


def load_env_file() -> bool:
    """
    Load environment variables from .env file.

    Returns:
        True if .env file was found and loaded, False otherwise

    Raises:
        EnvironmentError: If .env file cannot be found
    """
    env_path = find_env_file()

    if env_path is None:
        raise EnvironmentError(
            "No .env file found. Please ensure .env file exists in:\n"
            "  - Current directory\n"
            "  - Project root directory\n"
            "  - /Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl/"
        )

    try:
        success = load_dotenv(env_path, override=True)
        if success:
            logger.info(f"Successfully loaded environment variables from: {env_path}")
        else:
            logger.warning(f"Failed to load environment variables from: {env_path}")
        return success
    except Exception as e:
        raise EnvironmentError(f"Error loading .env file {env_path}: {str(e)}")


def validate_required_vars() -> Tuple[List[str], List[str]]:
    """
    Validate that required environment variables are present.

    Returns:
        Tuple of (present_vars, missing_vars)
    """
    present_vars = []
    missing_vars = []

    for var in REQUIRED_VARS:
        value = os.getenv(var)
        if value and value.strip():
            present_vars.append(var)
            logger.debug(f"✓ {var}: {'*' * min(len(value), 8)}")
        else:
            missing_vars.append(var)
            logger.warning(f"✗ {var}: Missing or empty")

    return present_vars, missing_vars


def validate_auth_config() -> Tuple[bool, List[str], str]:
    """
    Validate authentication configuration.

    At least one authentication method must be configured:
    - SNOWFLAKE_PRIVATE_KEY_PATH (preferred)
    - SNOWFLAKE_PASSWORD (fallback)

    Returns:
        Tuple of (is_valid, available_methods, recommended_method)
    """
    available_methods = []

    # Check RSA key authentication
    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    if key_path and key_path.strip():
        key_file = Path(key_path)
        if key_file.exists() and key_file.is_file():
            available_methods.append("RSA_KEY")
            logger.debug(f"✓ RSA Key found at: {key_path}")
        else:
            logger.warning(f"✗ RSA Key path specified but file not found: {key_path}")

    # Check password authentication
    password = os.getenv("SNOWFLAKE_PASSWORD")
    if password and password.strip():
        available_methods.append("PASSWORD")
        logger.debug("✓ Password authentication available")

    is_valid = len(available_methods) > 0

    if "RSA_KEY" in available_methods:
        recommended_method = "RSA_KEY"
    elif "PASSWORD" in available_methods:
        recommended_method = "PASSWORD"
    else:
        recommended_method = "NONE"

    return is_valid, available_methods, recommended_method


def load_snowflake_env(validate_auth: bool = True) -> Dict[str, str]:
    """
    Load and validate all Snowflake environment variables.

    Args:
        validate_auth: Whether to validate authentication configuration

    Returns:
        Dictionary containing all loaded environment variables

    Raises:
        EnvironmentError: If required variables are missing
        AuthenticationError: If authentication configuration is invalid
    """
    logger.info("Loading Snowflake environment configuration...")

    # Load .env file
    load_env_file()

    # Validate required variables
    present_vars, missing_vars = validate_required_vars()

    if missing_vars:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_vars)}\n\n"
            "Required variables:\n"
            + "\n".join(f"  - {var}" for var in REQUIRED_VARS)
            + "\n\nPlease check your .env file configuration."
        )
        raise EnvironmentError(error_msg)

    # Validate authentication if requested
    if validate_auth:
        auth_valid, auth_methods, recommended = validate_auth_config()

        if not auth_valid:
            error_msg = (
                "No valid authentication method configured.\n\n"
                "Please configure at least one of:\n"
                "  - SNOWFLAKE_PRIVATE_KEY_PATH (recommended)\n"
                "  - SNOWFLAKE_PASSWORD (fallback)\n\n"
                "For RSA key setup, see: docs/RSA_KEY_SETUP.md"
            )
            raise AuthenticationError(error_msg)

        logger.info(f"Authentication methods available: {', '.join(auth_methods)}")
        logger.info(f"Recommended method: {recommended}")

    # Collect all environment variables
    env_vars = {}

    # Add required variables
    for var in REQUIRED_VARS:
        env_vars[var] = os.getenv(var, "")

    # Add optional variables if present
    for var in OPTIONAL_VARS:
        value = os.getenv(var)
        if value is not None:
            env_vars[var] = value

    logger.info(f"Successfully loaded {len(env_vars)} environment variables")
    return env_vars


def validate_auth() -> bool:
    """
    Quick validation of authentication configuration.

    Returns:
        True if authentication is properly configured, False otherwise
    """
    try:
        load_env_file()
        auth_valid, auth_methods, recommended = validate_auth_config()

        if auth_valid:
            logger.info(f"✓ Authentication valid - methods: {', '.join(auth_methods)}")
        else:
            logger.error("✗ No valid authentication method configured")

        return auth_valid

    except Exception as e:
        logger.error(f"Authentication validation failed: {str(e)}")
        return False


def get_connection_info() -> Dict[str, str]:
    """
    Get formatted connection information for debugging.

    Returns:
        Dictionary with connection details (sensitive values masked)
    """
    try:
        env_vars = load_snowflake_env()

        # Mask sensitive values
        masked_vars = {}
        for key, value in env_vars.items():
            if any(
                sensitive in key.upper() for sensitive in ["PASSWORD", "KEY", "SECRET"]
            ):
                masked_vars[key] = "*" * min(len(str(value)), 8) if value else "Not set"
            else:
                masked_vars[key] = value or "Not set"

        return masked_vars

    except Exception as e:
        return {"error": str(e)}


def test_environment() -> None:
    """
    Test environment configuration and print detailed results.

    This function is exposed as the 'test-env' UV script command.
    """
    print("🔍 SnowTower SnowDDL Environment Test")
    print("=" * 50)

    try:
        # Test .env file loading
        env_path = find_env_file()
        if env_path:
            print(f"✓ .env file found: {env_path}")
        else:
            print("✗ .env file not found")
            return

        # Load and validate environment
        env_vars = load_snowflake_env()
        print(f"✓ Loaded {len(env_vars)} environment variables")

        # Show connection information
        print("\n📋 Connection Configuration:")
        print("-" * 30)
        conn_info = get_connection_info()
        for key, value in sorted(conn_info.items()):
            if key != "error":
                print(f"  {key}: {value}")

        # Validate authentication
        print("\n🔐 Authentication Status:")
        print("-" * 25)
        auth_valid, auth_methods, recommended = validate_auth_config()

        if auth_valid:
            print(f"✓ Authentication configured")
            print(f"  Available methods: {', '.join(auth_methods)}")
            print(f"  Recommended: {recommended}")
        else:
            print("✗ No valid authentication method")

        print("\n✅ Environment test completed successfully!")

    except Exception as e:
        print(f"\n❌ Environment test failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    test_environment()
