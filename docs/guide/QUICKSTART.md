# ⚡ SnowTower SnowDDL - 5-Minute Quickstart

Get up and running with SnowTower SnowDDL in less than 5 minutes!

---

## 📋 Prerequisites

Before you begin, ensure you have:

- ✅ **Python 3.10+** installed
- ✅ **Snowflake account** with credentials
- ✅ **Terminal/command line** access
- ✅ **Git** installed (optional, for cloning)

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Install UV Package Manager (30 seconds)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.sh | iex"
```

**Verify installation**:
```bash
uv --version
```

---

### Step 2: Clone & Setup Project (1 minute)

```bash
# Clone the repository
git clone <your-repo-url>
cd snowtower-snowddl

# Install all dependencies
uv sync
```

**What this does**: Installs 100+ dependencies including SnowDDL, Snowflake connector, and all management tools.

---

### Step 3: Configure Authentication (2 minutes)

#### Option A: RSA Key Authentication (Recommended)

Generate your RSA key pair:

```bash
# Generate private key (PKCS#8 format required by Snowflake)
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -nocrypt -out ~/.ssh/snowflake_rsa_key.p8

# Generate public key
openssl rsa -in ~/.ssh/snowflake_rsa_key.p8 -pubout -out ~/.ssh/snowflake_rsa_key.pub

# Secure your private key
chmod 400 ~/.ssh/snowflake_rsa_key.p8
```

**Add public key to Snowflake**:
```sql
-- Copy the output of this command:
cat ~/.ssh/snowflake_rsa_key.pub

-- Then in Snowflake, run:
ALTER USER <your_username> SET RSA_PUBLIC_KEY='<paste_public_key_here>';
```

#### Option B: Password Authentication (Quick Testing)

For quick testing, you can use password authentication (less secure).

---

### Step 4: Create Environment File (1 minute)

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or: vim .env, code .env, etc.
```

**Minimal configuration** (required fields only):

```bash
# Snowflake Connection
SNOWFLAKE_ACCOUNT=your_account_id        # e.g., ABC12345
SNOWFLAKE_USER=your_username             # Your Snowflake username
SNOWFLAKE_ROLE=ACCOUNTADMIN              # Or your role with sufficient permissions

# Authentication Method (choose one)
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/snowflake_rsa_key.p8  # If using RSA
# SNOWFLAKE_PASSWORD=your_password       # If using password (not recommended)

# Encryption Key (generate below)
SNOWFLAKE_CONFIG_FERNET_KEYS=<generated_key>
```

**Generate Fernet encryption key**:
```bash
uv run util-generate-key
```

Copy the output and paste it into `SNOWFLAKE_CONFIG_FERNET_KEYS` in your `.env` file.

---

### Step 5: Test Your Connection (30 seconds)

```bash
# Validate your configuration
uv run snowddl-validate

# Preview current infrastructure (safe, read-only)
uv run snowddl-plan
```

**Expected output**:
```
✅ Configuration validation passed!
📋 SnowDDL Plan Output: [shows your current Snowflake infrastructure]
```

---

## 🎉 You're Ready!

### What You Can Do Now

#### View Infrastructure
```bash
# See all users
uv run manage-users report --format table

# See warehouses
uv run manage-warehouses list

# Cost analysis
uv run manage-costs analyze
```

#### Create a New User
```bash
# Interactive wizard
uv run user-create

# Follow the prompts, then deploy:
uv run snowddl-plan      # Review changes
uv run snowddl-apply     # Apply to Snowflake
```

#### Access Web Interface

**Option 1: Local Streamlit (Development)**
```bash
# Launch local Streamlit dashboard
uv run web

# Opens at http://localhost:8501
```

**Option 2: Deploy to Snowflake (Production)**
```bash
# Deploy the Streamlit app to Snowflake
cd snowflake_app/
uv run python deploy.py

# Then access via Snowflake:
# 1. Log into https://app.snowflake.com
# 2. Click "Streamlit" in left sidebar
# 3. Find and click "SNOWTOWER_APP"
```

**App Location in Snowflake**:
- **Database**: `SNOWTOWER_APPS`
- **Schema**: `PUBLIC`
- **App Name**: `SNOWTOWER_APP`

---

## 🆘 Troubleshooting

### Issue: "Connection failed"

**Check your credentials**:
```bash
# Verify environment variables are loaded
cat .env | grep SNOWFLAKE_ACCOUNT

# Test with Snow CLI (if installed)
snow connection test
```

**Common fixes**:
- Ensure `SNOWFLAKE_ACCOUNT` doesn't include `.snowflakecomputing.com`
- If using RSA keys, verify the public key is added to your Snowflake user
- Check file permissions: `ls -la ~/.ssh/snowflake_rsa_key.p8` (should be 400)

### Issue: "ACCOUNTADMIN role required"

SnowDDL needs elevated permissions to manage infrastructure.

**Fix**:
```bash
# Option 1: Use ACCOUNTADMIN role
SNOWFLAKE_ROLE=ACCOUNTADMIN

# Option 2: Grant necessary privileges to your role
# (Contact your Snowflake admin)
```

### Issue: "Missing Fernet key"

**Generate a new key**:
```bash
uv run util-generate-key
```

Add the output to your `.env` file as `SNOWFLAKE_CONFIG_FERNET_KEYS`.

### Issue: "UV command not found"

**Install UV**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart your terminal or:
source ~/.bashrc  # or ~/.zshrc
```

---

## 📚 Next Steps

Now that you're set up, explore these guides:

### For End Users (Requesting Access)
📖 **[docs/NEW_USER_GUIDE.md](docs/NEW_USER_GUIDE.md)** - How to request Snowflake access via GitHub issues

### For Administrators
📖 **[README.md](README.md)** - Complete administrator guide (670 lines)
📖 **[docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md)** - Safe deployment procedures
📖 **[docs/MANAGEMENT_COMMANDS.md](docs/MANAGEMENT_COMMANDS.md)** - All available commands reference

### For Developers
📖 **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute (coming soon)
📖 **[site_docs/api/](site_docs/api/)** - Python API documentation

---

## 🔐 Security Best Practices

Before deploying to production:

1. **✅ Use RSA key authentication** (not passwords)
2. **✅ Never commit `.env` files** (already in `.gitignore`)
3. **✅ Rotate Fernet keys** periodically (quarterly recommended)
4. **✅ Use separate credentials** for dev/staging/production
5. **✅ Enable MFA** on your Snowflake account

---

## 💡 Common Commands Cheat Sheet

```bash
# Infrastructure Management
uv run snowddl-validate     # Check YAML syntax
uv run snowddl-plan         # Preview changes (SAFE)
uv run snowddl-apply        # Deploy changes (DESTRUCTIVE)

# User Management
uv run user-create          # Create new user (interactive)
uv run manage-users report  # List all users

# Resource Management
uv run manage-warehouses optimize    # Optimize warehouse configs
uv run manage-costs analyze         # Cost analysis
uv run manage-security audit        # Security audit

# Monitoring
uv run monitor-health       # System health check
uv run monitor-logs         # View logs

# Web Interface
uv run web                  # Launch Streamlit dashboard
```

---

## 🤔 Still Stuck?

### Get Help

1. **Check existing documentation**: See the [docs/](docs/) directory
2. **Search issues**: Check [GitHub Issues](../../issues) for similar problems
3. **Ask for help**: Create a new issue with the `question` label

### Detailed Troubleshooting

For comprehensive troubleshooting, see:
- 📖 **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** (coming soon)
- 📖 **README.md** - Troubleshooting section

---

## ⏱️ Time Breakdown

- **Install UV**: 30 seconds
- **Clone & Install Dependencies**: 1 minute
- **Generate RSA Keys**: 1 minute
- **Configure .env**: 1 minute
- **Test Connection**: 30 seconds
- **First Deployment**: 1 minute

**Total**: ~5 minutes to first successful deployment! 🎉

---

## 📞 Support

**Email**: admin@example.com
**GitHub Issues**: [Report a bug or request a feature](../../issues)
**Documentation**: [Complete README](README.md)

---

**Last Updated**: October 1, 2025
**Version**: 1.0.0
**Status**: ✅ Production Ready
