# SnowTower v0.2.0 Release Notes

**Release Date:** January 2026
**Focus:** CI/CD & Developer Experience

---

## Highlights

- **Automated CI/CD**: Every PR now runs 333 tests and linting automatically
- **Release Automation**: Just push a tag and GitHub creates the release with changelog
- **Claude Code Skills**: 3 focused skills replace 24 redundant agent files
- **Streamlined Contributing**: Clear workflow with CONTRIBUTING.md and PR templates

---

## New Features

### CI/CD Workflows

| Workflow | Purpose |
|----------|---------|
| `ci.yml` | Runs lint + 333 tests on every PR |
| `release.yml` | Auto-generates releases from tags |
| `labeler.yml` | Auto-labels PRs by file type |
| `changelog.yml` | Keeps changelog updated |

### GitHub Integration

- **PR Template**: Standardized format for all pull requests
- **Issue Template**: Self-service new user request form
- **Auto-labeling**: PRs automatically tagged (`infrastructure`, `documentation`, `python`, etc.)
- **Branch Protection**: `main` and `v*` branches require PRs and CI passing

### Claude Code Skills

Replaced 24 redundant agent files with 3 focused skills:

| Skill | Purpose |
|-------|---------|
| `snowtower-user` | End-users: access requests, connecting to Snowflake |
| `snowtower-admin` | Admins: SnowDDL operations, user management, troubleshooting |
| `snowtower-maintainer` | Project maintenance: README updates, documentation sync |

### Documentation

- **CONTRIBUTING.md**: Complete guide to branch strategy and PR workflow
- **Updated README**: Accurate CI/CD section with workflow diagrams
- **Reorganized docs**: `docs/agents/` renamed to `docs/llm-context/`

---

## Breaking Changes

None. This release is fully backwards compatible with v0.1.

---

## Upgrade Guide

```bash
# Pull latest changes
git pull origin main

# Install dependencies (no changes to requirements)
uv sync

# Verify everything works
uv run pytest
uv run snowddl-plan
```

---

## What's Next (v0.3 Roadmap)

Features deferred from v0.2 for future consideration:

- **Drift Detection Workflow**: Scheduled job to detect configuration drift
- **Issue → PR Automation**: Auto-generate PRs from user request issues
- **Scheduled Health Checks**: Daily/weekly automated infrastructure validation
- **Enhanced Test Coverage**: Target >80% coverage

---

## Contributors

- Database Tycoon Team
- Claude Code

---

## Links

- [Full Changelog](../CHANGELOG.md)
- [v0.2 Proposal](PROPOSAL.md)
- [GitHub Repository](https://github.com/Database-Tycoon/SnowTower)
