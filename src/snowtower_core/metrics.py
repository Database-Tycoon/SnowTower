"""
Metrics Collection System for SnowTower

Collects and exports operational metrics including:
- Operation execution times and latency
- Error rates by operation type
- Resource utilization
- API call counts and performance
- SnowDDL deployment metrics
- User management operation metrics

Features:
- Prometheus-compatible metric export
- In-memory metric aggregation
- Time-series data collection
- Percentile calculations (p50, p95, p99)
- Counter, Gauge, and Histogram metrics
- Metric visualization support

Usage:
    from snowtower_core.metrics import get_metrics, track_operation

    metrics = get_metrics()

    # Track operation
    with track_operation("user_creation"):
        create_user(...)

    # Manual metric recording
    metrics.increment("api_calls", labels={"endpoint": "/users"})
    metrics.record_duration("snowddl_apply", 1234.56)

    # Export metrics
    prometheus_output = metrics.export_prometheus()
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque
from threading import Lock
import statistics
import json

from .logging import get_logger, get_correlation_id

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """Single metric measurement"""

    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    """
    Counter metric - monotonically increasing value.
    Used for: request counts, error counts, etc.
    """

    name: str
    help_text: str
    values: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _lock: Lock = field(default_factory=Lock, repr=False)

    def increment(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment counter"""
        label_key = self._labels_to_key(labels or {})
        with self._lock:
            self.values[label_key] += amount

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value"""
        label_key = self._labels_to_key(labels or {})
        return self.values.get(label_key, 0.0)

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to string key"""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _key_to_labels(self, key: str) -> Dict[str, str]:
        """Convert string key back to labels dict"""
        if not key:
            return {}
        return dict(pair.split("=") for pair in key.split(","))


@dataclass
class Gauge:
    """
    Gauge metric - value that can go up or down.
    Used for: current connections, queue size, temperature, etc.
    """

    name: str
    help_text: str
    values: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _lock: Lock = field(default_factory=Lock, repr=False)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value"""
        label_key = self._labels_to_key(labels or {})
        with self._lock:
            self.values[label_key] = value

    def increment(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment gauge"""
        label_key = self._labels_to_key(labels or {})
        with self._lock:
            self.values[label_key] += amount

    def decrement(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Decrement gauge"""
        self.increment(-amount, labels)

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value"""
        label_key = self._labels_to_key(labels or {})
        return self.values.get(label_key, 0.0)

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to string key"""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


@dataclass
class Histogram:
    """
    Histogram metric - tracks distribution of values.
    Used for: request durations, response sizes, etc.
    """

    name: str
    help_text: str
    buckets: List[float] = field(
        default_factory=lambda: [
            0.005,
            0.01,
            0.025,
            0.05,
            0.075,
            0.1,
            0.25,
            0.5,
            0.75,
            1.0,
            2.5,
            5.0,
            7.5,
            10.0,
            float("inf"),
        ]
    )
    observations: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _lock: Lock = field(default_factory=Lock, repr=False)
    max_observations: int = 1000  # Keep last N observations per label set

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an observation"""
        label_key = self._labels_to_key(labels or {})
        with self._lock:
            obs = self.observations[label_key]
            obs.append(value)
            # Keep only last N observations
            if len(obs) > self.max_observations:
                self.observations[label_key] = obs[-self.max_observations :]

    def get_count(self, labels: Optional[Dict[str, str]] = None) -> int:
        """Get number of observations"""
        label_key = self._labels_to_key(labels or {})
        return len(self.observations.get(label_key, []))

    def get_sum(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get sum of all observations"""
        label_key = self._labels_to_key(labels or {})
        obs = self.observations.get(label_key, [])
        return sum(obs) if obs else 0.0

    def get_percentile(
        self, percentile: float, labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """
        Get percentile value (e.g., 50.0 for median, 95.0 for p95).

        Args:
            percentile: Percentile to calculate (0-100)
            labels: Optional labels to filter by

        Returns:
            Percentile value or None if no observations
        """
        label_key = self._labels_to_key(labels or {})
        obs = self.observations.get(label_key, [])
        if not obs:
            return None

        try:
            sorted_obs = sorted(obs)
            return statistics.quantiles(sorted_obs, n=100)[int(percentile) - 1]
        except (statistics.StatisticsError, IndexError):
            return sorted_obs[0] if sorted_obs else None

    def get_bucket_counts(
        self, labels: Optional[Dict[str, str]] = None
    ) -> Dict[float, int]:
        """Get count of observations in each bucket"""
        label_key = self._labels_to_key(labels or {})
        obs = self.observations.get(label_key, [])

        bucket_counts = {}
        for bucket in self.buckets:
            bucket_counts[bucket] = sum(1 for v in obs if v <= bucket)

        return bucket_counts

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to string key"""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class MetricsCollector:
    """
    Central metrics collection system.

    Provides registration and collection of various metric types.
    """

    def __init__(self):
        """Initialize metrics collector"""
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = Lock()

        logger.info("MetricsCollector initialized")

        # Register standard metrics
        self._register_standard_metrics()

    def _register_standard_metrics(self):
        """Register standard SnowTower metrics"""
        # Operation metrics
        self.register_counter(
            "snowtower_operations_total", "Total number of operations performed"
        )
        self.register_counter(
            "snowtower_operations_failed_total", "Total number of failed operations"
        )
        self.register_histogram(
            "snowtower_operation_duration_seconds", "Duration of operations in seconds"
        )

        # User management metrics
        self.register_counter(
            "snowtower_users_created_total", "Total number of users created"
        )
        self.register_counter(
            "snowtower_users_updated_total", "Total number of users updated"
        )
        self.register_counter(
            "snowtower_users_deleted_total", "Total number of users deleted"
        )
        self.register_gauge("snowtower_active_users", "Number of active users")

        # SnowDDL metrics
        self.register_counter(
            "snowtower_snowddl_plans_total", "Total number of SnowDDL plan operations"
        )
        self.register_counter(
            "snowtower_snowddl_applies_total",
            "Total number of SnowDDL apply operations",
        )
        self.register_histogram(
            "snowtower_snowddl_apply_duration_seconds",
            "Duration of SnowDDL apply operations",
        )
        self.register_counter(
            "snowtower_snowddl_changes_applied_total",
            "Total number of changes applied via SnowDDL",
        )

        # API metrics
        self.register_counter("snowtower_api_calls_total", "Total number of API calls")
        self.register_histogram(
            "snowtower_api_latency_seconds", "API call latency in seconds"
        )

        # Error metrics
        self.register_counter(
            "snowtower_errors_total", "Total number of errors by type"
        )

        # Authentication metrics
        self.register_counter(
            "snowtower_auth_attempts_total", "Total authentication attempts"
        )
        self.register_counter(
            "snowtower_auth_failures_total", "Total authentication failures"
        )

    def register_counter(self, name: str, help_text: str) -> Counter:
        """Register a counter metric"""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name=name, help_text=help_text)
            return self._counters[name]

    def register_gauge(self, name: str, help_text: str) -> Gauge:
        """Register a gauge metric"""
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name=name, help_text=help_text)
            return self._gauges[name]

    def register_histogram(
        self, name: str, help_text: str, buckets: Optional[List[float]] = None
    ) -> Histogram:
        """Register a histogram metric"""
        with self._lock:
            if name not in self._histograms:
                hist = Histogram(name=name, help_text=help_text)
                if buckets:
                    hist.buckets = buckets
                self._histograms[name] = hist
            return self._histograms[name]

    def increment(
        self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None
    ):
        """Increment a counter"""
        if name in self._counters:
            self._counters[name].increment(amount, labels)
        else:
            logger.warning(f"Counter not found: {name}")

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Set a gauge value"""
        if name in self._gauges:
            self._gauges[name].set(value, labels)
        else:
            logger.warning(f"Gauge not found: {name}")

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram observation"""
        if name in self._histograms:
            self._histograms[name].observe(value, labels)
        else:
            logger.warning(f"Histogram not found: {name}")

    def record_duration(
        self, operation: str, duration_seconds: float, success: bool = True
    ):
        """
        Record operation duration and outcome.

        Args:
            operation: Operation name
            duration_seconds: Duration in seconds
            success: Whether operation succeeded
        """
        labels = {"operation": operation}

        # Record duration
        self.observe("snowtower_operation_duration_seconds", duration_seconds, labels)

        # Increment operation counter
        self.increment("snowtower_operations_total", labels=labels)

        # Record failure if applicable
        if not success:
            self.increment("snowtower_operations_failed_total", labels=labels)

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics
        """
        lines = []

        # Export counters
        for counter in self._counters.values():
            lines.append(f"# HELP {counter.name} {counter.help_text}")
            lines.append(f"# TYPE {counter.name} counter")

            for label_key, value in counter.values.items():
                if label_key:
                    labels_str = "{" + label_key + "}"
                    lines.append(f"{counter.name}{labels_str} {value}")
                else:
                    lines.append(f"{counter.name} {value}")

        # Export gauges
        for gauge in self._gauges.values():
            lines.append(f"# HELP {gauge.name} {gauge.help_text}")
            lines.append(f"# TYPE {gauge.name} gauge")

            for label_key, value in gauge.values.items():
                if label_key:
                    labels_str = "{" + label_key + "}"
                    lines.append(f"{gauge.name}{labels_str} {value}")
                else:
                    lines.append(f"{gauge.name} {value}")

        # Export histograms
        for histogram in self._histograms.values():
            lines.append(f"# HELP {histogram.name} {histogram.help_text}")
            lines.append(f"# TYPE {histogram.name} histogram")

            for label_key, observations in histogram.observations.items():
                if observations:
                    # Count and sum
                    count = len(observations)
                    total = sum(observations)

                    base_labels = label_key if label_key else ""

                    # Buckets
                    bucket_counts = histogram.get_bucket_counts(
                        histogram._key_to_labels(label_key) if label_key else None
                    )
                    for bucket, bucket_count in bucket_counts.items():
                        bucket_label = f'le="{bucket}"'
                        if base_labels:
                            full_labels = f"{{{base_labels},{bucket_label}}}"
                        else:
                            full_labels = f"{{{bucket_label}}}"
                        lines.append(
                            f"{histogram.name}_bucket{full_labels} {bucket_count}"
                        )

                    # Count and sum
                    if base_labels:
                        labels_str = "{" + base_labels + "}"
                        lines.append(f"{histogram.name}_count{labels_str} {count}")
                        lines.append(f"{histogram.name}_sum{labels_str} {total}")
                    else:
                        lines.append(f"{histogram.name}_count {count}")
                        lines.append(f"{histogram.name}_sum {total}")

        return "\n".join(lines) + "\n"

    def export_json(self) -> Dict[str, Any]:
        """
        Export metrics as JSON.

        Returns:
            Dictionary of all metrics
        """
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "counters": {},
            "gauges": {},
            "histograms": {},
        }

        # Export counters
        for counter in self._counters.values():
            result["counters"][counter.name] = {
                "help": counter.help_text,
                "values": dict(counter.values),
            }

        # Export gauges
        for gauge in self._gauges.values():
            result["gauges"][gauge.name] = {
                "help": gauge.help_text,
                "values": dict(gauge.values),
            }

        # Export histograms
        for histogram in self._histograms.values():
            hist_data = {"help": histogram.help_text, "values": {}}

            for label_key, observations in histogram.observations.items():
                if observations:
                    hist_data["values"][label_key or "default"] = {
                        "count": len(observations),
                        "sum": sum(observations),
                        "min": min(observations),
                        "max": max(observations),
                        "mean": statistics.mean(observations),
                        "p50": histogram.get_percentile(
                            50,
                            histogram._key_to_labels(label_key) if label_key else None,
                        ),
                        "p95": histogram.get_percentile(
                            95,
                            histogram._key_to_labels(label_key) if label_key else None,
                        ),
                        "p99": histogram.get_percentile(
                            99,
                            histogram._key_to_labels(label_key) if label_key else None,
                        ),
                    }

            result["histograms"][histogram.name] = hist_data

        return result

    def get_summary(self) -> Dict[str, Any]:
        """
        Get human-readable summary of key metrics.

        Returns:
            Summary dictionary
        """
        summary = {
            "operations": {
                "total": self._counters.get(
                    "snowtower_operations_total", Counter("", "")
                ).get(),
                "failed": self._counters.get(
                    "snowtower_operations_failed_total", Counter("", "")
                ).get(),
            },
            "users": {
                "created": self._counters.get(
                    "snowtower_users_created_total", Counter("", "")
                ).get(),
                "updated": self._counters.get(
                    "snowtower_users_updated_total", Counter("", "")
                ).get(),
                "deleted": self._counters.get(
                    "snowtower_users_deleted_total", Counter("", "")
                ).get(),
                "active": self._gauges.get(
                    "snowtower_active_users", Gauge("", "")
                ).get(),
            },
            "snowddl": {
                "plans": self._counters.get(
                    "snowtower_snowddl_plans_total", Counter("", "")
                ).get(),
                "applies": self._counters.get(
                    "snowtower_snowddl_applies_total", Counter("", "")
                ).get(),
                "changes_applied": self._counters.get(
                    "snowtower_snowddl_changes_applied_total", Counter("", "")
                ).get(),
            },
            "api": {
                "total_calls": self._counters.get(
                    "snowtower_api_calls_total", Counter("", "")
                ).get(),
            },
            "errors": {
                "total": self._counters.get(
                    "snowtower_errors_total", Counter("", "")
                ).get(),
            },
            "authentication": {
                "attempts": self._counters.get(
                    "snowtower_auth_attempts_total", Counter("", "")
                ).get(),
                "failures": self._counters.get(
                    "snowtower_auth_failures_total", Counter("", "")
                ).get(),
            },
        }

        return summary


# Context manager for tracking operations
@contextmanager
def track_operation(
    operation: str,
    metrics: Optional[MetricsCollector] = None,
    labels: Optional[Dict[str, str]] = None,
):
    """
    Context manager for tracking operation duration and outcome.

    Args:
        operation: Operation name
        metrics: MetricsCollector instance (uses global if None)
        labels: Additional labels for the metric

    Example:
        with track_operation("user_creation"):
            create_user(...)
    """
    if metrics is None:
        metrics = get_metrics()

    start_time = time.time()
    success = False
    error = None

    full_labels = {"operation": operation}
    if labels:
        full_labels.update(labels)

    try:
        yield
        success = True
    except Exception as e:
        error = e
        raise
    finally:
        duration = time.time() - start_time
        metrics.record_duration(operation, duration, success)

        if error:
            metrics.increment(
                "snowtower_errors_total",
                labels={"operation": operation, "error_type": type(error).__name__},
            )


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """
    Get global metrics collector instance.

    Returns:
        Global MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics():
    """Reset global metrics collector (useful for testing)"""
    global _metrics_collector
    _metrics_collector = None
