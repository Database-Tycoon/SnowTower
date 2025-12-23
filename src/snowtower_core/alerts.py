"""
Alerting Framework for SnowTower

Provides multi-channel alerting capabilities for critical events:
- Failed SnowDDL deployments
- Authentication failures
- Security policy violations
- High error rates
- Resource utilization issues

Features:
- Multiple alert channels (Email, Webhook, Slack, Console)
- Alert severity levels (INFO, WARNING, ERROR, CRITICAL)
- Alert throttling and deduplication
- Alert aggregation
- Configurable thresholds
- Alert acknowledgment tracking

Usage:
    from snowtower_core.alerts import AlertManager, Alert, AlertSeverity

    alert_mgr = AlertManager()

    # Send alert
    alert_mgr.send_alert(
        Alert(
            severity=AlertSeverity.ERROR,
            title="SnowDDL Deployment Failed",
            message="Failed to apply 5 changes to Snowflake",
            source="snowddl_apply"
        )
    )

    # Configure alert channels
    alert_mgr.add_channel(SlackAlertChannel(webhook_url="..."))
    alert_mgr.add_channel(EmailAlertChannel(smtp_config={...}))
"""

import json
import smtplib
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Protocol
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
from threading import Lock
import hashlib
import os

from .logging import get_logger, get_correlation_id

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """
    Represents an alert.

    Attributes:
        severity: Alert severity level
        title: Short alert title
        message: Detailed alert message
        source: Source system/component that generated the alert
        metadata: Additional context about the alert
        timestamp: When the alert was created
        correlation_id: Correlation ID for tracking
        fingerprint: Unique fingerprint for deduplication
    """

    severity: AlertSeverity
    title: str
    message: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None
    correlation_id: Optional[str] = None
    fingerprint: Optional[str] = None

    def __post_init__(self):
        """Initialize computed fields"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

        if self.correlation_id is None:
            self.correlation_id = get_correlation_id()

        if self.fingerprint is None:
            self.fingerprint = self._compute_fingerprint()

    def _compute_fingerprint(self) -> str:
        """Compute unique fingerprint for deduplication"""
        content = f"{self.source}:{self.title}:{self.severity.value}"
        return hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["severity"] = self.severity.value
        return data

    def format_console(self) -> str:
        """Format for console output"""
        severity_colors = {
            AlertSeverity.INFO: "\033[36m",  # Cyan
            AlertSeverity.WARNING: "\033[33m",  # Yellow
            AlertSeverity.ERROR: "\033[31m",  # Red
            AlertSeverity.CRITICAL: "\033[35m",  # Magenta
        }
        reset = "\033[0m"

        color = severity_colors.get(self.severity, "")
        timestamp = datetime.fromisoformat(
            self.timestamp.replace("Z", "+00:00")
        ).strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"{color}[{self.severity.value.upper()}]{reset} {timestamp}",
            f"Source: {self.source}",
            f"Title: {self.title}",
            f"Message: {self.message}",
        ]

        if self.metadata:
            lines.append("Metadata:")
            for key, value in self.metadata.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)


class AlertChannel(Protocol):
    """Protocol for alert channels"""

    def send(self, alert: Alert) -> bool:
        """
        Send alert through this channel.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        ...

    def get_name(self) -> str:
        """Get channel name"""
        ...


class ConsoleAlertChannel:
    """Alert channel that prints to console"""

    def get_name(self) -> str:
        return "console"

    def send(self, alert: Alert) -> bool:
        """Print alert to console"""
        try:
            print("\n" + "=" * 80)
            print(alert.format_console())
            print("=" * 80 + "\n")
            return True
        except Exception as e:
            logger.error(f"Failed to send console alert: {e}")
            return False


class WebhookAlertChannel:
    """
    Alert channel that sends via HTTP webhook.

    Supports generic webhook format with JSON payload.
    """

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize webhook channel.

        Args:
            webhook_url: URL to POST alerts to
            headers: Optional HTTP headers
        """
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}

    def get_name(self) -> str:
        return f"webhook:{self.webhook_url}"

    def send(self, alert: Alert) -> bool:
        """Send alert via webhook"""
        try:
            payload = alert.to_dict()
            response = requests.post(
                self.webhook_url, json=payload, headers=self.headers, timeout=10
            )
            response.raise_for_status()
            logger.info(f"Alert sent via webhook: {alert.title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class SlackAlertChannel:
    """
    Alert channel for Slack via webhook.

    Uses Slack's incoming webhook format.
    """

    SEVERITY_COLORS = {
        AlertSeverity.INFO: "#36a64f",  # Green
        AlertSeverity.WARNING: "#ff9900",  # Orange
        AlertSeverity.ERROR: "#ff0000",  # Red
        AlertSeverity.CRITICAL: "#990000",  # Dark red
    }

    def __init__(
        self,
        webhook_url: str,
        channel: Optional[str] = None,
        username: str = "SnowTower",
    ):
        """
        Initialize Slack channel.

        Args:
            webhook_url: Slack incoming webhook URL
            channel: Override default channel (e.g., "#alerts")
            username: Bot username to display
        """
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username

    def get_name(self) -> str:
        return f"slack:{self.channel or 'default'}"

    def send(self, alert: Alert) -> bool:
        """Send alert to Slack"""
        try:
            color = self.SEVERITY_COLORS.get(alert.severity, "#808080")

            payload = {
                "username": self.username,
                "icon_emoji": ":rotating_light:",
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.severity.value.upper()}] {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {"title": "Source", "value": alert.source, "short": True},
                            {
                                "title": "Timestamp",
                                "value": alert.timestamp,
                                "short": True,
                            },
                        ],
                        "footer": "SnowTower Monitoring",
                        "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                        "ts": int(datetime.utcnow().timestamp()),
                    }
                ],
            }

            if self.channel:
                payload["channel"] = self.channel

            # Add metadata fields
            for key, value in alert.metadata.items():
                payload["attachments"][0]["fields"].append(
                    {"title": key, "value": str(value), "short": True}
                )

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Alert sent to Slack: {alert.title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False


class EmailAlertChannel:
    """
    Alert channel for email notifications.

    Supports SMTP email delivery.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_addr: str,
        to_addrs: List[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
    ):
        """
        Initialize email channel.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            from_addr: From email address
            to_addrs: List of recipient email addresses
            username: SMTP username (if required)
            password: SMTP password (if required)
            use_tls: Whether to use TLS
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def get_name(self) -> str:
        return f"email:{','.join(self.to_addrs)}"

    def send(self, alert: Alert) -> bool:
        """Send alert via email"""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[SnowTower {alert.severity.value.upper()}] {alert.title}"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            # Plain text version
            text_body = f"""
SnowTower Alert

Severity: {alert.severity.value.upper()}
Source: {alert.source}
Timestamp: {alert.timestamp}

Title: {alert.title}

Message:
{alert.message}

Metadata:
{json.dumps(alert.metadata, indent=2)}

Correlation ID: {alert.correlation_id}
            """.strip()

            # HTML version
            html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .header {{ background-color: #f0f0f0; padding: 10px; }}
        .severity-{alert.severity.value} {{ color: white; padding: 5px 10px; border-radius: 3px; }}
        .severity-info {{ background-color: #36a64f; }}
        .severity-warning {{ background-color: #ff9900; }}
        .severity-error {{ background-color: #ff0000; }}
        .severity-critical {{ background-color: #990000; }}
        .content {{ padding: 20px; }}
        .metadata {{ background-color: #f9f9f9; padding: 10px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>SnowTower Alert</h2>
        <span class="severity-{alert.severity.value}">{alert.severity.value.upper()}</span>
    </div>
    <div class="content">
        <p><strong>Source:</strong> {alert.source}</p>
        <p><strong>Timestamp:</strong> {alert.timestamp}</p>
        <h3>{alert.title}</h3>
        <p>{alert.message}</p>
        <div class="metadata">
            <strong>Metadata:</strong>
            <pre>{json.dumps(alert.metadata, indent=2)}</pre>
        </div>
        <p style="color: #888; font-size: 12px; margin-top: 20px;">
            Correlation ID: {alert.correlation_id}
        </p>
    </div>
</body>
</html>
            """

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Alert sent via email: {alert.title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False


@dataclass
class AlertThreshold:
    """
    Alert threshold configuration.

    Defines when to trigger an alert based on metric values.
    """

    metric_name: str
    threshold_value: float
    comparison: str = ">"  # >, <, >=, <=, ==
    window_minutes: int = 5
    severity: AlertSeverity = AlertSeverity.WARNING


class AlertManager:
    """
    Central alert management system.

    Manages alert channels, throttling, deduplication, and delivery.
    """

    def __init__(
        self,
        dedup_window_minutes: int = 60,
        throttle_window_minutes: int = 5,
        max_alerts_per_window: int = 10,
    ):
        """
        Initialize alert manager.

        Args:
            dedup_window_minutes: Deduplication window (same alert within this time won't be resent)
            throttle_window_minutes: Throttling window
            max_alerts_per_window: Maximum alerts per throttle window
        """
        self.channels: List[AlertChannel] = []
        self.thresholds: List[AlertThreshold] = []

        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        self.throttle_window = timedelta(minutes=throttle_window_minutes)
        self.max_alerts_per_window = max_alerts_per_window

        # Tracking
        self._sent_alerts: Dict[str, datetime] = {}  # fingerprint -> last sent time
        self._alert_counts: Dict[str, List[datetime]] = defaultdict(
            list
        )  # source -> list of timestamps
        self._lock = Lock()

        # Alert history
        self.alert_history: List[Alert] = []
        self.max_history_size = 1000

        logger.info("AlertManager initialized")

        # Auto-configure from environment
        self._auto_configure()

    def _auto_configure(self):
        """Auto-configure alert channels from environment variables"""
        # Add console channel by default
        self.add_channel(ConsoleAlertChannel())

        # Slack
        slack_webhook = os.getenv("SNOWTOWER_SLACK_WEBHOOK_URL")
        if slack_webhook:
            slack_channel = os.getenv("SNOWTOWER_SLACK_CHANNEL")
            self.add_channel(
                SlackAlertChannel(webhook_url=slack_webhook, channel=slack_channel)
            )
            logger.info("Configured Slack alert channel")

        # Email
        smtp_host = os.getenv("SNOWTOWER_SMTP_HOST")
        if smtp_host:
            self.add_channel(
                EmailAlertChannel(
                    smtp_host=smtp_host,
                    smtp_port=int(os.getenv("SNOWTOWER_SMTP_PORT", "587")),
                    from_addr=os.getenv(
                        "SNOWTOWER_ALERT_FROM_EMAIL", "alerts@snowtower.local"
                    ),
                    to_addrs=os.getenv("SNOWTOWER_ALERT_TO_EMAILS", "").split(","),
                    username=os.getenv("SNOWTOWER_SMTP_USERNAME"),
                    password=os.getenv("SNOWTOWER_SMTP_PASSWORD"),
                    use_tls=os.getenv("SNOWTOWER_SMTP_USE_TLS", "true").lower()
                    == "true",
                )
            )
            logger.info("Configured Email alert channel")

        # Generic webhook
        webhook_url = os.getenv("SNOWTOWER_ALERT_WEBHOOK_URL")
        if webhook_url:
            self.add_channel(WebhookAlertChannel(webhook_url=webhook_url))
            logger.info("Configured Webhook alert channel")

    def add_channel(self, channel: AlertChannel):
        """Add an alert channel"""
        self.channels.append(channel)
        logger.info(f"Added alert channel: {channel.get_name()}")

    def add_threshold(self, threshold: AlertThreshold):
        """Add an alert threshold"""
        self.thresholds.append(threshold)
        logger.info(
            f"Added alert threshold: {threshold.metric_name} {threshold.comparison} {threshold.threshold_value}"
        )

    def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert through all configured channels.

        Applies deduplication and throttling.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully through at least one channel
        """
        # Check deduplication
        if self._is_duplicate(alert):
            logger.debug(f"Alert deduplicated: {alert.title}")
            return False

        # Check throttling
        if self._is_throttled(alert):
            logger.warning(f"Alert throttled: {alert.title}")
            return False

        # Send through all channels
        sent_count = 0
        for channel in self.channels:
            try:
                if channel.send(alert):
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.get_name()}: {e}")

        # Track alert
        if sent_count > 0:
            with self._lock:
                self._sent_alerts[alert.fingerprint] = datetime.utcnow()
                self._alert_counts[alert.source].append(datetime.utcnow())
                self.alert_history.append(alert)

                # Limit history size
                if len(self.alert_history) > self.max_history_size:
                    self.alert_history = self.alert_history[-self.max_history_size :]

            logger.info(f"Alert sent via {sent_count} channels: {alert.title}")
            return True

        return False

    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if alert is a duplicate within dedup window"""
        with self._lock:
            if alert.fingerprint in self._sent_alerts:
                last_sent = self._sent_alerts[alert.fingerprint]
                if datetime.utcnow() - last_sent < self.dedup_window:
                    return True
        return False

    def _is_throttled(self, alert: Alert) -> bool:
        """Check if alert source is throttled"""
        with self._lock:
            # Clean old timestamps
            cutoff = datetime.utcnow() - self.throttle_window
            self._alert_counts[alert.source] = [
                ts for ts in self._alert_counts[alert.source] if ts > cutoff
            ]

            # Check throttle
            if len(self._alert_counts[alert.source]) >= self.max_alerts_per_window:
                return True

        return False

    def check_thresholds(self, metrics: Dict[str, float]):
        """
        Check metrics against configured thresholds.

        Args:
            metrics: Dictionary of metric_name -> value
        """
        for threshold in self.thresholds:
            if threshold.metric_name not in metrics:
                continue

            value = metrics[threshold.metric_name]
            triggered = False

            if threshold.comparison == ">":
                triggered = value > threshold.threshold_value
            elif threshold.comparison == "<":
                triggered = value < threshold.threshold_value
            elif threshold.comparison == ">=":
                triggered = value >= threshold.threshold_value
            elif threshold.comparison == "<=":
                triggered = value <= threshold.threshold_value
            elif threshold.comparison == "==":
                triggered = value == threshold.threshold_value

            if triggered:
                alert = Alert(
                    severity=threshold.severity,
                    title=f"Threshold Exceeded: {threshold.metric_name}",
                    message=f"Metric {threshold.metric_name} = {value} {threshold.comparison} {threshold.threshold_value}",
                    source="threshold_monitor",
                    metadata={
                        "metric_name": threshold.metric_name,
                        "current_value": value,
                        "threshold_value": threshold.threshold_value,
                        "comparison": threshold.comparison,
                    },
                )
                self.send_alert(alert)

    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """
        Get recent alerts.

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent alerts
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert
            for alert in self.alert_history
            if datetime.fromisoformat(alert.timestamp.replace("Z", "+00:00")) > cutoff
        ]


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """
    Get global alert manager instance.

    Returns:
        Global AlertManager instance
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


# Convenience functions for common alerts
def alert_deployment_failure(error_message: str, changes_count: int = 0):
    """Send alert for failed deployment"""
    alert = Alert(
        severity=AlertSeverity.ERROR,
        title="SnowDDL Deployment Failed",
        message=f"Failed to deploy infrastructure changes: {error_message}",
        source="snowddl_apply",
        metadata={"changes_count": changes_count, "error": error_message},
    )
    get_alert_manager().send_alert(alert)


def alert_auth_failure(username: str, method: str, error: str):
    """Send alert for authentication failure"""
    alert = Alert(
        severity=AlertSeverity.WARNING,
        title="Authentication Failure",
        message=f"Failed authentication attempt for user {username}",
        source="authentication",
        metadata={"username": username, "method": method, "error": error},
    )
    get_alert_manager().send_alert(alert)


def alert_security_violation(violation_type: str, details: str):
    """Send alert for security policy violation"""
    alert = Alert(
        severity=AlertSeverity.CRITICAL,
        title="Security Policy Violation",
        message=f"Security violation detected: {violation_type}",
        source="security_monitor",
        metadata={"violation_type": violation_type, "details": details},
    )
    get_alert_manager().send_alert(alert)


def alert_high_error_rate(operation: str, error_count: int, total_count: int):
    """Send alert for high error rate"""
    error_rate = (error_count / total_count * 100) if total_count > 0 else 0

    alert = Alert(
        severity=AlertSeverity.WARNING,
        title="High Error Rate Detected",
        message=f"Operation {operation} has error rate of {error_rate:.1f}%",
        source="error_monitor",
        metadata={
            "operation": operation,
            "error_count": error_count,
            "total_count": total_count,
            "error_rate_percent": round(error_rate, 2),
        },
    )
    get_alert_manager().send_alert(alert)
