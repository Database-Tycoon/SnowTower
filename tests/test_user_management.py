"""
Comprehensive Test Suite for User Management System

Tests user creation, authentication, lifecycle management, and YAML handling.
Covers the UserManager class and related components.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import user management components
from user_management import UserManager, UserType
from user_management.manager import UserValidationError, UserCreationError
from user_management.yaml_handler import YAMLHandler, YAMLError
from user_management.encryption import FernetEncryption


class TestUserCreation:
    """Test user creation functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path("/tmp/test_snowddl")
        self.temp_dir.mkdir(exist_ok=True)
        self.manager = UserManager(config_directory=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_create_person_user_with_rsa_key(self):
        """Test creating a PERSON user with RSA key authentication"""
        user_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@company.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
        }

        result = self.manager.create_user(interactive=False, **user_data)

        assert "JOHN_DOE" in result
        user_config = result["JOHN_DOE"]
        assert user_config["type"] == "PERSON"
        assert user_config["email"] == "john.doe@company.com"
        assert user_config["first_name"] == "John"
        assert user_config["last_name"] == "Doe"

    def test_create_person_user_with_password(self):
        """Test creating a PERSON user with encrypted password"""
        user_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@company.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
            "password_length": 20,
        }

        result = self.manager.create_user(interactive=False, **user_data)

        assert "JANE_SMITH" in result
        user_config = result["JANE_SMITH"]
        assert "password" in user_config
        assert user_config["password"].startswith("!decrypt")

    def test_create_service_account_rsa_required(self):
        """Test creating a SERVICE account (RSA keys recommended)"""
        user_data = {
            "first_name": "ETL",
            "last_name": "Service",
            "email": "etl@company.com",
            "user_type": UserType.SERVICE,
            "username": "ETL_SERVICE",
        }

        result = self.manager.create_user(interactive=False, **user_data)

        assert "ETL_SERVICE" in result
        user_config = result["ETL_SERVICE"]
        assert user_config["type"] == "SERVICE"

    def test_user_creation_validation_errors(self):
        """Test that user creation fails with missing required fields"""
        incomplete_data = {
            "first_name": "Missing",
            # Missing last_name and email
        }

        with pytest.raises(UserCreationError, match="Required field missing"):
            self.manager.create_user(interactive=False, **incomplete_data)

    def test_mfa_compliance_tracking(self):
        """Test MFA compliance validation for PERSON users"""
        user_data = {
            "first_name": "MFA",
            "last_name": "User",
            "email": "mfa@company.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
            "authentication_policy": "mfa_required_policy",
        }

        result = self.manager.create_user(interactive=False, **user_data)
        username = list(result.keys())[0]

        # Validate MFA compliance
        validation_result = self.manager.validate_user(username)
        assert validation_result["is_valid"]


class TestUserAuthentication:
    """Test user authentication setup and validation"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path("/tmp/test_snowddl_auth")
        self.temp_dir.mkdir(exist_ok=True)
        self.manager = UserManager(config_directory=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_dual_authentication_setup(self):
        """Test setting up both password and RSA key authentication"""
        user_data = {
            "first_name": "Dual",
            "last_name": "Auth",
            "email": "dual@company.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
        }

        result = self.manager.create_user(interactive=False, **user_data)
        user_config = result["DUAL_AUTH"]

        # Check that password was generated
        assert "password" in user_config
        assert user_config["password"].startswith("!decrypt")

    def test_password_encryption_integration(self):
        """Test that password encryption works correctly"""
        test_password = "TestPassword123!"
        encrypted = self.manager.encrypt_password(test_password)

        assert encrypted is not None
        assert encrypted != test_password
        assert len(encrypted) > 0

    def test_network_policy_assignment(self):
        """Test network policy assignment to users"""
        user_data = {
            "first_name": "Network",
            "last_name": "User",
            "email": "network@company.com",
            "user_type": UserType.PERSON,
            "network_policy": "office_network_policy",
            "auto_generate_password": True,
        }

        result = self.manager.create_user(interactive=False, **user_data)
        user_config = result["NETWORK_USER"]

        assert user_config.get("network_policy") == "office_network_policy"


class TestUserLifecycle:
    """Test user lifecycle operations"""

    def setup_method(self):
        """Set up test environment with a test user"""
        self.temp_dir = Path("/tmp/test_snowddl_lifecycle")
        self.temp_dir.mkdir(exist_ok=True)
        self.manager = UserManager(config_directory=self.temp_dir)

        # Create a test user
        user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@company.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
        }
        self.manager.create_user(interactive=False, **user_data)
        self.test_username = "TEST_USER"

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_user_modification(self):
        """Test updating an existing user"""
        success = self.manager.update_user(
            self.test_username, email="updated@company.com", default_warehouse="NEW_WH"
        )

        assert success
        user = self.manager.get_user(self.test_username)
        assert user["email"] == "updated@company.com"
        assert user["default_warehouse"] == "NEW_WH"

    def test_user_disable_enable(self):
        """Test disabling and enabling users"""
        # Disable user
        self.manager.update_user(self.test_username, disabled=True)
        user = self.manager.get_user(self.test_username)
        assert user.get("disabled") is True

        # Enable user
        self.manager.update_user(self.test_username, disabled=False)
        user = self.manager.get_user(self.test_username)
        assert user.get("disabled") is False

    def test_role_assignment(self):
        """Test assigning roles to users"""
        self.manager.update_user(self.test_username, default_role="DATA_ANALYST_ROLE")

        user = self.manager.get_user(self.test_username)
        assert user["default_role"] == "DATA_ANALYST_ROLE"


class TestPasswordGeneration:
    """Test automatic password generation functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path("/tmp/test_snowddl_password")
        self.temp_dir.mkdir(exist_ok=True)
        self.manager = UserManager(config_directory=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_generate_secure_password(self):
        """Test generating a secure password"""
        result = self.manager.generate_password(
            username="TEST_USER", user_type="PERSON", length=16
        )

        assert "plain_password" in result
        assert "yaml_value" in result
        assert len(result["plain_password"]) >= 16
        assert result["yaml_value"].startswith("!decrypt")

    def test_password_length_validation(self):
        """Test password length requirements"""
        result = self.manager.generate_password(username="TEST_USER", length=20)

        assert len(result["plain_password"]) == 20

    def test_regenerate_user_password(self):
        """Test regenerating password for existing user"""
        # Create user first
        user_data = {
            "first_name": "Test",
            "last_name": "Regen",
            "email": "regen@company.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
        }
        self.manager.create_user(interactive=False, **user_data)

        # Regenerate password
        success = self.manager.regenerate_user_password("TEST_REGEN", length=18)

        assert success


class TestUserValidation:
    """Test user configuration validation"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path("/tmp/test_snowddl_validation")
        self.temp_dir.mkdir(exist_ok=True)
        self.manager = UserManager(config_directory=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_validate_person_user_required_fields(self):
        """Test validation of PERSON user required fields"""
        # Create user with all required fields
        user_data = {
            "first_name": "Valid",
            "last_name": "Person",
            "email": "valid@company.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
        }
        self.manager.create_user(interactive=False, **user_data)

        result = self.manager.validate_user("VALID_PERSON")
        assert result["is_valid"]
        assert len(result["errors"]) == 0

    def test_validate_user_authentication_methods(self):
        """Test validation of authentication methods"""
        user_data = {
            "first_name": "Auth",
            "last_name": "Test",
            "email": "auth@company.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
        }
        self.manager.create_user(interactive=False, **user_data)

        result = self.manager.validate_user("AUTH_TEST")
        # Should have at least one authentication method
        assert result["is_valid"]


class TestYAMLHandler:
    """Test YAML file handling operations"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path("/tmp/test_yaml_handler")
        self.temp_dir.mkdir(exist_ok=True)
        self.handler = YAMLHandler(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_create_and_load_users(self):
        """Test creating and loading user configurations"""
        users = {
            "USER1": {
                "type": "PERSON",
                "first_name": "User",
                "last_name": "One",
                "email": "user1@test.com",
            },
            "USER2": {"type": "SERVICE", "email": "service@test.com"},
        }

        self.handler.save_users(users, backup=False)
        loaded_users = self.handler.load_users()

        assert len(loaded_users) == 2
        assert "USER1" in loaded_users
        assert "USER2" in loaded_users

    def test_merge_user_operation(self):
        """Test merging a single user into configuration"""
        # Start with empty config
        initial_users = {
            "INITIAL_USER": {"type": "PERSON", "email": "initial@test.com"}
        }
        self.handler.save_users(initial_users, backup=False)

        # Merge new user (mock the confirmation)
        with patch("user_management.yaml_handler.Confirm.ask", return_value=True):
            self.handler.merge_user(
                "NEW_USER", {"type": "SERVICE", "email": "new@test.com"}
            )

        users = self.handler.load_users()
        assert len(users) == 2
        assert "NEW_USER" in users

    def test_backup_creation(self):
        """Test backup file creation"""
        users = {"BACKUP_TEST": {"type": "PERSON", "email": "backup@test.com"}}
        self.handler.save_users(users, backup=False)

        backup_path = self.handler.backup_config("Test backup")

        assert backup_path.exists()
        assert backup_path.name.startswith("user_backup_")

    def test_list_backups(self):
        """Test listing backup files"""
        # Create a backup
        users = {"USER": {"type": "PERSON", "email": "user@test.com"}}
        self.handler.save_users(users, backup=False)
        self.handler.backup_config("First backup")

        backups = self.handler.list_backups()
        assert len(backups) >= 1
        assert backups[0]["description"] == "First backup"


class TestBulkOperations:
    """Test bulk user operations"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path("/tmp/test_snowddl_bulk")
        self.temp_dir.mkdir(exist_ok=True)
        self.manager = UserManager(config_directory=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_generate_multiple_passwords(self):
        """Test generating passwords for multiple users"""
        usernames = ["USER1", "USER2", "USER3"]
        results = self.manager.generate_passwords_bulk(usernames)

        assert len(results) == 3
        for username in usernames:
            assert username in results
            assert "plain_password" in results[username]
            assert "yaml_value" in results[username]

    def test_list_users_table_format(self):
        """Test listing users in table format"""
        # Create some test users
        for i in range(3):
            user_data = {
                "first_name": f"User{i}",
                "last_name": f"Test{i}",
                "email": f"user{i}@test.com",
                "user_type": UserType.PERSON,
                "auto_generate_password": True,
            }
            self.manager.create_user(interactive=False, **user_data)

        # List users (returns empty string for table format)
        result = self.manager.list_users(format="table")
        assert isinstance(result, str)

    def test_list_users_json_format(self):
        """Test listing users in JSON format"""
        user_data = {
            "first_name": "JSON",
            "last_name": "Test",
            "email": "json@test.com",
            "user_type": UserType.PERSON,
            "auto_generate_password": True,
        }
        self.manager.create_user(interactive=False, **user_data)

        result = self.manager.list_users(format="json")
        assert "JSON_TEST" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/user_management"])
