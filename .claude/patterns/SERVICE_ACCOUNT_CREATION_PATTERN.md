# SnowDDL Service Account Creation Pattern

**CRITICAL PATTERN**: This document describes the complete, standardized process for creating BI platform service accounts in SnowTower SnowDDL. This pattern MUST be followed for all new service account integrations (Tableau, PowerBI, Looker, Metabase, etc.).

## Pattern Overview

Every BI/service integration requires **6 configuration files** + **RSA key generation** + **secrets baseline update**.

**Reference Implementation**: LightDash service account (commit: cce2026)
- Located in: `feature/lightdash-service-account` branch
- Security Review: 100% compliance (8/8 checks passed)
- Pattern Matches: ANALYTICS_TOOL service account (gold standard for BI integrations)

---

## 🎯 Complete Workflow (Step-by-Step)

### Phase 1: Research & Planning

1. **Research Service IP Addresses**
   - Search for `[service name] IP addresses allowlist documentation`
   - Look for official documentation on network requirements
   - Document both US and international region IPs
   - Verify IPs are for cloud-hosted service (not self-hosted)

2. **Determine Access Requirements**
   - Which databases need read access? (usually: SOURCE_*, PROJ_*)
   - Which database needs write access? (usually: dedicated database)
   - Special permissions needed? (CREATE SCHEMA, TRUNCATE, etc.)

3. **Create Feature Branch**
   ```bash
   git checkout -b feature/[service-name]-service-account
   ```

---

### Phase 2: Configuration Creation (6 Files)

#### **File 1: Network Policy** (`snowddl/network_policy.yaml`)

**Template**:
```yaml
[service_name]_network_policy:
  allowed_ip_list:
    - [IP_ADDRESS_1]/32    # Region 1 (e.g., US)
    - [IP_ADDRESS_2]/32    # Region 2 (e.g., EU)
  comment: Restrict [Service Name] platform service account to approved [Service Name] IP addresses
```

**Placement**: Add alphabetically between existing policies

**Critical Rules**:
- Always use `/32` CIDR masks (single IP)
- Include descriptive comments with region info
- List all regional IPs (US, EU, APAC as applicable)

**Example** (LightDash):
```yaml
bi_tool_network_policy:
  allowed_ip_list:
    - 198.51.100.1/32    # US region (app.lightdash.cloud)
    - 198.51.100.2/32    # EU region (eu1.lightdash.cloud)
  comment: Restrict LightDash BI platform service account to approved LightDash IP addresses (US and EU regions)
```

---

#### **File 2: Warehouse** (`snowddl/warehouse.yaml`)

**Template**:
```yaml
[SERVICE_NAME]:
  auto_suspend: 60
  comment: [Service Name] platform warehouse for analytics and dashboard queries
  size: X-Small
```

**Placement**: Add alphabetically between existing warehouses

**Critical Rules**:
- Warehouse name: ALL CAPS, matches service name
- Always use `auto_suspend: 60` (1 minute)
- Always start with `size: X-Small` (can scale up later)
- Comment should mention "analytics" or "dashboard" or "BI"

**Example** (LightDash):
```yaml
BI_TOOL:
  auto_suspend: 60
  comment: LightDash BI platform warehouse for analytics and dashboard queries
  size: X-Small
```

---

#### **File 3: Technical Role** (`snowddl/tech_role.yaml`)

**Template**:
```yaml
[SERVICE_NAME]_TECH_ROLE:
  comment: [Service Name] technical role - Read access to source data, full read/write access to [SERVICE_NAME] database
  future_grants:
    TABLE:SELECT:
      - [SOURCE_DATABASE_1]
      - [SOURCE_DATABASE_2]
    TABLE:SELECT,INSERT,UPDATE,DELETE,TRUNCATE:
      - [SERVICE_DATABASE]
    VIEW:SELECT:
      - [SOURCE_DATABASE_1]
      - [SOURCE_DATABASE_2]
      - [SERVICE_DATABASE]
  grants:
    DATABASE:USAGE:
      - [SOURCE_DATABASE_1]
      - [SOURCE_DATABASE_2]
    DATABASE:USAGE,CREATE SCHEMA:
      - [SERVICE_DATABASE]
    WAREHOUSE:USAGE:
      - [SERVICE_WAREHOUSE]
```

**Placement**: Add alphabetically between existing tech roles

**Critical Rules**:
- **Least Privilege**: Only grant what's needed
- **Read-Only Sources**: Source databases get `SELECT` only
- **Write to Own DB**: Service database gets full permissions
- **Future Grants**: ALWAYS include for inheritance
- **CREATE SCHEMA**: Only on service's own database
- **Single Warehouse**: Only grant usage on service's warehouse

**Permission Decision Tree**:
```
Does service need to:
  - Read existing data? → DATABASE:USAGE + TABLE:SELECT + VIEW:SELECT
  - Create dashboards/materialized views? → DATABASE:USAGE,CREATE SCHEMA on own DB
  - Refresh data? → TABLE:INSERT,UPDATE,DELETE,TRUNCATE on own DB
  - Delete all data? → Consider if TRUNCATE is needed
```

**Example** (LightDash):
```yaml
LIGHTDASH_TECH_ROLE:
  comment: LightDash BI platform technical role - Read access to source data, full read/write access to BI_TOOL database
  future_grants:
    TABLE:SELECT:
      - PROJ_STRIPE
      - SOURCE_STRIPE
    TABLE:SELECT,INSERT,UPDATE,DELETE,TRUNCATE:
      - BI_TOOL
    VIEW:SELECT:
      - PROJ_STRIPE
      - SOURCE_STRIPE
      - BI_TOOL
  grants:
    DATABASE:USAGE:
      - PROJ_STRIPE
      - SOURCE_STRIPE
    DATABASE:USAGE,CREATE SCHEMA:
      - BI_TOOL
    WAREHOUSE:USAGE:
      - BI_TOOL
```

---

#### **File 4: Business Role** (`snowddl/business_role.yaml`)

**Template**:
```yaml
[SERVICE_NAME]_BUSINESS_ROLE:
  comment: Business role for [Service Name] - analytics and dashboard access
  tech_roles:
    - [SERVICE_NAME]_TECH_ROLE
  warehouse_usage:
    - [SERVICE_WAREHOUSE]
```

**Placement**: Add alphabetically between existing business roles

**Critical Rules**:
- **Single Tech Role**: One-to-one mapping (one business role → one tech role)
- **Warehouse Mapping**: Must match warehouse created in File 2
- **Naming Convention**: Business role grants tech role + warehouse

**Example** (LightDash):
```yaml
LIGHTDASH_BUSINESS_ROLE:
  comment: Business role for LightDash BI platform - analytics and dashboard access with read/write to BI_TOOL database
  tech_roles:
    - LIGHTDASH_TECH_ROLE
  warehouse_usage:
    - BI_TOOL
```

---

#### **File 5: Database Configuration** (`snowddl/[SERVICE_NAME]/params.yaml`)

**Template**:
```yaml
comment: [Service Name] database for analytics transformations and dashboard content
is_sandbox: false
```

**Location**: Create new directory `snowddl/[SERVICE_NAME]/`

**Critical Rules**:
- **Directory Name**: ALL CAPS, matches database name
- **Production Flag**: Always `is_sandbox: false` for production services
- **Comment**: Describe database purpose

**Example** (LightDash):
```
snowddl/BI_TOOL/params.yaml
```
```yaml
comment: LightDash BI platform database for analytics transformations and dashboard content
is_sandbox: false
```

---

#### **File 6: Service Account User** (`snowddl/user.yaml`)

**Template**:
```yaml
[SERVICE_NAME]:
  business_roles:
    - [SERVICE_NAME]_BUSINESS_ROLE
  comment: [Service Name] service account - Analytics and dashboard access - RSA key authentication only
  default_warehouse: [SERVICE_WAREHOUSE]
  email: [service_name]@example.com
  login_name: [SERVICE_NAME]
  network_policy: [service_name]_network_policy
  rsa_public_key: [PLACEHOLDER - TO BE REPLACED]
  type: SERVICE
```

**Placement**: Add alphabetically between existing users

**CRITICAL RULES - SERVICE ACCOUNTS**:
- ✅ **MUST HAVE**: `type: SERVICE`
- ✅ **MUST HAVE**: `rsa_public_key` (NO password field)
- ✅ **MUST HAVE**: `network_policy` (IP restrictions)
- ✅ **MUST HAVE**: Single business role
- ✅ **MUST HAVE**: Default warehouse (prevents unauthorized usage)
- ✅ **MUST HAVE**: Email in format `user@example.com`
- ❌ **NEVER HAVE**: `password` field
- ❌ **NEVER HAVE**: `first_name`, `last_name`, `display_name` (human user fields)
- ❌ **NEVER HAVE**: Multiple business roles

**Example** (LightDash):
```yaml
BI_TOOL:
  business_roles:
    - LIGHTDASH_BUSINESS_ROLE
  comment: LightDash BI platform service account - Analytics and dashboard access with read/write to BI_TOOL database - RSA key authentication only
  default_warehouse: BI_TOOL
  email: user@example.com
  login_name: BI_TOOL
  network_policy: bi_tool_network_policy
  rsa_public_key: MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuHRXNcHlWuPdjrp4Mbg+ydrGR52uGgmiXrene0EYLYfc6Cht/YN5dzBc35B5aZPkhSEofKEI8omfDIoqWjo19X/kYCD5V/UMlYd/yN9MHaSJXml8zYSlaKYUL8S0Y+7f4CZtsdfV8JpGyVmicwbeFGNfCS6hciBVnkbyqMfszp7TZY1Eop0Tm8vLJcZSfU3EjEg+I3sZ98ssX/t3xMI9B3/aajXNr10Dd5J9BbtWyDCZaWiyV8WQgT382iSATTDtTcliDgWMx0tgPn68lwok8GymNMa1Jo+6oaBG2GhUw7jgvLxU+0WRvKczyYZphvdyfXeCcJIrWSGy+sK43oDERwIDAQAB
  type: SERVICE
```

---

### Phase 3: RSA Key Generation

**Commands**:
```bash
# Create keys directory if it doesn't exist
mkdir -p keys

# Generate private key (PKCS#8 format, no passphrase)
cd keys
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out [service_name]_rsa_key.p8 -nocrypt

# Generate public key
openssl rsa -in [service_name]_rsa_key.p8 -pubout -out [service_name]_rsa_key.pub

# Extract public key content (remove headers/footers, no newlines)
cat [service_name]_rsa_key.pub | grep -v "BEGIN PUBLIC KEY" | grep -v "END PUBLIC KEY" | tr -d '\n'
```

**Replace Placeholder**:
1. Copy the output from the last command
2. Edit `snowddl/user.yaml`
3. Replace `[PLACEHOLDER - TO BE REPLACED]` with the public key

**Security**:
- ✅ Private key stays in `keys/` directory (gitignored)
- ✅ Public key goes in `snowddl/user.yaml` (safe to commit)
- ❌ NEVER commit private keys
- ❌ NEVER share private keys via Slack/email

---

### Phase 4: Secrets Baseline Update

**Problem**: Pre-commit hook detects RSA public keys as "Base64 High Entropy Strings"

**Solution**: Update `.secrets.baseline` to include RSA keys as verified findings

**Command**:
```bash
# Use uvx (not pre-commit directly) to scan and update baseline
uvx detect-secrets scan --baseline .secrets.baseline
```

**What This Does**:
- Scans all files for secrets
- Updates `.secrets.baseline` with current findings
- Marks RSA public keys as verified (not secrets)
- Future commits won't be blocked

**CRITICAL**: Always use `uvx` for this - don't skip the hook with `--no-verify`

---

### Phase 5: Commit

**Stage All Files**:
```bash
git add snowddl/user.yaml \
        snowddl/network_policy.yaml \
        snowddl/business_role.yaml \
        snowddl/tech_role.yaml \
        snowddl/warehouse.yaml \
        snowddl/[SERVICE_NAME]/ \
        .secrets.baseline
```

**Commit Template**:
```bash
git commit -m "Add [Service Name] service account with enterprise security

Creates complete infrastructure for [Service Name] integration following
SnowTower enterprise security patterns and best practices.

Infrastructure Components:
- [SERVICE_NAME] database for BI dashboard content and analytics
- [SERVICE_NAME] warehouse (X-Small, 60s auto-suspend) for cost efficiency
- [SERVICE_NAME]_TECH_ROLE with least privilege access model
- [SERVICE_NAME]_BUSINESS_ROLE for role hierarchy
- [service_name]_network_policy with IP allowlist ([regions])
- [SERVICE_NAME] service account with RSA-only authentication

Security Features:
- RSA key-pair authentication only (no password)
- Network policy restricts to [Service Name] cloud IPs ([list IPs])
- Read-only access to [source databases]
- Read/write access to dedicated [SERVICE_NAME] database only
- TYPE=SERVICE classification (MFA exempt)
- Dedicated warehouse for cost isolation

Access Model:
[SERVICE_NAME] user → [SERVICE_NAME]_BUSINESS_ROLE → [SERVICE_NAME]_TECH_ROLE
  ├─ Read-only: [source databases]
  ├─ Read/write: [SERVICE_NAME] database (CREATE SCHEMA permission)
  └─ Warehouse: [SERVICE_NAME] only

Security Review: 100% compliance (8/8 checks passed)
Pattern: Matches ANALYTICS_TOOL service account security model

Updates .secrets.baseline to include RSA public keys as verified findings

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Phase 6: Security Review Checklist

**Before Deployment - Verify**:

```
Service Account Security Checklist:
□ RSA key-pair authentication only (no password field)
□ Network policy with IP restrictions (all regions covered)
□ Least privilege access (read-only to sources, write to own DB only)
□ Proper role hierarchy (business → tech → permissions)
□ Service account classified (TYPE=SERVICE)
□ No MFA required (service accounts automatically exempt)
□ Warehouse cost optimization (auto_suspend: 60, size: X-Small)
□ Consistent with SnowTower patterns (compare to ANALYTICS_TOOL)
□ Future grants configured (permissions inherit to new objects)
□ Single business role assignment
□ Dedicated warehouse assignment
□ Network policy matches service provider's IPs
□ Private key secured in keys/ directory (gitignored)
□ Public key in user.yaml matches generated key
□ Secrets baseline updated (no pre-commit blocks)
□ All 6 config files created and alphabetically placed
□ Database directory created with params.yaml
□ Commit message follows template
```

**Security Review Should Confirm**:
- No security vulnerabilities (Critical/High/Medium)
- Matches existing service account patterns (ANALYTICS_TOOL, DBT_SERVICE)
- Complies with SnowTower enterprise standards
- Ready for production deployment

---

### Phase 7: Deployment

**Preview Changes**:
```bash
uv run snowddl-plan
```

**Review Output**:
- Verify all expected objects are being created
- Check for any unexpected changes
- Confirm no deletions or modifications to existing objects

**Deploy to Snowflake**:
```bash
uv run snowddl-apply
```

**Verify Deployment**:
```bash
# Check user was created
uv run manage-users --list --filter "name=[SERVICE_NAME]"

# Test connection manually (from service)
```

---

## 🎯 Architecture Pattern

```
[SERVICE_NAME] user (SERVICE account)
  ↓
[SERVICE_NAME]_BUSINESS_ROLE
  ↓
[SERVICE_NAME]_TECH_ROLE
  ├─ READ access:  [source databases]
  ├─ WRITE access: [SERVICE_NAME] database only
  └─ WAREHOUSE:    [SERVICE_NAME] only

Network Security:
  [service_name]_network_policy → Only allows [service IPs]

Authentication:
  RSA key-pair only (private key in keys/[service]_rsa_key.p8)
```

---

## 🚨 Common Mistakes to Avoid

### **1. Adding Password to Service Account**
❌ **WRONG**:
```yaml
BI_TOOL:
  password: '!decrypt gAAAAAB...'  # NEVER DO THIS
  rsa_public_key: MIIBIjAN...
  type: SERVICE
```

✅ **CORRECT**:
```yaml
BI_TOOL:
  rsa_public_key: MIIBIjAN...  # RSA only, no password
  type: SERVICE
```

**Why**: Service accounts should NEVER have passwords. Passwords introduce security risks (phishing, brute force, credential stuffing). RSA keys are cryptographically secure and can't be brute-forced.

---

### **2. Forgetting Network Policy**
❌ **WRONG**:
```yaml
BI_TOOL:
  # No network_policy field
  type: SERVICE
```

✅ **CORRECT**:
```yaml
BI_TOOL:
  network_policy: bi_tool_network_policy
  type: SERVICE
```

**Why**: Without network policy, credentials can be used from anywhere. Network policies enforce zero-trust security.

---

### **3. Granting Too Many Permissions**
❌ **WRONG**:
```yaml
LIGHTDASH_TECH_ROLE:
  grants:
    DATABASE:USAGE,CREATE SCHEMA,MODIFY,MONITOR:  # Too many permissions
      - PROJ_STRIPE
```

✅ **CORRECT**:
```yaml
LIGHTDASH_TECH_ROLE:
  grants:
    DATABASE:USAGE:  # Read-only
      - PROJ_STRIPE
    DATABASE:USAGE,CREATE SCHEMA:  # Write only to own DB
      - BI_TOOL
```

**Why**: Least privilege principle. BI tools should read from sources, write to their own database only.

---

### **4. Skipping Pre-Commit Hook (--no-verify)**
❌ **WRONG**:
```bash
git commit --no-verify -m "message"
```

✅ **CORRECT**:
```bash
uvx detect-secrets scan --baseline .secrets.baseline
git commit -m "message"  # Hook passes now
```

**Why**: Pre-commit hooks exist for security. Update the baseline instead of bypassing.

---

### **5. Using Broad Network Ranges**
❌ **WRONG**:
```yaml
bi_tool_network_policy:
  allowed_ip_list:
    - 35.245.0.0/16  # Entire /16 subnet
```

✅ **CORRECT**:
```yaml
bi_tool_network_policy:
  allowed_ip_list:
    - 198.51.100.1/32  # Single IP only
```

**Why**: Always use /32 masks (single IP) for maximum security. Only allow specific IPs.

---

### **6. Forgetting Future Grants**
❌ **WRONG**:
```yaml
LIGHTDASH_TECH_ROLE:
  grants:  # Only grants, no future_grants
    DATABASE:USAGE:
      - PROJ_STRIPE
```

✅ **CORRECT**:
```yaml
LIGHTDASH_TECH_ROLE:
  future_grants:  # Permissions inherit to new objects
    TABLE:SELECT:
      - PROJ_STRIPE
  grants:
    DATABASE:USAGE:
      - PROJ_STRIPE
```

**Why**: Without future_grants, new tables/views won't be accessible. Always include both.

---

### **7. Wrong User Type**
❌ **WRONG**:
```yaml
BI_TOOL:
  type: PERSON  # Wrong type
```

✅ **CORRECT**:
```yaml
BI_TOOL:
  type: SERVICE  # Correct type
```

**Why**: Service accounts must be TYPE=SERVICE. This exempts them from MFA requirements and applies different security policies.

---

## 📚 Reference Implementations

### **Gold Standard: ANALYTICS_TOOL**
- File: `snowddl/user.yaml` (line 94-104)
- Pattern: BI service account with network policy, RSA-only, dedicated warehouse
- Security: 100% compliant

### **Alternative: DBT_SERVICE**
- File: `snowddl/user.yaml` (line 15-24)
- Pattern: Data transformation service with RSA-only
- Note: Uses shared warehouse (acceptable for transformation workloads)

### **Latest: BI_TOOL**
- Branch: `feature/lightdash-service-account`
- Commit: cce2026
- Pattern: Newest implementation following this document exactly

---

## 🔍 Testing Your Implementation

### **Before Deployment**:

1. **Config Validation**:
```bash
# Check YAML syntax
yamllint snowddl/*.yaml snowddl/[SERVICE_NAME]/*.yaml

# Verify alphabetical ordering (manually review)
```

2. **Security Validation**:
```bash
# Ensure secrets baseline is updated
git diff .secrets.baseline

# Verify no passwords in service account
grep -A 20 "^[SERVICE_NAME]:" snowddl/user.yaml | grep "password"
# Should return nothing

# Verify TYPE=SERVICE
grep -A 20 "^[SERVICE_NAME]:" snowddl/user.yaml | grep "type: SERVICE"
# Should return match
```

3. **Pattern Consistency**:
```bash
# Compare to ANALYTICS_TOOL reference
diff <(grep -A 15 "^ANALYTICS_TOOL:" snowddl/user.yaml) \
     <(grep -A 15 "^[SERVICE_NAME]:" snowddl/user.yaml)
# Structure should be identical
```

---

### **After Deployment**:

1. **Snowflake Verification**:
```sql
-- Verify user was created
SHOW USERS LIKE '[SERVICE_NAME]';

-- Verify network policy assigned
DESC USER [SERVICE_NAME];

-- Verify role grants
SHOW GRANTS TO USER [SERVICE_NAME];

-- Test warehouse access
USE ROLE [SERVICE_NAME]_BUSINESS_ROLE;
USE WAREHOUSE [SERVICE_NAME];
SELECT CURRENT_WAREHOUSE();  -- Should return [SERVICE_NAME]

-- Test database permissions
SHOW DATABASES;  -- Should see [SERVICE_NAME], [source databases]
```

2. **Service Integration Test**:
- Configure service with private key
- Test connection from service UI
- Run simple query to verify permissions
- Verify query runs on correct warehouse

---

## 🎓 Key Principles

1. **Least Privilege**: Only grant what's needed, nothing more
2. **Defense in Depth**: Multiple security layers (RSA + network + permissions)
3. **Cost Optimization**: Dedicated warehouse with auto-suspend
4. **Pattern Consistency**: Always match existing patterns (ANALYTICS_TOOL reference)
5. **Documentation**: Clear comments explaining purpose and permissions
6. **Future-Proof**: Use future_grants for new objects
7. **Zero Trust**: Network policies restrict by IP
8. **Service Account Security**: No passwords, ever

---

## 📋 Quick Reference Checklist

**When Creating New Service Account**:

```
□ Research service IPs (official documentation)
□ Create feature branch
□ Add network policy (alphabetically)
□ Add warehouse (alphabetically)
□ Add technical role (alphabetically, least privilege)
□ Add business role (alphabetically)
□ Create database directory with params.yaml
□ Add user account (alphabetically, TYPE=SERVICE, no password)
□ Generate RSA key pair (keys/ directory)
□ Replace placeholder with public key
□ Update secrets baseline (uvx detect-secrets)
□ Stage all files (including .secrets.baseline)
□ Commit with template message
□ Run snowddl-plan (review output)
□ Run snowddl-apply (deploy)
□ Verify in Snowflake
□ Test from service
□ Document in project wiki/README
```

**Estimated Time**: 45-60 minutes for complete implementation

---

## 🚀 Future Services to Implement

Using this pattern, create service accounts for:

- **Tableau** (BI platform)
- **PowerBI** (Microsoft BI)
- **Looker** (Google BI)
- **Metabase** (Open source BI)
- **Superset** (Open source BI)
- **Mode Analytics** (BI platform)
- **Sisense** (BI platform)
- **ThoughtSpot** (AI-powered analytics)
- **Hex** (Collaborative data workspace)
- **Databricks** (Data lakehouse)
- **Airbyte** (Data integration)
- **Census** (Reverse ETL)
- **Hightouch** (Reverse ETL)

All should follow this exact pattern with appropriate customizations for their specific requirements.

---

## 📞 Need Help?

**Questions About Pattern**:
- Review ANALYTICS_TOOL implementation (snowddl/user.yaml line 94-104)
- Review BI_TOOL implementation (feature/lightdash-service-account branch)
- Consult SECURITY_AGENT for security questions
- Consult SNOWDDL_EXPERT_AGENT for SnowDDL syntax

**Deployment Issues**:
- Check DEPLOYMENT_AGENT
- Review DEPLOYMENT_TROUBLESHOOTING_AGENT

**Security Concerns**:
- Always consult SECURITY_AGENT before deployment
- Request security review for any deviations from pattern

---

**Document Version**: 1.0
**Last Updated**: 2025-10-10
**Reference Commit**: cce2026 (BI_TOOL service account)
**Pattern Status**: ✅ PRODUCTION READY - USE FOR ALL NEW SERVICE ACCOUNTS
