"""Integration tests for CLI commands.

Tests that all registered UV commands are accessible and respond correctly.
"""

import subprocess
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_command(cmd, timeout=30):
    """Run a UV command and return the result."""
    return subprocess.run(
        ["uv", "run"] + cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=timeout,
    )


class TestCoreCommands:
    """Test core SnowDDL operation commands."""

    def test_snowddl_plan_runs(self):
        """snowddl-plan should execute (may fail on missing connection)."""
        result = run_command(["snowddl-plan"])
        # Should not be 'command not found' (127)
        assert result.returncode != 127

    def test_snowddl_apply_has_help(self):
        """snowddl-apply should be a registered command."""
        result = run_command(["snowddl-apply", "--help"])
        assert result.returncode != 127

    def test_snowddl_validate_exists(self):
        """snowddl-validate should be a registered command."""
        result = run_command(["snowddl-validate", "--help"])
        assert result.returncode != 127

    def test_snowddl_diff_exists(self):
        """snowddl-diff should be a registered command."""
        result = run_command(["snowddl-diff", "--help"])
        assert result.returncode != 127


class TestUserManagementCommands:
    """Test user management commands."""

    def test_manage_users_help(self):
        """manage-users --help should show usage."""
        result = run_command(["manage-users", "--help"])
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "manage" in result.stdout.lower()

    def test_util_generate_key(self):
        """util-generate-key should generate a Fernet key."""
        result = run_command(["util-generate-key"])
        # Should output a base64-encoded key or help text
        assert result.returncode != 127


class TestResourceManagementCommands:
    """Test resource management commands."""

    def test_manage_warehouses_help(self):
        """manage-warehouses --help should show usage."""
        result = run_command(["manage-warehouses", "--help"])
        assert result.returncode == 0

    def test_manage_costs_help(self):
        """manage-costs --help should show usage."""
        result = run_command(["manage-costs", "--help"])
        assert result.returncode == 0

    def test_manage_security_help(self):
        """manage-security --help should show usage."""
        result = run_command(["manage-security", "--help"])
        assert result.returncode == 0

    def test_manage_backup_help(self):
        """manage-backup --help should show usage."""
        result = run_command(["manage-backup", "--help"])
        assert result.returncode == 0


class TestMonitoringCommands:
    """Test monitoring commands."""

    def test_monitor_health_help(self):
        """monitor-health --help should show usage."""
        result = run_command(["monitor-health", "--help"])
        assert result.returncode == 0

    def test_monitor_audit_help(self):
        """monitor-audit --help should show usage."""
        result = run_command(["monitor-audit", "--help"])
        assert result.returncode == 0

    def test_monitor_metrics_help(self):
        """monitor-metrics --help should show usage."""
        result = run_command(["monitor-metrics", "--help"])
        assert result.returncode == 0


class TestHelpCommand:
    """Test help and discovery."""

    def test_snowtower_help(self):
        """snowtower should show available commands."""
        result = run_command(["snowtower"])
        assert result.returncode == 0


class TestDeploySafe:
    """Test deploy-safe command."""

    def test_deploy_safe_help(self):
        """deploy-safe --help should show usage."""
        result = run_command(["deploy-safe", "--help"])
        assert result.returncode == 0
