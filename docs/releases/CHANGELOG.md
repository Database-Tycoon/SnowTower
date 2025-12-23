# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2025-10-19

### 🎉 Initial Public Release

**SnowTower v0.1.0** - Enterprise Snowflake infrastructure management platform.

This is the first public release of SnowTower, featuring a complete infrastructure-as-code solution for Snowflake with built-in safety mechanisms, automated deployment, and comprehensive documentation.

### Added

#### Core Features
- **Declarative Infrastructure Management** - YAML-based SnowDDL configuration for all Snowflake objects
- **Multi-Layer Security** - RSA key authentication, network policies, MFA compliance tracking
- **Automated CI/CD** - GitHub Actions workflows for validation and deployment
- **User Lifecycle Management** - Complete user onboarding, authentication, and access control
- **Cost Optimization** - Built-in cost monitoring and warehouse optimization tools
- **Web Interface** - Streamlit dashboard for visual management and operations
- **Safety Architecture** - Multi-tiered agent system preventing dangerous operations

#### Management Commands (50+ via UV)
- `uv run snowddl-plan` / `uv run snowddl-apply` - Infrastructure deployment
- `uv run manage-users` - User lifecycle management
- `uv run manage-warehouses` - Warehouse optimization
- `uv run manage-costs` - Cost analysis and reporting
- `uv run manage-security` - Security audits and compliance
- `uv run monitor-health` - System health monitoring
- `uv run web` - Launch Streamlit dashboard

#### Documentation
- Comprehensive README with user access guide and admin documentation
- 5-minute quickstart guide
- Complete configuration reference
- Architecture documentation and design patterns
- Troubleshooting guides with common solutions
- Agent system documentation for AI-assisted operations
- User management guides with authentication options

#### Security Features
- RSA key-pair authentication (primary method)
- Encrypted password fallback (Fernet encryption)
- Network policy enforcement with IP restrictions
- MFA compliance tracking and enforcement timeline
- Multi-factor authentication policies

#### Infrastructure Components
- User and role management system
- Database and schema configurations
- Warehouse auto-suspend and scaling policies
- Resource monitors with cost controls
- Network and authentication policies
- Storage integrations and external stages

### Changed
- Consolidated project from dual-repository to unified platform architecture
- Migrated all CLI functionality into single `snowtower-snowddl` repository
- Streamlined agent system from 16 to 7 specialized agents (78% reduction)
- Updated all documentation for public release (genericized sensitive data)
- Reorganized documentation structure for better discoverability

### Removed
- Internal development documentation and troubleshooting notes
- Test credentials and example keys
- Private account-specific references
- Duplicate and redundant documentation files
- Development-only markdown files

### Security
- All sensitive information redacted/genericized for public release
- Account IDs, emails, and IP addresses replaced with examples
- Emergency account references updated to generic names
- No private keys or credentials in repository (gitignored)

---

## Types of Changes
- 👥 **Users**: User account additions, modifications, or removals
- 🗄️ **Databases**: Database creation, configuration changes
- 👑 **Roles**: Role creation, permission updates
- 🏭 **Warehouses**: Warehouse configuration changes
- 🔐 **Policies**: Security and access policy updates
- 📝 **Other**: Documentation, configuration, or other changes

---

## Previous Development History

# Infrastructure Change Log

All notable infrastructure changes to this project are documented in this file.


## [2025-10-10] - Infrastructure Update

### Changed
- chore: Update pre-commit hooks to latest versions
- docs: Consolidate documentation and agent architecture (82% reduction)
- docs: update changelog for deployment 2560880c
- fix: remove invalid SCHEMA grants from future_grants
- docs: add comprehensive DLT privilege troubleshooting documentation
- feat: enable sandbox mode for PROJ_STRIPE database
- feat: add DBT_SERVICE service account for dbt Cloud
- fix: set SNOWFLAKE_ROLE to ACCOUNTADMIN for DLT pipeline access

### Infrastructure Changes
- Add LightDash BI platform service account with enterprise security (cce2026)
- fix: remove invalid SCHEMA grants from future_grants (2c31ae3)
- Merge branch 'feature/proj-stripe-sandbox-mode' into main (cc6e2ba)
- feat: enable sandbox mode for PROJ_STRIPE database (c234547)
- feat: add DBT_SERVICE service account for dbt Cloud (a0b046a)

### Deployment Info
- **Commit:** dd74b52c
- **Timestamp:** 2025-10-10 11:20:01 UTC
- **Triggered by:** example-user



## [2025-10-09] - Infrastructure Update

### Changed
- fix: remove invalid SCHEMA grants from future_grants
- docs: add comprehensive DLT privilege troubleshooting documentation
- feat: enable sandbox mode for PROJ_STRIPE database
- feat: add DBT_SERVICE service account for dbt Cloud
- fix: set SNOWFLAKE_ROLE to ACCOUNTADMIN for DLT pipeline access
- docs: Add comprehensive SnowDDL schema management guide
- fix: Convert schema.yaml files to proper directory-based structure
- docs: update changelog for deployment 5f54270a
- fix: Re-add SCHEMA to excluded object types to prevent SnowDDL from dropping schemas
- docs: update changelog for deployment 92a59206

### Infrastructure Changes
- fix: remove invalid SCHEMA grants from future_grants (2c31ae3)
- Merge branch 'feature/proj-stripe-sandbox-mode' into main (cc6e2ba)
- feat: enable sandbox mode for PROJ_STRIPE database (c234547)
- feat: add DBT_SERVICE service account for dbt Cloud (a0b046a)
- fix: Convert schema.yaml files to proper directory-based structure (80dd7e9)

### Deployment Info
- **Commit:** 2560880c
- **Timestamp:** 2025-10-09 11:38:41 UTC
- **Triggered by:** example-user



## [2025-10-06] - Infrastructure Update

### Changed
- fix: Re-add SCHEMA to excluded object types to prevent SnowDDL from dropping schemas
- docs: update changelog for deployment 92a59206
- docs: update changelog for deployment 2f86322e
- fix: Remove SCHEMA from excluded object types to allow schema deployment
- docs: update changelog for deployment 577ce2aa
- fix: Always use --apply-unsafe in CI/CD deployments
- fix: Correct owner_tech_role to use full SnowDDL role name
- docs: update changelog for deployment 6b565888
- docs: update changelog for deployment b1eb7d33

### Infrastructure Changes
- refactor: Remove owner_tech_role from PROJ_STRIPE schema config (92a5920)
- fix: Correct owner_tech_role to use full SnowDDL role name (c67b395)

### Deployment Info
- **Commit:** 5f54270a
- **Timestamp:** 2025-10-06 16:11:13 UTC
- **Triggered by:** example-user



## [2025-10-06] - Infrastructure Update

### Changed
- docs: update changelog for deployment 2f86322e
- fix: Remove SCHEMA from excluded object types to allow schema deployment
- docs: update changelog for deployment 577ce2aa
- fix: Always use --apply-unsafe in CI/CD deployments
- fix: Correct owner_tech_role to use full SnowDDL role name
- docs: update changelog for deployment 6b565888
- docs: update changelog for deployment b1eb7d33
- fix: Add missing base64 and tempfile imports to apply() function
- docs: update changelog for deployment 49b83b92

### Infrastructure Changes
- refactor: Remove owner_tech_role from PROJ_STRIPE schema config (92a5920)
- fix: Correct owner_tech_role to use full SnowDDL role name (c67b395)

### Deployment Info
- **Commit:** 92a59206
- **Timestamp:** 2025-10-06 16:03:25 UTC
- **Triggered by:** example-user



## [2025-10-06] - Infrastructure Update

### Changed
- fix: Remove SCHEMA from excluded object types to allow schema deployment
- docs: update changelog for deployment 577ce2aa
- fix: Always use --apply-unsafe in CI/CD deployments
- fix: Correct owner_tech_role to use full SnowDDL role name
- docs: update changelog for deployment 6b565888
- docs: update changelog for deployment b1eb7d33
- fix: Add missing base64 and tempfile imports to apply() function
- docs: update changelog for deployment 49b83b92
- fix: Add private key handling to apply() function
- docs: update changelog for deployment 9dc58e37

### Infrastructure Changes
- fix: Correct owner_tech_role to use full SnowDDL role name (c67b395)

### Deployment Info
- **Commit:** 2f86322e
- **Timestamp:** 2025-10-06 15:51:16 UTC
- **Triggered by:** example-user



## [2025-10-06] - Infrastructure Update

### Changed
- fix: Always use --apply-unsafe in CI/CD deployments
- fix: Correct owner_tech_role to use full SnowDDL role name
- docs: update changelog for deployment 6b565888
- docs: update changelog for deployment b1eb7d33
- fix: Add missing base64 and tempfile imports to apply() function
- docs: update changelog for deployment 49b83b92
- fix: Add private key handling to apply() function
- docs: update changelog for deployment 9dc58e37
- fix: Add future_grants to STRIPE role to prevent permission revocations
- fix: Add !ENV tag support to security scanner
- fix: Add !ENV tag support to YAML validator
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema

### Infrastructure Changes
- fix: Correct owner_tech_role to use full SnowDDL role name (c67b395)
- fix: Add future_grants to STRIPE role to prevent permission revocations (2182785)
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema (9e0ea3e)

### Deployment Info
- **Commit:** 577ce2aa
- **Timestamp:** 2025-10-06 13:11:07 UTC
- **Triggered by:** example-user



## [2025-10-06] - Infrastructure Update

### Changed
- docs: update changelog for deployment b1eb7d33
- fix: Add missing base64 and tempfile imports to apply() function
- docs: update changelog for deployment 49b83b92
- fix: Add private key handling to apply() function
- docs: update changelog for deployment 9dc58e37
- fix: Add future_grants to STRIPE role to prevent permission revocations
- fix: Add !ENV tag support to security scanner
- fix: Add !ENV tag support to YAML validator
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema
- docs: update changelog for deployment f6fccbca

### Infrastructure Changes
- fix: Add future_grants to STRIPE role to prevent permission revocations (2182785)
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema (9e0ea3e)
- Add GitHub token secret management for Streamlit automation (fefb0f7)

### Deployment Info
- **Commit:** 6b565888
- **Timestamp:** 2025-10-06 12:43:12 UTC
- **Triggered by:** example-user



## [2025-10-06] - Infrastructure Update

### Changed
- fix: Add missing base64 and tempfile imports to apply() function
- docs: update changelog for deployment 49b83b92
- fix: Add private key handling to apply() function
- docs: update changelog for deployment 9dc58e37
- fix: Add future_grants to STRIPE role to prevent permission revocations
- fix: Add !ENV tag support to security scanner
- fix: Add !ENV tag support to YAML validator
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema
- docs: update changelog for deployment f6fccbca

### Infrastructure Changes
- fix: Add future_grants to STRIPE role to prevent permission revocations (2182785)
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema (9e0ea3e)
- Add GitHub token secret management for Streamlit automation (fefb0f7)

### Deployment Info
- **Commit:** b1eb7d33
- **Timestamp:** 2025-10-06 12:23:08 UTC
- **Triggered by:** example-user



## [2025-10-06] - Infrastructure Update

### Changed
- fix: Add private key handling to apply() function
- docs: update changelog for deployment 9dc58e37
- fix: Add future_grants to STRIPE role to prevent permission revocations
- fix: Add !ENV tag support to security scanner
- fix: Add !ENV tag support to YAML validator
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema
- docs: update changelog for deployment f6fccbca
- docs: update changelog for deployment 090461f8

### Infrastructure Changes
- fix: Add future_grants to STRIPE role to prevent permission revocations (2182785)
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema (9e0ea3e)
- Add GitHub token secret management for Streamlit automation (fefb0f7)

### Deployment Info
- **Commit:** 49b83b92
- **Timestamp:** 2025-10-06 12:17:51 UTC
- **Triggered by:** example-user



## [2025-10-06] - Infrastructure Update

### Changed
- fix: Add future_grants to STRIPE role to prevent permission revocations
- fix: Add !ENV tag support to security scanner
- fix: Add !ENV tag support to YAML validator
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema
- docs: update changelog for deployment f6fccbca
- docs: update changelog for deployment 090461f8

### Infrastructure Changes
- fix: Add future_grants to STRIPE role to prevent permission revocations (2182785)
- feat: Rename PC_DBT_ROLE to DBT_STRIPE_ROLE and add ANALYTICS_TOOL.PROJ_STRIPE schema (9e0ea3e)
- Add GitHub token secret management for Streamlit automation (fefb0f7)

### Deployment Info
- **Commit:** 9dc58e37
- **Timestamp:** 2025-10-06 12:05:36 UTC
- **Triggered by:** example-user



## [2025-10-04] - Infrastructure Update

### Changed
- docs: update changelog for deployment 090461f8
- docs: update changelog for deployment 5c60d94f
- docs: update changelog for deployment 53a75c83

### Infrastructure Changes


### Deployment Info
- **Commit:** f6fccbca
- **Timestamp:** 2025-10-04 15:05:46 UTC
- **Triggered by:** example-user



## [2025-10-03] - Infrastructure Update

### Changed
- docs: update changelog for deployment 5c60d94f
- docs: update changelog for deployment 53a75c83
- docs: update changelog for deployment 9c8182fd

### Infrastructure Changes
- Refactor: Standardize YAML formatting across all SnowDDL config files (0fc0652)

### Deployment Info
- **Commit:** 090461f8
- **Timestamp:** 2025-10-03 15:15:20 UTC
- **Triggered by:** example-user



## [2025-10-02] - Infrastructure Update

### Changed
- docs: update changelog for deployment 53a75c83
- docs: update changelog for deployment 9c8182fd
- docs: update changelog for deployment 4d743282

### Infrastructure Changes
- Refactor: Standardize YAML formatting across all SnowDDL config files (0fc0652)

### Deployment Info
- **Commit:** 5c60d94f
- **Timestamp:** 2025-10-02 20:59:43 UTC
- **Triggered by:** example-user



## [2025-10-02] - Infrastructure Update

### Changed
- docs: update changelog for deployment 9c8182fd
- docs: update changelog for deployment 4d743282
- docs: update changelog for deployment 6b0b6aff

### Infrastructure Changes
- Refactor: Standardize YAML formatting across all SnowDDL config files (0fc0652)
- Add GitHub issue template and cleanup (6b0b6af)

### Deployment Info
- **Commit:** 53a75c83
- **Timestamp:** 2025-10-02 17:52:10 UTC
- **Triggered by:** example-user



## [2025-10-02] - Infrastructure Update

### Changed
- docs: update changelog for deployment 4d743282
- docs: update changelog for deployment 6b0b6aff
- docs: update changelog for deployment 74eebbee

### Infrastructure Changes
- Add GitHub issue template and cleanup (6b0b6af)

### Deployment Info
- **Commit:** 9c8182fd
- **Timestamp:** 2025-10-02 17:48:19 UTC
- **Triggered by:** example-user



## [2025-10-02] - Infrastructure Update

### Changed
- docs: update changelog for deployment 6b0b6aff
- docs: update changelog for deployment 74eebbee
- docs: update changelog for deployment f51d76fa

### Infrastructure Changes
- Add GitHub issue template and cleanup (6b0b6af)

### Deployment Info
- **Commit:** 4d743282
- **Timestamp:** 2025-10-02 13:14:36 UTC
- **Triggered by:** example-user



## [2025-10-02] - Infrastructure Update

### Changed
- docs: update changelog for deployment 74eebbee
- docs: update changelog for deployment f51d76fa
- feat: Add essential infrastructure updates and monitoring
- docs: Consolidate documentation and create organized structure

### Infrastructure Changes
- Add GitHub issue template and cleanup (6b0b6af)
- feat: Add essential infrastructure updates and monitoring (57e707c)

### Deployment Info
- **Commit:** 6b0b6aff
- **Timestamp:** 2025-10-02 12:31:37 UTC
- **Triggered by:** example-user



## [2025-10-02] - Infrastructure Update

### Changed
- docs: update changelog for deployment f51d76fa
- feat: Add essential infrastructure updates and monitoring
- docs: Consolidate documentation and create organized structure
- docs: update changelog for deployment 5e56e0ca

### Infrastructure Changes
- feat: Add essential infrastructure updates and monitoring (57e707c)

### Deployment Info
- **Commit:** 74eebbee
- **Timestamp:** 2025-10-02 12:02:58 UTC
- **Triggered by:** example-user



## [2025-10-02] - Infrastructure Update

### Changed
- feat: Add essential infrastructure updates and monitoring
- docs: Consolidate documentation and create organized structure
- docs: update changelog for deployment 5e56e0ca
- docs: Consolidate CI/CD documentation into main README
- Merge pull request #13 from Database-Tycoon/feature/snowddl-documentation-improvements
- docs: Add SnowDDL explanation and fix default warehouse reference
- docs: modernize README diagrams from ASCII to Mermaid
- docs: soften documentation tone and improve accessibility
- docs: update changelog for deployment a01dd367

### Infrastructure Changes
- feat: Add essential infrastructure updates and monitoring (57e707c)

### Deployment Info
- **Commit:** f51d76fa
- **Timestamp:** 2025-10-02 11:49:29 UTC
- **Triggered by:** example-user



## [2025-09-28] - Infrastructure Update

### Changed
- docs: Consolidate CI/CD documentation into main README
- Merge pull request #13 from Database-Tycoon/feature/snowddl-documentation-improvements
- docs: Add SnowDDL explanation and fix default warehouse reference
- docs: modernize README diagrams from ASCII to Mermaid
- docs: soften documentation tone and improve accessibility
- docs: update changelog for deployment a01dd367
- docs: clarify system-managed password policy and user restrictions

### Infrastructure Changes


### Deployment Info
- **Commit:** 5e56e0ca
- **Timestamp:** 2025-09-28 19:29:20 UTC
- **Triggered by:** example-user



## [2025-09-28] - Infrastructure Update

### Changed
- docs: clarify system-managed password policy and user restrictions
- docs: update changelog for deployment 445dd9a4
- docs: update changelog for deployment da12aff1
- Merge pull request #12 from Database-Tycoon/feature/oop-framework
- feat: Simplify Streamlit app to use existing SnowDDL-managed stages
- feat: Enhanced IAM role setup guidance in S3 configuration wizard
- feat: Complete GitOps workflow for S3-to-Git configuration sync
- feat: Add GitHub integration system for automated PR creation
- fix: Update snowflake.yml to use correct streamlit_app.py path
- feat: Add S3 integration infrastructure and documentation
- feat: Enhanced Snow Tower Streamlit app with S3 configuration wizard
- feat: Add form-based configuration editor and Snowflake UI deep links
- feat: Bundle SnowDDL configuration files with Streamlit app
- fix: Update entry points to use management_cli wrappers for CI compatibility
- fix: Critical snowddl-plan command now working
- feat: Database Manager with ownership separation and detailed info
- feat: Enhanced Database Manager with ownership separation
- fix: Keep version at v0.1 per user request
- feat: Add Database Manager to SnowTower Streamlit v0.2
- feat: Add SnowTower Honest Edition v0.1 - Minimal Streamlit interface

### Infrastructure Changes
- Add SNOWTOWER_MONITOR resource monitor definition (c921112)
- Add missing critical integration roles to prevent drops (e768b9b)
- feat: Simplify Streamlit app to use existing SnowDDL-managed stages (a212219)
- feat: Add S3 integration infrastructure and documentation (8709f05)
- fix: Critical snowddl-plan command now working (94f8e41)
- feat: add STREAMLIT_VIEWER role for SnowTower v0.1 (8ed177a)
- revert: restore Heather's RSA key (commented) for future fixing (3fddfad)
- fix: remove invalid RSA key from Heather's configuration (9869863)

### Deployment Info
- **Commit:** a01dd367
- **Timestamp:** 2025-09-28 17:44:33 UTC
- **Triggered by:** example-user



## [2025-09-28] - Infrastructure Update

### Changed
- docs: update changelog for deployment da12aff1
- Merge pull request #12 from Database-Tycoon/feature/oop-framework
- feat: Simplify Streamlit app to use existing SnowDDL-managed stages
- feat: Enhanced IAM role setup guidance in S3 configuration wizard
- feat: Complete GitOps workflow for S3-to-Git configuration sync
- feat: Add GitHub integration system for automated PR creation
- fix: Update snowflake.yml to use correct streamlit_app.py path
- feat: Add S3 integration infrastructure and documentation
- feat: Enhanced Snow Tower Streamlit app with S3 configuration wizard
- feat: Add form-based configuration editor and Snowflake UI deep links
- feat: Bundle SnowDDL configuration files with Streamlit app
- fix: Update entry points to use management_cli wrappers for CI compatibility
- fix: Critical snowddl-plan command now working
- feat: Database Manager with ownership separation and detailed info
- feat: Enhanced Database Manager with ownership separation
- fix: Keep version at v0.1 per user request
- feat: Add Database Manager to SnowTower Streamlit v0.2
- feat: Add SnowTower Honest Edition v0.1 - Minimal Streamlit interface
- feat: Implement self-service Snowflake access request system
- feat: Fixed Streamlit app for Snowflake deployment - removed SHOW commands

### Infrastructure Changes
- Add SNOWTOWER_MONITOR resource monitor definition (c921112)
- Add missing critical integration roles to prevent drops (e768b9b)
- feat: Simplify Streamlit app to use existing SnowDDL-managed stages (a212219)
- feat: Add S3 integration infrastructure and documentation (8709f05)
- fix: Critical snowddl-plan command now working (94f8e41)
- feat: add STREAMLIT_VIEWER role for SnowTower v0.1 (8ed177a)
- revert: restore Heather's RSA key (commented) for future fixing (3fddfad)
- fix: remove invalid RSA key from Heather's configuration (9869863)
- feat: implement intelligent SnowDDL apply with automatic flag detection (ba5f2f1)
- security: CRITICAL security audit and remediation complete (9a5071a)

### Deployment Info
- **Commit:** 445dd9a4
- **Timestamp:** 2025-09-28 16:54:31 UTC
- **Triggered by:** example-user



## [2025-09-28] - Infrastructure Update

### Changed
- Merge pull request #12 from Database-Tycoon/feature/oop-framework
- feat: Simplify Streamlit app to use existing SnowDDL-managed stages
- feat: Enhanced IAM role setup guidance in S3 configuration wizard
- feat: Complete GitOps workflow for S3-to-Git configuration sync
- feat: Add GitHub integration system for automated PR creation
- fix: Update snowflake.yml to use correct streamlit_app.py path
- feat: Add S3 integration infrastructure and documentation
- feat: Enhanced Snow Tower Streamlit app with S3 configuration wizard
- feat: Add form-based configuration editor and Snowflake UI deep links
- feat: Bundle SnowDDL configuration files with Streamlit app
- fix: Update entry points to use management_cli wrappers for CI compatibility
- fix: Critical snowddl-plan command now working
- feat: Database Manager with ownership separation and detailed info
- feat: Enhanced Database Manager with ownership separation
- fix: Keep version at v0.1 per user request
- feat: Add Database Manager to SnowTower Streamlit v0.2
- feat: Add SnowTower Honest Edition v0.1 - Minimal Streamlit interface
- feat: Implement self-service Snowflake access request system
- feat: Fixed Streamlit app for Snowflake deployment - removed SHOW commands
- feat: add STREAMLIT_VIEWER role for SnowTower v0.1

### Infrastructure Changes
- Add SNOWTOWER_MONITOR resource monitor definition (c921112)
- Add missing critical integration roles to prevent drops (e768b9b)
- feat: Simplify Streamlit app to use existing SnowDDL-managed stages (a212219)
- feat: Add S3 integration infrastructure and documentation (8709f05)
- fix: Critical snowddl-plan command now working (94f8e41)
- feat: add STREAMLIT_VIEWER role for SnowTower v0.1 (8ed177a)
- revert: restore Heather's RSA key (commented) for future fixing (3fddfad)
- fix: remove invalid RSA key from Heather's configuration (9869863)
- feat: implement intelligent SnowDDL apply with automatic flag detection (ba5f2f1)
- security: CRITICAL security audit and remediation complete (9a5071a)

### Deployment Info
- **Commit:** da12aff1
- **Timestamp:** 2025-09-28 16:46:09 UTC
- **Triggered by:** example-user



## [2025-09-23] - Infrastructure Update

### Changed
- feat: implement intelligent SnowDDL apply with automatic flag detection
- docs: update changelog for deployment 9a5071ae
- docs: update changelog for deployment 0828bbc6
- fix: update CAROL's password and RSA key formatting
- fix: add backup directories to gitignore and rename .backups to _backups
- feat: add password encryption script and update CAROL's encrypted password
- fix: remove duplicate changelog workflow
- fix: remove duplicate workflows causing simultaneous runs
- fix: remove problematic auto-approval step from PR validation workflow
- fix: update YAML security scanner to handle SnowDDL !decrypt tags
- fix: update production deployment workflow for current implementation
- docs: update agents with GitHub Actions success story and troubleshooting
- docs: add GitHub Actions secrets setup instructions
- fix: handle workflow_dispatch and improve private key error messages
- feat: add better error handling for SnowDDL plan generation
- fix: use UV environment for YAML security scan script
- fix: prevent bandit exit code from failing workflow
- feat: add workflow_dispatch triggers to all GitHub Actions workflows
- fix: correct safety command syntax and modernize pyproject.toml
- fix: resolve GitHub Actions PR validation workflow failures

### Infrastructure Changes
- feat: implement intelligent SnowDDL apply with automatic flag detection (ba5f2f1)
- security: CRITICAL security audit and remediation complete (9a5071a)
- fix: update CAROL's password and RSA key formatting (0828bbc)
- feat: add password encryption script and update CAROL's encrypted password (612b807)
- Merge main into heather branch (39948c4)
- fix: correct Heather's RSA public key base64 padding (6917948)
- docs: update workflow badges and test deployment workflow (295c5fb)
- Heather's User rsa key (9cfe0a3)

### Deployment Info
- **Commit:** 5f0308bb
- **Timestamp:** 2025-09-23 18:24:08 UTC
- **Triggered by:** example-user



## [2025-09-22] - Infrastructure Update

### Changed
- docs: update changelog for deployment 0828bbc6
- fix: update CAROL's password and RSA key formatting
- fix: add backup directories to gitignore and rename .backups to _backups
- feat: add password encryption script and update CAROL's encrypted password
- fix: remove duplicate changelog workflow
- fix: remove duplicate workflows causing simultaneous runs
- fix: remove problematic auto-approval step from PR validation workflow
- fix: update YAML security scanner to handle SnowDDL !decrypt tags
- fix: update production deployment workflow for current implementation
- docs: update agents with GitHub Actions success story and troubleshooting
- docs: add GitHub Actions secrets setup instructions
- fix: handle workflow_dispatch and improve private key error messages
- feat: add better error handling for SnowDDL plan generation
- fix: use UV environment for YAML security scan script
- fix: prevent bandit exit code from failing workflow
- feat: add workflow_dispatch triggers to all GitHub Actions workflows
- fix: correct safety command syntax and modernize pyproject.toml
- fix: resolve GitHub Actions PR validation workflow failures
- feat: add comprehensive resource monitor configuration
- fix: correct Heather's RSA public key base64 padding

### Infrastructure Changes
- security: CRITICAL security audit and remediation complete (9a5071a)
- fix: update CAROL's password and RSA key formatting (0828bbc)
- feat: add password encryption script and update CAROL's encrypted password (612b807)
- Merge main into heather branch (39948c4)
- fix: correct Heather's RSA public key base64 padding (6917948)
- docs: update workflow badges and test deployment workflow (295c5fb)
- Heather's User rsa key (9cfe0a3)

### Deployment Info
- **Commit:** 9a5071ae
- **Timestamp:** 2025-09-22 22:55:28 UTC
- **Triggered by:** example-user



## [2025-09-22] - Infrastructure Update

### Changed
- fix: update CAROL's password and RSA key formatting
- fix: add backup directories to gitignore and rename .backups to _backups
- feat: add password encryption script and update CAROL's encrypted password
- fix: remove duplicate changelog workflow
- fix: remove duplicate workflows causing simultaneous runs
- fix: remove problematic auto-approval step from PR validation workflow
- fix: update YAML security scanner to handle SnowDDL !decrypt tags
- fix: update production deployment workflow for current implementation
- docs: update agents with GitHub Actions success story and troubleshooting
- docs: add GitHub Actions secrets setup instructions
- fix: handle workflow_dispatch and improve private key error messages
- feat: add better error handling for SnowDDL plan generation
- fix: use UV environment for YAML security scan script
- fix: prevent bandit exit code from failing workflow
- feat: add workflow_dispatch triggers to all GitHub Actions workflows
- fix: correct safety command syntax and modernize pyproject.toml
- fix: resolve GitHub Actions PR validation workflow failures
- feat: add comprehensive resource monitor configuration
- fix: correct Heather's RSA public key base64 padding
- docs: update changelog for deployment 295c5fb4

### Infrastructure Changes
- fix: update CAROL's password and RSA key formatting (0828bbc)
- feat: add password encryption script and update CAROL's encrypted password (612b807)
- Merge main into heather branch (39948c4)
- fix: correct Heather's RSA public key base64 padding (6917948)
- docs: update workflow badges and test deployment workflow (295c5fb)
- Heather's User rsa key (9cfe0a3)

### Deployment Info
- **Commit:** 0828bbc6
- **Timestamp:** 2025-09-22 19:48:13 UTC
- **Triggered by:** example-user



## [2025-09-22] - Infrastructure Update

### Changed
- docs: update workflow badges and test deployment workflow
- fix: consolidate GitHub Actions workflows and fix UV command issues
- Merge pull request #10 from Database-Tycoon/feature/docs-on-snowflake
- feat: implement Snowflake-native documentation hosting system
- docs+build: comprehensive documentation and build system improvements
- docs: enhance self-service guide clarity
- docs: enhance quickstart guide readability
- docs: improve documentation consistency
- docs: improve formatting consistency and readability
- docs: Initialize CHANGELOG.md
- chore: Revert weekly monitor to 55 credits

### Infrastructure Changes
- docs: update workflow badges and test deployment workflow (295c5fb)
- chore: Revert weekly monitor to 55 credits (72b3144)

### Deployment Info
- **Commit:** 295c5fb4
- **Timestamp:** 2025-09-22 14:53:59 UTC
- **Triggered by:** example-user


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Types of Changes
- 👥 **Users**: User account additions, modifications, or removals
- 🗄️ **Databases**: Database creation, configuration changes
- 👑 **Roles**: Role creation, permission updates
- 🏭 **Warehouses**: Warehouse configuration changes
- 🔐 **Policies**: Security and access policy updates
- 📝 **Other**: Documentation, configuration, or other changes

---
