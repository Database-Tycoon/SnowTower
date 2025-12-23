#!/usr/bin/env python3
"""
Comprehensive Test Suite for SnowDDL Base Module

Tests abstract base classes and core SnowDDL object functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock
from abc import ABC

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.base import SnowDDLObject
from snowddl_core.snowddl_types import DependencyTuple, FQN, ObjectType


class TestSnowDDLObjectAbstract:
    """Test SnowDDLObject abstract class"""

    def test_cannot_instantiate_directly(self):
        """Test that SnowDDLObject cannot be instantiated directly"""
        with pytest.raises(TypeError):
            SnowDDLObject("test_name")

    def test_must_implement_abstract_methods(self):
        """Test that subclass must implement all abstract methods"""

        # Missing validate method
        class IncompleteObject1(SnowDDLObject):
            def to_yaml(self):
                return {}

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name)

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path("test.yaml")

        with pytest.raises(TypeError):
            IncompleteObject1("test")

    def test_concrete_implementation(self):
        """Test a complete concrete implementation"""

        class ConcreteObject(SnowDDLObject):
            def to_yaml(self):
                return {"name": self.name, "comment": self.comment}

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name, comment=data.get("comment"))

            def validate(self):
                return []

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path(config_dir) / f"{self.name}.yaml"

        obj = ConcreteObject("TEST_OBJECT", comment="Test comment")

        assert obj.name == "TEST_OBJECT"
        assert obj.comment == "Test comment"
        assert isinstance(obj, SnowDDLObject)


class TestSnowDDLObjectInitialization:
    """Test SnowDDLObject initialization"""

    def setup_method(self):
        """Set up test fixtures"""

        class TestObject(SnowDDLObject):
            object_type = "test_object"

            def to_yaml(self):
                return {"name": self.name}

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name, comment=data.get("comment"))

            def validate(self):
                return []

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path(config_dir) / f"{self.name}.yaml"

        self.TestObject = TestObject

    def test_init_with_name_only(self):
        """Test initialization with just name"""
        obj = self.TestObject("TEST_NAME")

        assert obj.name == "TEST_NAME"
        assert obj.comment is None

    def test_init_with_name_and_comment(self):
        """Test initialization with name and comment"""
        obj = self.TestObject("TEST_NAME", comment="Test comment")

        assert obj.name == "TEST_NAME"
        assert obj.comment == "Test comment"

    def test_object_type_class_variable(self):
        """Test that object_type is accessible as class variable"""
        assert self.TestObject.object_type == "test_object"

        obj = self.TestObject("TEST")
        assert obj.object_type == "test_object"


class TestToYaml:
    """Test to_yaml serialization"""

    def setup_method(self):
        """Set up test fixtures"""

        class TestObject(SnowDDLObject):
            def __init__(self, name, comment=None, custom_field=None):
                super().__init__(name, comment)
                self.custom_field = custom_field

            def to_yaml(self):
                yaml_dict = {"name": self.name}
                if self.comment:
                    yaml_dict["comment"] = self.comment
                if self.custom_field:
                    yaml_dict["custom_field"] = self.custom_field
                return yaml_dict

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name, comment=data.get("comment"))

            def validate(self):
                return []

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path(config_dir) / f"{self.name}.yaml"

        self.TestObject = TestObject

    def test_to_yaml_basic(self):
        """Test basic YAML serialization"""
        obj = self.TestObject("TEST")
        yaml_dict = obj.to_yaml()

        assert isinstance(yaml_dict, dict)
        assert yaml_dict["name"] == "TEST"

    def test_to_yaml_with_comment(self):
        """Test YAML serialization with comment"""
        obj = self.TestObject("TEST", comment="Test comment")
        yaml_dict = obj.to_yaml()

        assert yaml_dict["name"] == "TEST"
        assert yaml_dict["comment"] == "Test comment"

    def test_to_yaml_with_custom_fields(self):
        """Test YAML serialization with custom fields"""
        obj = self.TestObject("TEST", custom_field="custom_value")
        yaml_dict = obj.to_yaml()

        assert yaml_dict["custom_field"] == "custom_value"


class TestFromYaml:
    """Test from_yaml deserialization"""

    def setup_method(self):
        """Set up test fixtures"""

        class TestObject(SnowDDLObject):
            def __init__(self, name, comment=None, email=None):
                super().__init__(name, comment)
                self.email = email

            def to_yaml(self):
                return {"name": self.name}

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name, comment=data.get("comment"), email=data.get("email"))

            def validate(self):
                return []

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path(config_dir) / f"{self.name}.yaml"

        self.TestObject = TestObject

    def test_from_yaml_basic(self):
        """Test basic YAML deserialization"""
        data = {"comment": "Test comment"}
        obj = self.TestObject.from_yaml("TEST_NAME", data)

        assert obj.name == "TEST_NAME"
        assert obj.comment == "Test comment"

    def test_from_yaml_with_custom_fields(self):
        """Test YAML deserialization with custom fields"""
        data = {"comment": "Test comment", "email": "test@example.com"}
        obj = self.TestObject.from_yaml("TEST_NAME", data)

        assert obj.email == "test@example.com"

    def test_from_yaml_empty_data(self):
        """Test YAML deserialization with empty data"""
        obj = self.TestObject.from_yaml("TEST_NAME", {})

        assert obj.name == "TEST_NAME"
        assert obj.comment is None
        assert obj.email is None


class TestValidation:
    """Test validation functionality"""

    def setup_method(self):
        """Set up test fixtures"""

        class TestObject(SnowDDLObject):
            def __init__(self, name, comment=None, required_field=None):
                super().__init__(name, comment)
                self.required_field = required_field

            def to_yaml(self):
                return {}

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name)

            def validate(self):
                from snowddl_core.validation import ValidationError

                errors = []

                if not self.name:
                    errors.append(ValidationError("Name is required"))

                if not self.required_field:
                    errors.append(
                        ValidationError(
                            "required_field is missing",  # Include field name in message
                            object_name=self.name,
                            field="required_field",
                        )
                    )

                return errors

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path(config_dir) / f"{self.name}.yaml"

        self.TestObject = TestObject

    def test_validate_valid_object(self):
        """Test validation of valid object"""
        obj = self.TestObject("TEST", required_field="value")
        errors = obj.validate()

        assert len(errors) == 0

    def test_validate_invalid_object(self):
        """Test validation of invalid object"""
        obj = self.TestObject("TEST")  # Missing required_field
        errors = obj.validate()

        assert len(errors) > 0
        assert any("required_field" in str(e) for e in errors)

    def test_validate_returns_list(self):
        """Test that validate always returns a list"""
        obj = self.TestObject("TEST", required_field="value")
        errors = obj.validate()

        assert isinstance(errors, list)


class TestGetDependencies:
    """Test dependency tracking"""

    def setup_method(self):
        """Set up test fixtures"""

        class TestObject(SnowDDLObject):
            def __init__(self, name, comment=None, depends_on=None):
                super().__init__(name, comment)
                self.depends_on = depends_on or []

            def to_yaml(self):
                return {}

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name)

            def validate(self):
                return []

            def get_dependencies(self):
                # Return list of (object_type, object_name) tuples
                return [("ROLE", dep) for dep in self.depends_on]

            def get_file_path(self, config_dir):
                return Path(config_dir) / f"{self.name}.yaml"

        self.TestObject = TestObject

    def test_get_dependencies_none(self):
        """Test object with no dependencies"""
        obj = self.TestObject("TEST")
        deps = obj.get_dependencies()

        assert isinstance(deps, list)
        assert len(deps) == 0

    def test_get_dependencies_single(self):
        """Test object with single dependency"""
        obj = self.TestObject("TEST", depends_on=["ROLE1"])
        deps = obj.get_dependencies()

        assert len(deps) == 1
        assert deps[0] == ("ROLE", "ROLE1")

    def test_get_dependencies_multiple(self):
        """Test object with multiple dependencies"""
        obj = self.TestObject("TEST", depends_on=["ROLE1", "ROLE2", "ROLE3"])
        deps = obj.get_dependencies()

        assert len(deps) == 3
        assert ("ROLE", "ROLE1") in deps
        assert ("ROLE", "ROLE2") in deps
        assert ("ROLE", "ROLE3") in deps


class TestGetFilePath:
    """Test file path generation"""

    def setup_method(self):
        """Set up test fixtures"""

        class TestObject(SnowDDLObject):
            def to_yaml(self):
                return {}

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name)

            def validate(self):
                return []

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path(config_dir) / "objects" / f"{self.name}.yaml"

        self.TestObject = TestObject

    def test_get_file_path_basic(self):
        """Test basic file path generation"""
        obj = self.TestObject("TEST")
        config_dir = Path("/tmp/snowddl")
        file_path = obj.get_file_path(config_dir)

        assert isinstance(file_path, Path)
        assert str(file_path) == "/tmp/snowddl/objects/TEST.yaml"

    def test_get_file_path_different_configs(self):
        """Test file path with different config directories"""
        obj = self.TestObject("TEST")

        path1 = obj.get_file_path(Path("/config1"))
        path2 = obj.get_file_path(Path("/config2"))

        assert str(path1) == "/config1/objects/TEST.yaml"
        assert str(path2) == "/config2/objects/TEST.yaml"


class TestRoundtripSerialization:
    """Test round-trip YAML serialization/deserialization"""

    def setup_method(self):
        """Set up test fixtures"""

        class TestObject(SnowDDLObject):
            def __init__(self, name, comment=None, email=None, enabled=True):
                super().__init__(name, comment)
                self.email = email
                self.enabled = enabled

            def to_yaml(self):
                yaml_dict = {"name": self.name}
                if self.comment:
                    yaml_dict["comment"] = self.comment
                if self.email:
                    yaml_dict["email"] = self.email
                yaml_dict["enabled"] = self.enabled
                return yaml_dict

            @classmethod
            def from_yaml(cls, name, data):
                return cls(
                    name,
                    comment=data.get("comment"),
                    email=data.get("email"),
                    enabled=data.get("enabled", True),
                )

            def validate(self):
                return []

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path(config_dir) / f"{self.name}.yaml"

        self.TestObject = TestObject

    def test_roundtrip_serialization(self):
        """Test complete round-trip serialization"""
        # Create object
        original = self.TestObject(
            "TEST_USER", comment="Test comment", email="test@example.com", enabled=True
        )

        # Serialize to YAML
        yaml_dict = original.to_yaml()

        # Deserialize from YAML
        restored = self.TestObject.from_yaml("TEST_USER", yaml_dict)

        # Verify all fields match
        assert restored.name == original.name
        assert restored.comment == original.comment
        assert restored.email == original.email
        assert restored.enabled == original.enabled

    def test_roundtrip_with_defaults(self):
        """Test round-trip with default values"""
        original = self.TestObject("TEST")

        yaml_dict = original.to_yaml()
        restored = self.TestObject.from_yaml("TEST", yaml_dict)

        assert restored.name == original.name
        assert restored.enabled == original.enabled


class TestInheritancePatterns:
    """Test inheritance patterns"""

    def test_multiple_inheritance_levels(self):
        """Test multiple levels of inheritance"""

        class BaseObject(SnowDDLObject):
            def to_yaml(self):
                return {"name": self.name}

            @classmethod
            def from_yaml(cls, name, data):
                return cls(name)

            def validate(self):
                return []

            def get_dependencies(self):
                return []

            def get_file_path(self, config_dir):
                return Path(config_dir) / f"{self.name}.yaml"

        class MiddleObject(BaseObject):
            def __init__(self, name, comment=None, category=None):
                super().__init__(name, comment)
                self.category = category

        class LeafObject(MiddleObject):
            def __init__(self, name, comment=None, category=None, subcategory=None):
                super().__init__(name, comment, category)
                self.subcategory = subcategory

        obj = LeafObject(
            "TEST", comment="Comment", category="Cat1", subcategory="SubCat1"
        )

        assert obj.name == "TEST"
        assert obj.comment == "Comment"
        assert obj.category == "Cat1"
        assert obj.subcategory == "SubCat1"
        assert isinstance(obj, SnowDDLObject)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
