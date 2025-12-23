#!/usr/bin/env python3
"""
Comprehensive Test Suite for SnowDDL Validation Module

Tests validation framework, rules, severity levels, and validation errors.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.validation import ValidationError, ValidationContext, ValidationRule
from snowddl_core.snowddl_types import ValidationSeverity


class TestValidationError:
    """Test ValidationError class"""

    def test_validation_error_basic(self):
        """Test basic validation error creation"""
        error = ValidationError("Test error message")

        assert error.message == "Test error message"
        assert error.severity == ValidationSeverity.ERROR
        assert error.object_type is None
        assert error.object_name is None
        assert error.field is None

    def test_validation_error_with_severity(self):
        """Test validation error with custom severity"""
        warning = ValidationError("Test warning", severity=ValidationSeverity.WARNING)

        assert warning.severity == ValidationSeverity.WARNING

        info = ValidationError("Test info", severity=ValidationSeverity.INFO)

        assert info.severity == ValidationSeverity.INFO

    def test_validation_error_with_object_info(self):
        """Test validation error with object information"""
        error = ValidationError(
            "Invalid configuration",
            severity=ValidationSeverity.ERROR,
            object_type="USER",
            object_name="TEST_USER",
        )

        assert error.object_type == "USER"
        assert error.object_name == "TEST_USER"

    def test_validation_error_with_field(self):
        """Test validation error with field information"""
        error = ValidationError(
            "Invalid email format",
            object_type="USER",
            object_name="TEST_USER",
            field="email",
        )

        assert error.field == "email"

    def test_validation_error_str_basic(self):
        """Test string representation of basic error"""
        error = ValidationError("Test error")
        error_str = str(error)

        assert "[ERROR]" in error_str
        assert "Test error" in error_str

    def test_validation_error_str_with_object(self):
        """Test string representation with object info"""
        error = ValidationError(
            "Invalid configuration", object_type="USER", object_name="TEST_USER"
        )
        error_str = str(error)

        assert "[ERROR]" in error_str
        assert "USER" in error_str
        assert "TEST_USER" in error_str
        assert "Invalid configuration" in error_str

    def test_validation_error_str_with_field(self):
        """Test string representation with field"""
        error = ValidationError(
            "Invalid format", object_type="USER", object_name="TEST_USER", field="email"
        )
        error_str = str(error)

        assert "USER" in error_str
        assert "TEST_USER" in error_str
        assert "email" in error_str

    def test_validation_error_warning_str(self):
        """Test string representation of warning"""
        warning = ValidationError(
            "Consider using MFA", severity=ValidationSeverity.WARNING
        )
        warning_str = str(warning)

        assert "[WARNING]" in warning_str.upper()

    def test_validation_error_info_str(self):
        """Test string representation of info"""
        info = ValidationError(
            "User created successfully", severity=ValidationSeverity.INFO
        )
        info_str = str(info)

        assert "[INFO]" in info_str.upper()


class TestValidationSeverity:
    """Test ValidationSeverity enum"""

    def test_severity_error(self):
        """Test ERROR severity"""
        assert ValidationSeverity.ERROR.value == "error"

    def test_severity_warning(self):
        """Test WARNING severity"""
        assert ValidationSeverity.WARNING.value == "warning"

    def test_severity_info(self):
        """Test INFO severity"""
        assert ValidationSeverity.INFO.value == "info"

    def test_severity_comparison(self):
        """Test comparing severities"""
        error1 = ValidationError("Error 1", severity=ValidationSeverity.ERROR)
        error2 = ValidationError("Error 2", severity=ValidationSeverity.ERROR)
        warning = ValidationError("Warning", severity=ValidationSeverity.WARNING)

        assert error1.severity == error2.severity
        assert error1.severity != warning.severity


class TestValidationContext:
    """Test ValidationContext class"""

    def test_validation_context_init(self):
        """Test ValidationContext initialization"""
        mock_repo = Mock()
        context = ValidationContext(mock_repo)

        assert context.repository == mock_repo

    def test_object_exists_true(self):
        """Test object_exists returns True for existing object"""
        mock_repo = Mock()
        mock_repo.get_object.return_value = Mock()

        context = ValidationContext(mock_repo)
        exists = context.object_exists("USER", "TEST_USER")

        assert exists is True
        mock_repo.get_object.assert_called_once_with("USER", "TEST_USER")

    def test_object_exists_false(self):
        """Test object_exists returns False for non-existent object"""
        mock_repo = Mock()
        mock_repo.get_object.side_effect = KeyError("Object not found")

        context = ValidationContext(mock_repo)
        exists = context.object_exists("USER", "NONEXISTENT")

        assert exists is False

    def test_object_exists_multiple_checks(self):
        """Test multiple object existence checks"""
        mock_repo = Mock()

        def mock_get_object(obj_type, fqn):
            if fqn == "EXISTING":
                return Mock()
            raise KeyError("Not found")

        mock_repo.get_object.side_effect = mock_get_object

        context = ValidationContext(mock_repo)

        assert context.object_exists("USER", "EXISTING") is True
        assert context.object_exists("USER", "MISSING") is False


class TestValidationRule:
    """Test ValidationRule abstract class"""

    def test_validation_rule_is_abstract(self):
        """Test that ValidationRule cannot be instantiated directly"""
        with pytest.raises(TypeError):
            ValidationRule()

    def test_validation_rule_subclass_implementation(self):
        """Test that subclass must implement validate method"""

        class TestRule(ValidationRule):
            def validate(self, obj, context=None):
                return []

        rule = TestRule()
        errors = rule.validate(Mock())

        assert isinstance(errors, list)
        assert len(errors) == 0


class TestValidationScenarios:
    """Test various validation scenarios"""

    def test_validate_multiple_errors(self):
        """Test collecting multiple validation errors"""
        errors = [
            ValidationError("Error 1", object_type="USER", object_name="USER1"),
            ValidationError("Error 2", object_type="USER", object_name="USER1"),
            ValidationError("Error 3", object_type="USER", object_name="USER2"),
        ]

        assert len(errors) == 3
        assert all(isinstance(e, ValidationError) for e in errors)

    def test_validate_mixed_severities(self):
        """Test validation with mixed severity levels"""
        errors = [
            ValidationError("Critical error", severity=ValidationSeverity.ERROR),
            ValidationError("Warning message", severity=ValidationSeverity.WARNING),
            ValidationError("Info message", severity=ValidationSeverity.INFO),
        ]

        error_count = sum(1 for e in errors if e.severity == ValidationSeverity.ERROR)
        warning_count = sum(
            1 for e in errors if e.severity == ValidationSeverity.WARNING
        )
        info_count = sum(1 for e in errors if e.severity == ValidationSeverity.INFO)

        assert error_count == 1
        assert warning_count == 1
        assert info_count == 1

    def test_validation_error_aggregation(self):
        """Test aggregating validation errors by object"""
        errors = [
            ValidationError("Error 1", object_name="USER1"),
            ValidationError("Error 2", object_name="USER1"),
            ValidationError("Error 3", object_name="USER2"),
        ]

        errors_by_object = {}
        for error in errors:
            obj_name = error.object_name or "unknown"
            if obj_name not in errors_by_object:
                errors_by_object[obj_name] = []
            errors_by_object[obj_name].append(error)

        assert len(errors_by_object) == 2
        assert len(errors_by_object["USER1"]) == 2
        assert len(errors_by_object["USER2"]) == 1


class TestValidationErrorFormatting:
    """Test validation error formatting for different contexts"""

    def test_format_for_cli_output(self):
        """Test formatting errors for CLI output"""
        error = ValidationError(
            "Invalid email format",
            severity=ValidationSeverity.ERROR,
            object_type="USER",
            object_name="TEST_USER",
            field="email",
        )

        output = str(error)

        # Should contain all relevant information
        assert "ERROR" in output.upper()
        assert "USER" in output
        assert "TEST_USER" in output
        assert "email" in output
        assert "Invalid email format" in output

    def test_format_error_list(self):
        """Test formatting a list of errors"""
        errors = [
            ValidationError("Error 1", object_name="USER1"),
            ValidationError("Error 2", object_name="USER2"),
            ValidationError("Error 3", object_name="USER3"),
        ]

        formatted = "\n".join(str(e) for e in errors)

        assert "Error 1" in formatted
        assert "Error 2" in formatted
        assert "Error 3" in formatted

    def test_format_with_unicode(self):
        """Test formatting errors with unicode characters"""
        error = ValidationError(
            "Nom d'utilisateur invalide: Müller",
            object_type="UTILISATEUR",
            object_name="TEST_USER",
        )

        output = str(error)

        assert "Müller" in output
        assert "UTILISATEUR" in output


class TestValidationHelpers:
    """Test validation helper functionality"""

    def test_filter_errors_by_severity(self):
        """Test filtering errors by severity"""
        all_errors = [
            ValidationError("Error 1", severity=ValidationSeverity.ERROR),
            ValidationError("Warning 1", severity=ValidationSeverity.WARNING),
            ValidationError("Info 1", severity=ValidationSeverity.INFO),
            ValidationError("Error 2", severity=ValidationSeverity.ERROR),
        ]

        errors_only = [e for e in all_errors if e.severity == ValidationSeverity.ERROR]

        assert len(errors_only) == 2
        assert all(e.severity == ValidationSeverity.ERROR for e in errors_only)

    def test_has_errors_check(self):
        """Test checking if validation has errors"""
        errors = [
            ValidationError("Warning", severity=ValidationSeverity.WARNING),
            ValidationError("Info", severity=ValidationSeverity.INFO),
        ]

        has_errors = any(e.severity == ValidationSeverity.ERROR for e in errors)

        assert has_errors is False

        errors.append(ValidationError("Error", severity=ValidationSeverity.ERROR))
        has_errors = any(e.severity == ValidationSeverity.ERROR for e in errors)

        assert has_errors is True

    def test_group_errors_by_type(self):
        """Test grouping errors by object type"""
        errors = [
            ValidationError("Error 1", object_type="USER"),
            ValidationError("Error 2", object_type="ROLE"),
            ValidationError("Error 3", object_type="USER"),
            ValidationError("Error 4", object_type="WAREHOUSE"),
        ]

        errors_by_type = {}
        for error in errors:
            obj_type = error.object_type or "unknown"
            if obj_type not in errors_by_type:
                errors_by_type[obj_type] = []
            errors_by_type[obj_type].append(error)

        assert len(errors_by_type) == 3
        assert len(errors_by_type["USER"]) == 2
        assert len(errors_by_type["ROLE"]) == 1
        assert len(errors_by_type["WAREHOUSE"]) == 1


class TestValidationContextAdvanced:
    """Test advanced ValidationContext features"""

    def test_context_with_multiple_object_types(self):
        """Test context checking multiple object types"""
        mock_repo = Mock()

        def mock_get_object(obj_type, fqn):
            objects = {
                ("USER", "USER1"): Mock(),
                ("ROLE", "ROLE1"): Mock(),
                ("WAREHOUSE", "WH1"): Mock(),
            }
            key = (obj_type, fqn)
            if key in objects:
                return objects[key]
            raise KeyError("Not found")

        mock_repo.get_object.side_effect = mock_get_object

        context = ValidationContext(mock_repo)

        assert context.object_exists("USER", "USER1") is True
        assert context.object_exists("ROLE", "ROLE1") is True
        assert context.object_exists("WAREHOUSE", "WH1") is True
        assert context.object_exists("USER", "USER2") is False

    def test_context_validation_caching(self):
        """Test that context can cache validation results"""
        mock_repo = Mock()
        mock_repo.get_object.return_value = Mock()

        context = ValidationContext(mock_repo)

        # First call
        exists1 = context.object_exists("USER", "TEST")
        # Second call
        exists2 = context.object_exists("USER", "TEST")

        assert exists1 is True
        assert exists2 is True
        # Should call repository twice (no caching in basic implementation)
        assert mock_repo.get_object.call_count == 2


class TestValidationEdgeCases:
    """Test edge cases in validation"""

    def test_validation_error_with_none_values(self):
        """Test validation error with None values"""
        error = ValidationError("Error", object_type=None, object_name=None, field=None)

        output = str(error)
        assert "Error" in output

    def test_validation_error_with_empty_message(self):
        """Test validation error with empty message"""
        error = ValidationError("")

        assert error.message == ""
        output = str(error)
        assert "[ERROR]" in output.upper()

    def test_validation_error_with_very_long_message(self):
        """Test validation error with very long message"""
        long_message = "Error: " + "x" * 1000
        error = ValidationError(long_message)

        assert len(error.message) > 1000
        output = str(error)
        assert len(output) > 1000

    def test_validation_context_with_none_repository(self):
        """Test ValidationContext with None repository"""
        context = ValidationContext(None)

        assert context.repository is None

        # Should handle gracefully
        try:
            context.object_exists("USER", "TEST")
        except AttributeError:
            # Expected when repository is None
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
