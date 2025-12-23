"""Pytest configuration and shared fixtures for SnowDDL tests"""

import os
import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import Mock, patch


@pytest.fixture(scope="session")
def snowddl_test_config() -> Dict[str, str]:
    """Provide test configuration for SnowDDL"""
    return {
        "account": os.environ.get("TEST_SNOWFLAKE_ACCOUNT", "test-account"),
        "user": os.environ.get("TEST_SNOWFLAKE_USER", "test-user"),
        "role": "ACCOUNTADMIN",
        "warehouse": "COMPUTE_WH",
        "database": "SNOWDDL",
    }


@pytest.fixture(scope="function")
def temp_config_dir() -> Generator[Path, None, None]:
    """Create temporary configuration directory with basic SnowDDL structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)

        # Create basic user configuration
        user_config = {
            "TEST_USER": {
                "type": "PERSON",
                "login_name": "TEST_USER",
                "display_name": "Test User",
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "default_role": "TEST_ROLE",
                "must_change_password": False,
                "disabled": False,
            },
            "TEST_SERVICE": {
                "type": "SERVICE",
                "login_name": "TEST_SERVICE",
                "display_name": "Test Service Account",
                "default_role": "SERVICE_ROLE",
                "disabled": False,
                "rsa_public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----",
            },
        }
        (config_dir / "user.yaml").write_text(
            yaml.dump(user_config, default_flow_style=False)
        )

        # Create basic role configuration
        role_config = {
            "TEST_ROLE": {"type": "CUSTOM", "comment": "Test role for unit tests"},
            "SERVICE_ROLE": {"type": "CUSTOM", "comment": "Service role for testing"},
        }
        (config_dir / "role.yaml").write_text(
            yaml.dump(role_config, default_flow_style=False)
        )

        # Create warehouse configuration
        warehouse_config = {
            "TEST_WH": {
                "type": "WAREHOUSE",
                "size": "XSMALL",
                "auto_suspend": 60,
                "auto_resume": True,
                "initially_suspended": True,
                "comment": "Test warehouse",
            }
        }
        (config_dir / "warehouse.yaml").write_text(
            yaml.dump(warehouse_config, default_flow_style=False)
        )

        # Create database configuration
        db_dir = config_dir / "TEST_DB"
        db_dir.mkdir()
        (db_dir / "params.yaml").write_text(
            """
comment: Test database
data_retention_time_in_days: 7
"""
        )

        # Create schema configuration
        schema_dir = db_dir / "schema"
        schema_dir.mkdir()
        (schema_dir / "PUBLIC.yaml").write_text(
            """
type: SCHEMA
comment: Public schema for test database
"""
        )

        yield config_dir


@pytest.fixture
def mock_snowddl_command(monkeypatch):
    """Mock SnowDDL command execution"""

    def mock_run(*args, **kwargs):
        if isinstance(args[0], list) and any("snowddl" in str(arg) for arg in args[0]):
            # Determine operation from arguments
            if "--plan" in args[0]:
                return Mock(
                    returncode=0,
                    stdout="-- SnowDDL Plan --\nCREATE USER TEST_USER;\nCREATE ROLE TEST_ROLE;\n",
                    stderr="",
                )
            elif "--apply" in args[0]:
                return Mock(
                    returncode=0,
                    stdout="-- SnowDDL Apply --\nUser TEST_USER created\nRole TEST_ROLE created\n",
                    stderr="",
                )
            elif "--diff" in args[0]:
                return Mock(
                    returncode=0,
                    stdout="-- SnowDDL Diff --\n+CREATE USER NEW_USER;\n-DROP USER OLD_USER;\n",
                    stderr="",
                )
            else:
                return Mock(
                    returncode=0, stdout="SnowDDL operation completed", stderr=""
                )
        return Mock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", mock_run)


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "SAMPLE_USER": {
            "type": "PERSON",
            "login_name": "SAMPLE_USER",
            "display_name": "Sample User",
            "first_name": "Sample",
            "last_name": "User",
            "email": "sample.user@company.com",
            "default_role": "DEVELOPER",
            "must_change_password": False,
            "disabled": False,
        }
    }


@pytest.fixture
def sample_service_account_data():
    """Sample service account data for testing"""
    return {
        "SAMPLE_SERVICE": {
            "type": "SERVICE",
            "login_name": "SAMPLE_SERVICE",
            "display_name": "Sample Service Account",
            "default_role": "SERVICE_ROLE",
            "disabled": False,
            "rsa_public_key": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyJq7K8kJd8cJxKvx...
-----END PUBLIC KEY-----""",
        }
    }


@pytest.fixture
def sample_role_data():
    """Sample role data for testing"""
    return {
        "SAMPLE_ROLE": {"type": "CUSTOM", "comment": "Sample custom role for testing"}
    }


@pytest.fixture
def test_fernet_key():
    """Generate test Fernet key for encryption testing"""
    from cryptography.fernet import Fernet

    return Fernet.generate_key()


@pytest.fixture
def mock_encryption(monkeypatch, test_fernet_key):
    """Mock encryption functionality"""
    from cryptography.fernet import Fernet

    def mock_encrypt_password(password, key=None):
        if key is None:
            key = test_fernet_key
        f = Fernet(key)
        return f.encrypt(password.encode()).decode()

    def mock_decrypt_password(encrypted_password, key=None):
        if key is None:
            key = test_fernet_key
        f = Fernet(key)
        return f.decrypt(encrypted_password.encode()).decode()

    # Note: encrypt_password and decrypt_password are methods of FernetEncryption class
    # We'll skip mocking them for now since the tests that use them are skipped


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables"""
    test_env = {
        "SNOWFLAKE_ACCOUNT": "test-account",
        "SNOWFLAKE_USER": "test-user",
        "SNOWFLAKE_PASSWORD": "test-password",
        "SNOWFLAKE_ROLE": "ACCOUNTADMIN",
        "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH",
        "SNOWFLAKE_DATABASE": "SNOWDDL",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def config_validator():
    """Provide configuration validation utilities"""

    def validate_yaml_syntax(yaml_path: Path) -> tuple[bool, str]:
        """Validate YAML syntax"""
        try:
            with open(yaml_path) as f:
                yaml.safe_load(f)
            return True, ""
        except yaml.YAMLError as e:
            return False, str(e)

    def validate_user_config(user_data: dict) -> tuple[bool, list]:
        """Validate user configuration structure"""
        errors = []
        required_fields = ["type", "login_name"]

        for field in required_fields:
            if field not in user_data:
                errors.append(f"Missing required field: {field}")

        if user_data.get("type") == "PERSON":
            person_required = ["email", "first_name", "last_name"]
            for field in person_required:
                if field not in user_data:
                    errors.append(f"Missing required field for PERSON: {field}")

        return len(errors) == 0, errors

    return {
        "validate_yaml_syntax": validate_yaml_syntax,
        "validate_user_config": validate_user_config,
    }


@pytest.fixture
def git_repo_mock(monkeypatch):
    """Mock git repository operations"""

    class MockRepo:
        def __init__(self, path):
            self.path = path

        def git(self):
            return MockGit()

    class MockGit:
        def add(self, *args):
            pass

        def commit(self, *args, **kwargs):
            pass

        def status(self, *args, **kwargs):
            return "On branch main\nnothing to commit, working tree clean"

    def mock_repo_init(path):
        return MockRepo(path)

    monkeypatch.setattr("git.Repo", MockRepo)


@pytest.fixture
def snowflake_connection_mock():
    """Mock Snowflake connection for testing"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        ("TEST_USER", "PERSON", "test@example.com", "TEST_ROLE"),
        ("TEST_SERVICE", "SERVICE", None, "SERVICE_ROLE"),
    ]
    return mock_conn


@pytest.fixture
def deployment_history():
    """Mock deployment history for testing"""
    return [
        {
            "timestamp": "2023-08-15T10:30:00Z",
            "user": "test-user",
            "operation": "apply",
            "status": "success",
            "objects_created": 5,
            "objects_modified": 2,
            "objects_deleted": 0,
        },
        {
            "timestamp": "2023-08-14T15:45:00Z",
            "user": "test-user",
            "operation": "plan",
            "status": "success",
            "objects_created": 0,
            "objects_modified": 0,
            "objects_deleted": 0,
        },
    ]
