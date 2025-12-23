#!/usr/bin/env python3
"""
Batch RSA Key Generation for Snowflake Users
Generates RSA key pairs for multiple users and outputs public keys for SnowDDL configuration.

Usage:
    uv run python scripts/generate_rsa_keys_batch.py --users GRACE CAROL ESTUARY FABI_AI TOBIKO_CLOUD STEPHEN_RECOVERY
    uv run python scripts/generate_rsa_keys_batch.py --all-non-compliant
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def generate_rsa_key_pair(
    username: str, output_dir: Path, key_size: int = 2048
) -> tuple[Path, Path]:
    """
    Generate RSA key pair for a user.

    Args:
        username: Username for the key pair
        output_dir: Directory to store keys
        key_size: RSA key size (2048 or 4096)

    Returns:
        Tuple of (private_key_path, public_key_path)
    """
    username_lower = username.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    private_key_path = output_dir / f"{username_lower}_rsa_key_{timestamp}.p8"
    public_key_path = output_dir / f"{username_lower}_rsa_key_{timestamp}.pub"

    print(f"\n🔐 Generating {key_size}-bit RSA key pair for {username}...")

    try:
        # Generate private key in PKCS8 format
        genrsa_cmd = ["openssl", "genrsa", str(key_size)]
        genrsa_result = subprocess.run(
            genrsa_cmd, capture_output=True, text=True, check=True
        )

        pkcs8_cmd = ["openssl", "pkcs8", "-topk8", "-inform", "PEM", "-nocrypt"]
        pkcs8_result = subprocess.run(
            pkcs8_cmd,
            input=genrsa_result.stdout,
            capture_output=True,
            text=True,
            check=True,
        )

        # Write private key
        with open(private_key_path, "w") as f:
            f.write(pkcs8_result.stdout)

        # Set secure permissions
        private_key_path.chmod(0o400)

        # Extract public key
        rsa_cmd = ["openssl", "rsa", "-in", str(private_key_path), "-pubout"]
        rsa_result = subprocess.run(rsa_cmd, capture_output=True, text=True, check=True)

        # Write public key
        with open(public_key_path, "w") as f:
            f.write(rsa_result.stdout)

        print(f"✅ Private key: {private_key_path}")
        print(f"✅ Public key: {public_key_path}")

        return private_key_path, public_key_path

    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating keys for {username}: {e}")
        print(f"   stderr: {e.stderr}")
        sys.exit(1)


def extract_public_key_body(public_key_path: Path) -> str:
    """
    Extract the public key content without headers for SnowDDL YAML.

    Args:
        public_key_path: Path to public key file

    Returns:
        Public key content as single-line string
    """
    with open(public_key_path, "r") as f:
        lines = f.readlines()

    # Remove header/footer and newlines
    key_body = "".join([line.strip() for line in lines if not line.startswith("-----")])

    return key_body


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate RSA keys for Snowflake users"
    )
    parser.add_argument(
        "--users", nargs="+", help="List of usernames to generate keys for"
    )
    parser.add_argument(
        "--all-non-compliant",
        action="store_true",
        help="Generate keys for all non-compliant users",
    )
    parser.add_argument(
        "--key-size",
        type=int,
        choices=[2048, 4096],
        default=2048,
        help="RSA key size (default: 2048)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("keys"),
        help="Output directory for keys (default: keys/)",
    )

    args = parser.parse_args()

    # Define non-compliant users based on migration plan
    NON_COMPLIANT_USERS = [
        "GRACE",  # PERSON - no RSA, no password
        "CAROL",  # PERSON - password only
        "ESTUARY",  # SERVICE - no auth configured
        "FABI_AI",  # SERVICE - no auth configured
        "TOBIKO_CLOUD",  # SERVICE - no auth configured
        "STEPHEN_RECOVERY",  # PERSON - emergency account, password only
    ]

    # Determine which users to process
    if args.all_non_compliant:
        users = NON_COMPLIANT_USERS
    elif args.users:
        users = args.users
    else:
        parser.print_help()
        sys.exit(1)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🔑 Snowflake RSA Key Generation - Batch Mode")
    print("=" * 70)
    print(f"📁 Output directory: {args.output_dir}")
    print(f"🔢 Key size: {args.key_size} bits")
    print(f"👥 Users to process: {len(users)}")
    print("=" * 70)

    # Generate keys for each user
    results = {}
    for username in users:
        private_key, public_key = generate_rsa_key_pair(
            username, args.output_dir, args.key_size
        )
        public_key_body = extract_public_key_body(public_key)
        results[username] = {
            "private_key": private_key,
            "public_key": public_key,
            "public_key_body": public_key_body,
        }

    # Output summary and SnowDDL configuration
    print("\n" + "=" * 70)
    print("✅ KEY GENERATION COMPLETE")
    print("=" * 70)

    print("\n📋 SNOWDDL YAML CONFIGURATION")
    print("=" * 70)
    print("\nCopy these public keys to snowddl/user.yaml:\n")

    for username, info in results.items():
        print(f"{username}:")
        print(f"  rsa_public_key: {info['public_key_body']}")
        print()

    print("=" * 70)
    print("\n🔐 PRIVATE KEY DISTRIBUTION")
    print("=" * 70)
    print("\nSecurely distribute these private keys:\n")

    for username, info in results.items():
        print(f"• {username}: {info['private_key']}")

    print("\n⚠️  SECURITY REMINDERS:")
    print(
        "  1. Store private keys in secure locations (1Password, AWS Secrets Manager)"
    )
    print("  2. NEVER commit private keys to Git")
    print("  3. Set permissions to 400: chmod 400 keys/*_rsa_key*.p8")
    print("  4. Share via secure channels only")
    print("  5. Document key distribution in secure audit log")

    print("\n📝 NEXT STEPS:")
    print("  1. Update snowddl/user.yaml with public keys")
    print("  2. Run: uv run snowddl-plan")
    print("  3. Review changes carefully")
    print("  4. Run: uv run snowddl-apply")
    print("  5. Distribute private keys securely")
    print("  6. Test authentication for each user")

    print("\n" + "=" * 70)
    print("✅ Script completed successfully")
    print("=" * 70)


if __name__ == "__main__":
    main()
