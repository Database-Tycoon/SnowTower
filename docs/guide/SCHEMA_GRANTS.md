# Schema Grants Management

## Overview

SnowDDL deliberately excludes SCHEMA objects from management to avoid conflicts with tools like dbt that create their own schemas. This means schema-level grants must be managed separately.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `uv run deploy-safe` | **Recommended** - Deploys SnowDDL + applies schema grants |
| `uv run apply-schema-grants` | Apply schema grants only |
| `uv run validate-schema-grants` | Validate schema grant configuration |

## The Problem

When you grant permissions on a database, those permissions don't automatically cascade to schemas within that database. You need explicit schema grants for:

- `USAGE` - Access to schema
- `CREATE TABLE` - Create tables in schema
- `CREATE VIEW` - Create views in schema
- `SELECT` - Read from all tables/views in schema

---

## dbt Project Setup (CRITICAL - Read This First!)

**Every dbt project writing to Snowflake requires a 3-step setup.** This is not optional - without it, dbt will fail with permission errors like:

```
SQL access control error: Insufficient privileges to operate on table 'DATE_SPINE'
SQL access control error: View 'MY_VIEW' already exists, but current role has no privileges
```

### Why dbt Needs Special Setup

dbt doesn't just SELECT data - it needs to:
- CREATE new tables and views
- ALTER existing tables (for incremental models)
- DROP and recreate views
- REPLACE existing objects

Standard SnowDDL grants (SELECT, INSERT, UPDATE, DELETE) are **not sufficient**. dbt needs **OWNERSHIP** of the objects it manages.

### The 3-Step Solution

#### Step 1: Add schema_owner to Business Role

In `snowddl/business_role.yaml`, add the `schema_owner` property:

```yaml
DBT_ANALYTICS_ROLE:
  comment: Business role for dbt - includes schema owner for table/view modification
  tech_roles:
    - DBT_STRIPE_ROLE  # Your technical role with SELECT grants on source data
  schema_owner:
    - PROJ_STRIPE.PROJ_STRIPE  # CRITICAL: Grants the schema owner role
  warehouse_usage:
    - TRANSFORMING
```

**What this does:** Grants the auto-created `PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE` to the business role. This role OWNS all objects in the schema.

#### Step 2: Deploy with SnowDDL

```bash
# Preview the changes - look for the schema owner grant
uv run snowddl-plan

# You should see something like:
# GRANT ROLE "PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE" TO ROLE "DBT_ANALYTICS_ROLE__B_ROLE"

# Apply the changes
uv run deploy-safe
```

#### Step 3: Transfer Ownership of Existing Objects (One-Time Migration)

**This step is required if objects already exist in the schema.**

SnowDDL only sets up FUTURE ownership grants. Existing objects remain owned by whoever created them (often ACCOUNTADMIN). You must transfer ownership once:

```sql
-- Run these as ACCOUNTADMIN in Snowflake

-- Transfer table ownership
GRANT OWNERSHIP ON ALL TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
  TO ROLE PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE COPY CURRENT GRANTS;

-- Transfer view ownership
GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
  TO ROLE PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE COPY CURRENT GRANTS;

-- If you have procedures
GRANT OWNERSHIP ON ALL PROCEDURES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE
  TO ROLE PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE COPY CURRENT GRANTS;
```

**Generic template:**
```sql
GRANT OWNERSHIP ON ALL TABLES IN SCHEMA <DATABASE>.<SCHEMA>
  TO ROLE <DATABASE>__<SCHEMA>__OWNER__S_ROLE COPY CURRENT GRANTS;

GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA <DATABASE>.<SCHEMA>
  TO ROLE <DATABASE>__<SCHEMA>__OWNER__S_ROLE COPY CURRENT GRANTS;
```

### Verifying the Setup

```bash
# Check the grant chain exists
snow sql --query "SHOW GRANTS TO ROLE DBT_ANALYTICS_ROLE__B_ROLE" | grep OWNER

# Should show: PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE

# Check object ownership
snow sql --query "SELECT TABLE_NAME, TABLE_OWNER FROM PROJ_STRIPE.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'PROJ_STRIPE'"

# All objects should be owned by: PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE
```

### The Complete Grant Chain

After setup, permissions flow like this:

```
dbt service user (e.g., DBT_SERVICE)
  └── User role (DBT_PROD__U_ROLE)
        └── Business role (DBT_ANALYTICS_ROLE__B_ROLE)
              ├── Technical role (DBT_STRIPE_ROLE__T_ROLE) - SELECT on source data
              └── Schema owner role (PROJ_STRIPE__PROJ_STRIPE__OWNER__S_ROLE)
                    └── OWNS all tables/views in PROJ_STRIPE.PROJ_STRIPE
```

### Setting Up a New dbt Project Checklist

- [ ] Create technical role in `tech_role.yaml` with SELECT grants on source schemas
- [ ] Create business role in `business_role.yaml` with:
  - [ ] `tech_roles` pointing to your technical role
  - [ ] `schema_owner` pointing to your target schema (e.g., `PROJ_STRIPE.PROJ_STRIPE`)
  - [ ] `warehouse_usage` for your compute warehouse
- [ ] Create the dbt service user in `user.yaml` with the business role as default
- [ ] Run `uv run snowddl-plan` and verify the OWNER__S_ROLE grant appears
- [ ] Run `uv run deploy-safe` to apply changes
- [ ] If schema has existing objects, run ownership transfer SQL (Step 3 above)
- [ ] Test dbt run in CI/CD

---

## Solution: Schema Grant Configuration

### Configuration File

Create `snowddl/schema_grants.yaml`:

```yaml
schema_grants:
  - database: RAW
    schema: PUBLIC
    roles:
      - role: DBT_ROLE
        privileges: [USAGE, CREATE TABLE, CREATE VIEW]
      - role: ANALYST_ROLE
        privileges: [USAGE, SELECT]

  - database: ANALYTICS
    schema: MARTS
    roles:
      - role: ANALYST_ROLE
        privileges: [USAGE, SELECT]
```

### Applying Schema Grants

```bash
# Validate configuration first
uv run validate-schema-grants

# Apply schema grants
uv run apply-schema-grants

# Or use the combined safe deployment
uv run deploy-safe
```

## Best Practices

1. **Always use `deploy-safe`** - This runs SnowDDL first, then applies schema grants
2. **Version control your schema grants** - Keep `schema_grants.yaml` in git
3. **Review before applying** - Use `--dry-run` flag to preview changes
4. **Document grant purposes** - Add comments explaining why each grant exists
5. **For dbt: Use schema_owner** - Don't try to grant individual privileges; use the schema_owner pattern

## Troubleshooting

### "Insufficient privileges to operate on table"

**Cause:** dbt doesn't have ownership of existing objects.

**Fix:**
1. Ensure `schema_owner` is set in business role (Step 1 above)
2. Transfer ownership of existing objects (Step 3 above)

### "View already exists, but current role has no privileges"

**Cause:** Same as above - dbt can see the view but doesn't own it.

**Fix:** Transfer ownership with `GRANT OWNERSHIP ON ALL VIEWS...`

### "Insufficient privileges" after SnowDDL deploy

**Cause:** SnowDDL may have reset grants.

**Fix:** Use `uv run deploy-safe` which applies schema grants after SnowDDL.

### Grants not persisting

**Cause:** SnowDDL resets grants on each apply.

**Fix:** Use `deploy-safe` which applies schema grants after SnowDDL.

### dbt can't create objects in a NEW schema

**Cause:** For new schemas without existing objects, you only need Steps 1 and 2. The schema_owner role will automatically own all future objects.

**Fix:** Ensure the schema exists and run `deploy-safe`.
