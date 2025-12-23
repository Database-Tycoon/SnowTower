"""
Test Suite for Management CLI Wrapper Functions

Tests the CLI wrapper functions in management_cli.py that provide
entry points for UV commands.
"""

import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path

# Import CLI wrapper functions
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from management_cli import (
    warehouses,
    costs,
    security,
    backup,
    users,
    snowddl_plan,
    snowddl_apply,
    user_create,
    monitor_health,
)


class TestWarehousesCLI:
    """Test warehouse management CLI wrapper"""

    @patch("manage_warehouses.main")
    def test_warehouses_command_executes(self, mock_main):
        """Test that warehouses command calls the main function"""
        warehouses()
        mock_main.assert_called_once()

    @patch("manage_warehouses.main")
    def test_warehouses_command_handles_errors(self, mock_main):
        """Test error handling in warehouses command"""
        mock_main.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            warehouses()


class TestCostsCLI:
    """Test cost management CLI wrapper"""

    @patch("cost_optimization.main")
    def test_costs_command_executes(self, mock_main):
        """Test that costs command calls the main function"""
        costs()
        mock_main.assert_called_once()

    @patch("cost_optimization.main")
    def test_costs_command_handles_errors(self, mock_main):
        """Test error handling in costs command"""
        mock_main.side_effect = Exception("Cost analysis error")

        with pytest.raises(Exception, match="Cost analysis error"):
            costs()


class TestSecurityCLI:
    """Test security audit CLI wrapper"""

    @patch("security_audit.main")
    def test_security_command_executes(self, mock_main):
        """Test that security command calls the main function"""
        security()
        mock_main.assert_called_once()

    @patch("security_audit.main")
    def test_security_command_handles_errors(self, mock_main):
        """Test error handling in security command"""
        mock_main.side_effect = Exception("Security audit error")

        with pytest.raises(Exception, match="Security audit error"):
            security()


class TestBackupCLI:
    """Test backup and restore CLI wrapper"""

    @patch("backup_restore.main")
    def test_backup_command_executes(self, mock_main):
        """Test that backup command calls the main function"""
        backup()
        mock_main.assert_called_once()

    @patch("backup_restore.main")
    def test_backup_command_handles_errors(self, mock_main):
        """Test error handling in backup command"""
        mock_main.side_effect = Exception("Backup error")

        with pytest.raises(Exception, match="Backup error"):
            backup()


class TestUsersCLI:
    """Test user management CLI wrapper"""

    @patch("manage_users.main")
    def test_users_command_executes(self, mock_main):
        """Test that users command calls the main function"""
        users()
        mock_main.assert_called_once()

    @patch("manage_users.main")
    def test_users_command_handles_errors(self, mock_main):
        """Test error handling in users command"""
        mock_main.side_effect = Exception("User management error")

        with pytest.raises(Exception, match="User management error"):
            users()


class TestSnowDDLCLI:
    """Test SnowDDL CLI wrappers"""

    @patch("snowtower_snowddl.cli.plan")
    def test_snowddl_plan_executes(self, mock_plan):
        """Test that snowddl-plan command executes"""
        snowddl_plan()
        mock_plan.assert_called_once()

    @patch("snowtower_snowddl.cli.apply")
    def test_snowddl_apply_executes(self, mock_apply):
        """Test that snowddl-apply command executes"""
        snowddl_apply()
        mock_apply.assert_called_once()

    @patch("snowtower_snowddl.cli.plan")
    def test_snowddl_plan_handles_errors(self, mock_plan):
        """Test error handling in snowddl-plan"""
        mock_plan.side_effect = Exception("Plan generation error")

        with pytest.raises(Exception, match="Plan generation error"):
            snowddl_plan()


class TestUserCreateCLI:
    """Test user creation CLI wrapper"""

    @patch("user_create.main")
    def test_user_create_command_executes(self, mock_main):
        """Test that user-create command calls the main function"""
        user_create()
        mock_main.assert_called_once()

    @patch("user_create.main")
    def test_user_create_command_handles_errors(self, mock_main):
        """Test error handling in user-create command"""
        mock_main.side_effect = Exception("User creation error")

        with pytest.raises(Exception, match="User creation error"):
            user_create()


class TestMonitorHealthCLI:
    """Test health monitoring CLI wrapper"""

    @patch("monitor_health.main")
    def test_monitor_health_command_executes(self, mock_main):
        """Test that monitor-health command calls the main function"""
        monitor_health()
        mock_main.assert_called_once()

    @patch("monitor_health.main")
    def test_monitor_health_command_handles_errors(self, mock_main):
        """Test error handling in monitor-health command"""
        mock_main.side_effect = Exception("Health check error")

        with pytest.raises(Exception, match="Health check error"):
            monitor_health()


class TestCLIIntegration:
    """Test CLI integration and command chaining"""

    @patch("manage_warehouses.main")
    @patch("cost_optimization.main")
    def test_sequential_command_execution(self, mock_costs, mock_warehouses):
        """Test executing multiple CLI commands sequentially"""
        # Execute commands in sequence
        warehouses()
        costs()

        # Verify both were called
        mock_warehouses.assert_called_once()
        mock_costs.assert_called_once()

    def test_cli_command_availability(self):
        """Test that all CLI commands are importable"""
        from management_cli import (
            warehouses,
            costs,
            security,
            backup,
            users,
            snowddl_plan,
            snowddl_apply,
            snowddl_validate,
            user_create,
            monitor_health,
            monitor_logs,
        )

        # All imports should succeed without errors
        assert warehouses is not None
        assert costs is not None
        assert snowddl_plan is not None


class TestCLIErrorHandling:
    """Test CLI error handling and recovery"""

    @patch("manage_users.main")
    def test_cli_recovers_from_import_error(self, mock_main):
        """Test that CLI handles import errors gracefully"""
        mock_main.side_effect = ImportError("Module not found")

        with pytest.raises(ImportError):
            users()


class TestCLIDocumentation:
    """Test CLI command documentation and help"""

    def test_cli_module_has_docstring(self):
        """Test that management_cli module has documentation"""
        import management_cli

        assert management_cli.__doc__ is not None

    def test_cli_functions_have_docstrings(self):
        """Test that CLI wrapper functions have docstrings"""
        from management_cli import warehouses, costs, security

        assert warehouses.__doc__ is not None
        assert costs.__doc__ is not None
        assert security.__doc__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/management_cli.py"])
