# SnowTower Developer Skill

## Overview

The `snowtower-developer` skill provides comprehensive guidance for developers contributing to the SnowTower codebase. This skill helps with:

- Setting up development environment
- Understanding codebase architecture
- Following coding standards and patterns
- Creating new UV commands
- Writing and running tests
- Debugging issues
- Submitting pull requests
- Performing code reviews

## When to Use This Skill

Use this skill when you need help with:

- **Code Contributions**: Adding new features or functionality
- **Bug Fixes**: Debugging and fixing issues
- **Testing**: Writing unit tests, integration tests, or running test suites
- **Development Setup**: Initial environment configuration
- **UV Commands**: Creating new management commands
- **Pull Requests**: Submitting code for review
- **Code Review**: Reviewing pull requests
- **Debugging**: Troubleshooting test failures or code issues

## How to Invoke

In Claude Code, you can invoke this skill by mentioning:

- "Use the developer skill"
- "Help me add a new feature"
- "How do I write tests for this?"
- "Show me how to create a UV command"
- "What's the development workflow?"

Or explicitly:
```
/snowtower-developer
```

## Skill Contents

The skill covers:

1. **Quick Start** - Setting up your development environment
2. **Architecture** - Understanding the codebase structure
3. **Workflows** - Common development tasks
4. **Coding Standards** - Style guide and best practices
5. **Testing** - Writing and running tests
6. **Debugging** - Troubleshooting techniques
7. **Pull Requests** - Contribution workflow
8. **Advanced Topics** - Dependency injection, CLI extensions, validation

## Related Skills

- **snowtower-admin**: For infrastructure deployment and operations
- **snowtower-maintainer**: For documentation and project maintenance
- **snowtower-user**: For end-user access and connection help

## Quick Examples

### Adding a New Command

```bash
# 1. Create script
vim scripts/my_feature.py

# 2. Add wrapper
vim src/management_cli.py

# 3. Register in pyproject.toml
# 4. Test
uv sync
uv run my-feature --help
```

### Running Tests

```bash
# All tests
uv run pytest -v

# Specific test
uv run pytest tests/test_user_management.py -v

# With coverage
uv run pytest --cov=src --cov-report=term
```

### Creating a PR

```bash
git checkout v0.2
git checkout -b feature/my-feature
# Make changes...
uv run pre-commit run --all-files
uv run pytest -v
git commit -m "feat: Add my feature"
gh pr create --base v0.2
```

## Contributing to This Skill

If you find ways to improve this skill, please:

1. Edit `.claude/skills/snowtower-developer/SKILL.md`
2. Submit a PR with your improvements
3. Document any new patterns or workflows you discover

---

**Happy coding! 🚀**
