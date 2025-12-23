# Troubleshooting Guide

Common issues and solutions for SnowTower SnowDDL.

---

## 🔐 Authentication Issues

### Error: "Connection failed" or "Authentication failed"

**Symptom**: Cannot connect to Snowflake when running commands.

**Causes & Solutions**:

1. **RSA Key Issues**:
   ```bash
   # Verify RSA key path is correct
   ls -la ~/.ssh/snowddl_rsa_key.p8

   # Check permissions (should be 400)
   chmod 400 ~/.ssh/snowddl_rsa_key.p8

   # Verify public key is added to Snowflake user
   cat ~/.ssh/snowddl_rsa_key.pub
   # Then in Snowflake: ALTER USER <username> SET RSA_PUBLIC_KEY='<paste_key>';
   ```

2. **Environment Variables Not Loaded**:
   ```bash
   # Verify .env file exists
   cat .env | grep SNOWFLAKE_ACCOUNT

   # Ensure commands use uv run (loads .env automatically)
   uv run snowddl-plan  # ✅ Correct
   snowddl plan         # ❌ Won't load .env
   ```

3. **Wrong Account Identifier**:
   ```bash
   # WRONG: Include .snowflakecomputing.com
   SNOWFLAKE_ACCOUNT=YOUR_ACCOUNT.snowflakecomputing.com

   # CORRECT: Account ID only
   SNOWFLAKE_ACCOUNT=YOUR_ACCOUNT
   ```

---

## ⚠️ Permission Errors

### Error: "Insufficient privileges" or "Access denied"

**Symptom**: Commands fail with permission errors.

**Solution**:
```bash
# SnowDDL needs ACCOUNTADMIN or equivalent
# Update .env:
SNOWFLAKE_ROLE=ACCOUNTADMIN

# Or grant necessary privileges (contact Snowflake admin)
```

**Why ACCOUNTADMIN?**: SnowDDL needs to read all objects for proper infrastructure discovery.

---

## 🔑 Fernet Encryption Issues

### Error: "Invalid Fernet key" or "Decryption failed"

**Symptom**: Cannot decrypt passwords in YAML files.

**Solutions**:

1. **Generate New Key**:
   ```bash
   uv run util-generate-key
   # Copy output to SNOWFLAKE_CONFIG_FERNET_KEYS in .env
   ```

2. **Re-encrypt Passwords**:
   ```bash
   # If you changed the Fernet key, re-encrypt all passwords
   uv run user-update-password <username>
   ```

3. **Key Mismatch**:
   - Ensure `.env` Fernet key matches the key used to encrypt passwords in YAML
   - Check `snowddl/user.yaml` for `encrypted_password` values
   - All must be encrypted with the same key

---

## 📦 SnowDDL Plan/Apply Issues

### Error: "Plan shows unexpected changes"

**Symptom**: `snowddl-plan` shows DROP operations or unexpected modifications.

**Diagnosis**:
```bash
# Check what SnowDDL sees
uv run snowddl-plan --show-debug

# Compare with actual Snowflake state
# (requires Snowflake access)
```

**Common Causes**:
1. **Manual changes in Snowflake**: Someone modified objects outside SnowDDL
2. **Missing YAML definitions**: Object exists in Snowflake but not in YAML
3. **Name case mismatch**: Snowflake uppercases names by default

**Solution**:
```bash
# Option 1: Add missing definitions to YAML
# Edit appropriate snowddl/*.yaml file

# Option 2: Remove object from Snowflake (if truly unwanted)
# snowddl-apply will handle the DROP
```

### Error: "Apply failed with network policy error"

**Symptom**: `snowddl-apply` fails when deploying network policies.

**Solution**:
```bash
# Use correct flags for policy changes
uv run snowddl-apply --apply-network-policy --apply-all-policy

# Or use intelligent apply (auto-detects flags)
uv run snowddl-apply  # Analyzes plan output and adds needed flags
```

---

## 👤 User Management Issues

### Error: "User creation failed"

**Symptom**: `user-create` command fails or user not appearing in Snowflake.

**Checklist**:
1. **YAML file created?**
   ```bash
   # Check if user was added to snowddl/user.yaml
   grep -A 10 "login_name: NEWUSER" snowddl/user.yaml
   ```

2. **Plan and apply run?**
   ```bash
   uv run snowddl-plan   # Should show CREATE USER
   uv run snowddl-apply  # Actually creates the user
   ```

3. **Password encrypted?**
   ```bash
   # Verify encrypted_password field exists
   # Format: gAAAAA... (starts with gAAAAA)
   ```

### Error: "User cannot login"

**Symptom**: User created but cannot authenticate.

**Solutions**:

1. **RSA Key Not Added**:
   ```bash
   # User needs to provide their public key
   # Then admin runs:
   uv run user-update-rsa <username> /path/to/user_rsa_key.pub
   ```

2. **Wrong Password**:
   ```bash
   # Reset password
   uv run user-update-password <username>
   ```

3. **Network Policy Blocking**:
   ```bash
   # Check if user's IP is allowed
   # Edit snowddl/network_policy.yaml
   # Add user's IP to allowed_ip_list
   ```

---

## 🗄️ Database & Schema Issues

### Error: "Database not found" in SnowDDL plan

**Symptom**: SnowDDL plan references database that doesn't exist.

**Solution**:
```bash
# Check database definitions
ls -la snowddl/database.yaml

# Verify database exists in Snowflake
# or add to YAML if intended to be created
```

### Error: "Schema parameter changes showing every time"

**Symptom**: `snowddl-plan` always shows schema parameter changes even when nothing changed.

**Cause**: Parameter drift between Snowflake and SnowDDL definitions.

**Solution**:
```bash
# Update params.yaml to match current Snowflake state
# In snowddl/{DATABASE}/params.yaml
```

---

## 🌐 Streamlit Deployment Issues

### Error: "Streamlit app not accessible"

**Symptom**: Deployed Streamlit app shows "This app can't be reached".

**Solution**:
```bash
# Ensure using stage-based deployment (not native app)
# Check snowflake_app/deploy.py

# Verify stage exists
# In Snowflake: LIST @SNOWTOWER_DEPLOYMENT_STAGE;
```

### Error: "Configuration table not found" in Streamlit

**Symptom**: Streamlit app fails to load configuration.

**Solution**:
```sql
-- Create configuration schema and table manually
CREATE SCHEMA IF NOT EXISTS SNOWTOWER_CONFIG;
CREATE TABLE IF NOT EXISTS SNOWTOWER_CONFIG.APP_CONFIG (
    config_key VARCHAR,
    config_value VARIANT,
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

---

## 🔧 UV & Dependency Issues

### Error: "uv: command not found"

**Symptom**: Cannot run `uv` commands.

**Solution**:
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal or source:
source ~/.bashrc  # or ~/.zshrc
```

### Error: "Module not found" when running commands

**Symptom**: Python import errors when running `uv run` commands.

**Solution**:
```bash
# Reinstall dependencies
uv sync

# If still failing, clear cache and reinstall
rm -rf .venv
uv sync
```

---

## 🔍 Diagnostic Commands

### Check System Health
```bash
# Verify Snowflake connection
uv run snowddl-plan

# Check authentication method
cat .env | grep SNOWFLAKE_PRIVATE_KEY_PATH  # RSA key
cat .env | grep SNOWFLAKE_PASSWORD          # Password (fallback)

# List all users
uv run users report --format table

# Verify installed dependencies
uv pip list
```

### Debug SnowDDL
```bash
# Verbose SnowDDL output
uv run snowddl-plan --config-path ./snowddl --debug

# Check SnowDDL version
uv pip show snowddl
```

### Verify Environment
```bash
# Check required files exist
ls -la .env snowddl/ scripts/

# Verify git status
git status
git log --oneline -5

# Check Python version (requires 3.10+)
python --version
```

---

## 🆘 Getting Help

### Before Creating an Issue

1. **Check logs**:
   ```bash
   # SnowDDL logs
   uv run snowddl-plan 2>&1 | tee snowddl.log

   # UV logs
   uv run --verbose <command>
   ```

2. **Verify setup**:
   ```bash
   # Run setup validation
   uv run snowddl-validate
   ```

3. **Search existing issues**:
   - Check GitHub Issues for similar problems

### Creating an Issue

Include this information:
```
- **Error message**: (full error output)
- **Command run**: (exact command that failed)
- **Environment**:
  - OS: (macOS/Linux/Windows)
  - Python version: (python --version)
  - UV version: (uv --version)
  - SnowDDL version: (uv pip show snowddl)
- **Steps to reproduce**:
  1. ...
  2. ...
- **Expected behavior**: (what should happen)
- **Actual behavior**: (what actually happened)
```

### Contact

- **GitHub Issues**: https://github.com/Database-Tycoon/snowtower/issues
- **Email**: admin@example.com
- **Documentation**: See README.md and docs/ directory

---

## 📋 Common Error Reference

| Error | Likely Cause | Quick Fix |
|-------|--------------|-----------|
| `Connection failed` | Wrong credentials/RSA key | Check `.env` file, verify RSA key permissions |
| `Insufficient privileges` | Not ACCOUNTADMIN | Set `SNOWFLAKE_ROLE=ACCOUNTADMIN` in `.env` |
| `Invalid Fernet key` | Wrong encryption key | Regenerate with `uv run util-generate-key` |
| `Module not found` | Missing dependencies | Run `uv sync` |
| `uv: command not found` | UV not installed | Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `Network policy error` | Wrong apply flags | Use `--apply-network-policy --apply-all-policy` |
| `User cannot login` | RSA key or network policy | Add RSA key, check IP allowlist |
| `Database not found` | Missing YAML definition | Add to `snowddl/database.yaml` |

---

**Last Updated**: October 1, 2025
**Version**: 1.0.0
