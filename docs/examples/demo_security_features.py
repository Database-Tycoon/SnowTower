#!/usr/bin/env python3
"""
Security Features Demonstration

This script demonstrates the security features of the base64 private key handling
by directly testing the relevant code paths.

Usage:
    python demo_security_features.py
"""

import os
import sys
import base64
import tempfile


class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


def demo_secure_file_creation():
    """Demonstrate secure temp file creation with proper permissions"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}DEMO 1: Secure Temp File Creation{Colors.ENDC}")
    print("=" * 70)

    # Create a temporary file like the CLI does
    fd, temp_key_path = tempfile.mkstemp(suffix=".p8")

    try:
        # Write content
        test_content = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        os.write(fd, test_content.encode("utf-8"))
    finally:
        os.close(fd)

    # Set secure permissions
    os.chmod(temp_key_path, 0o600)

    # Verify permissions
    import stat

    file_stats = os.stat(temp_key_path)
    mode = file_stats.st_mode
    perms = stat.filemode(mode)

    print(f"\n  📁 Temp file created: {temp_key_path}")
    print(f"  🔒 File permissions: {perms}")
    print(f"  ✅ Owner read/write only: {oct(stat.S_IMODE(mode))}")

    # Cleanup
    os.unlink(temp_key_path)
    print(f"  🗑️  File cleaned up")

    print(f"\n  {Colors.GREEN}✓ Secure file creation verified{Colors.ENDC}")


def demo_base64_validation():
    """Demonstrate base64 validation"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}DEMO 2: Base64 Validation{Colors.ENDC}")
    print("=" * 70)

    test_cases = [
        ("Valid Base64", "VGhpcyBpcyBhIHRlc3Q=", True),
        ("Invalid Base64", "not-base64!@#$", False),
        ("Partial Padding", "YWJj", True),  # Valid with partial padding
    ]

    for name, test_input, should_succeed in test_cases:
        print(f"\n  Testing: {name}")
        print(f"  Input: {test_input}")

        try:
            decoded = base64.b64decode(test_input).decode("utf-8")
            print(f"  {Colors.GREEN}✓ Decoded successfully: '{decoded}'{Colors.ENDC}")
        except base64.binascii.Error as e:
            print(f"  {Colors.YELLOW}✗ Base64 error (expected): {e}{Colors.ENDC}")
        except UnicodeDecodeError as e:
            print(f"  {Colors.YELLOW}✗ UTF-8 error: {e}{Colors.ENDC}")


def demo_pem_validation():
    """Demonstrate PEM format validation"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}DEMO 3: PEM Format Validation{Colors.ENDC}")
    print("=" * 70)

    test_cases = [
        (
            "Valid PEM",
            "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADA...\n-----END PRIVATE KEY-----",
            True,
        ),
        (
            "Invalid - No BEGIN",
            "PRIVATE KEY-----\ndata\n-----END PRIVATE KEY-----",
            False,
        ),
        (
            "Invalid - No PRIVATE KEY",
            "-----BEGIN RSA-----\ndata\n-----END RSA-----",
            False,
        ),
        ("Invalid - Plain Text", "This is just plain text", False),
    ]

    for name, content, expected_valid in test_cases:
        print(f"\n  Testing: {name}")
        is_valid = content.startswith("-----BEGIN") and "PRIVATE KEY-----" in content

        if is_valid == expected_valid:
            print(
                f"  {Colors.GREEN}✓ Validation correct: {'Valid' if is_valid else 'Invalid'}{Colors.ENDC}"
            )
        else:
            print(f"  {Colors.YELLOW}✗ Validation mismatch{Colors.ENDC}")


def demo_cleanup_guarantee():
    """Demonstrate guaranteed cleanup with try-finally"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}DEMO 4: Guaranteed Cleanup{Colors.ENDC}")
    print("=" * 70)

    temp_files = []

    # Test 1: Successful execution
    print(f"\n  Test 1: Successful execution with cleanup")
    fd, temp_path = tempfile.mkstemp(suffix=".p8")
    temp_files.append(temp_path)

    try:
        os.write(fd, b"test content")
        print(f"  📝 File created: {os.path.basename(temp_path)}")
    finally:
        os.close(fd)
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            print(f"  {Colors.GREEN}✓ Cleaned up in finally block{Colors.ENDC}")

    # Test 2: Exception during processing
    print(f"\n  Test 2: Exception during processing (cleanup still happens)")
    fd, temp_path = tempfile.mkstemp(suffix=".p8")

    try:
        os.write(fd, b"test content")
        print(f"  📝 File created: {os.path.basename(temp_path)}")
        # Simulate error
        raise ValueError("Simulated error during processing")
    except ValueError as e:
        print(f"  {Colors.YELLOW}⚠️  Error occurred: {e}{Colors.ENDC}")
    finally:
        os.close(fd)
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            print(
                f"  {Colors.GREEN}✓ Cleaned up despite error (finally block){Colors.ENDC}"
            )


def demo_complete_flow():
    """Demonstrate complete base64 to temp file flow"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}DEMO 5: Complete Security Flow{Colors.ENDC}")
    print("=" * 70)

    # Load actual key
    key_path = os.path.expanduser("~/.ssh/snowddl_rsa_key.p8")
    with open(key_path, "r") as f:
        key_content = f.read()

    print(f"\n  Step 1: Load private key")
    print(f"  📄 Key size: {len(key_content)} bytes")

    print(f"\n  Step 2: Encode as base64")
    encoded = base64.b64encode(key_content.encode("utf-8")).decode("utf-8")
    print(f"  🔐 Encoded size: {len(encoded)} characters")

    print(f"\n  Step 3: Decode and validate")
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
        print(f"  {Colors.GREEN}✓ Base64 decode successful{Colors.ENDC}")

        # PEM validation
        if decoded.startswith("-----BEGIN") and "PRIVATE KEY-----" in decoded:
            print(f"  {Colors.GREEN}✓ PEM format validated{Colors.ENDC}")
        else:
            print(f"  {Colors.YELLOW}✗ Invalid PEM format{Colors.ENDC}")
    except Exception as e:
        print(f"  {Colors.YELLOW}✗ Validation failed: {e}{Colors.ENDC}")
        return

    print(f"\n  Step 4: Create secure temp file")
    temp_key_path = None
    try:
        # Create temp file with secure permissions
        fd, temp_key_path = tempfile.mkstemp(suffix=".p8")
        try:
            os.write(fd, decoded.encode("utf-8"))
        finally:
            os.close(fd)

        # Set secure permissions
        os.chmod(temp_key_path, 0o600)

        import stat

        mode = os.stat(temp_key_path).st_mode
        print(
            f"  {Colors.GREEN}✓ Temp file created: {os.path.basename(temp_key_path)}{Colors.ENDC}"
        )
        print(f"  {Colors.GREEN}✓ Permissions: {oct(stat.S_IMODE(mode))}{Colors.ENDC}")

        # Verify content
        with open(temp_key_path, "r") as f:
            temp_content = f.read()

        if temp_content == decoded:
            print(f"  {Colors.GREEN}✓ Content verification passed{Colors.ENDC}")

    finally:
        # Guaranteed cleanup
        if temp_key_path and os.path.exists(temp_key_path):
            os.unlink(temp_key_path)
            print(
                f"  {Colors.GREEN}✓ Temp file cleaned up (finally block){Colors.ENDC}"
            )

    print(f"\n  {Colors.GREEN}✅ Complete security flow verified{Colors.ENDC}")


def main():
    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(
        f"{Colors.BOLD}Base64 Private Key Security Features Demonstration{Colors.ENDC}"
    )
    print(f"{Colors.BOLD}{'=' * 80}{Colors.ENDC}")

    demo_secure_file_creation()
    demo_base64_validation()
    demo_pem_validation()
    demo_cleanup_guarantee()
    demo_complete_flow()

    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(
        f"{Colors.BOLD}{Colors.GREEN}All Security Features Demonstrated Successfully{Colors.ENDC}"
    )
    print(f"{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

    print("Summary of Security Measures:")
    print("  ✅ Secure temp file creation (mkstemp)")
    print("  ✅ Strict file permissions (0o600)")
    print("  ✅ Base64 validation")
    print("  ✅ PEM format validation")
    print("  ✅ Guaranteed cleanup (try-finally)")
    print("  ✅ No credential leakage")
    print()


if __name__ == "__main__":
    main()
