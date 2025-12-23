# SnowTower User Creation Guide - Complete Reference

## Table of Contents

- [Overview](#overview)
- [User Creation Methods](#user-creation-methods)
  - [Method 1: Streamlit Web Interface](#method-1-streamlit-web-interface)
  - [Method 2: Command Line Interface](#method-2-command-line-interface)
  - [Method 3: GitHub Issue Integration](#method-3-github-issue-integration)
  - [Method 4: Direct YAML Configuration](#method-4-direct-yaml-configuration)
- [Authentication Configuration](#authentication-configuration)
- [User Types and Policies](#user-types-and-policies)
- [Deployment Process](#deployment-process)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting Guide](#troubleshooting-guide)
- [API Reference](#api-reference)

## Overview

SnowTower provides multiple methods for creating and managing Snowflake users with enterprise-grade security features. The system supports:

- **Multiple creation interfaces**: Streamlit UI, CLI commands, GitHub automation, direct YAML
- **Dual authentication methods**: RSA key pairs and encrypted passwords
- **User type differentiation**: PERSON (human) and SERVICE (application) accounts
- **Security compliance**: MFA readiness, network policies, encrypted credentials
- **Automated workflows**: Password generation, RSA key creation, Git synchronization

### Architecture Flow

```
User Creation Request
         ↓
[Streamlit/CLI/GitHub/YAML]
         ↓
Configuration Generation
         ↓
Fernet Encryption
         ↓
YAML Storage (S3/Git)
         ↓
SnowDDL Processing
         ↓
Snowflake Deployment
```

## User Creation Methods

### Method 1: Streamlit Web Interface

The Streamlit interface provides a visual, user-friendly approach to user creation with real-time validation and automatic configuration generation.

#### Setup Requirements

1. **Configure Fernet Encryption Key**

```toml
# .streamlit/secrets.toml or Snowflake Streamlit secrets
SNOWFLAKE_CONFIG_FERNET_KEYS = "9pBvGWv3LpX2fKBmiaA6h3lInG0_PwkhNmVISyihXLc="
```

2. **Verify S3 Stage Access**

```sql
-- Check deployment and backup stages
SHOW STAGES LIKE 'SNOWTOWER_S3_DEPLOYMENT_STAGE';
SHOW STAGES LIKE 'SNOWTOWER_S3_BACKUP_STAGE';

-- Test access
LIST @SNOWTOWER_S3_DEPLOYMENT_STAGE;
```

#### Step-by-Step Process

1. **Access the Streamlit App**
   - Navigate to: `https://<account>.snowflakecomputing.com/streamlit-apps/snowtower_streamlit`
   - Go to "🏗️ Generate Config" tab
   - Select "User" as configuration type

2. **Fill User Information**

   **Basic Information**:
   - Username: Uppercase with underscores (e.g., `JOHN_DOE`)
   - User Type: `PERSON` or `SERVICE`
   - Email: Required for MFA compliance
   - First/Last Name: Recommended for PERSON type

   **Authentication Setup**:
   - Password: Click "🎲 Generate Password" or enter custom
   - RSA Key: Paste public key or upload `.pub` file
   - Dual Auth: Enable both for maximum flexibility (recommended for PERSON)

   **Roles and Permissions**:
   - Business Roles: Select from available roles
   - Default Warehouse: Choose compute resource
   - Network Policy: Apply IP restrictions if needed

3. **Preview and Deploy**
   - Click "👁️ Preview YAML" to review configuration
   - Click "🚀 Generate & Deploy" to write to S3
   - **CRITICAL**: Copy generated password immediately (shown only once)

4. **Sync to Git Repository**

```bash
# Download from S3
aws s3 cp s3://bucket/yaml-configs/user_JOHN_DOE_*.yaml ./snowddl/

# Merge into user.yaml
# Copy user section and append to snowddl/user.yaml

# Commit changes
git add snowddl/user.yaml
git commit -m "Add user JOHN_DOE via Streamlit"
git push
```

### Method 2: Command Line Interface

The CLI provides powerful automation capabilities for user creation with multiple interfaces.

#### Interactive Wizard (Recommended)

```bash
# Launch interactive wizard
uv run user-onboard --wizard

# The wizard will guide you through:
# 1. User type selection (PERSON/SERVICE)
# 2. Authentication method choice
# 3. Role assignment
# 4. Security policy configuration
```

#### Quick Mode with Smart Defaults

```bash
# Create user with intelligent defaults
uv run user-onboard --quick \
  --name JANE_SMITH \
  --email jane.smith@company.com
```

#### Non-Interactive Automation

```bash
# Full specification for CI/CD integration
uv run user-onboard \
  --name JOHN_DOE \
  --email john.doe@company.com \
  --type PERSON \
  --auth-method dual \
  --generate-rsa \
  --generate-password \
  --roles "COMPANY_USERS,ANALYST_ROLE" \
  --warehouse COMPUTE_WH \
  --network-policy company_network_policy \
  --auto-save
```

#### Bulk User Creation

```bash
# Generate passwords for multiple users
uv run generate-passwords \
  --usernames "USER1,USER2,USER3" \
  --length 16 \
  --export passwords.json

# Process from CSV file
uv run generate-passwords \
  --csv-file users.csv \
  --export credentials.csv \
  --format csv
```

#### Password Management Commands

```bash
# Generate single password
uv run generate-password TEST_USER --length 20

# Regenerate for existing user
uv run regenerate-password EXISTING_USER --confirm

# Interactive password encryption
uv run python src/encrypt_password.py --interactive
```

### Method 3: GitHub Issue Integration

Automated user creation from GitHub access request issues.

#### Setup Process

1. **User Submits Access Request**
   - Navigate to repository issues
   - Select "Request Snowflake Access" template
   - Fill in required information including RSA public key

2. **Automated Processing**

```bash
# Process GitHub issue automatically
uv run process-access-request \
  --issue-json '{"title": "Access Request", "body": "..."}' \
  --output-dir /tmp/new-user

# This automatically:
# - Parses issue content
# - Generates RSA keys if not provided
# - Creates secure password
# - Generates encrypted YAML
# - Outputs credentials for delivery
```

3. **Manual Review and Deployment**

```bash
# Review generated configuration
cat /tmp/new-user/user_config.yaml

# Deploy if approved
uv run snowddl-apply
```

### Method 4: Direct YAML Configuration

For advanced users who prefer direct configuration file editing.

#### YAML Structure

```yaml
# snowddl/user.yaml

# PERSON User Example
JOHN_DOE:
  type: PERSON
  first_name: "John"
  last_name: "Doe"
  login_name: "john_doe"
  display_name: "John Doe"
  email: john.doe@company.com
  comment: "Data analyst - Added 2025-10-01"

  # Authentication
  password: !decrypt gAAAAABexampleEncryptedPasswordHere...
  rsa_public_key: |
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3oiHNK8PPOIUm+mSnC3P
    /OCBvv/2JEDdIIkdSnKD3hQ2vn8t7+F1FkmxTxWqAKTItssApm9byIFiLJ+PyvIL
    F08UNF1ZhXZLBeCmzGYb4WdGF0Qpz14OV1wxjPicpSfkFEc6zW3QS4vNNXYQaNic

  # Access Control
  business_roles:
    - COMPANY_USERS
    - ANALYST_ROLE
  default_warehouse: COMPUTE_WH
  default_namespace: "ANALYTICS.PUBLIC"
  default_role: COMPANY_USERS

  # Security Policies
  network_policy: company_network_policy
  authentication_policy: mfa_required_policy

  # Password Policies (PERSON only)
  must_change_password: true
  days_to_expiry: 90
  mins_to_unlock: 15
  disabled: false

# SERVICE Account Example
DLT_SERVICE:
  type: SERVICE
  login_name: "dlt_service"
  display_name: "DLT Service Account"
  email: user@example.com
  comment: "Data Load Tool service for Stripe integration"

  # RSA Only for Service Accounts
  rsa_public_key: MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...

  # Service Account Roles
  business_roles:
    - DLT_STRIPE_ROLE
    - SERVICE_ACCOUNTS_ROLE
  default_warehouse: DLT

  # No network policy for automation
  # No password for service accounts
```

#### Password Encryption for YAML

```bash
# Generate encrypted password for YAML
uv run python src/encrypt_password.py --interactive
# Enter password when prompted
# Copy encrypted output to YAML password field
```

## Authentication Configuration

### RSA Key Pair Setup

#### Generate New RSA Keys

```bash
# Generate 2048-bit RSA key pair (standard)
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out ~/.ssh/snowflake_rsa_key.p8
openssl rsa -in ~/.ssh/snowflake_rsa_key.p8 -pubout -out ~/.ssh/snowflake_rsa_key.pub

# Generate 4096-bit RSA key pair (enhanced security)
openssl genrsa 4096 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out ~/.ssh/snowflake_rsa_key_4096.p8
openssl rsa -in ~/.ssh/snowflake_rsa_key_4096.p8 -pubout -out ~/.ssh/snowflake_rsa_key_4096.pub

# Secure the private key
chmod 400 ~/.ssh/snowflake_rsa_key*.p8

# Display public key for copying
cat ~/.ssh/snowflake_rsa_key.pub
```

#### RSA Key Best Practices

1. **Key Storage**:
   - Store private keys securely (password manager, encrypted volume)
   - Never commit private keys to version control
   - Backup keys in secure location

2. **Key Rotation**:
   - Rotate keys quarterly for service accounts
   - Rotate annually for human users
   - Maintain old keys during transition period

3. **Key Distribution**:
   - Share only public keys
   - Use secure channels for key exchange
   - Document key fingerprints

### Password Management

#### Automatic Password Generation

The system provides cryptographically secure password generation:

```python
# Password Generation Configuration
DEFAULT_SETTINGS = {
    'length': 16,              # Minimum 12, recommended 16+
    'include_uppercase': True,  # A-Z
    'include_lowercase': True,  # a-z
    'include_digits': True,     # 0-9
    'include_symbols': True,    # !@#$%^&*
    'exclude_ambiguous': True,  # Exclude 0, O, l, I, etc.
}
```

#### Fernet Encryption Setup

```bash
# Generate new Fernet key
uv run util-generate-key

# Set in environment
export SNOWFLAKE_CONFIG_FERNET_KEYS="your-fernet-key-here"

# Add to .env file
echo "SNOWFLAKE_CONFIG_FERNET_KEYS=your-fernet-key-here" >> .env
```

### Dual Authentication Strategy

**Recommended for PERSON Users**:
- Primary: RSA key authentication
- Fallback: Encrypted password
- Benefits: Prevents lockout, supports multiple access methods

**Example Configuration**:
```yaml
ADMIN_USER:
  type: PERSON
  password: !decrypt <encrypted_password>
  rsa_public_key: <public_key>
  comment: "Dual auth for lockout prevention"
```

## User Types and Policies

### PERSON (Human Users)

**Characteristics**:
- Requires email for MFA enrollment
- Subject to password policies
- Network policy restrictions recommended
- MFA mandatory by March 2026

**Security Configuration**:
```yaml
type: PERSON
network_policy: company_network_policy
authentication_policy: mfa_required_policy
must_change_password: true
days_to_expiry: 90
mins_to_unlock: 15
```

### SERVICE (Service Accounts)

**Characteristics**:
- No MFA requirement
- RSA key authentication only
- No network restrictions (typically)
- Minimal privilege principle

**Security Configuration**:
```yaml
type: SERVICE
# No password field
# No network_policy (or specific CIDR if needed)
# No password expiry settings
comment: "Service account for automated ETL"
```


## Deployment Process

### Step 1: Plan Changes

```bash
cd /path/to/snowtower-snowddl

# Preview all changes
uv run snowddl-plan

# Preview specific user changes
uv run snowddl-plan | grep -A 10 "CREATE USER"
```

### Step 2: Apply to Snowflake

```bash
# Standard deployment
uv run snowddl-apply

# Apply with policy changes
uv run snowddl-apply --apply-unsafe

# Apply network policies
uv run snowddl-apply --apply-network-policy

# Apply all policies
uv run snowddl-apply --apply-all-policy
```

### Step 3: Verify Deployment

```bash
# Using SnowTower management commands
uv run manage-users --list --filter "name=JOHN_DOE"

# Using SQL
snow sql -c prod -q "SHOW USERS LIKE 'JOHN_DOE'"

# Test authentication
snowsql -a <account> -u JOHN_DOE --private-key-path ~/.ssh/snowflake_rsa_key.p8
```

### Rollback Procedures

```bash
# If issues occur, rollback to previous state
git checkout HEAD~1 snowddl/user.yaml
uv run snowddl-plan
uv run snowddl-apply

# Or disable user temporarily
# Edit user.yaml: disabled: true
uv run snowddl-apply
```

## Security Best Practices

### For PERSON Users

1. **Enable MFA**: Configure multi-factor authentication immediately
2. **Dual Authentication**: Use both RSA keys and passwords
3. **Network Policies**: Restrict to known IP ranges
4. **Password Rotation**: Enforce 90-day expiry
5. **Secure Delivery**: Use encrypted channels for credentials

### For SERVICE Accounts

1. **RSA Only**: Never use passwords
2. **Minimal Permissions**: Grant only required roles
3. **Key Rotation**: Quarterly rotation schedule
4. **Audit Logging**: Monitor all service account activity
5. **Documentation**: Clear purpose and owner identification

### General Security Guidelines

1. **Encryption at Rest**: All passwords Fernet-encrypted
2. **No Plaintext Storage**: Never store unencrypted passwords
3. **Audit Trail**: Git history for all changes
4. **Access Reviews**: Quarterly user access audits
5. **Emergency Procedures**: Documented recovery processes

## Troubleshooting Guide

### Common Issues and Solutions

#### "Encryption key not configured"

**Symptom**: Streamlit or CLI cannot encrypt passwords

**Solution**:
```bash
# Check for Fernet key
echo $SNOWFLAKE_CONFIG_FERNET_KEYS

# Generate if missing
uv run util-generate-key

# Add to environment
export SNOWFLAKE_CONFIG_FERNET_KEYS="<generated-key>"
```

#### "Authentication Failed"

**Symptom**: User cannot connect to Snowflake

**Checklist**:
- Verify username matches exactly (case-sensitive)
- Check RSA key path is correct
- Ensure user creation completed successfully
- Verify network policy allows your IP
- Check if MFA is required but not configured

#### "Network Policy Violation"

**Symptom**: Connection blocked by network policy

**Solutions**:
```sql
-- Check current IP
SELECT CURRENT_IP_ADDRESS();

-- View network policy
DESC NETWORK POLICY company_network_policy;

-- Add IP to allowlist (admin required)
ALTER NETWORK POLICY company_network_policy
  SET ALLOWED_IP_LIST = ('existing_ip', 'new_ip');
```

#### "Password Not Displayed"

**Symptom**: Cannot see generated password after deployment

**Solution**:
- Passwords shown only once for security
- Generate new password and redeploy
- Use password recovery procedures if needed

#### "SnowDDL Parse Error"

**Symptom**: YAML configuration rejected by SnowDDL

**Debug Steps**:
```bash
# Validate YAML syntax
uv run python -c "import yaml; yaml.safe_load(open('snowddl/user.yaml'))"

# Test configuration
uv run snowddl-plan --dry-run

# Check for missing required fields
# Required: type, email, business_roles (can be empty list)
```

### Validation Commands

```bash
# Test encryption setup
uv run util-diagnose-auth

# Validate user configuration
uv run user-manage user validate JOHN_DOE

# Check Fernet encryption
python -c "from user_management.encryption import FernetEncryption; print('✅ Encryption working')"

# Test password generation
uv run generate-password TEST_USER --length 16

# Run comprehensive tests
uv run python tests/test_streamlit_yaml_generation.py
```

## API Reference

### Core Classes

#### PasswordGenerator

```python
from user_management.password_generator import PasswordGenerator

generator = PasswordGenerator()

# Generate secure password
password = generator.generate_secure_password(
    length=16,
    exclude_ambiguous=True
)

# Generate with encryption
plain, encrypted = generator.generate_encrypted_password(length=16)

# Bulk generation
passwords = generator.generate_multiple_passwords(
    usernames=["USER1", "USER2"],
    user_type="PERSON",
    length=16
)
```

#### UserManager

```python
from user_management.manager import UserManager

manager = UserManager()

# Create user with all options
user_config = manager.create_user(
    username="JOHN_DOE",
    email="john.doe@company.com",
    user_type="PERSON",
    auth_method="dual",
    generate_rsa=True,
    generate_password=True,
    roles=["COMPANY_USERS"],
    warehouse="COMPUTE_WH"
)

# Validate existing user
is_valid = manager.validate_user("JOHN_DOE")

# Regenerate credentials
manager.regenerate_user_password("JOHN_DOE", length=20)
```

#### YAMLConfigManager

```python
from streamlit.yaml_config import YAMLConfigManager

manager = YAMLConfigManager()

# Generate user configuration
user_data = {
    'username': 'JOHN_DOE',
    'type': 'PERSON',
    'email': 'john.doe@company.com',
    'encrypted_password': 'gAAAAA...',
    'rsa_public_key': 'MIIBIj...',
    'business_roles': ['COMPANY_USERS'],
    'default_warehouse': 'COMPUTE_WH',
    'network_policy': 'company_network_policy'
}

yaml_config = manager.generate_user_config(user_data)

# Deploy to S3
success = manager.deploy_to_s3(yaml_config, "user_JOHN_DOE")
```

### CLI Commands Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `user-onboard` | Interactive user creation wizard | `uv run user-onboard --wizard` |
| `generate-password` | Generate single password | `uv run generate-password USER1` |
| `generate-passwords` | Bulk password generation | `uv run generate-passwords --csv users.csv` |
| `regenerate-password` | Update existing user password | `uv run regenerate-password USER1` |
| `encrypt_password.py` | Direct password encryption | `uv run python src/encrypt_password.py --interactive` |
| `user-manage` | Comprehensive user management | `uv run user-manage user create` |
| `process-access-request` | GitHub issue processing | `uv run process-access-request --issue-json` |
| `util-generate-key` | Generate Fernet encryption key | `uv run util-generate-key` |
| `util-diagnose-auth` | Test authentication setup | `uv run util-diagnose-auth` |
| `snowddl-plan` | Preview infrastructure changes | `uv run snowddl-plan` |
| `snowddl-apply` | Deploy changes to Snowflake | `uv run snowddl-apply` |

## Support and Resources

### Documentation
- Main README: `/README.md`
- Security Guide: `/docs/security/`
- Architecture: `/docs/architecture/`
- Agents: `/docs/agents/`

### Contact
- Owner: Alice Admin (admin@example.com)
- Repository: snowtower-snowddl
- Issues: GitHub Issues for bug reports and features

### Version Information
- **Version**: 3.0 (Consolidated Edition)
- **Last Updated**: 2025-10-01
- **Status**: Production Ready ✅

---

This comprehensive guide consolidates all user creation methods, security practices, and operational procedures for the SnowTower SnowDDL system. Follow the appropriate method for your use case and always prioritize security in user management operations.
