---
name: snowtower-developer
description: Comprehensive skill for SnowTower contributors and developers. Use when contributing code, fixing bugs, adding features, writing tests, or developing new functionality. Triggers on mentions of development, coding, testing, PR creation, bug fixes, or feature implementation.
---

# SnowTower Developer Guide

A comprehensive skill for developers contributing to the SnowTower codebase.

## Who This Skill Is For

- **Contributors** adding new features or fixing bugs
- **Developers** extending SnowTower functionality
- **QA engineers** writing tests
- **Maintainers** reviewing code and managing releases

---

## 🚀 Quick Start for New Developers

### Initial Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR-USERNAME/snowtower-public.git
cd snowtower-public

# 2. Install UV package manager (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Create development environment
uv sync --all-extras --dev

# 4. Set up pre-commit hooks
uv run pre-commit install

# 5. Create .env file for testing
cp .env.example .env
# Edit .env with test credentials (mock credentials are fine for tests)

# 6. Verify setup
uv run pytest -v
uv run pre-commit run --all-files
```

### First Build

```bash
# Run all quality checks
uv run pre-commit run --all-files  # Linting, formatting, secrets check
uv run pytest -v                    # Run all 355 tests
uv run pytest --cov=src             # With coverage report
```

---

## 📁 Codebase Architecture

### Directory Structure

```
snowtower-public/
├── src/                          # Source code
│   ├── snowddl_core/            # OOP framework for SnowDDL
│   │   ├── base.py              # Base classes for all objects
│   │   ├── account_objects.py   # Users, roles, warehouses
│   │   ├── database_objects.py  # Databases, schemas
│   │   ├── validation.py        # Validation framework
│   │   └── safety/              # Safety and checkpoint system
│   ├── user_management/         # User lifecycle management
│   │   ├── manager.py           # UserManager class
│   │   ├── yaml_handler.py      # YAML read/write
│   │   └── encryption.py        # Fernet encryption
│   ├── snowtower_core/          # Core business logic
│   │   ├── models.py            # Data models
│   │   ├── metrics.py           # Metrics collection
│   │   └── managers.py          # Business logic managers
│   ├── automation/              # GitHub integration
│   └── management_cli.py        # CLI entry points
├── scripts/                      # Management scripts
│   ├── manage_users.py          # User management
│   ├── manage_warehouses.py     # Warehouse management
│   ├── cost_optimization.py     # Cost analysis
│   └── deploy_safe.py           # Safe deployment wrapper
├── tests/                        # Test suite
│   ├── test_*.py                # Unit tests
│   ├── integration/             # Integration tests
│   ├── manual/                  # Manual test scripts
│   └── fixtures/                # Test fixtures
├── snowddl/                      # YAML infrastructure definitions
└── docs/                         # Documentation
```

### Key Design Patterns

1. **Command Pattern**: UV commands wrap scripts in `management_cli.py`
2. **Repository Pattern**: `YAMLHandler` abstracts file operations
3. **Strategy Pattern**: Different authentication methods (RSA vs password)
4. **Factory Pattern**: User creation with type-specific handling
5. **Dependency Injection**: Testable components with mocked dependencies

---

## 🔧 Development Workflows

### Adding a New UV Command

**Follow the established 4-step pattern:**

#### Step 1: Create Script in `scripts/`

```python
# scripts/my_new_feature.py
from dotenv import load_dotenv
load_dotenv()  # MUST BE FIRST LINE

import argparse
from pathlib import Path
from snowddl_core import SnowflakeClient  # Use OOP framework

def main():
    """Main entry point for my new feature."""
    parser = argparse.ArgumentParser(
        description="Description of my feature"
    )
    parser.add_argument('--option', help='Example option')
    args = parser.parse_args()

    # Implementation here
    print(f"Running my feature with option: {args.option}")

if __name__ == "__main__":
    main()
```

**Critical Rules:**
- ✅ `load_dotenv()` MUST be the first line
- ✅ Use `argparse` for CLI interface
- ✅ Import from `snowddl_core` OOP framework
- ✅ Include docstrings
- ✅ Add type hints

#### Step 2: Add Wrapper in `src/management_cli.py`

```python
def my_new_feature():
    """Run my new feature command."""
    from my_new_feature import main
    main()
```

#### Step 3: Register in `pyproject.toml`

```toml
[project.scripts]
my-new-feature = "src.management_cli:my_new_feature"
```

#### Step 4: Test the Command

```bash
# Sync dependencies
uv sync

# Test command
uv run my-new-feature --help
uv run my-new-feature --option test
```

### Writing Tests

**Test Location Strategy:**
- `tests/test_<module>.py` - Unit tests for `src/<module>.py`
- `tests/integration/` - End-to-end tests
- `tests/manual/` - Complex manual verification scripts

**Example Unit Test:**

```python
# tests/test_my_feature.py
"""Tests for my new feature."""
import pytest
from unittest.mock import Mock, patch
from my_new_feature import main

class TestMyFeature:
    """Test suite for my feature."""

    def test_basic_functionality(self):
        """Test basic feature operation."""
        # Arrange
        expected = "expected result"

        # Act
        result = my_function()

        # Assert
        assert result == expected

    @patch('my_new_feature.SnowflakeClient')
    def test_with_mock_snowflake(self, mock_client):
        """Test feature with mocked Snowflake connection."""
        # Setup mock
        mock_client.return_value.execute.return_value = []

        # Test with mock
        result = main()

        # Verify
        mock_client.return_value.execute.assert_called_once()
```

**Run Tests:**

```bash
# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/test_my_feature.py -v

# Run with coverage
uv run pytest --cov=src --cov-report=term

# Run in parallel (faster)
uv run pytest -n auto

# Run only failed tests from last run
uv run pytest --lf
```

---

## 🎨 Coding Standards

### Python Style Guide

**Follow these conventions:**

1. **Type Hints (Required)**
   ```python
   def create_user(
       username: str,
       email: str,
       user_type: UserType
   ) -> dict[str, Any]:
       """Create a new user."""
       pass
   ```

2. **Docstrings (Required)**
   ```python
   def process_data(data: list[dict]) -> pd.DataFrame:
       """
       Process raw data into structured DataFrame.

       Args:
           data: List of dictionaries containing raw data

       Returns:
           Pandas DataFrame with processed data

       Raises:
           ValueError: If data is empty or malformed
       """
       pass
   ```

3. **Error Handling**
   ```python
   # Use custom exceptions
   from snowddl_core.exceptions import SnowDDLError

   if not username:
       raise SnowDDLError("Username is required")
   ```

4. **Constants**
   ```python
   # Use uppercase for constants
   DEFAULT_WAREHOUSE_SIZE = "X-SMALL"
   MAX_PASSWORD_LENGTH = 256
   ```

### Pre-commit Checks

**These run automatically on commit:**

```yaml
# .pre-commit-config.yaml
- Black (code formatting)
- YAML validation
- Trailing whitespace removal
- Secrets detection (prevent credential leaks)
- File size limits
```

**Run manually:**

```bash
# Check all files
uv run pre-commit run --all-files

# Check specific files
uv run pre-commit run --files src/my_file.py

# Skip hooks (rarely needed)
git commit --no-verify
```

---

## 🐛 Debugging Workflows

### Debug a Failing Test

```bash
# Run with detailed output
uv run pytest tests/test_user_management.py -vv --tb=long

# Run with debugger
uv run pytest tests/test_user_management.py --pdb

# Print test output (disable capture)
uv run pytest tests/test_user_management.py -s
```

### Debug a Command

```python
# Add to script for debugging
import pdb; pdb.set_trace()  # Breakpoint

# Or use rich for better output
from rich import print
print(f"Debug info: {variable}")
```

### Common Issues

**Issue: Import errors**
```bash
# Solution: Ensure sync is up to date
uv sync --all-extras --dev
```

**Issue: Test failures with Snowflake connection**
```bash
# Solution: Tests use mocks, no real connection needed
# Check your mock setup:
@patch('module.SnowflakeClient')
def test_with_mock(self, mock_client):
    # Configure mock to return expected values
    mock_client.return_value.execute.return_value = []
```

**Issue: Pre-commit hooks failing**
```bash
# Solution: Auto-fix most issues
uv run pre-commit run --all-files

# Then commit the fixes
git add .
git commit -m "fix: Apply pre-commit fixes"
```

---

## 📝 Pull Request Workflow

### Creating a Feature Branch

```bash
# Always branch from the release branch (v0.2, v0.3, etc.)
git checkout v0.2
git pull origin v0.2
git checkout -b feature/my-awesome-feature
```

### Development Cycle

```bash
# 1. Make changes
vim src/my_file.py

# 2. Write tests
vim tests/test_my_file.py

# 3. Run quality checks
uv run pre-commit run --all-files
uv run pytest -v

# 4. Commit with conventional commit format
git add .
git commit -m "feat: Add my awesome feature"

# 5. Push and create PR
git push -u origin feature/my-awesome-feature
gh pr create --base v0.2 --title "feat: Add my awesome feature"
```

### Commit Message Format

**Use Conventional Commits:**

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks
- `ci:` - CI/CD changes

**Examples:**

```bash
git commit -m "feat: Add user bulk import command"
git commit -m "fix: Correct warehouse auto-suspend calculation"
git commit -m "docs: Update QUICKSTART with new commands"
git commit -m "test: Add integration tests for user management"
```

### PR Checklist

Before submitting, ensure:

- [ ] All tests pass: `uv run pytest -v`
- [ ] Pre-commit checks pass: `uv run pre-commit run --all-files`
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No secrets in code
- [ ] Type hints are added
- [ ] Docstrings are complete

---

## 🧪 Testing Best Practices

### Test Organization

```python
# tests/test_user_management.py
class TestUserCreation:
    """Tests for user creation functionality."""

    def setup_method(self):
        """Set up test fixtures before each test."""
        self.manager = UserManager(config_directory=Path("/tmp/test"))

    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree("/tmp/test", ignore_errors=True)

    def test_create_person_user(self):
        """Test creating a PERSON type user."""
        result = self.manager.create_user(
            first_name="John",
            last_name="Doe",
            user_type=UserType.PERSON
        )
        assert "JOHN_DOE" in result
```

### Mocking Snowflake Connections

```python
# Always mock Snowflake for unit tests
@patch('snowflake.connector.connect')
def test_snowflake_operation(mock_connect):
    """Test operation with mocked Snowflake connection."""
    # Setup mock
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [('RESULT',)]
    mock_connect.return_value.cursor.return_value = mock_cursor

    # Run test
    result = my_snowflake_function()

    # Verify
    assert result == [('RESULT',)]
    mock_connect.assert_called_once()
```

### Property-Based Testing (Advanced)

```python
from hypothesis import given, strategies as st

@given(
    username=st.text(min_size=1, max_size=50),
    email=st.emails()
)
def test_user_creation_with_random_inputs(username, email):
    """Test user creation with random inputs (property-based)."""
    # This runs 100+ times with different random inputs
    result = create_user(username, email)
    assert validate_user(result)
```

---

## 🏗️ Using the SnowDDL OOP Framework

### Creating Objects Programmatically

```python
from snowddl_core import User, Role, Warehouse, WarehouseSize, UserType
from snowddl_core.safety import create_checkpoint

# Create a user object
user = User(
    name="JOHN_DOE",
    comment="Data Analyst",
    user_type=UserType.PERSON,
    email="john@company.com",
    default_role="ANALYST_ROLE"
)

# Create a warehouse
warehouse = Warehouse(
    name="ANALYTICS_WH",
    size=WarehouseSize.SMALL,
    auto_suspend=300,
    auto_resume=True,
    comment="Analytics team warehouse"
)

# Create safety checkpoint before modifications
checkpoint = create_checkpoint("Before user creation")

# Write to YAML
user.to_yaml(Path("snowddl/user.yaml"))
warehouse.to_yaml(Path("snowddl/warehouse.yaml"))
```

### Reading YAML Configurations

```python
from user_management.yaml_handler import YAMLHandler

# Read existing configuration
handler = YAMLHandler("snowddl/user.yaml")
users = handler.load()

# Modify
users["NEW_USER"] = {
    "comment": "New data analyst",
    "type": "PERSON",
    "email": "new@company.com"
}

# Write back
handler.save(users)
```

---

## 📊 Performance Testing

### Benchmarking Commands

```bash
# Run performance benchmarks
uv run pytest tests/ --benchmark-only

# Compare benchmark results
uv run pytest tests/ --benchmark-compare
```

### Writing Benchmarks

```python
def test_user_creation_performance(benchmark):
    """Benchmark user creation performance."""
    result = benchmark(
        create_user,
        username="TEST_USER",
        email="test@example.com"
    )
    assert result is not None
```

---

## 🔍 Code Review Guidelines

### As a Reviewer

**Check for:**
- [ ] Tests cover new functionality
- [ ] No hardcoded credentials or secrets
- [ ] Type hints are present
- [ ] Docstrings are complete
- [ ] Error handling is appropriate
- [ ] No breaking changes without migration path
- [ ] CI checks pass
- [ ] Performance implications considered

### As a Contributor

**Before requesting review:**
- [ ] Self-review your code
- [ ] Remove debug statements and commented code
- [ ] Ensure variable names are descriptive
- [ ] Add comments for complex logic
- [ ] Update documentation
- [ ] Test edge cases

---

## 🚢 Release Process

### Pre-Release Checklist

See `docs/releases/RELEASE_CHECKLIST.md` for full details.

**Critical steps:**

```bash
# 1. Run full test suite
uv run pytest -v

# 2. All tests MUST pass
# No release with failing tests!

# 3. Update version
vim pyproject.toml  # Update version number

# 4. Update changelog
vim CHANGELOG.md

# 5. Create release PR
git checkout -b release/v0.3.0
git commit -m "chore: Prepare v0.3.0 release"
gh pr create --base main

# 6. After merge, tag release
git checkout main
git pull
git tag v0.3.0
git push origin v0.3.0  # Triggers release workflow
```

---

## 🎯 Common Development Tasks

### Add a New Snowflake Object Type

1. **Create class in `src/snowddl_core/`**
   ```python
   # src/snowddl_core/account_objects.py
   class MyNewObject(AccountLevelObject):
       """New Snowflake object type."""
       pass
   ```

2. **Add to exports in `__init__.py`**

3. **Write tests**

4. **Update documentation**

### Add a New Authentication Method

1. **Extend authentication module**
   ```python
   # src/user_management/authentication.py
   class NewAuthMethod:
       """New authentication method."""
       pass
   ```

2. **Update user YAML schema**

3. **Add tests with mocks**

4. **Update security documentation**

### Add a New Management Command

See "Adding a New UV Command" section above.

---

## 📚 Essential Documentation

### For Developers

- `CLAUDE.md` - Project overview and quick reference
- `docs/llm-context/PATTERNS.md` - Code patterns and conventions
- `docs/contributing/CONTRIBUTING.md` - Contribution guidelines
- `docs/contributing/HOW_TO_TEST.md` - Testing strategies
- `src/snowddl_core/README.md` - OOP framework documentation

### For Understanding the Domain

- `docs/guide/ARCHITECTURE.md` - System architecture
- `docs/guide/QUICKSTART.md` - User guide
- `docs/guide/SCHEMA_GRANTS.md` - Schema permission management

---

## 🆘 Getting Help

### When Stuck

1. **Check existing tests** for examples
2. **Read module docstrings** for API documentation
3. **Search GitHub issues** for similar problems
4. **Ask in discussions** or open an issue

### Useful Commands

```bash
# See all UV commands
uv run snowtower

# Get help for specific command
uv run manage-users --help

# Run interactive Python with project imports
uv run python
>>> from snowddl_core import User
>>> help(User)

# Check dependencies
uv tree

# Update dependencies
uv lock --upgrade
```

---

## ✨ Best Practices Summary

1. **Always use `load_dotenv()` first** in scripts
2. **Write tests** for all new features
3. **Use type hints** everywhere
4. **Mock Snowflake** connections in tests
5. **Follow conventional commits** format
6. **Run pre-commit** before pushing
7. **Create checkpoints** before destructive operations
8. **Document** public APIs with docstrings
9. **Branch from release branches** not main
10. **Keep PRs focused** on single features

---

## 🎓 Advanced Topics

### Dependency Injection for Testing

```python
# Make functions testable by injecting dependencies
def process_users(
    config_path: Path,
    yaml_handler: Optional[YAMLHandler] = None
):
    """Process users with optional injected handler for testing."""
    handler = yaml_handler or YAMLHandler(config_path)
    # Use handler...
```

### Extending the CLI

```python
# Add subcommands with click
import click

@click.group()
def my_command():
    """My command group."""
    pass

@my_command.command()
@click.option('--verbose', is_flag=True)
def subcommand(verbose):
    """A subcommand."""
    if verbose:
        print("Verbose mode enabled")
```

### Working with YAML Schema Validation

```python
from pydantic import BaseModel, ValidationError

class UserSchema(BaseModel):
    """Schema for user YAML validation."""
    comment: str
    type: str
    email: str

# Validate YAML data
try:
    user = UserSchema(**yaml_data)
except ValidationError as e:
    print(f"Invalid user config: {e}")
```

---

**Happy Coding! 🚀**

For questions or improvements to this skill, open an issue or PR on GitHub.
