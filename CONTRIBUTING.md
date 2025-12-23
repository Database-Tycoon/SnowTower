# Contributing to SnowTower

## Branch Strategy

SnowTower uses a **release branch** workflow:

```
feature/* ──► v0.x (release branch) ──► main
```

### Protected Branches

The following branches are protected and require PRs:

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Production releases | PR required, 1 approval, CI must pass |
| `v0.x` | Release staging | PR required, 1 approval, CI must pass |

**You cannot push directly to `main` or release branches (`v0.x`).**

### Workflow

1. **Create feature branch** from the current release branch:
   ```bash
   git checkout v0.2
   git pull origin v0.2
   git checkout -b feature/my-feature
   ```

2. **Make changes** and commit:
   ```bash
   # Run pre-commit before committing
   uv run pre-commit run --all-files

   git add .
   git commit -m "feat: Add my feature"
   ```

3. **Push and create PR** targeting the release branch:
   ```bash
   git push -u origin feature/my-feature
   gh pr create --base v0.2
   ```

4. **After PR approval and merge**, changes go to the release branch

5. **When ready to release**, the release branch merges to `main` and gets tagged

## CI Requirements

All PRs must pass CI checks before merging:

- **Lint & Format Check**: `uv run pre-commit run --all-files`
- **Run Tests**: `uv run pytest`

### Local Verification

Before pushing, always run:

```bash
# Install pre-commit hooks (one-time)
uv run pre-commit install

# Run all checks
uv run pre-commit run --all-files
uv run pytest
```

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: Add new feature
fix: Fix bug
docs: Update documentation
style: Format code
refactor: Refactor code
test: Add tests
chore: Maintenance tasks
```

Examples:
```bash
git commit -m "feat: Add user creation workflow"
git commit -m "fix: Correct warehouse auto-suspend timing"
git commit -m "docs: Update README badges"
```

## Pull Request Guidelines

### PR Template

PRs should include:
- **Summary**: What changed and why
- **Change Type**: Infrastructure / Code / Documentation / Tests / CI/CD
- **Related Issues**: Link issues with `Closes #123` or `Fixes #123`
- **Test Plan**: How you verified the changes
- **Checklist**: Pre-commit passes, no secrets, tests pass

### Linking to Issues

When your PR addresses an issue, use closing keywords:
```markdown
Closes #123
Fixes #456
```

This automatically closes the issue when the PR is merged.

## Release Process

1. **All features merged** to release branch (e.g., `v0.2`)
2. **Final testing** on release branch
3. **Create PR** from release branch to `main`
4. **Merge and tag**:
   ```bash
   git checkout main
   git pull
   git tag v0.2.0
   git push origin v0.2.0
   ```
5. **Release workflow** automatically creates GitHub Release

## What NOT to Do

- **Don't push directly** to `main` or release branches
- **Don't force push** to protected branches
- **Don't skip pre-commit** hooks
- **Don't merge without CI passing**
- **Don't include secrets** in commits (credentials, API keys, etc.)

## Getting Help

- **Issues**: [Open an issue](https://github.com/Database-Tycoon/SnowTower/issues/new/choose)
- **Discussions**: Use GitHub Discussions for questions
