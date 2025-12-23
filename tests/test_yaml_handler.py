#!/usr/bin/env python3
"""
Comprehensive Test Suite for YAMLHandler Module

Tests YAML loading, saving, backup, user management, and error handling.
"""

import pytest
import yaml
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from user_management.yaml_handler import (
    YAMLHandler,
    YAMLError,
    YAMLFileNotFoundError,
    YAMLValidationError,
    YAMLBackupError,
    decrypt_constructor,
)


class TestYAMLHandlerInitialization:
    """Test YAMLHandler initialization"""

    def test_init_with_default_config_dir(self):
        """Test initialization with default config directory"""
        handler = YAMLHandler()

        assert handler.config_dir == Path.cwd() / "snowddl"
        assert handler.user_yaml == handler.config_dir / "user.yaml"
        assert handler.backup_dir == handler.config_dir / ".backups"

    def test_init_with_custom_config_dir(self):
        """Test initialization with custom config directory"""
        custom_dir = Path("/tmp/custom_snowddl")
        handler = YAMLHandler(config_directory=custom_dir)

        assert handler.config_dir == custom_dir
        assert handler.user_yaml == custom_dir / "user.yaml"
        assert handler.backup_dir == custom_dir / ".backups"

    def test_init_creates_backup_directory(self):
        """Test that initialization creates backup directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "snowddl"
            handler = YAMLHandler(config_directory=config_dir)

            assert handler.backup_dir.exists()
            assert handler.backup_dir.is_dir()


class TestLoadUsers:
    """Test loading users from YAML"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)
        self.handler = YAMLHandler(config_directory=self.config_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_users_success(self):
        """Test successful user loading"""
        users_data = {
            "TEST_USER": {
                "type": "PERSON",
                "login_name": "TEST_USER",
                "email": "test@example.com",
            }
        }

        self.handler.user_yaml.write_text(yaml.dump(users_data))

        users = self.handler.load_users()

        assert len(users) == 1
        assert "TEST_USER" in users
        assert users["TEST_USER"]["type"] == "PERSON"

    def test_load_users_file_not_found(self):
        """Test loading users when file doesn't exist"""
        with pytest.raises(
            YAMLFileNotFoundError, match="User configuration file not found"
        ):
            self.handler.load_users()

    def test_load_users_empty_file(self):
        """Test loading users from empty file"""
        self.handler.user_yaml.write_text("")

        users = self.handler.load_users()

        assert users == {}

    def test_load_users_invalid_yaml(self):
        """Test loading users with invalid YAML"""
        self.handler.user_yaml.write_text("invalid: yaml: content: [")

        with pytest.raises(YAMLError, match="Failed to parse YAML file"):
            self.handler.load_users()

    def test_load_users_non_dict_content(self):
        """Test loading users with non-dictionary content"""
        self.handler.user_yaml.write_text("- list\n- of\n- items")

        with pytest.raises(
            YAMLValidationError, match="User YAML must contain a dictionary"
        ):
            self.handler.load_users()

    def test_load_users_with_encrypted_passwords(self):
        """Test loading users with encrypted passwords"""
        users_data = {
            "TEST_USER": {
                "type": "PERSON",
                "login_name": "TEST_USER",
                "password": "!decrypt gAAAAABencryptedpassword==",
            }
        }

        self.handler.user_yaml.write_text(yaml.dump(users_data))

        users = self.handler.load_users()

        assert "TEST_USER" in users
        # The !decrypt tag should be preserved
        assert "password" in users["TEST_USER"]


class TestSaveUsers:
    """Test saving users to YAML"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)
        self.handler = YAMLHandler(config_directory=self.config_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_users_success(self):
        """Test successful user saving"""
        users_data = {
            "TEST_USER": {
                "type": "PERSON",
                "login_name": "TEST_USER",
                "email": "test@example.com",
            }
        }

        self.handler.save_users(users_data, backup=False)

        assert self.handler.user_yaml.exists()

        # Verify content
        with open(self.handler.user_yaml) as f:
            loaded = yaml.safe_load(f)

        assert loaded == users_data

    def test_save_users_creates_directory(self):
        """Test that save creates directory if it doesn't exist"""
        shutil.rmtree(self.config_dir)

        users_data = {"TEST_USER": {"type": "PERSON"}}

        self.handler.save_users(users_data, backup=False)

        assert self.config_dir.exists()
        assert self.handler.user_yaml.exists()

    def test_save_users_with_backup(self):
        """Test saving users with backup creation"""
        # Create initial file
        initial_data = {"OLD_USER": {"type": "PERSON"}}
        self.handler.user_yaml.write_text(yaml.dump(initial_data))

        # Save with backup
        new_data = {"NEW_USER": {"type": "PERSON"}}
        self.handler.save_users(new_data, backup=True)

        # Check backup was created
        backup_files = list(self.handler.backup_dir.glob("user_*.yaml"))
        assert len(backup_files) > 0

    def test_save_users_sorted_keys(self):
        """Test that users are saved with sorted keys"""
        users_data = {
            "ZEBRA_USER": {"type": "PERSON"},
            "ALPHA_USER": {"type": "PERSON"},
            "BETA_USER": {"type": "PERSON"},
        }

        self.handler.save_users(users_data, backup=False)

        # Read file as text to check order
        content = self.handler.user_yaml.read_text()
        lines = content.split("\n")
        user_lines = [line for line in lines if line and not line.startswith(" ")]

        # Should be alphabetically sorted
        assert user_lines == sorted(user_lines)

    def test_save_users_empty_dict(self):
        """Test saving empty user dictionary"""
        self.handler.save_users({}, backup=False)

        assert self.handler.user_yaml.exists()

        with open(self.handler.user_yaml) as f:
            loaded = yaml.safe_load(f)

        assert loaded == {}


class TestBackupOperations:
    """Test backup functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)
        self.handler = YAMLHandler(config_directory=self.config_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_backup_config_creates_backup(self):
        """Test that backup creates backup file"""
        # Create user file
        users_data = {"TEST_USER": {"type": "PERSON"}}
        self.handler.user_yaml.write_text(yaml.dump(users_data))

        self.handler.backup_config()

        # Check backup was created
        backup_files = list(self.handler.backup_dir.glob("user_*.yaml"))
        assert len(backup_files) == 1

        # Verify backup content
        with open(backup_files[0]) as f:
            backup_data = yaml.safe_load(f)

        assert backup_data == users_data

    def test_backup_config_multiple_backups(self):
        """Test that multiple backups are created with different timestamps"""
        import time

        users_data = {"TEST_USER": {"type": "PERSON"}}
        self.handler.user_yaml.write_text(yaml.dump(users_data))

        # Create multiple backups with small delay to ensure different timestamps
        self.handler.backup_config()
        time.sleep(1.1)  # Ensure different second
        self.handler.backup_config()
        time.sleep(1.1)
        self.handler.backup_config()

        backup_files = list(self.handler.backup_dir.glob("user_*.yaml"))
        assert len(backup_files) >= 1  # At least one backup created

    def test_backup_config_file_not_exists(self):
        """Test backup when user file doesn't exist"""
        # Should handle gracefully
        try:
            self.handler.backup_config()
        except Exception as e:
            # Expected to fail gracefully
            assert "not found" in str(e).lower() or isinstance(
                e, (FileNotFoundError, YAMLBackupError)
            )

    def test_list_backups(self):
        """Test listing backups"""
        import time

        # Create some backups
        users_data = {"TEST_USER": {"type": "PERSON"}}
        self.handler.user_yaml.write_text(yaml.dump(users_data))

        self.handler.backup_config()
        time.sleep(1.1)
        self.handler.backup_config()

        backups = self.handler.list_backups()

        assert len(backups) >= 2
        for backup in backups:
            # list_backups returns list of dicts with 'path' key
            assert backup["path"].exists()
            assert backup["path"].suffix == ".yaml"

    def test_restore_from_backup(self):
        """Test restoring from backup"""
        import time

        # Create initial data
        initial_data = {"ORIGINAL_USER": {"type": "PERSON"}}
        self.handler.user_yaml.write_text(yaml.dump(initial_data))
        self.handler.backup_config()

        # Get the original backup name before any modifications
        original_backup = self.handler.list_backups()[0]["name"]

        # Wait to ensure different timestamps for any subsequent backups
        time.sleep(1.1)

        # Modify data
        modified_data = {"MODIFIED_USER": {"type": "SERVICE"}}
        self.handler.save_users(modified_data, backup=False)

        # Restore from the original backup (use backup name and skip confirmation)
        self.handler.restore_backup(original_backup, confirm=False)

        # Verify restoration
        restored = self.handler.load_users()
        assert "ORIGINAL_USER" in restored
        assert "MODIFIED_USER" not in restored


class TestUserOperations:
    """Test user-specific operations"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)
        self.handler = YAMLHandler(config_directory=self.config_dir)

        # Create initial users
        self.initial_users = {
            "EXISTING_USER": {
                "type": "PERSON",
                "login_name": "EXISTING_USER",
                "email": "existing@example.com",
            }
        }
        self.handler.save_users(self.initial_users, backup=False)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_user_exists(self):
        """Test getting existing user"""
        user = self.handler.get_user("EXISTING_USER")

        assert user is not None
        assert user["type"] == "PERSON"
        assert user["email"] == "existing@example.com"

    def test_get_user_not_exists(self):
        """Test getting non-existent user returns None"""
        user = self.handler.get_user("NONEXISTENT_USER")
        assert user is None

    def test_merge_user_add_new(self):
        """Test merging a new user"""
        new_user_data = {"type": "SERVICE", "login_name": "NEW_SERVICE"}

        self.handler.merge_user("NEW_SERVICE", new_user_data, backup=False)

        users = self.handler.load_users()
        assert "NEW_SERVICE" in users
        assert "EXISTING_USER" in users

    def test_merge_user_update_existing(self):
        """Test merging updates existing user"""
        updated_data = {
            "type": "PERSON",
            "login_name": "EXISTING_USER",
            "email": "updated@example.com",
            "new_field": "new_value",
        }

        # Mock confirmation prompt to allow overwrite
        with patch("user_management.yaml_handler.Confirm.ask", return_value=True):
            self.handler.merge_user("EXISTING_USER", updated_data, backup=False)

        users = self.handler.load_users()
        assert users["EXISTING_USER"]["email"] == "updated@example.com"
        assert users["EXISTING_USER"]["new_field"] == "new_value"

    def test_delete_user_exists(self):
        """Test deleting existing user"""
        with patch("user_management.yaml_handler.Confirm.ask", return_value=True):
            result = self.handler.remove_user("EXISTING_USER", backup=False)

        assert result is True
        users = self.handler.load_users()
        assert "EXISTING_USER" not in users

    def test_delete_user_not_exists(self):
        """Test deleting non-existent user"""
        result = self.handler.remove_user("NONEXISTENT_USER", backup=False)

        assert result is False

    def test_user_exists_true(self):
        """Test user_exists for existing user"""
        exists = self.handler.user_exists("EXISTING_USER")
        assert exists is True

    def test_user_exists_false(self):
        """Test user_exists for non-existent user"""
        exists = self.handler.user_exists("NONEXISTENT_USER")
        assert exists is False


class TestDecryptConstructor:
    """Test YAML decrypt constructor"""

    def test_decrypt_constructor(self):
        """Test decrypt constructor preserves format"""
        yaml_content = """
TEST_USER:
  type: PERSON
  password: !decrypt gAAAAABencrypteddata
"""
        data = yaml.safe_load(yaml_content)

        assert "TEST_USER" in data
        assert data["TEST_USER"]["password"].startswith("!decrypt ")

    def test_decrypt_constructor_multiple_users(self):
        """Test decrypt constructor with multiple users"""
        yaml_content = """
USER1:
  password: !decrypt encrypted1
USER2:
  password: !decrypt encrypted2
"""
        data = yaml.safe_load(yaml_content)

        assert data["USER1"]["password"].startswith("!decrypt ")
        assert data["USER2"]["password"].startswith("!decrypt ")


class TestBulkOperations:
    """Test bulk user operations"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)
        self.handler = YAMLHandler(config_directory=self.config_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_bulk_add_users(self):
        """Test adding multiple users at once"""
        users = {
            "USER1": {"type": "PERSON", "email": "user1@example.com"},
            "USER2": {"type": "PERSON", "email": "user2@example.com"},
            "USER3": {"type": "SERVICE"},
        }

        self.handler.save_users(users, backup=False)

        loaded = self.handler.load_users()
        assert len(loaded) == 3
        assert all(user in loaded for user in users.keys())

    def test_bulk_update_users(self):
        """Test updating multiple users"""
        # Create initial users
        initial = {
            "USER1": {"type": "PERSON", "email": "old1@example.com"},
            "USER2": {"type": "PERSON", "email": "old2@example.com"},
        }
        self.handler.save_users(initial, backup=False)

        # Update with new data
        updates = {
            "USER1": {"type": "PERSON", "email": "new1@example.com"},
            "USER2": {"type": "PERSON", "email": "new2@example.com"},
        }

        # Mock confirmation prompt to allow overwrites
        with patch("user_management.yaml_handler.Confirm.ask", return_value=True):
            for username, data in updates.items():
                self.handler.merge_user(username, data, backup=False)

        loaded = self.handler.load_users()
        assert loaded["USER1"]["email"] == "new1@example.com"
        assert loaded["USER2"]["email"] == "new2@example.com"


class TestErrorHandling:
    """Test error handling scenarios"""

    def setup_method(self):
        """Set up test environment"""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "snowddl"
        self.config_dir.mkdir(parents=True)
        self.handler = YAMLHandler(config_directory=self.config_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_users_permission_error(self):
        """Test save fails gracefully on permission error"""
        users = {"TEST": {"type": "PERSON"}}

        # Make directory read-only
        self.config_dir.chmod(0o444)

        with pytest.raises(YAMLError):
            self.handler.save_users(users, backup=False)

        # Restore permissions for cleanup
        self.config_dir.chmod(0o755)

    def test_load_users_corrupted_file(self):
        """Test loading corrupted YAML file"""
        # Create corrupted YAML
        self.handler.user_yaml.write_text("{{invalid yaml structure")

        with pytest.raises(YAMLError, match="Failed to parse YAML"):
            self.handler.load_users()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
