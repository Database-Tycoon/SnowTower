# Changelog

All notable changes to SnowTower are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.3.0] - 2026-02-22

### Added
- `validate-config` command: Pre-deployment YAML validation with cross-reference integrity checks
- `generate-terraform` command: Convert SnowDDL YAML to Terraform HCL with import blocks
- Integration test suite: 58 tests covering CLI, authentication, YAML validation, deployment workflows
- Secrets scanning: detect-secrets pre-commit hook + TruffleHog CI job
- `validate-config` pre-commit hook for automatic YAML validation on commit
- `validate-config` CI step for validation on every push/PR
- Terraform boilerplate example output in `terraform-snowflake-boilerplate/`
- Unit tests for `validate_config.py` and `generate_terraform.py`

### Changed
- Consolidated `.claude` resources: ~2,900 lines across 13 files reduced to ~580 lines across 5 files
- Rewrote 4 Claude Code skills as concise task guides (~60-116 lines each)
- Enhanced root `CLAUDE.md` as single source of truth with SnowDDL knowledge base
- Version bumped to 0.3.0

### Fixed
- Mismatched `default_role` references in `user.yaml` (ANALYST__B_ROLE, DLT_INGESTION_ROLE__B_ROLE)
- Stale references to nonexistent `.claude/agents/` directory
- Dead links to deleted `docs/llm-context/` directory

### Removed
- `docs/llm-context/` directory (4 files) - consolidated into root CLAUDE.md
- Redundant skill files (developer README/CHANGELOG, maintainer PROJECT_STRUCTURE, skills README)

## [0.2.0] - 2025-10-15

### Added
- Claude Code skills: snowtower-user, snowtower-admin, snowtower-developer, snowtower-maintainer
- CI/CD workflows: lint, test, secrets scanning via GitHub Actions
- PR template and issue templates
- CONTRIBUTING.md with development guidelines
- Pre-commit hooks for code formatting and YAML validation
- ASCII banner command (`snowtower-banner`)

### Changed
- Consolidated from dual-repo to single unified platform
- Updated README with badges and improved documentation

## [0.1.0] - 2025-08-01

### Added
- Initial release of SnowTower enterprise Snowflake infrastructure management
- SnowDDL YAML-based infrastructure definitions (users, roles, warehouses, policies)
- User management with Fernet encryption and RSA key authentication
- OOP framework for SnowDDL operations (`snowddl_core`)
- Management CLI: warehouses, costs, security, backup, users
- Monitoring: health, audit, metrics
- Deploy-safe wrapper with safety checks
- Network, authentication, password, and session policies
- Resource monitors with trigger configuration
- Comprehensive documentation (README, QUICKSTART, RSA_KEY_SETUP)
- MFA compliance tracking for Snowflake 2025-2026 rollout
- 25+ CLI commands across 7 categories

**Full Changelog**: https://github.com/Database-Tycoon/SnowTower/commits/main
