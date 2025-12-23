#!/usr/bin/env python3
"""
CI/CD Simulation Test for Base64 Private Key Handling

This test simulates GitHub Actions environment by:
1. NOT loading .env file (no SNOWFLAKE_PRIVATE_KEY_PATH)
2. Setting SNOWFLAKE_PRIVATE_KEY directly
3. Running snowddl CLI directly (not via uv run which loads .env)

Usage:
    python test_cicd_simulation.py
"""

import os
import sys
import base64
import subprocess
import tempfile
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'


def print_test(message: str):
    print(f"{Colors.CYAN}🧪 {message}{Colors.ENDC}")


def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")


def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")


def run_cli_directly(env_vars: dict) -> tuple:
    """Run CLI directly using Python to simulate CI/CD (no .env loading)"""
    # Create isolated environment without .env
    test_env = {
        'SNOWFLAKE_ACCOUNT': os.environ.get('SNOWFLAKE_ACCOUNT', 'YOUR_ACCOUNT'),
        'SNOWFLAKE_USER': os.environ.get('SNOWFLAKE_USER', 'SNOWDDL'),
        'SNOWFLAKE_ROLE': os.environ.get('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        'SNOWFLAKE_WAREHOUSE': os.environ.get('SNOWFLAKE_WAREHOUSE', 'MAIN_WAREHOUSE'),
        'PATH': os.environ['PATH'],
        'HOME': os.environ['HOME'],
    }

    # Add test-specific variables
    test_env.update(env_vars)

    # Explicitly DO NOT include SNOWFLAKE_PRIVATE_KEY_PATH
    if 'SNOWFLAKE_PRIVATE_KEY_PATH' in test_env:
        del test_env['SNOWFLAKE_PRIVATE_KEY_PATH']

    # Run the plan command directly
    result = subprocess.run(
        ['python', '-c', '''
import sys
sys.path.insert(0, "/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl/src")
from snowtower_snowddl.cli import plan
plan()
'''],
        capture_output=True,
        text=True,
        env=test_env,
        cwd='/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl'
    )

    return result.returncode, result.stdout, result.stderr


def test_invalid_base64():
    """Test 1: Invalid base64 encoding"""
    print(f"\n{Colors.BOLD}TEST 1: Invalid Base64 Encoding (CI/CD Simulation){Colors.ENDC}")
    print_test("Setting SNOWFLAKE_PRIVATE_KEY with invalid base64...")

    env_vars = {
        'SNOWFLAKE_PRIVATE_KEY': 'invalid_base64!@#$%^&*()'
    }

    returncode, stdout, stderr = run_cli_directly(env_vars)
    output = stdout + stderr

    if "Detected private key in environment variable" in output:
        print_success("Private key detection triggered")

        if "Invalid base64-encoded private key" in output:
            print_success("PASS: Correctly detected invalid base64 encoding")
            return True
        else:
            print_error("FAIL: Should have shown base64 error message")
            print(f"Output:\n{output[:500]}")
            return False
    else:
        print_error("FAIL: Private key detection not triggered")
        print(f"Output:\n{output[:500]}")
        return False


def test_invalid_pem():
    """Test 2: Valid base64 but invalid PEM format"""
    print(f"\n{Colors.BOLD}TEST 2: Valid Base64, Invalid PEM (CI/CD Simulation){Colors.ENDC}")
    print_test("Setting SNOWFLAKE_PRIVATE_KEY with non-PEM content...")

    invalid_content = "This is not a PEM key"
    encoded = base64.b64encode(invalid_content.encode('utf-8')).decode('utf-8')

    env_vars = {
        'SNOWFLAKE_PRIVATE_KEY': encoded
    }

    returncode, stdout, stderr = run_cli_directly(env_vars)
    output = stdout + stderr

    if "Detected private key in environment variable" in output:
        print_success("Private key detection triggered")

        if "not a valid PEM private key" in output:
            print_success("PASS: Correctly detected invalid PEM format")
            return True
        else:
            print_error("FAIL: Should have shown PEM validation error")
            print(f"Output:\n{output[:500]}")
            return False
    else:
        print_error("FAIL: Private key detection not triggered")
        print(f"Output:\n{output[:500]}")
        return False


def test_valid_base64():
    """Test 3: Valid base64-encoded private key"""
    print(f"\n{Colors.BOLD}TEST 3: Valid Base64-Encoded Key (CI/CD Simulation){Colors.ENDC}")
    print_test("Loading actual private key and encoding...")

    key_path = os.path.expanduser('~/.ssh/snowddl_rsa_key.p8')
    with open(key_path, 'r') as f:
        key_content = f.read()

    encoded = base64.b64encode(key_content.encode('utf-8')).decode('utf-8')
    print_success(f"Encoded key ({len(encoded)} chars)")

    env_vars = {
        'SNOWFLAKE_PRIVATE_KEY': encoded
    }

    returncode, stdout, stderr = run_cli_directly(env_vars)
    output = stdout + stderr

    if "Detected private key in environment variable" in output:
        print_success("Private key detection triggered")

        if returncode == 0:
            print_success("PASS: Plan executed successfully with base64 key")
            return True
        else:
            print_error(f"FAIL: Plan failed with return code {returncode}")
            print(f"Output:\n{output[:500]}")
            return False
    else:
        print_error("FAIL: Private key detection not triggered")
        print(f"Output:\n{output[:500]}")
        return False


def main():
    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}CI/CD Simulation - Base64 Private Key Error Handling Tests{Colors.ENDC}")
    print(f"{Colors.BOLD}{'=' * 80}{Colors.ENDC}")

    print(f"\n{Colors.YELLOW}NOTE: This test simulates GitHub Actions by:{Colors.ENDC}")
    print(f"{Colors.YELLOW}- Not loading .env file{Colors.ENDC}")
    print(f"{Colors.YELLOW}- Running CLI directly with isolated environment{Colors.ENDC}")
    print(f"{Colors.YELLOW}- SNOWFLAKE_PRIVATE_KEY_PATH explicitly NOT set{Colors.ENDC}")

    results = []
    results.append(("Invalid Base64", test_invalid_base64()))
    results.append(("Invalid PEM Format", test_invalid_pem()))
    results.append(("Valid Base64 Key", test_valid_base64()))

    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}TEST SUMMARY{Colors.ENDC}")
    print(f"{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.ENDC}" if result else f"{Colors.RED}FAIL{Colors.ENDC}"
        print(f"{test_name:.<50} {status}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.ENDC}\n")

    if passed == total:
        print_success("All CI/CD simulation tests passed!")
        print_success("Base64 error handling works correctly in GitHub Actions environment")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
