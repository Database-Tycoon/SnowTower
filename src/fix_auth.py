#!/usr/bin/env python3
"""
Authentication Fix Script for SnowTower SnowDDL

This script helps fix authentication issues by testing different methods
and providing specific configuration recommendations.

Usage:
    python fix_auth.py
    uv run fix-auth
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    from dotenv import load_dotenv
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
except ImportError as e:
    print(f"ERROR: Missing required dependencies: {e}")
    print("Please run: uv sync")
    exit(1)


def main():
    """Main authentication fix function."""
    console = Console()

    console.print(
        Panel(
            "Authentication Fix Wizard for SnowTower SnowDDL\n"
            "This wizard will help diagnose and fix authentication issues.",
            title="🔧 Auth Fix Wizard",
            border_style="blue",
        )
    )

    # Load current environment
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    current_config = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "private_key_path": os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
    }

    console.print("[bold blue]Current Configuration:[/bold blue]")
    console.print(f"Account: {current_config['account']}")
    console.print(f"User: {current_config['user']}")
    console.print(f"Role: {current_config['role']}")
    console.print(f"Warehouse: {current_config['warehouse']}")
    console.print(f"Private Key: {current_config['private_key_path'] or 'Not set'}")
    console.print(f"Password: {'Set' if current_config['password'] else 'Not set'}")

    # Check snow CLI connections
    console.print("\n[bold blue]Checking Snow CLI Connections...[/bold blue]")
    try:
        result = subprocess.run(
            ["snow", "connection", "list"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            console.print("[green]Available Connections:[/green]")
            console.print(result.stdout)

            # Test each connection
            console.print("\n[bold blue]Testing Connections...[/bold blue]")
            connections = parse_connections(result.stdout)
            working_connections = []

            for conn_name in connections:
                console.print(f"Testing connection: {conn_name}")
                test_result = subprocess.run(
                    [
                        "snow",
                        "sql",
                        "-c",
                        conn_name,
                        "-q",
                        "SELECT CURRENT_USER(), CURRENT_ROLE()",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if test_result.returncode == 0:
                    console.print(f"[green]✓[/green] {conn_name} - Working")
                    working_connections.append(conn_name)
                    console.print(f"  Result: {test_result.stdout.strip()}")
                else:
                    console.print(f"[red]✗[/red] {conn_name} - Failed")
                    console.print(f"  Error: {test_result.stderr.strip()}")

            # Provide recommendations
            if working_connections:
                console.print(
                    f"\n[green]Found {len(working_connections)} working connection(s)![/green]"
                )
                console.print("\n[bold]Recommendations:[/bold]")

                console.print("1. **Use a working snow CLI connection for SnowDDL:**")
                for conn in working_connections:
                    console.print(f"   - {conn}")

                console.print("\n2. **Set up SnowDDL to use the same authentication:**")
                console.print(
                    "   Option A: Update your .env file to match a working connection"
                )
                console.print(
                    "   Option B: Create a new snow CLI connection specifically for SnowDDL"
                )

                if Confirm.ask(
                    "\nWould you like to create a new snow CLI connection for SnowDDL?"
                ):
                    create_snowddl_connection(console, current_config)

                if Confirm.ask("\nWould you like to test SnowDDL connectivity now?"):
                    test_snowddl_connectivity(console)

            else:
                console.print("\n[red]No working connections found![/red]")
                console.print("\n[bold]Next Steps:[/bold]")
                console.print("1. Create a new snow CLI connection:")
                console.print("   snow connection add")
                console.print("2. Test the connection:")
                console.print("   snow sql -q 'SELECT CURRENT_USER()'")
                console.print(
                    "3. Update your .env file to match the working connection"
                )

        else:
            console.print("[red]Failed to list snow CLI connections[/red]")
            console.print(f"Error: {result.stderr}")

    except Exception as e:
        console.print(f"[red]Error checking snow CLI: {e}[/red]")

    # Final recommendations
    console.print("\n[bold blue]Summary & Next Steps:[/bold blue]")
    console.print(
        Panel(
            """1. Ensure you have a working snow CLI connection
2. Update .env file to match working connection credentials
3. Test with: uv run investigate-monitors --mode connectivity
4. If still failing, try password authentication instead of RSA keys
5. Contact admin if user account needs key registration in Snowflake""",
            title="🎯 Action Plan",
            border_style="green",
        )
    )


def parse_connections(output: str) -> list:
    """Parse connection names from snow connection list output."""
    connections = []
    lines = output.split("\n")
    for line in lines:
        if "|" in line and "connection_name" not in line and line.strip():
            parts = line.split("|")
            if len(parts) > 0:
                conn_name = parts[0].strip()
                if conn_name and conn_name not in ["-", "+"]:
                    connections.append(conn_name)
    return connections


def create_snowddl_connection(console: Console, current_config: Dict[str, Any]) -> None:
    """Guide user through creating a SnowDDL-specific connection."""
    console.print("\n[bold blue]Creating SnowDDL Connection...[/bold blue]")

    console.print("This will create a new snow CLI connection called 'snowddl'")
    console.print("Using your current .env configuration:")
    console.print(f"Account: {current_config['account']}")
    console.print(f"User: {current_config['user']}")
    console.print(f"Role: {current_config['role']}")

    auth_method = Prompt.ask(
        "Choose authentication method",
        choices=["password", "rsa_key"],
        default="rsa_key",
    )

    if auth_method == "password":
        if not current_config["password"]:
            console.print("[red]No password set in .env file![/red]")
            console.print("Add SNOWFLAKE_PASSWORD to your .env file first")
            return

        cmd = [
            "snow",
            "connection",
            "add",
            "--connection-name",
            "snowddl",
            "--account",
            current_config["account"],
            "--user",
            current_config["user"],
            "--password",
            current_config["password"],
        ]

        if current_config["role"]:
            cmd.extend(["--role", current_config["role"]])
        if current_config["warehouse"]:
            cmd.extend(["--warehouse", current_config["warehouse"]])

    else:  # RSA key
        if not current_config["private_key_path"]:
            console.print("[red]No private key path set in .env file![/red]")
            console.print("Add SNOWFLAKE_PRIVATE_KEY_PATH to your .env file first")
            return

        cmd = [
            "snow",
            "connection",
            "add",
            "--connection-name",
            "snowddl",
            "--account",
            current_config["account"],
            "--user",
            current_config["user"],
            "--private-key-path",
            current_config["private_key_path"],
        ]

        if current_config["role"]:
            cmd.extend(["--role", current_config["role"]])
        if current_config["warehouse"]:
            cmd.extend(["--warehouse", current_config["warehouse"]])

    console.print(f"\nRunning: {' '.join(cmd[:8])}... [hidden credentials]")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            console.print("[green]✓[/green] Connection created successfully!")
            console.print("Testing new connection...")

            test_result = subprocess.run(
                [
                    "snow",
                    "sql",
                    "-c",
                    "snowddl",
                    "-q",
                    "SELECT CURRENT_USER(), CURRENT_ROLE()",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if test_result.returncode == 0:
                console.print("[green]✓[/green] New connection works!")
                console.print(f"Result: {test_result.stdout.strip()}")
            else:
                console.print("[red]✗[/red] New connection failed")
                console.print(f"Error: {test_result.stderr}")
        else:
            console.print("[red]✗[/red] Failed to create connection")
            console.print(f"Error: {result.stderr}")

    except Exception as e:
        console.print(f"[red]Error creating connection: {e}[/red]")


def test_snowddl_connectivity(console: Console) -> None:
    """Test SnowDDL connectivity using the investigation script."""
    console.print("\n[bold blue]Testing SnowDDL Connectivity...[/bold blue]")

    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "investigate-monitors",
                "--mode",
                "connectivity",
                "--output-format",
                "human",
            ],
            timeout=60,
        )

        if result.returncode == 0:
            console.print("[green]✓[/green] SnowDDL connectivity test passed!")
        else:
            console.print("[red]✗[/red] SnowDDL connectivity test failed")
            console.print("Check the output above for details")

    except Exception as e:
        console.print(f"[red]Error running connectivity test: {e}[/red]")


if __name__ == "__main__":
    main()
