"""
Checkpoint and rollback management for SnowDDL operations.

This module provides functionality for creating checkpoints before changes
and rolling back to previous states if needed.
"""

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from snowddl_core.safety.constants import THRESHOLDS
from snowddl_core.safety.risk import Change


@dataclass
class Checkpoint:
    """
    Represents a saved state checkpoint.

    Contains all information needed to restore the system to a previous state.
    """

    checkpoint_id: str
    timestamp: datetime
    description: str
    project_state: Dict[str, Any]  # Serialized project state
    files_backup: Dict[str, str]  # File path -> content mapping
    metadata: Dict[str, Any]
    verification_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "project_state": self.project_state,
            "files_backup": self.files_backup,
            "metadata": self.metadata,
            "verification_hash": self.verification_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Create checkpoint from dictionary."""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            description=data["description"],
            project_state=data["project_state"],
            files_backup=data["files_backup"],
            metadata=data["metadata"],
            verification_hash=data["verification_hash"],
        )


@dataclass
class RollbackPlan:
    """
    Plan for rolling back to a previous state.

    Contains the steps needed to restore the system.
    """

    checkpoint_id: str
    steps: List[Change]  # Inverse operations to apply
    verification_tests: List[str]  # Tests to run after rollback
    estimated_duration_seconds: int

    def __str__(self) -> str:
        """String representation of rollback plan."""
        return (
            f"RollbackPlan to checkpoint {self.checkpoint_id}: "
            f"{len(self.steps)} steps, ~{self.estimated_duration_seconds}s"
        )


class CheckpointManager:
    """
    Manages checkpoints for safe rollback of infrastructure changes.

    Creates snapshots of the current state before changes and provides
    rollback capabilities if changes fail or cause issues.
    """

    def __init__(self, project, checkpoint_dir: Optional[Path] = None):
        """
        Initialize checkpoint manager.

        Args:
            project: SnowDDLProject instance
            checkpoint_dir: Directory to store checkpoints (default: .snowddl_checkpoints/)
        """
        self.project = project
        # Store checkpoints outside the snowddl config directory to avoid parsing issues
        self.checkpoint_dir = checkpoint_dir or Path.cwd() / ".snowddl_checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Clean up old checkpoints on initialization
        self._cleanup_old_checkpoints()

    def create_checkpoint(
        self,
        description: str = "Manual checkpoint",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a checkpoint of the current state.

        Args:
            description: Description of the checkpoint
            metadata: Additional metadata to store with checkpoint

        Returns:
            checkpoint_id for the created checkpoint
        """
        checkpoint_id = self._generate_checkpoint_id()
        timestamp = datetime.now()

        # Serialize current project state
        project_state = self._serialize_project_state()

        # Backup YAML files
        files_backup = self._backup_yaml_files()

        # Calculate verification hash
        verification_hash = self._calculate_state_hash(project_state)

        # Create checkpoint object
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=timestamp,
            description=description,
            project_state=project_state,
            files_backup=files_backup,
            metadata=metadata or {},
            verification_hash=verification_hash,
        )

        # Save checkpoint to disk
        self._save_checkpoint(checkpoint)

        print(f"✅ Created checkpoint: {checkpoint_id} - {description}")
        return checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str, verify: bool = True) -> bool:
        """
        Restore system to a previous checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore
            verify: Whether to verify the restoration

        Returns:
            True if restoration successful
        """
        # Load checkpoint
        checkpoint = self._load_checkpoint(checkpoint_id)

        if not checkpoint:
            print(f"❌ Checkpoint not found: {checkpoint_id}")
            return False

        print(f"🔄 Restoring to checkpoint: {checkpoint_id} ({checkpoint.description})")

        # Restore YAML files
        self._restore_yaml_files(checkpoint.files_backup)

        # Reload project from restored files
        self.project.load_all()

        # Verify restoration if requested
        if verify:
            current_hash = self._calculate_state_hash(self._serialize_project_state())
            if current_hash != checkpoint.verification_hash:
                print("⚠️ Warning: Restoration verification failed - state may differ")
                return False

        print(f"✅ Successfully restored to checkpoint: {checkpoint_id}")
        return True

    def list_checkpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List available checkpoints.

        Args:
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoint summaries
        """
        checkpoints = []

        # Get all checkpoint files
        checkpoint_files = sorted(
            self.checkpoint_dir.glob("*.checkpoint"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for checkpoint_file in checkpoint_files[:limit]:
            try:
                with open(checkpoint_file, "r") as f:
                    data = json.load(f)

                checkpoints.append(
                    {
                        "checkpoint_id": data["checkpoint_id"],
                        "timestamp": data["timestamp"],
                        "description": data["description"],
                        "file": str(checkpoint_file),
                    }
                )
            except Exception as e:
                print(f"⚠️ Error reading checkpoint {checkpoint_file}: {e}")

        return checkpoints

    def create_rollback_plan(
        self,
        changes: List[Change],
        checkpoint_id: Optional[str] = None,
    ) -> RollbackPlan:
        """
        Create a plan for rolling back changes.

        Args:
            changes: List of changes to create rollback for
            checkpoint_id: Checkpoint to roll back to (or latest if None)

        Returns:
            RollbackPlan with steps to restore previous state
        """
        if not checkpoint_id:
            # Use latest checkpoint
            checkpoints = self.list_checkpoints(limit=1)
            if checkpoints:
                checkpoint_id = checkpoints[0]["checkpoint_id"]
            else:
                # Create checkpoint now
                checkpoint_id = self.create_checkpoint("Pre-change checkpoint")

        # Generate inverse operations for each change
        rollback_steps = []
        for change in reversed(changes):  # Apply in reverse order
            inverse = self._create_inverse_change(change)
            if inverse:
                rollback_steps.append(inverse)

        # Create verification tests
        verification_tests = [
            "Verify all users can authenticate",
            "Verify ACCOUNTADMIN access is available",
            "Verify network policies allow access",
            "Verify warehouses are operational",
            "Verify resource monitors are at safe thresholds",
        ]

        # Estimate duration (rough estimate)
        estimated_duration = len(rollback_steps) * 2  # 2 seconds per step

        return RollbackPlan(
            checkpoint_id=checkpoint_id,
            steps=rollback_steps,
            verification_tests=verification_tests,
            estimated_duration_seconds=estimated_duration,
        )

    def _generate_checkpoint_id(self) -> str:
        """Generate unique checkpoint ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        return f"checkpoint_{timestamp}_{random_suffix}"

    def _serialize_project_state(self) -> Dict[str, Any]:
        """Serialize the current project state to a dictionary."""
        state = {
            "users": {},
            "warehouses": {},
            "business_roles": {},
            "technical_roles": {},
            "resource_monitors": {},
        }

        # Serialize each object type
        for name, user in self.project.users.items():
            state["users"][name] = user.to_yaml()

        for name, wh in self.project.warehouses.items():
            state["warehouses"][name] = wh.to_yaml()

        for name, role in self.project.business_roles.items():
            state["business_roles"][name] = role.to_yaml()

        for name, role in self.project.technical_roles.items():
            state["technical_roles"][name] = role.to_yaml()

        for name, monitor in self.project.resource_monitors.items():
            state["resource_monitors"][name] = monitor.to_yaml()

        return state

    def _backup_yaml_files(self) -> Dict[str, str]:
        """Backup all YAML files in the config directory."""
        backups = {}

        # Find all YAML files
        yaml_files = list(self.project.config_dir.glob("**/*.yaml")) + list(
            self.project.config_dir.glob("**/*.yml")
        )

        for yaml_file in yaml_files:
            # Get relative path from config dir
            rel_path = yaml_file.relative_to(self.project.config_dir)

            # Read file content
            try:
                with open(yaml_file, "r") as f:
                    content = f.read()
                backups[str(rel_path)] = content
            except Exception as e:
                print(f"⚠️ Warning: Could not backup {yaml_file}: {e}")

        return backups

    def _restore_yaml_files(self, files_backup: Dict[str, str]) -> None:
        """Restore YAML files from backup."""
        for rel_path, content in files_backup.items():
            file_path = self.project.config_dir / rel_path

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content
            with open(file_path, "w") as f:
                f.write(content)

    def _calculate_state_hash(self, state: Dict[str, Any]) -> str:
        """Calculate hash of the state for verification."""
        # Sort state for consistent hashing
        state_json = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to disk."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.checkpoint"

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

    def _load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from disk."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.checkpoint"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r") as f:
                data = json.load(f)
            return Checkpoint.from_dict(data)
        except Exception as e:
            print(f"❌ Error loading checkpoint {checkpoint_id}: {e}")
            return None

    def _cleanup_old_checkpoints(self) -> None:
        """Remove checkpoints older than retention period."""
        retention_days = THRESHOLDS["checkpoint_retention_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        for checkpoint_file in self.checkpoint_dir.glob("*.checkpoint"):
            # Check file modification time
            mtime = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)

            if mtime < cutoff_date:
                checkpoint_file.unlink()
                print(f"🗑️ Cleaned up old checkpoint: {checkpoint_file.name}")

    def _create_inverse_change(self, change: Change) -> Optional[Change]:
        """
        Create an inverse change to undo the given change.

        Args:
            change: Change to create inverse for

        Returns:
            Inverse Change object or None if not reversible
        """
        from snowddl_core.safety.risk import ChangeType

        inverse_map = {
            ChangeType.CREATE: ChangeType.DROP,
            ChangeType.DROP: ChangeType.CREATE,
            ChangeType.UPDATE: ChangeType.UPDATE,
            ChangeType.GRANT: ChangeType.REVOKE,
            ChangeType.REVOKE: ChangeType.GRANT,
            ChangeType.ALTER: ChangeType.ALTER,
        }

        inverse_type = inverse_map.get(change.change_type)

        if not inverse_type:
            return None

        # Create inverse change
        return Change(
            object_type=change.object_type,
            object_name=change.object_name,
            change_type=inverse_type,
            old_value=change.new_value,  # Swap old and new
            new_value=change.old_value,
            field_name=change.field_name,
            category=change.category,
            risk_level=change.risk_level,
            metadata={"original_change_id": id(change), "is_rollback": True},
        )
