# SnowDDL Core - Pythonic OOP Framework

A modern, type-safe Python API for programmatically managing SnowDDL configurations with 100% backward compatibility with existing YAML files.

## Features

- **Pythonic API**: Clean, intuitive Python classes for all Snowflake objects
- **Type Safety**: Full type hints throughout (Python 3.10+)
- **YAML Compatible**: Seamless integration with existing SnowDDL YAML files
- **Validation Framework**: Comprehensive validation with security best practices
- **Dependency Management**: Automatic dependency tracking and resolution
- **Project Orchestration**: High-level `SnowDDLProject` API for configuration management

## Quick Start

### Installation

The framework is part of the `snowtower-snowddl` package:

```bash
uv sync
```

### Basic Usage

```python
from snowddl_core import SnowDDLProject, User, Warehouse, BusinessRole

# Load existing configuration
project = SnowDDLProject("./snowddl")
project.load_all()

print(f"Loaded: {project.summary()}")

# Get existing user
user = project.get_user("ALICE")
print(f"User: {user.name}, Email: {user.email}")

# Create new objects
new_user = User(
    name="DATA_ENGINEER",
    login_name="data_engineer",
    type="PERSON",
    email="engineer@company.com",
    business_roles=["DATA_ENGINEER_ROLE"],
    default_warehouse="ETL_WH"
)

# Add to project
project.add_user(new_user)

# Save to YAML
project.save_all()
```

## Core Classes

### Base Classes

- **`SnowDDLObject`**: Abstract base for all objects
- **`AccountLevelObject`**: Base for account-level objects (users, warehouses, roles)
- **`DatabaseLevelObject`**: Base for database-level objects
- **`SchemaLevelObject`**: Base for schema-level objects

### Account Objects

- **`User`**: Snowflake user accounts with authentication and authorization
- **`Warehouse`**: Compute warehouses for query execution
- **`BusinessRole`**: High-level roles combining permissions
- **`TechnicalRole`**: Technical roles for specific object permissions
- **`ResourceMonitor`**: Resource monitors for cost control

### Project Management

- **`SnowDDLProject`**: Main orchestrator for loading, managing, and saving configurations

## API Reference

### Creating Objects

```python
# User with RSA key authentication
user = User(
    name="SERVICE_ACCOUNT",
    login_name="service_user",
    type="SERVICE",
    rsa_public_key="MIIBIjAN...",
    business_roles=["SERVICE_ROLE"],
    comment="Service account for automation"
)

# Multi-cluster warehouse
warehouse = Warehouse(
    name="PRODUCTION_WH",
    size="Large",
    min_cluster_count=1,
    max_cluster_count=5,
    scaling_policy="STANDARD",
    auto_suspend=300,
    enable_query_acceleration=True
)

# Business role with permissions
role = BusinessRole(
    name="DATA_ANALYST_ROLE",
    database_read=["ANALYTICS_DB"],
    schema_read=["ANALYTICS_DB.PUBLIC"],
    warehouse_usage=["ANALYST_WH"]
)
```

### Working with Projects

```python
# Initialize project
project = SnowDDLProject("./snowddl")

# Load configurations
project.load_all()  # Load everything
project.load_users()  # Load only users
project.load_warehouses()  # Load only warehouses

# Access objects
user = project.get_user("USERNAME")
warehouse = project.get_warehouse("WH_NAME")
role = project.get_business_role("ROLE_NAME")

# Add objects
project.add_user(new_user)
project.add_warehouse(new_warehouse)
project.add_business_role(new_role)

# Get all objects
all_objects = project.get_all_objects()

# Validate
errors = project.validate()
for error in errors:
    print(error)

# Save configurations
project.save_all()  # Save everything
project.save_users()  # Save only users
```

### YAML Serialization

```python
# Convert object to YAML dictionary
yaml_dict = user.to_yaml()

# Create object from YAML
user = User.from_yaml("USERNAME", yaml_dict)

# YAML round-trip
original = User(name="TEST", login_name="test", email="test@test.com")
yaml_data = original.to_yaml()
restored = User.from_yaml("TEST", yaml_data)
assert original.to_yaml() == restored.to_yaml()
```

### Validation

```python
# Validate individual object
user = User(name="TEST", login_name="test", type="PERSON")
# Missing email and authentication
errors = user.validate()
for error in errors:
    print(error)
# Output:
# [ERROR] User TEST: PERSON type requires email
# [ERROR] User TEST: PERSON type requires authentication

# Validate entire project
project = SnowDDLProject("./snowddl")
project.load_all()
errors = project.validate()
print(f"Found {len(errors)} validation errors")
```

### Helper Methods

```python
# User methods
user.set_rsa_key(public_key_string)
user.add_role("ROLE_NAME")
user.remove_role("ROLE_NAME")
user.set_password(plain_password)  # Encrypts with Fernet

# BusinessRole methods
role.grant_database_access("DB_NAME", "read")
role.grant_schema_access("DB.SCHEMA", "write")
role.add_warehouse_usage("WH_NAME")
role.add_tech_role("TECH_ROLE")

# Warehouse methods
warehouse.set_size("X-Large")
warehouse.enable_multi_cluster(min_count=1, max_count=10, policy="STANDARD")
```

## Type Hints and IDE Support

All classes are fully type-hinted for excellent IDE support:

```python
from snowddl_core import User, UserType
from typing import Optional

def create_user(
    name: str,
    login_name: str,
    user_type: UserType = "PERSON",
    email: Optional[str] = None
) -> User:
    return User(
        name=name,
        login_name=login_name,
        type=user_type,
        email=email
    )
```

## Examples

See `EXAMPLE_USAGE.py` for comprehensive examples including:

1. Loading and inspecting configurations
2. Creating users programmatically
3. Creating warehouses with advanced settings
4. Creating business roles with permissions
5. Creating resource monitors
6. Validation workflows
7. Saving configurations

Run the examples:

```bash
uv run python src/snowddl_core/EXAMPLE_USAGE.py
```

## Architecture

### Class Hierarchy

```
SnowDDLObject (ABC)
├── AccountLevelObject (ABC)
│   ├── User
│   ├── Warehouse
│   ├── BusinessRole
│   ├── TechnicalRole
│   └── ResourceMonitor
├── DatabaseLevelObject (ABC)
│   └── Database
└── SchemaLevelObject (ABC)
    ├── Table
    ├── View
    └── ...
```

### Mixins

Mixins provide reusable functionality:

- **`PolicyReferenceMixin`**: Authentication and network policy references
- **`EncryptedFieldMixin`**: Password encryption/decryption
- **`TableLikeMixin`**: Data governance policies
- **`TransientMixin`**: Transient and retention settings

### File Structure

```
src/snowddl_core/
├── __init__.py           # Public API exports
├── base.py               # Base classes
├── mixins.py             # Mixin classes
├── account_objects.py    # Account-level objects
├── validation.py         # Validation framework
├── project.py            # Project orchestration
├── snowddl_types.py      # Type definitions
├── exceptions.py         # Custom exceptions
├── EXAMPLE_USAGE.py      # Usage examples
└── README.md            # This file
```

## Testing

### Unit Tests

```bash
# Test individual components
uv run python -c "from snowddl_core import User; u = User(name='TEST', login_name='test'); print(u)"
```

### Integration Tests

```bash
# Test with actual SnowDDL
uv run snowddl-plan
```

### Example Tests

```bash
# Run all examples
uv run python src/snowddl_core/EXAMPLE_USAGE.py
```

## Migration Guide

### From Dataclasses

The framework was refactored from dataclasses to regular classes:

```python
# Old (dataclass style - still works via from_yaml)
@dataclass
class User:
    name: str
    login_name: str = ""

# New (regular class)
class User:
    def __init__(self, name: str, login_name: str, ...):
        self.name = name
        self.login_name = login_name
```

### From YAML-Only Workflows

If you previously only edited YAML files:

```python
# Now you can use Python API
from snowddl_core import SnowDDLProject, User

# Load existing config
project = SnowDDLProject("./snowddl")
project.load_all()

# Modify in Python
user = project.get_user("ALICE")
user.add_role("NEW_ROLE")

# Save back to YAML
project.save_all()
```

## Best Practices

1. **Use type hints**: Always specify types for better IDE support
2. **Validate early**: Call `.validate()` before saving
3. **Use helper methods**: Leverage built-in methods like `add_role()` and `grant_database_access()`
4. **Project-level operations**: Use `SnowDDLProject` for loading/saving YAML
5. **Error handling**: Check validation errors before deployment

## Advanced Usage

### Custom Validation Rules

```python
from snowddl_core.validation import ValidationRule, ValidationError, ValidationContext

class CustomRule(ValidationRule):
    def validate(self, obj, context):
        errors = []
        # Custom validation logic
        return errors

validator = Validator()
validator.add_rule(CustomRule())
```

### Dependency Tracking

```python
# Get dependencies
user = project.get_user("ALICE")
deps = user.get_dependencies()
for dep_type, dep_name in deps:
    print(f"Depends on {dep_type}: {dep_name}")
```

### Encryption

```python
import os

# Set Fernet key
os.environ['SNOWFLAKE_CONFIG_FERNET_KEYS'] = 'your-key-here'

# Encrypt password
user.set_password("plain_password")  # Automatically encrypted

# Decrypt password
plain = user.get_plain_password()
```

## Troubleshooting

### YAML Tag Errors

If you see `ConstructorError: could not determine a constructor for the tag '!decrypt'`:

```python
# The framework auto-registers YAML tags when importing
from snowddl_core import SnowDDLProject  # This registers !decrypt tag
```

### Validation Errors

```python
# Get detailed validation info
errors = project.validate()
for error in errors:
    print(f"{error.severity}: {error.object_type} {error.object_name} - {error.message}")
```

## Contributing

When adding new object types:

1. Create class inheriting from appropriate base
2. Implement abstract methods: `to_yaml()`, `from_yaml()`, `validate()`, `get_dependencies()`, `get_file_path()`
3. Add type hints and docstrings
4. Add to `__init__.py` exports
5. Update project loader/saver methods
6. Add examples

## License

Part of the SnowTower project.

## Support

For issues and questions, refer to the main SnowTower documentation or create an issue in the repository.
