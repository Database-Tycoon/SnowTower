#!/usr/bin/env python3
"""
Test Suite for Automatic Password Generation

Tests the password generation functionality including:
- PasswordGenerator class
- Integration with UserManager
- CLI commands
- Encryption validation
- Security requirements
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from user_management.password_generator import (
    PasswordGenerator,
    PasswordGenerationError,
)
from user_management.encryption import FernetEncryption
from user_management.manager import UserManager


class TestPasswordGenerator:
    """Test the PasswordGenerator class"""

    def setup_method(self):
        """Set up test environment"""
        # Mock Fernet encryption for testing
        self.mock_encryption = MagicMock()
        self.mock_encryption.encrypt_password.return_value = "mock_encrypted_password"
        self.mock_encryption.validate_encryption.return_value = True

        self.generator = PasswordGenerator(self.mock_encryption)

    def test_generate_secure_password_default(self):
        """Test default password generation"""
        password = self.generator.generate_secure_password()

        assert len(password) == 16
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*" for c in password)

    def test_generate_secure_password_custom_length(self):
        """Test password generation with custom length"""
        password = self.generator.generate_secure_password(length=20)
        assert len(password) == 20

    def test_generate_secure_password_minimum_length(self):
        """Test password generation fails with too short length"""
        with pytest.raises(PasswordGenerationError):
            self.generator.generate_secure_password(length=8)

    def test_generate_secure_password_no_symbols(self):
        """Test password generation without symbols"""
        password = self.generator.generate_secure_password(include_symbols=False)
        assert not any(c in "!@#$%^&*" for c in password)

    def test_generate_secure_password_exclude_ambiguous(self):
        """Test password generation excluding ambiguous characters"""
        password = self.generator.generate_secure_password(exclude_ambiguous=True)
        ambiguous_chars = "0O1lI"
        assert not any(c in ambiguous_chars for c in password)

    def test_generate_encrypted_password(self):
        """Test encrypted password generation"""
        plain, encrypted = self.generator.generate_encrypted_password()

        assert len(plain) == 16
        assert encrypted == "mock_encrypted_password"
        self.mock_encryption.encrypt_password.assert_called_once_with(plain)

    def test_generate_user_password(self):
        """Test complete user password generation"""
        result = self.generator.generate_user_password("TEST_USER", "PERSON", 16)

        assert result["username"] == "TEST_USER"
        assert result["user_type"] == "PERSON"
        assert result["length"] == 16
        assert "plain_password" in result
        assert "encrypted_password" in result
        assert "yaml_value" in result
        assert result["yaml_value"].startswith("!decrypt ")
        assert result["encryption_valid"] is True

    def test_generate_multiple_passwords(self):
        """Test bulk password generation"""
        usernames = ["USER1", "USER2", "USER3"]
        results = self.generator.generate_multiple_passwords(usernames)

        assert len(results) == 3
        for username in usernames:
            assert username in results
            assert results[username]["username"] == username

    def test_validate_password_strength(self):
        """Test password strength validation"""
        # Strong password
        strong = self.generator.validate_password_strength("StrongP@ssw0rd123")
        assert strong["is_strong"] is True
        assert strong["strength_level"] == "Strong"

        # Weak password
        weak = self.generator.validate_password_strength("weak")
        assert weak["is_strong"] is False
        assert weak["strength_level"] == "Weak"


class TestUserManagerIntegration:
    """Test password generation integration with UserManager"""

    def setup_method(self):
        """Set up test environment"""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "snowddl"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Mock components
        with patch("user_management.manager.FernetEncryption") as mock_fernet, patch(
            "user_management.manager.RSAKeyManager"
        ) as mock_rsa, patch("user_management.manager.YAMLHandler") as mock_yaml, patch(
            "user_management.manager.SnowDDLAccountManager"
        ) as mock_snowddl:
            mock_fernet.return_value = MagicMock()
            mock_rsa.return_value = MagicMock()
            mock_yaml.return_value = MagicMock()
            mock_snowddl.return_value = MagicMock()

            self.manager = UserManager(self.config_dir)

    def test_generate_password_method(self):
        """Test UserManager generate_password method"""
        with patch.object(
            self.manager.password_generator, "generate_user_password"
        ) as mock_gen:
            mock_gen.return_value = {
                "username": "TEST_USER",
                "plain_password": "test123",
                "yaml_value": "!decrypt encrypted",
            }

            result = self.manager.generate_password("TEST_USER", "PERSON", 16)

            assert result["username"] == "TEST_USER"
            mock_gen.assert_called_once_with(
                username="TEST_USER", user_type="PERSON", length=16
            )

    def test_regenerate_user_password_method(self):
        """Test UserManager regenerate_user_password method"""
        # Mock existing user
        self.manager.yaml_handler.get_user.return_value = {"type": "PERSON"}
        self.manager.update_user = MagicMock(return_value=True)

        with patch.object(self.manager, "generate_password") as mock_gen:
            mock_gen.return_value = {
                "plain_password": "newpass123",
                "yaml_value": "!decrypt newencrypted",
            }

            result = self.manager.regenerate_user_password("TEST_USER", 16)

            assert result is True
            mock_gen.assert_called_once()
            self.manager.update_user.assert_called_once()


class TestCLIIntegration:
    """Test CLI command integration"""

    def test_cli_generate_password_import(self):
        """Test that CLI commands can be imported without errors"""
        try:
            from user_management.cli import (
                generate_password,
                regenerate_password,
                bulk_generate_passwords,
            )

            assert callable(generate_password)
            assert callable(regenerate_password)
            assert callable(bulk_generate_passwords)
        except ImportError as e:
            pytest.fail(f"Failed to import CLI commands: {e}")


class TestSecurityRequirements:
    """Test security requirements compliance"""

    def setup_method(self):
        """Set up test environment"""
        self.mock_encryption = MagicMock()
        self.mock_encryption.encrypt_password.return_value = "mock_encrypted"
        self.generator = PasswordGenerator(self.mock_encryption)

    def test_password_complexity_requirements(self):
        """Test that generated passwords meet complexity requirements"""
        for _ in range(10):  # Test multiple generations
            password = self.generator.generate_secure_password()

            # Length requirement
            assert len(password) >= 16

            # Character type requirements
            assert any(c.islower() for c in password), "Must contain lowercase"
            assert any(c.isupper() for c in password), "Must contain uppercase"
            assert any(c.isdigit() for c in password), "Must contain digits"
            assert any(c in "!@#$%^&*" for c in password), "Must contain symbols"

    def test_password_randomness(self):
        """Test that passwords are random (not predictable)"""
        passwords = [self.generator.generate_secure_password() for _ in range(10)]

        # All passwords should be different
        assert len(set(passwords)) == 10, "Passwords should be unique"

    def test_yaml_format_security(self):
        """Test that YAML output is properly formatted for security"""
        result = self.generator.generate_user_password("TEST_USER")

        # Should use !decrypt prefix
        assert result["yaml_value"].startswith("!decrypt ")

        # Should not contain plain password in YAML value
        assert result["plain_password"] not in result["yaml_value"]


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_missing_fernet_key(self):
        """Test behavior when Fernet key is missing"""
        # Create a mock encryption that raises an error on encrypt_password
        mock_encryption = MagicMock()
        mock_encryption.encrypt_password.side_effect = Exception(
            "No encryption key available"
        )

        generator = PasswordGenerator(encryption=mock_encryption)

        with pytest.raises(PasswordGenerationError):
            generator.generate_encrypted_password()

    def test_invalid_parameters(self):
        """Test invalid parameter handling"""
        generator = PasswordGenerator(MagicMock())

        # Invalid length
        with pytest.raises(PasswordGenerationError):
            generator.generate_secure_password(length=5)

        # No character types selected
        with pytest.raises(PasswordGenerationError):
            generator.generate_secure_password(
                include_lowercase=False,
                include_uppercase=False,
                include_digits=False,
                include_symbols=False,
            )


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])
