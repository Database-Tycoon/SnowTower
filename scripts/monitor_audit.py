#!/usr/bin/env python3
"""
Audit Trail Viewer Script for SnowTower

Query and display audit events.

Usage:
    uv run monitor-audit
    uv run monitor-audit --action user_create
    uv run monitor-audit --resource-type user
    uv run monitor-audit --actor john_doe
    uv run monitor-audit --days 7
    uv run monitor-audit --compliance-report
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowtower_core.audit import get_audit_logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def display_audit_events(events: list, limit: int = 50):
    """Display audit events in a table"""

    if not events:
        console.print("[yellow]No audit events found[/yellow]")
        return

    table = Table(
        title=f"Audit Events ({len(events)} total, showing {min(len(events), limit)})"
    )
    table.add_column("Timestamp", style="dim", width=20)
    table.add_column("Action", style="cyan", width=20)
    table.add_column("Resource", style="white", width=25)
    table.add_column("Actor", style="green", width=15)
    table.add_column("Status", width=10)

    for event in events[:limit]:
        timestamp = event.timestamp
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

        status_style = "green" if event.status == "success" else "red"
        resource = f"{event.resource_type}:{event.resource_id}"

        table.add_row(
            timestamp,
            event.action,
            resource[:24] if len(resource) > 24 else resource,
            event.actor,
            f"[{status_style}]{event.status}[/{status_style}]",
        )

    console.print(table)


def display_compliance_report(report: dict):
    """Display compliance report"""

    console.print(
        Panel(
            f"Compliance Report\n{report['period']['start']} to {report['period']['end']}",
            style="bold cyan",
        )
    )

    # Summary
    console.print(f"\n[bold]Total Events:[/bold] {report['total_events']}")

    # By action
    if report["by_action"]:
        action_table = Table(title="Events by Action")
        action_table.add_column("Action", style="cyan")
        action_table.add_column("Count", style="white", justify="right")

        for action, count in sorted(
            report["by_action"].items(), key=lambda x: x[1], reverse=True
        ):
            action_table.add_row(action, str(count))

        console.print(action_table)

    # By actor
    if report["by_actor"]:
        actor_table = Table(title="Events by Actor")
        actor_table.add_column("Actor", style="cyan")
        actor_table.add_column("Count", style="white", justify="right")

        for actor, count in sorted(
            report["by_actor"].items(), key=lambda x: x[1], reverse=True
        )[:10]:
            actor_table.add_row(actor, str(count))

        console.print(actor_table)

    # Security events
    if report["security_events"]:
        console.print(
            f"\n[bold yellow]⚠️  Security Events: {len(report['security_events'])}[/bold yellow]"
        )

    # Failed operations
    if report["failed_operations"]:
        console.print(
            f"[bold red]❌ Failed Operations: {len(report['failed_operations'])}[/bold red]"
        )


def main():
    parser = argparse.ArgumentParser(description="View SnowTower audit trail")
    parser.add_argument("--action", "-a", help="Filter by action")
    parser.add_argument("--resource-type", "-r", help="Filter by resource type")
    parser.add_argument("--resource-id", help="Filter by resource ID")
    parser.add_argument("--actor", help="Filter by actor")
    parser.add_argument(
        "--status", "-s", choices=["success", "failure"], help="Filter by status"
    )
    parser.add_argument(
        "--days", "-d", type=int, default=7, help="Days to look back (default: 7)"
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Maximum events to display"
    )
    parser.add_argument(
        "--compliance-report",
        "-c",
        action="store_true",
        help="Generate compliance report",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        audit_logger = get_audit_logger()

        start_date = datetime.utcnow() - timedelta(days=args.days)
        end_date = datetime.utcnow()

        if args.compliance_report:
            # Generate compliance report
            report = audit_logger.get_compliance_report(start_date, end_date)

            if args.json:
                print(json.dumps(report, indent=2))
            else:
                display_compliance_report(report)
        else:
            # Query events
            events = audit_logger.query_events(
                start_date=start_date,
                action=args.action,
                resource_type=args.resource_type,
                resource_id=args.resource_id,
                actor=args.actor,
                status=args.status,
                limit=args.limit * 2,  # Query more, display subset
            )

            if args.json:
                print(json.dumps([e.to_dict() for e in events[: args.limit]], indent=2))
            else:
                display_audit_events(events, limit=args.limit)

    except Exception as e:
        console.print(f"[red]Error querying audit trail: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
