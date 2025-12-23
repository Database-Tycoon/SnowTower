#!/usr/bin/env python3
"""
Log Viewer Script for SnowTower

View and filter structured logs.

Usage:
    uv run monitor-logs
    uv run monitor-logs --level ERROR
    uv run monitor-logs --operation user_creation
    uv run monitor-logs --tail 50
    uv run monitor-logs --since "2024-01-01"
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

console = Console()


def parse_log_line(line: str) -> dict:
    """Parse JSON log line"""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"message": line.strip(), "level": "UNKNOWN"}


def display_logs(
    log_file: Path,
    level: str = None,
    operation: str = None,
    tail: int = None,
    since: str = None,
    follow: bool = False,
):
    """Display logs with filters"""

    if not log_file.exists():
        console.print(f"[yellow]Log file not found: {log_file}[/yellow]")
        return

    since_dt = datetime.fromisoformat(since) if since else None

    table = Table(title=f"Logs from {log_file.name}")
    table.add_column("Timestamp", style="dim", width=20)
    table.add_column("Level", width=10)
    table.add_column("Logger", style="cyan", width=20)
    table.add_column("Message", style="white")

    lines = []
    with open(log_file, "r") as f:
        for line in f:
            if not line.strip():
                continue

            log_entry = parse_log_line(line)

            # Apply filters
            if level and log_entry.get("level") != level:
                continue

            if operation and log_entry.get("operation") != operation:
                continue

            if since_dt:
                try:
                    log_time = datetime.fromisoformat(
                        log_entry.get("timestamp", "").replace("Z", "+00:00")
                    )
                    if log_time < since_dt:
                        continue
                except:
                    pass

            lines.append(log_entry)

    # Apply tail limit
    if tail:
        lines = lines[-tail:]

    # Display
    for log_entry in lines:
        level_style = {
            "DEBUG": "dim",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
        }.get(log_entry.get("level", "UNKNOWN"), "white")

        timestamp = log_entry.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

        table.add_row(
            timestamp,
            f"[{level_style}]{log_entry.get('level', 'UNKNOWN')}[/{level_style}]",
            log_entry.get("logger", "")[:18],
            log_entry.get("message", "")[:60],
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="View SnowTower logs")
    parser.add_argument(
        "--level",
        "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Filter by log level",
    )
    parser.add_argument("--operation", "-o", help="Filter by operation name")
    parser.add_argument(
        "--tail",
        "-n",
        type=int,
        default=100,
        help="Number of lines to show (default: 100)",
    )
    parser.add_argument("--since", "-s", help="Show logs since datetime (ISO format)")
    parser.add_argument(
        "--file", "-f", help="Log file to read (default: logs/snowtower.log)"
    )

    args = parser.parse_args()

    log_file = Path(args.file) if args.file else Path.cwd() / "logs" / "snowtower.log"

    try:
        display_logs(
            log_file=log_file,
            level=args.level,
            operation=args.operation,
            tail=args.tail,
            since=args.since,
        )
    except Exception as e:
        console.print(f"[red]Error viewing logs: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
