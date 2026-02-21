---
name: snowtower-maintainer
description: Maintains SnowTower project documentation, README, and Claude configuration. Use when updating documentation, auditing .claude folder contents, syncing README with actual project state, or reviewing agent/pattern definitions. Triggers on mentions of documentation, README, maintenance, or .claude folder updates.
---

# SnowTower Project Maintainer

Assumes CLAUDE.md is loaded for project context.

## README Audit Checklist

1. **Verify commands** mentioned in README exist:
   ```bash
   uv run --help | grep -E "snowddl-plan|deploy-safe|manage-users"
   ```
2. **Check workflow badges** match `.github/workflows/`
3. **Verify documentation links** resolve to existing files
4. **Update statistics** (users, databases, warehouses):
   ```bash
   echo "Users: $(grep -c '^  [A-Z]' snowddl/user.yaml 2>/dev/null || echo N/A)"
   echo "Databases: $(ls -d snowddl/*/ 2>/dev/null | grep -v __pycache__ | wc -l)"
   echo "Warehouses: $(grep -c '^  [A-Z]' snowddl/warehouse.yaml 2>/dev/null || echo N/A)"
   ```

## Documentation Sync Table

| Doc File | Should Match |
|----------|--------------|
| `docs/guide/MANAGEMENT_COMMANDS.md` | `pyproject.toml` scripts |
| `docs/guide/QUICKSTART.md` | Current setup process |
| `docs/guide/SCHEMA_GRANTS.md` | Current grant handling |
| `README.md` | Actual project capabilities |

## Quick Health Check

```bash
ls -la snowddl/ src/ scripts/ docs/   # Verify structure
uv run --help                          # Check commands
uv run pytest --co -q | tail -5        # Verify tests collect
uv run pre-commit run --all-files      # Check formatting
```

## Release Planning

1. **Check open issues:**
   ```bash
   gh issue list --state open --label P1
   gh issue list --state open
   ```
2. **Review completed work since last release:**
   ```bash
   git log v0.X..HEAD --oneline
   ```
3. **Create version branch:**
   ```bash
   git checkout main && git pull
   git checkout -b v0.X
   git push -u origin v0.X
   ```
4. **Pre-release checklist:**
   - [ ] `uv run pytest` passes
   - [ ] CHANGELOG.md updated
   - [ ] README current (badges, commands, stats)
   - [ ] Documentation links valid
5. **Release:**
   ```bash
   gh release create vX.Y --title "vX.Y - Title" --notes "..."
   ```

## .claude/ Directory Structure

```
.claude/
├── patterns/         # Reusable patterns (e.g., SERVICE_ACCOUNT_CREATION_PATTERN.md)
├── skills/           # Claude Code skills (4 task-specific guides)
└── settings.local.json
```

## When to Trigger

- User asks to update README or documentation
- Before releases to ensure docs are current
- After significant feature additions
- When onboarding new contributors
- User asks to plan a new release version
