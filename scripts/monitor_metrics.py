#!/usr/bin/env python3
"""
Metrics Viewer Script for SnowTower

Display operational metrics and statistics.

Usage:
    uv run monitor-metrics
    uv run monitor-metrics --prometheus
    uv run monitor-metrics --json
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowtower_core.metrics import get_metrics
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def display_metrics_summary():
    """Display metrics summary"""
    metrics = get_metrics()
    summary = metrics.get_summary()

    console.print(
        Panel(
            "SnowTower Operational Metrics",
            style="bold cyan",
            subtitle=f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
        )
    )

    # Operations
    ops_table = Table(title="Operations")
    ops_table.add_column("Metric", style="cyan")
    ops_table.add_column("Value", style="white", justify="right")

    total_ops = summary["operations"].get("total", 0)
    failed_ops = summary["operations"].get("failed", 0)
    error_rate = (failed_ops / total_ops * 100) if total_ops > 0 else 0

    ops_table.add_row("Total Operations", str(total_ops))
    ops_table.add_row("Failed Operations", str(failed_ops))
    ops_table.add_row("Success Rate", f"{100 - error_rate:.1f}%")

    console.print(ops_table)

    # Users
    if any(summary["users"].values()):
        users_table = Table(title="User Management")
        users_table.add_column("Metric", style="cyan")
        users_table.add_column("Value", style="white", justify="right")

        users_table.add_row("Users Created", str(summary["users"].get("created", 0)))
        users_table.add_row("Users Updated", str(summary["users"].get("updated", 0)))
        users_table.add_row("Users Deleted", str(summary["users"].get("deleted", 0)))
        users_table.add_row("Active Users", str(summary["users"].get("active", 0)))

        console.print(users_table)

    # SnowDDL
    if any(summary["snowddl"].values()):
        snowddl_table = Table(title="SnowDDL Operations")
        snowddl_table.add_column("Metric", style="cyan")
        snowddl_table.add_column("Value", style="white", justify="right")

        snowddl_table.add_row("Plans", str(summary["snowddl"].get("plans", 0)))
        snowddl_table.add_row("Applies", str(summary["snowddl"].get("applies", 0)))
        snowddl_table.add_row(
            "Changes Applied", str(summary["snowddl"].get("changes_applied", 0))
        )

        console.print(snowddl_table)

    # Errors
    if summary["errors"].get("total", 0) > 0:
        console.print(
            f"\n[yellow]⚠️  Total Errors: {summary['errors']['total']}[/yellow]"
        )

    # Authentication
    if summary["authentication"].get("attempts", 0) > 0:
        auth_failures = summary["authentication"].get("failures", 0)
        auth_attempts = summary["authentication"].get("attempts", 0)
        auth_success_rate = (
            ((auth_attempts - auth_failures) / auth_attempts * 100)
            if auth_attempts > 0
            else 100
        )

        console.print(
            f"\n[blue]🔐 Authentication Success Rate: {auth_success_rate:.1f}%[/blue]"
        )
        if auth_failures > 0:
            console.print(f"   Failures: {auth_failures}")


def main():
    parser = argparse.ArgumentParser(description="View SnowTower metrics")
    parser.add_argument(
        "--prometheus", "-p", action="store_true", help="Output in Prometheus format"
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        metrics = get_metrics()

        if args.prometheus:
            # Prometheus format
            print(metrics.export_prometheus())
        elif args.json:
            # JSON format
            print(json.dumps(metrics.export_json(), indent=2))
        else:
            # Rich console format
            display_metrics_summary()

    except Exception as e:
        console.print(f"[red]Error retrieving metrics: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
