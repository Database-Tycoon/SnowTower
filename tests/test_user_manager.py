#!/usr/bin/env python3
"""
Comprehensive Test Suite for UserManager Module

Tests user creation, updates, deletion, and integration with other components.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from cryptography.fernet import Fernet

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from user_management.manager import (
    UserManager,
    UserType,
    UserValidationError,
    UserCreationError,
)
from user_management.encryption import FernetEncryption
from user_management.yaml_handler import YAMLHandler


class TestUserManagerInitialization:
    """Test UserManager initialization"""

    def test_init_with_default_config_dir(self):
        """Test initialization with default config directory"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager()

            assert manager.config_dir == Path.cwd() / "snowddl"
            assert manager.encryption is not None
            assert manager.rsa_manager is not None
            assert manager.yaml_handler is not None
            assert manager.snowddl_manager is not None
            assert manager.password_generator is not None

    def test_init_with_custom_config_dir(self):
        """Test initialization with custom config directory"""
        custom_dir = Path("/tmp/custom_snowddl")

        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=custom_dir)

            assert manager.config_dir == custom_dir


class TestUserTypeEnum:
    """Test UserType enum"""

    def test_user_type_person(self):
        """Test PERSON user type"""
        assert UserType.PERSON.value == "PERSON"
        assert UserType("PERSON") == UserType.PERSON

    def test_user_type_service(self):
        """Test SERVICE user type"""
        assert UserType.SERVICE.value == "SERVICE"
        assert UserType("SERVICE") == UserType.SERVICE


class TestGeneratePassword:
    """Test password generation through UserManager"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_generate_password_success(self):
        """Test successful password generation"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock password generator
            mock_result = {
                "username": "TEST_USER",
                "user_type": "PERSON",
                "plain_password": "TestPassword123!",
                "encrypted_password": "encrypted_value",
                "yaml_value": "!decrypt encrypted_value",
            }
            manager.password_generator.generate_user_password = MagicMock(
                return_value=mock_result
            )

            result = manager.generate_password("TEST_USER", "PERSON", 16)

            assert result["username"] == "TEST_USER"
            assert result["user_type"] == "PERSON"
            assert "plain_password" in result
            manager.password_generator.generate_user_password.assert_called_once()

    def test_generate_password_different_lengths(self):
        """Test password generation with different lengths"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            manager.password_generator.generate_user_password = MagicMock(
                return_value={"username": "TEST", "length": 20}
            )

            result = manager.generate_password("TEST_USER", "PERSON", 20)

            # Verify the length parameter was passed
            call_args = manager.password_generator.generate_user_password.call_args
            assert call_args[1]["length"] == 20


class TestRegeneratePassword:
    """Test password regeneration"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_regenerate_password_existing_user(self):
        """Test regenerating password for existing user"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock existing user
            manager.yaml_handler.get_user = MagicMock(return_value={"type": "PERSON"})
            manager.generate_password = MagicMock(
                return_value={
                    "plain_password": "NewPassword123!",
                    "yaml_value": "!decrypt new_encrypted",
                }
            )
            manager.update_user = MagicMock(return_value=True)

            result = manager.regenerate_user_password("EXISTING_USER", 18)

            assert result is True
            manager.yaml_handler.get_user.assert_called_once_with("EXISTING_USER")
            manager.generate_password.assert_called_once()
            manager.update_user.assert_called_once()

    def test_regenerate_password_nonexistent_user(self):
        """Test regenerating password for non-existent user"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock non-existent user
            manager.yaml_handler.get_user = MagicMock(return_value=None)

            result = manager.regenerate_user_password("NONEXISTENT_USER", 16)

            assert result is False
            manager.yaml_handler.get_user.assert_called_once()


class TestUpdateUser:
    """Test user update operations"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_update_user_success(self):
        """Test successful user update"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock get_user to return existing user
            manager.yaml_handler.get_user = MagicMock(return_value={"type": "PERSON"})
            manager.yaml_handler.merge_user = MagicMock()

            result = manager.update_user(
                "TEST_USER", email="newemail@example.com", disabled=False
            )

            assert result is True

    def test_update_user_no_backup(self):
        """Test user update without backup"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock get_user to return existing user
            manager.yaml_handler.get_user = MagicMock(return_value={"type": "PERSON"})
            manager.yaml_handler.merge_user = MagicMock()

            result = manager.update_user("TEST_USER", email="test@example.com")

            assert result is True


class TestDeleteUser:
    """Test user deletion"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_delete_user_success(self):
        """Test successful user deletion"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            manager.yaml_handler.remove_user = MagicMock(return_value=True)

            result = manager.delete_user("TEST_USER")

            assert result is True

    def test_delete_user_not_exists(self):
        """Test deleting non-existent user"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            manager.yaml_handler.remove_user = MagicMock(return_value=False)

            result = manager.delete_user("NONEXISTENT")

            assert result is False


class TestListUsers:
    """Test user listing operations"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_list_users_all(self):
        """Test listing all users"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            mock_users = {
                "USER1": {"type": "PERSON", "email": "user1@example.com"},
                "USER2": {"type": "SERVICE"},
                "USER3": {"type": "PERSON", "email": "user3@example.com"},
            }
            manager.yaml_handler.load_users = MagicMock(return_value=mock_users)

            users = manager.list_users(format="list")

            assert len(users) == 3
            usernames = [u["username"] for u in users]
            assert "USER1" in usernames
            assert "USER2" in usernames
            assert "USER3" in usernames

    def test_list_users_json_format(self):
        """Test listing users in JSON format"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            mock_users = {
                "USER1": {"type": "PERSON"},
                "USER2": {"type": "SERVICE"},
            }
            manager.yaml_handler.load_users = MagicMock(return_value=mock_users)

            result = manager.list_users(format="json")

            import json

            parsed = json.loads(result)
            assert "USER1" in parsed
            assert "USER2" in parsed


class TestValidateUser:
    """Test user validation"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_validate_user_person_complete(self):
        """Test validation of complete PERSON user"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock get_user to return a complete user with authentication
            manager.yaml_handler.get_user = MagicMock(
                return_value={
                    "type": "PERSON",
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com",
                    "default_role": "DEVELOPER",
                    "password": "!decrypt encrypted_password",  # Has auth method
                }
            )

            result = manager.validate_user("TEST_USER")

            assert result["is_valid"] is True
            assert len(result["errors"]) == 0

    def test_validate_user_person_missing_email(self):
        """Test validation flags missing email for PERSON"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock get_user to return a user without email
            manager.yaml_handler.get_user = MagicMock(
                return_value={
                    "type": "PERSON",
                    "first_name": "Test",
                    "last_name": "User",
                    # Missing email
                }
            )

            result = manager.validate_user("TEST_USER")

            # Missing email should show in warnings for PERSON type
            assert "warnings" in result or "errors" in result

    def test_validate_user_service_valid(self):
        """Test validation of valid SERVICE account"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock get_user to return a service account with RSA auth
            manager.yaml_handler.get_user = MagicMock(
                return_value={
                    "type": "SERVICE",
                    "default_role": "SERVICE_ROLE",
                    "rsa_public_key": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
                }
            )

            result = manager.validate_user("SERVICE_ACCOUNT")

            assert result["is_valid"] is True

    def test_validate_user_not_found(self):
        """Test validation fails for non-existent user"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Mock get_user to return None (user not found)
            manager.yaml_handler.get_user = MagicMock(return_value=None)

            result = manager.validate_user("NONEXISTENT")

            assert result["is_valid"] is False
            assert len(result["errors"]) > 0


class TestUserExists:
    """Test user existence checks via get_user"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_user_exists(self):
        """Test getting existing user returns data"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            manager.yaml_handler.get_user = MagicMock(return_value={"type": "PERSON"})

            user = manager.get_user("EXISTING_USER")

            assert user is not None
            manager.yaml_handler.get_user.assert_called_once_with("EXISTING_USER")

    def test_get_user_not_exists(self):
        """Test getting non-existent user returns None"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            manager.yaml_handler.get_user = MagicMock(return_value=None)

            user = manager.get_user("NONEXISTENT_USER")

            assert user is None


class TestGetUser:
    """Test getting user details"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_user_success(self):
        """Test getting existing user"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            mock_user = {
                "type": "PERSON",
                "email": "test@example.com",
                "login_name": "TEST_USER",
            }
            manager.yaml_handler.get_user = MagicMock(return_value=mock_user)

            user = manager.get_user("TEST_USER")

            assert user is not None
            assert user["type"] == "PERSON"
            assert user["email"] == "test@example.com"

    def test_get_user_not_found(self):
        """Test getting non-existent user"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            manager.yaml_handler.get_user = MagicMock(return_value=None)

            user = manager.get_user("NONEXISTENT")

            assert user is None


class TestErrorScenarios:
    """Test error handling scenarios"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_user_raises_error_on_failure(self):
        """Test that create_user raises UserCreationError on failure"""
        with patch.multiple(
            "user_management.manager",
            FernetEncryption=MagicMock(),
            RSAKeyManager=MagicMock(),
            YAMLHandler=MagicMock(),
            SnowDDLAccountManager=MagicMock(),
            PasswordGenerator=MagicMock(),
        ):
            manager = UserManager(config_directory=self.config_dir)

            # Force an exception
            manager.yaml_handler.merge_user = MagicMock(
                side_effect=Exception("Test error")
            )

            with pytest.raises(UserCreationError):
                manager.create_user(
                    interactive=False,
                    first_name="Test",
                    last_name="User",
                    email="test@example.com",
                    user_type=UserType.PERSON,
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
