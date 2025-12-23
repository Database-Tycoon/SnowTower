# SnowTower Monitoring & Observability Guide

**Comprehensive guide to monitoring, logging, auditing, and alerting in SnowTower**

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Structured Logging](#structured-logging)
- [Audit Trail](#audit-trail)
- [Metrics Collection](#metrics-collection)
- [Alerting](#alerting)
- [Monitoring Commands](#monitoring-commands)
- [Configuration](#configuration)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

SnowTower includes enterprise-grade monitoring and observability capabilities designed to provide complete visibility into infrastructure operations, user management activities, and system health.

### Key Features

- **Structured Logging**: JSON-formatted logs with correlation IDs for distributed tracing
- **Audit Trail**: Immutable audit log for compliance and security tracking
- **Metrics Collection**: Operational metrics with Prometheus export support
- **Multi-Channel Alerting**: Flexible alerting via Console, Email, Slack, and Webhooks
- **Security Focus**: Automatic masking of sensitive data in logs and audit trails

### Philosophy

- **Non-Intrusive**: Minimal performance impact on operations
- **Comprehensive**: Cover all critical infrastructure operations
- **Secure**: Never log passwords, keys, or sensitive credentials
- **Actionable**: Logs and metrics enable rapid debugging and troubleshooting

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                   SnowTower Application                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Logging    │  │  Audit Trail │  │   Metrics    │ │
│  │   System     │  │    System    │  │  Collection  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │          │
│         └──────────────────┼──────────────────┘          │
│                            │                             │
│                   ┌────────▼────────┐                    │
│                   │   Alert System  │                    │
│                   └────────┬────────┘                    │
└────────────────────────────┼─────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼────┐      ┌─────▼─────┐      ┌────▼────┐
     │ Console │      │   Email   │      │  Slack  │
     └─────────┘      └───────────┘      └─────────┘
```

### Storage Locations

```
snowtower-snowddl/
├── logs/
│   ├── snowtower.log              # Structured application logs (JSON)
│   ├── snowtower.log.1            # Rotated log files
│   └── audit/
│       ├── audit_2024-09-30.csv   # Daily audit logs
│       └── audit_2024-09-29.csv
```

---

## Structured Logging

### Overview

SnowTower uses structured JSON logging for machine-readable, searchable logs with rich context.

### Log Format

Each log entry includes:

```json
{
  "timestamp": "2024-09-30T14:23:45.123456Z",
  "level": "INFO",
  "logger": "snowtower.user_management",
  "message": "User created successfully",
  "correlation_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "operation": "user_creation",
  "username": "JOHN_DOE",
  "user_type": "PERSON"
}
```

### Usage in Code

```python
from snowtower_core.logging import get_logger, correlation_context

logger = get_logger(__name__)

# Simple logging
logger.info("Operation started")

# With context
logger.info("User created", extra={
    "username": "JOHN_DOE",
    "user_type": "PERSON",
    "operation": "user_creation"
})

# With correlation ID
with correlation_context():
    logger.info("Starting complex operation")
    # ... perform operations ...
    logger.info("Operation completed")
    # Both logs share the same correlation_id
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (non-critical issues)
- **ERROR**: Error messages (operation failed)
- **CRITICAL**: Critical system failures

### Sensitive Data Masking

Passwords, keys, and secrets are automatically masked:

```python
logger.info("User config", extra={"password": "secret123"})
# Output: {"password": "***MASKED***"}
```

Masked patterns:
- `password`, `encrypted_password`
- `api_key`, `secret`, `token`
- `rsa_key`, `private_key`
- Environment variables like `SNOWFLAKE_PASSWORD`

### Configuration

Via environment variables:

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export SNOWTOWER_LOG_LEVEL=INFO

# Log file location (default: logs/snowtower.log)
export SNOWTOWER_LOG_FILE=/var/log/snowtower/app.log
```

Via code:

```python
from snowtower_core.logging import setup_logging

setup_logging(
    log_level="INFO",
    log_file=Path("/var/log/snowtower/app.log"),
    json_format=True,
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5
)
```

---

## Audit Trail

### Overview

Immutable audit log tracking all infrastructure changes for compliance, security, and debugging.

### Tracked Operations

**User Management:**
- User creation, updates, deletion
- Password changes
- RSA key rotation
- User enable/disable

**Infrastructure:**
- SnowDDL plan and apply operations
- Warehouse configuration changes
- Role assignments
- Security policy updates

**Authentication:**
- Authentication attempts (success/failure)
- MFA enable/disable

### Audit Event Format (CSV)

```csv
timestamp,correlation_id,action,actor,resource_type,resource_id,status,old_value,new_value,metadata,error_message
2024-09-30T14:23:45Z,a1b2c3d4...,user_create,admin,user,JOHN_DOE,success,,"{'type':'PERSON','email':'john@company.com'}",,
```

### Usage in Code

```python
from snowtower_core.audit import get_audit_logger

audit = get_audit_logger()

# Log user creation
audit.log_user_creation("JOHN_DOE", {
    "type": "PERSON",
    "email": "john@company.com"
})

# Log infrastructure change
audit.log_event(
    action="warehouse_resize",
    resource_type="warehouse",
    resource_id="COMPUTE_WH",
    old_value={"size": "SMALL"},
    new_value={"size": "MEDIUM"}
)

# Query audit trail
recent_events = audit.get_recent_events(hours=24)
user_activity = audit.get_user_activity("JOHN_DOE", days=30)
```

### Querying Audit Logs

```python
# Filter by multiple criteria
events = audit.query_events(
    start_date=datetime(2024, 9, 1),
    action="user_create",
    resource_type="user",
    actor="admin",
    limit=100
)

# Generate compliance report
report = audit.get_compliance_report(
    start_date=datetime(2024, 9, 1),
    end_date=datetime(2024, 9, 30)
)
```

---

## Metrics Collection

### Overview

Collects operational metrics for monitoring system health and performance. Exports in Prometheus format.

### Available Metrics

**Operations:**
- `snowtower_operations_total` - Total operations performed
- `snowtower_operations_failed_total` - Failed operations
- `snowtower_operation_duration_seconds` - Operation duration histogram

**User Management:**
- `snowtower_users_created_total` - Users created
- `snowtower_users_updated_total` - Users updated
- `snowtower_users_deleted_total` - Users deleted
- `snowtower_active_users` - Active users (gauge)

**SnowDDL:**
- `snowtower_snowddl_plans_total` - SnowDDL plan operations
- `snowtower_snowddl_applies_total` - SnowDDL apply operations
- `snowtower_snowddl_apply_duration_seconds` - Apply duration histogram
- `snowtower_snowddl_changes_applied_total` - Changes applied

**Errors:**
- `snowtower_errors_total` - Total errors by type

**Authentication:**
- `snowtower_auth_attempts_total` - Authentication attempts
- `snowtower_auth_failures_total` - Authentication failures

### Usage in Code

```python
from snowtower_core.metrics import get_metrics, track_operation

metrics = get_metrics()

# Track operation duration
with track_operation("user_creation"):
    create_user(...)

# Manual metric recording
metrics.increment("custom_counter", labels={"type": "example"})
metrics.set_gauge("queue_size", 42)
metrics.observe("request_duration", 0.234)  # seconds

# Export metrics
prometheus_text = metrics.export_prometheus()
json_metrics = metrics.export_json()
```

### Metric Types

**Counter** - Monotonically increasing value:
```python
counter = metrics.register_counter("requests_total", "Total requests")
counter.increment()
```

**Gauge** - Value that can go up or down:
```python
gauge = metrics.register_gauge("queue_size", "Queue size")
gauge.set(42)
gauge.increment(5)
gauge.decrement(3)
```

**Histogram** - Distribution of values:
```python
histogram = metrics.register_histogram("duration_seconds", "Duration")
histogram.observe(0.234)

# Get percentiles
p95 = histogram.get_percentile(95)
p99 = histogram.get_percentile(99)
```

---

## Alerting

### Overview

Multi-channel alerting system for critical events with throttling and deduplication.

### Alert Severities

- **INFO**: Informational alerts
- **WARNING**: Warning conditions
- **ERROR**: Error conditions requiring attention
- **CRITICAL**: Critical issues requiring immediate action

### Supported Channels

#### 1. Console

Prints alerts to console (always enabled):

```python
# Automatically configured
```

#### 2. Slack

Sends formatted alerts to Slack via webhook:

```bash
export SNOWTOWER_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
export SNOWTOWER_SLACK_CHANNEL=#alerts  # Optional
```

#### 3. Email

Sends email alerts via SMTP:

```bash
export SNOWTOWER_SMTP_HOST=smtp.gmail.com
export SNOWTOWER_SMTP_PORT=587
export SNOWTOWER_SMTP_USERNAME=alerts@company.com
export SNOWTOWER_SMTP_PASSWORD=your_password
export SNOWTOWER_ALERT_FROM_EMAIL=alerts@company.com
export SNOWTOWER_ALERT_TO_EMAILS=admin@company.com,ops@company.com
```

#### 4. Webhook

Generic HTTP webhook for custom integrations:

```bash
export SNOWTOWER_ALERT_WEBHOOK_URL=https://your-endpoint.com/alerts
```

### Usage in Code

```python
from snowtower_core.alerts import (
    get_alert_manager,
    Alert,
    AlertSeverity,
    alert_deployment_failure
)

alert_mgr = get_alert_manager()

# Send custom alert
alert = Alert(
    severity=AlertSeverity.ERROR,
    title="Deployment Failed",
    message="Failed to apply 5 changes to Snowflake",
    source="snowddl_apply",
    metadata={
        "changes_count": 5,
        "error": "Connection timeout"
    }
)
alert_mgr.send_alert(alert)

# Convenience functions
alert_deployment_failure("Connection timeout", changes_count=5)
alert_auth_failure("JOHN_DOE", "RSA", "Invalid key")
alert_security_violation("Policy detached", "Network policy removed")
alert_high_error_rate("user_creation", error_count=10, total_count=50)
```

### Alert Throttling

Prevents alert flooding:

- **Deduplication**: Same alert won't be sent within 60 minutes
- **Throttling**: Maximum 10 alerts per source per 5 minutes

```python
alert_mgr = AlertManager(
    dedup_window_minutes=60,
    throttle_window_minutes=5,
    max_alerts_per_window=10
)
```

### Alert Thresholds

Define automatic alerts based on metric thresholds:

```python
from snowtower_core.alerts import AlertThreshold, AlertSeverity

alert_mgr.add_threshold(AlertThreshold(
    metric_name="error_rate",
    threshold_value=10.0,
    comparison=">",
    window_minutes=5,
    severity=AlertSeverity.WARNING
))

# Check thresholds
metrics = {"error_rate": 15.2}
alert_mgr.check_thresholds(metrics)  # Triggers alert
```

---

## Monitoring Commands

### 1. System Health Check

Check overall system health:

```bash
# Basic health check
uv run monitor-health

# Detailed output
uv run monitor-health --detailed

# JSON output (for automation)
uv run monitor-health --json
```

**Output:**
- Logging system status
- Audit trail status
- Metrics summary
- Alert system status
- Error rates
- Recent activity

### 2. Log Viewer

View and filter structured logs:

```bash
# View last 100 logs
uv run monitor-logs

# Filter by level
uv run monitor-logs --level ERROR

# Filter by operation
uv run monitor-logs --operation user_creation

# View specific log file
uv run monitor-logs --file logs/snowtower.log.1

# Show last 50 logs
uv run monitor-logs --tail 50

# Logs since specific date
uv run monitor-logs --since "2024-09-30T00:00:00"
```

### 3. Audit Trail Viewer

Query and analyze audit events:

```bash
# View recent audit events
uv run monitor-audit

# Filter by action
uv run monitor-audit --action user_create

# Filter by resource type
uv run monitor-audit --resource-type user

# Filter by actor
uv run monitor-audit --actor admin

# Last 30 days
uv run monitor-audit --days 30

# Generate compliance report
uv run monitor-audit --compliance-report

# JSON output
uv run monitor-audit --json
```

### 4. Metrics Viewer

Display operational metrics:

```bash
# View metrics summary
uv run monitor-metrics

# Prometheus format
uv run monitor-metrics --prometheus

# JSON format
uv run monitor-metrics --json
```

---

## Configuration

### Environment Variables

```bash
# Logging
export SNOWTOWER_LOG_LEVEL=INFO
export SNOWTOWER_LOG_FILE=/var/log/snowtower/app.log

# Slack Alerts
export SNOWTOWER_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
export SNOWTOWER_SLACK_CHANNEL=#alerts

# Email Alerts
export SNOWTOWER_SMTP_HOST=smtp.gmail.com
export SNOWTOWER_SMTP_PORT=587
export SNOWTOWER_SMTP_USERNAME=alerts@company.com
export SNOWTOWER_SMTP_PASSWORD=your_password
export SNOWTOWER_ALERT_FROM_EMAIL=alerts@company.com
export SNOWTOWER_ALERT_TO_EMAILS=admin@company.com,ops@company.com

# Generic Webhook
export SNOWTOWER_ALERT_WEBHOOK_URL=https://your-endpoint.com/alerts
```

### Programmatic Configuration

```python
from pathlib import Path
from snowtower_core.logging import setup_logging
from snowtower_core.audit import AuditLogger
from snowtower_core.alerts import AlertManager, SlackAlertChannel

# Configure logging
setup_logging(
    log_level="INFO",
    log_file=Path("/var/log/snowtower/app.log"),
    json_format=True
)

# Configure audit
audit = AuditLogger(
    audit_dir=Path("/var/log/snowtower/audit"),
    format="csv"
)

# Configure alerts
alert_mgr = AlertManager()
alert_mgr.add_channel(SlackAlertChannel(
    webhook_url="https://hooks.slack.com/...",
    channel="#alerts"
))
```

---

## Integration Examples

### Example 1: User Creation with Full Monitoring

```python
from snowtower_core.logging import get_logger, correlation_context
from snowtower_core.audit import get_audit_logger
from snowtower_core.metrics import get_metrics, track_operation
from snowtower_core.alerts import alert_high_error_rate

logger = get_logger(__name__)
audit = get_audit_logger()
metrics = get_metrics()

def create_user(username, config):
    """Create user with full monitoring"""

    with correlation_context():
        logger.info("Creating user", extra={"username": username})

        try:
            with track_operation("user_creation"):
                # Create user
                result = _do_create_user(username, config)

                # Log success
                logger.info("User created successfully", extra={
                    "username": username,
                    "user_type": config.get('type')
                })

                # Audit trail
                audit.log_user_creation(username, config)

                # Metrics
                metrics.increment("snowtower_users_created_total", labels={
                    "user_type": config.get('type')
                })

                return result

        except Exception as e:
            logger.error(f"User creation failed", extra={
                "username": username,
                "error": str(e)
            }, exc_info=True)

            # Record error metric
            metrics.increment("snowtower_errors_total", labels={
                "operation": "user_creation",
                "error_type": type(e).__name__
            })

            raise
```

### Example 2: SnowDDL Apply with Monitoring

```python
def snowddl_apply_monitored(changes_count):
    """SnowDDL apply with comprehensive monitoring"""

    with correlation_context() as corr_id:
        logger.info("Starting SnowDDL apply", extra={
            "changes_count": changes_count
        })

        try:
            with track_operation("snowddl_apply"):
                # Apply changes
                result = subprocess.run([...], capture_output=True)

                if result.returncode == 0:
                    # Success
                    logger.info("SnowDDL apply successful")
                    audit.log_snowddl_apply(changes_count, success=True)
                    metrics.increment("snowtower_snowddl_applies_total")
                    metrics.increment("snowtower_snowddl_changes_applied_total",
                                     amount=changes_count)
                else:
                    # Failure
                    error = result.stderr.decode()
                    logger.error("SnowDDL apply failed", extra={"error": error})
                    audit.log_snowddl_apply(changes_count, success=False, error=error)

                    # Send alert
                    alert_deployment_failure(error, changes_count)

                    raise Exception(f"SnowDDL apply failed: {error}")

        except Exception as e:
            metrics.increment("snowtower_errors_total", labels={
                "operation": "snowddl_apply"
            })
            raise
```

---

## Troubleshooting

### Logs Not Appearing

**Problem**: No logs in `logs/snowtower.log`

**Solutions:**
1. Check if logs directory exists and is writable
2. Verify `SNOWTOWER_LOG_LEVEL` is set appropriately
3. Check if logging is initialized: `setup_logging()`
4. Ensure application has write permissions

```bash
mkdir -p logs
chmod 755 logs
export SNOWTOWER_LOG_LEVEL=DEBUG
```

### Audit Events Missing

**Problem**: Audit trail not recording events

**Solutions:**
1. Check audit directory exists: `logs/audit/`
2. Verify audit logger is initialized
3. Check file permissions

```python
from snowtower_core.audit import get_audit_logger

audit = get_audit_logger()
print(f"Audit directory: {audit.audit_dir}")
```

### Alerts Not Sending

**Problem**: Alerts not being delivered

**Solutions:**
1. Check alert channels are configured
2. Verify environment variables are set
3. Check alert throttling/deduplication
4. Test channel connectivity

```python
from snowtower_core.alerts import get_alert_manager

alert_mgr = get_alert_manager()
print(f"Configured channels: {len(alert_mgr.channels)}")
for channel in alert_mgr.channels:
    print(f"  - {channel.get_name()}")
```

### Metrics Not Collecting

**Problem**: Metrics showing zeros

**Solutions:**
1. Ensure operations are using `track_operation()` context manager
2. Verify metrics are being incremented
3. Check global metrics instance

```python
from snowtower_core.metrics import get_metrics

metrics = get_metrics()
summary = metrics.get_summary()
print(summary)
```

---

## Best Practices

### 1. Use Correlation IDs

Always use correlation contexts for multi-step operations:

```python
with correlation_context():
    # All logs share the same correlation_id
    step1()
    step2()
    step3()
```

### 2. Log at Appropriate Levels

- **DEBUG**: Detailed diagnostic info (development only)
- **INFO**: Normal operations
- **WARNING**: Unexpected but handled situations
- **ERROR**: Operation failures
- **CRITICAL**: System-wide failures

### 3. Include Context in Logs

Always include relevant context:

```python
logger.info("Processing user", extra={
    "username": username,
    "operation": "update",
    "user_type": user_type
})
```

### 4. Track All Critical Operations

Use `track_operation()` for timing and error tracking:

```python
with track_operation("critical_operation"):
    perform_operation()
```

### 5. Audit All State Changes

Log to audit trail for any data modification:

```python
audit.log_event(
    action="state_change",
    resource_type="resource",
    resource_id="ID",
    old_value=old_state,
    new_value=new_state
)
```

### 6. Set Up Alerting Early

Configure alert channels during deployment:

```bash
# Add to .env
SNOWTOWER_SLACK_WEBHOOK_URL=https://...
SNOWTOWER_ALERT_TO_EMAILS=team@company.com
```

### 7. Regular Monitoring

Schedule regular health checks:

```bash
# Add to cron
0 */4 * * * cd /path/to/snowtower && uv run monitor-health --json > /var/log/health.log
```

### 8. Review Audit Logs Regularly

Generate compliance reports periodically:

```bash
uv run monitor-audit --compliance-report --days 30 > monthly_compliance_report.txt
```

### 9. Monitor Error Rates

Set up threshold alerts for error rates:

```python
alert_mgr.add_threshold(AlertThreshold(
    metric_name="error_rate",
    threshold_value=5.0,  # 5%
    comparison=">",
    severity=AlertSeverity.WARNING
))
```

### 10. Export Metrics to Prometheus

For production deployments, expose metrics endpoint:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
from snowtower_core.metrics import get_metrics

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            metrics = get_metrics()
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(metrics.export_prometheus().encode())

server = HTTPServer(('0.0.0.0', 9090), MetricsHandler)
server.serve_forever()
```

---

## Appendix: Log Query Examples

### Find All Failed Operations

```bash
uv run monitor-logs --level ERROR --tail 1000
```

### Track User Activity

```bash
uv run monitor-audit --resource-id JOHN_DOE --days 30
```

### Monitor Deployment Success Rate

```bash
uv run monitor-audit --action snowddl_apply --days 7
```

### Check Error Rate Trends

```bash
uv run monitor-metrics --json | jq '.operations'
```

### Find Security Events

```bash
uv run monitor-audit --action auth_failure --days 7
```

---

## Support

For issues or questions about monitoring:

1. Check this documentation
2. Review logs: `uv run monitor-logs --level ERROR`
3. Check system health: `uv run monitor-health --detailed`
4. Review audit trail: `uv run monitor-audit --compliance-report`

---

**Last Updated**: 2024-09-30
**Version**: 1.0.0
