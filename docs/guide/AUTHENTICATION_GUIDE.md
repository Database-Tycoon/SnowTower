# SnowTower Authentication Guide

## Table of Contents

- [Overview](#overview)
- [Authentication Methods](#authentication-methods)
- [RSA Key Authentication](#rsa-key-authentication)
- [Password Authentication](#password-authentication)
- [Dual Authentication Strategy](#dual-authentication-strategy)
- [Authentication by User Type](#authentication-by-user-type)
- [Security Best Practices](#security-best-practices)
- [MFA Compliance](#mfa-compliance)
- [Troubleshooting](#troubleshooting)

## Overview

SnowTower implements a comprehensive authentication strategy designed for enterprise security, compliance, and operational flexibility. The system supports multiple authentication methods with clear guidelines for when to use each approach.

### Authentication Hierarchy

1. **RSA Key Pairs** (Score: 100/100) - Most Secure
2. **Dual Authentication** (Score: 95/100) - Recommended for Admins
3. **Encrypted Passwords** (Score: 70/100) - Fallback Only
4. **Plain Passwords** (Score: 0/100) - Never Used

### Key Principles

- **Defense in Depth**: Multiple authentication layers
- **Least Privilege**: Minimal access by default
- **Zero Trust**: Verify everything, trust nothing
- **Compliance Ready**: MFA-compliant for 2026 mandate
- **Emergency Access**: Maintained through careful planning

## Authentication Methods

### Method Comparison

| Method | Security Score | Use Case | Pros | Cons |
|--------|---------------|----------|------|------|
| **RSA Only** | 100/100 | Service accounts, CLI tools | Most secure, no password exposure | Requires key management |
| **Dual (RSA + Password)** | 95/100 | Admin users, production access | Lockout prevention, flexible | More complex setup |
| **Password Only** | 40/100 | Emergency access only | Simple, universal | Less secure, rotation needed |
| **No Auth** | 0/100 | Never | None | Unacceptable security risk |

## RSA Key Authentication

### What is RSA Authentication?

RSA key authentication uses asymmetric cryptography where:
- **Private Key**: Kept secret on your machine
- **Public Key**: Shared with Snowflake
- **Authentication**: Proves identity without transmitting secrets

### Generating RSA Keys

#### Standard 2048-bit Keys (Minimum Security)

```bash
# Generate private key in PKCS8 format
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out ~/.ssh/snowflake_rsa_key.p8

# Extract public key
openssl rsa -in ~/.ssh/snowflake_rsa_key.p8 -pubout -out ~/.ssh/snowflake_rsa_key.pub

# Secure the private key
chmod 400 ~/.ssh/snowflake_rsa_key.p8
```

#### Enhanced 4096-bit Keys (Recommended)

```bash
# Generate stronger key pair
openssl genrsa 4096 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out ~/.ssh/snowflake_rsa_key_4096.p8
openssl rsa -in ~/.ssh/snowflake_rsa_key_4096.p8 -pubout -out ~/.ssh/snowflake_rsa_key_4096.pub
chmod 400 ~/.ssh/snowflake_rsa_key_4096.p8
```

#### Automated Key Generation via CLI

```bash
# Using user onboarding tool
uv run user-onboard --generate-rsa --rsa-key-size 4096

# Output location
keys/{username}_rsa_key_{timestamp}.p8
keys/{username}_rsa_key_{timestamp}.pub
```

### RSA Key Format

Public keys must be in PEM format:

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3oiHNK8PPOIUm+mSnC3P
/OCBvv/2JEDdIIkdSnKD3hQ2vn8t7+F1FkmxTxWqAKTItssApm9byIFiLJ+PyvIL
F08UNF1ZhXZLBeCmzGYb4WdGF0Qpz14OV1wxjPicpSfkFEc6zW3QS4vNNXYQaNic
...additional lines...
-----END PUBLIC KEY-----
```

### Configuring RSA in SnowDDL

```yaml
# In snowddl/user.yaml
USERNAME:
  type: PERSON
  rsa_public_key: |
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3oiHNK8PPOIUm+mSnC3P
    /OCBvv/2JEDdIIkdSnKD3hQ2vn8t7+F1FkmxTxWqAKTItssApm9byIFiLJ+PyvIL
    # ... rest of key
```

### Using RSA Authentication

#### SnowSQL Connection

```bash
snowsql \
  --accountname YOUR_ACCOUNT \
  --username YOUR_USERNAME \
  --private-key-path ~/.ssh/snowflake_rsa_key.p8 \
  --role YOUR_ROLE \
  --warehouse YOUR_WAREHOUSE
```

#### Python Connector

```python
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Load private key
with open('~/.ssh/snowflake_rsa_key.p8', 'rb') as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None,
        backend=default_backend()
    )

# Connect to Snowflake
conn = snowflake.connector.connect(
    user='YOUR_USERNAME',
    account='YOUR_ACCOUNT',
    private_key=private_key,
    role='YOUR_ROLE',
    warehouse='YOUR_WAREHOUSE'
)
```

#### Snow CLI

```bash
# Configure connection
snow connection add \
  --connection-name prod \
  --account YOUR_ACCOUNT \
  --user YOUR_USERNAME \
  --private-key-path ~/.ssh/snowflake_rsa_key.p8

# Use connection
snow sql -c prod -q "SELECT CURRENT_USER()"
```

## Password Authentication

### Password Security Model

SnowTower implements a comprehensive password security model:

1. **Generation**: Cryptographically secure random passwords
2. **Encryption**: Fernet symmetric encryption at rest
3. **Storage**: Encrypted in YAML configurations
4. **Transmission**: Never sent in plaintext
5. **Rotation**: Enforced periodic changes

### Password Generation

#### Automatic Generation (Recommended)

```bash
# Single user
uv run generate-password USERNAME --length 20

# Bulk generation
uv run generate-passwords --usernames "USER1,USER2,USER3" --length 16

# With custom options
uv run generate-password USERNAME \
  --length 24 \
  --exclude-ambiguous \
  --user-type PERSON
```

#### Manual Password Encryption

```bash
# Interactive mode (most secure)
uv run python src/encrypt_password.py --interactive
# Enter password when prompted
# Receive: gAAAAABexampleEncryptedPasswordHere......

# Direct mode (less secure, avoid)
uv run python src/encrypt_password.py "MyPassword123!"
```

### Fernet Encryption Setup

#### Generate Encryption Key

```bash
# Generate new Fernet key
uv run util-generate-key
# Output: 9pBvGWv3LpX2fKBmiaA6h3lInG0_PwkhNmVISyihXLc=

# Or using Python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### Configure Environment

```bash
# Set in environment
export SNOWFLAKE_CONFIG_FERNET_KEYS="9pBvGWv3LpX2fKBmiaA6h3lInG0_PwkhNmVISyihXLc="

# Add to .env file
echo "SNOWFLAKE_CONFIG_FERNET_KEYS=9pBvGWv3LpX2fKBmiaA6h3lInG0_PwkhNmVISyihXLc=" >> .env

# For Streamlit
# Add to .streamlit/secrets.toml
SNOWFLAKE_CONFIG_FERNET_KEYS = "9pBvGWv3LpX2fKBmiaA6h3lInG0_PwkhNmVISyihXLc="
```

### Password Configuration in YAML

```yaml
USERNAME:
  type: PERSON
  # Encrypted password with Fernet
  password: !decrypt gAAAAABexampleEncryptedPasswordHere...

  # Password policies (PERSON only)
  must_change_password: true
  days_to_expiry: 90
  mins_to_unlock: 15
```

### Password Best Practices

1. **Minimum Length**: 12 characters (16+ recommended)
2. **Complexity**: Upper, lower, numbers, symbols
3. **Uniqueness**: Never reuse passwords
4. **Storage**: Only encrypted, never plaintext
5. **Delivery**: Secure channels only (1Password, encrypted email)

## Dual Authentication Strategy

### Why Dual Authentication?

Dual authentication (RSA + Password) provides:

- **Lockout Prevention**: Alternative access method if one fails
- **Flexibility**: Different tools support different methods
- **Security**: RSA for automation, password for emergency
- **Compliance**: Meets various security requirements

### Implementing Dual Authentication

#### Via CLI

```bash
uv run user-onboard \
  --name ADMIN_USER \
  --email admin@company.com \
  --type PERSON \
  --auth-method dual \
  --generate-rsa \
  --generate-password
```

#### Via YAML Configuration

```yaml
ADMIN_USER:
  type: PERSON
  email: admin@company.com

  # Both authentication methods
  rsa_public_key: |
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
  password: !decrypt gAAAAABexampleEncryptedPasswordHere......

  comment: "Admin with dual auth for lockout prevention"
```

### Usage Scenarios

| Scenario | Primary Auth | Fallback Auth | Reason |
|----------|-------------|---------------|---------|
| Daily CLI work | RSA key | - | Secure, automated |
| Web UI access | Password | - | Browser-based only |
| Emergency access | Password | RSA key | Network issues |
| Script automation | RSA key | - | No password exposure |
| Initial setup | Password | RSA key | Key not yet configured |

## Authentication by User Type

### PERSON (Human Users)

**Standard Configuration**:
```yaml
JOHN_DOE:
  type: PERSON
  email: john.doe@company.com

  # Dual authentication recommended
  rsa_public_key: <public_key>
  password: !decrypt <encrypted_password>

  # Security policies
  network_policy: company_network_policy
  authentication_policy: mfa_required_policy

  # Password policies
  must_change_password: true
  days_to_expiry: 90
  mins_to_unlock: 15
```

**Authentication Requirements**:
- MFA mandatory by March 2026
- Network policy restrictions
- Regular password rotation
- Audit logging enabled

### SERVICE (Service Accounts)

**Standard Configuration**:
```yaml
ETL_SERVICE:
  type: SERVICE
  email: etl@company.com

  # RSA ONLY - never use passwords
  rsa_public_key: <public_key>
  # NO password field

  # No network restrictions for automation
  # No password policies

  comment: "ETL service for data pipeline"
```

**Authentication Requirements**:
- RSA key authentication only
- No password ever
- No MFA requirement
- Quarterly key rotation


## Security Best Practices

### Key Management

1. **Storage**:
   - Private keys in encrypted storage
   - Use password managers for key passphrases
   - Backup keys in secure locations

2. **Rotation**:
   ```bash
   # Quarterly for service accounts
   # Annual for human users
   # Generate new keys
   openssl genrsa 4096 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out new_key.p8

   # Update in SnowDDL
   # Deploy changes
   # Test new keys
   # Remove old keys after grace period
   ```

3. **Distribution**:
   - Share only public keys
   - Use secure channels
   - Verify key fingerprints

### Password Management

1. **Generation**:
   ```python
   # Password requirements
   MIN_LENGTH = 12
   RECOMMENDED_LENGTH = 16
   REQUIRE_UPPER = True
   REQUIRE_LOWER = True
   REQUIRE_DIGIT = True
   REQUIRE_SYMBOL = True
   EXCLUDE_AMBIGUOUS = True  # No 0, O, l, I
   ```

2. **Rotation Schedule**:
   - Human users: 90 days
   - Admin accounts: 60 days
   - Service accounts: Never (use RSA)
   - Emergency accounts: Annual

3. **Delivery Methods**:
   - 1Password shared vaults
   - Encrypted email
   - Secure messaging
   - Never plaintext email

### Network Security

```yaml
# Network policy configuration
network_policies:
  company_network_policy:
    allowed_ip_list:
      - 192.0.2.10/32  # Office
      - 192.168.1.0/24    # VPN
    blocked_ip_list: []
    comment: "Human users network restriction"
```

## MFA Compliance

### Timeline

- **March 2026**: Mandatory MFA for all PERSON users
- **Current Status**: MFA-ready infrastructure deployed
- **Enforcement**: Automatic via authentication_policy

### Configuration

```yaml
# MFA-required authentication policy
authentication_policies:
  mfa_required_policy:
    mfa_enrollment: REQUIRED
    mfa_authentication_methods:
      - PASSWORD
      - SAML
    client_types:
      - SNOWFLAKE_UI
      - DRIVERS
```

### User Setup

```sql
-- Enable MFA for user
ALTER USER john_doe SET MUST_CHANGE_PASSWORD = TRUE;

-- User enrolls MFA on next login
-- Follow Snowflake MFA setup wizard
```

## Troubleshooting

### Common Authentication Issues

#### "Authentication failed"

**Diagnosis**:
```bash
# Test RSA key
openssl rsa -in ~/.ssh/snowflake_rsa_key.p8 -check

# Verify public key format
cat ~/.ssh/snowflake_rsa_key.pub | head -1
# Should show: -----BEGIN PUBLIC KEY-----

# Check user configuration
uv run show users --filter "name=USERNAME"
```

**Solutions**:
1. Verify username case (must match exactly)
2. Check key file permissions (400 or 600)
3. Ensure key path is correct
4. Verify user exists in Snowflake

#### "Invalid private key"

**Diagnosis**:
```bash
# Check key format
file ~/.ssh/snowflake_rsa_key.p8
# Should show: ASCII text

# Verify PKCS8 format
openssl pkcs8 -in ~/.ssh/snowflake_rsa_key.p8 -nocrypt
```

**Solutions**:
1. Regenerate key in PKCS8 format
2. Remove password from key file
3. Check for corruption

#### "Password decrypt error"

**Diagnosis**:
```python
# Test Fernet key
from cryptography.fernet import Fernet
key = "your-fernet-key"
f = Fernet(key.encode())
# Should not error
```

**Solutions**:
1. Verify SNOWFLAKE_CONFIG_FERNET_KEYS is set
2. Ensure same key used for encryption/decryption
3. Check for key rotation issues

#### "MFA not configured"

**Solutions**:
1. User must log in via Snowflake UI
2. Follow MFA enrollment wizard
3. Configure authenticator app
4. Test MFA before enforcement

### Validation Commands

```bash
# Test authentication setup
uv run util-diagnose-auth

# Validate user configuration
uv run user-manage user validate USERNAME

# Test RSA connection
snow sql -c prod -q "SELECT CURRENT_USER()"

# Test password encryption
uv run python src/encrypt_password.py --interactive

# Verify Fernet setup
python -c "from user_management.encryption import FernetEncryption; FernetEncryption()"
```

## Migration Strategies

### From Password-Only to RSA

1. **Generate RSA keys** for all users
2. **Add keys** to user configurations
3. **Test RSA** authentication
4. **Deprecate passwords** gradually
5. **Remove passwords** after transition

### From Plain to Encrypted Passwords

1. **Generate Fernet key**
2. **Encrypt existing passwords**
3. **Update YAML** configurations
4. **Deploy changes**
5. **Verify authentication**

### To Dual Authentication

1. **Identify critical users** (admins, emergency)
2. **Add second auth method**
3. **Test both methods**
4. **Document access procedures**
5. **Train users** on dual auth

## Summary

SnowTower's authentication system provides:

- **Maximum Security**: RSA keys for all programmatic access
- **Flexibility**: Multiple authentication methods
- **Compliance**: MFA-ready for 2026 mandate
- **Emergency Access**: Carefully planned recovery procedures
- **Best Practices**: Industry-standard security patterns

Follow the authentication method appropriate for your user type and always prioritize security over convenience.

---

**Version**: 3.0 | **Last Updated**: 2025-10-01 | **Status**: Production Ready ✅
