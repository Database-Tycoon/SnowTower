---
name: snowtower-user
description: Helps end-users get Snowflake access and use the platform. Use when users ask about requesting access, generating RSA keys, connecting to Snowflake, or basic Snowflake usage. Triggers on mentions of access requests, RSA keys, connection issues, or "how do I get access".
---

# SnowTower End-User Guide

Assumes CLAUDE.md is loaded for project context.

## Getting Access (3 Steps)

### Step 1: Generate RSA Keys

```bash
# Generate key pair
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out ~/.ssh/snowflake_rsa_key.p8
openssl rsa -in ~/.ssh/snowflake_rsa_key.p8 -pubout -out ~/.ssh/snowflake_rsa_key.pub

# Secure private key
chmod 400 ~/.ssh/snowflake_rsa_key.p8

# Copy public key for access request
cat ~/.ssh/snowflake_rsa_key.pub
```

**Private key** (`~/.ssh/snowflake_rsa_key.p8`) - NEVER share. **Public key** (`.pub`) - safe to share.

### Step 2: Submit Access Request

1. Go to the [Access Request Form](../../issues/new/choose)
2. Select "New User Request"
3. Fill in: name, email, team, reason, **paste public key**
4. Typical approval: 3-5 business days

### Step 3: Connect to Snowflake

**Snow CLI (recommended):**
```bash
snow connection add \
  --connection-name prod \
  --account YOUR_ACCOUNT \
  --user YOUR_USERNAME \
  --authenticator SNOWFLAKE_JWT \
  --private-key-path ~/.ssh/snowflake_rsa_key.p8

snow sql -c prod -q "SELECT CURRENT_USER(), CURRENT_ROLE()"
```

**Python:**
```python
import snowflake.connector
conn = snowflake.connector.connect(
    account='YOUR_ACCOUNT',
    user='YOUR_USERNAME',
    private_key_file='~/.ssh/snowflake_rsa_key.p8',
    warehouse='MAIN_WAREHOUSE',
    role='YOUR_ROLE'
)
```

## First Session Checklist

```sql
SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE();
SHOW DATABASES;
SHOW ROLES;
USE DATABASE DEV_YOURNAME;
CREATE SCHEMA IF NOT EXISTS sandbox;
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Authentication failed | Check key permissions: `chmod 400 ~/.ssh/snowflake_rsa_key.p8` |
| Insufficient privileges | Verify role: `SELECT CURRENT_ROLE();` - request more access via GitHub issue |
| Cannot connect | Check: account approved? Account ID correct? Key path correct? On VPN? |

## Getting More Access

Open a GitHub issue specifying what you need and business justification.
