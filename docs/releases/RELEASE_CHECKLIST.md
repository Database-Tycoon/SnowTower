# Release Checklist

Pre-release verification checklist for SnowTower SnowDDL.

## Quick Release Check

```bash
# Run this from the project root
uv run pytest && echo "Ready for release"
```

---

## Full Checklist

### 1. Tests

- [ ] All tests pass: `uv run pytest`
- [ ] No skipped tests without documented reason
- [ ] Test coverage acceptable: `uv run pytest --cov=src --cov-report=term-missing`

```bash
uv run pytest -v
```

### 2. Code Quality

- [ ] No uncommitted changes: `git status`
- [ ] On correct branch (main or release branch)
- [ ] All feature branches merged

```bash
git status
git branch -a
```

### 3. Dependencies

- [ ] Dependencies up to date: `uv sync`
- [ ] No security vulnerabilities in dependencies
- [ ] `pyproject.toml` version matches release

```bash
uv sync
uv pip list --outdated
```

### 4. Documentation

- [ ] README.md is current
- [ ] CHANGELOG.md updated with release notes
- [ ] Version number updated where needed

### 5. Security

- [ ] No secrets in committed files
- [ ] `.env` files not committed
- [ ] `keys/` directory not committed

```bash
# Check for potential secrets
git diff --cached --name-only | xargs grep -l -i "password\|secret\|key" 2>/dev/null || echo "No obvious secrets found"

# Verify gitignore working
git status --ignored
```

### 6. Build Verification

- [ ] Package installs correctly: `uv sync`
- [ ] CLI commands work: `uv run --help`
- [ ] Core commands functional:

```bash
uv run snowddl-plan --help
uv run manage-users --help
uv run manage-warehouses --help
```

### 7. Final Steps

- [ ] Create git tag: `git tag -a v0.x.x -m "Release v0.x.x"`
- [ ] Push tag: `git push origin v0.x.x`
- [ ] Create GitHub release with notes from CHANGELOG

---

## One-Liner Verification

Run all critical checks at once:

```bash
uv sync && uv run pytest && git status && echo "All checks passed"
```
