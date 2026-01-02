# Code Patterns and Conventions

## Python Patterns

### Script Template
Every script in `scripts/` should follow this pattern:

```python
#!/usr/bin/env python3
"""
Script description.

Usage:
    uv run command-name [options]
"""

from dotenv import load_dotenv
load_dotenv()  # ALWAYS FIRST

import argparse
import sys
from pathlib import Path

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.snowddl_core import SnowDDLClient


def parse_args():
    parser = argparse.ArgumentParser(
        description="Command description",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        client = SnowDDLClient()
        # Implementation here

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### CLI Wrapper Pattern
In `src/management_cli.py`:

```python
def my_command():
    """Short description for --help."""
    from scripts.my_script import main
    main()
```

### Configuration Loading Pattern
```python
import os
from dotenv import load_dotenv

load_dotenv()

SNOWFLAKE_CONFIG = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
}
```

## YAML Patterns

### User Definition
```yaml
# Standard human user
USERNAME:
  type: PERSON
  default_role: USER_ROLE
  default_warehouse: USER_WH
  must_change_password: false
  network_policy: OFFICE_NETWORK_POLICY
  comment: "Description of user purpose"
```

### Service Account with RSA
```yaml
# Service account (no password)
SERVICE_NAME:
  type: SERVICE
  default_role: SERVICE_ROLE
  default_warehouse: SERVICE_WH
  rsa_public_key: |
    -----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...
    -----END PUBLIC KEY-----
  comment: "Service account for X integration"
```

### Role with Grants
```yaml
ROLE_NAME:
  comment: "Role description"
  grants:
    - database: DATABASE_NAME
      privileges: [USAGE]
    - schema: DATABASE_NAME.SCHEMA_NAME
      privileges: [USAGE, SELECT]
    - warehouse: WAREHOUSE_NAME
      privileges: [USAGE]
```

### Network Policy
```yaml
POLICY_NAME:
  allowed_ip_list:
    - "10.0.0.0/8"
    - "192.168.1.0/24"
  blocked_ip_list: []
  comment: "Office network access only"
```

## Naming Conventions

### Files
- Scripts: `snake_case.py` (e.g., `manage_users.py`)
- YAML configs: `snake_case.yaml` (e.g., `network_policy.yaml`)
- Documentation: `UPPER_CASE.md` (e.g., `QUICKSTART.md`)

### Snowflake Objects
- Users: `UPPERCASE` (e.g., `ANALYST_USER`)
- Roles: `UPPERCASE_ROLE` (e.g., `ANALYST_ROLE`)
- Warehouses: `UPPERCASE_WH` (e.g., `COMPUTE_WH`)
- Databases: `UPPERCASE` (e.g., `RAW`, `ANALYTICS`)

### Python
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

## Error Handling Pattern

```python
import sys
from typing import Optional


class SnowTowerError(Exception):
    """Base exception for SnowTower errors."""
    pass


class ConfigurationError(SnowTowerError):
    """Configuration-related errors."""
    pass


def safe_operation(func):
    """Decorator for safe operation execution."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SnowTowerError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(2)
    return wrapper
```

## Testing Patterns

### Unit Test
```python
import pytest
from scripts.my_script import my_function


def test_my_function_success():
    result = my_function("valid_input")
    assert result == expected_output


def test_my_function_error():
    with pytest.raises(ValueError):
        my_function("invalid_input")
```

### Integration Test
```python
import pytest
from unittest.mock import patch


@pytest.fixture
def mock_snowflake():
    with patch("src.snowddl_core.SnowDDLClient") as mock:
        yield mock


def test_integration(mock_snowflake):
    mock_snowflake.return_value.execute.return_value = []
    # Test implementation
```

## SnowDDL Role Hierarchy Patterns

### Role Types and Naming

SnowDDL automatically creates roles with specific suffixes:

| Role Type | Suffix | Purpose | Example |
|-----------|--------|---------|---------|
| User Role | `__U_ROLE` | Per-user role | `DLT__U_ROLE` |
| Technical Role | `__T_ROLE` | Service/app permissions | `DLT_STRIPE_TECH_ROLE__T_ROLE` |
| Business Role | `__B_ROLE` | Logical groupings | `DLT_STRIPE_ROLE__B_ROLE` |
| Schema Owner | `__S_ROLE` | Object ownership | `SOURCE_STRIPE__STRIPE_WHY__OWNER__S_ROLE` |
| Database Owner | `__D_ROLE` | Database-level ownership | `SOURCE_STRIPE__OWNER__D_ROLE` |

### Role Inheritance Hierarchy

```
User Role (DLT__U_ROLE)
    ├── Business Role (DLT_STRIPE_ROLE__B_ROLE)
    │       ├── Technical Role (DLT_STRIPE_TECH_ROLE__T_ROLE)
    │       └── Schema Owner Role (SOURCE_STRIPE__STRIPE_WHY__OWNER__S_ROLE)
    │
    └── Technical Role (directly granted if needed)
```

**Key insight**: Business roles INHERIT from technical roles AND can have schema_owner.
This means permissions flow: User → Business → Technical + Schema Owner.

## Data Loading (DLT) Permission Patterns

### The Table Stage Problem

When DLT loads data, it uses Snowflake's `COPY INTO` with table stages:

```sql
COPY INTO my_table FROM @my_table  -- @table_name is the table stage
```

**Critical requirement**: Only the TABLE OWNER can access table stages.

If DLT doesn't own the tables (common with SnowDDL's default SCHEMA_OWNER permission model),
loading fails with:

```
SQL access control error: Insufficient privileges to operate on table stage 'CHARGE'
```

### Solution: Grant Schema Owner Role to Business Role

SnowDDL's `schema_owner` property on business roles is the correct solution:

```yaml
# snowddl/business_role.yaml
DLT_STRIPE_ROLE:
  comment: DLT Stripe pipeline - includes schema owner for table stage access
  tech_roles:
    - DLT_STRIPE_TECH_ROLE
  schema_owner:
    - SOURCE_STRIPE.STRIPE_WHY  # Grants SOURCE_STRIPE__STRIPE_WHY__OWNER__S_ROLE
  warehouse_usage:
    - DLT
```

**Why this works**:
1. `schema_owner` grants the auto-created `SOURCE_STRIPE__STRIPE_WHY__OWNER__S_ROLE` to the business role
2. The user's role inherits from the business role (DLT__U_ROLE → DLT_STRIPE_ROLE__B_ROLE)
3. Therefore, the DLT user can access table stages through this inheritance chain

### What Doesn't Work (and Why)

**Technical roles don't support `schema_owner`:**
```yaml
# tech_role.yaml - This WON'T work!
DLT_STRIPE_TECH_ROLE:
  schema_owner:  # NOT SUPPORTED in tech_role.yaml
    - SOURCE_STRIPE.STRIPE_WHY
```

SnowDDL's schema only allows: `grants`, `future_grants`, `account_grants`, `comment`

**Role grants in technical roles don't work:**
```yaml
# tech_role.yaml - This ALSO won't work!
DLT_STRIPE_TECH_ROLE:
  grants:
    ROLE:  # NOT a valid object type for grants
      - SOURCE_STRIPE__STRIPE_WHY__OWNER__S_ROLE
```

Grant keys must be `OBJECT_TYPE:PRIVILEGE`, not just `ROLE`.

### Complete DLT Permission Configuration

**Technical Role** (`tech_role.yaml`):
```yaml
DLT_STRIPE_TECH_ROLE:
  comment: DLT Stripe pipeline permissions
  future_grants:
    FILE_FORMAT:USAGE:
      - SOURCE_STRIPE
    SEQUENCE:USAGE:
      - SOURCE_STRIPE
    STAGE:USAGE,READ,WRITE:
      - SOURCE_STRIPE
    TABLE:SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES:
      - SOURCE_STRIPE
    VIEW:SELECT:
      - SOURCE_STRIPE
  grants:
    DATABASE:USAGE,CREATE SCHEMA,MONITOR,MODIFY:
      - SOURCE_STRIPE
    SCHEMA:USAGE,MODIFY,MONITOR,CREATE TABLE,CREATE VIEW,CREATE FILE FORMAT,CREATE STAGE,CREATE SEQUENCE:
      - SOURCE_STRIPE.STRIPE_WHY
    WAREHOUSE:USAGE,MONITOR,OPERATE:
      - DLT
```

**Business Role** (`business_role.yaml`):
```yaml
DLT_STRIPE_ROLE:
  comment: DLT Stripe pipeline with schema owner access for table stages
  tech_roles:
    - DLT_STRIPE_TECH_ROLE
  schema_owner:
    - SOURCE_STRIPE.STRIPE_WHY  # CRITICAL for table stage access
  warehouse_usage:
    - DLT
```

### Verifying the Configuration

**Check role grants:**
```bash
snow sql --query "SHOW GRANTS OF ROLE SOURCE_STRIPE__STRIPE_WHY__OWNER__S_ROLE"
# Should show: granted to DLT_STRIPE_ROLE__B_ROLE
```

**Check table ownership:**
```bash
snow sql --query "SELECT TABLE_NAME, TABLE_OWNER FROM SOURCE_STRIPE.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'STRIPE_WHY'"
# Should show: TABLE_OWNER = SOURCE_STRIPE__STRIPE_WHY__OWNER__S_ROLE
```

**Check user inheritance:**
```bash
snow sql --query "SHOW GRANTS TO USER DLT"
# Should include: DLT_STRIPE_TECH_ROLE__T_ROLE
# User role should inherit from business role which has schema_owner
```

## Permission Model Patterns

### One-Time Ownership Migration for Existing Schemas

When adding `schema_owner` to a business role for a schema that already has objects,
existing objects need a one-time ownership transfer. SnowDDL only grants future ownership,
not retroactive ownership.

**Problem**: DBT or other tools create objects BEFORE schema_owner is configured.
These objects remain owned by the original creator (often ACCOUNTADMIN).

**Symptom**: After adding `schema_owner` and running SnowDDL apply:
```
SQL access control error: Insufficient privileges to operate on table 'MY_TABLE'
SQL access control error: View 'MY_VIEW' already exists, but current role has no privileges
```

**Solution**: One-time ownership transfer after SnowDDL creates the schema owner role:

```sql
-- Transfer table ownership
GRANT OWNERSHIP ON ALL TABLES IN SCHEMA DB_NAME.SCHEMA_NAME
  TO ROLE DB_NAME__SCHEMA_NAME__OWNER__S_ROLE COPY CURRENT GRANTS;

-- Transfer view ownership
GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA DB_NAME.SCHEMA_NAME
  TO ROLE DB_NAME__SCHEMA_NAME__OWNER__S_ROLE COPY CURRENT GRANTS;

-- If needed: procedures, functions, etc.
GRANT OWNERSHIP ON ALL PROCEDURES IN SCHEMA DB_NAME.SCHEMA_NAME
  TO ROLE DB_NAME__SCHEMA_NAME__OWNER__S_ROLE COPY CURRENT GRANTS;
```

**Real example** (PROJ_STRIPE.PROJ_STRIPE for DBT):
```sql
GRANT OWNERSHIP ON ALL TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
  TO ROLE PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE COPY CURRENT GRANTS;

GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
  TO ROLE PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE COPY CURRENT GRANTS;
```

**After migration**: Future objects are automatically owned by the schema owner role
through SnowDDL's future ownership grants.

### Default SCHEMA_OWNER Model

The default SnowDDL permission model creates schema owner roles with future OWNERSHIP grants:

```
When a table is created in SOURCE_STRIPE.STRIPE_WHY:
1. Creator initially owns it
2. Future ownership grant transfers ownership to SOURCE_STRIPE__STRIPE_WHY__OWNER__S_ROLE
3. Original creator loses table stage access
```

**Impact on data loaders**: DLT creates tables, but loses ownership, so it can't load data.

**Solution**: Grant the schema owner role to DLT's business role (see above).

### Alternative: Custom Permission Model (Not Recommended)

You CAN create a custom permission model that doesn't transfer ownership:

```yaml
# snowddl/permission_model.yaml
dlt_loader:
  ruleset: SCHEMA_OWNER
  owner_future_grants:
    TABLE: [SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES]  # No OWNERSHIP!
```

**Why this isn't recommended**:
1. Mixed ownership creates complexity
2. SnowDDL prefers consistent ownership patterns
3. The schema_owner solution on business roles is cleaner

## Separating Read vs Write Access

### Pattern: Source Database Read-Only for Transformers

```yaml
# tech_role.yaml
DBT_STRIPE_ROLE:
  comment: dbt role - READ-ONLY access to source, WRITE to project
  future_grants:
    TABLE:SELECT:
      - SOURCE_STRIPE  # Read-only
    TABLE:SELECT,INSERT,UPDATE,DELETE,TRUNCATE:
      - PROJ_STRIPE    # Full write
  grants:
    SCHEMA:USAGE:
      - SOURCE_STRIPE.STRIPE_WHY  # Just USAGE, no CREATE
    SCHEMA:USAGE,MODIFY,CREATE TABLE,CREATE VIEW:
      - PROJ_STRIPE.PROJ_STRIPE   # Full write
```

**Key principle**: Loaders write to SOURCE_*, transformers write to PROJ_*.

## Git Patterns

### Commit Messages
```
type: short description

Longer description if needed.

Types: feat, fix, docs, refactor, test, chore
```

### Branch Names
```
feature/description
fix/issue-description
docs/what-changed
```
