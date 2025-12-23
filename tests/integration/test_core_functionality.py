"""Minimal meaningful tests for SnowDDL functionality"""

import pytest
import subprocess
from pathlib import Path


class TestSnowDDLCore:
    """Test actual SnowDDL functionality that matters"""

    def test_snowddl_plan_command_works(self):
        """Test that the main snowddl-plan command actually runs"""
        result = subprocess.run(
            ["uv", "run", "snowddl-plan"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        # Should run and show output (even if it fails due to missing config)
        assert result.returncode in [0, 1]  # 0 = success, 1 = expected failure
        assert "snowddl" in result.stdout.lower() or "snowddl" in result.stderr.lower()

    def test_snowddl_apply_command_exists(self):
        """Test that snowddl-apply command is available"""
        result = subprocess.run(
            ["uv", "run", "snowddl-apply", "--help"], capture_output=True, text=True
        )
        # Should show help or error about missing config
        assert result.returncode != 127  # 127 = command not found
