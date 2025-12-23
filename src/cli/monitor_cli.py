#!/usr/bin/env python3
"""
Consolidated monitoring CLI.

Usage:
    uv run monitor health    # System health checks
    uv run monitor audit     # Audit trail analysis
    uv run monitor metrics   # Operational metrics
    uv run monitor logs      # Log analysis
"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def show_help():
    """Show monitor command help."""
    print(
        """
Monitor - System Monitoring & Observability

Usage: uv run monitor <subcommand>

Subcommands:
    health     System health checks and status
    audit      Query and display audit trail events
    metrics    Display operational metrics and statistics
    logs       View and filter structured logs

Examples:
    uv run monitor health
    uv run monitor audit
    uv run monitor metrics
    uv run monitor logs

For detailed help on a subcommand:
    uv run monitor <subcommand> --help
"""
    )


def main():
    """Route to appropriate monitoring subcommand."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    subcommand = sys.argv[1].lower()

    # Remove the subcommand from argv so the underlying script sees correct args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if subcommand in ("health", "h"):
        from monitor_health import main as health_main

        health_main()
    elif subcommand in ("audit", "a"):
        from monitor_audit import main as audit_main

        audit_main()
    elif subcommand in ("metrics", "m"):
        from monitor_metrics import main as metrics_main

        metrics_main()
    elif subcommand in ("logs", "l"):
        from monitor_logs import main as logs_main

        logs_main()
    elif subcommand in ("--help", "-h", "help"):
        show_help()
    else:
        print(f"Unknown subcommand: {subcommand}")
        print("Run 'uv run monitor --help' for available subcommands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
