#!/usr/bin/env python3
"""
Cost Optimization Script for SnowDDL

Analyze and optimize Snowflake costs by:
- Downsizing warehouses
- Setting aggressive auto-suspend
- Adding resource monitors
- Identifying unused resources
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
from snowddl_core.safety import CheckpointManager


def analyze_costs(project: SnowDDLProject):
    """Analyze potential cost savings."""

    print("\n💰 COST OPTIMIZATION ANALYSIS")
    print("=" * 80)

    savings = {
        "warehouse_downsize": [],
        "auto_suspend": [],
        "missing_monitors": [],
        "oversized_dev": [],
    }

    # Analyze warehouses
    for name, wh in project.warehouses.items():
        # Check auto-suspend
        if not wh.auto_suspend or wh.auto_suspend > 60:
            current = wh.auto_suspend or "Never"
            savings["auto_suspend"].append(
                {
                    "warehouse": name,
                    "current": current,
                    "recommended": 60,
                    "impact": "High" if not wh.auto_suspend else "Medium",
                }
            )

        # Check DEV/TEST warehouse sizes
        if any(keyword in name.upper() for keyword in ["DEV", "TEST", "DEMO"]):
            if wh.size and wh.size not in ["X-Small"]:
                savings["oversized_dev"].append(
                    {
                        "warehouse": name,
                        "current": wh.size,
                        "recommended": "X-Small",
                        "impact": "Medium",
                    }
                )

        # Check for missing monitors
        if not wh.resource_monitor:
            savings["missing_monitors"].append({"warehouse": name, "impact": "High"})

    # Print recommendations
    total_recommendations = sum(len(v) for v in savings.values())

    if total_recommendations == 0:
        print("✅ Your configuration is already optimized!")
        return savings

    print(f"\n📊 Found {total_recommendations} optimization opportunities:\n")

    # Auto-suspend recommendations
    if savings["auto_suspend"]:
        print("🕐 AUTO-SUSPEND OPTIMIZATIONS")
        print("-" * 40)
        for item in savings["auto_suspend"]:
            print(f"  {item['warehouse']}: {item['current']} → {item['recommended']}s")
        print(f"  Potential savings: HIGH (reduce idle time costs)")

    # Oversized DEV warehouses
    if savings["oversized_dev"]:
        print("\n📐 DEV/TEST WAREHOUSE DOWNSIZING")
        print("-" * 40)
        for item in savings["oversized_dev"]:
            print(f"  {item['warehouse']}: {item['current']} → {item['recommended']}")
        print(f"  Potential savings: MEDIUM (reduce compute costs)")

    # Missing monitors
    if savings["missing_monitors"]:
        print("\n🚨 MISSING RESOURCE MONITORS")
        print("-" * 40)
        for item in savings["missing_monitors"]:
            print(f"  {item['warehouse']}: No monitor assigned")
        print(f"  Risk: HIGH (uncontrolled spending)")

    return savings


def apply_optimizations(project: SnowDDLProject, mode: str = "balanced"):
    """Apply cost optimizations based on mode."""

    print(f"\n🔧 Applying {mode.upper()} optimizations...")

    changes = 0

    # Define settings by mode
    modes = {
        "aggressive": {"auto_suspend": 60, "dev_size": "X-Small"},
        "balanced": {"auto_suspend": 120, "dev_size": "X-Small"},
        "conservative": {"auto_suspend": 300, "dev_size": "Small"},
    }

    settings = modes[mode]

    # Apply to warehouses
    for name, wh in project.warehouses.items():
        modified = False

        # Update auto-suspend
        if not wh.auto_suspend or wh.auto_suspend > settings["auto_suspend"]:
            old = wh.auto_suspend
            wh.auto_suspend = settings["auto_suspend"]
            print(f"  ⏱️  {name}: auto-suspend {old}s → {settings['auto_suspend']}s")
            modified = True

        # Downsize DEV/TEST warehouses
        if any(keyword in name.upper() for keyword in ["DEV", "TEST", "DEMO"]):
            if wh.size and wh.size not in ["X-Small", "Small"]:
                old_size = wh.size
                wh.size = settings["dev_size"]
                print(f"  📐 {name}: {old_size} → {settings['dev_size']}")
                modified = True

        # Add default monitor if missing
        if not wh.resource_monitor and project.resource_monitors:
            # Use first available monitor
            monitor = list(project.resource_monitors.keys())[0]
            wh.resource_monitor = monitor
            print(f"  📊 {name}: assigned monitor {monitor}")
            modified = True

        if modified:
            changes += 1

    if changes > 0:
        project.save_warehouses()
        print(f"\n💾 Applied {changes} optimizations to warehouse.yaml")
    else:
        print("\n✅ No changes needed")

    return changes


def estimate_savings(project: SnowDDLProject):
    """Estimate potential cost savings."""

    print("\n💵 ESTIMATED MONTHLY SAVINGS")
    print("=" * 80)

    # Rough estimates (credits per month)
    size_credits = {
        "X-Small": 24,  # 1 credit/hour * 24 hours
        "Small": 48,  # 2 credits/hour
        "Medium": 96,  # 4 credits/hour
        "Large": 192,  # 8 credits/hour
        "X-Large": 384,  # 16 credits/hour
    }

    total_savings = 0

    # Calculate savings from downsizing
    for name, wh in project.warehouses.items():
        if any(keyword in name.upper() for keyword in ["DEV", "TEST"]):
            current_size = wh.size or "X-Small"
            if current_size != "X-Small":
                current_cost = size_credits.get(current_size, 24)
                new_cost = size_credits["X-Small"]
                savings = (current_cost - new_cost) * 10  # Assume 10 hours/day usage
                total_savings += savings
                print(
                    f"  {name}: ${savings:.0f}/month (downsize {current_size} → X-Small)"
                )

    # Calculate savings from auto-suspend
    warehouses_without_suspend = sum(
        1 for wh in project.warehouses.values() if not wh.auto_suspend
    )
    if warehouses_without_suspend > 0:
        suspend_savings = warehouses_without_suspend * 50  # Rough estimate
        total_savings += suspend_savings
        print(
            f"  Auto-suspend: ${suspend_savings:.0f}/month ({warehouses_without_suspend} warehouses)"
        )

    print("-" * 80)
    print(f"  TOTAL ESTIMATED SAVINGS: ${total_savings:.0f}/month")
    print(f"  Annual savings: ${total_savings * 12:.0f}")

    return total_savings


def main():
    parser = argparse.ArgumentParser(description="Optimize SnowDDL for cost savings")
    parser.add_argument("--config", default="./snowddl", help="Config directory")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze cost optimization opportunities"
    )

    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply cost optimizations")
    apply_parser.add_argument(
        "--mode",
        choices=["aggressive", "balanced", "conservative"],
        default="balanced",
        help="Optimization mode",
    )

    # Estimate command
    estimate_parser = subparsers.add_parser(
        "estimate", help="Estimate potential savings"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load project
    project = SnowDDLProject(args.config)

    if args.command == "analyze":
        analyze_costs(project)
    elif args.command == "apply":
        checkpoint_mgr = CheckpointManager(project)
        checkpoint_id = checkpoint_mgr.create_checkpoint("Before cost optimization")
        print(f"🔒 Created checkpoint: {checkpoint_id}")
        apply_optimizations(project, args.mode)
    elif args.command == "estimate":
        estimate_savings(project)


if __name__ == "__main__":
    main()
