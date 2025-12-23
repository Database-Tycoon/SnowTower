"""
Centralized Structured Logging Module for SnowTower

Provides enterprise-grade structured logging with:
- JSON formatting for machine-readable logs
- Correlation IDs for operation tracking
- Context enrichment (user, operation, resource)
- Multiple output destinations (file, console, external services)
- Log level filtering and rotation
- Security: automatic masking of sensitive data

Usage:
    from snowtower_core.logging import get_logger, set_correlation_id

    logger = get_logger(__name__)

    with set_correlation_id():  # Auto-generates correlation ID
        logger.info("Starting operation", extra={
            "operation": "user_creation",
            "username": "JOHN_DOE",
            "user_type": "PERSON"
        })
"""

import logging
import logging.handlers
import json
import sys
import uuid
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager
from threading import local
import os

# Thread-local storage for correlation IDs
_thread_local = local()

# Sensitive patterns to mask in logs
SENSITIVE_PATTERNS = [
    (
        re.compile(r'"password"\s*:\s*"[^"]*"', re.IGNORECASE),
        '"password": "***MASKED***"',
    ),
    (
        re.compile(r'"encrypted_password"\s*:\s*"[^"]*"', re.IGNORECASE),
        '"encrypted_password": "***MASKED***"',
    ),
    (
        re.compile(r'"api_key"\s*:\s*"[^"]*"', re.IGNORECASE),
        '"api_key": "***MASKED***"',
    ),
    (re.compile(r'"secret"\s*:\s*"[^"]*"', re.IGNORECASE), '"secret": "***MASKED***"'),
    (re.compile(r'"token"\s*:\s*"[^"]*"', re.IGNORECASE), '"token": "***MASKED***"'),
    (
        re.compile(r"SNOWFLAKE_PASSWORD=\S+", re.IGNORECASE),
        "SNOWFLAKE_PASSWORD=***MASKED***",
    ),
    (re.compile(r"rsa_key[^}]*}", re.IGNORECASE), 'rsa_key": "***MASKED***"'),
]


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in JSON format with:
    - Standard fields: timestamp, level, logger, message
    - Context fields: correlation_id, user, operation, resource
    - Custom fields: anything passed via extra parameter
    """

    def __init__(self, mask_sensitive: bool = True):
        """
        Initialize the formatter.

        Args:
            mask_sensitive: Whether to mask sensitive data in logs
        """
        super().__init__()
        self.mask_sensitive = mask_sensitive

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Build base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add custom fields from extra parameter
        custom_fields = [
            "operation",
            "user",
            "resource",
            "status",
            "duration_ms",
            "username",
            "user_type",
            "action",
            "old_value",
            "new_value",
            "error_code",
            "resource_type",
            "resource_id",
        ]

        for field in custom_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        # Convert to JSON
        json_str = json.dumps(log_entry, default=str)

        # Mask sensitive data
        if self.mask_sensitive:
            json_str = self._mask_sensitive_data(json_str)

        return json_str

    def _mask_sensitive_data(self, text: str) -> str:
        """
        Mask sensitive data patterns in log output.

        Args:
            text: Text to mask

        Returns:
            Text with sensitive data masked
        """
        for pattern, replacement in SENSITIVE_PATTERNS:
            text = pattern.sub(replacement, text)
        return text


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for console output.

    Formats logs in a readable format with colors (if supported).
    Also masks sensitive data.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def __init__(self, mask_sensitive: bool = True, use_colors: bool = True):
        """
        Initialize the formatter.

        Args:
            mask_sensitive: Whether to mask sensitive data
            use_colors: Whether to use ANSI colors (disable for non-TTY)
        """
        super().__init__()
        self.mask_sensitive = mask_sensitive
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human reading"""
        # Color coding for level
        if self.use_colors:
            level_color = self.COLORS.get(record.levelname, "")
            reset = self.COLORS["RESET"]
            level_str = f"{level_color}{record.levelname:8s}{reset}"
        else:
            level_str = f"{record.levelname:8s}"

        # Build message
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        correlation_id = (
            get_correlation_id()[:8] if get_correlation_id() else "--------"
        )

        message = f"[{timestamp}] [{correlation_id}] {level_str} {record.name}: {record.getMessage()}"

        # Add custom fields if present
        extras = []
        if hasattr(record, "operation"):
            extras.append(f"operation={record.operation}")
        if hasattr(record, "user"):
            extras.append(f"user={record.user}")
        if hasattr(record, "resource"):
            extras.append(f"resource={record.resource}")

        if extras:
            message += f" [{', '.join(extras)}]"

        # Add exception if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        # Mask sensitive data
        if self.mask_sensitive:
            for pattern, replacement in SENSITIVE_PATTERNS:
                message = pattern.sub(replacement, message)

        return message


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from thread-local storage.

    Returns:
        Current correlation ID or None
    """
    return getattr(_thread_local, "correlation_id", None)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set the correlation ID for the current thread.

    Args:
        correlation_id: Correlation ID to set. If None, generates a new UUID.

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    _thread_local.correlation_id = correlation_id
    return correlation_id


def clear_correlation_id():
    """Clear the correlation ID for the current thread."""
    if hasattr(_thread_local, "correlation_id"):
        delattr(_thread_local, "correlation_id")


@contextmanager
def correlation_context(correlation_id: Optional[str] = None):
    """
    Context manager for correlation ID.

    Automatically sets and clears correlation ID for a block of code.

    Args:
        correlation_id: Correlation ID to use. If None, generates a new one.

    Example:
        with correlation_context():
            logger.info("This log will have a correlation ID")
            do_some_work()
            logger.info("This log will have the same correlation ID")
    """
    old_id = get_correlation_id()
    new_id = set_correlation_id(correlation_id)
    try:
        yield new_id
    finally:
        if old_id:
            set_correlation_id(old_id)
        else:
            clear_correlation_id()


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    log_to_console: bool = True,
    json_format: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    mask_sensitive: bool = True,
) -> logging.Logger:
    """
    Setup centralized logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, uses default location.
        log_to_console: Whether to log to console
        json_format: Whether to use JSON format for file logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        mask_sensitive: Whether to mask sensitive data in logs

    Returns:
        Configured root logger

    Example:
        setup_logging(
            log_level="DEBUG",
            log_file=Path("/var/log/snowtower/app.log"),
            json_format=True
        )
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Setup file logging if requested
    if log_file or not log_to_console:
        if log_file is None:
            # Default log location
            log_file = Path.cwd() / "logs" / "snowtower.log"

        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )

        # Use JSON formatter for files
        if json_format:
            file_handler.setFormatter(
                StructuredFormatter(mask_sensitive=mask_sensitive)
            )
        else:
            file_handler.setFormatter(
                HumanReadableFormatter(mask_sensitive=mask_sensitive, use_colors=False)
            )

        root_logger.addHandler(file_handler)

    # Setup console logging if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            HumanReadableFormatter(mask_sensitive=mask_sensitive, use_colors=True)
        )
        root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)
        **kwargs: Additional configuration passed to setup_logging

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    # Setup logging if not already configured
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        # Read configuration from environment
        log_level = os.getenv("SNOWTOWER_LOG_LEVEL", "INFO")
        log_file = os.getenv("SNOWTOWER_LOG_FILE")
        log_file_path = Path(log_file) if log_file else None

        setup_logging(log_level=log_level, log_file=log_file_path, **kwargs)

    return logging.getLogger(name)


# Convenience functions for common logging patterns
def log_operation_start(logger: logging.Logger, operation: str, **context):
    """
    Log the start of an operation.

    Args:
        logger: Logger instance
        operation: Operation name
        **context: Additional context fields
    """
    logger.info(
        f"Starting operation: {operation}",
        extra={"operation": operation, "status": "started", **context},
    )


def log_operation_success(
    logger: logging.Logger,
    operation: str,
    duration_ms: Optional[float] = None,
    **context,
):
    """
    Log successful completion of an operation.

    Args:
        logger: Logger instance
        operation: Operation name
        duration_ms: Operation duration in milliseconds
        **context: Additional context fields
    """
    extra = {"operation": operation, "status": "success", **context}
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)

    logger.info(f"Operation completed: {operation}", extra=extra)


def log_operation_failure(
    logger: logging.Logger, operation: str, error: Exception, **context
):
    """
    Log operation failure.

    Args:
        logger: Logger instance
        operation: Operation name
        error: Exception that caused the failure
        **context: Additional context fields
    """
    logger.error(
        f"Operation failed: {operation}",
        extra={
            "operation": operation,
            "status": "failed",
            "error": str(error),
            "error_type": type(error).__name__,
            **context,
        },
        exc_info=True,
    )


# Pre-configured logger for the monitoring system itself
monitoring_logger = get_logger("snowtower.monitoring")
