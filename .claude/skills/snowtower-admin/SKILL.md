---
name: snowtower-admin
description: Advanced skill for SnowTower infrastructure administrators. Use for SnowDDL operations, user provisioning, role management, CI/CD deployments, troubleshooting, and Snowflake administration. Triggers on mentions of snowddl, deploy, user creation, role grants, infrastructure changes, or admin operations.
---

# SnowTower Administrator Guide

Assumes CLAUDE.md is loaded for project context, role hierarchy, and SnowDDL knowledge.

## Deployment Checklist

```bash
# 1. Edit YAML files in snowddl/
# 2. ALWAYS preview first
uv run snowddl-plan
# 3. Review output for unexpected DROP/REVOKE statements
# 4. Apply using safe deployment (preserves schema grants)
uv run deploy-safe
```

**Why `deploy-safe`?** Raw `snowddl-apply` can revoke schema-level grants managed by dbt. The wrapper restores them automatically.

**Plan output flags:**
- `CREATE` / `ALTER` - normally expected
- `DROP` - verify this is intentional
- Mass `REVOKE` - likely schema drift (see CLAUDE.md "Schema Drift Problem")
- Changes to ACCOUNTADMIN/SECURITYADMIN - red flag

## User Creation

**Option 1: Interactive wizard** (recommended)
```bash
uv run manage-users create
```

**Option 2: Edit YAML directly** in `snowddl/user.yaml`

**Option 3: Non-interactive**
```bash
uv run manage-users create --first-name Jane --last-name Smith --email jane@company.com --role ANALYST_ROLE
```

**Encrypt passwords:**
```bash
uv run snowddl-encrypt "MySecurePassword123!"
# Use output in YAML with !decrypt tag
```

**For service accounts:** See [Service Account Pattern](../../.claude/patterns/SERVICE_ACCOUNT_CREATION_PATTERN.md)

## Role Management

**Business Role** (`snowddl/business_role.yaml`):
```yaml
ANALYST_ROLE:
  comment: "Business analysts with read access"
  tech_roles:
    - STRIPE_READER_ROLE
  warehouse_usage:
    - MAIN_WAREHOUSE
  schema_read:
    - PROJ_STRIPE.ANALYTICS
```

**Technical Role** (`snowddl/tech_role.yaml`): See grant format in CLAUDE.md "SnowDDL Object Type Reference".

## Troubleshooting Quick Fixes

| Problem | Fix |
|---------|-----|
| Schema grant drift (mass REVOKEs) | Use `uv run deploy-safe` instead of raw apply |
| "Object does not exist" | Ensure using `-r ACCOUNTADMIN` |
| "Insufficient privileges" | Check `SNOWFLAKE_ROLE=ACCOUNTADMIN` in `.env` |
| Exit code 8 | Not an error - means changes were applied |
| User locked out | `ALTER USER USERNAME SET MINS_TO_UNLOCK = 0;` |

## Emergency Procedures

**Rollback last deployment:**
```bash
git checkout HEAD~1 -- snowddl/
uv run deploy-safe
```

**Service account reset:**
```bash
uv run generate-rsa-batch --users SNOWDDL --force
snow sql -q "ALTER USER SNOWDDL SET RSA_PUBLIC_KEY='...'"
gh secret set SNOWFLAKE_PRIVATE_KEY < new_key.p8
```

**MFA compliance check:**
```bash
uv run manage-security --check-mfa
```

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | PRs, pushes | Lint + test validation |
| `release.yml` | Tags `v*` | Create GitHub release |
| `labeler.yml` | PRs | Auto-label by file type |
| `changelog.yml` | Push to main | Update changelog |
