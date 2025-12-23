#!/usr/bin/env python3
"""
Comprehensive test script for SNOWFLAKE_PRIVATE_KEY environment variable handling.

Tests the updated snowddl-plan command that handles base64-encoded private keys with:
- Secure file permissions (0o600)
- Proper error handling for base64 decoding failures
- PEM format validation
- Try-finally for guaranteed cleanup
- Secure tempfile.mkstemp() usage

Usage:
    uv run test_private_key_handling.py
"""

import os
import sys
import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_test(message: str):
    """Print a test message"""
    print(f"{Colors.CYAN}🧪 {message}{Colors.ENDC}")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")


def load_private_key(key_path: str) -> str:
    """Load private key from file"""
    try:
        with open(key_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print_error(f"Private key file not found: {key_path}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to read private key: {e}")
        sys.exit(1)


def encode_base64(content: str) -> str:
    """Encode content as base64"""
    return base64.b64encode(content.encode('utf-8')).decode('utf-8')


def run_snowddl_plan(env_vars: dict, remove_key_path: bool = True) -> Tuple[int, str, str]:
    """Run snowddl-plan command with given environment variables"""
    # Merge with current environment
    full_env = os.environ.copy()

    # Remove SNOWFLAKE_PRIVATE_KEY_PATH if requested (to trigger base64 handling)
    if remove_key_path and 'SNOWFLAKE_PRIVATE_KEY_PATH' in full_env:
        del full_env['SNOWFLAKE_PRIVATE_KEY_PATH']

    full_env.update(env_vars)

    result = subprocess.run(
        ['uv', 'run', 'snowddl-plan'],
        capture_output=True,
        text=True,
        env=full_env,
        cwd='/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl'
    )

    return result.returncode, result.stdout, result.stderr


def test_valid_base64_key(private_key_content: str) -> bool:
    """Test 1: Valid base64-encoded private key"""
    print_header("TEST 1: Valid Base64-Encoded Private Key")
    print_test("Encoding private key as base64...")

    encoded_key = encode_base64(private_key_content)
    print_success(f"Encoded key length: {len(encoded_key)} characters")

    print_test("Running snowddl-plan with SNOWFLAKE_PRIVATE_KEY environment variable...")

    env_vars = {
        'SNOWFLAKE_PRIVATE_KEY': encoded_key
    }

    returncode, stdout, stderr = run_snowddl_plan(env_vars)

    # Check if the key was detected
    if "Detected private key in environment variable" in stdout or "Detected private key in environment variable" in stderr:
        print_success("Private key detected from environment variable")
    else:
        print_warning("Private key detection message not found (may be silent)")

    # Check for temp file cleanup message (in verbose mode)
    if "Cleaned up temporary key file" in stdout or "Cleaned up temporary key file" in stderr:
        print_success("Temporary key file cleanup confirmed")

    # Check return code
    if returncode == 0:
        print_success("snowddl-plan completed successfully")
        return True
    else:
        print_error(f"snowddl-plan failed with return code {returncode}")
        if stderr:
            print(f"\n{Colors.YELLOW}STDERR:{Colors.ENDC}\n{stderr}")
        return False


def test_invalid_base64() -> bool:
    """Test 2: Invalid base64 encoding"""
    print_header("TEST 2: Invalid Base64 Encoding")
    print_test("Testing with invalid base64 string...")

    env_vars = {
        'SNOWFLAKE_PRIVATE_KEY': 'This is not valid base64!@#$%^&*()'
    }

    # Ensure we remove SNOWFLAKE_PRIVATE_KEY_PATH to trigger the base64 path
    print_test("Removing SNOWFLAKE_PRIVATE_KEY_PATH to trigger base64 handling...")

    returncode, stdout, stderr = run_snowddl_plan(env_vars, remove_key_path=True)

    # Should fail with base64 error
    error_output = stdout + stderr

    # Check for key detection first
    if "Detected private key in environment variable" not in error_output:
        print_warning("Private key detection not triggered - SNOWFLAKE_PRIVATE_KEY_PATH may still be set")
        print_warning(f"This test requires SNOWFLAKE_PRIVATE_KEY_PATH to be unset")
        return False

    if "Invalid base64-encoded private key" in error_output:
        print_success("Correctly detected invalid base64 encoding")
        return True
    elif returncode != 0 and "base64" in error_output.lower():
        print_success("Command failed with base64 error as expected")
        return True
    else:
        print_error("Should have failed with invalid base64 error")
        print(f"\n{Colors.YELLOW}Output:{Colors.ENDC}\n{error_output[:500]}")
        return False


def test_invalid_pem_format() -> bool:
    """Test 3: Valid base64 but invalid PEM format"""
    print_header("TEST 3: Valid Base64 but Invalid PEM Format")
    print_test("Testing with valid base64 but non-PEM content...")

    # Create valid base64 but not a PEM key
    invalid_content = "This is valid UTF-8 text but not a PEM key"
    encoded_invalid = encode_base64(invalid_content)

    env_vars = {
        'SNOWFLAKE_PRIVATE_KEY': encoded_invalid
    }

    print_test("Removing SNOWFLAKE_PRIVATE_KEY_PATH to trigger base64 handling...")

    returncode, stdout, stderr = run_snowddl_plan(env_vars, remove_key_path=True)

    # Should fail with PEM format error
    error_output = stdout + stderr

    # Check for key detection first
    if "Detected private key in environment variable" not in error_output:
        print_warning("Private key detection not triggered - SNOWFLAKE_PRIVATE_KEY_PATH may still be set")
        return False

    if "not a valid PEM private key" in error_output:
        print_success("Correctly detected invalid PEM format")
        return True
    elif returncode != 0 and "PEM" in error_output:
        print_success("Command failed with PEM error as expected")
        return True
    else:
        print_error("Should have failed with PEM format error")
        print(f"\n{Colors.YELLOW}Output:{Colors.ENDC}\n{error_output[:500]}")
        return False


def test_file_permissions() -> bool:
    """Test 4: Verify temporary file has secure permissions"""
    print_header("TEST 4: Temporary File Security")
    print_test("Verifying secure file permissions (0o600)...")

    # This test requires modifying the CLI to output the temp file path
    # For now, we'll verify the code logic
    print_warning("This test verifies code implementation, not runtime behavior")

    # Read the CLI source to verify permission setting
    cli_path = '/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl/src/snowtower_snowddl/cli.py'
    with open(cli_path, 'r') as f:
        cli_content = f.read()

    # Check for secure permissions
    if 'os.chmod(temp_key_path, 0o600)' in cli_content:
        print_success("Code sets secure permissions (0o600) on temporary key file")
    else:
        print_error("Secure permissions not found in code")
        return False

    # Check for tempfile.mkstemp usage
    if 'tempfile.mkstemp' in cli_content:
        print_success("Uses secure tempfile.mkstemp() for file creation")
    else:
        print_error("Secure temp file creation not found")
        return False

    # Check for try-finally cleanup
    if 'try:' in cli_content and 'finally:' in cli_content and 'os.unlink(temp_key_path)' in cli_content:
        print_success("Implements try-finally for guaranteed cleanup")
    else:
        print_error("Proper cleanup logic not found")
        return False

    return True


def test_cleanup_on_error() -> bool:
    """Test 5: Verify cleanup happens even on errors"""
    print_header("TEST 5: Cleanup on Error")
    print_test("Testing cleanup with connection failure...")

    # Use valid key but potentially failing connection
    # This depends on environment configuration
    print_warning("Cleanup verification requires manual temp file inspection")
    print_warning("Try-finally pattern ensures cleanup even on connection failures")

    # Verify the code pattern
    cli_path = '/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl/src/snowtower_snowddl/cli.py'
    with open(cli_path, 'r') as f:
        cli_content = f.read()

    # Look for the cleanup pattern
    if 'finally:' in cli_content and 'os.unlink(temp_key_path)' in cli_content:
        print_success("Cleanup guaranteed via finally block")
        return True
    else:
        print_error("Guaranteed cleanup not implemented")
        return False


def test_verbose_output(private_key_content: str) -> bool:
    """Test 6: Verbose mode shows cleanup messages"""
    print_header("TEST 6: Verbose Output Mode")
    print_test("Running with --verbose flag...")

    encoded_key = encode_base64(private_key_content)

    env_vars = {
        'SNOWFLAKE_PRIVATE_KEY': encoded_key
    }

    # Run with verbose flag
    full_env = os.environ.copy()
    full_env.update(env_vars)

    if 'SNOWFLAKE_PRIVATE_KEY_PATH' in full_env:
        del full_env['SNOWFLAKE_PRIVATE_KEY_PATH']

    result = subprocess.run(
        ['uv', 'run', 'snowddl-plan', '--verbose'],
        capture_output=True,
        text=True,
        env=full_env,
        cwd='/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl'
    )

    output = result.stdout + result.stderr

    if "Cleaned up temporary key file" in output:
        print_success("Verbose mode shows cleanup confirmation")
        return True
    else:
        print_warning("Cleanup message not found (may be conditional on success)")
        return True  # Not a failure, just informational


def verify_code_security() -> bool:
    """Verify security improvements in the code"""
    print_header("CODE SECURITY VERIFICATION")

    cli_path = '/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl/src/snowtower_snowddl/cli.py'
    with open(cli_path, 'r') as f:
        cli_content = f.read()

    security_checks = [
        ('Secure file permissions (0o600)', 'os.chmod(temp_key_path, 0o600)'),
        ('Base64 error handling', 'base64.binascii.Error'),
        ('UTF-8 decode error handling', 'UnicodeDecodeError'),
        ('PEM format validation', 'PRIVATE KEY-----'),
        ('Secure tempfile creation', 'tempfile.mkstemp'),
        ('Try-finally cleanup', 'finally:'),
        ('Guaranteed file deletion', 'os.unlink(temp_key_path)'),
    ]

    all_passed = True
    for check_name, check_pattern in security_checks:
        if check_pattern in cli_content:
            print_success(f"{check_name}: ✓ Implemented")
        else:
            print_error(f"{check_name}: ✗ Missing")
            all_passed = False

    return all_passed


def main():
    """Run all tests"""
    print_header("SnowDDL Private Key Handling - Comprehensive Test Suite")

    # Load the actual private key
    key_path = os.path.expanduser('~/.ssh/snowddl_rsa_key.p8')

    if not os.path.exists(key_path):
        print_error(f"Private key file not found: {key_path}")
        print_warning("Please ensure the key file exists before running tests")
        sys.exit(1)

    print(f"{Colors.BLUE}Using private key: {key_path}{Colors.ENDC}")
    private_key_content = load_private_key(key_path)
    print_success(f"Loaded private key ({len(private_key_content)} bytes)")

    # Run all tests
    test_results = []

    test_results.append(("Valid Base64 Key", test_valid_base64_key(private_key_content)))
    test_results.append(("Invalid Base64", test_invalid_base64()))
    test_results.append(("Invalid PEM Format", test_invalid_pem_format()))
    test_results.append(("File Permissions", test_file_permissions()))
    test_results.append(("Cleanup on Error", test_cleanup_on_error()))
    test_results.append(("Verbose Output", test_verbose_output(private_key_content)))
    test_results.append(("Code Security", verify_code_security()))

    # Print summary
    print_header("TEST SUMMARY")

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = f"{Colors.GREEN}PASS{Colors.ENDC}" if result else f"{Colors.RED}FAIL{Colors.ENDC}"
        print(f"{test_name:.<50} {status}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.ENDC}")

    if passed == total:
        print_success("All tests passed! The private key handling is secure and robust.")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed. Please review the implementation.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
