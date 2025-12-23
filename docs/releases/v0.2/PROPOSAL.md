# SnowTower v0.2 Release Proposal

**Focus Area**: CI/CD & GitHub Management
**Target**: Q1 2026
**Status**: Planning

---

## Executive Summary

Version 0.2 will transform SnowTower from a local infrastructure management tool into a fully automated GitOps platform. The release focuses on three pillars:

1. **GitHub Actions Workflows** - Automated testing, validation, and deployment
2. **GitHub Integration Features** - PR automation and issue-driven infrastructure
3. **Release Automation** - Changelog generation, versioning, and publishing

---

## Feature 1: GitHub Actions Workflows

### 1.1 CI Pipeline (Pull Requests)

**File**: `.github/workflows/ci.yml`

Triggers on every PR to `main`:

```yaml
- Run pytest (all 333+ tests)
- Run pre-commit (Black, YAML validation, secrets scanning)
- Run snowddl-plan (dry-run validation)
- Post plan output as PR comment
- Block merge if tests fail
```

**Benefits**:
- Catches breaking changes before merge
- Shows infrastructure diff in PR for review
- Ensures code quality standards

### 1.2 CD Pipeline (Releases)

**File**: `.github/workflows/release.yml`

Triggers on version tags (`v*`):

```yaml
- Build and validate package
- Generate changelog from commits
- Create GitHub Release with notes
- Publish to PyPI (optional, future)
```

### 1.3 Scheduled Health Checks

**File**: `.github/workflows/scheduled.yml`

Daily/weekly automated checks:

```yaml
- Dependency security audit (uv audit)
- Documentation link checker
- License compliance check
```

---

## Feature 2: GitHub Integration Features

### 2.1 PR-Based Infrastructure Changes

When a PR modifies `snowddl/*.yaml` files:

1. **Auto-label** PRs with `infrastructure`, `user-change`, `security`, etc.
2. **Run `snowddl-plan`** and post diff as PR comment
3. **Require approval** from designated reviewers for sensitive changes
4. **On merge**: Optionally trigger `snowddl-apply` (with safeguards)

### 2.2 Issue-Driven User Provisioning

Integrate the GitHub issue → SnowDDL user creation workflow:

1. User submits "New User Request" issue using template
2. GitHub Action parses issue, generates YAML config
3. Creates PR with new user configuration
4. On approval + merge, user is provisioned

**Files to include**:
- `.github/ISSUE_TEMPLATE/new-user-request.yml`
- `.github/workflows/process-user-request.yml`
- `scripts/generate_user_from_issue.py` (already exists)

### 2.3 Drift Detection

Scheduled workflow to detect configuration drift:

```yaml
- Run snowddl-plan against live Snowflake
- If drift detected, create issue with details
- Alert via Slack/email (configurable)
```

---

## Feature 3: Release Automation

### 3.1 Semantic Versioning

Adopt conventional commits for automatic versioning:

- `feat:` → minor version bump
- `fix:` → patch version bump
- `BREAKING CHANGE:` → major version bump

### 3.2 Changelog Generation

Auto-generate `CHANGELOG.md` from commit messages:

- Group by type (Features, Fixes, Breaking Changes)
- Link to PRs and issues
- Include contributor credits

### 3.3 Release Checklist Automation

**File**: `.github/workflows/release-checklist.yml`

Pre-release validation:

```yaml
- All tests pass
- No security vulnerabilities
- Documentation updated
- Version bumped in pyproject.toml
- CHANGELOG updated
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1-2)

| Task | Priority | Effort |
|------|----------|--------|
| Create CI workflow (tests + pre-commit) | P0 | 2 hours |
| Add snowddl-plan to PR checks | P0 | 2 hours |
| Set up branch protection rules | P0 | Done ✅ |
| Create PR template | P1 | 1 hour |

### Phase 2: PR Automation (Week 3-4)

| Task | Priority | Effort |
|------|----------|--------|
| Auto-labeling based on changed files | P1 | 2 hours |
| Post plan output as PR comment | P1 | 3 hours |
| Add required reviewers for sensitive files | P1 | 1 hour |

### Phase 3: Issue Integration (Week 5-6)

| Task | Priority | Effort |
|------|----------|--------|
| New user request issue template | P1 | 2 hours |
| Issue → PR automation workflow | P2 | 4 hours |
| Documentation for self-service | P2 | 2 hours |

### Phase 4: Release Automation (Week 7-8)

| Task | Priority | Effort |
|------|----------|--------|
| Changelog generation workflow | P2 | 3 hours |
| Release workflow with notes | P2 | 2 hours |
| Version bump automation | P3 | 2 hours |

---

## Security Considerations

### Secrets Management

- Store Snowflake credentials in GitHub Secrets
- Use OIDC for Snowflake authentication (preferred)
- Never log sensitive output in Actions

### Permissions

- Workflows use minimal required permissions
- Sensitive operations require manual approval
- Audit log for all automated changes

### Branch Protection

Already configured:
- ✅ Require PR reviews (1 approval)
- ✅ Dismiss stale reviews
- ✅ Enforce for admins
- ✅ Require linear history
- ✅ Block force pushes

---

## Success Metrics

| Metric | Target |
|--------|--------|
| PR merge time | < 24 hours |
| Test coverage | > 80% |
| Zero direct commits to main | 100% |
| Automated releases | 100% of releases |
| Drift detection | Daily checks |

---

## Open Questions

1. **PyPI Publishing**: Should v0.2 be published to PyPI for `pip install snowtower`?
2. **Snowflake OIDC**: Set up OIDC authentication for GitHub Actions → Snowflake?
3. **Auto-apply on merge**: Should merging a PR automatically apply changes to Snowflake, or require manual trigger?
4. **Multi-environment**: Support for dev/staging/prod environments in workflows?

---

## Dependencies

- GitHub Actions (free for public repos)
- GitHub Secrets for credentials
- Existing `scripts/` tooling (mostly complete)

---

## Timeline

| Milestone | Target Date |
|-----------|-------------|
| v0.1.1 (bug fixes) | January 2026 |
| v0.2-alpha (CI/CD basics) | February 2026 |
| v0.2-beta (full automation) | February 2026 |
| v0.2.0 (stable release) | March 2026 |

---

## Next Steps

1. Review and approve this proposal
2. Create GitHub Project board for v0.2
3. Start with Phase 1 (CI foundation)
4. Iterate based on feedback

---

*Proposal created: December 2025*
*Author: Claude Code + Database Tycoon*
