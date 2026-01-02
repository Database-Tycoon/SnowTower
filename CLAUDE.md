# CLAUDE.md - SnowTower SnowDDL

> Enterprise Snowflake infrastructure management with Infrastructure as Code

## Quick Reference

```bash
# Essential commands
uv run snowddl-plan      # Preview infrastructure changes
uv run snowddl-apply     # Apply changes (needs confirmation)
uv run manage-users      # User management
uv run manage-warehouses # Warehouse management
uv run manage-costs      # Cost analysis
uv sync                  # Install dependencies
```

## Critical Rules

1. **Always use UV**: `uv run`, `uv sync`, `uv add` - never pip
2. **Plan before apply**: Always run `snowddl-plan` first
3. **Load dotenv**: Every script must call `load_dotenv()` first
4. **Confirm destructive actions**: Never auto-apply infrastructure changes
5. **Tests must pass before release**: Run `uv run pytest` and resolve all failures before any release

## Release Requirements

**Before any release (v0.1, v1.0, etc.):**
1. Run full test suite: `uv run pytest`
2. All tests must pass OR failures must be explicitly discussed and documented
3. No release should proceed with unresolved test failures
4. Document any known issues in release notes

See [Release Checklist](docs/releases/RELEASE_CHECKLIST.md) for full pre-release verification steps.

## Project Structure

```
snowtower-snowddl/
├── snowddl/           # YAML infrastructure definitions
├── src/               # Python source
│   ├── snowddl_core/  # OOP framework
│   └── management_cli.py  # CLI entry points
├── scripts/           # Management scripts
├── docs/              # Documentation
│   ├── guide/         # User guides
│   ├── contributing/  # Developer docs
│   ├── llm-context/   # LLM configuration
│   └── ...
└── pyproject.toml     # UV/Python config
```

## Creating New Commands

1. Create script in `scripts/my_script.py`:
```python
from dotenv import load_dotenv
load_dotenv()  # MUST BE FIRST

import argparse
def main():
    parser = argparse.ArgumentParser()
    # ... implementation
```

2. Add wrapper in `src/management_cli.py`:
```python
def my_command():
    from scripts.my_script import main
    main()
```

3. Register in `pyproject.toml`:
```toml
[project.scripts]
my-command = "src.management_cli:my_command"
```

4. Test: `uv sync && uv run my-command --help`

## Key Files

| File | Purpose |
|------|---------|
| `snowddl/*.yaml` | Infrastructure definitions |
| `src/management_cli.py` | CLI entry points |
| `pyproject.toml` | Dependencies and commands |
| `.env` | Environment variables (not in git) |

## SnowDDL Knowledge Base

### CLI Parameters

**Critical: `--env-prefix` is NOT for environment variables!**

```bash
# WRONG - This prefixes all OBJECT NAMES with "SNOWFLAKE__"
snowddl --env-prefix SNOWFLAKE plan  # Looks for SNOWFLAKE__MY_DATABASE, etc.

# RIGHT - Just use environment variables directly
snowddl -c snowddl -r ACCOUNTADMIN plan  # Uses SNOWFLAKE_* env vars for connection
```

The `--env-prefix` parameter adds a prefix to all object names (databases, schemas, roles, warehouses) for environment separation (DEV, PROD). It does NOT control environment variable naming.

**Must use `-r ACCOUNTADMIN`** to see all grants across roles/schemas when running plan.

### Schema Grants in SnowDDL

Schema grants are defined in `tech_role.yaml` using `SCHEMA:<privilege>` format:

```yaml
# tech_role.yaml
DBT_STRIPE_ROLE:
  grants:
    # Schema-level grants (the key insight!)
    SCHEMA:USAGE:
      - SOURCE_STRIPE.STRIPE_WHY
      - PROJ_STRIPE.PROJ_STRIPE
    SCHEMA:CREATE TABLE,CREATE VIEW,MODIFY:
      - PROJ_STRIPE.PROJ_STRIPE
    # Database grants
    DATABASE:USAGE,CREATE SCHEMA:
      - SOURCE_STRIPE
      - PROJ_STRIPE
```

**Grant format**: `<OBJECT_TYPE>:<PRIVILEGE1,PRIVILEGE2>` with list of fully-qualified names.

### Understanding Plan Output

When `snowddl-plan` shows REVOKE statements, it means:
- Grants exist in Snowflake that aren't defined in YAML
- SnowDDL wants to remove them to match the declared state

Common causes of REVOKE drift:
1. **Schema grants applied by dbt** - dbt creates schemas and grants permissions
2. **Manual grants** - Someone ran GRANT commands directly
3. **Missing YAML definitions** - Grants exist but aren't in tech_role.yaml

**To fix**: Add the missing grants to `tech_role.yaml` using the appropriate format.

### Schema Drift Problem

The "schema drift" issue occurs when:
1. dbt or other tools create/modify schemas with grants
2. Those grants aren't tracked in SnowDDL YAML
3. Every plan shows 100s of REVOKE statements

**Solution path**:
1. Run `uv run snowddl-plan` to see all REVOKEs
2. Parse the REVOKE statements to identify missing grants
3. Add `SCHEMA:<privilege>` grants to `tech_role.yaml`
4. Re-run plan to verify drift is eliminated

### SnowDDL Documentation

- [Schema Config](https://docs.snowddl.com/basic/yaml-configs/schema) - Schema params.yaml structure
- [Technical Roles](https://docs.snowddl.com/basic/yaml-configs/technical-role) - Grant definitions
- [Business Roles](https://docs.snowddl.com/basic/yaml-configs/business-role) - schema_read/write abstractions
- [Env Prefix Guide](https://docs.snowddl.com/guides/other-guides/env-prefix) - Environment separation

## Setting Up dbt Projects (CRITICAL)

**Every dbt project requires this 3-step setup.** Without it, dbt will fail with permission errors.

### The Problem

dbt needs to CREATE, ALTER, and DROP tables/views. SnowDDL's schema owner roles have these permissions,
but dbt must inherit that role AND existing objects must be owned by that role.

### Step 1: Add schema_owner to Business Role

In `snowddl/business_role.yaml`, add `schema_owner` for your dbt target schema:

```yaml
DBT_ANALYTICS_ROLE:
  comment: Business role for dbt - includes schema owner for table/view modification
  tech_roles:
    - DBT_STRIPE_ROLE  # Your technical role with SELECT grants
  schema_owner:
    - PROJ_STRIPE.PROJ_STRIPE  # CRITICAL: Grants the schema owner role
  warehouse_usage:
    - TRANSFORMING
```

### Step 2: Deploy with SnowDDL

```bash
uv run snowddl-plan   # Verify: should show GRANT ROLE "...__OWNER__S_ROLE" TO ROLE "...__B_ROLE"
uv run deploy-safe    # Apply the changes
```

### Step 3: Transfer Ownership of Existing Objects (One-Time)

**This is required if objects already exist in the schema.** SnowDDL only sets up FUTURE ownership grants.

```sql
-- Run these as ACCOUNTADMIN
GRANT OWNERSHIP ON ALL TABLES IN SCHEMA <DB>.<SCHEMA>
  TO ROLE <DB>__<SCHEMA>__OWNER__S_ROLE COPY CURRENT GRANTS;

GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA <DB>.<SCHEMA>
  TO ROLE <DB>__<SCHEMA>__OWNER__S_ROLE COPY CURRENT GRANTS;
```

**Real example for PROJ_STRIPE.PROJ_STRIPE:**
```sql
GRANT OWNERSHIP ON ALL TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
  TO ROLE PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE COPY CURRENT GRANTS;

GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
  TO ROLE PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE COPY CURRENT GRANTS;
```

### Why This Works

The grant chain after setup:
```
dbt service user (e.g., DBT_SERVICE)
  → User role (DBT_PROD__U_ROLE)
    → Business role (DBT_ANALYTICS_ROLE__B_ROLE)
      → Schema owner role (PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE)
        → OWNS all tables/views in schema
```

### Common Errors Without This Setup

```
SQL access control error: Insufficient privileges to operate on table 'DATE_SPINE'
SQL access control error: View 'MY_VIEW' already exists, but current role has no privileges
```

**Fix:** Complete all 3 steps above.

## For More Details

- [Full LLM Instructions](docs/llm-context/CLAUDE.md)
- [Project Context](docs/llm-context/CONTEXT.md)
- [Code Patterns](docs/llm-context/PATTERNS.md)
- [CLI Reference](docs/guide/MANAGEMENT_COMMANDS.md)
