"""Integration tests for authentication methods.

Tests RSA key operations, Fernet encryption roundtrips, and YAML password handling.
"""

import os
import subprocess
import tempfile
import pytest
import yaml
from pathlib import Path
from cryptography.fernet import Fernet

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from user_management.encryption import FernetEncryption
from user_management.yaml_handler import YAMLHandler


class TestRSAKeyGeneration:
    """Test RSA key pair generation and validation."""

    def test_generate_rsa_key_pair(self):
        """Generate an RSA key pair using openssl and verify format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            private_key = Path(tmpdir) / "test_key.p8"
            public_key = Path(tmpdir) / "test_key.pub"

            # Generate private key
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f"openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out {private_key}",
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Key generation failed: {result.stderr}"

            # Generate public key from private
            result = subprocess.run(
                [
                    "openssl",
                    "rsa",
                    "-in",
                    str(private_key),
                    "-pubout",
                    "-out",
                    str(public_key),
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

            # Verify files exist and have content
            assert private_key.exists()
            assert public_key.exists()

            pub_content = public_key.read_text()
            assert "BEGIN PUBLIC KEY" in pub_content
            assert "END PUBLIC KEY" in pub_content

    def test_rsa_public_key_in_yaml_format(self):
        """Verify RSA public key can be stored in YAML user config format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            private_key = Path(tmpdir) / "test_key.p8"
            public_key = Path(tmpdir) / "test_key.pub"

            subprocess.run(
                [
                    "bash",
                    "-c",
                    f"openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out {private_key}",
                ],
                capture_output=True,
            )
            subprocess.run(
                ["openssl", "rsa", "-in", str(private_key), "-pubout", "-out", str(public_key)],
                capture_output=True,
            )

            pub_content = public_key.read_text()
            # Strip headers for SnowDDL format
            lines = pub_content.strip().split("\n")
            key_body = "\n".join(lines[1:-1])

            user_config = {
                "TEST_SERVICE": {
                    "type": "SERVICE",
                    "rsa_public_key": key_body,
                    "default_role": "TEST_ROLE",
                }
            }

            yaml_output = yaml.dump(user_config, default_flow_style=False)
            reloaded = yaml.safe_load(yaml_output)

            assert reloaded["TEST_SERVICE"]["rsa_public_key"] == key_body


class TestFernetEncryptionRoundtrip:
    """Test full encryption/decryption lifecycle."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypt a password and decrypt it back."""
        key = Fernet.generate_key().decode("utf-8")
        enc = FernetEncryption(key=key)

        passwords = [
            "SimplePassword123!",
            "P@$$w0rd!#%^&*()",
            "Unicode: Ünîcödé 你好",
            "",
            "A" * 1000,
        ]

        for password in passwords:
            encrypted = enc.encrypt_password(password)
            decrypted = enc.decrypt_password(encrypted)
            assert decrypted == password, f"Roundtrip failed for: {password!r}"

    def test_key_rotation_preserves_passwords(self):
        """Key rotation should re-encrypt without losing data."""
        old_key = Fernet.generate_key().decode("utf-8")
        new_key = Fernet.generate_key().decode("utf-8")

        old_enc = FernetEncryption(key=old_key)
        new_enc = FernetEncryption(key=new_key)

        original_passwords = {
            "user1": "Password1!",
            "user2": "Password2!",
            "user3": "Password3!",
        }

        encrypted = {user: old_enc.encrypt_password(pw) for user, pw in original_passwords.items()}

        rotated = old_enc.rotate_keys(old_key, new_key, encrypted)

        for user, original_pw in original_passwords.items():
            decrypted = new_enc.decrypt_password(rotated[user])
            assert decrypted == original_pw

    def test_wrong_key_fails(self):
        """Decryption with wrong key should fail cleanly."""
        key1 = Fernet.generate_key().decode("utf-8")
        key2 = Fernet.generate_key().decode("utf-8")

        enc1 = FernetEncryption(key=key1)
        enc2 = FernetEncryption(key=key2)

        encrypted = enc1.encrypt_password("Secret123!")

        from user_management.encryption import InvalidEncryptedDataError

        with pytest.raises(InvalidEncryptedDataError):
            enc2.decrypt_password(encrypted)


class TestYAMLPasswordHandling:
    """Test encrypted passwords in YAML config files."""

    def test_user_yaml_with_encrypted_password(self):
        """Users with encrypted passwords should load and save correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            handler = YAMLHandler(config_directory=config_dir)

            users = {
                "ENCRYPTED_USER": {
                    "type": "PERSON",
                    "login_name": "ENCRYPTED_USER",
                    "email": "test@example.com",
                    "password": "!decrypt gAAAAABencryptedplaceholder",
                }
            }

            handler.save_users(users, backup=False)
            loaded = handler.load_users()

            assert "ENCRYPTED_USER" in loaded
            assert "password" in loaded["ENCRYPTED_USER"]

    def test_service_account_no_password(self):
        """Service accounts should work without passwords."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            handler = YAMLHandler(config_directory=config_dir)

            users = {
                "SVC_ACCOUNT": {
                    "type": "SERVICE",
                    "login_name": "SVC_ACCOUNT",
                    "rsa_public_key": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...",
                    "default_role": "SERVICE_ROLE",
                }
            }

            handler.save_users(users, backup=False)
            loaded = handler.load_users()

            assert "SVC_ACCOUNT" in loaded
            assert "password" not in loaded["SVC_ACCOUNT"]
            assert loaded["SVC_ACCOUNT"]["rsa_public_key"].startswith("MIIBIjAN")
