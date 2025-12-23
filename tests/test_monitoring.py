"""
Unit Tests for SnowTower Monitoring Components

Tests for logging, audit, metrics, and alerting systems.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add src to path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import directly from snowtower_core module files
import importlib.util

# Load logging module
spec = importlib.util.spec_from_file_location(
    "st_logging", src_path / "snowtower_core" / "logging.py"
)
st_logging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st_logging)
get_logger = st_logging.get_logger
setup_logging = st_logging.setup_logging
correlation_context = st_logging.correlation_context
get_correlation_id = st_logging.get_correlation_id
set_correlation_id = st_logging.set_correlation_id
log_operation_start = st_logging.log_operation_start
log_operation_success = st_logging.log_operation_success
log_operation_failure = st_logging.log_operation_failure

# Load audit module
spec = importlib.util.spec_from_file_location(
    "st_audit", src_path / "snowtower_core" / "audit.py"
)
st_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st_audit)
AuditLogger = st_audit.AuditLogger
AuditEvent = st_audit.AuditEvent
AuditAction = st_audit.AuditAction
AuditStatus = st_audit.AuditStatus

# Load metrics module
spec = importlib.util.spec_from_file_location(
    "st_metrics", src_path / "snowtower_core" / "metrics.py"
)
st_metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st_metrics)
MetricsCollector = st_metrics.MetricsCollector
Counter = st_metrics.Counter
Gauge = st_metrics.Gauge
Histogram = st_metrics.Histogram
track_operation = st_metrics.track_operation

# Load alerts module
spec = importlib.util.spec_from_file_location(
    "st_alerts", src_path / "snowtower_core" / "alerts.py"
)
st_alerts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st_alerts)
AlertManager = st_alerts.AlertManager
Alert = st_alerts.Alert
AlertSeverity = st_alerts.AlertSeverity
ConsoleAlertChannel = st_alerts.ConsoleAlertChannel


class TestStructuredLogging:
    """Test structured logging functionality"""

    def test_logger_creation(self):
        """Test logger can be created"""
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"

    def test_correlation_id_context(self):
        """Test correlation ID context manager"""
        assert get_correlation_id() is None

        with correlation_context() as corr_id:
            assert corr_id is not None
            assert get_correlation_id() == corr_id

        # Context cleared after exit
        assert get_correlation_id() is None

    def test_set_correlation_id(self):
        """Test manual correlation ID setting"""
        test_id = "test-correlation-id"
        result = set_correlation_id(test_id)
        assert result == test_id
        assert get_correlation_id() == test_id

    def test_log_operation_helpers(self):
        """Test operation logging helper functions"""
        logger = get_logger("test")

        # These should not raise exceptions
        log_operation_start(logger, "test_op")
        log_operation_success(logger, "test_op", duration_ms=123.45)
        log_operation_failure(logger, "test_op", Exception("Test error"))


class TestAuditTrail:
    """Test audit trail functionality"""

    def test_audit_logger_creation(self, tmp_path):
        """Test audit logger can be created"""
        audit = AuditLogger(audit_dir=tmp_path / "audit")
        assert audit.audit_dir.exists()

    def test_audit_event_creation(self):
        """Test audit event can be created"""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            correlation_id="test-id",
            action="user_create",
            actor="admin",
            resource_type="user",
            resource_id="TEST_USER",
            status="success",
        )
        assert event.action == "user_create"
        assert event.resource_id == "TEST_USER"

    def test_log_user_creation(self, tmp_path):
        """Test logging user creation"""
        audit = AuditLogger(audit_dir=tmp_path / "audit", format="csv")

        user_config = {"type": "PERSON", "email": "test@example.com"}

        audit.log_user_creation("TEST_USER", user_config)

        # Verify audit file was created
        audit_files = list((tmp_path / "audit").glob("audit_*.csv"))
        assert len(audit_files) > 0

    def test_query_events(self, tmp_path):
        """Test querying audit events"""
        audit = AuditLogger(audit_dir=tmp_path / "audit", format="csv")

        # Log some events
        for i in range(5):
            audit.log_event(
                action="test_action",
                resource_type="test",
                resource_id=f"resource_{i}",
                status="success",
            )

        # Query events
        events = audit.query_events(action="test_action")
        assert len(events) == 5

    def test_get_recent_events(self, tmp_path):
        """Test getting recent events"""
        audit = AuditLogger(audit_dir=tmp_path / "audit")

        audit.log_event(
            action="test_action",
            resource_type="test",
            resource_id="test_resource",
            status="success",
        )

        recent = audit.get_recent_events(hours=24)
        assert len(recent) > 0


class TestMetricsCollection:
    """Test metrics collection functionality"""

    def test_metrics_collector_creation(self):
        """Test metrics collector can be created"""
        metrics = MetricsCollector()
        assert metrics is not None

    def test_counter_metric(self):
        """Test counter metric"""
        counter = Counter(name="test_counter", help_text="Test counter")
        counter.increment()
        counter.increment(5)

        assert counter.get() == 6.0

    def test_counter_with_labels(self):
        """Test counter with labels"""
        counter = Counter(name="test_counter", help_text="Test counter")
        counter.increment(labels={"type": "a"})
        counter.increment(2, labels={"type": "a"})
        counter.increment(labels={"type": "b"})

        assert counter.get(labels={"type": "a"}) == 3.0
        assert counter.get(labels={"type": "b"}) == 1.0

    def test_gauge_metric(self):
        """Test gauge metric"""
        gauge = Gauge(name="test_gauge", help_text="Test gauge")
        gauge.set(10)
        gauge.increment(5)
        gauge.decrement(3)

        assert gauge.get() == 12.0

    def test_histogram_metric(self):
        """Test histogram metric"""
        histogram = Histogram(name="test_histogram", help_text="Test histogram")

        # Record some observations
        for value in [0.1, 0.2, 0.3, 0.4, 0.5]:
            histogram.observe(value)

        assert histogram.get_count() == 5
        assert histogram.get_sum() == pytest.approx(1.5)

    def test_histogram_percentiles(self):
        """Test histogram percentile calculations"""
        histogram = Histogram(name="test_histogram", help_text="Test histogram")

        # Record 100 observations
        for i in range(1, 101):
            histogram.observe(i)

        p50 = histogram.get_percentile(50)
        p95 = histogram.get_percentile(95)
        p99 = histogram.get_percentile(99)

        assert p50 is not None
        assert p95 is not None
        assert p99 is not None
        assert p50 < p95 < p99

    def test_track_operation_success(self):
        """Test track_operation context manager with success"""
        metrics = MetricsCollector()

        with track_operation("test_operation", metrics):
            pass  # Successful operation

        # Check metrics were recorded
        assert (
            metrics._counters["snowtower_operations_total"].get(
                labels={"operation": "test_operation"}
            )
            == 1.0
        )

    def test_track_operation_failure(self):
        """Test track_operation context manager with failure"""
        metrics = MetricsCollector()

        try:
            with track_operation("test_operation", metrics):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Check failure was recorded
        assert (
            metrics._counters["snowtower_operations_failed_total"].get(
                labels={"operation": "test_operation"}
            )
            == 1.0
        )

    def test_prometheus_export(self):
        """Test Prometheus format export"""
        metrics = MetricsCollector()

        metrics.increment("snowtower_operations_total")
        prometheus_output = metrics.export_prometheus()

        assert "snowtower_operations_total" in prometheus_output
        assert "# HELP" in prometheus_output
        assert "# TYPE" in prometheus_output

    def test_json_export(self):
        """Test JSON format export"""
        metrics = MetricsCollector()

        metrics.increment("snowtower_operations_total")
        json_output = metrics.export_json()

        assert "counters" in json_output
        assert "gauges" in json_output
        assert "histograms" in json_output
        assert "timestamp" in json_output


class TestAlertSystem:
    """Test alerting system functionality"""

    def test_alert_manager_creation(self):
        """Test alert manager can be created"""
        alert_mgr = AlertManager()
        assert alert_mgr is not None

    def test_alert_creation(self):
        """Test alert can be created"""
        alert = Alert(
            severity=AlertSeverity.ERROR,
            title="Test Alert",
            message="This is a test alert",
            source="test",
        )

        assert alert.severity == AlertSeverity.ERROR
        assert alert.title == "Test Alert"
        assert alert.fingerprint is not None

    def test_console_alert_channel(self):
        """Test console alert channel"""
        channel = ConsoleAlertChannel()

        alert = Alert(
            severity=AlertSeverity.INFO,
            title="Test Alert",
            message="Test message",
            source="test",
        )

        # Should not raise exception
        result = channel.send(alert)
        assert result is True

    def test_alert_deduplication(self):
        """Test alert deduplication"""
        alert_mgr = AlertManager(dedup_window_minutes=1)
        alert_mgr.add_channel(ConsoleAlertChannel())

        alert = Alert(
            severity=AlertSeverity.INFO,
            title="Test Alert",
            message="Test message",
            source="test",
        )

        # First alert should succeed
        result1 = alert_mgr.send_alert(alert)
        assert result1 is True

        # Duplicate should be blocked
        result2 = alert_mgr.send_alert(alert)
        assert result2 is False

    def test_alert_throttling(self):
        """Test alert throttling"""
        alert_mgr = AlertManager(throttle_window_minutes=1, max_alerts_per_window=2)
        alert_mgr.add_channel(ConsoleAlertChannel())

        # Send alerts up to the limit
        for i in range(2):
            alert = Alert(
                severity=AlertSeverity.INFO,
                title=f"Alert {i}",
                message="Test",
                source="test",
            )
            result = alert_mgr.send_alert(alert)
            assert result is True

        # Next alert should be throttled
        alert = Alert(
            severity=AlertSeverity.INFO, title="Alert 3", message="Test", source="test"
        )
        result = alert_mgr.send_alert(alert)
        assert result is False

    def test_get_recent_alerts(self):
        """Test getting recent alerts"""
        alert_mgr = AlertManager()
        alert_mgr.add_channel(ConsoleAlertChannel())

        alert = Alert(
            severity=AlertSeverity.INFO,
            title="Test Alert",
            message="Test",
            source="test",
        )

        alert_mgr.send_alert(alert)

        recent = alert_mgr.get_recent_alerts(hours=1)
        assert len(recent) > 0


class TestIntegration:
    """Integration tests combining multiple monitoring components"""

    def test_full_operation_monitoring(self, tmp_path):
        """Test complete monitoring of an operation"""
        # Setup
        audit = AuditLogger(audit_dir=tmp_path / "audit")
        metrics = MetricsCollector()
        alert_mgr = AlertManager()

        # Simulate operation
        with correlation_context() as corr_id:
            with track_operation("test_operation", metrics):
                # Log to audit
                audit.log_event(
                    action="test_action",
                    resource_type="test",
                    resource_id="test_resource",
                    status="success",
                )

        # Verify all monitoring systems recorded the operation
        assert (
            metrics._counters["snowtower_operations_total"].get(
                labels={"operation": "test_operation"}
            )
            == 1.0
        )

        audit_events = audit.get_recent_events(hours=1)
        assert len(audit_events) > 0

    def test_error_monitoring_flow(self, tmp_path):
        """Test monitoring flow for error scenarios"""
        audit = AuditLogger(audit_dir=tmp_path / "audit")
        metrics = MetricsCollector()
        alert_mgr = AlertManager()
        alert_mgr.add_channel(ConsoleAlertChannel())

        try:
            with track_operation("error_operation", metrics):
                # Log to audit
                audit.log_event(
                    action="error_action",
                    resource_type="test",
                    resource_id="test_resource",
                    status="failure",
                    error_message="Test error",
                )

                # Send alert
                alert = Alert(
                    severity=AlertSeverity.ERROR,
                    title="Operation Failed",
                    message="Test operation failed",
                    source="test",
                )
                alert_mgr.send_alert(alert)

                # Raise error to trigger failure tracking
                raise ValueError("Test error")

        except ValueError:
            pass

        # Verify error was tracked
        assert (
            metrics._counters["snowtower_operations_failed_total"].get(
                labels={"operation": "error_operation"}
            )
            == 1.0
        )

        # Verify alert was sent
        assert len(alert_mgr.alert_history) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
