"""
Custom exceptions for SnowDDL framework.

This module defines all custom exceptions used throughout the SnowDDL
object-oriented framework.
"""

from typing import Optional


class SnowDDLError(Exception):
    """Base exception for all SnowDDL errors"""

    pass


class ValidationError(SnowDDLError):
    """Raised when object validation fails"""

    def __init__(
        self,
        message: str,
        object_type: Optional[str] = None,
        object_name: Optional[str] = None,
        field: Optional[str] = None,
    ):
        self.message = message
        self.object_type = object_type
        self.object_name = object_name
        self.field = field
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context"""
        if self.object_type and self.object_name:
            prefix = f"{self.object_type} {self.object_name}"
            if self.field:
                prefix += f".{self.field}"
            return f"{prefix}: {self.message}"
        return self.message


class DependencyError(SnowDDLError):
    """Raised when dependency resolution fails"""

    def __init__(
        self,
        message: str,
        object_type: Optional[str] = None,
        object_name: Optional[str] = None,
        dependency_type: Optional[str] = None,
        dependency_name: Optional[str] = None,
    ):
        self.message = message
        self.object_type = object_type
        self.object_name = object_name
        self.dependency_type = dependency_type
        self.dependency_name = dependency_name
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with dependency context"""
        if self.object_type and self.object_name:
            msg = f"{self.object_type} {self.object_name}"
            if self.dependency_type and self.dependency_name:
                msg += f" depends on {self.dependency_type} {self.dependency_name}"
            msg += f": {self.message}"
            return msg
        return self.message


class CircularDependencyError(DependencyError):
    """Raised when circular dependencies are detected"""

    def __init__(self, cycle: list[tuple[str, str]]):
        self.cycle = cycle
        cycle_str = " -> ".join([f"{obj_type}:{fqn}" for obj_type, fqn in cycle])
        super().__init__(f"Circular dependency detected: {cycle_str}")


class SerializationError(SnowDDLError):
    """Raised when YAML serialization/deserialization fails"""

    def __init__(
        self,
        message: str,
        object_type: Optional[str] = None,
        object_name: Optional[str] = None,
        file_path: Optional[str] = None,
    ):
        self.message = message
        self.object_type = object_type
        self.object_name = object_name
        self.file_path = file_path
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with file context"""
        if self.file_path:
            prefix = f"File {self.file_path}"
            if self.object_type and self.object_name:
                prefix += f" ({self.object_type} {self.object_name})"
            return f"{prefix}: {self.message}"
        if self.object_type and self.object_name:
            return f"{self.object_type} {self.object_name}: {self.message}"
        return self.message


class EncryptionError(SnowDDLError):
    """Raised when password encryption/decryption fails"""

    def __init__(self, message: str, user_name: Optional[str] = None):
        self.message = message
        self.user_name = user_name
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with user context"""
        if self.user_name:
            return f"User {self.user_name}: {self.message}"
        return self.message


class ConfigurationError(SnowDDLError):
    """Raised when configuration is invalid or missing"""

    pass


class ObjectNotFoundError(SnowDDLError):
    """Raised when a referenced object cannot be found"""

    def __init__(self, message_or_type: str, fqn: str = None):
        # Support both (message) and (object_type, fqn) signatures
        if fqn is not None:
            self.object_type = message_or_type
            self.fqn = fqn
            super().__init__(f"{message_or_type} '{fqn}' not found")
        else:
            self.object_type = None
            self.fqn = None
            super().__init__(message_or_type)


class SnowflakeConnectionError(SnowDDLError):
    """Raised when connection to Snowflake fails"""

    def __init__(self, message: str):
        super().__init__(message)


# Alias for backward compatibility
SnowDDLException = SnowDDLError
