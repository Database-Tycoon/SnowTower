#!/usr/bin/env python3
"""
Management CLI wrapper for SnowDDL management scripts.

This module provides entry points for all management commands.
"""

import sys
from pathlib import Path

# Add the parent directory to the path to access scripts
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def warehouses():
    """Run warehouse management commands."""
    from manage_warehouses import main

    main()


def costs():
    """Run cost optimization commands."""
    from cost_optimization import main

    main()


def security():
    """Run security audit commands."""
    from security_audit import main

    main()


def backup():
    """Run backup and restore commands."""
    from backup_restore import main

    main()


def users():
    """Run user management commands."""
    from manage_users import main

    main()


def apply_schema_grants():
    """Apply schema-level USAGE grants that SnowDDL cannot manage."""
    from apply_schema_grants import main

    main()


def validate_schema_grants():
    """Validate schema grants consistency between tech_role.yaml and apply_schema_grants.py."""
    from validate_schema_grants import main

    main()


def process_access_request():
    """Process GitHub issue access requests."""
    from generate_user_from_issue import main

    main()


def snowddl_plan():
    """Run SnowDDL plan command."""
    # Add src directory to path if not already there
    import sys
    from pathlib import Path

    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from snowtower_snowddl.cli import plan

    plan()


def snowddl_validate():
    """Run SnowDDL validate command."""
    # Add src directory to path if not already there
    import sys
    from pathlib import Path

    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from snowtower_snowddl.cli import validate_config

    validate_config()


def snowddl_apply():
    """Run SnowDDL apply command."""
    # Add src directory to path if not already there
    import sys
    from pathlib import Path

    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from snowtower_snowddl.cli import apply

    apply()


def snowddl_diff():
    """Run SnowDDL diff command."""
    # Add src directory to path if not already there
    import sys
    from pathlib import Path

    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from snowtower_snowddl.cli import diff

    diff()


def snowddl_lint():
    """Run SnowDDL lint command."""
    # Add src directory to path if not already there
    import sys
    from pathlib import Path

    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from snowtower_snowddl.cli import lint_config

    lint_config()


def update_user_password():
    """Update user password safely."""
    # Add src directory to path if not already there
    import sys
    from pathlib import Path

    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from snowtower_snowddl.cli import update_user_password

    update_user_password()


# === CONFIGURATION VALIDATION ===


def validate_config():
    """Validate SnowDDL YAML configuration files before deployment."""
    from validate_config import main

    main()


# === STREAMLIT TESTING COMMANDS ===


def validate_streamlit():
    """Run comprehensive pre-deployment validation for Streamlit apps."""
    from validate_streamlit import main

    main()


# === REMOVED FUNCTIONS (Missing Implementations) ===
# The following functions were removed because their scripts don't exist:
# - test_s3_deployment() - missing scripts/test_s3_deployment.py
# - test_streamlit_local() - missing implementation
# - test_streamlit_deployed() - missing implementation
# - deploy_streamlit_safe() - missing implementation
# - detect_streamlit_errors() - missing scripts/common_streamlit_errors.py


def user_create():
    """Unified user creation command (consolidated from multiple scripts)."""
    from user_create import main

    main()


# === MONITORING COMMANDS ===


def monitor_health():
    """Check system health and display status."""
    from monitor_health import main

    main()


def monitor_logs():
    """View and filter structured logs."""
    from monitor_logs import main

    main()


def monitor_audit():
    """Query and display audit trail events."""
    from monitor_audit import main

    main()


def monitor_metrics():
    """Display operational metrics and statistics."""
    from monitor_metrics import main

    main()


# === AUTOMATION COMMANDS ===


def github_to_snowddl():
    """Automate GitHub issue to SnowDDL user deployment with PR creation."""
    from github_issue_to_snowddl import main

    main()


def generate_terraform():
    """Generate Terraform HCL files from SnowDDL YAML configurations."""
    from generate_terraform import main

    main()


if __name__ == "__main__":
    print("Use 'uv run <command>' where command includes:")
    print("  Core: warehouses, costs, security, backup, users")
    print("  SnowDDL: snowddl-plan, snowddl-apply, snowddl-validate")
    print("  User Management: user-create (unified), manage-users (full CLI)")
    print("  Monitoring: monitor-health, monitor-logs, monitor-audit, monitor-metrics")
    print("  Streamlit: validate-streamlit, web, deploy-streamlit")
    print("  Automation: github-to-snowddl (GitHub issue -> SnowDDL PR)")
