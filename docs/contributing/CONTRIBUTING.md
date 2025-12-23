# Contributing to SnowTower SnowDDL

Thank you for your interest in contributing to SnowTower! This guide will help you get started with development, understand our workflows, and make effective contributions.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Coding Standards](#coding-standards)
6. [Testing Requirements](#testing-requirements)
7. [Documentation Standards](#documentation-standards)
8. [Pull Request Process](#pull-request-process)
9. [CI/CD Pipeline](#cicd-pipeline)
10. [Getting Help](#getting-help)

---

## Getting Started

### Prerequisites

- **Python 3.10+** installed
- **UV package manager** installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Git** installed and configured
- **Snowflake account** with ACCOUNTADMIN access (for testing)
- **RSA key pair** for Snowflake authentication
- **GitHub account** for contributing

### Quick Setup

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/snowtower-snowddl.git
cd snowtower-snowddl

# 3. Add upstream remote
git remote add upstream https://github.com/Database-Tycoon/snowtower.git

# 4. Install dependencies
uv sync

# 5. Set up environment
cp .env.example .env
# Edit .env with your Snowflake credentials

# 6. Verify setup
uv run monitor-health
```

---

## Development Environment

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Core language |
| UV | Latest | Package management |
| Git | 2.0+ | Version control |
| Pre-commit | Latest | Code quality hooks |

### Installing UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### Environment Setup

```bash
# Install all dependencies (including dev dependencies)
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Verify pre-commit works
uv run pre-commit run --all-files
```

### IDE Setup

#### VS Code (Recommended)

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true
}
```

#### PyCharm

1. Settings → Project → Python Interpreter
2. Add interpreter → Existing environment
3. Select `.venv/bin/python`
4. Enable Ruff linter in Settings → Tools → External Tools

---

## Project Structure

### Directory Overview

```
snowtower-snowddl/
├── .github/              # CI/CD workflows and issue templates
│   ├── workflows/        # GitHub Actions
│   ├── scripts/          # CI/CD helper scripts
│   └── ISSUE_TEMPLATE/   # Issue templates
├── snowddl/              # SnowDDL YAML configurations
│   ├── *.yaml            # Account-level configs
│   └── {DATABASE}/       # Database-specific configs
├── src/                  # Python source code
│   ├── snowddl_core/     # SnowDDL OOP framework
│   ├── user_management/  # User lifecycle management
│   ├── snowtower_core/   # Operations & monitoring
│   ├── web/              # Streamlit components
│   └── management_cli.py # CLI orchestrator
├── scripts/              # Management scripts
├── streamlit_apps/       # Streamlit applications
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── manual/           # Manual test scripts
│   └── fixtures/         # Test fixtures
├── docs/                 # Documentation
├── pyproject.toml        # Project configuration
└── uv.lock               # Dependency lock file
```

### Key Modules

**Core Infrastructure:**
- `src/snowddl_core/` - OOP framework for SnowDDL operations
- `src/user_management/` - User lifecycle and authentication
- `src/snowtower_core/` - Operations, monitoring, metrics

**Scripts:**
- `scripts/manage_*.py` - Management utilities (users, warehouses, costs)
- `.github/scripts/` - CI/CD automation scripts

**Web Interface:**
- `streamlit_apps/admin/` - Administrative dashboard
- `streamlit_apps/recipes/` - Self-service workflows
- `src/web/` - Shared Streamlit components

---

## Development Workflow

### Branch Strategy

We follow **GitHub Flow** with protected main branch:

```
main (protected)
  ↓
feature/your-feature-name
  ↓
Pull Request → Review → Merge
```

### Creating a Feature

```bash
# 1. Update main branch
git checkout main
git pull upstream main

# 2. Create feature branch
git checkout -b feature/add-new-command

# 3. Make changes and commit
git add .
git commit -m "Add new warehouse management command"

# 4. Push to your fork
git push origin feature/add-new-command

# 5. Create Pull Request on GitHub
```

### Branch Naming

- **Feature:** `feature/description` (e.g., `feature/add-cost-alerts`)
- **Bugfix:** `fix/description` (e.g., `fix/user-creation-error`)
- **Documentation:** `docs/description` (e.g., `docs/update-quickstart`)
- **Refactor:** `refactor/description` (e.g., `refactor/user-manager`)
- **Test:** `test/description` (e.g., `test/add-warehouse-tests`)

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(user-mgmt): Add batch user creation command

Implemented `uv run user-create-batch` command that accepts CSV input
for creating multiple users at once. Includes validation and dry-run mode.

Closes #123
```

```
fix(snowddl): Handle missing RSA key fingerprint gracefully

Users without RSA keys now fall back to password authentication
without throwing errors.

Fixes #456
```

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length:** 100 characters (not 79)
- **Quotes:** Double quotes for strings
- **Imports:** Absolute imports preferred
- **Type hints:** Required for public functions

### Code Formatting

We use **Ruff** for linting and formatting:

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .
```

### Type Annotations

```python
# Good - with type hints
def create_user(username: str, email: str, role: str) -> dict[str, Any]:
    """Create a new Snowflake user.

    Args:
        username: Snowflake username (uppercase)
        email: User email address
        role: Default role name

    Returns:
        Dictionary containing user configuration

    Raises:
        ValueError: If username is invalid
    """
    ...

# Bad - no type hints
def create_user(username, email, role):
    ...
```

### Docstrings

Use **Google-style docstrings**:

```python
def calculate_cost(warehouse: str, hours: float) -> Decimal:
    """Calculate warehouse cost for given hours.

    Calculates the cost based on warehouse size and hours of operation.
    Applies any active resource monitor discounts.

    Args:
        warehouse: Warehouse name
        hours: Hours of operation

    Returns:
        Total cost in credits

    Raises:
        WarehouseNotFoundError: If warehouse doesn't exist

    Example:
        >>> cost = calculate_cost("COMPUTE_WH", 2.5)
        >>> print(f"Cost: {cost} credits")
        Cost: 10.0 credits
    """
    ...
```

### Error Handling

```python
# Good - specific exceptions
try:
    user = create_user(username)
except UserAlreadyExistsError:
    logger.warning(f"User {username} already exists")
    user = get_user(username)
except SnowflakeConnectionError as e:
    logger.error(f"Failed to connect to Snowflake: {e}")
    raise

# Bad - bare except
try:
    user = create_user(username)
except:
    pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed information for debugging")
logger.info("General informational messages")
logger.warning("Warning messages for potentially harmful situations")
logger.error("Error messages")
logger.critical("Critical errors that may cause system failure")

# Include context
logger.info(f"Creating user {username} with role {role}")
logger.error(f"Failed to create user {username}: {error}", exc_info=True)
```

---

## Testing Requirements

### Test Structure

```
tests/
├── unit/                 # Fast, isolated tests
│   ├── test_user_manager.py
│   ├── test_warehouse_manager.py
│   └── ...
├── integration/          # Integration tests with Snowflake
│   ├── test_snowddl_integration.py
│   ├── test_user_creation_flow.py
│   └── ...
├── fixtures/             # Test data and fixtures
│   ├── users.yaml
│   └── warehouses.yaml
└── conftest.py           # Pytest configuration
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_user_manager.py

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run only unit tests (fast)
uv run pytest tests/unit

# Run only integration tests
uv run pytest tests/integration

# Run tests matching pattern
uv run pytest -k "test_user"
```

### Writing Tests

```python
import pytest
from src.user_management import UserManager

class TestUserManager:
    """Test suite for UserManager class."""

    @pytest.fixture
    def user_manager(self):
        """Create UserManager instance for testing."""
        return UserManager(config_path="tests/fixtures/test_config.yaml")

    def test_create_user_success(self, user_manager):
        """Test successful user creation."""
        user = user_manager.create_user(
            username="TEST_USER",
            email="test@example.com",
            role="DATA_ANALYST__T_ROLE"
        )

        assert user["username"] == "TEST_USER"
        assert user["email"] == "test@example.com"
        assert user["disabled"] is False

    def test_create_user_invalid_username(self, user_manager):
        """Test user creation with invalid username."""
        with pytest.raises(ValueError, match="Username must be uppercase"):
            user_manager.create_user(
                username="lowercase_user",
                email="test@example.com",
                role="DATA_ANALYST__T_ROLE"
            )
```

### Test Coverage Requirements

- **Minimum coverage:** 70% for new code
- **Target coverage:** 80%+ overall
- **Critical paths:** 100% coverage (authentication, deployment)

### Integration Testing

Integration tests require a Snowflake sandbox account:

```bash
# Set test environment
export SNOWFLAKE_TEST_ACCOUNT=test_account
export SNOWFLAKE_TEST_USER=test_user
export SNOWFLAKE_TEST_ROLE=SYSADMIN

# Run integration tests
uv run pytest tests/integration -v
```

---

## Documentation Standards

### Code Documentation

- **All public functions:** Must have docstrings
- **All classes:** Must have class-level docstrings
- **Complex logic:** Inline comments explaining why, not what

### Markdown Documentation

- **Headings:** Use ATX-style (`#` not underlines)
- **Code blocks:** Always specify language
- **Links:** Use reference-style for repeated links
- **Line length:** Soft limit of 100 characters

### UV Command Documentation

When adding new UV commands, update `docs/MANAGEMENT_COMMANDS.md`:

```markdown
### `uv run new-command`

**Purpose:** Brief description

**Usage:**
```bash
uv run new-command [OPTIONS]
```

**Options:**
- `--option1` - Description
- `--option2` - Description

**Examples:**
```bash
# Example 1: Basic usage
uv run new-command --option1 value

# Example 2: Advanced usage
uv run new-command --option1 value --option2 value
```

**Related Commands:**
- `uv run related-command1`
- `uv run related-command2`
```

---

## Pull Request Process

### Before Submitting

- [ ] Code follows style guide (Ruff passes)
- [ ] All tests pass (`uv run pytest`)
- [ ] Test coverage maintained or improved
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow conventions
- [ ] Pre-commit hooks pass

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated (if applicable)
- [ ] Manual testing performed

## SnowDDL Plan Output
```
Paste output of `uv run snowddl-plan` if infrastructure changes
```

## Checklist
- [ ] Code follows project style guide
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated and passing

## Related Issues
Closes #123
Related to #456
```

### Review Process

1. **Automated Checks:** CI/CD runs tests, linting, SnowDDL plan
2. **Code Review:** Maintainer reviews code quality and design
3. **Testing:** Reviewer tests changes in sandbox environment
4. **Approval:** Minimum 1 approving review required
5. **Merge:** Squash and merge to main branch

### PR Guidelines

**DO:**
- Keep PRs focused and small (< 400 lines preferred)
- Include tests for new features
- Update documentation
- Respond to review comments promptly
- Rebase on main before requesting review

**DON'T:**
- Mix multiple unrelated changes
- Include commented-out code
- Commit `.env` files or credentials
- Break existing functionality
- Ignore CI/CD failures

---

## CI/CD Pipeline

### Automated Workflows

#### PR Validation (`.github/workflows/pr-validation.yml`)

**Triggers:** Pull requests to main

**Steps:**
1. YAML syntax validation
2. Security scanning (Bandit, Safety)
3. Code linting (Ruff)
4. Unit tests
5. Integration tests (if applicable)
6. SnowDDL plan generation
7. Coverage report

**Artifacts:**
- Test results
- Coverage report
- SnowDDL plan output

#### Merge Deployment (`.github/workflows/merge-deploy.yml`)

**Triggers:** Merge to main branch

**Steps:**
1. Create pre-deployment snapshot
2. Run safety gates
3. Execute SnowDDL apply
4. Post-deployment health check
5. Notification (Slack/Email)
6. Rollback on failure

**Safety Gates:**
- No DROP operations in production
- User changes don't affect admins
- Network policy changes tested
- Backup exists

### Local CI Simulation

```bash
# Run all checks locally before pushing
./scripts/ci-check.sh

# Or manually:
uv run ruff check .
uv run pytest --cov
uv run snowddl-validate
uv run snowddl-plan
```

---

## Getting Help

### Resources

- **Documentation:** [docs/](docs/)
- **API Reference:** Run `uv run docs-api` and open `docs/api/index.html`
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Quickstart:** [QUICKSTART.md](QUICKSTART.md)

### Communication

- **GitHub Issues:** Bug reports and feature requests
- **GitHub Discussions:** General questions and ideas
- **Slack:** #snowtower channel (if applicable)

### Asking Good Questions

When asking for help:

1. **Search first:** Check existing issues and documentation
2. **Be specific:** Include error messages, code snippets, logs
3. **Provide context:** OS, Python version, UV version
4. **Include steps to reproduce:** How can others reproduce the issue?
5. **Share what you've tried:** What troubleshooting have you done?

**Example:**

```
**Environment:**
- OS: macOS 14.0
- Python: 3.11.5
- UV: 0.1.0
- SnowDDL: 0.50.2

**Issue:**
Getting "Authentication failed" when running `uv run snowddl-plan`

**Steps to Reproduce:**
1. Set up .env with SNOWFLAKE_USER=ADMIN
2. Run `uv run snowddl-plan`
3. See error: "Authentication failed"

**What I've Tried:**
- Verified .env has correct account name
- Checked RSA key exists at path
- Ran `uv run util-diagnose-auth` (shows connection OK)

**Error Output:**
```
[paste full error here]
```

**Expected Behavior:**
SnowDDL plan should show infrastructure changes
```

---

## Common Development Tasks

### Adding a New UV Command

```python
# 1. Create script in scripts/
# scripts/new_command.py
from dotenv import load_dotenv
import argparse

load_dotenv()  # ALWAYS load .env first

def main():
    parser = argparse.ArgumentParser(description="New command description")
    parser.add_argument("--option", help="Option description")
    args = parser.parse_args()

    # Implementation
    print("Command executed successfully")

if __name__ == "__main__":
    main()
```

```python
# 2. Add wrapper in src/management_cli.py
def new_command():
    """Wrapper for new command."""
    import subprocess
    subprocess.run(["python", "scripts/new_command.py"])
```

```toml
# 3. Register in pyproject.toml
[project.scripts]
new-command = "src.management_cli:new_command"
```

```bash
# 4. Test command
uv sync
uv run new-command --help
```

```markdown
# 5. Document in docs/MANAGEMENT_COMMANDS.md
(See Documentation Standards section)
```

### Adding a New Test

```python
# tests/unit/test_new_feature.py
import pytest
from src.module import NewFeature

class TestNewFeature:
    @pytest.fixture
    def feature(self):
        return NewFeature()

    def test_basic_functionality(self, feature):
        result = feature.do_something()
        assert result is True
```

### Updating SnowDDL Configuration

```yaml
# 1. Edit YAML in snowddl/
# snowddl/user.yaml
NEW_USER:
  type: PERSON
  ...
```

```bash
# 2. Preview changes
uv run snowddl-plan

# 3. Review plan output carefully

# 4. Apply if approved
uv run snowddl-apply --apply-unsafe
```

---

## Release Process

(For maintainers only)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release branch: `release/v1.0.0`
4. Tag release: `git tag v1.0.0`
5. Push tag: `git push --tags`
6. Create GitHub release with notes
7. Deploy to production

---

## License

By contributing to SnowTower, you agree that your contributions will be licensed under the same license as the project.

---

## Thank You!

Your contributions make SnowTower better for everyone. We appreciate your time and effort!

**Questions?** Open an issue or start a discussion on GitHub.

---

**Last Updated:** October 9, 2025
**Version:** 1.0
**Maintained By:** SnowTower Team
