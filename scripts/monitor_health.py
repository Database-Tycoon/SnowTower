#!/usr/bin/env python3
"""
System Health Monitoring Script for SnowTower

Checks system health and displays current status including:
- Metrics summary
- Recent errors
- Audit log statistics
- Alert status
- Resource health

Usage:
    uv run monitor-health
    uv run monitor-health --json
    uv run monitor-health --detailed
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowtower_core.logging import get_logger, setup_logging
from snowtower_core.metrics import get_metrics
from snowtower_core.audit import get_audit_logger
from snowtower_core.alerts import get_alert_manager
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()
logger = get_logger(__name__)


def check_logging_health() -> dict:
    """Check logging system health"""
    log_dir = Path.cwd() / "logs"

    status = {"status": "healthy", "log_dir_exists": log_dir.exists(), "log_files": []}

    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        status["log_files"] = [f.name for f in log_files]
        status["log_file_count"] = len(log_files)

        # Check if logs are recent
        if log_files:
            latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
            latest_time = datetime.fromtimestamp(latest_log.stat().st_mtime)
            hours_old = (datetime.now() - latest_time).total_seconds() / 3600

            if hours_old > 24:
                status["status"] = "warning"
                status["warning"] = f"Latest log is {hours_old:.1f} hours old"
    else:
        status["status"] = "warning"
        status["warning"] = "Log directory does not exist"

    return status


def check_audit_health() -> dict:
    """Check audit system health"""
    audit_dir = Path.cwd() / "logs" / "audit"

    status = {
        "status": "healthy",
        "audit_dir_exists": audit_dir.exists(),
        "audit_files": [],
    }

    if audit_dir.exists():
        audit_files = list(audit_dir.glob("audit_*.csv")) + list(
            audit_dir.glob("audit_*.jsonl")
        )
        status["audit_files"] = [f.name for f in audit_files]
        status["audit_file_count"] = len(audit_files)

        # Get recent event count
        if audit_files:
            audit_logger = get_audit_logger()
            recent_events = audit_logger.get_recent_events(hours=24)
            status["events_last_24h"] = len(recent_events)
    else:
        status["status"] = "info"
        status["info"] = "Audit directory does not exist yet"

    return status


def check_metrics_health() -> dict:
    """Check metrics system health"""
    metrics = get_metrics()

    summary = metrics.get_summary()

    status = {
        "status": "healthy",
        "operations": summary.get("operations", {}),
        "users": summary.get("users", {}),
        "errors": summary.get("errors", {}),
    }

    # Check error rates
    total_ops = summary.get("operations", {}).get("total", 0)
    failed_ops = summary.get("operations", {}).get("failed", 0)

    if total_ops > 0:
        error_rate = (failed_ops / total_ops) * 100
        status["error_rate_percent"] = round(error_rate, 2)

        if error_rate > 10:
            status["status"] = "warning"
            status["warning"] = f"High error rate: {error_rate:.1f}%"
        elif error_rate > 25:
            status["status"] = "critical"
            status["warning"] = f"Critical error rate: {error_rate:.1f}%"

    return status


def check_alert_health() -> dict:
    """Check alerting system health"""
    alert_mgr = get_alert_manager()

    status = {
        "status": "healthy",
        "channel_count": len(alert_mgr.channels),
        "channels": [channel.get_name() for channel in alert_mgr.channels],
        "recent_alerts": len(alert_mgr.alert_history),
    }

    # Get recent alerts
    recent = alert_mgr.get_recent_alerts(hours=24)
    status["alerts_last_24h"] = len(recent)

    critical_alerts = [a for a in recent if a.severity.value == "critical"]
    if critical_alerts:
        status["status"] = "warning"
        status["warning"] = f"{len(critical_alerts)} critical alerts in last 24h"
        status["critical_alerts"] = len(critical_alerts)

    return status


def display_health_summary(detailed: bool = False):
    """Display health summary in rich format"""
    console.print(
        Panel(
            Text("SnowTower System Health Check", style="bold cyan"),
            subtitle=f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
        )
    )

    # Check all subsystems
    checks = {
        "Logging": check_logging_health(),
        "Audit Trail": check_audit_health(),
        "Metrics": check_metrics_health(),
        "Alerting": check_alert_health(),
    }

    # Summary table
    table = Table(title="System Components")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    overall_status = "healthy"

    for component, status_info in checks.items():
        status = status_info["status"]

        # Determine status color
        if status == "healthy":
            status_color = "green"
        elif status == "warning":
            status_color = "yellow"
            overall_status = (
                "warning" if overall_status == "healthy" else overall_status
            )
        elif status == "critical":
            status_color = "red"
            overall_status = "critical"
        else:
            status_color = "blue"

        # Get details
        details = []
        if "warning" in status_info:
            details.append(status_info["warning"])
        if "info" in status_info:
            details.append(status_info["info"])

        details_str = "; ".join(details) if details else "All systems operational"

        table.add_row(
            component, f"[{status_color}]{status.upper()}[/{status_color}]", details_str
        )

    console.print(table)

    # Detailed information if requested
    if detailed:
        console.print("\n[bold cyan]Detailed Information:[/bold cyan]\n")

        # Metrics details
        metrics_status = checks["Metrics"]
        if metrics_status["operations"]:
            ops_table = Table(title="Operations Metrics")
            ops_table.add_column("Metric", style="cyan")
            ops_table.add_column("Value", style="white")

            ops_table.add_row(
                "Total Operations", str(metrics_status["operations"].get("total", 0))
            )
            ops_table.add_row(
                "Failed Operations", str(metrics_status["operations"].get("failed", 0))
            )
            ops_table.add_row(
                "Error Rate", f"{metrics_status.get('error_rate_percent', 0):.2f}%"
            )

            console.print(ops_table)

        # User metrics
        if metrics_status["users"]:
            users_table = Table(title="User Management Metrics")
            users_table.add_column("Metric", style="cyan")
            users_table.add_column("Value", style="white")

            users_table.add_row(
                "Users Created", str(metrics_status["users"].get("created", 0))
            )
            users_table.add_row(
                "Users Updated", str(metrics_status["users"].get("updated", 0))
            )
            users_table.add_row(
                "Users Deleted", str(metrics_status["users"].get("deleted", 0))
            )
            users_table.add_row(
                "Active Users", str(metrics_status["users"].get("active", 0))
            )

            console.print(users_table)

        # Recent alerts
        alert_status = checks["Alerting"]
        if alert_status["alerts_last_24h"] > 0:
            console.print(
                f"\n[yellow]⚠️  {alert_status['alerts_last_24h']} alerts in last 24 hours[/yellow]"
            )

        # Audit statistics
        audit_status = checks["Audit Trail"]
        if "events_last_24h" in audit_status:
            console.print(
                f"\n[blue]📋 {audit_status['events_last_24h']} audit events in last 24 hours[/blue]"
            )

    # Overall status
    console.print()
    if overall_status == "healthy":
        console.print("[bold green]✅ All systems healthy[/bold green]")
    elif overall_status == "warning":
        console.print("[bold yellow]⚠️  System warnings detected[/bold yellow]")
    else:
        console.print("[bold red]❌ Critical issues detected[/bold red]")

    return checks


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Check SnowTower system health")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--detailed", "-d", action="store_true", help="Show detailed information"
    )

    args = parser.parse_args()

    try:
        # Setup logging
        setup_logging(log_level="INFO", log_to_console=False)

        if args.json:
            # JSON output
            checks = {
                "timestamp": datetime.now().isoformat(),
                "logging": check_logging_health(),
                "audit": check_audit_health(),
                "metrics": check_metrics_health(),
                "alerting": check_alert_health(),
            }
            print(json.dumps(checks, indent=2))
        else:
            # Rich console output
            display_health_summary(detailed=args.detailed)

    except Exception as e:
        console.print(f"[red]Error checking system health: {e}[/red]")
        logger.error(f"Health check failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
