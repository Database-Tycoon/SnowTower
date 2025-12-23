# SnowDDL Management Commands Reference

**Updated for consolidated command structure** - Commands have been reorganized for better discoverability and consistency.

## 🆕 Quick Discovery

```bash
# NEW: See all available commands organized by category
uv run snowtower
```

## Command Categories

### 🔧 Core SnowDDL Operations

```bash
# Plan infrastructure changes (ALWAYS RUN FIRST!)
uv run snowddl-plan

# Apply infrastructure changes
uv run snowddl-apply

# Validate configuration
uv run snowddl-validate

# Show differences
uv run snowddl-diff

# Lint configuration files
uv run snowddl-lint
```

### 👤 User Management (CONSOLIDATED)

**All user operations now use `manage-users` command:**

```bash
# Interactive user creation (recommended)
uv run manage-users create

# Non-interactive user creation
uv run manage-users create --first-name John --last-name Doe --email john@example.com

# List users
uv run manage-users list
uv run manage-users list --format json
uv run manage-users list --user-type PERSON

# Show user details
uv run manage-users show USERNAME

# Update user
uv run manage-users update USERNAME --email new@email.com
uv run manage-users update USERNAME --default-role NEW_ROLE

# Delete user
uv run manage-users delete USERNAME
uv run manage-users delete USERNAME --force

# Validate configuration
uv run manage-users validate USERNAME
uv run manage-users validate-all

# Password operations
uv run manage-users generate-password USERNAME
uv run manage-users regenerate-password USERNAME
uv run manage-users encrypt-password

# RSA key operations
uv run manage-users generate-keys USERNAME
uv run manage-users rotate-keys USERNAME
uv run manage-users list-keys

# Bulk operations
uv run manage-users bulk-generate-passwords --usernames "USER1,USER2"
uv run manage-users import-csv users.csv

# Service account management
uv run manage-users snowddl-account test
uv run manage-users snowddl-account status
uv run manage-users snowddl-account permissions

# Configuration backup
uv run manage-users backup --description "Before changes"
```

### 🏢 Resource Management

```bash
# Warehouse Management
uv run manage-warehouses list
uv run manage-warehouses resize X-Small --warehouses DEV_WH,TEST_WH --save
uv run manage-warehouses auto-suspend 60 --save
uv run manage-warehouses assign-monitor DEV_MONITOR --warehouses DEV_WH --save
uv run manage-warehouses optimize          # Show recommendations
uv run manage-warehouses optimize --apply   # Apply optimizations

# Schema-Level Grants (SnowDDL Workaround)
uv run apply-schema-grants
# Applies schema-level USAGE grants that SnowDDL cannot manage
# See docs/SCHEMA_GRANTS_WORKAROUND.md for details

# Cost Optimization
uv run manage-costs analyze
uv run manage-costs apply --mode balanced    # balanced/aggressive/conservative
uv run manage-costs estimate

# Security Auditing
uv run manage-security full
uv run manage-security auth
uv run manage-security mfa
uv run manage-security sacred
uv run manage-security roles

# Backup & Restore
uv run manage-backup create
uv run manage-backup create --description "Before major changes"
uv run manage-backup list
uv run manage-backup restore 20240923_143022
uv run manage-backup compare 20240923_143022
uv run manage-backup cleanup
uv run manage-backup cleanup --days 7
```

### 📊 Monitoring & Observability

```bash
# System health checks
uv run monitor-health

# Audit trail analysis
uv run monitor-audit

# Operational metrics
uv run monitor-metrics
```

### 🌐 Web Interface

```bash
# Launch administrative dashboard
uv run web
# Opens at http://localhost:8501

# Deploy Streamlit apps to Snowflake
uv run deploy-streamlit
```

### 🔑 Utilities

```bash
# Generate Fernet encryption key
uv run util-generate-key

# Diagnose authentication issues
uv run util-diagnose-auth

# Fix authentication problems
uv run util-fix-auth
```

### 📚 Documentation

```bash
# Serve documentation locally
uv run docs-serve

# Build documentation
uv run docs-build
```

### 🤖 Automation

```bash
# Process GitHub issue for user access requests
uv run process-access-request

# Convert GitHub issue to SnowDDL PR
uv run github-to-snowddl
```

## Common Workflows

### Daily Operations
```bash
# Morning health check
uv run monitor-health
uv run manage-costs analyze
uv run manage-users list
```

### After SnowDDL Deployment
```bash
# 1. Plan and review changes
uv run snowddl-plan

# 2. Apply infrastructure changes
uv run snowddl-apply

# 3. Apply schema grants (SnowDDL doesn't manage these)
uv run apply-schema-grants

# 4. Verify (will show REVOKE drift, but that's expected - see docs/SCHEMA_GRANTS_WORKAROUND.md)
uv run snowddl-plan
```

### Security Compliance Check
```bash
uv run manage-security full
uv run manage-security mfa
```

### Before Major Changes
```bash
uv run manage-backup create --description "Before Q3 updates"
# Make your changes...
# If something goes wrong:
uv run manage-backup restore <backup_id>
```

### New User Onboarding (Recommended Workflow)
```bash
# Option 1: Interactive mode (easiest, recommended)
uv run manage-users create
# Follow the prompts to create user with password + RSA keys

# Option 2: Non-interactive mode
uv run manage-users create --first-name Jane --last-name Smith --email jane.smith@company.com
# Auto-generates secure password and RSA keys

# Then deploy the changes
uv run snowddl-plan
uv run snowddl-apply

# Verify user creation
uv run manage-users list
uv run manage-users show JANE_SMITH
```

### Monthly Optimization
```bash
# Analyze opportunities
uv run manage-costs analyze

# Review and apply
uv run manage-costs apply --mode balanced

# Clean up old backups
uv run manage-backup cleanup
```

### Granting Schema Access to Users
```bash
# 1. Create schema configuration (if doesn't exist)
# Edit snowddl/{DATABASE}/schema.yaml to add grants

# 2. Apply the schema grants
uv run apply-schema-grants

# 3. Verify access works for users
# Users should now be able to access the schema

# Note: SnowDDL will show these grants as drift (REVOKE statements)
# This is expected - see docs/SCHEMA_GRANTS_WORKAROUND.md
```

## ⚠️ Deprecated Commands

The following commands are deprecated and will be removed in a future version. They will show a warning and redirect to the new commands:

| Deprecated Command | New Command | Status |
|-------------------|-------------|--------|
| `uv run user-create` | `uv run manage-users create` | Shows warning + redirects |
| `uv run user-manage` | `uv run manage-users` | Shows warning + redirects |
| `uv run user-account` | `uv run manage-users snowddl-account` | Shows warning |
| `uv run users` | `uv run manage-users` | Shows warning |
| `uv run health-check` | `uv run monitor-health` | Shows warning |
| `uv run generate-passwords` | `uv run manage-users bulk-generate-passwords` | Shows warning |
| `uv run generate-user-password` | `uv run manage-users generate-password` | Shows warning |

**Migration is simple:** Just replace the old command with the new one. The functionality is identical.

## Environment Setup

All commands automatically load environment variables from `.env` file for:
- Fernet encryption key (for password management)
- Snowflake connection parameters
- Other configuration settings

Make sure your `.env` file is properly configured before running commands.

## Safety Features

- All modification commands require `--save` flag to persist changes
- Automatic checkpoint creation before changes
- Bootstrap mode for initial infrastructure setup
- Protected service account safeguards (SNOWDDL)

## Getting Help

Each command supports `--help` for detailed options:
```bash
uv run manage-warehouses --help
uv run manage-costs apply --help
uv run manage-users create --help
uv run snowddl-plan --help
uv run util-diagnose-auth --help
```

## 💡 Pro Tips

1. **Always plan before apply:**
   ```bash
   uv run snowddl-plan  # Review changes carefully
   uv run snowddl-apply  # Only if plan looks good
   ```

2. **Use the help command for discovery:**
   ```bash
   uv run snowtower  # See all commands organized by category
   ```

3. **Consolidate user operations:**
   ```bash
   # All user operations now under one command
   uv run manage-users <subcommand>
   ```

4. **Check health regularly:**
   ```bash
   uv run monitor-health  # Quick system check
   ```

5. **Backup before major changes:**
   ```bash
   uv run manage-backup create --description "Before major refactor"
   ```

## 🚀 Quick Start for New Users

```bash
# 1. Discover available commands
uv run snowtower

# 2. Check system health
uv run monitor-health

# 3. List existing users
uv run manage-users list

# 4. Preview infrastructure
uv run snowddl-plan

# 5. Launch web interface
uv run web
```

---

**Need more help?** Check out the full documentation in the `docs/` directory or run any command with `--help`.
