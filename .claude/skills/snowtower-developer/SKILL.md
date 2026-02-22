---
name: snowtower-developer
description: Comprehensive skill for SnowTower contributors and developers. Use when contributing code, fixing bugs, adding features, writing tests, or developing new functionality. Triggers on mentions of development, coding, testing, PR creation, bug fixes, or feature implementation.
---

# SnowTower Developer Guide

Assumes CLAUDE.md is loaded for project context and command patterns.

## Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR-USERNAME/snowtower-public.git
cd snowtower-public

# 2. Install UV (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync --all-extras --dev

# 4. Set up pre-commit hooks
uv run pre-commit install

# 5. Create .env (mock credentials fine for tests)
cp .env.example .env

# 6. Verify
uv run pytest -v
uv run pre-commit run --all-files
```

## Adding a New UV Command (4-Step Pattern)

See CLAUDE.md "Creating New Commands" for the template. Summary:

1. **Create script** in `scripts/my_script.py` - `load_dotenv()` MUST be first, use argparse
2. **Add wrapper** in `src/management_cli.py`
3. **Register** in `pyproject.toml` under `[project.scripts]`
4. **Test**: `uv sync && uv run my-command --help`

## Running Tests

```bash
uv run pytest -v                    # All tests
uv run pytest tests/test_foo.py -v  # Specific file
uv run pytest --cov=src             # With coverage
uv run pytest -n auto               # Parallel (faster)
uv run pytest --lf                  # Only last-failed
uv run pytest -vv --tb=long         # Detailed failure output
uv run pytest --pdb                 # Drop into debugger on failure
```

**Mocking Snowflake** (required for unit tests - no real connection needed):
```python
@patch('module.SnowflakeClient')
def test_with_mock(self, mock_client):
    mock_client.return_value.execute.return_value = []
    # test implementation
```

## PR Workflow

```bash
# 1. Branch from release branch
git checkout v0.2 && git pull
git checkout -b feature/my-feature

# 2. Develop + test
uv run pre-commit run --all-files
uv run pytest -v

# 3. Commit (conventional commits)
git commit -m "feat: Add my feature"

# 4. Push + create PR
git push -u origin feature/my-feature
gh pr create --base v0.2
```

**Commit types:** `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`

## PR Checklist

- [ ] Tests pass: `uv run pytest -v`
- [ ] Pre-commit passes: `uv run pre-commit run --all-files`
- [ ] New features have tests
- [ ] No secrets in code
- [ ] Commit messages follow convention

## Pre-commit Hooks

Runs automatically on commit: Black formatting, YAML validation, trailing whitespace, secrets detection, file size limits.

```bash
uv run pre-commit run --all-files   # Manual run
uv run pre-commit run --files src/my_file.py  # Specific files
```

## Common Issues

| Problem | Fix |
|---------|-----|
| Import errors | `uv sync --all-extras --dev` |
| Tests need Snowflake | Tests use mocks - check mock setup |
| Pre-commit failing | Run `uv run pre-commit run --all-files`, commit fixes |

## Useful Commands

```bash
uv run --help          # See all UV commands
uv tree                # Check dependencies
uv lock --upgrade      # Update dependencies
uv run python          # Interactive Python with project imports
```
