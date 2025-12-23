#!/usr/bin/env python3
"""
SnowTower Command Help System

Provides categorized command listing and discovery for all UV commands.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def show_commands():
    """Display all available SnowTower commands organized by category"""

    console.print(
        Panel(
            "[bold cyan]SnowTower[/bold cyan] - Snowflake Infrastructure Management\n"
            "Enterprise-grade infrastructure as code for Snowflake",
            border_style="cyan",
        )
    )

    # Create tables for each category
    categories = [
        {
            "title": "SnowDDL Core Operations",
            "description": "Infrastructure deployment and validation",
            "commands": [
                (
                    "snowddl-plan",
                    "Preview infrastructure changes (always run first!)",
                    "uv run snowddl-plan",
                ),
                (
                    "snowddl-apply",
                    "Apply infrastructure changes to Snowflake",
                    "uv run snowddl-apply",
                ),
                (
                    "snowddl-validate",
                    "Validate YAML configuration files",
                    "uv run snowddl-validate",
                ),
                (
                    "snowddl-diff",
                    "Show differences between local and Snowflake",
                    "uv run snowddl-diff",
                ),
                (
                    "deploy-safe",
                    "Deploy SnowDDL + apply schema grants",
                    "uv run deploy-safe",
                ),
            ],
        },
        {
            "title": "User Management",
            "description": "User lifecycle and access control",
            "commands": [
                (
                    "manage-users",
                    "Complete user management CLI",
                    "uv run manage-users --help",
                ),
                (
                    "  create",
                    "Create new user (interactive or batch)",
                    "uv run manage-users create",
                ),
                (
                    "  list",
                    "List all users with filters",
                    "uv run manage-users list",
                ),
                (
                    "  update",
                    "Update user attributes",
                    "uv run manage-users update USERNAME",
                ),
                (
                    "  delete",
                    "Delete a user",
                    "uv run manage-users delete USERNAME",
                ),
                (
                    "  show",
                    "Show detailed user info",
                    "uv run manage-users show USERNAME",
                ),
                (
                    "  generate-password",
                    "Generate password for user",
                    "uv run manage-users generate-password USERNAME",
                ),
                (
                    "  validate",
                    "Validate user configuration",
                    "uv run manage-users validate USERNAME",
                ),
            ],
        },
        {
            "title": "Resource Management",
            "description": "Warehouses, costs, and resource optimization",
            "commands": [
                (
                    "manage-warehouses",
                    "Warehouse management and optimization",
                    "uv run manage-warehouses list",
                ),
                (
                    "  list",
                    "List all warehouses",
                    "uv run manage-warehouses list",
                ),
                (
                    "  resize",
                    "Resize warehouses",
                    "uv run manage-warehouses resize X-Small --all",
                ),
                (
                    "  auto-suspend",
                    "Set auto-suspend times",
                    "uv run manage-warehouses auto-suspend 60",
                ),
                (
                    "  optimize",
                    "Cost optimization analysis",
                    "uv run manage-warehouses optimize --apply",
                ),
                (
                    "manage-costs",
                    "Cost analysis and optimization",
                    "uv run manage-costs analyze",
                ),
                (
                    "  analyze",
                    "Analyze current costs",
                    "uv run manage-costs analyze",
                ),
                (
                    "  apply",
                    "Apply optimizations",
                    "uv run manage-costs apply --mode balanced",
                ),
                (
                    "manage-security",
                    "Security auditing and compliance",
                    "uv run manage-security full",
                ),
                (
                    "manage-backup",
                    "Configuration backup/restore",
                    "uv run manage-backup create",
                ),
            ],
        },
        {
            "title": "Schema Grants",
            "description": "Manage schema-level permissions (SnowDDL limitation workaround)",
            "commands": [
                (
                    "apply-schema-grants",
                    "Apply schema USAGE grants",
                    "uv run apply-schema-grants",
                ),
                (
                    "validate-schema-grants",
                    "Validate schema grants consistency",
                    "uv run validate-schema-grants",
                ),
            ],
        },
        {
            "title": "Monitoring & Observability",
            "description": "System health and operational metrics",
            "commands": [
                ("monitor-health", "System health checks", "uv run monitor-health"),
                ("monitor-audit", "Audit trail analysis", "uv run monitor-audit"),
                (
                    "monitor-metrics",
                    "Operational metrics dashboard",
                    "uv run monitor-metrics",
                ),
            ],
        },
        {
            "title": "Utilities",
            "description": "Helper tools and utilities",
            "commands": [
                (
                    "util-generate-key",
                    "Generate Fernet encryption key",
                    "uv run util-generate-key",
                ),
                (
                    "util-diagnose-auth",
                    "Diagnose authentication issues",
                    "uv run util-diagnose-auth",
                ),
                (
                    "util-fix-auth",
                    "Fix authentication problems",
                    "uv run util-fix-auth",
                ),
                (
                    "generate-rsa-batch",
                    "Generate RSA keys for multiple users",
                    "uv run generate-rsa-batch",
                ),
            ],
        },
        {
            "title": "Documentation",
            "description": "Documentation tools",
            "commands": [
                ("docs-serve", "Serve documentation locally", "uv run docs-serve"),
                ("docs-build", "Build documentation", "uv run docs-build"),
            ],
        },
    ]

    # Display each category
    for category in categories:
        console.print(f"\n[bold]{category['title']}[/bold]")
        console.print(f"[dim]{category['description']}[/dim]\n")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")

        for cmd, desc, _ in category["commands"]:
            table.add_row(cmd, desc)

        console.print(table)

    # Footer with helpful tips
    console.print("\n" + "-" * 80)
    console.print("\n[bold]Tips:[/bold]")
    console.print("  - Use [cyan]uv run <command> --help[/cyan] for detailed options")
    console.print(
        "  - Always run [cyan]uv run snowddl-plan[/cyan] before [cyan]snowddl-apply[/cyan]"
    )
    console.print("  - Use [cyan]uv run manage-users[/cyan] for all user operations")
    console.print("  - View full docs: [cyan]docs/guide/MANAGEMENT_COMMANDS.md[/cyan]")
    console.print("\n[bold]Quick Start:[/bold]")
    console.print("  1. Check health: [cyan]uv run monitor-health[/cyan]")
    console.print("  2. List users: [cyan]uv run manage-users list[/cyan]")
    console.print("  3. Preview changes: [cyan]uv run snowddl-plan[/cyan]")
    console.print("  4. Apply changes: [cyan]uv run snowddl-apply[/cyan]")
    console.print()


def main():
    """Main entry point"""
    show_commands()


if __name__ == "__main__":
    main()
