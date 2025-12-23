# SnowTower User Management - Quick Reference Card

## 🚀 5-Minute User Creation

### Option A: Streamlit Web UI
```bash
1. Open: https://<account>.snowflakecomputing.com/streamlit-apps/snowtower_streamlit
2. Go to "🏗️ Generate Config" → Select "User"
3. Fill: Username, Email, Type (PERSON/SERVICE)
4. Auth: Click "🎲 Generate Password" and/or paste RSA key
5. Deploy: Click "🚀 Generate & Deploy"
6. COPY PASSWORD NOW! (shown only once)
```

### Option B: CLI Interactive
```bash
# Interactive wizard (easiest)
uv run user-onboard --wizard

# Quick mode with defaults
uv run user-onboard --quick --name JOHN_DOE --email john@company.com
```

### Option C: CLI Non-Interactive
```bash
uv run user-onboard \
  --name JOHN_DOE \
  --email john.doe@company.com \
  --type PERSON \
  --auth-method dual \
  --generate-rsa \
  --generate-password \
  --auto-save
```

## 📋 Required Fields Checklist

- [ ] **Username**: UPPERCASE_WITH_UNDERSCORES
- [ ] **Email**: user@domain.com
- [ ] **Type**: PERSON or SERVICE
- [ ] **Auth Method**: RSA key OR password (or both)
- [ ] **Business Roles**: Can be empty list []
- [ ] **Default Warehouse**: COMPUTE_WH or MAIN_WAREHOUSE

## 🔐 Authentication Quick Guide

| User Type | Recommended Auth | Why |
|-----------|-----------------|-----|
| **PERSON (Admin)** | Dual (RSA + Password) | Prevents lockout, maximum flexibility |
| **PERSON (Regular)** | RSA Key | More secure than passwords |
| **SERVICE** | RSA Key ONLY | Never use passwords for automation |
| **EMERGENCY** | Password Only, No Network Policy | Access from anywhere in crisis |

### Generate RSA Keys
```bash
# Standard 2048-bit
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out ~/.ssh/snowflake_rsa_key.p8
openssl rsa -in ~/.ssh/snowflake_rsa_key.p8 -pubout -out ~/.ssh/snowflake_rsa_key.pub
chmod 400 ~/.ssh/snowflake_rsa_key.p8
```

### Encrypt Password
```bash
# Interactive (secure)
uv run python src/encrypt_password.py --interactive

# Generate new Fernet key if needed
uv run util-generate-key
```

## 🎯 Common User Templates

### Data Analyst
```yaml
Type: PERSON
Auth: Password + RSA Key
Roles: COMPANY_USERS
Network Policy: company_network_policy
Must Change Password: Yes
```

### Service Account
```yaml
Type: SERVICE
Auth: RSA Key ONLY (no password!)
Roles: SERVICE_ACCOUNTS_ROLE
Network Policy: None
```

### Admin User
```yaml
Type: PERSON
Auth: Dual (RSA + Password)
Roles: ADMIN_ROLE
Network Policy: company_network_policy
Must Change Password: No (emergency access)
```

## 🚢 Deployment Commands

```bash
# Preview changes
uv run snowddl-plan

# Apply to Snowflake
uv run snowddl-apply

# Apply with policies
uv run snowddl-apply --apply-unsafe --apply-network-policy

# Verify user
uv run show users --filter "name=JOHN_DOE"
```

## 🔄 Git Sync Process

### From Streamlit to Git
```bash
# Download from S3
aws s3 cp s3://bucket/yaml-configs/user_*.yaml ./snowddl/

# Add to user.yaml
# Merge the user configuration into snowddl/user.yaml

# Commit
git add snowddl/user.yaml
git commit -m "Add user via Streamlit"
git push
```

## 🐛 Quick Troubleshooting

| Issue | Fix |
|-------|-----|
| **"Encryption key not configured"** | `export SNOWFLAKE_CONFIG_FERNET_KEYS="<key>"` |
| **"Authentication failed"** | Check username case, RSA key path |
| **"Network policy violation"** | Your IP not in allowlist |
| **"Password not shown"** | One-time display, generate new one |
| **"YAML parse error"** | Check required fields: type, email |

## 🛠️ Essential Commands

```bash
# User Management
uv run user-onboard --wizard              # Interactive creation
uv run generate-password USER1            # Generate password
uv run regenerate-password USER1          # Update password
uv run user-manage user validate USER1    # Validate config

# Testing & Diagnostics
uv run util-diagnose-auth                 # Test authentication
uv run snowddl-plan --dry-run            # Validate YAML
uv run python tests/test_*.py            # Run tests

# Deployment
uv run snowddl-plan                      # Preview changes
uv run snowddl-apply                     # Deploy to Snowflake
uv run show users                        # List all users
```

## 🏃 Speed Run: New User in 2 Minutes

1. **Generate credentials** (30 sec):
   ```bash
   uv run user-onboard --quick --name USER1 --email user1@company.com
   ```

2. **Review YAML** (15 sec):
   ```bash
   cat snowddl/user.yaml | grep -A 20 USER1
   ```

3. **Deploy** (45 sec):
   ```bash
   uv run snowddl-plan && uv run snowddl-apply
   ```

4. **Verify** (30 sec):
   ```bash
   uv run show users --filter "name=USER1"
   ```

## 📞 Help & Support

- **Full Guide**: `/docs/user-management/USER_CREATION_GUIDE.md`
- **Auth Details**: `/docs/user-management/AUTHENTICATION_GUIDE.md`
- **Owner**: Alice Admin (admin@example.com)

## ⚡ Pro Tips

1. **Always use `--wizard` for first-time users**
2. **Copy passwords immediately after generation**
3. **Use dual auth for admin accounts**
4. **Never use passwords for service accounts**
5. **Test with `--dry-run` before applying**
6. **Keep Fernet key backed up securely**
7. **Rotate RSA keys quarterly for services**

---

**Version**: 3.0 | **Updated**: 2025-10-01 | **Status**: Production Ready ✅
