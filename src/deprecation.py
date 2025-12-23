#!/usr/bin/env python3
"""
Deprecation warnings for legacy UV commands.

This module provides warning messages for commands that have been consolidated
or renamed to improve the UV command system consistency.
"""

import sys
from rich.console import Console
from rich.panel import Panel

console = Console()


def warn_deprecated(old_command: str, new_command: str, description: str = ""):
    """Show deprecation warning and redirect to new command"""
    console.print(
        Panel(
            f"[yellow]⚠️  Command Deprecated[/yellow]\n\n"
            f"The command [red]{old_command}[/red] has been deprecated.\n"
            f"Please use [green]{new_command}[/green] instead.\n\n"
            f"{description}\n\n"
            f"[dim]This command will be removed in a future version.[/dim]",
            border_style="yellow",
            title="Deprecation Warning",
        )
    )


def warn_user_create():
    """Deprecation warning for user-create command"""
    warn_deprecated(
        old_command="uv run user-create",
        new_command="uv run manage-users create",
        description="All user management operations have been consolidated into the "
        "[cyan]manage-users[/cyan] command for consistency.",
    )

    console.print("\n[bold]Quick Migration:[/bold]")
    console.print("  • Interactive mode: [cyan]uv run manage-users create[/cyan]")
    console.print(
        "  • Batch mode: [cyan]uv run manage-users create --first-name John --last-name Doe --email john@example.com[/cyan]"
    )
    console.print("  • Full help: [cyan]uv run manage-users create --help[/cyan]\n")

    # Ask if they want to run the new command
    from rich.prompt import Confirm

    if Confirm.ask("Would you like to run the new command now?", default=True):
        from user_management.cli import main

        sys.argv[0] = "manage-users"
        sys.argv.insert(1, "create")
        main()
    else:
        sys.exit(0)


def warn_users():
    """Deprecation warning for users command"""
    warn_deprecated(
        old_command="uv run users",
        new_command="uv run manage-users",
        description="The command has been renamed to follow the [cyan]manage-*[/cyan] "
        "naming convention for resource management commands.",
    )

    console.print("\n[bold]Available Subcommands:[/bold]")
    console.print("  • [cyan]manage-users list[/cyan] - List all users")
    console.print("  • [cyan]manage-users create[/cyan] - Create new user")
    console.print("  • [cyan]manage-users show USERNAME[/cyan] - Show user details")
    console.print("  • [cyan]manage-users --help[/cyan] - Full command list\n")

    sys.exit(0)


def warn_user_manage():
    """Deprecation warning for user-manage command"""
    warn_deprecated(
        old_command="uv run user-manage",
        new_command="uv run manage-users",
        description="The command has been renamed to follow the [cyan]manage-*[/cyan] "
        "naming convention for consistency with other resource management commands.",
    )

    console.print("\n[bold]Usage:[/bold]")
    console.print("  [cyan]uv run manage-users[/cyan] [dim]<subcommand>[/dim]\n")

    # Forward to the new command
    from rich.prompt import Confirm

    if Confirm.ask("Would you like to run the new command now?", default=True):
        from user_management.cli import main

        sys.argv[0] = "manage-users"
        main()
    else:
        sys.exit(0)


def warn_user_account():
    """Deprecation warning for user-account command"""
    warn_deprecated(
        old_command="uv run user-account",
        new_command="uv run manage-users snowddl-account",
        description="Service account management has been integrated into the main "
        "[cyan]manage-users[/cyan] command.",
    )

    console.print("\n[bold]Service Account Commands:[/bold]")
    console.print(
        "  • [cyan]uv run manage-users snowddl-account test[/cyan] - Test connection"
    )
    console.print(
        "  • [cyan]uv run manage-users snowddl-account status[/cyan] - Show status"
    )
    console.print(
        "  • [cyan]uv run manage-users snowddl-account permissions[/cyan] - Check permissions\n"
    )

    sys.exit(0)


def warn_health_check():
    """Deprecation warning for health-check command"""
    warn_deprecated(
        old_command="uv run health-check",
        new_command="uv run monitor-health",
        description="Health check functionality has been consolidated into the "
        "[cyan]monitor-health[/cyan] command.",
    )

    console.print("\n[bold]Monitoring Commands:[/bold]")
    console.print("  • [cyan]uv run monitor-health[/cyan] - System health checks")
    console.print("  • [cyan]uv run monitor-audit[/cyan] - Audit trail analysis")
    console.print("  • [cyan]uv run monitor-metrics[/cyan] - Operational metrics\n")

    sys.exit(0)


def warn_generate_passwords():
    """Deprecation warning for generate-passwords command"""
    warn_deprecated(
        old_command="uv run generate-passwords",
        new_command="uv run manage-users bulk-generate-passwords",
        description="Password generation has been integrated into the [cyan]manage-users[/cyan] command.",
    )

    console.print("\n[bold]Password Generation Commands:[/bold]")
    console.print(
        "  • [cyan]uv run manage-users generate-password USERNAME[/cyan] - Single user"
    )
    console.print(
        "  • [cyan]uv run manage-users bulk-generate-passwords --usernames 'USER1,USER2'[/cyan] - Multiple users"
    )
    console.print(
        "  • [cyan]uv run manage-users regenerate-password USERNAME[/cyan] - Regenerate existing\n"
    )

    sys.exit(0)


if __name__ == "__main__":
    console.print("[red]This module should not be run directly.[/red]")
    console.print("It provides deprecation warnings for UV commands.")
    sys.exit(1)
