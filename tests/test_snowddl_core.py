"""
Comprehensive Test Suite for SnowDDL Core OOP Framework

Tests the object-oriented framework for SnowDDL configurations including
User, Warehouse, BusinessRole, and SnowDDLProject classes.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

# Import SnowDDL core components
from snowddl_core import (
    SnowDDLProject,
    User,
    Warehouse,
    BusinessRole,
    TechnicalRole,
    ResourceMonitor,
)
from snowddl_core.base import AccountLevelObject
from snowddl_core.validation import ValidationError


class TestUserObject:
    """Test User object functionality"""

    def test_user_creation_with_all_fields(self):
        """Test creating a User with all fields"""
        user = User(
            name="JOHN_DOE",
            login_name="john_doe",
            type="PERSON",
            first_name="John",
            last_name="Doe",
            email="john.doe@company.com",
            default_warehouse="COMPUTE_WH",
            business_roles=["ANALYST_ROLE"],
            authentication_policy="mfa_policy",
        )

        assert user.name == "JOHN_DOE"
        assert user.type == "PERSON"
        assert user.email == "john.doe@company.com"
        assert "ANALYST_ROLE" in user.business_roles

    def test_user_to_yaml_conversion(self):
        """Test User to YAML dictionary conversion"""
        user = User(
            name="TEST_USER",
            login_name="test_user",
            type="PERSON",
            first_name="Test",
            last_name="User",
            email="test@company.com",
        )

        yaml_data = user.to_yaml()

        assert yaml_data["first_name"] == "Test"
        assert yaml_data["last_name"] == "User"
        assert yaml_data["email"] == "test@company.com"
        assert yaml_data["login_name"] == "test_user"

    def test_user_from_yaml_loading(self):
        """Test creating User from YAML data"""
        yaml_data = {
            "type": "PERSON",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@company.com",
            "login_name": "jane_smith",
            "default_warehouse": "COMPUTE_WH",
        }

        user = User.from_yaml("JANE_SMITH", yaml_data)

        assert user.name == "JANE_SMITH"
        assert user.first_name == "Jane"
        assert user.last_name == "Smith"
        assert user.email == "jane@company.com"

    def test_user_validation_person_requires_email(self):
        """Test that PERSON type requires email"""
        user = User(
            name="INVALID_USER",
            login_name="invalid",
            type="PERSON",
            first_name="Invalid",
            last_name="User",
            # Missing email
        )

        errors = user.validate()
        assert len(errors) > 0
        assert any("email" in str(error).lower() for error in errors)

    def test_user_validation_service_requires_rsa(self):
        """Test that SERVICE type should use RSA key"""
        user = User(
            name="SERVICE_ACCOUNT",
            login_name="service",
            type="SERVICE",
            email="service@company.com",
            # Missing RSA key
        )

        errors = user.validate()
        assert len(errors) > 0
        assert any("rsa" in str(error).lower() for error in errors)

    def test_user_add_remove_roles(self):
        """Test adding and removing roles from user"""
        user = User(
            name="TEST_USER", login_name="test", type="PERSON", email="test@company.com"
        )

        # Add role
        user.add_role("ANALYST_ROLE")
        assert "ANALYST_ROLE" in user.business_roles

        # Remove role
        user.remove_role("ANALYST_ROLE")
        assert "ANALYST_ROLE" not in user.business_roles

    def test_user_set_rsa_key(self):
        """Test setting RSA public key"""
        user = User(
            name="TEST_USER",
            login_name="test",
            type="SERVICE",
            email="service@company.com",
        )

        # Set RSA key with headers
        public_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""

        user.set_rsa_key(public_key)
        assert user.rsa_public_key is not None
        assert "-----BEGIN" not in user.rsa_public_key

    def test_user_dependencies(self):
        """Test user dependency tracking"""
        user = User(
            name="TEST_USER",
            login_name="test",
            type="PERSON",
            email="test@company.com",
            business_roles=["ROLE1", "ROLE2"],
            default_warehouse="COMPUTE_WH",
        )

        deps = user.get_dependencies()

        # Should have role and warehouse dependencies
        assert ("business_role", "ROLE1") in deps
        assert ("business_role", "ROLE2") in deps
        assert ("warehouse", "COMPUTE_WH") in deps


class TestWarehouseObject:
    """Test Warehouse object functionality"""

    def test_warehouse_creation(self):
        """Test creating a basic warehouse"""
        warehouse = Warehouse(name="COMPUTE_WH", size="X-Small", auto_suspend=60)

        assert warehouse.name == "COMPUTE_WH"
        assert warehouse.size == "X-Small"
        assert warehouse.auto_suspend == 60

    def test_warehouse_multi_cluster_configuration(self):
        """Test multi-cluster warehouse configuration"""
        warehouse = Warehouse(
            name="MULTI_WH",
            size="Large",
            min_cluster_count=2,
            max_cluster_count=5,
            scaling_policy="ECONOMY",
        )

        assert warehouse.min_cluster_count == 2
        assert warehouse.max_cluster_count == 5
        assert warehouse.scaling_policy == "ECONOMY"

    def test_warehouse_enable_multi_cluster(self):
        """Test enabling multi-cluster on warehouse"""
        warehouse = Warehouse(name="TEST_WH")

        warehouse.enable_multi_cluster(min_count=1, max_count=10, policy="STANDARD")

        assert warehouse.min_cluster_count == 1
        assert warehouse.max_cluster_count == 10
        assert warehouse.scaling_policy == "STANDARD"

    def test_warehouse_set_size(self):
        """Test setting warehouse size"""
        warehouse = Warehouse(name="TEST_WH", size="X-Small")

        warehouse.set_size("Large")
        assert warehouse.size == "Large"

    def test_warehouse_to_yaml(self):
        """Test warehouse YAML serialization"""
        warehouse = Warehouse(
            name="TEST_WH",
            size="Medium",
            auto_suspend=300,
            enable_query_acceleration=True,
        )

        yaml_data = warehouse.to_yaml()

        assert yaml_data["size"] == "Medium"
        assert yaml_data["auto_suspend"] == 300
        assert yaml_data["enable_query_acceleration"] is True

    def test_warehouse_from_yaml(self):
        """Test warehouse deserialization from YAML"""
        yaml_data = {
            "size": "Large",
            "auto_suspend": 120,
            "min_cluster_count": 2,
            "max_cluster_count": 4,
        }

        warehouse = Warehouse.from_yaml("PROD_WH", yaml_data)

        assert warehouse.name == "PROD_WH"
        assert warehouse.size == "Large"
        assert warehouse.min_cluster_count == 2

    def test_warehouse_validation(self):
        """Test warehouse configuration validation"""
        warehouse = Warehouse(
            name="INVALID_WH",
            min_cluster_count=5,
            max_cluster_count=2,  # Invalid: min > max
        )

        errors = warehouse.validate()
        assert len(errors) > 0

    def test_warehouse_dependencies(self):
        """Test warehouse dependency tracking"""
        warehouse = Warehouse(name="TEST_WH", resource_monitor="COST_MONITOR")

        deps = warehouse.get_dependencies()
        assert ("resource_monitor", "COST_MONITOR") in deps


class TestBusinessRoleObject:
    """Test BusinessRole object functionality"""

    def test_business_role_creation(self):
        """Test creating a business role"""
        role = BusinessRole(
            name="ANALYST_ROLE",
            database_read=["ANALYTICS_DB"],
            warehouse_usage=["COMPUTE_WH"],
            comment="Analytics role for data analysts",
        )

        assert role.name == "ANALYST_ROLE"
        assert "ANALYTICS_DB" in role.database_read
        assert "COMPUTE_WH" in role.warehouse_usage

    def test_business_role_grant_database_access(self):
        """Test granting database access to role"""
        role = BusinessRole(name="TEST_ROLE")

        role.grant_database_access("DB1", "read")
        role.grant_database_access("DB2", "write")
        role.grant_database_access("DB3", "owner")

        assert "DB1" in role.database_read
        assert "DB2" in role.database_write
        assert "DB3" in role.database_owner

    def test_business_role_grant_schema_access(self):
        """Test granting schema-level access"""
        role = BusinessRole(name="TEST_ROLE")

        role.grant_schema_access("DB.SCHEMA1", "read")
        role.grant_schema_access("DB.SCHEMA2", "write")

        assert "DB.SCHEMA1" in role.schema_read
        assert "DB.SCHEMA2" in role.schema_write

    def test_business_role_add_warehouse_usage(self):
        """Test adding warehouse usage to role"""
        role = BusinessRole(name="TEST_ROLE")

        role.add_warehouse_usage("WH1")
        role.add_warehouse_usage("WH2")

        assert "WH1" in role.warehouse_usage
        assert "WH2" in role.warehouse_usage

    def test_business_role_add_tech_role(self):
        """Test adding technical role"""
        role = BusinessRole(name="BUSINESS_ROLE")

        role.add_tech_role("TECH_ROLE_1")
        role.add_tech_role("TECH_ROLE_2")

        assert "TECH_ROLE_1" in role.tech_roles
        assert "TECH_ROLE_2" in role.tech_roles

    def test_business_role_to_yaml(self):
        """Test business role YAML serialization"""
        role = BusinessRole(
            name="TEST_ROLE",
            database_read=["DB1", "DB2"],
            warehouse_usage=["WH1"],
            tech_roles=["TECH1"],
        )

        yaml_data = role.to_yaml()

        assert yaml_data["database_read"] == ["DB1", "DB2"]
        assert yaml_data["warehouse_usage"] == ["WH1"]
        assert yaml_data["tech_roles"] == ["TECH1"]

    def test_business_role_validation_schema_fqn(self):
        """Test validation of schema FQN format"""
        role = BusinessRole(
            name="INVALID_ROLE",
            schema_read=["INVALID_SCHEMA"],  # Missing DATABASE.SCHEMA format
        )

        errors = role.validate()
        assert len(errors) > 0

    def test_business_role_dependencies(self):
        """Test business role dependency tracking"""
        role = BusinessRole(
            name="TEST_ROLE",
            database_read=["DB1", "DB2"],
            warehouse_usage=["WH1"],
            tech_roles=["TECH1"],
        )

        deps = role.get_dependencies()

        assert ("database", "DB1") in deps
        assert ("database", "DB2") in deps
        assert ("warehouse", "WH1") in deps
        assert ("tech_role", "TECH1") in deps


class TestSnowDDLProject:
    """Test SnowDDLProject orchestrator"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path("/tmp/test_snowddl_project")
        self.temp_dir.mkdir(exist_ok=True)

        # Create sample user.yaml
        users = {
            "USER1": {
                "type": "PERSON",
                "first_name": "User",
                "last_name": "One",
                "email": "user1@test.com",
                "login_name": "user1",
            }
        }

        with open(self.temp_dir / "user.yaml", "w") as f:
            yaml.dump(users, f)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_project_initialization(self):
        """Test project initialization"""
        project = SnowDDLProject(self.temp_dir, auto_load=False)

        assert project.config_dir == self.temp_dir
        assert len(project.users) == 0

    def test_project_load_all(self):
        """Test loading all configurations"""
        project = SnowDDLProject(self.temp_dir, auto_load=True)

        assert "USER1" in project.users
        assert project.users["USER1"].first_name == "User"

    def test_project_add_user(self):
        """Test adding a user to project"""
        project = SnowDDLProject(self.temp_dir, auto_load=False)

        user = User(
            name="NEW_USER", login_name="new_user", type="PERSON", email="new@test.com"
        )

        project.add_user(user)
        assert "NEW_USER" in project.users

    def test_project_add_warehouse(self):
        """Test adding a warehouse to project"""
        project = SnowDDLProject(self.temp_dir, auto_load=False)

        warehouse = Warehouse(name="TEST_WH", size="Medium")

        project.add_warehouse(warehouse)
        assert "TEST_WH" in project.warehouses

    def test_project_get_user(self):
        """Test retrieving a user"""
        project = SnowDDLProject(self.temp_dir, auto_load=True)

        user = project.get_user("USER1")
        assert user is not None
        assert user.name == "USER1"

    def test_project_get_all_objects(self):
        """Test getting all objects"""
        project = SnowDDLProject(self.temp_dir, auto_load=True)

        # Add some objects
        project.add_warehouse(Warehouse(name="WH1"))
        project.add_business_role(BusinessRole(name="ROLE1"))

        all_objects = project.get_all_objects()
        assert len(all_objects) >= 3  # At least 1 user + 1 warehouse + 1 role

    def test_project_validate(self):
        """Test project validation"""
        project = SnowDDLProject(self.temp_dir, auto_load=True)

        # Add invalid user
        invalid_user = User(
            name="INVALID",
            login_name="invalid",
            type="PERSON",
            # Missing email
        )
        project.add_user(invalid_user)

        errors = project.validate()
        assert len(errors) > 0

    def test_project_object_exists(self):
        """Test checking object existence"""
        project = SnowDDLProject(self.temp_dir, auto_load=True)

        assert project.object_exists("user", "USER1")
        assert not project.object_exists("user", "NONEXISTENT")

    def test_project_summary(self):
        """Test project summary statistics"""
        project = SnowDDLProject(self.temp_dir, auto_load=True)

        summary = project.summary()

        assert "users" in summary
        assert "warehouses" in summary
        assert summary["users"] >= 1

    def test_project_save_users(self):
        """Test saving users to YAML"""
        project = SnowDDLProject(self.temp_dir, auto_load=False)

        user = User(
            name="SAVE_TEST",
            login_name="save_test",
            type="PERSON",
            email="save@test.com",
        )
        project.add_user(user)

        project.save_users()

        # Verify file was created
        assert (self.temp_dir / "user.yaml").exists()


class TestResourceMonitor:
    """Test ResourceMonitor object"""

    def test_resource_monitor_creation(self):
        """Test creating a resource monitor"""
        monitor = ResourceMonitor(
            name="COST_MONITOR",
            credit_quota=1000,
            frequency="MONTHLY",
            notify_at=[80, 90],
            suspend_at=100,
        )

        assert monitor.name == "COST_MONITOR"
        assert monitor.credit_quota == 1000
        assert 80 in monitor.notify_at

    def test_resource_monitor_to_yaml(self):
        """Test resource monitor YAML serialization"""
        monitor = ResourceMonitor(name="TEST_MONITOR", credit_quota=500, suspend_at=95)

        yaml_data = monitor.to_yaml()
        assert yaml_data["credit_quota"] == 500
        assert yaml_data["suspend_at"] == 95

    def test_resource_monitor_validation(self):
        """Test resource monitor validation"""
        monitor = ResourceMonitor(
            name="INVALID_MONITOR", suspend_at=150  # Invalid: > 100%
        )

        errors = monitor.validate()
        assert len(errors) > 0


class TestYAMLRoundTrip:
    """Test YAML serialization round-trips"""

    def test_user_yaml_roundtrip(self):
        """Test User YAML round-trip"""
        original = User(
            name="TEST",
            login_name="test",
            type="PERSON",
            email="test@test.com",
            first_name="Test",
            last_name="User",
        )

        yaml_data = original.to_yaml()
        restored = User.from_yaml("TEST", yaml_data)

        assert original.email == restored.email
        assert original.first_name == restored.first_name

    def test_warehouse_yaml_roundtrip(self):
        """Test Warehouse YAML round-trip"""
        original = Warehouse(name="TEST_WH", size="Large", auto_suspend=300)

        yaml_data = original.to_yaml()
        restored = Warehouse.from_yaml("TEST_WH", yaml_data)

        assert original.size == restored.size
        assert original.auto_suspend == restored.auto_suspend


class TestObjectIdentity:
    """Test object identity and comparison"""

    def test_user_equality(self):
        """Test user equality comparison"""
        user1 = User(
            name="TEST", login_name="test", type="PERSON", email="test@test.com"
        )
        user2 = User(
            name="TEST", login_name="test", type="PERSON", email="test@test.com"
        )

        assert user1 == user2

    def test_user_hash(self):
        """Test user hashing for sets/dicts"""
        user1 = User(
            name="TEST", login_name="test", type="PERSON", email="test@test.com"
        )
        user2 = User(
            name="TEST", login_name="test", type="PERSON", email="test@test.com"
        )

        user_set = {user1, user2}
        assert len(user_set) == 1  # Should be deduplicated


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/snowddl_core"])
