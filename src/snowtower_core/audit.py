"""
Audit Trail System for SnowTower

Comprehensive audit logging for all infrastructure changes including:
- User lifecycle operations (create, update, delete)
- Role assignments and modifications
- Warehouse configuration changes
- Security policy updates
- SnowDDL apply operations
- Authentication changes

Features:
- Immutable audit log (append-only)
- Multiple storage backends (CSV, JSON, database)
- Automatic change detection (before/after values)
- Compliance reporting
- Audit log querying and filtering

Usage:
    from snowtower_core.audit import AuditLogger, AuditEvent

    audit = AuditLogger()

    # Log user creation
    audit.log_user_creation("JOHN_DOE", {
        "type": "PERSON",
        "email": "john@company.com"
    })

    # Log infrastructure change
    audit.log_change(
        action="update_warehouse",
        resource="COMPUTE_WH",
        old_value={"size": "SMALL"},
        new_value={"size": "MEDIUM"}
    )
"""

import csv
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import os
from threading import Lock

from .logging import get_logger, get_correlation_id

logger = get_logger(__name__)


class AuditAction(str, Enum):
    """Enumeration of auditable actions"""

    # User operations
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ENABLE = "user_enable"
    USER_DISABLE = "user_disable"
    PASSWORD_CHANGE = "password_change"
    RSA_KEY_ROTATE = "rsa_key_rotate"

    # Role operations
    ROLE_CREATE = "role_create"
    ROLE_UPDATE = "role_update"
    ROLE_DELETE = "role_delete"
    ROLE_GRANT = "role_grant"
    ROLE_REVOKE = "role_revoke"

    # Warehouse operations
    WAREHOUSE_CREATE = "warehouse_create"
    WAREHOUSE_UPDATE = "warehouse_update"
    WAREHOUSE_DELETE = "warehouse_delete"
    WAREHOUSE_RESIZE = "warehouse_resize"
    WAREHOUSE_SUSPEND = "warehouse_suspend"
    WAREHOUSE_RESUME = "warehouse_resume"

    # Security operations
    POLICY_CREATE = "policy_create"
    POLICY_UPDATE = "policy_update"
    POLICY_DELETE = "policy_delete"
    POLICY_ATTACH = "policy_attach"
    POLICY_DETACH = "policy_detach"

    # SnowDDL operations
    SNOWDDL_PLAN = "snowddl_plan"
    SNOWDDL_APPLY = "snowddl_apply"
    SNOWDDL_ROLLBACK = "snowddl_rollback"

    # Database operations
    DATABASE_CREATE = "database_create"
    DATABASE_UPDATE = "database_update"
    DATABASE_DELETE = "database_delete"

    # Schema operations
    SCHEMA_CREATE = "schema_create"
    SCHEMA_UPDATE = "schema_update"
    SCHEMA_DELETE = "schema_delete"

    # Authentication
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    MFA_ENABLE = "mfa_enable"
    MFA_DISABLE = "mfa_disable"

    # Generic
    GENERIC_CHANGE = "generic_change"


class AuditStatus(str, Enum):
    """Status of audited operation"""

    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    PARTIAL = "partial"


@dataclass
class AuditEvent:
    """
    Represents a single audit event.

    Attributes:
        timestamp: When the event occurred (ISO 8601 format)
        correlation_id: Correlation ID for tracking related operations
        action: Type of action performed
        actor: Who performed the action (username or service account)
        resource_type: Type of resource affected (user, role, warehouse, etc.)
        resource_id: Identifier of the affected resource
        status: Outcome of the operation
        old_value: Resource state before change (JSON)
        new_value: Resource state after change (JSON)
        metadata: Additional context about the operation
        error_message: Error details if operation failed
    """

    timestamp: str
    correlation_id: Optional[str]
    action: str
    actor: str
    resource_type: str
    resource_id: str
    status: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    metadata: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    def to_csv_row(self) -> List[str]:
        """Convert to CSV row"""
        return [
            self.timestamp,
            self.correlation_id or "",
            self.action,
            self.actor,
            self.resource_type,
            self.resource_id,
            self.status,
            self.old_value or "",
            self.new_value or "",
            self.metadata or "",
            self.error_message or "",
        ]

    @classmethod
    def from_csv_row(cls, row: List[str]) -> "AuditEvent":
        """Create from CSV row"""
        return cls(
            timestamp=row[0],
            correlation_id=row[1] or None,
            action=row[2],
            actor=row[3],
            resource_type=row[4],
            resource_id=row[5],
            status=row[6],
            old_value=row[7] or None,
            new_value=row[8] or None,
            metadata=row[9] or None,
            error_message=row[10] if len(row) > 10 else None,
        )


class AuditLogger:
    """
    Central audit logging system for SnowTower.

    Manages audit trail with multiple storage backends and provides
    querying capabilities.
    """

    CSV_HEADERS = [
        "timestamp",
        "correlation_id",
        "action",
        "actor",
        "resource_type",
        "resource_id",
        "status",
        "old_value",
        "new_value",
        "metadata",
        "error_message",
    ]

    def __init__(
        self,
        audit_dir: Optional[Path] = None,
        format: str = "csv",
        actor: Optional[str] = None,
    ):
        """
        Initialize audit logger.

        Args:
            audit_dir: Directory to store audit logs. Defaults to ./logs/audit/
            format: Storage format ('csv' or 'json')
            actor: Default actor for audit events (can be overridden per event)
        """
        self.audit_dir = audit_dir or Path.cwd() / "logs" / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        self.format = format
        self.default_actor = actor or os.getenv("USER", "system")

        # Thread-safe file writing
        self._lock = Lock()

        # Current audit file
        self._current_file = self._get_audit_file()

        logger.info(f"AuditLogger initialized: {self.audit_dir}")

    def _get_audit_file(self) -> Path:
        """Get the current audit log file (rotates daily)"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        if self.format == "csv":
            return self.audit_dir / f"audit_{date_str}.csv"
        else:
            return self.audit_dir / f"audit_{date_str}.jsonl"

    def _ensure_csv_headers(self, file_path: Path):
        """Ensure CSV file has headers"""
        if not file_path.exists() or file_path.stat().st_size == 0:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.CSV_HEADERS)

    def log_event(
        self,
        action: Union[AuditAction, str],
        resource_type: str,
        resource_id: str,
        status: Union[AuditStatus, str] = AuditStatus.SUCCESS,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """
        Log an audit event.

        Args:
            action: Action performed
            resource_type: Type of resource (user, role, warehouse, etc.)
            resource_id: Identifier of the resource
            status: Outcome of the operation
            old_value: Resource state before change
            new_value: Resource state after change
            actor: Who performed the action
            metadata: Additional context
            error_message: Error details if operation failed
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            correlation_id=get_correlation_id(),
            action=action.value if isinstance(action, AuditAction) else action,
            actor=actor or self.default_actor,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status.value if isinstance(status, AuditStatus) else status,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            metadata=json.dumps(metadata) if metadata else None,
            error_message=error_message,
        )

        self._write_event(event)

        # Also log to structured logger
        logger.info(
            f"Audit: {action} on {resource_type}:{resource_id}",
            extra={
                "operation": "audit",
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "status": event.status,
            },
        )

    def _write_event(self, event: AuditEvent):
        """Write event to audit log file"""
        with self._lock:
            current_file = self._get_audit_file()

            if self.format == "csv":
                self._ensure_csv_headers(current_file)
                with open(current_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(event.to_csv_row())
            else:  # JSON Lines format
                with open(current_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event.to_dict()) + "\n")

    # Convenience methods for common operations

    def log_user_creation(
        self, username: str, user_config: Dict[str, Any], actor: Optional[str] = None
    ):
        """Log user creation"""
        self.log_event(
            action=AuditAction.USER_CREATE,
            resource_type="user",
            resource_id=username,
            status=AuditStatus.SUCCESS,
            new_value=user_config,
            actor=actor,
        )

    def log_user_update(
        self,
        username: str,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        actor: Optional[str] = None,
    ):
        """Log user update"""
        self.log_event(
            action=AuditAction.USER_UPDATE,
            resource_type="user",
            resource_id=username,
            status=AuditStatus.SUCCESS,
            old_value=old_config,
            new_value=new_config,
            actor=actor,
        )

    def log_user_deletion(self, username: str, actor: Optional[str] = None):
        """Log user deletion"""
        self.log_event(
            action=AuditAction.USER_DELETE,
            resource_type="user",
            resource_id=username,
            status=AuditStatus.SUCCESS,
            actor=actor,
        )

    def log_password_change(self, username: str, actor: Optional[str] = None):
        """Log password change (doesn't log actual password)"""
        self.log_event(
            action=AuditAction.PASSWORD_CHANGE,
            resource_type="user",
            resource_id=username,
            status=AuditStatus.SUCCESS,
            metadata={"note": "Password changed (not logged for security)"},
            actor=actor,
        )

    def log_snowddl_apply(
        self,
        changes_count: int,
        success: bool = True,
        error: Optional[str] = None,
        actor: Optional[str] = None,
    ):
        """Log SnowDDL apply operation"""
        self.log_event(
            action=AuditAction.SNOWDDL_APPLY,
            resource_type="infrastructure",
            resource_id="snowddl_config",
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            metadata={"changes_count": changes_count},
            error_message=error,
            actor=actor,
        )

    def log_warehouse_change(
        self,
        warehouse_name: str,
        action: str,
        old_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None,
    ):
        """Log warehouse configuration change"""
        self.log_event(
            action=action,
            resource_type="warehouse",
            resource_id=warehouse_name,
            status=AuditStatus.SUCCESS,
            old_value=old_state,
            new_value=new_state,
            actor=actor,
        )

    def log_security_policy_change(
        self,
        policy_name: str,
        policy_type: str,
        action: str,
        old_config: Optional[Dict[str, Any]] = None,
        new_config: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None,
    ):
        """Log security policy change"""
        self.log_event(
            action=action,
            resource_type=f"policy_{policy_type}",
            resource_id=policy_name,
            status=AuditStatus.SUCCESS,
            old_value=old_config,
            new_value=new_config,
            actor=actor,
        )

    def log_auth_attempt(
        self,
        username: str,
        success: bool,
        method: str = "unknown",
        error: Optional[str] = None,
    ):
        """Log authentication attempt"""
        self.log_event(
            action=AuditAction.AUTH_SUCCESS if success else AuditAction.AUTH_FAILURE,
            resource_type="authentication",
            resource_id=username,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            metadata={"method": method},
            error_message=error,
            actor=username,
        )

    # Querying methods

    def query_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """
        Query audit events with filters.

        Args:
            start_date: Filter events after this date
            end_date: Filter events before this date
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            actor: Filter by actor
            status: Filter by status
            limit: Maximum number of events to return

        Returns:
            List of matching audit events
        """
        events = []

        # Determine which files to search
        if start_date and end_date:
            date_range = self._get_date_range(start_date, end_date)
        elif start_date:
            date_range = self._get_date_range(start_date, datetime.now())
        else:
            # Search all files
            date_range = None

        # Get files to search
        if date_range:
            files = [self._get_audit_file_for_date(d) for d in date_range]
            files = [f for f in files if f.exists()]
        else:
            if self.format == "csv":
                files = list(self.audit_dir.glob("audit_*.csv"))
            else:
                files = list(self.audit_dir.glob("audit_*.jsonl"))

        # Search files
        for file_path in sorted(files, reverse=True):  # Most recent first
            file_events = self._read_events_from_file(file_path)

            # Apply filters
            for event in file_events:
                if action and event.action != action:
                    continue
                if resource_type and event.resource_type != resource_type:
                    continue
                if resource_id and event.resource_id != resource_id:
                    continue
                if actor and event.actor != actor:
                    continue
                if status and event.status != status:
                    continue

                # Date filtering
                if start_date or end_date:
                    event_date = datetime.fromisoformat(
                        event.timestamp.replace("Z", "+00:00")
                    )
                    if start_date and event_date < start_date:
                        continue
                    if end_date and event_date > end_date:
                        continue

                events.append(event)

                if limit and len(events) >= limit:
                    return events

        return events

    def _read_events_from_file(self, file_path: Path) -> List[AuditEvent]:
        """Read events from a single audit file"""
        events = []

        if self.format == "csv":
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if row:  # Skip empty rows
                        try:
                            events.append(AuditEvent.from_csv_row(row))
                        except Exception as e:
                            logger.warning(f"Failed to parse audit row: {e}")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            events.append(AuditEvent(**data))
                        except Exception as e:
                            logger.warning(f"Failed to parse audit JSON: {e}")

        return events

    def _get_audit_file_for_date(self, date: datetime) -> Path:
        """Get audit file path for a specific date"""
        date_str = date.strftime("%Y-%m-%d")
        if self.format == "csv":
            return self.audit_dir / f"audit_{date_str}.csv"
        else:
            return self.audit_dir / f"audit_{date_str}.jsonl"

    def _get_date_range(self, start: datetime, end: datetime) -> List[datetime]:
        """Get list of dates between start and end"""
        dates = []
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)

        while current <= end:
            dates.append(current)
            current += timedelta(days=1)

        return dates

    def get_recent_events(self, hours: int = 24, limit: int = 100) -> List[AuditEvent]:
        """
        Get recent audit events.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of events

        Returns:
            List of recent events
        """
        start_date = datetime.utcnow() - timedelta(hours=hours)
        return self.query_events(start_date=start_date, limit=limit)

    def get_user_activity(self, username: str, days: int = 30) -> List[AuditEvent]:
        """
        Get all activity for a specific user.

        Args:
            username: Username to query
            days: Number of days to look back

        Returns:
            List of events for the user
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        return self.query_events(
            start_date=start_date, resource_id=username, resource_type="user"
        )

    def get_compliance_report(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Generate compliance report for date range.

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            Compliance report dictionary
        """
        events = self.query_events(start_date=start_date, end_date=end_date)

        report = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_events": len(events),
            "by_action": {},
            "by_resource_type": {},
            "by_status": {},
            "by_actor": {},
            "security_events": [],
            "failed_operations": [],
        }

        # Analyze events
        for event in events:
            # Count by action
            report["by_action"][event.action] = (
                report["by_action"].get(event.action, 0) + 1
            )

            # Count by resource type
            report["by_resource_type"][event.resource_type] = (
                report["by_resource_type"].get(event.resource_type, 0) + 1
            )

            # Count by status
            report["by_status"][event.status] = (
                report["by_status"].get(event.status, 0) + 1
            )

            # Count by actor
            report["by_actor"][event.actor] = report["by_actor"].get(event.actor, 0) + 1

            # Collect security events
            if event.action in [
                AuditAction.AUTH_FAILURE.value,
                AuditAction.POLICY_DETACH.value,
                AuditAction.MFA_DISABLE.value,
            ]:
                report["security_events"].append(event.to_dict())

            # Collect failed operations
            if event.status == AuditStatus.FAILURE.value:
                report["failed_operations"].append(event.to_dict())

        return report


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(audit_dir: Optional[Path] = None) -> AuditLogger:
    """
    Get global audit logger instance.

    Args:
        audit_dir: Directory for audit logs

    Returns:
        Global AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(audit_dir=audit_dir)
    return _audit_logger
