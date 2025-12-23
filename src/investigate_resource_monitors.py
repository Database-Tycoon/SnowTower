#!/usr/bin/env python3
"""
Resource Monitor Investigation Script for SnowTower SnowDDL

This script investigates critical resource monitor deployment safety issues by:
1. Testing Snowflake CLI connectivity
2. Analyzing existing resource monitors and warehouse configurations
3. Assessing credit usage patterns and safety of proposed limits
4. Providing actionable deployment recommendations

Usage:
    python investigate_resource_monitors.py [--mode={full|connectivity|monitors|warehouses|credits|safety}]
    python investigate_resource_monitors.py --output-format={json|human|both}
    python investigate_resource_monitors.py --save-results
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from env_loader import (
        load_snowflake_env,
        validate_auth,
        EnvironmentError,
        AuthenticationError,
    )
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.logging import RichHandler
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError as e:
    print(f"ERROR: Missing required dependencies: {e}")
    print("Please run: uv sync")
    sys.exit(1)


class ResourceMonitorInvestigator:
    """Comprehensive resource monitor safety investigation tool."""

    def __init__(self, console: Console):
        self.console = console
        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "investigation_id": f"rm_investigation_{int(datetime.now().timestamp())}",
            "status": "started",
            "tests": {},
            "warnings": [],
            "recommendations": [],
            "safe_to_deploy": None,
            "error_details": [],
        }
        self.setup_logging()
        self.load_environment()

    def setup_logging(self) -> None:
        """Setup structured logging with rich formatting."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[
                RichHandler(console=self.console, rich_tracebacks=True, show_path=False)
            ],
        )
        self.logger = logging.getLogger("resource_monitor_investigator")

    def load_environment(self) -> None:
        """Load and validate environment configuration using env_loader utility."""
        try:
            # Use the reliable env_loader utility
            env_vars = load_snowflake_env(validate_auth=True)

            self.env_config = {
                "account": env_vars.get("SNOWFLAKE_ACCOUNT"),
                "user": env_vars.get("SNOWFLAKE_USER"),
                "role": env_vars.get("SNOWFLAKE_ROLE"),
                "warehouse": env_vars.get("SNOWFLAKE_WAREHOUSE"),
                "auth_method": "rsa_key"
                if env_vars.get("SNOWFLAKE_PRIVATE_KEY_PATH")
                else "password",
            }

            self.logger.info(
                f"Environment loaded successfully: {self.env_config['account']}/{self.env_config['user']}"
            )
            self.logger.info(f"Authentication method: {self.env_config['auth_method']}")

        except (EnvironmentError, AuthenticationError) as e:
            self.add_error("Environment configuration error", str(e))
            self.logger.error(f"Failed to load environment: {str(e)}")
        except Exception as e:
            self.add_error(
                "Unexpected environment error", f"Error loading environment: {str(e)}"
            )
            self.logger.error(f"Unexpected error in environment loading: {str(e)}")

    def add_error(self, error_type: str, details: str) -> None:
        """Add error to results with logging."""
        error_entry = {
            "type": error_type,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.results["error_details"].append(error_entry)
        self.logger.error(f"[red]{error_type}:[/red] {details}")

    def add_warning(self, warning: str) -> None:
        """Add warning to results with logging."""
        self.results["warnings"].append(
            {"message": warning, "timestamp": datetime.now().isoformat()}
        )
        self.logger.warning(f"[yellow]WARNING:[/yellow] {warning}")

    def add_recommendation(self, recommendation: str, priority: str = "medium") -> None:
        """Add recommendation to results."""
        self.results["recommendations"].append(
            {
                "message": recommendation,
                "priority": priority,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def execute_snow_command(
        self, command: List[str], timeout: int = 30
    ) -> Tuple[bool, str, str]:
        """
        Safely execute snow CLI command with proper error handling.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            full_command = ["snow"] + command
            self.logger.debug(f"Executing: {' '.join(full_command)}")

            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path(__file__).parent.parent,
            )

            success = result.returncode == 0
            if not success:
                self.logger.debug(f"Command failed with code {result.returncode}")
                self.logger.debug(f"STDERR: {result.stderr}")

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            self.add_error("Command timeout", error_msg)
            return False, "", error_msg
        except FileNotFoundError:
            error_msg = "snow CLI not found in PATH"
            self.add_error("CLI not found", error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Unexpected error executing command: {str(e)}"
            self.add_error("Command execution error", error_msg)
            return False, "", error_msg

    def test_connectivity(self) -> bool:
        """Test basic Snowflake connectivity using snow CLI."""
        self.console.print("[bold blue]Testing Snowflake Connectivity...[/bold blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Connecting to Snowflake...", total=None)

            # First, check available connections
            conn_success, conn_stdout, conn_stderr = self.execute_snow_command(
                ["connection", "list"]
            )

            # Test basic connection with simple query
            success, stdout, stderr = self.execute_snow_command(
                [
                    "sql",
                    "-q",
                    "SELECT CURRENT_VERSION() as VERSION, CURRENT_USER() as USER, CURRENT_ROLE() as ROLE",
                ]
            )

            # If default connection fails, try other connections
            if not success and conn_success:
                self.console.print(
                    "[yellow]Default connection failed, trying alternative connections...[/yellow]"
                )
                connections = self._parse_connections(conn_stdout)
                for conn_name in connections:
                    self.console.print(
                        f"[yellow]Trying connection: {conn_name}[/yellow]"
                    )
                    alt_success, alt_stdout, alt_stderr = self.execute_snow_command(
                        [
                            "sql",
                            "-c",
                            conn_name,
                            "-q",
                            "SELECT CURRENT_VERSION() as VERSION, CURRENT_USER() as USER, CURRENT_ROLE() as ROLE",
                        ]
                    )
                    if alt_success:
                        success, stdout, stderr = alt_success, alt_stdout, alt_stderr
                        self.add_recommendation(
                            f"Use connection '{conn_name}' for reliable access", "high"
                        )
                        break

            progress.stop()

        if success:
            self.results["tests"]["connectivity"] = {
                "status": "success",
                "details": "Successfully connected to Snowflake",
                "output": stdout.strip(),
                "available_connections": conn_stdout
                if conn_success
                else "Could not retrieve connections",
            }
            self.console.print("[green]✓[/green] Snowflake connectivity test passed")
            return True
        else:
            self.results["tests"]["connectivity"] = {
                "status": "failed",
                "details": f"Connection failed: {stderr}",
                "error": stderr,
                "available_connections": conn_stdout
                if conn_success
                else "Could not retrieve connections",
                "troubleshooting": self._generate_auth_troubleshooting(stderr),
            }
            self.console.print("[red]✗[/red] Snowflake connectivity test failed")
            self.add_error("Connectivity test failed", stderr)

            # Display troubleshooting information
            self._display_auth_troubleshooting(stderr)
            return False

    def _parse_connections(self, conn_output: str) -> List[str]:
        """Parse connection names from snow CLI output."""
        connections = []
        lines = conn_output.split("\n")
        for line in lines:
            if "|" in line and "connection_name" not in line:
                parts = line.split("|")
                if len(parts) > 0:
                    conn_name = parts[0].strip()
                    if conn_name and conn_name != "-":
                        connections.append(conn_name)
        return connections

    def _generate_auth_troubleshooting(self, error_msg: str) -> Dict[str, Any]:
        """Generate specific troubleshooting steps based on error message."""
        troubleshooting = {
            "error_type": "unknown",
            "likely_cause": "Unknown authentication issue",
            "recommended_actions": [],
        }

        if "JWT token is invalid" in error_msg:
            troubleshooting.update(
                {
                    "error_type": "jwt_authentication",
                    "likely_cause": "RSA private key authentication failure",
                    "recommended_actions": [
                        "Verify RSA private key file exists and is readable",
                        "Check if private key passphrase is required",
                        "Ensure public key is properly registered in Snowflake user settings",
                        "Regenerate RSA key pair if needed",
                        "Try password authentication as fallback",
                    ],
                }
            )
        elif "Incorrect username or password" in error_msg:
            troubleshooting.update(
                {
                    "error_type": "password_authentication",
                    "likely_cause": "Invalid username/password combination",
                    "recommended_actions": [
                        "Verify SNOWFLAKE_USER and authentication method in .env",
                        "Check if user account is locked or disabled",
                        "Verify account name (SNOWFLAKE_ACCOUNT) is correct",
                        "Test login through Snowflake web interface",
                        "Switch to RSA key authentication for service accounts",
                    ],
                }
            )
        elif "Failed to connect" in error_msg:
            troubleshooting.update(
                {
                    "error_type": "connection_failure",
                    "likely_cause": "Network or account configuration issue",
                    "recommended_actions": [
                        "Verify SNOWFLAKE_ACCOUNT value is correct",
                        "Check network connectivity to Snowflake",
                        "Verify account is active and not suspended",
                        "Check for regional-specific account URLs",
                    ],
                }
            )

        return troubleshooting

    def _display_auth_troubleshooting(self, error_msg: str) -> None:
        """Display authentication troubleshooting information."""
        troubleshooting = self._generate_auth_troubleshooting(error_msg)

        content = f"""
🔍 **Error Type:** {troubleshooting['error_type'].replace('_', ' ').title()}

🎯 **Likely Cause:** {troubleshooting['likely_cause']}

🔧 **Recommended Actions:**
"""
        for i, action in enumerate(troubleshooting["recommended_actions"], 1):
            content += f"\n   {i}. {action}"

        content += f"""

📋 **Quick Fixes to Try:**
   • Run: uv run diagnose-auth (for detailed auth analysis)
   • Check: snow connection list (see available connections)
   • Test: snow sql -c [connection_name] -q "SELECT 1" (test specific connection)
   • Verify: uv run test-env (check environment configuration)
"""

        self.console.print(
            Panel(content, title="🚨 Authentication Troubleshooting", border_style="red")
        )

    def check_existing_monitors(self) -> bool:
        """Check existing resource monitors in Snowflake."""
        self.console.print(
            "[bold blue]Checking Existing Resource Monitors...[/bold blue]"
        )

        # Query for existing resource monitors
        success, stdout, stderr = self.execute_snow_command(
            [
                "sql",
                "-q",
                """
            SELECT
                NAME,
                CREDIT_QUOTA,
                USED_CREDITS,
                REMAINING_CREDITS,
                LEVEL,
                FREQUENCY,
                START_TIME,
                END_TIME,
                SUSPEND_AT,
                SUSPEND_IMMEDIATELY_AT,
                NOTIFY_AT,
                NOTIFY_USERS,
                CREATED_ON,
                OWNER
            FROM SNOWFLAKE.ACCOUNT_USAGE.RESOURCE_MONITORS
            WHERE DELETED IS NULL
            ORDER BY CREATED_ON DESC
            """,
            ]
        )

        if success:
            self.results["tests"]["existing_monitors"] = {
                "status": "success",
                "details": "Successfully retrieved resource monitor information",
                "output": stdout.strip(),
            }

            # Parse and display results
            if stdout.strip():
                self.console.print("[green]✓[/green] Found existing resource monitors")
                self._display_monitor_table(stdout)
            else:
                self.console.print(
                    "[yellow]![/yellow] No existing resource monitors found"
                )
                self.add_warning("No existing resource monitors configured")

            return True
        else:
            self.results["tests"]["existing_monitors"] = {
                "status": "failed",
                "details": f"Failed to retrieve resource monitors: {stderr}",
                "error": stderr,
            }
            self.console.print(
                "[red]✗[/red] Failed to check existing resource monitors"
            )
            self.add_error("Monitor check failed", stderr)
            return False

    def analyze_warehouse_status(self) -> bool:
        """Analyze current warehouse configurations and resource monitor assignments."""
        self.console.print(
            "[bold blue]Analyzing Warehouse Configurations...[/bold blue]"
        )

        # Query warehouse information
        success, stdout, stderr = self.execute_snow_command(
            [
                "sql",
                "-q",
                """
            SELECT
                w.NAME,
                w.STATE,
                w.TYPE,
                w.SIZE,
                w.RUNNING,
                w.QUEUED,
                w.IS_DEFAULT,
                w.IS_CURRENT,
                w.AUTO_SUSPEND,
                w.AUTO_RESUME,
                w.RESOURCE_MONITOR,
                w.COMMENT,
                w.CREATED_ON,
                w.RESUMED_ON,
                w.UPDATED_ON
            FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSES w
            WHERE w.DELETED IS NULL
            ORDER BY w.CREATED_ON DESC
            """,
            ]
        )

        if success:
            self.results["tests"]["warehouse_analysis"] = {
                "status": "success",
                "details": "Successfully retrieved warehouse information",
                "output": stdout.strip(),
            }

            self.console.print("[green]✓[/green] Warehouse analysis completed")
            self._display_warehouse_table(stdout)
            return True
        else:
            self.results["tests"]["warehouse_analysis"] = {
                "status": "failed",
                "details": f"Failed to analyze warehouses: {stderr}",
                "error": stderr,
            }
            self.console.print("[red]✗[/red] Failed to analyze warehouses")
            self.add_error("Warehouse analysis failed", stderr)
            return False

    def analyze_credit_usage(self) -> bool:
        """Analyze recent credit usage patterns."""
        self.console.print("[bold blue]Analyzing Credit Usage Patterns...[/bold blue]")

        # Get credit usage for last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        success, stdout, stderr = self.execute_snow_command(
            [
                "sql",
                "-q",
                f"""
            SELECT
                DATE(START_TIME) as USAGE_DATE,
                WAREHOUSE_NAME,
                SUM(CREDITS_USED) as DAILY_CREDITS,
                COUNT(*) as QUERY_COUNT,
                AVG(CREDITS_USED) as AVG_CREDITS_PER_QUERY,
                MAX(CREDITS_USED) as MAX_CREDITS_SINGLE_QUERY
            FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
            WHERE START_TIME >= '{start_date.strftime('%Y-%m-%d')}'
              AND START_TIME <= '{end_date.strftime('%Y-%m-%d')}'
            GROUP BY DATE(START_TIME), WAREHOUSE_NAME
            ORDER BY USAGE_DATE DESC, DAILY_CREDITS DESC
            """,
            ]
        )

        if success:
            self.results["tests"]["credit_usage"] = {
                "status": "success",
                "details": "Successfully retrieved credit usage data",
                "output": stdout.strip(),
                "analysis_period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            }

            self.console.print("[green]✓[/green] Credit usage analysis completed")
            self._display_credit_usage_table(stdout)
            return True
        else:
            self.results["tests"]["credit_usage"] = {
                "status": "failed",
                "details": f"Failed to analyze credit usage: {stderr}",
                "error": stderr,
            }
            self.console.print("[red]✗[/red] Failed to analyze credit usage")
            self.add_error("Credit usage analysis failed", stderr)
            return False

    def assess_deployment_safety(self) -> bool:
        """Assess safety of deploying new resource monitors based on usage patterns."""
        self.console.print("[bold blue]Assessing Deployment Safety...[/bold blue]")

        safety_checks = []

        # Check 1: Verify current credit consumption
        if (
            "credit_usage" in self.results["tests"]
            and self.results["tests"]["credit_usage"]["status"] == "success"
        ):
            usage_data = self.results["tests"]["credit_usage"]["output"]
            if usage_data.strip():
                safety_checks.append("✓ Credit usage data available for analysis")
                self.add_recommendation(
                    "Review credit usage patterns before setting monitor limits", "high"
                )
            else:
                safety_checks.append("⚠ No recent credit usage data found")
                self.add_warning(
                    "No recent credit usage data - proceed with conservative limits"
                )

        # Check 2: Verify existing monitors don't conflict
        if "existing_monitors" in self.results["tests"]:
            if self.results["tests"]["existing_monitors"]["status"] == "success":
                monitor_data = self.results["tests"]["existing_monitors"]["output"]
                if monitor_data.strip():
                    safety_checks.append(
                        "⚠ Existing resource monitors found - check for conflicts"
                    )
                    self.add_warning(
                        "Existing resource monitors detected - verify no conflicts with new monitors"
                    )
                else:
                    safety_checks.append(
                        "✓ No existing resource monitors to conflict with"
                    )

        # Check 3: Verify warehouse assignments
        if (
            "warehouse_analysis" in self.results["tests"]
            and self.results["tests"]["warehouse_analysis"]["status"] == "success"
        ):
            safety_checks.append("✓ Warehouse configurations analyzed")
            self.add_recommendation(
                "Ensure all production warehouses have appropriate monitor assignments",
                "high",
            )

        # Determine overall safety
        failed_tests = [
            k for k, v in self.results["tests"].items() if v.get("status") == "failed"
        ]
        critical_warnings = len(
            [w for w in self.results["warnings"] if "failed" in w["message"].lower()]
        )

        if failed_tests:
            self.results["safe_to_deploy"] = False
            self.add_recommendation(
                f"Fix failed tests before deployment: {', '.join(failed_tests)}",
                "critical",
            )
        elif critical_warnings > 0:
            self.results["safe_to_deploy"] = "conditional"
            self.add_recommendation(
                "Address critical warnings before deployment", "high"
            )
        else:
            self.results["safe_to_deploy"] = True
            self.add_recommendation(
                "Deployment appears safe - proceed with caution and monitoring",
                "medium",
            )

        self.results["tests"]["safety_assessment"] = {
            "status": "completed",
            "checks": safety_checks,
            "safe_to_deploy": self.results["safe_to_deploy"],
        }

        # Display safety assessment
        self._display_safety_assessment(safety_checks)

        return True

    def _display_monitor_table(self, data: str) -> None:
        """Display resource monitors in a formatted table."""
        if not data.strip():
            return

        table = Table(title="Existing Resource Monitors")
        lines = data.strip().split("\n")

        if len(lines) > 1:
            # Add columns based on first line (headers)
            headers = lines[0].split("|")
            for header in headers[:6]:  # Limit displayed columns
                table.add_column(header.strip(), overflow="fold")

            # Add data rows
            for line in lines[1:]:
                if line.strip():
                    values = [val.strip() for val in line.split("|")]
                    table.add_row(*values[:6])

        self.console.print(table)

    def _display_warehouse_table(self, data: str) -> None:
        """Display warehouse configurations in a formatted table."""
        if not data.strip():
            return

        table = Table(title="Warehouse Configurations")
        lines = data.strip().split("\n")

        if len(lines) > 1:
            # Key columns to display
            table.add_column("Name", style="bold")
            table.add_column("State")
            table.add_column("Size")
            table.add_column("Auto Suspend")
            table.add_column("Resource Monitor")

            # Parse and add data
            for line in lines[1:]:
                if line.strip():
                    values = [val.strip() for val in line.split("|")]
                    if len(values) >= 11:
                        table.add_row(
                            values[0],  # NAME
                            values[1],  # STATE
                            values[3],  # SIZE
                            values[8],  # AUTO_SUSPEND
                            values[10] if values[10] else "None",  # RESOURCE_MONITOR
                        )

        self.console.print(table)

    def _display_credit_usage_table(self, data: str) -> None:
        """Display credit usage analysis in a formatted table."""
        if not data.strip():
            self.console.print("[yellow]No credit usage data available[/yellow]")
            return

        table = Table(title="Recent Credit Usage (Last 30 Days)")
        table.add_column("Date")
        table.add_column("Warehouse", style="bold")
        table.add_column("Daily Credits", justify="right")
        table.add_column("Query Count", justify="right")
        table.add_column("Avg Credits/Query", justify="right")

        lines = data.strip().split("\n")
        for line in lines[1:10]:  # Show top 10 entries
            if line.strip():
                values = [val.strip() for val in line.split("|")]
                if len(values) >= 5:
                    table.add_row(*values[:5])

        self.console.print(table)

    def _display_safety_assessment(self, checks: List[str]) -> None:
        """Display safety assessment results."""
        panel_content = "\n".join(checks)

        if self.results["safe_to_deploy"] is True:
            panel_style = "green"
            title = "✓ DEPLOYMENT SAFETY: APPROVED"
        elif self.results["safe_to_deploy"] == "conditional":
            panel_style = "yellow"
            title = "⚠ DEPLOYMENT SAFETY: CONDITIONAL"
        else:
            panel_style = "red"
            title = "✗ DEPLOYMENT SAFETY: NOT APPROVED"

        self.console.print(Panel(panel_content, title=title, border_style=panel_style))

    def run_investigation(self, mode: str = "full") -> Dict[str, Any]:
        """
        Run the complete investigation based on specified mode.

        Args:
            mode: Investigation mode (full, connectivity, monitors, warehouses, credits, safety)
        """
        self.console.print(
            Panel(
                f"Resource Monitor Deployment Safety Investigation\n"
                f"Mode: {mode.upper()}\n"
                f"Investigation ID: {self.results['investigation_id']}",
                title="SnowTower SnowDDL Investigation",
                border_style="blue",
            )
        )

        try:
            # Run tests based on mode
            if mode in ["full", "connectivity"]:
                if not self.test_connectivity():
                    if mode == "connectivity":
                        return self.results
                    self.add_warning(
                        "Connectivity test failed - some tests may not be reliable"
                    )

            if mode in ["full", "monitors"]:
                self.check_existing_monitors()

            if mode in ["full", "warehouses"]:
                self.analyze_warehouse_status()

            if mode in ["full", "credits"]:
                self.analyze_credit_usage()

            if mode in ["full", "safety"]:
                self.assess_deployment_safety()

            self.results["status"] = "completed"

        except KeyboardInterrupt:
            self.results["status"] = "interrupted"
            self.console.print("\n[yellow]Investigation interrupted by user[/yellow]")
        except Exception as e:
            self.results["status"] = "error"
            self.add_error("Investigation error", str(e))
            self.logger.exception("Unexpected error during investigation")

        return self.results

    def save_results(self, output_path: Optional[Path] = None) -> Path:
        """Save investigation results to a timestamped file."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = (
                Path(__file__).parent.parent / f"investigation_results_{timestamp}.json"
            )

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        self.console.print(f"[green]Results saved to:[/green] {output_path}")
        return output_path

    def format_human_summary(self) -> str:
        """Generate human-readable summary of investigation results."""
        summary = []
        summary.append(f"# Resource Monitor Investigation Summary")
        summary.append(f"**Investigation ID:** {self.results['investigation_id']}")
        summary.append(f"**Timestamp:** {self.results['timestamp']}")
        summary.append(f"**Status:** {self.results['status'].upper()}")
        summary.append("")

        # Test Results
        summary.append("## Test Results")
        for test_name, test_data in self.results["tests"].items():
            status = test_data.get("status", "unknown")
            emoji = "✓" if status == "success" else "✗" if status == "failed" else "⚠"
            summary.append(
                f"- {emoji} **{test_name.replace('_', ' ').title()}:** {status}"
            )
        summary.append("")

        # Safety Assessment
        if self.results.get("safe_to_deploy") is not None:
            summary.append("## Deployment Safety")
            if self.results["safe_to_deploy"] is True:
                summary.append("🟢 **APPROVED** - Deployment appears safe")
            elif self.results["safe_to_deploy"] == "conditional":
                summary.append("🟡 **CONDITIONAL** - Address warnings before deployment")
            else:
                summary.append(
                    "🔴 **NOT APPROVED** - Fix critical issues before deployment"
                )
            summary.append("")

        # Warnings
        if self.results["warnings"]:
            summary.append("## ⚠️ Warnings")
            for warning in self.results["warnings"]:
                summary.append(f"- {warning['message']}")
            summary.append("")

        # Recommendations
        if self.results["recommendations"]:
            summary.append("## 📋 Recommendations")
            for rec in sorted(
                self.results["recommendations"],
                key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[
                    x["priority"]
                ],
            ):
                priority_emoji = {
                    "critical": "🚨",
                    "high": "🔥",
                    "medium": "💡",
                    "low": "📝",
                }[rec["priority"]]
                summary.append(
                    f"- {priority_emoji} **{rec['priority'].upper()}:** {rec['message']}"
                )
            summary.append("")

        # Errors
        if self.results["error_details"]:
            summary.append("## ❌ Errors")
            for error in self.results["error_details"]:
                summary.append(f"- **{error['type']}:** {error['details']}")
            summary.append("")

        return "\n".join(summary)


def main():
    """Main entry point for the investigation script."""
    parser = argparse.ArgumentParser(
        description="Investigate resource monitor deployment safety for SnowTower SnowDDL"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "connectivity", "monitors", "warehouses", "credits", "safety"],
        default="full",
        help="Investigation mode (default: full)",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "human", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--save-results", action="store_true", help="Save results to timestamped file"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup console
    console = Console()

    # Create investigator
    investigator = ResourceMonitorInvestigator(console)

    if args.debug:
        investigator.logger.setLevel(logging.DEBUG)

    # Run investigation
    results = investigator.run_investigation(args.mode)

    # Output results
    if args.output_format in ["json", "both"]:
        console.print("\n[bold]JSON Results:[/bold]")
        console.print_json(data=results)

    if args.output_format in ["human", "both"]:
        console.print("\n[bold]Summary Report:[/bold]")
        summary = investigator.format_human_summary()
        console.print(
            Panel(summary, title="Investigation Summary", border_style="blue")
        )

    # Save results if requested
    if args.save_results:
        investigator.save_results()

    # Exit with appropriate code
    exit_code = 0
    if results["status"] == "error":
        exit_code = 1
    elif results["status"] == "interrupted":
        exit_code = 130
    elif results.get("safe_to_deploy") is False:
        exit_code = 2

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
