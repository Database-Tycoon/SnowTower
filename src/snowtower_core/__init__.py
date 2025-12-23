"""
SnowTower Core - Extended Object-Oriented Framework for Snowflake Management

This package extends the SnowDDL Core framework to include comprehensive Snowflake
infrastructure management capabilities with integrated web interface support.

Key Features:
- Complete CRUD operations for all Snowflake objects
- Manager classes for business logic separation
- Integrated Snowflake client connectivity
- Web interface model support
- Type-safe API with full validation
- Comprehensive test coverage
"""

# Import all from snowddl_core for backward compatibility
from snowddl_core import *
from snowddl_core import __all__ as _snowddl_core_all

# Extended models for web interface
from .models import (
    UserModel,
    RoleModel,
    WarehouseModel,
    DatabaseModel,
    SchemaModel,
    SecurityPolicyModel,
)

# Manager classes for business logic
from .managers import (
    UserManager,
    RoleManager,
    WarehouseManager,
    DatabaseManager,
    SchemaManager,
    SecurityPolicyManager,
    SnowflakeClientManager,
)

# Monitoring and observability
from .logging import (
    get_logger,
    setup_logging,
    correlation_context,
    set_correlation_id,
    get_correlation_id,
    log_operation_start,
    log_operation_success,
    log_operation_failure,
)

from .audit import (
    AuditLogger,
    AuditEvent,
    AuditAction,
    AuditStatus,
    get_audit_logger,
)

from .metrics import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    get_metrics,
    track_operation,
)

from .alerts import (
    AlertManager,
    Alert,
    AlertSeverity,
    AlertChannel,
    ConsoleAlertChannel,
    WebhookAlertChannel,
    SlackAlertChannel,
    EmailAlertChannel,
    get_alert_manager,
    alert_deployment_failure,
    alert_auth_failure,
    alert_security_violation,
    alert_high_error_rate,
)

__version__ = "1.0.0"

# Extend the __all__ from snowddl_core
__all__ = [
    # Everything from snowddl_core
    *_snowddl_core_all,
    # Extended models
    "UserModel",
    "RoleModel",
    "WarehouseModel",
    "DatabaseModel",
    "SchemaModel",
    "SecurityPolicyModel",
    # Manager classes
    "UserManager",
    "RoleManager",
    "WarehouseManager",
    "DatabaseManager",
    "SchemaManager",
    "SecurityPolicyManager",
    "SnowflakeClientManager",
    # Monitoring and observability
    "get_logger",
    "setup_logging",
    "correlation_context",
    "set_correlation_id",
    "get_correlation_id",
    "log_operation_start",
    "log_operation_success",
    "log_operation_failure",
    "AuditLogger",
    "AuditEvent",
    "AuditAction",
    "AuditStatus",
    "get_audit_logger",
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "get_metrics",
    "track_operation",
    "AlertManager",
    "Alert",
    "AlertSeverity",
    "AlertChannel",
    "ConsoleAlertChannel",
    "WebhookAlertChannel",
    "SlackAlertChannel",
    "EmailAlertChannel",
    "get_alert_manager",
    "alert_deployment_failure",
    "alert_auth_failure",
    "alert_security_violation",
    "alert_high_error_rate",
]
