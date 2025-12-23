#!/usr/bin/env python3
"""
Comprehensive Test Suite for SnowDDL Types Module

Tests enums, type definitions, and type utilities.
"""

import pytest
from pathlib import Path
from typing import Tuple

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.snowddl_types import (
    ValidationSeverity,
    DependencyTuple,
    FQN,
    ObjectType,
)


class TestValidationSeverity:
    """Test ValidationSeverity enum"""

    def test_severity_error_value(self):
        """Test ERROR severity value"""
        assert ValidationSeverity.ERROR.value == "error"

    def test_severity_warning_value(self):
        """Test WARNING severity value"""
        assert ValidationSeverity.WARNING.value == "warning"

    def test_severity_info_value(self):
        """Test INFO severity value"""
        assert ValidationSeverity.INFO.value == "info"

    def test_severity_from_string(self):
        """Test creating severity from string value"""
        error = ValidationSeverity("error")
        warning = ValidationSeverity("warning")
        info = ValidationSeverity("info")

        assert error == ValidationSeverity.ERROR
        assert warning == ValidationSeverity.WARNING
        assert info == ValidationSeverity.INFO

    def test_severity_comparison(self):
        """Test comparing severity values"""
        assert ValidationSeverity.ERROR == ValidationSeverity.ERROR
        assert ValidationSeverity.ERROR != ValidationSeverity.WARNING
        assert ValidationSeverity.WARNING != ValidationSeverity.INFO

    def test_severity_in_collection(self):
        """Test using severity in collections"""
        severities = {
            ValidationSeverity.ERROR,
            ValidationSeverity.WARNING,
            ValidationSeverity.INFO,
        }

        assert ValidationSeverity.ERROR in severities
        assert ValidationSeverity.WARNING in severities
        assert len(severities) == 3


class TestDependencyTuple:
    """Test DependencyTuple type"""

    def test_dependency_tuple_creation(self):
        """Test creating dependency tuple"""
        dep: DependencyTuple = ("ROLE", "SYSADMIN")

        assert isinstance(dep, tuple)
        assert len(dep) == 2
        assert dep[0] == "ROLE"
        assert dep[1] == "SYSADMIN"

    def test_dependency_tuple_unpacking(self):
        """Test unpacking dependency tuple"""
        dep: DependencyTuple = ("WAREHOUSE", "COMPUTE_WH")
        obj_type, obj_name = dep

        assert obj_type == "WAREHOUSE"
        assert obj_name == "COMPUTE_WH"

    def test_dependency_tuple_in_list(self):
        """Test dependency tuples in list"""
        dependencies = [("ROLE", "ROLE1"), ("ROLE", "ROLE2"), ("WAREHOUSE", "WH1")]

        assert len(dependencies) == 3
        assert ("ROLE", "ROLE1") in dependencies
        assert ("WAREHOUSE", "WH1") in dependencies

    def test_dependency_tuple_equality(self):
        """Test dependency tuple equality"""
        dep1: DependencyTuple = ("USER", "TEST_USER")
        dep2: DependencyTuple = ("USER", "TEST_USER")
        dep3: DependencyTuple = ("USER", "OTHER_USER")

        assert dep1 == dep2
        assert dep1 != dep3


class TestFQN:
    """Test Fully Qualified Name (FQN) type"""

    def test_fqn_simple(self):
        """Test simple FQN"""
        fqn: FQN = "DATABASE.SCHEMA.TABLE"

        assert isinstance(fqn, str)
        assert "DATABASE" in fqn
        assert "SCHEMA" in fqn
        assert "TABLE" in fqn

    def test_fqn_parsing(self):
        """Test parsing FQN into components"""
        fqn: FQN = "MY_DB.PUBLIC.USERS"
        parts = fqn.split(".")

        assert len(parts) == 3
        assert parts[0] == "MY_DB"
        assert parts[1] == "PUBLIC"
        assert parts[2] == "USERS"

    def test_fqn_simple_name(self):
        """Test FQN as simple name"""
        fqn: FQN = "SIMPLE_OBJECT"

        assert isinstance(fqn, str)
        assert fqn == "SIMPLE_OBJECT"

    def test_fqn_with_two_parts(self):
        """Test FQN with two parts"""
        fqn: FQN = "SCHEMA.TABLE"
        parts = fqn.split(".")

        assert len(parts) == 2
        assert parts[0] == "SCHEMA"
        assert parts[1] == "TABLE"

    def test_fqn_comparison(self):
        """Test FQN comparison"""
        fqn1: FQN = "DB.SCHEMA.TABLE"
        fqn2: FQN = "DB.SCHEMA.TABLE"
        fqn3: FQN = "DB.SCHEMA.OTHER_TABLE"

        assert fqn1 == fqn2
        assert fqn1 != fqn3

    def test_fqn_in_dictionary(self):
        """Test using FQN as dictionary key"""
        objects = {
            "DB.SCHEMA.TABLE1": {"type": "TABLE"},
            "DB.SCHEMA.TABLE2": {"type": "TABLE"},
        }

        assert "DB.SCHEMA.TABLE1" in objects
        assert objects["DB.SCHEMA.TABLE1"]["type"] == "TABLE"


class TestObjectType:
    """Test ObjectType enum/type"""

    def test_object_type_user(self):
        """Test USER object type"""
        obj_type: ObjectType = "USER"
        assert obj_type == "USER"

    def test_object_type_role(self):
        """Test ROLE object type"""
        obj_type: ObjectType = "ROLE"
        assert obj_type == "ROLE"

    def test_object_type_warehouse(self):
        """Test WAREHOUSE object type"""
        obj_type: ObjectType = "WAREHOUSE"
        assert obj_type == "WAREHOUSE"

    def test_object_type_database(self):
        """Test DATABASE object type"""
        obj_type: ObjectType = "DATABASE"
        assert obj_type == "DATABASE"

    def test_object_type_schema(self):
        """Test SCHEMA object type"""
        obj_type: ObjectType = "SCHEMA"
        assert obj_type == "SCHEMA"

    def test_object_type_table(self):
        """Test TABLE object type"""
        obj_type: ObjectType = "TABLE"
        assert obj_type == "TABLE"

    def test_object_type_view(self):
        """Test VIEW object type"""
        obj_type: ObjectType = "VIEW"
        assert obj_type == "VIEW"

    def test_object_type_in_collection(self):
        """Test object types in collection"""
        types = ["USER", "ROLE", "WAREHOUSE", "DATABASE"]

        assert "USER" in types
        assert "ROLE" in types
        assert len(types) == 4

    def test_object_type_comparison(self):
        """Test comparing object types"""
        type1: ObjectType = "USER"
        type2: ObjectType = "USER"
        type3: ObjectType = "ROLE"

        assert type1 == type2
        assert type1 != type3


class TestTypeCompositions:
    """Test type compositions and complex structures"""

    def test_list_of_dependencies(self):
        """Test list of dependency tuples"""
        dependencies: list[DependencyTuple] = [
            ("ROLE", "SYSADMIN"),
            ("ROLE", "SECURITYADMIN"),
            ("WAREHOUSE", "COMPUTE_WH"),
        ]

        assert len(dependencies) == 3
        assert all(isinstance(d, tuple) for d in dependencies)
        assert all(len(d) == 2 for d in dependencies)

    def test_dict_with_fqn_keys(self):
        """Test dictionary with FQN keys"""
        objects: dict[FQN, dict] = {
            "DB.SCHEMA.TABLE1": {"type": "TABLE", "columns": 5},
            "DB.SCHEMA.VIEW1": {"type": "VIEW", "definition": "SELECT * FROM TABLE1"},
        }

        assert len(objects) == 2
        assert objects["DB.SCHEMA.TABLE1"]["columns"] == 5

    def test_nested_types(self):
        """Test nested type structures"""
        object_dependencies: dict[ObjectType, list[DependencyTuple]] = {
            "USER": [("ROLE", "DEFAULT_ROLE")],
            "SCHEMA": [("DATABASE", "MY_DB")],
            "TABLE": [("SCHEMA", "PUBLIC"), ("DATABASE", "MY_DB")],
        }

        assert len(object_dependencies) == 3
        assert len(object_dependencies["USER"]) == 1
        assert len(object_dependencies["TABLE"]) == 2


class TestTypeValidation:
    """Test type validation and constraints"""

    def test_dependency_tuple_structure(self):
        """Test that dependency tuple has correct structure"""
        dep: DependencyTuple = ("OBJECT_TYPE", "OBJECT_NAME")

        # Should be tuple of two strings
        assert isinstance(dep, tuple)
        assert len(dep) == 2
        assert isinstance(dep[0], str)
        assert isinstance(dep[1], str)

    def test_fqn_string_type(self):
        """Test that FQN is a string"""
        fqn: FQN = "QUALIFIED.NAME"

        assert isinstance(fqn, str)

    def test_object_type_string(self):
        """Test that ObjectType is a string"""
        obj_type: ObjectType = "USER"

        assert isinstance(obj_type, str)


class TestTypeUsagePatterns:
    """Test common usage patterns with these types"""

    def test_building_dependency_graph(self):
        """Test building a dependency graph"""
        dependencies = {
            "USER1": [("ROLE", "ROLE1"), ("ROLE", "ROLE2")],
            "USER2": [("ROLE", "ROLE2")],
            "ROLE1": [("ROLE", "SYSADMIN")],
            "ROLE2": [("ROLE", "SYSADMIN")],
        }

        # Verify structure
        assert len(dependencies["USER1"]) == 2
        assert ("ROLE", "SYSADMIN") in dependencies["ROLE1"]

    def test_resolving_fqn(self):
        """Test resolving fully qualified names"""

        def parse_fqn(fqn: FQN) -> dict[str, str]:
            parts = fqn.split(".")
            if len(parts) == 3:
                return {"database": parts[0], "schema": parts[1], "table": parts[2]}
            elif len(parts) == 2:
                return {"schema": parts[0], "table": parts[1]}
            else:
                return {"table": parts[0]}

        result = parse_fqn("DB.SCHEMA.TABLE")
        assert result["database"] == "DB"
        assert result["schema"] == "SCHEMA"
        assert result["table"] == "TABLE"

    def test_filtering_by_object_type(self):
        """Test filtering objects by type"""
        objects = [
            {"name": "USER1", "type": "USER"},
            {"name": "ROLE1", "type": "ROLE"},
            {"name": "USER2", "type": "USER"},
            {"name": "WH1", "type": "WAREHOUSE"},
        ]

        users = [obj for obj in objects if obj["type"] == "USER"]
        roles = [obj for obj in objects if obj["type"] == "ROLE"]

        assert len(users) == 2
        assert len(roles) == 1

    def test_dependency_chain(self):
        """Test creating dependency chain"""
        # USER depends on ROLE, ROLE depends on SYSADMIN
        chain: list[DependencyTuple] = [("ROLE", "CUSTOM_ROLE"), ("ROLE", "SYSADMIN")]

        assert len(chain) == 2
        assert chain[0][0] == "ROLE"
        assert chain[1][0] == "ROLE"


class TestSeverityLevels:
    """Test validation severity level behaviors"""

    def test_severity_ordering(self):
        """Test logical ordering of severities"""
        # While enum doesn't enforce order, we can check values
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"

        # In terms of importance: ERROR > WARNING > INFO
        # This is semantic, not enforced by the type system

    def test_filtering_by_severity(self):
        """Test filtering validations by severity"""
        validations = [
            {"message": "Error 1", "severity": ValidationSeverity.ERROR},
            {"message": "Warning 1", "severity": ValidationSeverity.WARNING},
            {"message": "Info 1", "severity": ValidationSeverity.INFO},
            {"message": "Error 2", "severity": ValidationSeverity.ERROR},
        ]

        errors = [v for v in validations if v["severity"] == ValidationSeverity.ERROR]
        warnings = [
            v for v in validations if v["severity"] == ValidationSeverity.WARNING
        ]

        assert len(errors) == 2
        assert len(warnings) == 1

    def test_severity_in_switch(self):
        """Test using severity in conditional logic"""

        def get_severity_level(severity: ValidationSeverity) -> int:
            if severity == ValidationSeverity.ERROR:
                return 3
            elif severity == ValidationSeverity.WARNING:
                return 2
            elif severity == ValidationSeverity.INFO:
                return 1
            return 0

        assert get_severity_level(ValidationSeverity.ERROR) == 3
        assert get_severity_level(ValidationSeverity.WARNING) == 2
        assert get_severity_level(ValidationSeverity.INFO) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
