# SnowTower v0.3 Roadmap

**Status:** Planning
**Focus:** Advanced Automation & Quality

---

## Overview

v0.3 builds on the CI/CD foundation from v0.2 with advanced automation features and improved test coverage.

---

## Deferred from v0.2

These features were in the v0.2 proposal but deferred:

### 1. Drift Detection Workflow

**Priority:** High
**Effort:** Medium

Scheduled workflow to detect configuration drift:

```yaml
# .github/workflows/drift-detection.yml
name: Drift Detection
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM
jobs:
  detect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uv run snowddl-plan
      - name: Create issue if drift detected
        if: failure()
        uses: actions/github-script@v7
        # ... create issue with drift details
```

**Benefits:**
- Early detection of manual changes
- Audit trail of infrastructure state
- Alerts before drift becomes problematic

---

### 2. Issue → PR Automation

**Priority:** Medium
**Effort:** Medium

Automatically generate PRs from user request issues:

```yaml
# .github/workflows/process-user-request.yml
name: Process User Request
on:
  issues:
    types: [opened]
jobs:
  process:
    if: contains(github.event.issue.labels.*.name, 'user-request')
    steps:
      - run: uv run process-access-request --issue ${{ github.event.issue.number }}
      - run: gh pr create --title "feat: Add user from issue #${{ github.event.issue.number }}"
```

**Benefits:**
- Self-service user provisioning
- Reduces admin workload
- Consistent user configuration

---

### 3. Scheduled Health Checks

**Priority:** Low
**Effort:** Low

Weekly automated health validation:

```yaml
# .github/workflows/health-check.yml
name: Scheduled Health Check
on:
  schedule:
    - cron: '0 8 * * 1'  # Weekly on Monday
jobs:
  health:
    steps:
      - run: uv run monitor-health
      - run: uv run manage-costs --analyze
```

**Benefits:**
- Proactive issue detection
- Cost monitoring
- Security compliance checks

---

## New Features for v0.3

### 4. Enhanced Test Coverage

**Priority:** High
**Effort:** High

Target: >80% test coverage (currently ~40%)

- Integration tests for CLI commands
- End-to-end deployment tests
- Mock Snowflake connection tests

### 5. snowddl-plan PR Comments

**Priority:** High
**Effort:** Medium

Post plan output directly to PR comments:

```yaml
- name: Post plan to PR
  uses: actions/github-script@v7
  with:
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        body: `### SnowDDL Plan\n\`\`\`\n${planOutput}\n\`\`\``
      })
```

**Requires:** Snowflake secrets in GitHub Actions

### 6. PyPI Publishing

**Priority:** Low
**Effort:** Low

Enable `pip install snowtower`:

```yaml
# .github/workflows/publish.yml
- uses: pypa/gh-action-pypi-publish@release/v1
  with:
    password: ${{ secrets.PYPI_API_TOKEN }}
```

---

## Open Questions

1. **Snowflake OIDC**: Should we use OIDC for GitHub Actions → Snowflake auth?
2. **Auto-apply**: Should merging PRs automatically apply to Snowflake?
3. **Multi-environment**: Support for dev/staging/prod in workflows?

---

## Success Metrics

| Metric | v0.2 | v0.3 Target |
|--------|------|-------------|
| Test coverage | ~40% | >80% |
| Drift detection | Manual | Automated daily |
| User provisioning | Semi-manual | Self-service |
| PR plan visibility | None | Auto-commented |

---

*Created: January 2026*
