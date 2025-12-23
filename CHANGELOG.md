# Changelog

All notable changes to the SnowTower SnowDDL project will be documented in this file.


## [2025-12-03] - Infrastructure Update

### Changed
- Merge pull request #75 from Database-Tycoon/fix/dlt-table-stage-permissions
- fix: Add schema_owner to DBT business role for PROJ_STRIPE access
- docs: update changelog for deployment 79410355
- Merge pull request #74 from Database-Tycoon/fix/dlt-table-stage-permissions
- chore: Remove plan generation from PR validation workflow
- fix: Change DEV_CAROL to non-sandbox to match existing PERMANENT schema
- docs: update changelog for deployment 7559b03e
- Merge pull request #73 from Database-Tycoon/fix/dlt-table-stage-permissions
- fix: Add schema_owner to DLT business role for table stage access
- docs: Add note about DLT schema owner role requirement
- docs: update changelog for deployment 23fe7d97
- Merge pull request #72 from Database-Tycoon/fix/ci-workflow-exit-codes
- fix: Remove obsolete transfer_ownership_to_dbt step from CI
- fix: Use uv run for transfer_ownership_to_dbt.py
- fix: Handle snowddl-apply exit code 8 as success
- fix: Handle snowddl-plan exit codes in all deployment steps

### Infrastructure Changes
- fix: Add schema_owner to DBT business role for PROJ_STRIPE access (a542757)
- fix: Change DEV_CAROL to non-sandbox to match existing PERMANENT schema (d29f9ff)
- fix: Add schema_owner to DLT business role for table stage access (da7de9f)
- docs: Add note about DLT schema owner role requirement (dc81bf1)

### Deployment Info
- **Commit:** 50a30bf6
- **Timestamp:** 2025-12-03 12:45:03 UTC
- **Triggered by:** example-user



## [2025-12-03] - Infrastructure Update

### Changed
- Merge pull request #74 from Database-Tycoon/fix/dlt-table-stage-permissions
- chore: Remove plan generation from PR validation workflow
- fix: Change DEV_CAROL to non-sandbox to match existing PERMANENT schema
- docs: update changelog for deployment 7559b03e
- Merge pull request #73 from Database-Tycoon/fix/dlt-table-stage-permissions
- fix: Add schema_owner to DLT business role for table stage access
- docs: Add note about DLT schema owner role requirement
- docs: update changelog for deployment 23fe7d97
- Merge pull request #72 from Database-Tycoon/fix/ci-workflow-exit-codes
- fix: Remove obsolete transfer_ownership_to_dbt step from CI
- fix: Use uv run for transfer_ownership_to_dbt.py
- fix: Handle snowddl-apply exit code 8 as success
- fix: Handle snowddl-plan exit codes in all deployment steps
- fix: Handle snowddl-plan non-zero exit codes in deployment workflow
- docs: update changelog for deployment 73736954

### Infrastructure Changes
- fix: Change DEV_CAROL to non-sandbox to match existing PERMANENT schema (d29f9ff)
- fix: Add schema_owner to DLT business role for table stage access (da7de9f)
- docs: Add note about DLT schema owner role requirement (dc81bf1)

### Deployment Info
- **Commit:** 79410355
- **Timestamp:** 2025-12-03 12:14:32 UTC
- **Triggered by:** example-user



## [2025-12-03] - Infrastructure Update

### Changed
- Merge pull request #73 from Database-Tycoon/fix/dlt-table-stage-permissions
- fix: Add schema_owner to DLT business role for table stage access
- docs: Add note about DLT schema owner role requirement
- docs: update changelog for deployment 23fe7d97
- Merge pull request #72 from Database-Tycoon/fix/ci-workflow-exit-codes
- fix: Remove obsolete transfer_ownership_to_dbt step from CI
- fix: Use uv run for transfer_ownership_to_dbt.py
- fix: Handle snowddl-apply exit code 8 as success
- fix: Handle snowddl-plan exit codes in all deployment steps
- fix: Handle snowddl-plan non-zero exit codes in deployment workflow
- docs: update changelog for deployment 73736954
- Merge pull request #71 from Database-Tycoon/feature/eliminate-schema-drift
- feat: Enable SnowDDL schema management and fix directory structure
- docs: Add SnowDDL knowledge base and fix test script
- fix: Resolve all test failures and add release checklist
- chore: Prepare for v0.1 release
- chore: Add keys/ to .gitignore and cleanup local artifacts
- fix: Correct docs path in help_cli.py
- feat: Remove web/Streamlit features for v0.1 release
- docs: restructure documentation and add LLM agent configuration

### Infrastructure Changes
- fix: Add schema_owner to DLT business role for table stage access (da7de9f)
- docs: Add note about DLT schema owner role requirement (dc81bf1)
- feat: Enable SnowDDL schema management and fix directory structure (8d49e44)
- feat: Add schema.yaml files for all databases to eliminate schema drift (8fc2140)

### Deployment Info
- **Commit:** 7559b03e
- **Timestamp:** 2025-12-03 11:46:16 UTC
- **Triggered by:** example-user



## [2025-11-30] - Infrastructure Update

### Changed
- Merge pull request #72 from Database-Tycoon/fix/ci-workflow-exit-codes
- fix: Remove obsolete transfer_ownership_to_dbt step from CI
- fix: Use uv run for transfer_ownership_to_dbt.py
- fix: Handle snowddl-apply exit code 8 as success
- fix: Handle snowddl-plan exit codes in all deployment steps
- fix: Handle snowddl-plan non-zero exit codes in deployment workflow
- docs: update changelog for deployment 73736954
- Merge pull request #71 from Database-Tycoon/feature/eliminate-schema-drift
- feat: Enable SnowDDL schema management and fix directory structure
- docs: Add SnowDDL knowledge base and fix test script
- fix: Resolve all test failures and add release checklist
- chore: Prepare for v0.1 release
- chore: Add keys/ to .gitignore and cleanup local artifacts
- fix: Correct docs path in help_cli.py
- feat: Remove web/Streamlit features for v0.1 release
- docs: restructure documentation and add LLM agent configuration
- docs: Add comprehensive next steps guide for schema drift elimination
- feat: Add schema.yaml files for all databases to eliminate schema drift
- docs: Add comprehensive CHANGELOG.md for 0.1 release
- fix: Remove 6 non-working command references

### Infrastructure Changes
- feat: Enable SnowDDL schema management and fix directory structure (8d49e44)
- feat: Add schema.yaml files for all databases to eliminate schema drift (8fc2140)
- feat: Add IP 192.0.2.10 to bi_tool_network_policy (a0d86c5)

### Deployment Info
- **Commit:** 23fe7d97
- **Timestamp:** 2025-11-30 23:33:51 UTC
- **Triggered by:** example-user



## [2025-11-30] - Infrastructure Update

### Changed
- Merge pull request #71 from Database-Tycoon/feature/eliminate-schema-drift
- feat: Enable SnowDDL schema management and fix directory structure
- docs: Add SnowDDL knowledge base and fix test script
- fix: Resolve all test failures and add release checklist
- chore: Prepare for v0.1 release
- chore: Add keys/ to .gitignore and cleanup local artifacts
- fix: Correct docs path in help_cli.py
- feat: Remove web/Streamlit features for v0.1 release
- docs: restructure documentation and add LLM agent configuration
- docs: Add comprehensive next steps guide for schema drift elimination
- feat: Add schema.yaml files for all databases to eliminate schema drift
- docs: Add comprehensive CHANGELOG.md for 0.1 release
- fix: Remove 6 non-working command references
- Merge pull request #59 from Database-Tycoon/fix/automatic-ownership-transfer-in-ci
- fix: add automatic ownership transfer to deployment workflow
- Merge pull request #58 from Database-Tycoon/fix/lightdash-network-policy-deployment
- fix: Add ownership investigation and transfer tools
- fix: Prevent dbt permission loss with deploy-safe wrapper
- feat: Add IP 192.0.2.10 to bi_tool_network_policy
- docs: Add Lightdash network policy deployment documentation

### Infrastructure Changes
- feat: Enable SnowDDL schema management and fix directory structure (8d49e44)
- feat: Add schema.yaml files for all databases to eliminate schema drift (8fc2140)
- feat: Add IP 192.0.2.10 to bi_tool_network_policy (a0d86c5)
- Add RSA public key for CAROL user (3d8fcac)
- fix: Add CREATE SCHEMA privilege to DBT_STRIPE_ROLE for SOURCE_STRIPE (3a59c83)

### Deployment Info
- **Commit:** 73736954
- **Timestamp:** 2025-11-30 20:16:38 UTC
- **Triggered by:** example-user


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-21

### 🎉 Initial Release

The first official release of SnowTower - a unified Snowflake infrastructure management platform with comprehensive CLI commands and Infrastructure as Code capabilities.

### ✨ Major Features

#### Infrastructure as Code
- **SnowDDL Integration**: Complete declarative infrastructure management via YAML configurations
- **Safe Deployment Workflow**: `uv run deploy-safe` ensures schema grants are always applied after infrastructure changes
- **Intelligent Plan Filtering** ⭐: Automatic suppression of expected schema grant drift in PR reviews (see [#66](https://github.com/Database-Tycoon/snowtower/pull/66))
  - Eliminates hundreds of REVOKE statements from plan output
  - Makes actual infrastructure changes crystal clear
  - Preserves full audit trail in collapsible sections
  - Integrated into CI/CD workflows

#### User Management
- **Complete User Lifecycle**: Interactive and non-interactive user creation with `uv run manage-users`
- **Dual Authentication**: RSA key-pair (primary) + encrypted password (fallback) for all users
- **MFA Compliance Tracking**: Ready for Snowflake's 2025-2026 mandatory MFA rollout
- **Bulk Operations**: Password generation, CSV import, key rotation

#### Resource Management
- **Warehouse Management**: Resize, auto-suspend, cost optimization with `uv run manage-warehouses`
- **Cost Optimization**: Analysis and recommendations with `uv run manage-costs`
- **Security Auditing**: Comprehensive security checks with `uv run manage-security`
- **Backup & Restore**: Configuration snapshots with `uv run manage-backup`

#### Monitoring & Observability
- **Health Checks**: System health monitoring with `uv run monitor-health`
- **Audit Logs**: Complete audit trail with `uv run monitor-audit`
- **Operational Metrics**: Performance and usage metrics with `uv run monitor-metrics`

#### CI/CD Automation
- **GitHub Actions Workflows**: Automated PR validation and production deployment
- **Safety Gates**: Pre-deployment validation, security scanning, health checks
- **Schema Grant Protection**: Automatic application of schema grants after every deployment
- **Emergency Rollback**: Snapshot-based rollback capabilities

### 🔐 Security

- **MFA Enforcement**: Timeline-ready for Snowflake's mandatory MFA (March 2026)
- **RSA Key Authentication**: Prioritized for all service accounts
- **Encrypted Passwords**: Fernet encryption for all password storage
- **Network Policies**: IP restrictions for human users (192.0.2.10/32)
- **Emergency Access**: STEPHEN_RECOVERY account preserved without network restrictions
- **Audit Trail**: Complete logging of all infrastructure changes

### 📚 Documentation

- **Comprehensive README**: User-focused onboarding and administrator guide
- **Management Commands Reference**: Complete CLI command documentation
- **Quick Start Guide**: 5-minute setup for new users
- **Schema Grants Workaround**: Detailed explanation of SnowDDL's SCHEMA exclusion pattern
- **Security Guides**: Authentication setup, MFA compliance, RSA key generation
- **0.1 Release Review**: Comprehensive pre-release audit and recommendations

### 🛠️ CLI Commands

**25+ Working Commands** organized in 7 categories:

#### Core SnowDDL Operations (5 commands)
- `snowddl-plan` - Preview infrastructure changes with intelligent filtering
- `snowddl-apply` - Apply infrastructure changes
- `snowddl-validate` - Validate YAML configurations
- `snowddl-diff` - Show differences
- `deploy-safe` - Safe deployment with automatic schema grants ⭐

#### User Management (1 command with subcommands)
- `manage-users` - Complete user lifecycle (create, list, update, delete, validate, etc.)

#### Resource Management (6 commands)
- `manage-warehouses` - Warehouse operations and optimization
- `manage-costs` - Cost analysis and optimization
- `manage-security` - Security auditing
- `manage-backup` - Configuration backup/restore
- `apply-schema-grants` - Apply schema-level grants ⭐
- `validate-schema-grants` - Validate schema grant consistency

#### Monitoring (3 commands)
- `monitor-health` - System health checks
- `monitor-audit` - Audit trail analysis
- `monitor-metrics` - Operational metrics

#### Web Interface (2 commands)
- `web` - Launch Streamlit dashboard
- `deploy-streamlit` - Deploy Streamlit apps to Snowflake

#### Utilities (4 commands)
- `util-generate-key` - Generate Fernet encryption key
- `util-diagnose-auth` - Diagnose authentication issues
- `util-fix-auth` - Fix authentication problems
- `generate-rsa-batch` - Batch RSA key generation

#### Automation (2 commands)
- `github-to-snowddl` - Convert GitHub issues to SnowDDL PRs
- `process-access-request` - Process user access requests

#### Documentation (2 commands)
- `docs-serve` - Serve documentation locally
- `docs-build` - Build documentation

#### New in 0.1 (1 command)
- `filter-plan` - Intelligent plan output filtering ⭐

### 🐛 Fixed

- **Schema Grant Drift Noise**: Intelligent filtering eliminates hundreds of REVOKE statements from PR reviews
- **Missing Command References**: Removed 6 non-existent commands from registry
  - `test-s3-deployment`
  - `sync-s3-configs`
  - `test-streamlit-local`
  - `test-streamlit-deployed`
  - `deploy-streamlit-safe`
  - `detect-streamlit-errors`
- **Documentation Accuracy**: Updated command documentation to reflect actual implementations

### ⚠️ Known Limitations

#### Web UI
- **Status**: Has known errors and issues
- **Recommendation**: Use CLI commands instead
- **Launch Command**: `uv run web` works but may have runtime errors
- **Roadmap**: Full web UI refactoring planned for 0.2 release

#### Test Coverage
- **Current**: ~40% (filter tests only)
- **Target**: >80% by 0.2 release
- **Status**: Integration tests planned but not yet implemented

#### Streamlit Testing
- Basic validation available via `validate-streamlit`
- Advanced testing commands deferred to future release

### 🚀 Deployment

#### Prerequisites
- Python 3.10+
- UV package manager
- Snowflake account with ACCOUNTADMIN role
- RSA key pair for authentication

#### Quick Start
```bash
# 1. Clone and install
git clone https://github.com/Database-Tycoon/snowtower.git
cd snowtower-snowddl
uv sync

# 2. Configure authentication
cp .env.example .env
# Edit .env with your credentials

# 3. Preview changes
uv run snowddl-plan

# 4. Deploy safely
uv run deploy-safe
```

### 📊 Project Statistics

- **Active Users**: 13 configured (7 human, 5 service accounts)
- **Databases Managed**: 6 production databases
- **Warehouses**: 8 with auto-suspend
- **Resource Monitors**: 7 active cost monitors
- **Security Policies**: Network and authentication policies enforced
- **Test Coverage**: 13 passing tests for plan filtering

### 🔄 Migration Guide

This is the initial release, so no migration is required. For users of the pre-release versions:

1. **Update Dependencies**: Run `uv sync` to install all dependencies
2. **Review Commands**: Some commands have been removed - see Fixed section above
3. **Update Workflows**: CI/CD workflows now include intelligent filtering
4. **Review Documentation**: New comprehensive guides in `docs/` directory

### 🙏 Acknowledgments

- Built with [SnowDDL](https://github.com/littleK0i/SnowDDL) by littleK0i
- Powered by [UV](https://github.com/astral-sh/uv) package manager by Astral
- Infrastructure automation via [GitHub Actions](https://github.com/features/actions)

### 📝 Notes

- **Recommended Deployment**: Always use `uv run deploy-safe` instead of `snowddl-apply`
- **Schema Grants**: See `docs/SCHEMA_GRANTS_WORKAROUND.md` for critical information
- **MFA Timeline**: Enable MFA for human users before March 2026 deadline
- **RSA Keys**: Primary authentication method for all service accounts

---

## [Unreleased]

### Planned for 0.2.0
- Complete web UI refactoring and error fixes
- Integration test suite for CLI commands
- Increased test coverage (>80%)
- Advanced Streamlit testing commands
- API documentation generation
- Multi-account support exploration

---

**Full Changelog**: https://github.com/Database-Tycoon/snowtower/commits/v0.1.0
