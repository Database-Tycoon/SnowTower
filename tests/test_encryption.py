#!/usr/bin/env python3
"""
Comprehensive Test Suite for FernetEncryption Module

Tests encryption, decryption, key management, key rotation, and error handling.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from user_management.encryption import (
    FernetEncryption,
    FernetEncryptionError,
    FernetKeyMissingError,
    InvalidEncryptedDataError,
)


class TestFernetEncryptionInitialization:
    """Test FernetEncryption initialization and key management"""

    def test_init_with_provided_key(self):
        """Test initialization with provided key"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        assert encryption.key == key
        assert encryption._fernet is not None

    def test_init_without_key_loads_from_env(self, monkeypatch):
        """Test initialization loads key from environment"""
        key = Fernet.generate_key().decode("utf-8")
        monkeypatch.setenv("SNOWFLAKE_CONFIG_FERNET_KEYS", key)

        encryption = FernetEncryption()

        assert encryption.key == key
        assert encryption._fernet is not None

    def test_init_without_key_no_env(self, monkeypatch):
        """Test initialization without key or environment variable"""
        monkeypatch.delenv("SNOWFLAKE_CONFIG_FERNET_KEYS", raising=False)

        encryption = FernetEncryption()

        assert encryption.key is None
        assert encryption._fernet is None

    def test_init_with_invalid_key(self):
        """Test initialization with invalid key raises error"""
        with pytest.raises(FernetEncryptionError, match="Invalid Fernet key"):
            FernetEncryption(key="invalid_key_format")


class TestPasswordEncryption:
    """Test password encryption functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.key = Fernet.generate_key().decode("utf-8")
        self.encryption = FernetEncryption(key=self.key)

    def test_encrypt_password_success(self):
        """Test successful password encryption"""
        password = "TestPassword123!"
        encrypted = self.encryption.encrypt_password(password)

        assert encrypted is not None
        assert encrypted != password
        assert isinstance(encrypted, str)

    def test_encrypt_password_without_fernet_key(self):
        """Test encryption fails without Fernet key"""
        encryption = FernetEncryption()  # No key

        with pytest.raises(FernetKeyMissingError, match="No Fernet key available"):
            encryption.encrypt_password("password")

    def test_encrypt_password_with_special_characters(self):
        """Test encryption with special characters"""
        password = "P@ssw0rd!#$%^&*()"
        encrypted = self.encryption.encrypt_password(password)

        assert encrypted is not None
        assert encrypted != password

    def test_encrypt_password_with_unicode(self):
        """Test encryption with unicode characters"""
        password = "Pässwörd123!你好"
        encrypted = self.encryption.encrypt_password(password)

        assert encrypted is not None
        assert encrypted != password

    def test_encrypt_empty_password(self):
        """Test encryption of empty password"""
        encrypted = self.encryption.encrypt_password("")
        assert encrypted is not None


class TestPasswordDecryption:
    """Test password decryption functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.key = Fernet.generate_key().decode("utf-8")
        self.encryption = FernetEncryption(key=self.key)

    def test_decrypt_password_success(self):
        """Test successful password decryption"""
        password = "TestPassword123!"
        encrypted = self.encryption.encrypt_password(password)
        decrypted = self.encryption.decrypt_password(encrypted)

        assert decrypted == password

    def test_decrypt_password_without_fernet_key(self):
        """Test decryption fails without Fernet key"""
        encryption_no_key = FernetEncryption()  # No key

        with pytest.raises(FernetKeyMissingError, match="No Fernet key available"):
            encryption_no_key.decrypt_password("some_encrypted_data")

    def test_decrypt_password_with_wrong_key(self):
        """Test decryption with wrong key fails"""
        password = "TestPassword123!"
        encrypted = self.encryption.encrypt_password(password)

        # Create new encryption with different key
        wrong_key = Fernet.generate_key().decode("utf-8")
        wrong_encryption = FernetEncryption(key=wrong_key)

        with pytest.raises(
            InvalidEncryptedDataError, match="Invalid encrypted password"
        ):
            wrong_encryption.decrypt_password(encrypted)

    def test_decrypt_invalid_data(self):
        """Test decryption of invalid data"""
        with pytest.raises(
            InvalidEncryptedDataError, match="Invalid encrypted password"
        ):
            self.encryption.decrypt_password("not_encrypted_data")

    def test_decrypt_corrupted_data(self):
        """Test decryption of corrupted data"""
        password = "TestPassword123!"
        encrypted = self.encryption.encrypt_password(password)

        # Corrupt the encrypted data
        corrupted = encrypted[:-5] + "xxxxx"

        with pytest.raises(InvalidEncryptedDataError):
            self.encryption.decrypt_password(corrupted)


class TestEncryptionValidation:
    """Test encryption validation functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.key = Fernet.generate_key().decode("utf-8")
        self.encryption = FernetEncryption(key=self.key)

    def test_validate_encryption_success(self):
        """Test validation of valid encrypted password"""
        password = "TestPassword123!"
        encrypted = self.encryption.encrypt_password(password)

        is_valid = self.encryption.validate_encryption(encrypted)
        assert is_valid is True

    def test_validate_encryption_failure_invalid_data(self):
        """Test validation fails for invalid data"""
        is_valid = self.encryption.validate_encryption("invalid_data")
        assert is_valid is False

    def test_validate_encryption_failure_no_key(self):
        """Test validation fails without key"""
        encryption_no_key = FernetEncryption()
        is_valid = encryption_no_key.validate_encryption("some_data")
        assert is_valid is False


class TestKeyGeneration:
    """Test Fernet key generation"""

    def test_generate_key_creates_valid_key(self):
        """Test that generated key is valid"""
        key = FernetEncryption.generate_key()

        assert key is not None
        assert isinstance(key, str)
        assert len(key) == 44  # Base64 encoded Fernet key length

    def test_generate_key_creates_unique_keys(self):
        """Test that multiple key generations create unique keys"""
        key1 = FernetEncryption.generate_key()
        key2 = FernetEncryption.generate_key()
        key3 = FernetEncryption.generate_key()

        assert key1 != key2
        assert key2 != key3
        assert key1 != key3

    def test_generated_key_works_for_encryption(self):
        """Test that generated key works for encryption/decryption"""
        key = FernetEncryption.generate_key()
        encryption = FernetEncryption(key=key)

        password = "TestPassword123!"
        encrypted = encryption.encrypt_password(password)
        decrypted = encryption.decrypt_password(encrypted)

        assert decrypted == password


class TestKeyRotation:
    """Test key rotation functionality"""

    def test_rotate_keys_success(self):
        """Test successful key rotation"""
        old_key = Fernet.generate_key().decode("utf-8")
        new_key = Fernet.generate_key().decode("utf-8")

        old_encryption = FernetEncryption(key=old_key)

        # Encrypt passwords with old key
        passwords = {
            "user1": old_encryption.encrypt_password("password1"),
            "user2": old_encryption.encrypt_password("password2"),
            "user3": old_encryption.encrypt_password("password3"),
        }

        # Rotate keys
        rotated = old_encryption.rotate_keys(old_key, new_key, passwords)

        assert len(rotated) == 3
        assert "user1" in rotated
        assert "user2" in rotated
        assert "user3" in rotated

        # Verify passwords can be decrypted with new key
        new_encryption = FernetEncryption(key=new_key)
        assert new_encryption.decrypt_password(rotated["user1"]) == "password1"
        assert new_encryption.decrypt_password(rotated["user2"]) == "password2"
        assert new_encryption.decrypt_password(rotated["user3"]) == "password3"

    def test_rotate_keys_with_invalid_old_key(self):
        """Test key rotation fails with invalid old key"""
        old_key = Fernet.generate_key().decode("utf-8")
        new_key = Fernet.generate_key().decode("utf-8")
        wrong_old_key = Fernet.generate_key().decode("utf-8")

        encryption = FernetEncryption(key=old_key)

        passwords = {"user1": encryption.encrypt_password("password1")}

        with pytest.raises(FernetEncryptionError, match="Key rotation failed"):
            encryption.rotate_keys(wrong_old_key, new_key, passwords)

    def test_rotate_keys_empty_passwords(self):
        """Test key rotation with empty password dictionary"""
        old_key = Fernet.generate_key().decode("utf-8")
        new_key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=old_key)

        rotated = encryption.rotate_keys(old_key, new_key, {})

        assert rotated == {}


class TestKeyInfo:
    """Test key information export"""

    def test_export_key_info_with_key(self):
        """Test key info export with key present"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        info = encryption.export_key_info()

        assert info["has_key"] is True
        assert "algorithm" in info
        assert info["algorithm"] == "Fernet (AES-128 in CBC mode with HMAC-SHA256)"
        assert info["key_length"] == 44

    def test_export_key_info_without_key(self):
        """Test key info export without key"""
        encryption = FernetEncryption()

        info = encryption.export_key_info()

        assert info["has_key"] is False
        assert info["key_length"] == 0

    def test_export_key_info_from_environment(self, monkeypatch):
        """Test key info shows environment as source"""
        key = Fernet.generate_key().decode("utf-8")
        monkeypatch.setenv("SNOWFLAKE_CONFIG_FERNET_KEYS", key)

        encryption = FernetEncryption()
        info = encryption.export_key_info()

        assert info["has_key"] is True
        assert info["key_source"] == "environment"


class TestInteractiveEncrypt:
    """Test interactive encryption functionality"""

    def test_interactive_encrypt_no_key(self):
        """Test interactive encryption fails without key"""
        encryption = FernetEncryption()

        with pytest.raises(FernetKeyMissingError, match="No Fernet key available"):
            encryption.interactive_encrypt()

    @patch("user_management.encryption.Prompt.ask")
    @patch("user_management.encryption.Confirm.ask")
    def test_interactive_encrypt_success(self, mock_confirm, mock_prompt):
        """Test successful interactive encryption"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        # Mock user input
        mock_prompt.side_effect = ["TestPassword123!", "TestPassword123!"]
        mock_confirm.return_value = False  # Don't verify

        result = encryption.interactive_encrypt()

        assert result is not None
        assert result != ""
        assert encryption.validate_encryption(result)

    @patch("user_management.encryption.Prompt.ask")
    def test_interactive_encrypt_empty_password(self, mock_prompt):
        """Test interactive encryption with empty password"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        # Mock empty password
        mock_prompt.return_value = ""

        result = encryption.interactive_encrypt()
        assert result == ""

    @patch("user_management.encryption.Prompt.ask")
    def test_interactive_encrypt_password_mismatch(self, mock_prompt):
        """Test interactive encryption with mismatched passwords"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        # Mock mismatched passwords
        mock_prompt.side_effect = ["Password1", "Password2"]

        result = encryption.interactive_encrypt()
        assert result == ""

    @patch("user_management.encryption.Prompt.ask")
    @patch("user_management.encryption.Confirm.ask")
    def test_interactive_encrypt_with_verification(self, mock_confirm, mock_prompt):
        """Test interactive encryption with verification"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        # Mock user input with verification
        mock_prompt.side_effect = ["TestPassword123!", "TestPassword123!"]
        mock_confirm.return_value = True  # Verify

        result = encryption.interactive_encrypt()

        assert result is not None
        assert result != ""

        # Verify decryption works
        decrypted = encryption.decrypt_password(result)
        assert decrypted == "TestPassword123!"


class TestEncryptionEdgeCases:
    """Test edge cases and error scenarios"""

    def test_encrypt_very_long_password(self):
        """Test encryption of very long password"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        password = "A" * 10000  # 10k character password
        encrypted = encryption.encrypt_password(password)
        decrypted = encryption.decrypt_password(encrypted)

        assert decrypted == password

    def test_multiple_encrypt_same_password_different_output(self):
        """Test that encrypting same password twice produces different output"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        password = "TestPassword123!"
        encrypted1 = encryption.encrypt_password(password)
        encrypted2 = encryption.encrypt_password(password)

        # Encrypted values should be different (due to IV/timestamp)
        assert encrypted1 != encrypted2

        # But both should decrypt to same password
        assert encryption.decrypt_password(encrypted1) == password
        assert encryption.decrypt_password(encrypted2) == password

    def test_encryption_roundtrip_multiple_times(self):
        """Test multiple encryption/decryption cycles"""
        key = Fernet.generate_key().decode("utf-8")
        encryption = FernetEncryption(key=key)

        password = "TestPassword123!"

        for _ in range(10):
            encrypted = encryption.encrypt_password(password)
            decrypted = encryption.decrypt_password(encrypted)
            assert decrypted == password


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
