# SnowTower Documentation

## Quick Links

| I want to... | Go to... |
|--------------|----------|
| Get started quickly | [Quickstart](guide/QUICKSTART.md) |
| See all CLI commands | [CLI Reference](guide/MANAGEMENT_COMMANDS.md) |
| Create a new user | [User Creation](guide/USER_CREATION_GUIDE.md) |
| Fix schema permissions | [Schema Grants](guide/SCHEMA_GRANTS.md) |
| Troubleshoot issues | [Troubleshooting](guide/TROUBLESHOOTING.md) |
| View the changelog | [Changelog](releases/CHANGELOG.md) |
| Use LLMs with this repo | [Agent Config](agents/) |

---

## Guide

All user-facing documentation.

**Getting Started**
- [Quickstart](guide/QUICKSTART.md) - Get up and running in 5 minutes
- [Architecture](guide/ARCHITECTURE.md) - System design overview

**User Management**
- [User Creation Guide](guide/USER_CREATION_GUIDE.md) - Creating and managing users
- [Authentication Guide](guide/AUTHENTICATION_GUIDE.md) - RSA keys, passwords, MFA
- [Quick Reference](guide/QUICK_REFERENCE.md) - User management cheat sheet

**Operations**
- [Monitoring](guide/MONITORING.md) - Logging, metrics, alerting
- [Troubleshooting](guide/TROUBLESHOOTING.md) - Common issues and solutions

**Reference**
- [Management Commands](guide/MANAGEMENT_COMMANDS.md) - Complete CLI reference
- [Configuration Reference](guide/CONFIGURATION_REFERENCE.md) - Environment variables and YAML

**Security**
- [Security Notice](guide/SECURITY_NOTICE.md) - RSA key storage best practices
- [Schema Grants](guide/SCHEMA_GRANTS.md) - Managing schema-level permissions

---

## Agents (LLM Configuration)

Configuration files for using LLMs with this codebase.

- [README](agents/README.md) - Overview and quick start
- [CLAUDE.md](agents/CLAUDE.md) - Full project instructions for Claude
- [CONTEXT.md](agents/CONTEXT.md) - Domain knowledge and project context
- [PATTERNS.md](agents/PATTERNS.md) - Code patterns and conventions

---

## Contributing

For developers and contributors.

- [Contributing Guide](contributing/CONTRIBUTING.md) - How to contribute
- [Testing Guide](contributing/HOW_TO_TEST.md) - Running and writing tests
- [Agent Safety Architecture](contributing/AGENT_SAFETY_ARCHITECTURE.md) - AI agent system
- [Agent Communication Matrix](contributing/AGENT_COMMUNICATION_MATRIX.md) - Agent patterns

---

## Releases

- [Changelog](releases/CHANGELOG.md) - Version history
- [v0.1 Release](releases/v0.1/) - Initial release docs

---

## Examples

Configuration examples, integrations, and templates.

- [Recce Setup](examples/RECCE_SETUP.md) - Integration guide
- Sample files: JSON, Python, and YAML examples

---

## Blog

Development journey and lessons learned: [Blog](blog/)

---

## Archive

Historical documentation: [Archive](archive/)

---

## Need Help?

- [Troubleshooting Guide](guide/TROUBLESHOOTING.md)
- Run `uv run snowtower` for interactive help
- [GitHub Issues](https://github.com/Database-Tycoon/snowtower/issues)

---

**Last Updated**: November 2025
