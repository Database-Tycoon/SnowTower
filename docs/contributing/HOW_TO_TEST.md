# How to Test SnowTower SnowDDL

Complete testing guide for the Streamlit app and all functionality.

---

## 🎯 Quick Access: Run the Streamlit App

### Method 1: Local Development (Fastest)

```bash
# From project root
uv run web

# App opens at: http://localhost:8501
```

**What it does**: Runs Streamlit locally on your machine, connects to Snowflake using credentials from `.env`

### Method 2: Deploy to Snowflake (Production)

```bash
# Navigate to Snowflake app directory
cd snowflake_app/

# Deploy to Snowflake
uv run python deploy.py

# Access the deployed app:
# 1. Go to https://app.snowflake.com
# 2. Click "Streamlit" in left sidebar
# 3. Find "SNOWTOWER_APP" and click it
```

**What it does**: Deploys app to Snowflake's native Streamlit environment

**App Details**:
- **Database**: `SNOWTOWER_APPS`
- **Schema**: `PUBLIC`
- **App Name**: `SNOWTOWER_APP`

---

## 🧪 Testing the Application

### 1. Test User Interface

```bash
# Start local app
uv run web
```

**Test checklist**:
- [ ] App loads without errors
- [ ] Can see SnowTower branding/title
- [ ] Configuration sections render
- [ ] User management interface visible
- [ ] Cost analysis features work
- [ ] Warehouse management accessible

### 2. Test User Creation Workflow

**Via Streamlit**:
1. Open app: `uv run web`
2. Navigate to "User Management" section
3. Click "Create New User"
4. Fill in user details
5. Submit form
6. Verify YAML file updated in `snowddl/user.yaml`

**Via CLI**:
```bash
# Interactive user creation wizard
uv run user-create

# Follow prompts, then check:
cat snowddl/user.yaml | grep -A 10 "NEWUSER"
```

### 3. Test Infrastructure Management

```bash
# View current infrastructure state
uv run snowddl-plan

# Expected: Shows current Snowflake infrastructure
# Should NOT show unexpected DROPs or changes
```

### 4. Test Security Features

```bash
# Test pre-commit hooks
uv run pre-commit run --all-files

# Expected: All checks pass
# SQL injection patterns blocked
# No secrets detected
```

### 5. Test Connection & Authentication

```bash
# Validate configuration
uv run snowddl-validate

# Expected: "✅ Configuration validation passed!"

# Test Snowflake connection
uv run snowddl-plan

# Expected: Successfully connects and shows plan output
```

---

## 📊 Testing Different Features

### Cost Analysis
```bash
# Run cost analysis
uv run manage-costs analyze

# Expected: Shows warehouse costs, recommendations
```

### Warehouse Management
```bash
# List warehouses
uv run manage-warehouses list

# Expected: Shows all warehouses with status
```

### Security Audit
```bash
# Run security audit
uv run manage-security audit

# Expected: Shows MFA compliance, network policies
```

### User Reporting
```bash
# Generate user report
uv run manage-users report --format table

# Expected: Table of all users with roles
```

---

## 🔍 Verification Checklist

### After Local Testing
- [ ] Streamlit app runs without errors (`uv run web`)
- [ ] Can navigate all sections of the app
- [ ] User creation workflow completes successfully
- [ ] YAML files update correctly when changes made
- [ ] No sensitive data exposed in logs or UI

### After Snowflake Deployment
- [ ] Deployment completes successfully
- [ ] Can access app via Snowflake web UI
- [ ] App has necessary permissions
- [ ] Configuration persists between sessions
- [ ] S3 integration works (if configured)

### Security Verification
- [ ] No passwords in `.env` file (should use RSA keys)
- [ ] `.env` not tracked in Git
- [ ] Pre-commit hooks installed and working
- [ ] SQL injection protections in place (IDENTIFIER() used)
- [ ] Repository is private on GitHub

---

## 🐛 Common Issues & Solutions

### Issue: "Streamlit app won't start locally"

**Solution**:
```bash
# Reinstall dependencies
uv sync

# Check if app file exists
ls -la src/web/app.py

# Try again
uv run web
```

### Issue: "Snowflake deployment fails"

**Check**:
```bash
# Verify Snow CLI installed
snow --version

# Check you're in correct directory
cd snowflake_app/
pwd

# Verify required files
ls -la streamlit_app.py environment.yml
```

**Solution**:
```bash
# Install Snow CLI if missing
uv pip install snowflake-cli-labs

# Retry deployment
uv run python deploy.py
```

### Issue: "Cannot connect to Snowflake"

**Solution**:
```bash
# Check .env configuration
cat .env | grep SNOWFLAKE_ACCOUNT
cat .env | grep SNOWFLAKE_USER
cat .env | grep SNOWFLAKE_ROLE

# Verify RSA key exists and has correct permissions
ls -la ~/.ssh/snowddl_rsa_key.p8
chmod 400 ~/.ssh/snowddl_rsa_key.p8

# Test connection
uv run snowddl-validate
```

### Issue: "App shows 'Configuration table not found'"

**Solution** (in Snowflake SQL):
```sql
-- Create configuration schema and table
CREATE SCHEMA IF NOT EXISTS SNOWTOWER_CONFIG;
CREATE TABLE IF NOT EXISTS SNOWTOWER_CONFIG.APP_CONFIG (
    config_key VARCHAR,
    config_value VARIANT,
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

---

## 📝 Test Scenarios

### Scenario 1: New User Onboarding
1. User submits GitHub issue requesting access
2. Admin uses Streamlit app to create user
3. YAML file updates automatically
4. Admin runs `uv run snowddl-plan` to review
5. Admin runs `uv run snowddl-apply` to deploy
6. User receives credentials and can login

### Scenario 2: Cost Optimization
1. Admin opens Streamlit app
2. Navigates to "Cost Analysis" section
3. Reviews warehouse usage patterns
4. Identifies underutilized warehouses
5. Adjusts warehouse sizes via interface
6. Changes committed to YAML
7. `snowddl-apply` deploys changes

### Scenario 3: Security Audit
1. Admin runs `uv run manage-security audit`
2. Reviews MFA compliance status
3. Checks network policy assignments
4. Identifies users without MFA
5. Uses Streamlit app to update user configurations
6. Re-runs audit to confirm improvements

---

## 🎯 Success Criteria

Your deployment is ready for production when:

- [ ] ✅ Streamlit app runs locally without errors
- [ ] ✅ App deploys to Snowflake successfully
- [ ] ✅ User creation workflow works end-to-end
- [ ] ✅ All security fixes applied (SQL injection, credentials)
- [ ] ✅ Pre-commit hooks prevent future security issues
- [ ] ✅ Documentation complete (QUICKSTART, TROUBLESHOOTING)
- [ ] ✅ Repository is private (protecting PII)
- [ ] ✅ Connection to Snowflake works with RSA keys
- [ ] ✅ SnowDDL plan/apply workflow functions correctly

---

## 🚀 Ready to Deploy?

### Pre-deployment Checklist
```bash
# 1. Verify all tests pass
uv run pre-commit run --all-files

# 2. Validate configuration
uv run snowddl-validate

# 3. Preview changes
uv run snowddl-plan

# 4. Test local app
uv run web
# (Check all features work)

# 5. Deploy to Snowflake
cd snowflake_app/
uv run python deploy.py
```

### Post-deployment Verification
1. Access app in Snowflake web UI
2. Test user creation workflow
3. Verify configuration persists
4. Check permissions work correctly
5. Confirm no errors in Snowflake logs

---

## 📞 Need Help?

- **Documentation**: See QUICKSTART.md, TROUBLESHOOTING.md, README.md
- **Issues**: https://github.com/Database-Tycoon/snowtower/issues
- **Email**: admin@example.com

---

**Last Updated**: October 1, 2025
**Status**: ✅ Ready for Testing
