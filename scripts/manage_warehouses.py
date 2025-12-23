#!/usr/bin/env python3
"""
Warehouse Management Script for SnowDDL

Common warehouse operations:
- List warehouses
- Resize warehouses
- Set auto-suspend times
- Assign resource monitors
- Generate reports
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

# Add parent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.project import SnowDDLProject
from snowddl_core.account_objects import Warehouse
from snowddl_core.safety import CheckpointManager


def list_warehouses(project: SnowDDLProject, args):
    """List all warehouses with details."""

    print("\n📊 WAREHOUSE REPORT")
    print("=" * 90)
    print(
        f"{'Name':<25} {'Size':<10} {'Auto-Suspend':<15} {'Monitor':<25} {'Comment':<30}"
    )
    print("-" * 90)

    for name, wh in sorted(project.warehouses.items()):
        auto_suspend = f"{wh.auto_suspend}s" if wh.auto_suspend else "Never"
        monitor = wh.resource_monitor or "None"
        comment = (
            (wh.comment[:27] + "...")
            if wh.comment and len(wh.comment) > 30
            else (wh.comment or "")
        )

        print(
            f"{name:<25} {wh.size or 'X-Small':<10} {auto_suspend:<15} {monitor:<25} {comment:<30}"
        )

    print("-" * 90)
    print(f"Total: {len(project.warehouses)} warehouses")

    # Size distribution
    sizes = {}
    for wh in project.warehouses.values():
        size = wh.size or "X-Small"
        sizes[size] = sizes.get(size, 0) + 1

    print(f"Sizes: {', '.join(f'{s}:{c}' for s, c in sorted(sizes.items()))}")


def resize_warehouses(project: SnowDDLProject, args):
    """Resize warehouses."""

    if args.all:
        warehouses = project.warehouses.keys()
    else:
        warehouses = args.warehouses.split(",")

    resized = []

    for name in warehouses:
        wh = project.get_warehouse(name.upper())
        if wh:
            old_size = wh.size or "X-Small"
            wh.size = args.size
            resized.append(name.upper())
            print(f"  📐 Resized {name.upper()}: {old_size} → {args.size}")
        else:
            print(f"  ⚠️  Warehouse {name.upper()} not found")

    if args.save and resized:
        project.save_warehouses()
        print(f"\n💾 Saved {len(resized)} changes to warehouse.yaml")

    return resized


def set_auto_suspend(project: SnowDDLProject, args):
    """Set auto-suspend times for warehouses."""

    updated = []

    for name, wh in project.warehouses.items():
        # Apply filter if specified
        if args.filter_size and wh.size != args.filter_size:
            continue

        old_suspend = wh.auto_suspend
        wh.auto_suspend = args.seconds
        updated.append(name)

        print(f"  ⏱️  {name}: {old_suspend}s → {args.seconds}s")

    if args.save and updated:
        project.save_warehouses()
        print(f"\n💾 Updated {len(updated)} warehouses in warehouse.yaml")

    return updated


def assign_monitors(project: SnowDDLProject, args):
    """Assign resource monitors to warehouses."""

    # Check if monitor exists
    if not project.get_resource_monitor(args.monitor):
        print(f"❌ Resource monitor {args.monitor} not found")
        return []

    if args.all:
        warehouses = project.warehouses.keys()
    else:
        warehouses = args.warehouses.split(",")

    assigned = []

    for name in warehouses:
        wh = project.get_warehouse(name.upper())
        if wh:
            old_monitor = wh.resource_monitor
            wh.resource_monitor = args.monitor
            assigned.append(name.upper())
            print(f"  📊 {name.upper()}: {old_monitor or 'None'} → {args.monitor}")
        else:
            print(f"  ⚠️  Warehouse {name.upper()} not found")

    if args.save and assigned:
        project.save_warehouses()
        print(f"\n💾 Assigned monitor to {len(assigned)} warehouses")

    return assigned


def optimize_warehouses(project: SnowDDLProject, args):
    """Optimize warehouse configurations for cost."""

    print("\n💰 WAREHOUSE OPTIMIZATION RECOMMENDATIONS")
    print("=" * 80)

    recommendations = []

    for name, wh in project.warehouses.items():
        issues = []

        # Check auto-suspend
        if not wh.auto_suspend or wh.auto_suspend > 300:
            issues.append(
                f"Set auto-suspend to 60s (currently: {wh.auto_suspend or 'Never'})"
            )

        # Check size for non-production
        if "DEV" in name or "TEST" in name:
            if wh.size and wh.size not in ["X-Small", "Small"]:
                issues.append(f"Downsize to X-Small (currently: {wh.size})")

        # Check resource monitor
        if not wh.resource_monitor:
            issues.append("Add resource monitor")

        if issues:
            recommendations.append((name, issues))
            print(f"\n{name}:")
            for issue in issues:
                print(f"  • {issue}")

    if not recommendations:
        print("✅ All warehouses are optimized!")
    else:
        print(f"\n\n💡 Found {len(recommendations)} warehouses to optimize")

        if args.apply:
            print("\nApplying optimizations...")
            for name, issues in recommendations:
                wh = project.get_warehouse(name)
                for issue in issues:
                    if "auto-suspend to 60s" in issue:
                        wh.auto_suspend = 60
                    elif "Downsize to X-Small" in issue:
                        wh.size = "X-Small"

            project.save_warehouses()
            print("💾 Optimizations saved to warehouse.yaml")

    return recommendations


def main():
    parser = argparse.ArgumentParser(description="Manage SnowDDL warehouses")
    parser.add_argument("--config", default="./snowddl", help="Config directory")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all warehouses")

    # Resize command
    resize_parser = subparsers.add_parser("resize", help="Resize warehouses")
    resize_parser.add_argument(
        "size", choices=["X-Small", "Small", "Medium", "Large", "X-Large"]
    )
    resize_parser.add_argument("--warehouses", help="Comma-separated warehouse names")
    resize_parser.add_argument(
        "--all", action="store_true", help="Resize all warehouses"
    )
    resize_parser.add_argument("--save", action="store_true", help="Save to YAML")

    # Auto-suspend command
    suspend_parser = subparsers.add_parser("auto-suspend", help="Set auto-suspend time")
    suspend_parser.add_argument("seconds", type=int, help="Seconds before auto-suspend")
    suspend_parser.add_argument(
        "--filter-size", help="Only update warehouses of this size"
    )
    suspend_parser.add_argument("--save", action="store_true", help="Save to YAML")

    # Assign monitor command
    monitor_parser = subparsers.add_parser(
        "assign-monitor", help="Assign resource monitor"
    )
    monitor_parser.add_argument("monitor", help="Resource monitor name")
    monitor_parser.add_argument("--warehouses", help="Comma-separated warehouse names")
    monitor_parser.add_argument(
        "--all", action="store_true", help="Assign to all warehouses"
    )
    monitor_parser.add_argument("--save", action="store_true", help="Save to YAML")

    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Optimize for cost")
    optimize_parser.add_argument(
        "--apply", action="store_true", help="Apply optimizations"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load project
    project = SnowDDLProject(args.config)

    # Create checkpoint for modifying commands
    if args.command in ["resize", "auto-suspend", "assign-monitor"] or (
        args.command == "optimize" and args.apply
    ):
        checkpoint_mgr = CheckpointManager(project)
        checkpoint_id = checkpoint_mgr.create_checkpoint(
            f"Before warehouse {args.command}"
        )
        print(f"🔒 Created checkpoint: {checkpoint_id}")

    # Execute command
    if args.command == "list":
        list_warehouses(project, args)
    elif args.command == "resize":
        resize_warehouses(project, args)
    elif args.command == "auto-suspend":
        set_auto_suspend(project, args)
    elif args.command == "assign-monitor":
        assign_monitors(project, args)
    elif args.command == "optimize":
        optimize_warehouses(project, args)


if __name__ == "__main__":
    main()
