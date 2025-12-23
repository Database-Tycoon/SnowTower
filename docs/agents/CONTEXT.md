# Project Context

## Domain Knowledge

### What is SnowDDL?
SnowDDL is an open-source tool for managing Snowflake infrastructure as code. It:
- Reads YAML configuration files
- Compares desired state with actual Snowflake state
- Generates and executes DDL statements to reconcile differences

### What is SnowTower?
SnowTower is our enterprise wrapper around SnowDDL that adds:
- User lifecycle management with MFA compliance
- Cost optimization and monitoring
- Security policies and network controls
- CLI commands via UV package manager

## Key Concepts

### Infrastructure as Code (IaC)
All Snowflake objects are defined in YAML files under `snowddl/`:
- Changes are version-controlled in git
- Deployments go through CI/CD (GitHub Actions)
- `plan` shows changes, `apply` executes them

### Role-Based Access Control (RBAC)
```
ACCOUNTADMIN (top-level)
    ↓
SYSADMIN → USERADMIN → SECURITYADMIN
    ↓           ↓            ↓
Business Roles (__B_ROLE)
    ↓
Technical Roles (__T_ROLE)
    ↓
Object Permissions
```

### User Types
- **PERSON**: Human users, require MFA, have network policies
- **SERVICE**: Service accounts, use RSA keys, typically unrestricted

### Authentication Methods
1. **RSA Key Pairs** - Passwordless, most secure
2. **Encrypted Passwords** - Fernet encryption, fallback only
3. **MFA** - Multi-factor auth, mandatory for humans by 2026

## Technology Stack

| Component | Technology |
|-----------|------------|
| Infrastructure | Snowflake (cloud data warehouse) |
| IaC Tool | SnowDDL |
| Language | Python 3.10+ |
| Package Manager | UV (fast pip alternative) |
| CI/CD | GitHub Actions |
| Encryption | Fernet (symmetric) |

## Snowflake-Specific Knowledge

### Object Hierarchy
```
Account
  └── Database
        └── Schema
              ├── Tables
              ├── Views
              ├── Stages
              └── Procedures
```

### Common Privileges
- `USAGE` - Access to use an object
- `SELECT` - Read data
- `INSERT/UPDATE/DELETE` - Modify data
- `CREATE TABLE/VIEW` - Create objects
- `OWNERSHIP` - Full control

### SnowDDL Limitations
- Does not manage SCHEMA objects (conflicts with dbt)
- Schema grants must be handled separately
- Some object types require `--apply-unsafe` flag

## Project History

- **2024**: Initial SnowDDL implementation
- **2025 Q1**: Security hardening (MFA, network policies)
- **2025 Q2**: CLI consolidation, UV migration
- **2025 Q3**: Repository unification (snowtower-cli merged)
- **Current**: Documentation restructure, agent support
