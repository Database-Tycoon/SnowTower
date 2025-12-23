# SnowDDL Configuration Directory

This directory contains all Snowflake infrastructure configurations managed by SnowDDL.

<!-- Updated workflow testing - 2025-09-22 -->

## Directory Structure

```
snowddl/
├── user.yaml                   # User accounts and authentication
├── business_role.yaml          # Business-oriented roles
├── tech_role.yaml             # Technical/system roles
├── user_role.yaml             # Individual user roles
├── authentication_policy.yaml # MFA and authentication policies
├── network_policy.yaml        # Network access policies
├── password_policy.yaml       # Password complexity policies
├── session_policy.yaml        # Session timeout policies
├── warehouse.yaml             # Compute warehouse definitions
├── DEV_CAROL/               # Developer sandboxes
├── DEV_DAVE/
├── DEV_EVE/
├── DEV_FRANK/
├── DEV_GRACE/
├── DEV_ALICE/
├── SOURCE_STRIPE/             # Source system databases
├── PROJ_STRIPE/               # Project databases
└── SNOWTOWER_APPS/            # Application database
```

## Configuration Guidelines

### Account-Level Configs
- **user.yaml**: All user accounts with encrypted passwords and RSA keys
- **business_role.yaml**: Business-oriented role definitions
- **tech_role.yaml**: Technical and system role definitions
- **user_role.yaml**: Individual user role assignments
- **authentication_policy.yaml**: MFA enforcement policies
- **network_policy.yaml**: IP-based access control
- **password_policy.yaml**: Password complexity requirements
- **session_policy.yaml**: Session timeout management
- **warehouse.yaml**: Compute resources

### Database Configs
Each database directory contains:
- `params.yaml`: Database parameters and settings
- Schema subdirectories with their objects

## Key Concepts

### User Authentication
- Human users (TYPE=PERSON) require MFA via authentication policies
- Service accounts (TYPE=SERVICE) use RSA key authentication
- Passwords are encrypted using Fernet encryption

### Role Hierarchy
1. **Tech Roles**: System administration and technical operations
2. **Business Roles**: Department/function-specific access
3. **User Roles**: Individual user role assignments

### Security Policies
- **Authentication**: MFA enforcement for compliance
- **Network**: IP-based access control
- **Password**: Complexity and rotation requirements
- **Session**: Timeout and idle management

## Usage

### Preview Changes
```bash
uv run snowddl-plan
```

### Apply Changes
```bash
uv run snowddl-apply
```

### Validate Configs
```bash
uv run snowddl-validate
```

## Important Notes

1. **Always use ACCOUNTADMIN role** for SnowDDL operations
2. **Set SNOWFLAKE_CONFIG_FERNET_KEYS** in `.env` for password decryption
3. **Review plan output carefully** before applying changes
4. **Never leave authentication methods blank** to prevent lockouts

## See Also
- [Deployment Guide](../docs/deployment/DEPLOYMENT_GUIDE.md)
- [MFA Compliance](../docs/security/MFA_COMPLIANCE.md)
- [Lockout Prevention](../docs/security/LOCKOUT_PREVENTION.md)
