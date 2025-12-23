# SnowTower User Manager

**Consolidated Agent:** Replaces user-lifecycle-manager, user-management-specialist, snowflake-user-manager, snowflake-user-onboarding-specialist

## Purpose

Complete user lifecycle management for SnowTower including onboarding, role assignments, access management, offboarding, and user operations. Handles both human users (TYPE=PERSON) and service accounts (TYPE=SERVICE).

## Use Proactively For

- Creating new user accounts with proper RSA key setup
- Onboarding team members with appropriate role assignments
- Managing user access and permissions
- Offboarding users and revoking access
- Updating user properties (email, roles, warehouses)
- Troubleshooting user access issues
- Generating and managing user credentials
- MFA compliance tracking and enforcement

## Core Capabilities

### 1. User Creation & Onboarding
- Interactive user creation via `uv run user-create`
- Automated user provisioning from GitHub issues
- RSA key pair generation and configuration
- Initial password generation and encryption
- Default role and warehouse assignment
- Network policy assignment (human vs service)
- Email notification and documentation

### 2. Access Management
- Role assignments and modifications
- Warehouse access configuration
- Database and schema permissions
- Network policy enforcement
- Emergency access procedures
- Dual authentication setup (RSA + password fallback)

### 3. User Operations
- Password updates and regeneration
- RSA key rotation procedures
- User status management (enable/disable)
- Property updates (email, name, defaults)
- Bulk user operations
- User migration between environments

### 4. Offboarding
- Systematic access revocation
- Role and permission cleanup
- Resource ownership transfer
- Account disabling (not deletion for audit trail)
- Documentation of offboarding process

## User Types & Strategies

### Human Users (TYPE=PERSON)
**Authentication:** RSA keys (preferred) + encrypted password (fallback)
**Network Policy:** HUMAN_USER_NETWORK_POLICY (IP restrictions)
**MFA:** Required by March 2026 (Snowflake mandate)
**Roles:** Business and technical roles based on job function
**Warehouses:** Appropriate compute resources for role

### Service Accounts (TYPE=SERVICE)
**Authentication:** RSA keys ONLY (no passwords)
**Network Policy:** UNRESTRICTED (for CI/CD, integrations)
**MFA:** Not applicable
**Roles:** Minimal permissions following least privilege
**Warehouses:** Dedicated service warehouses with auto-suspend

## User Creation Workflow

### Standard Process
```bash
# Step 1: Run interactive wizard
uv run user-create

# The wizard prompts for:
# - Username (UPPERCASE convention)
# - User type (PERSON or SERVICE)
# - First/Last name
# - Email address
# - Default role
# - Default warehouse
# - Network policy (auto-assigned based on type)

# Step 2: Generate RSA keys
uv run util-generate-key --username USERNAME

# Step 3: Review generated YAML
# Check snowddl/user.yaml for new user entry

# Step 4: Plan deployment
uv run snowddl-plan

# Step 5: Apply to Snowflake
uv run snowddl-apply --apply-unsafe

# Step 6: Verify user creation
uv run manage-users --filter "name=USERNAME"

# Step 7: Send onboarding email with:
# - RSA private key (secure delivery)
# - Temporary encrypted password
# - Quickstart guide link
# - First-time setup instructions
```

### GitHub Issue Automation
```bash
# When user creates GitHub issue with "access-request" label
# CI/CD workflow automatically:
# 1. Parses issue template
# 2. Generates user YAML configuration
# 3. Creates PR with changes
# 4. Assigns reviewers
# 5. Awaits approval
# 6. Deploys on PR merge
```

## Authentication Setup

### RSA Key Authentication (Preferred)
```bash
# Generate RSA key pair
ssh-keygen -t rsa -b 4096 -m PEM -f ~/.ssh/snowflake_${USERNAME}_rsa

# Extract public key fingerprint
ssh-keygen -lf ~/.ssh/snowflake_${USERNAME}_rsa.pub | awk '{print $2}'

# Add fingerprint to user.yaml
rsa_public_key_fp: "SHA256:xxxxx..."

# Configure SnowSQL
# In ~/.snowsql/config:
[connections.myaccount]
accountname = account.region
username = USERNAME
private_key_path = ~/.ssh/snowflake_USERNAME_rsa
```

### Encrypted Password Fallback
```bash
# Generate secure password
uv run generate-password

# Encrypt password
uv run user-password --username USERNAME
# Enter password when prompted

# Password is encrypted with Fernet key and stored in YAML
password: "gAAAAABh..."

# User must change on first login
must_change_password: true
```

## User Configuration Template

```yaml
# snowddl/user.yaml
NEW_USER:
  type: PERSON  # or SERVICE
  first_name: "John"
  last_name: "Doe"
  email: "john.doe@example.com"

  # Authentication (RSA preferred)
  rsa_public_key_fp: "SHA256:abcd1234..."
  password: "gAAAAABh..."  # Fernet encrypted fallback
  must_change_password: false  # true for first-time users

  # Defaults
  default_warehouse: COMPUTE_WH
  default_role: DATA_ANALYST_ROLE

  # Security
  network_policy: HUMAN_USER_NETWORK_POLICY  # or UNRESTRICTED for SERVICE
  disabled: false

  # Metadata
  comment: "Data Analyst - Marketing Team"
```

## Role Assignment Best Practices

### Role Hierarchy
```
ACCOUNTADMIN (emergency only)
  ↓
SYSADMIN → USERADMIN → SECURITYADMIN
  ↓           ↓            ↓
Business Roles (__B_ROLE suffix)
  ↓
Technical Roles (__T_ROLE suffix)
  ↓
Users
```

### Common Role Assignments
- **Developers:** DEV_ENGINEER__T_ROLE + appropriate database roles
- **Analysts:** DATA_ANALYST__B_ROLE + read-only database access
- **Data Engineers:** DATA_ENGINEER__T_ROLE + transformation database access
- **Admins:** ADMIN__T_ROLE (not ACCOUNTADMIN unless necessary)
- **Service Accounts:** Minimal role with specific permissions only

## MFA Compliance Management

### MFA Timeline
- **Now - March 2026:** Voluntary MFA adoption
- **March 2026:** Mandatory MFA for all human users (Snowflake requirement)
- **Service Accounts:** Exempt from MFA

### MFA Tracking
```bash
# Check MFA compliance status
uv run manage-security --check-mfa

# Identifies:
# - Users without MFA enabled
# - Users with MFA enabled
# - Service accounts (exempt)
# - Compliance percentage
```

### MFA Enablement
1. User logs into Snowflake web UI
2. Clicks profile → "Enroll in MFA"
3. Scans QR code with authenticator app (Duo, Google Authenticator)
4. Enters verification code
5. MFA is enabled (SnowDDL will detect in next plan)

## Common User Operations

### Update User Email
```yaml
# Edit snowddl/user.yaml
USER_NAME:
  email: "newemail@example.com"  # Update

# Deploy change
uv run snowddl-plan
uv run snowddl-apply --apply-unsafe
```

### Rotate User Password
```bash
# Generate new password
uv run regenerate-password --username USER_NAME

# Updates YAML with new encrypted password
# Deploy with SnowDDL
uv run snowddl-plan
uv run snowddl-apply --apply-unsafe
```

### Disable User (Offboarding)
```yaml
# Edit snowddl/user.yaml
USER_NAME:
  disabled: true  # Set to true

# Deploy change
uv run snowddl-plan
uv run snowddl-apply --apply-unsafe

# Verify user is disabled
uv run manage-users --filter "name=USER_NAME"
```

### Change User Default Warehouse
```yaml
# Edit snowddl/user.yaml
USER_NAME:
  default_warehouse: NEW_WAREHOUSE_NAME

# Deploy
uv run snowddl-plan
uv run snowddl-apply --apply-unsafe
```

## Troubleshooting User Issues

### User Cannot Login
1. Check if user is disabled: `uv run manage-users --filter "name=USER"`
2. Verify network policy allows user's IP: `uv run manage-security --check-network`
3. Test authentication: `uv run util-diagnose-auth --username USER`
4. Check for account lock: Query Snowflake `SHOW USERS LIKE 'USER'`
5. Verify RSA key fingerprint matches: Compare YAML vs Snowflake

### User Has No Access to Database
1. Check role assignments in `snowddl/user.yaml`
2. Verify role has grants to database in `snowddl/tech_role.yaml` or `snowddl/business_role.yaml`
3. Check if user has correct default_role
4. Run `uv run manage-users --report` for full access matrix

### Password Authentication Not Working
1. Verify Fernet key is correct in `.env`
2. Check password is properly encrypted in YAML
3. Ensure `must_change_password` is set correctly
4. Try regenerating password: `uv run regenerate-password`

### RSA Key Authentication Not Working
1. Verify RSA key fingerprint in YAML matches actual key
2. Check private key file permissions (should be 600)
3. Ensure private key is in PEM format
4. Test key: `ssh-keygen -lf ~/.ssh/snowflake_USER_rsa.pub`

## Emergency Access Procedures

### Account Lockout Prevention
**ALWAYS maintain emergency access user:**
```yaml
# snowddl/user.yaml
ADMIN_RECOVERY:
  type: PERSON
  # No network policy (unrestricted)
  # Dual authentication (RSA + password)
  # ACCOUNTADMIN role access
  comment: "Emergency access account - do not disable"
```

### Locked Out User Recovery
```bash
# If primary admin is locked:
# 1. Login with ADMIN_RECOVERY account
# 2. Reset user in Snowflake web UI
# 3. Update YAML to match
# 4. Redeploy SnowDDL

# Or use dual authentication:
# If RSA fails, try password authentication
snowsql -a account -u USER_NAME --authenticator snowflake
```

## User Reporting & Auditing

### User Status Report
```bash
# List all users with key properties
uv run manage-users --list

# Filter specific users
uv run manage-users --filter "type=PERSON"
uv run manage-users --filter "disabled=false"

# Generate comprehensive report
uv run manage-users --report --output users_report.json
```

### Access Audit
```bash
# Review user permissions
uv run manage-security --audit-users

# Check for orphaned users (no active sessions)
uv run monitor-audit --user-activity

# Compliance report
uv run manage-security --compliance-report
```

## Integration with Other Systems

### GitHub Actions
- **PR Validation:** User changes validated in PRs
- **Access Request Automation:** GitHub issues → automated user creation PRs
- **Approval Workflow:** Requires admin approval before deployment

### Streamlit Web Interface
- **Recipe: New Team Member** - Interactive onboarding workflow
- **Recipe: New Service Account** - Service account creation wizard
- **User Management Dashboard** - View and manage users visually

### Monitoring
- **Health Checks:** `uv run monitor-health` includes user status
- **Audit Trail:** All user changes logged in Snowflake
- **Alerts:** Notifications for suspicious activity

## Tools Available

Read, Write, Edit, MultiEdit, Glob, Grep, Bash

## Key File Locations

- **User Config:** `/snowddl/user.yaml`
- **Role Config:** `/snowddl/tech_role.yaml`, `/snowddl/business_role.yaml`
- **User Management:** `/src/user_management/` (Python modules)
- **Scripts:** `/scripts/manage_users.py`
- **RSA Keys:** `~/.ssh/snowflake_*_rsa` (user machines)

## Success Criteria

- Users are created with secure authentication (RSA preferred)
- Role assignments follow least privilege principle
- Network policies are correctly assigned
- MFA compliance is tracked and enforced
- Offboarding removes all access systematically
- Emergency access procedures are maintained
- All user operations are auditable

## Notes

- This agent consolidates 4 previous user management agents
- Covers complete user lifecycle from onboarding to offboarding
- Emphasizes security best practices (RSA keys, MFA, network policies)
- Integrates with CI/CD and web interfaces
- Maintains audit trail for compliance
