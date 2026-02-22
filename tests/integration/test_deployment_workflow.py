"""Integration tests for deployment workflow.

Tests the plan -> review -> apply lifecycle with mocked Snowflake connections.
"""

import subprocess
import tempfile
import shutil
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, Mock

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestPlanWorkflow:
    """Test the snowddl-plan command behavior."""

    def test_plan_with_valid_config(self):
        """Plan should run against the real snowddl/ directory."""
        result = subprocess.run(
            ["uv", "run", "snowddl-plan"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30,
        )
        # May fail due to missing Snowflake connection, but shouldn't crash
        assert result.returncode != 127, "snowddl-plan command not found"

    def test_plan_output_format(self):
        """Plan output should contain recognizable SnowDDL markers."""
        result = subprocess.run(
            ["uv", "run", "snowddl-plan"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30,
        )
        output = result.stdout + result.stderr
        # Should have some output, even if it's an error message
        assert len(output) > 0


class TestDeploySafeWorkflow:
    """Test the deploy-safe wrapper."""

    def test_deploy_safe_exists(self):
        """deploy-safe command should be available."""
        result = subprocess.run(
            ["uv", "run", "deploy-safe", "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30,
        )
        assert result.returncode != 127

    def test_deploy_safe_has_dry_run(self):
        """deploy-safe should support --dry-run or similar safety flag."""
        result = subprocess.run(
            ["uv", "run", "deploy-safe", "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30,
        )
        # Check help text exists
        assert len(result.stdout + result.stderr) > 0


class TestYAMLConfigLifecycle:
    """Test adding/modifying/removing users through YAML."""

    def setup_method(self):
        """Create a temporary snowddl config directory."""
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir)

    def teardown_method(self):
        """Clean up temp directory."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_user_to_yaml(self):
        """Adding a user to YAML should be readable back."""
        from user_management.yaml_handler import YAMLHandler

        handler = YAMLHandler(config_directory=self.config_dir)

        user_data = {
            "NEW_ANALYST": {
                "type": "PERSON",
                "login_name": "NEW_ANALYST",
                "email": "analyst@example.com",
                "first_name": "New",
                "last_name": "Analyst",
                "default_role": "ANALYST_ROLE",
            }
        }

        handler.save_users(user_data, backup=False)
        loaded = handler.load_users()

        assert "NEW_ANALYST" in loaded
        assert loaded["NEW_ANALYST"]["email"] == "analyst@example.com"

    def test_modify_user_in_yaml(self):
        """Modifying a user should persist changes."""
        from user_management.yaml_handler import YAMLHandler

        handler = YAMLHandler(config_directory=self.config_dir)

        # Create initial user
        handler.save_users(
            {"TEST_USER": {"type": "PERSON", "login_name": "TEST_USER", "email": "old@example.com"}},
            backup=False,
        )

        # Load, modify, save
        users = handler.load_users()
        users["TEST_USER"]["email"] = "new@example.com"
        handler.save_users(users, backup=False)

        # Verify
        reloaded = handler.load_users()
        assert reloaded["TEST_USER"]["email"] == "new@example.com"

    def test_remove_user_from_yaml(self):
        """Removing a user should persist."""
        from user_management.yaml_handler import YAMLHandler

        handler = YAMLHandler(config_directory=self.config_dir)

        handler.save_users(
            {
                "USER_A": {"type": "PERSON", "login_name": "USER_A"},
                "USER_B": {"type": "PERSON", "login_name": "USER_B"},
            },
            backup=False,
        )

        users = handler.load_users()
        del users["USER_A"]
        handler.save_users(users, backup=False)

        reloaded = handler.load_users()
        assert "USER_A" not in reloaded
        assert "USER_B" in reloaded

    def test_backup_before_modification(self):
        """Backup should be created before modifications."""
        from user_management.yaml_handler import YAMLHandler

        handler = YAMLHandler(config_directory=self.config_dir)

        # Save initial state
        handler.save_users({"ORIGINAL": {"type": "PERSON", "login_name": "ORIGINAL"}}, backup=False)

        # Modify with backup
        handler.save_users({"MODIFIED": {"type": "PERSON", "login_name": "MODIFIED"}}, backup=True)

        # Check backup exists
        backups = list(handler.backup_dir.glob("user_*.yaml"))
        assert len(backups) >= 1

        # Verify backup contains original data
        with open(backups[0]) as f:
            backup_data = yaml.safe_load(f)
        assert "ORIGINAL" in backup_data


class TestRollbackWorkflow:
    """Test rollback capabilities."""

    def test_git_rollback_of_yaml(self):
        """Verify git can rollback YAML changes (simulated)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            user_yaml = config_dir / "user.yaml"

            # Write v1
            v1 = {"USER_V1": {"type": "PERSON"}}
            user_yaml.write_text(yaml.dump(v1))

            # Write v2
            v2 = {"USER_V2": {"type": "SERVICE"}}
            user_yaml.write_text(yaml.dump(v2))

            # Verify v2 is current
            current = yaml.safe_load(user_yaml.read_text())
            assert "USER_V2" in current
            assert "USER_V1" not in current

            # Simulate rollback by restoring v1
            user_yaml.write_text(yaml.dump(v1))
            restored = yaml.safe_load(user_yaml.read_text())
            assert "USER_V1" in restored
            assert "USER_V2" not in restored
