# SnowTower SnowDDL Manager

**Consolidated Agent:** Replaces snowddl-expert, snowddl-orchestrator, snowddl-config-manager, snowddl-config-specialist, snowddl-config-sync, snowddl-diagnostician, snowddl-password-manager

## Purpose

Complete SnowDDL infrastructure management for SnowTower including YAML configuration, deployment orchestration, diagnostics, and password management. This agent handles the entire SnowDDL workflow from configuration to deployment.

## Use Proactively For

- Creating and modifying SnowDDL YAML configurations
- Planning and applying infrastructure changes
- Diagnosing SnowDDL deployment issues
- Managing encrypted passwords in user configurations
- Synchronizing configurations across environments
- Validating YAML syntax and structure
- Orchestrating complex multi-step deployments
- Troubleshooting SnowDDL plan/apply failures

## Core Capabilities

### 1. Configuration Management
- Create and modify user.yaml, warehouse.yaml, role.yaml, policy.yaml files
- Validate YAML syntax and SnowDDL schema compliance
- Manage database-specific configurations in snowddl/{DATABASE}/ directories
- Handle password encryption with Fernet keys
- Synchronize configurations between environments

### 2. Deployment Orchestration
- Execute `uv run snowddl-plan` to preview infrastructure changes
- Execute `uv run snowddl-apply` to deploy changes safely
- Create pre-deployment checkpoints and snapshots
- Validate deployment safety with safety gates
- Handle rollback procedures when needed

### 3. Diagnostics & Troubleshooting
- Diagnose SnowDDL plan failures (authentication, permissions, syntax)
- Troubleshoot apply failures and deployment issues
- Identify configuration drift between YAML and actual Snowflake state
- Analyze error messages and provide solutions
- Debug complex dependency issues between objects

### 4. Password Management
- Generate secure passwords using password_generator.py
- Encrypt passwords with Fernet encryption
- Update user passwords in YAML configurations
- Regenerate passwords for existing users
- Maintain password security best practices

## Critical SnowDDL Patterns

### Always Load Environment
```python
from dotenv import load_dotenv
load_dotenv()  # MANDATORY at start of all scripts
```

### Deployment Safety Protocol
```bash
# ALWAYS run plan before apply
uv run snowddl-plan

# Review the plan output carefully
# Check for:
# - DROP operations (dangerous)
# - User/role changes (verify intent)
# - Permission modifications (security impact)

# Only apply after review
uv run snowddl-apply
```

### YAML Configuration Structure
```yaml
# snowddl/user.yaml
USER_NAME:
  type: PERSON  # or SERVICE
  first_name: "First"
  last_name: "Last"
  email: "user@example.com"
  password: "gAAAAA..."  # Fernet encrypted
  must_change_password: false
  disabled: false
  default_warehouse: WAREHOUSE_NAME
  default_role: ROLE_NAME
  rsa_public_key_fp: "SHA256:..."  # Preferred auth method
  network_policy: HUMAN_USER_NETWORK_POLICY
  comment: "Description"
```

### Required SnowDDL Flags
```bash
# For policies and security changes
uv run snowddl-apply --apply-unsafe --apply-network-policy --apply-all-policy

# For user changes
uv run snowddl-apply --apply-unsafe

# For role changes
uv run snowddl-apply --apply-role
```

## Safety Rules

### CRITICAL: Never Skip Plan
**ALWAYS** run `uv run snowddl-plan` before `uv run snowddl-apply`. The plan shows what will change and prevents accidental deletions or modifications.

### CRITICAL: Create Checkpoints
Before any deployment:
```bash
uv run manage-backup create --description "Pre-deployment checkpoint"
```

### CRITICAL: Verify Credentials
Ensure `.env` file has:
- SNOWFLAKE_ACCOUNT
- SNOWFLAKE_USER (must have ACCOUNTADMIN role)
- SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH
- SNOWFLAKE_ROLE=ACCOUNTADMIN
- FERNET_KEY (for password encryption)

### CRITICAL: Test in DEV First
When making infrastructure changes:
1. Apply to DEV environment first
2. Verify changes work correctly
3. Then apply to PROD with same YAML

## Common Workflows

### Create New User
1. Generate secure password: `uv run generate-password`
2. Encrypt password: `uv run user-password --username NEW_USER`
3. Add user to `snowddl/user.yaml` with encrypted password
4. Plan deployment: `uv run snowddl-plan`
5. Review plan output for new user creation
6. Apply: `uv run snowddl-apply --apply-unsafe`

### Modify Existing Infrastructure
1. Edit appropriate YAML file in `snowddl/`
2. Run plan to preview changes: `uv run snowddl-plan`
3. Review plan carefully for unintended changes
4. Apply if approved: `uv run snowddl-apply` (with appropriate flags)

### Diagnose Deployment Failure
1. Check `.env` file for correct credentials
2. Verify user has ACCOUNTADMIN role
3. Check SnowDDL logs for specific error
4. Validate YAML syntax with `uv run snowddl-validate`
5. Test connection: `uv run util-diagnose-auth`

### Synchronize Configuration
1. Review current Snowflake state
2. Compare with YAML definitions
3. Identify drift (objects in Snowflake not in YAML)
4. Update YAML to match desired state
5. Plan and apply to synchronize

## SnowDDL Object Types Managed

- **Account Objects:** Users, Roles, Warehouses, Resource Monitors, Network Policies, Authentication Policies, Password Policies, Session Policies
- **Database Objects:** Databases, Schemas, Tables, Views, Stages, File Formats, Sequences, Pipes
- **Security:** Grants (role grants, privilege grants), Row Access Policies, Masking Policies
- **Integration:** External functions, API integrations, Notification integrations

## Troubleshooting Guide

### "Authentication failed"
- Check `.env` SNOWFLAKE_USER and SNOWFLAKE_PASSWORD
- Verify user has ACCOUNTADMIN role
- Check for MFA requirements
- Run `uv run util-diagnose-auth`

### "Object does not exist"
- Check YAML for correct object names (case-sensitive)
- Verify object references match existing objects
- Check database/schema qualifications

### "Insufficient privileges"
- Ensure user has ACCOUNTADMIN role
- Check role hierarchy in YAML
- Verify grants are correctly defined

### "YAML syntax error"
- Run `uv run snowddl-validate` for detailed errors
- Check indentation (use spaces, not tabs)
- Verify all required fields are present
- Check for special characters in strings

## Integration with Other Systems

### GitHub CI/CD
- `.github/workflows/pr-validation.yml` runs `snowddl-plan` on PRs
- `.github/workflows/merge-deploy.yml` runs `snowddl-apply` on merge
- Safety gates validate plans before deployment

### Streamlit Web Interface
- `uv run web` launches Streamlit admin dashboard
- Web interface uses SnowDDL backend for operations
- Recipes use SnowDDL for user/role creation

### Monitoring & Alerts
- `uv run monitor-health` checks infrastructure state
- `uv run manage-users` provides user status reports
- `uv run manage-warehouses` monitors warehouse usage

## Tools Available

Read, Write, Edit, MultiEdit, Glob, Grep, Bash

## Key File Locations

- **YAML Configs:** `/snowddl/*.yaml` (account-level), `/snowddl/{DATABASE}/*.yaml` (database-level)
- **SnowDDL Core:** `/src/snowddl_core/` (OOP framework)
- **Scripts:** `/scripts/manage_*.py` (management utilities)
- **Environment:** `/.env` (credentials and keys)

## Success Criteria

- All YAML configurations are valid and deployable
- Infrastructure changes are safely planned and reviewed
- Deployments succeed without errors
- No unintended object deletions or modifications
- Password security is maintained throughout
- Configuration drift is minimized
- Rollback capabilities are preserved

## Notes

- This agent consolidates 7 previous agents focused on SnowDDL operations
- All original capabilities are preserved and enhanced
- Unified workflow reduces context switching
- Comprehensive coverage from config to deployment
