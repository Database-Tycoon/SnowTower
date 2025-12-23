#!/usr/bin/env python3
"""
Backup and Restore Script for SnowDDL

Manage configuration backups:
- Create timestamped backups
- List available backups
- Restore from backup
- Compare configurations
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

# Add parent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.project import SnowDDLProject
from snowddl_core.safety import CheckpointManager


def create_backup(project: SnowDDLProject, description: str = None):
    """Create a full backup of current configuration."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(".snowddl_backups") / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📦 Creating backup: {timestamp}")

    # Copy all YAML files
    config_dir = Path(project.config_dir)
    files_copied = 0

    for yaml_file in config_dir.glob("**/*.yaml"):
        rel_path = yaml_file.relative_to(config_dir)
        target = backup_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(yaml_file, target)
        files_copied += 1
        print(f"  • Backed up {rel_path}")

    # Save metadata
    metadata = {
        "timestamp": timestamp,
        "description": description or "Manual backup",
        "files": files_copied,
        "summary": project.summary(),
    }

    with open(backup_dir / "backup_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✅ Backup created: {backup_dir}")
    print(f"   Files: {files_copied}")

    return timestamp


def list_backups():
    """List all available backups."""

    backup_root = Path(".snowddl_backups")
    if not backup_root.exists():
        print("No backups found")
        return []

    print("\n📋 AVAILABLE BACKUPS")
    print("=" * 80)
    print(f"{'Timestamp':<20} {'Description':<40} {'Files':<10}")
    print("-" * 80)

    backups = []

    for backup_dir in sorted(backup_root.iterdir(), reverse=True):
        if backup_dir.is_dir():
            metadata_file = backup_dir / "backup_metadata.json"

            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                timestamp = metadata["timestamp"]
                description = (
                    metadata["description"][:37] + "..."
                    if len(metadata["description"]) > 40
                    else metadata["description"]
                )
                files = metadata["files"]

                print(f"{timestamp:<20} {description:<40} {files:<10}")
                backups.append(timestamp)

    print(f"\nTotal: {len(backups)} backups")

    return backups


def restore_backup(project: SnowDDLProject, backup_id: str):
    """Restore configuration from backup."""

    backup_dir = Path(".snowddl_backups") / backup_id

    if not backup_dir.exists():
        print(f"❌ Backup not found: {backup_id}")
        return False

    print(f"\n🔄 Restoring from backup: {backup_id}")

    # First create a checkpoint of current state
    checkpoint_mgr = CheckpointManager(project)
    checkpoint_id = checkpoint_mgr.create_checkpoint(f"Before restore from {backup_id}")
    print(f"   Created safety checkpoint: {checkpoint_id}")

    # Load backup metadata
    with open(backup_dir / "backup_metadata.json", "r") as f:
        metadata = json.load(f)

    print(f"   Description: {metadata['description']}")

    # Restore files
    config_dir = Path(project.config_dir)
    files_restored = 0

    for yaml_file in backup_dir.glob("**/*.yaml"):
        if yaml_file.name == "backup_metadata.json":
            continue

        rel_path = yaml_file.relative_to(backup_dir)
        target = config_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(yaml_file, target)
        files_restored += 1
        print(f"  • Restored {rel_path}")

    print(f"\n✅ Restored {files_restored} files from backup")
    print(f"   Safety checkpoint available: {checkpoint_id}")

    # Reload project
    project.load_all()

    return True


def compare_with_backup(project: SnowDDLProject, backup_id: str):
    """Compare current configuration with a backup."""

    backup_dir = Path(".snowddl_backups") / backup_id

    if not backup_dir.exists():
        print(f"❌ Backup not found: {backup_id}")
        return

    print(f"\n🔍 Comparing with backup: {backup_id}")

    # Load backup project
    backup_project = SnowDDLProject(str(backup_dir))

    # Compare summaries
    current_summary = project.summary()
    backup_summary = backup_project.summary()

    print("\n" + "=" * 60)
    print(f"{'Object Type':<20} {'Current':<15} {'Backup':<15} {'Difference':<10}")
    print("-" * 60)

    for obj_type in current_summary:
        current = current_summary[obj_type]
        backup = backup_summary.get(obj_type, 0)
        diff = current - backup
        diff_str = f"+{diff}" if diff > 0 else str(diff) if diff != 0 else "="

        print(f"{obj_type:<20} {current:<15} {backup:<15} {diff_str:<10}")

    # Detailed user comparison
    print("\n📝 User Changes:")
    current_users = set(project.users.keys())
    backup_users = set(backup_project.users.keys())

    added = current_users - backup_users
    removed = backup_users - current_users

    if added:
        print(f"  Added: {', '.join(added)}")
    if removed:
        print(f"  Removed: {', '.join(removed)}")
    if not added and not removed:
        print("  No changes")


def cleanup_old_backups(days: int = 30):
    """Remove backups older than specified days."""

    backup_root = Path(".snowddl_backups")
    if not backup_root.exists():
        return

    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
    removed = 0

    for backup_dir in backup_root.iterdir():
        if backup_dir.is_dir():
            # Check age
            mtime = backup_dir.stat().st_mtime
            if mtime < cutoff:
                shutil.rmtree(backup_dir)
                removed += 1
                print(f"  🗑️  Removed old backup: {backup_dir.name}")

    if removed > 0:
        print(f"\n✅ Cleaned up {removed} old backups")


def main():
    parser = argparse.ArgumentParser(
        description="Backup and restore SnowDDL configurations"
    )
    parser.add_argument("--config", default="./snowddl", help="Config directory")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create backup
    create_parser = subparsers.add_parser("create", help="Create a backup")
    create_parser.add_argument("--description", help="Backup description")

    # List backups
    list_parser = subparsers.add_parser("list", help="List available backups")

    # Restore backup
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_id", help="Backup timestamp ID")

    # Compare with backup
    compare_parser = subparsers.add_parser("compare", help="Compare with backup")
    compare_parser.add_argument("backup_id", help="Backup timestamp ID")

    # Cleanup old backups
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    cleanup_parser.add_argument(
        "--days", type=int, default=30, help="Keep backups newer than N days"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load project (except for list/cleanup)
    if args.command not in ["list", "cleanup"]:
        project = SnowDDLProject(args.config)

    if args.command == "create":
        create_backup(project, args.description)
    elif args.command == "list":
        list_backups()
    elif args.command == "restore":
        restore_backup(project, args.backup_id)
    elif args.command == "compare":
        compare_with_backup(project, args.backup_id)
    elif args.command == "cleanup":
        cleanup_old_backups(args.days)


if __name__ == "__main__":
    main()
