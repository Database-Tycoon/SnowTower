# SnowDDL Management Scripts

Practical Python scripts for managing Snowflake infrastructure through the SnowDDL OOP framework.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Available Scripts](#available-scripts)
  - [1. manage_users.py](#1-manage_userspy---user-management)
  - [2. manage_warehouses.py](#2-manage_warehousespy---warehouse-operations)
  - [3. cost_optimization.py](#3-cost_optimizationpy---cost-saving-operations)
  - [4. security_audit.py](#4-security_auditpy---security-auditing)
  - [5. backup_restore.py](#5-backup_restorepy---backup-and-restore)
- [Quick Start](#quick-start)
- [Integration with SnowDDL](#integration-with-snowddl)

## Overview

These scripts provide a command-line interface for common SnowDDL operations using the object-oriented framework. Each script is designed to be practical, focused, and production-ready.

## Prerequisites

### 1. Environment Setup

```bash
# Ensure you're in the snowtower-snowddl directory
cd /Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl

# Load environment variables (includes SNOWFLAKE_CONFIG_FERNET_KEYS)
source <(cat .env | grep -v '^#' | sed 's/^/export /')

# Or manually set Fernet key if needed
export SNOWFLAKE_CONFIG_FERNET_KEYS=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
```

### 2. Configuration Directory

- Default: `./snowddl/`
- Override with `--config-dir` flag on any script

## Available Scripts

### 1. manage_users.py - User Management

Comprehensive user management including creation, updates, role assignment, and reporting.

#### Quick Examples

```bash
# Add a new person user with password
python scripts/manage_users.py add \
  --name JOHN_DOE \
  --email john.doe@company.com \
  --password "SecurePass123!" \
  --save

# Add service account with RSA key
python scripts/manage_users.py add \
  --name ETL_SERVICE \
  --type SERVICE \
  --rsa-key-file ~/.ssh/etl_rsa.pub \
  --save

# Generate user report
python scripts/manage_users.py report --format table

# Assign role to user
python scripts/manage_users.py assign-role \
  --user JOHN_DOE \
  --role ANALYST_ROLE \
  --save

# Bulk update emails from CSV
python scripts/manage_users.py bulk-update \
  --file users.csv \
  --update-type email \
  --save
```

[Full documentation →](manage_users.md)

### 2. manage_warehouses.py - Warehouse Operations

Manage warehouse sizing, auto-suspend settings, and resource monitor assignments.

#### Quick Examples

```bash
# List all warehouses
python scripts/manage_warehouses.py list

# Resize a warehouse
python scripts/manage_warehouses.py resize \
  --name ADMIN \
  --size Medium \
  --save

# Set auto-suspend timeout
python scripts/manage_warehouses.py auto-suspend \
  --name FIVETRAN \
  --timeout 300 \
  --save

# Assign resource monitor
python scripts/manage_warehouses.py assign-monitor \
  --warehouse DLT \
  --monitor DLT_PIPELINE_MONITOR \
  --save

# Bulk resize from CSV
python scripts/manage_warehouses.py bulk-resize \
  --file warehouses.csv \
  --save

# Show warehouse details
python scripts/manage_warehouses.py show \
  --name MAIN_WAREHOUSE
```

#### CSV Format for Bulk Resize

```csv
name,size
ADMIN,Small
FIVETRAN,Medium
DLT,Large
```

### 3. cost_optimization.py - Cost-Saving Operations

Analyze and optimize Snowflake costs through warehouse downsizing, auto-suspend optimization, and monitoring.

#### Quick Examples

```bash
# Analyze warehouses for cost savings
python scripts/cost_optimization.py analyze

# Downsize all warehouses by one level
python scripts/cost_optimization.py downsize-all --save

# Optimize auto-suspend (aggressive = 60s)
python scripts/cost_optimization.py optimize-suspend \
  --strategy aggressive \
  --save

# Assign monitors to unmonitored warehouses
python scripts/cost_optimization.py auto-monitor --save

# Apply all recommended optimizations
python scripts/cost_optimization.py apply-recommendations --save

# Generate cost savings report
python scripts/cost_optimization.py savings-report
```

#### Auto-Suspend Strategies

- **aggressive**: 60 seconds (maximum savings)
- **balanced**: 300 seconds (5 minutes - recommended)
- **conservative**: 600 seconds (10 minutes - minimal disruption)

### 4. security_audit.py - Security Auditing

Comprehensive security auditing for MFA compliance, RSA keys, password policies, and network policies.

#### Quick Examples

```bash
# Full security audit
python scripts/security_audit.py full-audit

# Check RSA key configuration
python scripts/security_audit.py check-rsa-keys

# Check MFA compliance readiness
python scripts/security_audit.py check-mfa

# Find users with weak authentication
python scripts/security_audit.py weak-auth

# Check network policy coverage
python scripts/security_audit.py check-network-policies

# Generate compliance report
python scripts/security_audit.py compliance-report \
  --format table

# Get security recommendations
python scripts/security_audit.py recommendations
```

#### Security Checks Performed

1. **RSA Key Coverage**: Identifies users without RSA keys
2. **MFA Compliance**: Calculates readiness for 2025-2026 MFA rollout
3. **Password Policies**: Validates encryption and appropriate usage
4. **Network Policies**: Checks IP restriction coverage
5. **Weak Authentication**: Flags security vulnerabilities

### 5. backup_restore.py - Backup and Restore

Create, manage, and restore configuration backups with full version control.

#### Quick Examples

```bash
# Create backup with description
python scripts/backup_restore.py create \
  --description "Before MFA rollout"

# Create tagged backup
python scripts/backup_restore.py create \
  --tag pre_production \
  --description "Pre-production checkpoint"

# List all backups
python scripts/backup_restore.py list

# Show backup details
python scripts/backup_restore.py show \
  --backup 2024-09-23_150430

# Restore from backup
python scripts/backup_restore.py restore \
  --backup 2024-09-23_150430

# Compare current config with backup
python scripts/backup_restore.py diff \
  --backup 2024-09-23_150430

# Clean old backups (keep last 10)
python scripts/backup_restore.py cleanup --keep 10

# Export backup to archive
python scripts/backup_restore.py export \
  --backup 2024-09-23_150430 \
  --output backup.tar.gz

# Import backup from archive
python scripts/backup_restore.py import \
  --file backup.tar.gz
```

#### Backup Features

- Automatic timestamping
- Metadata tracking (description, tag, created_by)
- Diff functionality
- Auto-backup before restore
- Cleanup management
- Export/import support

## Quick Start

### Complete Workflow Example

```bash
# 1. Create a backup before changes
python scripts/backup_restore.py create \
  --description "Before warehouse optimization"

# 2. Run security audit
python scripts/security_audit.py full-audit

# 3. Optimize costs
python scripts/cost_optimization.py analyze
python scripts/cost_optimization.py apply-recommendations --save

# 4. Add new user
python scripts/manage_users.py add \
  --name NEW_USER \
  --email new@company.com \
  --type PERSON \
  --save

# 5. Preview Snowflake changes
uv run snowddl-plan

# 6. Apply to Snowflake
uv run snowddl-apply

# 7. Verify deployment
python scripts/manage_users.py show --name NEW_USER
```

### Daily Operations Checklist

```bash
# Morning: Health check
python scripts/manage_warehouses.py list
python scripts/cost_optimization.py analyze

# Weekly: Security audit
python scripts/security_audit.py full-audit

# Monthly: Backup cleanup
python scripts/backup_restore.py cleanup --keep 10
```

## Integration with SnowDDL

All scripts use the SnowDDL OOP framework which provides:

- **Type-safe object creation**: User, Role, Warehouse objects with validation
- **Automatic password encryption**: Fernet encryption with `!decrypt` tags
- **Dependency tracking**: Validates role and warehouse references
- **YAML serialization**: Compatible with SnowDDL plan/apply
- **Validation framework**: Catches configuration errors before deployment

### Standard Deployment Workflow

```bash
# 1. Make changes with scripts
python scripts/manage_*.py [command] --save

# 2. Preview Snowflake changes
uv run snowddl-plan

# 3. Review the plan output carefully

# 4. Apply to Snowflake
uv run snowddl-apply

# 5. Verify deployment
uv run snowddl-diff
```

### Key Classes Used

```python
from snowddl_core.project import SnowDDLProject
from snowddl_core.account_objects import User, Warehouse, ResourceMonitor

# Load project
project = SnowDDLProject("./snowddl")

# Make changes programmatically
user = User(name="EXAMPLE", email="example@company.com")
project.add_user(user)

# Save to YAML
project.save_all()
```

## Common Use Cases

### 1. User Onboarding

```bash
# Complete user setup
python scripts/manage_users.py add \
  --name ALICE_JOHNSON \
  --email alice@company.com \
  --type PERSON \
  --password "TempPass123!" \
  --roles ANALYST_ROLE \
  --warehouse ANALYST_WH \
  --save

uv run snowddl-plan
uv run snowddl-apply
```

### 2. Cost Optimization Sprint

```bash
# Create backup
python scripts/backup_restore.py create \
  --description "Pre-optimization checkpoint"

# Analyze and optimize
python scripts/cost_optimization.py analyze
python scripts/cost_optimization.py downsize-all --save
python scripts/cost_optimization.py optimize-suspend \
  --strategy balanced \
  --save

# Deploy
uv run snowddl-plan
uv run snowddl-apply
```

### 3. Security Compliance Audit

```bash
# Run full audit
python scripts/security_audit.py full-audit

# Get recommendations
python scripts/security_audit.py recommendations

# Generate compliance report
python scripts/security_audit.py compliance-report \
  --format json \
  --output compliance_$(date +%Y%m%d).json
```

### 4. Disaster Recovery

```bash
# Emergency restore
python scripts/backup_restore.py list
python scripts/backup_restore.py restore \
  --backup 2024-09-23_150430

# Verify and deploy
uv run snowddl-plan
uv run snowddl-apply
```

## Troubleshooting

### Common Errors

#### 1. Fernet Key Not Set

```bash
Error: SNOWFLAKE_CONFIG_FERNET_KEYS environment variable not set
```

**Solution:**
```bash
export SNOWFLAKE_CONFIG_FERNET_KEYS=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
```

#### 2. Import Errors

```bash
ModuleNotFoundError: No module named 'snowddl_core'
```

**Solution:**
```bash
# Ensure you're in the correct directory
cd /Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl

# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

#### 3. Configuration Not Found

```bash
Error: Configuration directory not found: ./snowddl
```

**Solution:**
```bash
# Specify correct path
python scripts/manage_users.py --config-dir /path/to/snowddl [command]
```

## Best Practices

1. **Always Create Backups Before Major Changes**
   ```bash
   python scripts/backup_restore.py create --description "Reason for change"
   ```

2. **Preview Before Apply**
   ```bash
   # Use --dry-run where available
   python scripts/cost_optimization.py downsize-all --dry-run

   # Always run snowddl-plan
   uv run snowddl-plan
   ```

3. **Regular Security Audits**
   ```bash
   # Weekly security check
   python scripts/security_audit.py full-audit
   ```

4. **Monitor Cost Trends**
   ```bash
   # Monthly cost analysis
   python scripts/cost_optimization.py analyze
   ```

5. **Version Control All Changes**
   ```bash
   git add snowddl/
   git commit -m "feat: optimize warehouse costs"
   ```

## Script Comparison

| Script | Primary Use Case | Output | Modifies Config |
|--------|-----------------|--------|-----------------|
| `manage_users.py` | User lifecycle management | Users, roles | Yes (with --save) |
| `manage_warehouses.py` | Warehouse operations | Warehouses | Yes (with --save) |
| `cost_optimization.py` | Cost reduction | Analysis, recommendations | Yes (with --save) |
| `security_audit.py` | Security compliance | Audit reports | No |
| `backup_restore.py` | Configuration backups | Backup status | Yes (backups only) |

## Related Documentation

- [SnowDDL OOP Framework](/src/snowddl_core/README.md)
- [User Management System](/src/user_management/README.md)
- [SnowDDL Official Documentation](https://snowddl.readthedocs.io/)
- [Project README](/README.md)

## Support

For issues or questions:

1. **Check validation errors**: `python scripts/manage_users.py save --dry-run`
2. **Review SnowDDL docs**: `uv run docs-serve`
3. **View configuration**: `python scripts/manage_users.py report --format table`
4. **Run security audit**: `python scripts/security_audit.py full-audit`

## Contributing

To extend these scripts:

1. **Add New Commands**: Extend argparse subparsers
2. **Add New Reports**: Implement new `_report_*` methods
3. **Add Validation**: Extend validation logic in relevant methods
4. **Follow Patterns**: Use existing scripts as templates

## License

Part of the SnowTower SnowDDL project - see main repository for license information.
