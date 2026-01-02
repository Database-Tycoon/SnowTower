# CLAUDE.md - SnowTower SnowDDL Project Instructions

## Project Overview

**SnowTower SnowDDL** is an enterprise Snowflake infrastructure management platform using Infrastructure as Code (IaC) with SnowDDL.

### What This Project Does
- Manages Snowflake infrastructure via declarative YAML files
- Provides CLI commands for user, warehouse, and cost management
- Includes security policies, network policies, and MFA compliance

## Critical Rules

### Always Do
1. **Use UV for all Python operations**: `uv run <command>`, `uv sync`, `uv add <package>`
2. **Load environment variables**: Every script must start with `load_dotenv()`
3. **Run plan before apply**: Always `uv run snowddl-plan` before `uv run snowddl-apply`
4. **Follow existing patterns**: Check `scripts/` for examples before creating new commands

### Never Do
1. **Never run `snowddl-apply` without user confirmation**
2. **Never commit credentials or secrets**
3. **Never modify `snowddl/*.yaml` without understanding the impact**
4. **Never use pip directly** - always use UV

## Key Commands

```bash
# Infrastructure
uv run snowddl-plan      # Preview changes (ALWAYS RUN FIRST)
uv run snowddl-apply     # Apply changes (REQUIRES CONFIRMATION)
uv run deploy-safe       # Recommended: deploys + applies schema grants

# User Management
uv run manage-users      # Full user management CLI

# Operations
uv run manage-warehouses # Warehouse management
uv run manage-costs      # Cost analysis
uv run monitor-health    # System health

# Development
uv sync                  # Install dependencies
uv run pytest           # Run tests
```

## Project Structure

```
snowtower-snowddl/
├── snowddl/                    # Infrastructure definitions (YAML)
│   ├── user.yaml              # User definitions
│   ├── role.yaml              # Role definitions
│   ├── warehouse.yaml         # Warehouse configs
│   ├── network_policy.yaml    # Network policies
│   └── {DATABASE}/            # Database-specific configs
├── src/
│   ├── snowddl_core/          # OOP framework
│   ├── user_management/       # User lifecycle
│   └── management_cli.py      # CLI entry points
├── scripts/                   # Management scripts
├── docs/                      # Documentation
└── pyproject.toml            # UV/Python config
```

## Creating New Commands

Follow this pattern:

### 1. Create Script in `scripts/`

```python
#!/usr/bin/env python3
"""Description of what this script does."""

from dotenv import load_dotenv
load_dotenv()  # MANDATORY - must be first

import argparse
from src.snowddl_core import SnowDDLClient

def main():
    parser = argparse.ArgumentParser(description="Command description")
    parser.add_argument("--option", help="Option description")
    args = parser.parse_args()

    # Implementation here

if __name__ == "__main__":
    main()
```

### 2. Add Wrapper in `src/management_cli.py`

```python
def my_command():
    """Run my command."""
    from scripts.my_script import main
    main()
```

### 3. Register in `pyproject.toml`

```toml
[project.scripts]
my-command = "src.management_cli:my_command"
```

### 4. Test

```bash
uv sync
uv run my-command --help
```

## YAML Configuration Patterns

### User Definition
```yaml
# snowddl/user.yaml
ANALYST_USER:
  type: PERSON
  default_role: ANALYST_ROLE
  default_warehouse: ANALYST_WH
  must_change_password: false
  network_policy: OFFICE_NETWORK_POLICY
```

### Role Definition
```yaml
# snowddl/role.yaml
ANALYST_ROLE:
  comment: "Read-only analyst access"
  grants:
    - database: ANALYTICS
      privileges: [USAGE]
```

### Service Account (RSA Key Auth)
```yaml
# snowddl/user.yaml
DBT_SERVICE:
  type: SERVICE
  default_role: DBT_ROLE
  rsa_public_key: |
    -----BEGIN PUBLIC KEY-----
    MIIBIjANBgk...
    -----END PUBLIC KEY-----
```

## Security Considerations

### Authentication Hierarchy
1. **RSA Key Pairs** - Preferred for all users
2. **Encrypted Passwords** - Fallback only (Fernet encryption)
3. **MFA** - Required for human users by 2026

### Network Policies
- Human users: Restricted to office IP
- Service accounts: Typically unrestricted
- Emergency access: STEPHEN_RECOVERY has no network policy

## Common Tasks

### Add a New User
```bash
uv run manage-users create  # Interactive wizard
uv run snowddl-plan          # Preview
uv run deploy-safe           # Apply (with schema grants)
```

### Check System Health
```bash
uv run monitor-health
uv run manage-costs --analyze
```

### Debug SnowDDL Issues
```bash
uv run snowddl-plan --verbose
# Check snowddl/*.yaml for syntax errors
```

## Environment Variables

Required in `.env`:
```
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password  # Or use RSA key
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
FERNET_KEY=your_fernet_key  # For password encryption
```

## SnowDDL Deep Knowledge

### Critical: Understanding `--env-prefix`

**The `--env-prefix` parameter is NOT for environment variable naming!**

```bash
# WRONG understanding - This does NOT read from SNOWFLAKE_* env vars
snowddl --env-prefix SNOWFLAKE plan

# What it ACTUALLY does - Prefixes all OBJECT NAMES
# It looks for objects like: SNOWFLAKE__MY_DATABASE, SNOWFLAKE__MY_ROLE, etc.
```

The `--env-prefix` adds a prefix to object names for environment separation (DEV__, PROD__, etc.).
SnowDDL reads connection credentials from environment variables automatically (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, etc.) without needing `--env-prefix`.

**Correct usage**:
```bash
# Use -r ACCOUNTADMIN to see all grants when planning
snowddl -c snowddl -r ACCOUNTADMIN plan

# For environment separation (multiple envs on same account)
snowddl -c snowddl --env-prefix DEV plan   # Creates DEV__DATABASE, DEV__ROLE, etc.
```

### Schema Grants in Technical Roles

Schema grants must be defined in `tech_role.yaml` using `SCHEMA:<privilege>` format:

```yaml
# snowddl/tech_role.yaml
DBT_STRIPE_ROLE:
  comment: dbt service role for Stripe transformations
  grants:
    # SCHEMA grants - the key to eliminating drift!
    SCHEMA:USAGE:
      - SOURCE_STRIPE.STRIPE_WHY
      - PROJ_STRIPE.PROJ_STRIPE
    SCHEMA:CREATE TABLE,CREATE VIEW,CREATE PROCEDURE,MODIFY:
      - PROJ_STRIPE.PROJ_STRIPE
    # DATABASE grants
    DATABASE:USAGE,CREATE SCHEMA:
      - SOURCE_STRIPE
      - PROJ_STRIPE
    # WAREHOUSE grants
    WAREHOUSE:USAGE:
      - TRANSFORMING
  future_grants:
    TABLE:SELECT:
      - SOURCE_STRIPE
    TABLE:SELECT,INSERT,UPDATE,DELETE,TRUNCATE:
      - PROJ_STRIPE
```

**Grant format**: `<OBJECT_TYPE>:<PRIVILEGE1,PRIVILEGE2>:` followed by list of fully-qualified object names.

### Understanding Plan Drift (REVOKE Statements)

When `uv run snowddl-plan` shows many REVOKE statements:

```
REVOKE USAGE ON SCHEMA "SOURCE_STRIPE"."STRIPE_WHY" FROM ROLE "BI_WRITER_TECH_ROLE__T_ROLE";
REVOKE ALL ON SCHEMA "PROJ_STRIPE"."PROJ_STRIPE" FROM ROLE "DBT_STRIPE_ROLE__T_ROLE";
```

This means:
1. Grants exist in Snowflake that aren't defined in YAML
2. SnowDDL wants to revoke them to match the declared state
3. These often come from dbt or manual GRANT commands

**Common drift sources**:
- dbt runs that create schemas and grant permissions
- Manual `GRANT` commands run by admins
- Other tools (Lightdash, Omni) that manage their own permissions

**Solution**: Add the missing `SCHEMA:<privilege>` grants to `tech_role.yaml`.

### Eliminating Schema Drift

**Problem**: Every plan shows 100s of REVOKE statements for schema grants.

**Root cause**: dbt and other tools grant schema permissions that aren't tracked in SnowDDL.

**Solution steps**:
1. Run `uv run snowddl-plan` and capture output
2. Parse REVOKE statements to identify:
   - Which roles need grants
   - Which schemas they need access to
   - What privileges they have
3. Add `SCHEMA:<privileges>` entries to appropriate roles in `tech_role.yaml`
4. Re-run plan to verify drift is eliminated

**Example parsing**:
```
REVOKE USAGE ON SCHEMA "SOURCE_STRIPE"."STRIPE_WHY" FROM ROLE "BI_WRITER_TECH_ROLE__T_ROLE"
       ↓              ↓                                    ↓
   Privilege     Schema name                           Role name (without __T_ROLE suffix)
```

Add to `tech_role.yaml`:
```yaml
BI_WRITER_TECH_ROLE:
  grants:
    SCHEMA:USAGE:
      - SOURCE_STRIPE.STRIPE_WHY
```

### SnowDDL Object Type Reference

| Object Type | Grant Key | Example |
|------------|-----------|---------|
| Database | `DATABASE:` | `DATABASE:USAGE,CREATE SCHEMA` |
| Schema | `SCHEMA:` | `SCHEMA:USAGE,CREATE TABLE` |
| Table | `TABLE:` | `TABLE:SELECT,INSERT` |
| View | `VIEW:` | `VIEW:SELECT` |
| Warehouse | `WAREHOUSE:` | `WAREHOUSE:USAGE,OPERATE` |
| Stage | `STAGE:` | `STAGE:USAGE,READ,WRITE` |
| Function | `FUNCTION:` | `FUNCTION:USAGE` |
| Procedure | `PROCEDURE:` | `PROCEDURE:USAGE` |

### SnowDDL Documentation Links

- [Schema Config](https://docs.snowddl.com/basic/yaml-configs/schema)
- [Technical Roles](https://docs.snowddl.com/basic/yaml-configs/technical-role)
- [Business Roles](https://docs.snowddl.com/basic/yaml-configs/business-role)
- [Permission Model](https://docs.snowddl.com/basic/yaml-configs/permission-model)
- [Env Prefix Guide](https://docs.snowddl.com/guides/other-guides/env-prefix)

## Getting Help

- **Troubleshooting**: `docs/guide/TROUBLESHOOTING.md`
- **CLI Reference**: `docs/guide/MANAGEMENT_COMMANDS.md`
- **Architecture**: `docs/guide/ARCHITECTURE.md`
