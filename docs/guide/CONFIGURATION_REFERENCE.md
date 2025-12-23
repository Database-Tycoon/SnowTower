# Configuration Reference

**Complete reference for SnowTower SnowDDL configuration including environment variables and YAML structure.**

---

## Table of Contents

1. [Environment Variables (.env)](#environment-variables-env)
2. [SnowDDL YAML Configuration](#snowddl-yaml-configuration)
3. [Configuration Examples](#configuration-examples)
4. [Security Best Practices](#security-best-practices)
5. [Troubleshooting Configuration](#troubleshooting-configuration)

---

## Environment Variables (.env)

### Setup

```bash
# Copy template to create your .env file
cp .env.example .env

# Set secure file permissions
chmod 600 .env

# Edit with your credentials
vi .env
```

### Required Variables

#### Snowflake Connection

```bash
# Your Snowflake account identifier
# Format: <account_locator>.<region>.<cloud>
# Example: YOUR_ACCOUNT, or abc12345.us-east-1.aws
SNOWFLAKE_ACCOUNT=your_account_identifier
```

**How to find:**
- Login to Snowflake web UI
- URL shows: `https://<account>.snowflakecomputing.com`
- Account identifier is the `<account>` part

```bash
# Snowflake username (must have ACCOUNTADMIN role)
# Example: ADMIN_USER, ALICE, etc.
SNOWFLAKE_USER=your_username
```

**Requirements:**
- Must exist in Snowflake
- Must have ACCOUNTADMIN role for SnowDDL operations
- Must have RSA public key registered (for key-pair auth)

```bash
# Role to use for operations
# MUST be ACCOUNTADMIN for SnowDDL to work correctly
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

**Why ACCOUNTADMIN:**
- SnowDDL needs to create/modify users, roles, warehouses
- Only ACCOUNTADMIN can manage account-level objects
- Lower privileges will cause deployment failures

```bash
# Warehouse for DDL operations
# Use an existing warehouse with auto-suspend enabled
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

**Best Practices:**
- Use small warehouse (X-SMALL or SMALL)
- Enable auto-suspend (300 seconds recommended)
- Dedicated warehouse for admin operations

#### RSA Key Authentication

```bash
# Path to your RSA private key file (PEM format)
# REQUIRED for secure authentication
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/snowflake_rsa_key.p8
```

**Generate RSA Keys:**
```bash
# Generate private key (2048-bit minimum, 4096-bit recommended)
openssl genrsa -out ~/.ssh/snowflake_rsa_key.p8 4096

# Extract public key
openssl rsa -in ~/.ssh/snowflake_rsa_key.p8 -pubout -out ~/.ssh/snowflake_rsa_key.pub

# Set secure permissions
chmod 400 ~/.ssh/snowflake_rsa_key.p8
chmod 644 ~/.ssh/snowflake_rsa_key.pub

# Get public key fingerprint for YAML
ssh-keygen -lf ~/.ssh/snowflake_rsa_key.pub
# Output: 4096 SHA256:abc123... user@host (RSA)
# Use the SHA256:abc123... part in your user.yaml
```

#### SnowDDL Configuration

```bash
# Fernet encryption key for password encryption in YAML
# REQUIRED - Generate with openssl or Python
SNOWFLAKE_CONFIG_FERNET_KEYS=your_fernet_encryption_key
```

**Generate Fernet Key:**
```bash
# Method 1: Using UV command (recommended)
uv run util-generate-key

# Method 2: Using Python
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Method 3: Using OpenSSL
openssl rand -base64 32
```

**Critical:**
- Keep this key secure - all encrypted passwords depend on it
- Never commit to git
- Store securely (password manager, secrets manager)
- If lost, all encrypted passwords must be regenerated

### Optional Variables

#### SnowDDL Behavior

```bash
# SnowDDL configuration directory (default: ./snowddl)
SNOWFLAKE_CONFIG_DIR=./snowddl
```

```bash
# Auto-confirm deployments (default: false, requires manual confirmation)
# WARNING: Set to true only for CI/CD automation
SNOWDDL_AUTO_CONFIRM=false
```

```bash
# Enable verbose logging for troubleshooting
SNOWDDL_VERBOSE=true
```

```bash
# Dry-run mode (plan only, never apply)
SNOWDDL_DRY_RUN=true
```

#### Alternative Authentication (Fallback Only)

```bash
# Password authentication (NOT RECOMMENDED)
# Only use as emergency fallback - RSA keys are required
# SNOWFLAKE_PASSWORD=your_encrypted_password
```

**Note:** SnowTower strongly recommends RSA key authentication. Passwords should only be used as emergency fallback.

#### MFA Settings

```bash
# MFA passcode (if MFA is enabled on your account)
# Leave empty if using RSA keys (MFA not required for key-pair auth)
# SNOWFLAKE_MFA_PASSCODE=123456
```

#### Logging & Monitoring

```bash
# Log file location (default: ./logs/snowddl.log)
SNOWDDL_LOG_FILE=./logs/snowddl.log
```

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
SNOWDDL_LOG_LEVEL=INFO
```

#### GitHub Integration (for CI/CD)

```bash
# GitHub personal access token for automation
# Needed for: Issue-based user provisioning, PR automation
GITHUB_TOKEN=ghp_your_token_here
```

**Generate Token:**
1. GitHub Settings → Developer Settings → Personal Access Tokens
2. Generate new token (classic)
3. Scopes needed: `repo`, `workflow`, `write:discussion`

```bash
# GitHub repository (format: owner/repo)
GITHUB_REPOSITORY=your-org/snowtower-snowddl
```

#### S3 Integration (Optional)

```bash
# AWS credentials for S3 configuration sync
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=us-east-1

# S3 bucket for configuration storage
S3_CONFIG_BUCKET=snowtower-configs
S3_CONFIG_PREFIX=environments/production
```

### Complete .env Example

```bash
# ============================================================================
# SNOWFLAKE CONNECTION (REQUIRED)
# ============================================================================
SNOWFLAKE_ACCOUNT=abc12345.us-east-1
SNOWFLAKE_USER=ADMIN_USER
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# ============================================================================
# RSA KEY AUTHENTICATION (REQUIRED)
# ============================================================================
SNOWFLAKE_PRIVATE_KEY_PATH=/Users/username/.ssh/snowflake_rsa_key.p8

# ============================================================================
# SNOWDDL CONFIGURATION (REQUIRED)
# ============================================================================
SNOWFLAKE_CONFIG_FERNET_KEYS=gAAAAABhK8Z9_example_fernet_key_base64_encoded

# ============================================================================
# OPTIONAL SETTINGS
# ============================================================================
SNOWFLAKE_CONFIG_DIR=./snowddl
SNOWDDL_AUTO_CONFIRM=false
SNOWDDL_VERBOSE=false
SNOWDDL_LOG_LEVEL=INFO

# ============================================================================
# GITHUB INTEGRATION (for CI/CD)
# ============================================================================
GITHUB_TOKEN=ghp_example_token
GITHUB_REPOSITORY=your-org/snowtower-snowddl

# ============================================================================
# AWS S3 (if using S3 config sync)
# ============================================================================
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# S3_CONFIG_BUCKET=snowtower-configs
```

---

## SnowDDL YAML Configuration

### Directory Structure

```
snowddl/
├── user.yaml                    # User accounts
├── tech_role.yaml               # Technical roles
├── business_role.yaml           # Business roles
├── warehouse.yaml               # Compute warehouses
├── resource_monitor.yaml        # Cost controls
├── network_policy.yaml          # Network access rules
├── authentication_policy.yaml   # Authentication rules
├── password_policy.yaml         # Password requirements
├── session_policy.yaml          # Session settings
├── {DATABASE}/                  # Database-specific configs
│   ├── schema.yaml              # Schemas
│   ├── table.yaml               # Tables
│   ├── view.yaml                # Views
│   ├── stage.yaml               # Stages
│   └── ...                      # Other database objects
```

### User Configuration (user.yaml)

```yaml
# Format: USERNAME (must be UPPERCASE)
EXAMPLE_USER:
  # User type: PERSON (human) or SERVICE (service account)
  type: PERSON

  # User details
  first_name: "John"
  last_name: "Doe"
  email: "john.doe@company.com"

  # Authentication - RSA keys (PREFERRED)
  rsa_public_key_fp: "SHA256:abc123def456..."

  # Authentication - Password fallback (encrypted with Fernet key)
  password: "gAAAAABhK8Z9..."  # Fernet encrypted
  must_change_password: false

  # Defaults
  default_warehouse: COMPUTE_WH
  default_role: DATA_ANALYST__T_ROLE
  default_namespace: DATABASE.SCHEMA  # Optional

  # Security
  network_policy: HUMAN_USER_NETWORK_POLICY  # Or ~ for unrestricted
  disabled: false
  days_to_expiry: 90  # Account expiry (optional)

  # Metadata
  comment: "Data Analyst - Marketing Team"
  display_name: "John Doe"  # Optional
```

**User Types:**

**PERSON (Human Users):**
- Requires network policy (IP restrictions)
- Should have MFA enabled (mandatory by March 2026)
- RSA keys + password fallback
- Business or technical roles

**SERVICE (Service Accounts):**
- No network policy (unrestricted for CI/CD)
- RSA keys ONLY (no passwords)
- Minimal permissions (least privilege)
- Technical roles only

**Field Reference:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `type` | Yes | PERSON or SERVICE | User category |
| `first_name` | Yes | String | First name |
| `last_name` | Yes | String | Last name |
| `email` | Yes | Email | Contact email |
| `rsa_public_key_fp` | Recommended | SHA256:... | RSA key fingerprint |
| `password` | Optional | Encrypted | Fernet-encrypted password |
| `must_change_password` | No | Boolean | Force password change |
| `default_warehouse` | Yes | Warehouse | Default compute |
| `default_role` | Yes | Role | Default role |
| `network_policy` | Conditional | Policy or ~ | Required for PERSON |
| `disabled` | No | Boolean | Account status |
| `comment` | Recommended | String | Description |

### Role Configuration (tech_role.yaml / business_role.yaml)

```yaml
DATA_ANALYST__T_ROLE:
  # Parent role in hierarchy
  owner_role: SYSADMIN

  # Comment
  comment: "Technical role for data analysts"

  # Grants to this role
  owner_warehouse_read:
    - COMPUTE_WH
    - ANALYTICS_WH

  owner_warehouse_write:
    - COMPUTE_WH

  owner_database_read:
    - DATABASE_NAME

  owner_schema_read:
    - DATABASE_NAME.SCHEMA_NAME

  owner_table_read:
    - DATABASE_NAME.SCHEMA_NAME.TABLE_NAME
```

**Role Naming Conventions:**
- Technical roles: `ROLE_NAME__T_ROLE`
- Business roles: `ROLE_NAME__B_ROLE`
- Admin roles: `ROLE_NAME` (no suffix)

**Role Hierarchy:**
```
ACCOUNTADMIN
    ↓
SYSADMIN → USERADMIN → SECURITYADMIN
    ↓           ↓            ↓
Business Roles (__B_ROLE)
    ↓
Technical Roles (__T_ROLE)
    ↓
Users
```

### Warehouse Configuration (warehouse.yaml)

```yaml
COMPUTE_WH:
  # Warehouse size
  size: MEDIUM  # X-SMALL, SMALL, MEDIUM, LARGE, X-LARGE, 2X-LARGE, etc.

  # Auto-suspend after inactivity (seconds)
  auto_suspend: 300  # 5 minutes

  # Auto-resume on query
  auto_resume: true

  # Multi-cluster settings
  min_cluster_count: 1
  max_cluster_count: 4
  scaling_policy: STANDARD  # or ECONOMY

  # Resource monitor
  resource_monitor: DAILY_MONITOR  # Optional

  # Initial state
  initially_suspended: true

  # Comment
  comment: "General purpose compute warehouse"
```

**Warehouse Sizes & Cost:**

| Size | Credits/Hour | Use Case |
|------|--------------|----------|
| X-SMALL | 1 | Development, testing |
| SMALL | 2 | Small analytics, ad-hoc queries |
| MEDIUM | 4 | Standard workloads |
| LARGE | 8 | Large transformations |
| X-LARGE | 16 | Heavy processing |
| 2X-LARGE | 32 | Very large workloads |

**Auto-Suspend Recommendations:**
- Development: 60-300 seconds
- Production analytics: 300-600 seconds
- ETL workloads: 600-900 seconds
- CI/CD: 60 seconds (fast shutdown)

### Network Policy Configuration (network_policy.yaml)

```yaml
HUMAN_USER_NETWORK_POLICY:
  # Allowed IP addresses/ranges (CIDR notation)
  allowed_ip_list:
    - "203.0.113.0/24"       # Office network
    - "198.51.100.10/32"     # VPN gateway
    - "192.0.2.50/32"        # Home office

  # Blocked IP addresses (takes precedence over allowed)
  blocked_ip_list: []

  comment: "Restricts human users to known IP addresses"
```

**Important:**
- Service accounts should have `network_policy: ~` (unrestricted)
- Always maintain one unrestricted admin account for emergencies
- Test network policy changes carefully to avoid lockout

### Authentication Policy (authentication_policy.yaml)

```yaml
STANDARD_AUTH_POLICY:
  # Allowed authentication methods
  authentication_methods:
    - KEYPAIR  # RSA key-pair (preferred)
    - PASSWORD  # Password authentication

  # MFA methods (when using password auth)
  mfa_authentication_methods:
    - PASSWORD  # Require MFA for password auth
    - SAML      # SAML with MFA

  # MFA enrollment requirement
  mfa_enrollment: OPTIONAL  # REQUIRED (mandatory by March 2026)

  # Security integrations (for SSO)
  security_integrations: []

  comment: "Standard authentication policy with MFA"
```

### Password Policy (password_policy.yaml)

```yaml
STRONG_PASSWORD_POLICY:
  password_min_length: 14
  password_max_length: 256
  password_min_upper_case_chars: 2
  password_min_lower_case_chars: 2
  password_min_numeric_chars: 2
  password_min_special_chars: 1
  password_max_age_days: 90
  password_max_retries: 5
  password_lockout_time_mins: 30
  password_history: 5  # Prevent reuse of last 5 passwords

  comment: "Enterprise-grade password requirements"
```

### Resource Monitor (resource_monitor.yaml)

```yaml
DAILY_MONITOR:
  # Credit quota
  credit_quota: 100  # Credits per month/week/day

  # Frequency
  frequency: DAILY  # MONTHLY, WEEKLY, DAILY, YEARLY, NEVER

  # Start time (for YEARLY/MONTHLY)
  start_timestamp: "2025-01-01 00:00"

  # Triggers (percentage of quota)
  triggers:
    - at_percentage: 80
      action: NOTIFY
    - at_percentage: 100
      action: SUSPEND
    - at_percentage: 120
      action: SUSPEND_IMMEDIATE

  # Notification recipients
  notify_users:
    - ADMIN_USER
    - FINANCE_USER

  comment: "Daily credit limit with notifications"
```

**Actions:**
- `NOTIFY`: Send alert but continue
- `SUSPEND`: Suspend warehouse after current queries complete
- `SUSPEND_IMMEDIATE`: Immediately suspend warehouse

---

## Configuration Examples

### Example 1: New Human User

```yaml
# user.yaml
ALICE_SMITH:
  type: PERSON
  first_name: "Alice"
  last_name: "Smith"
  email: "alice.smith@company.com"

  # RSA key authentication
  rsa_public_key_fp: "SHA256:abc123..."

  # Fallback password
  password: "gAAAAABhK8Z9..."
  must_change_password: false

  default_warehouse: COMPUTE_WH
  default_role: DATA_ANALYST__T_ROLE
  network_policy: HUMAN_USER_NETWORK_POLICY
  disabled: false

  comment: "Data Analyst - Sales Team"
```

### Example 2: Service Account for CI/CD

```yaml
# user.yaml
CI_CD_SERVICE:
  type: SERVICE
  first_name: "CI/CD"
  last_name: "Service"
  email: "devops@company.com"

  # RSA keys only - no password
  rsa_public_key_fp: "SHA256:def456..."

  default_warehouse: CI_CD_WH
  default_role: CI_CD__T_ROLE
  network_policy: ~  # Unrestricted for CI/CD

  disabled: false
  comment: "GitHub Actions service account"
```

### Example 3: Cost-Optimized Warehouse

```yaml
# warehouse.yaml
ETL_WH:
  size: LARGE
  auto_suspend: 300  # 5 minutes
  auto_resume: true

  # Single cluster (no multi-cluster scaling)
  min_cluster_count: 1
  max_cluster_count: 1

  # Cost control
  resource_monitor: DAILY_MONITOR

  initially_suspended: true
  comment: "ETL processing warehouse - auto-suspend enabled"
```

---

## Security Best Practices

### File Permissions

```bash
# .env file (contains credentials)
chmod 600 .env

# RSA private key
chmod 400 ~/.ssh/snowflake_rsa_key.p8

# RSA public key (can be world-readable)
chmod 644 ~/.ssh/snowflake_rsa_key.pub

# YAML configuration files
chmod 644 snowddl/*.yaml
```

### Git Ignore

Ensure `.gitignore` includes:

```
# Environment and secrets
.env
.env.*
!.env.example

# RSA keys
*.p8
*.pem
*_rsa
*_rsa.pub
*.key
*.priv

# Snowflake credentials
snowflake_*.p8
```

### Credential Rotation

**Monthly:**
- Review user access
- Check for inactive accounts

**Quarterly:**
- Rotate emergency account passwords
- Review network policies
- Update Fernet key (requires re-encrypting all passwords)

**Annually:**
- Rotate RSA keys for admin accounts
- Review all service accounts
- Audit role assignments

### Backup Configuration

```bash
# Backup .env file (to secure location)
cp .env ~/.secure-backups/.env.$(date +%Y%m%d)

# Backup YAML configurations
tar -czf snowddl-config-$(date +%Y%m%d).tar.gz snowddl/

# Backup RSA keys
cp ~/.ssh/snowflake_*.p8 /secure/backup/location/
```

---

## Troubleshooting Configuration

### Common Issues

#### "Authentication failed"

**Check:**
```bash
# Verify .env variables
grep SNOWFLAKE .env

# Test RSA key
ls -la ~/.ssh/snowflake_rsa_key.p8

# Verify Fernet key
grep FERNET .env
```

#### "Permission denied" on .env

**Fix:**
```bash
chmod 600 .env
```

#### "SnowDDL cannot find config"

**Check:**
```bash
# Verify config directory
echo $SNOWFLAKE_CONFIG_DIR
ls -la snowddl/

# Check YAML files exist
ls -la snowddl/*.yaml
```

#### "Fernet decryption failed"

**Cause:** Wrong Fernet key in .env

**Fix:**
```bash
# Regenerate all passwords with correct key
uv run regenerate-password --username ALL
```

### Validation Commands

```bash
# Validate environment configuration
uv run util-diagnose-auth

# Validate YAML syntax
uv run snowddl-validate

# Test connection
uv run monitor-health

# Verify SnowDDL can read config
uv run snowddl-plan
```

---

## Related Documentation

- [Quickstart Guide](../QUICKSTART.md) - Initial setup
- [Authentication Guide](user-management/AUTHENTICATION_GUIDE.md) - Authentication details
- [User Creation Guide](user-management/USER_CREATION_GUIDE.md) - User management
- [Troubleshooting](../TROUBLESHOOTING.md) - General troubleshooting

---

**Last Updated:** October 9, 2025
**Version:** 2.0
**Maintained By:** SnowTower Team
