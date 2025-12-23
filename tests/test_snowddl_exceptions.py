#!/usr/bin/env python3
"""
Comprehensive Test Suite for SnowDDL Exceptions Module

Tests exception classes, error handling, and exception hierarchies.
"""

import pytest
from pathlib import Path

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.exceptions import (
    SnowDDLError,
    SnowDDLException,
    ValidationError,
    DependencyError,
    CircularDependencyError,
    SerializationError,
    ConfigurationError,
    ObjectNotFoundError,
    SnowflakeConnectionError,
)


class TestSnowDDLException:
    """Test base SnowDDLError"""

    def test_base_exception_creation(self):
        """Test creating base exception"""
        exc = SnowDDLError("Test error message")

        assert str(exc) == "Test error message"
        assert isinstance(exc, Exception)

    def test_base_exception_inheritance(self):
        """Test that SnowDDLError inherits from Exception"""
        exc = SnowDDLError("Test")

        assert isinstance(exc, Exception)
        assert isinstance(exc, SnowDDLError)

    def test_base_exception_with_empty_message(self):
        """Test exception with empty message"""
        exc = SnowDDLError("")

        assert str(exc) == ""

    def test_base_exception_raising(self):
        """Test raising base exception"""
        with pytest.raises(SnowDDLError, match="Test error"):
            raise SnowDDLError("Test error")

    def test_base_exception_catching(self):
        """Test catching base exception"""
        try:
            raise SnowDDLError("Caught error")
        except SnowDDLError as e:
            assert str(e) == "Caught error"

    def test_exception_with_unicode(self):
        """Test exception with unicode characters"""
        exc = SnowDDLError("Error with unicode: ñ, ü, 中文")

        assert "ñ" in str(exc)
        assert "中文" in str(exc)


class TestSerializationError:
    """Test SerializationError exception"""

    def test_serialization_error_creation(self):
        """Test creating serialization error"""
        exc = SerializationError("Invalid configuration")

        assert isinstance(exc, SnowDDLError)

    def test_serialization_error_inheritance(self):
        """Test SerializationError inherits from SnowDDLError"""
        exc = SerializationError("Serialization error")

        assert isinstance(exc, SnowDDLError)
        assert isinstance(exc, SerializationError)
        assert isinstance(exc, Exception)

    def test_serialization_error_raising(self):
        """Test raising serialization error"""
        with pytest.raises(SerializationError):
            raise SerializationError("Bad serialization")

    def test_serialization_error_base_catch(self):
        """Test catching as base SnowDDLError"""
        try:
            raise SerializationError("Serialization error")
        except SnowDDLError as e:
            assert isinstance(e, SerializationError)


class TestValidationError:
    """Test ValidationError exception"""

    def test_validation_error_creation(self):
        """Test creating validation error"""
        exc = ValidationError("Validation failed")

        assert str(exc) == "Validation failed"
        assert isinstance(exc, SnowDDLException)

    def test_validation_error_inheritance(self):
        """Test ValidationError inherits properly"""
        exc = ValidationError("Invalid data")

        assert isinstance(exc, SnowDDLException)
        assert isinstance(exc, ValidationError)

    def test_validation_error_with_details(self):
        """Test validation error with details"""
        exc = ValidationError("Field 'email' is required")

        assert "email" in str(exc)
        assert "required" in str(exc)

    def test_validation_error_raising(self):
        """Test raising validation error"""
        with pytest.raises(ValidationError, match="Invalid"):
            raise ValidationError("Invalid input")


class TestDependencyError:
    """Test DependencyError exception"""

    def test_dependency_error_creation(self):
        """Test creating dependency error"""
        exc = DependencyError("Circular dependency detected")

        assert "Circular dependency" in str(exc)
        assert isinstance(exc, SnowDDLException)

    def test_dependency_error_inheritance(self):
        """Test DependencyError inherits properly"""
        exc = DependencyError("Dependency issue")

        assert isinstance(exc, SnowDDLException)
        assert isinstance(exc, DependencyError)

    def test_dependency_error_with_objects(self):
        """Test dependency error mentioning objects"""
        exc = DependencyError("USER1 depends on ROLE1 which does not exist")

        assert "USER1" in str(exc)
        assert "ROLE1" in str(exc)

    def test_dependency_error_raising(self):
        """Test raising dependency error"""
        with pytest.raises(DependencyError, match="Missing dependency"):
            raise DependencyError("Missing dependency")


class TestSnowflakeConnectionError:
    """Test SnowflakeConnectionError exception"""

    def test_connection_error_creation(self):
        """Test creating connection error"""
        exc = SnowflakeConnectionError("Failed to connect to Snowflake")

        assert "Failed to connect" in str(exc)
        assert isinstance(exc, SnowDDLException)

    def test_connection_error_inheritance(self):
        """Test SnowflakeConnectionError inherits properly"""
        exc = SnowflakeConnectionError("Connection failed")

        assert isinstance(exc, SnowDDLException)
        assert isinstance(exc, SnowflakeConnectionError)

    def test_connection_error_with_details(self):
        """Test connection error with details"""
        exc = SnowflakeConnectionError(
            "Connection timeout after 30 seconds to account MY_ACCOUNT"
        )

        assert "timeout" in str(exc)
        assert "MY_ACCOUNT" in str(exc)

    def test_connection_error_raising(self):
        """Test raising connection error"""
        with pytest.raises(SnowflakeConnectionError, match="Authentication failed"):
            raise SnowflakeConnectionError("Authentication failed")


class TestObjectNotFoundError:
    """Test ObjectNotFoundError exception"""

    def test_object_not_found_creation(self):
        """Test creating object not found error"""
        exc = ObjectNotFoundError("USER 'TEST_USER' not found")

        assert "TEST_USER" in str(exc)
        assert "not found" in str(exc)
        assert isinstance(exc, SnowDDLException)

    def test_object_not_found_inheritance(self):
        """Test ObjectNotFoundError inherits properly"""
        exc = ObjectNotFoundError("Object missing")

        assert isinstance(exc, SnowDDLException)
        assert isinstance(exc, ObjectNotFoundError)

    def test_object_not_found_with_type(self):
        """Test object not found with type and name"""
        exc = ObjectNotFoundError("ROLE 'CUSTOM_ROLE' does not exist")

        assert "ROLE" in str(exc)
        assert "CUSTOM_ROLE" in str(exc)

    def test_object_not_found_raising(self):
        """Test raising object not found error"""
        with pytest.raises(ObjectNotFoundError, match="TABLE1"):
            raise ObjectNotFoundError("TABLE 'TABLE1' not found")


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance"""

    def test_catch_all_snowddl_exceptions(self):
        """Test catching all SnowDDL exceptions with base class"""
        exceptions = [
            ConfigurationError("Config error"),
            ValidationError("Validation error"),
            DependencyError("Dependency error"),
            SnowflakeConnectionError("Connection error"),
            ObjectNotFoundError("Object not found"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except SnowDDLException as e:
                # Should catch all of them
                assert isinstance(e, SnowDDLException)

    def test_specific_exception_catch_order(self):
        """Test exception catch order (specific before general)"""
        caught_type = None

        try:
            raise ConfigurationError("Config error")
        except ConfigurationError:
            caught_type = "ConfigurationError"
        except SnowDDLException:
            caught_type = "SnowDDLException"

        assert caught_type == "ConfigurationError"

    def test_general_exception_catch(self):
        """Test catching with general Exception"""
        try:
            raise ValidationError("Validation error")
        except Exception as e:
            assert isinstance(e, Exception)
            assert isinstance(e, SnowDDLException)
            assert isinstance(e, ValidationError)


class TestExceptionChaining:
    """Test exception chaining and context"""

    def test_exception_chaining_from(self):
        """Test exception chaining with from"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ConfigurationError("Config error") from e
        except ConfigurationError as exc:
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)

    def test_exception_context(self):
        """Test exception context"""
        try:
            try:
                raise KeyError("Missing key")
            except KeyError:
                raise ObjectNotFoundError("Object not found")
        except ObjectNotFoundError as exc:
            assert exc.__context__ is not None
            assert isinstance(exc.__context__, KeyError)


class TestExceptionMessages:
    """Test exception message formatting"""

    def test_multiline_message(self):
        """Test exception with multiline message"""
        message = """Configuration error:
        - Missing required field 'name'
        - Invalid value for 'type'"""

        exc = ConfigurationError(message)

        assert "Missing required field" in str(exc)
        assert "Invalid value" in str(exc)

    def test_formatted_message(self):
        """Test exception with formatted message"""
        user = "TEST_USER"
        role = "TEST_ROLE"
        message = f"User '{user}' cannot be granted role '{role}'"

        exc = DependencyError(message)

        assert user in str(exc)
        assert role in str(exc)

    def test_message_with_special_characters(self):
        """Test exception message with special characters"""
        exc = ValidationError("Invalid chars: !@#$%^&*()")

        assert "!@#$%^&*()" in str(exc)


class TestExceptionUseCases:
    """Test real-world exception usage patterns"""

    def test_configuration_file_not_found(self):
        """Test configuration file not found scenario"""
        config_file = "missing_config.yaml"

        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError(f"Configuration file not found: {config_file}")

        assert "missing_config.yaml" in str(exc_info.value)

    def test_invalid_user_configuration(self):
        """Test invalid user configuration"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("User must have either password or RSA key")

        assert "password" in str(exc_info.value).lower()
        assert "rsa" in str(exc_info.value).lower()

    def test_circular_dependency(self):
        """Test circular dependency detection"""
        with pytest.raises(DependencyError) as exc_info:
            raise DependencyError("Circular dependency: ROLE1 -> ROLE2 -> ROLE1")

        assert "Circular" in str(exc_info.value)
        assert "ROLE1" in str(exc_info.value)

    def test_snowflake_authentication_failure(self):
        """Test Snowflake authentication failure"""
        with pytest.raises(SnowflakeConnectionError) as exc_info:
            raise SnowflakeConnectionError(
                "Authentication failed: Invalid username or password"
            )

        assert "Authentication" in str(exc_info.value)

    def test_object_not_found_in_snowflake(self):
        """Test object not found in Snowflake"""
        with pytest.raises(ObjectNotFoundError) as exc_info:
            raise ObjectNotFoundError("WAREHOUSE 'COMPUTE_WH' does not exist")

        assert "WAREHOUSE" in str(exc_info.value)
        assert "COMPUTE_WH" in str(exc_info.value)


class TestExceptionAttributes:
    """Test exception attributes and properties"""

    def test_exception_args(self):
        """Test exception args attribute"""
        exc = ConfigurationError("Error message")

        assert exc.args == ("Error message",)
        assert len(exc.args) == 1

    def test_exception_str_repr(self):
        """Test exception string representation"""
        exc = ValidationError("Test error")

        assert str(exc) == "Test error"
        # repr might include class name
        assert "Test error" in repr(exc)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
