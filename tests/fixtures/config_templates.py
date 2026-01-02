"""Configuration templates for SnowDDL tests"""

# Basic User Configuration Templates
BASIC_USER_CONFIG = {
    "TEST_USER": {
        "type": "PERSON",
        "login_name": "TEST_USER",
        "display_name": "Test User",
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "default_role": "PUBLIC",
        "must_change_password": False,
        "disabled": False,
    }
}

SERVICE_ACCOUNT_CONFIG = {
    "TEST_SERVICE": {
        "type": "SERVICE",
        "login_name": "TEST_SERVICE",
        "display_name": "Test Service Account",
        "default_role": "SERVICE_ROLE",
        "disabled": False,
        "rsa_public_key": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----""",
    }
}

# Role Configuration Templates
BASIC_ROLE_CONFIG = {
    "CUSTOM_ROLE": {"type": "CUSTOM", "comment": "Custom role for testing"},
    "SERVICE_ROLE": {"type": "CUSTOM", "comment": "Role for service accounts"},
}

# Warehouse Configuration Templates
WAREHOUSE_CONFIG = {
    "TEST_WH": {
        "type": "WAREHOUSE",
        "size": "XSMALL",
        "auto_suspend": 60,
        "auto_resume": True,
        "initially_suspended": True,
        "comment": "Test warehouse for integration tests",
    }
}

# Database Parameters Template
DATABASE_PARAMS = {
    "comment": "Test database for integration testing",
    "data_retention_time_in_days": 7,
}

# Network Policy Templates
NETWORK_POLICY_CONFIG = {
    "TEST_NETWORK_POLICY": {
        "type": "NETWORK_POLICY",
        "allowed_ip_list": ["192.168.1.0/24", "10.0.0.0/8"],
        "blocked_ip_list": [],
        "comment": "Test network policy",
    }
}

# Password Policy Templates
PASSWORD_POLICY_CONFIG = {
    "TEST_PASSWORD_POLICY": {
        "type": "PASSWORD_POLICY",
        "password_min_length": 8,
        "password_max_age_days": 180,
        "password_min_upper_case_chars": 1,
        "password_min_lower_case_chars": 1,
        "password_min_numeric_chars": 1,
        "password_min_special_chars": 0,
        "password_history": 3,
        "comment": "Test password policy",
    }
}

# Authentication Policy Templates
AUTHENTICATION_POLICY_CONFIG = {
    "TEST_AUTH_POLICY": {
        "type": "AUTHENTICATION_POLICY",
        "authentication_methods": ["SAML", "PASSWORD"],
        "mfa_authentication_methods": ["SAML"],
        "client_types": ["SNOWFLAKE_UI", "DRIVERS"],
        "security_integrations": ["SAML_INTEGRATION"],
        "comment": "Test authentication policy",
    }
}

# Session Policy Templates
SESSION_POLICY_CONFIG = {
    "TEST_SESSION_POLICY": {
        "type": "SESSION_POLICY",
        "session_idle_timeout_mins": 60,
        "session_ui_idle_timeout_mins": 30,
        "comment": "Test session policy",
    }
}

# Complex Multi-Environment Template
MULTI_ENV_CONFIG = {
    "users": {
        "ENV_USER_{{env}}": {
            "type": "PERSON",
            "login_name": "ENV_USER_{{env}}",
            "display_name": "{{env}} Environment User",
            "first_name": "{{env}}",
            "last_name": "User",
            "email": "{{env}}.user@company.com",
            "default_role": "{{env}}_ROLE",
        }
    },
    "roles": {
        "{{env}}_ROLE": {"type": "CUSTOM", "comment": "Role for {{env}} environment"}
    },
    "warehouses": {
        "{{env}}_WH": {
            "type": "WAREHOUSE",
            "size": "{{warehouse_size}}",
            "auto_suspend": 60,
            "auto_resume": True,
            "comment": "{{env}} environment warehouse",
        }
    },
}

# Validation Test Cases
INVALID_USER_CONFIGS = [
    {
        "name": "MISSING_TYPE",
        "config": {
            "login_name": "TEST_USER",
            "email": "test@example.com",
            # Missing required 'type' field
        },
        "expected_error": "Missing required field: type",
    },
    {
        "name": "INVALID_EMAIL",
        "config": {
            "type": "PERSON",
            "login_name": "TEST_USER",
            "email": "invalid-email",  # Invalid email format
        },
        "expected_error": "Invalid email format",
    },
    {
        "name": "SERVICE_WITH_EMAIL",
        "config": {
            "type": "SERVICE",
            "login_name": "SERVICE_USER",
            "email": "service@example.com",  # Services shouldn't have email
        },
        "expected_error": "Service accounts should not have email",
    },
]

# Integration Test Scenarios
DEPLOYMENT_SCENARIOS = [
    {
        "name": "basic_user_creation",
        "description": "Create a basic user with minimal configuration",
        "config": BASIC_USER_CONFIG,
        "expected_objects": ["USER TEST_USER"],
    },
    {
        "name": "service_account_with_rsa",
        "description": "Create service account with RSA key",
        "config": SERVICE_ACCOUNT_CONFIG,
        "expected_objects": ["USER TEST_SERVICE"],
    },
    {
        "name": "full_infrastructure",
        "description": "Deploy complete infrastructure stack",
        "config": {
            "users": BASIC_USER_CONFIG,
            "roles": BASIC_ROLE_CONFIG,
            "warehouses": WAREHOUSE_CONFIG,
        },
        "expected_objects": [
            "USER TEST_USER",
            "ROLE CUSTOM_ROLE",
            "ROLE SERVICE_ROLE",
            "WAREHOUSE TEST_WH",
        ],
    },
]

# Error Scenarios for Testing
ERROR_SCENARIOS = [
    {
        "name": "malformed_yaml",
        "content": "invalid: yaml: content:",
        "expected_error": "YAML parsing error",
    },
    {
        "name": "circular_role_dependency",
        "content": {
            "ROLE_A": {"type": "CUSTOM", "parent_role": "ROLE_B"},
            "ROLE_B": {"type": "CUSTOM", "parent_role": "ROLE_A"},
        },
        "expected_error": "Circular dependency detected",
    },
    {
        "name": "missing_referenced_role",
        "content": {
            "users": {
                "USER_WITH_MISSING_ROLE": {
                    "type": "PERSON",
                    "default_role": "NONEXISTENT_ROLE",
                }
            }
        },
        "expected_error": "Referenced role does not exist",
    },
]

# Performance Test Data
LARGE_CONFIG_TEMPLATE = {
    "users": {
        f"USER_{i:04d}": {
            "type": "PERSON",
            "login_name": f"USER_{i:04d}",
            "display_name": f"Test User {i:04d}",
            "first_name": "Test",
            "last_name": f"User{i:04d}",
            "email": f"user{i:04d}@company.com",
            "default_role": f"ROLE_{i % 10:02d}",
        }
        for i in range(100)  # 100 users for performance testing
    },
    "roles": {
        f"ROLE_{i:02d}": {"type": "CUSTOM", "comment": f"Test role {i:02d}"}
        for i in range(10)  # 10 roles
    },
}

# Backup and Restore Test Data
BACKUP_TEST_CONFIG = {
    "original_state": {
        "users": {
            "ORIGINAL_USER": {
                "type": "PERSON",
                "login_name": "ORIGINAL_USER",
                "email": "original@company.com",
            }
        }
    },
    "modified_state": {
        "users": {
            "ORIGINAL_USER": {
                "type": "PERSON",
                "login_name": "ORIGINAL_USER",
                "email": "modified@company.com",  # Changed email
            },
            "NEW_USER": {
                "type": "PERSON",
                "login_name": "NEW_USER",
                "email": "new@company.com",
            },
        }
    },
}
