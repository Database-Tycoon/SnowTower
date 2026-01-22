# SnowTower Claude Code Skills

This directory contains Claude Code skills for different user personas working with SnowTower.

## Available Skills

### 🧑‍💻 [snowtower-developer](./snowtower-developer/)
**For: Code Contributors**

Comprehensive development guide covering:
- Development environment setup
- Codebase architecture
- Creating UV commands
- Writing tests
- Debugging workflows
- Pull request process
- Code review guidelines

**Invoke with:** `/snowtower-developer` or mention "developer workflow", "add feature", "write tests"

---

### 👨‍💼 [snowtower-admin](./snowtower-admin/)
**For: Infrastructure Administrators**

Advanced administrative operations including:
- SnowDDL deployments
- User provisioning and lifecycle
- Role and permission management
- Warehouse optimization
- Cost analysis
- Security audits
- Troubleshooting production issues

**Invoke with:** `/snowtower-admin` or mention "deploy", "snowddl", "user creation", "infrastructure"

---

### 👥 [snowtower-user](./snowtower-user/)
**For: End Users**

Getting started and basic operations:
- Requesting Snowflake access
- Generating RSA keys
- Connecting to Snowflake
- Basic SQL queries
- Understanding roles and permissions
- Troubleshooting connection issues

**Invoke with:** `/snowtower-user` or mention "access request", "connection", "RSA keys"

---

### 📝 [snowtower-maintainer](./snowtower-maintainer/)
**For: Project Maintainers**

Project maintenance and documentation:
- README updates
- Documentation synchronization
- Claude configuration management
- Project structure audits
- Release management

**Invoke with:** `/snowtower-maintainer` or mention "documentation", "README", "project maintenance"

---

## Skill Usage Guide

### How to Invoke a Skill

In Claude Code, you can invoke skills in several ways:

1. **Direct command:**
   ```
   /snowtower-developer
   ```

2. **Natural language mention:**
   ```
   "Use the developer skill to help me add a new feature"
   "I need admin help deploying changes"
   "Show me the user guide for connecting to Snowflake"
   ```

3. **Context-based automatic triggering:**
   Skills may auto-trigger based on keywords:
   - "deploy", "snowddl" → admin skill
   - "test", "PR", "feature" → developer skill
   - "access", "connection" → user skill

### Choosing the Right Skill

| Task | Skill | Example |
|------|-------|---------|
| Add new feature | Developer | "Help me create a new UV command" |
| Deploy to Snowflake | Admin | "How do I safely deploy these changes?" |
| Request account access | User | "I need to connect to Snowflake" |
| Update documentation | Maintainer | "Sync README with latest changes" |
| Fix a bug | Developer | "Debug this test failure" |
| Create new user | Admin | "Provision a new user account" |
| Setup dev environment | Developer | "Initialize my development environment" |
| Run cost analysis | Admin | "Analyze warehouse costs" |

### Skill Overlap

Some tasks may use multiple skills:

- **Release Management**: Developer (code/tests) + Maintainer (docs/changelog)
- **New User Onboarding**: User (initial access) + Admin (provisioning)
- **Feature Development**: Developer (code) + Admin (infrastructure changes)

## Contributing to Skills

Skills are written in Markdown and located in `.claude/skills/<skill-name>/SKILL.md`.

### Adding a New Skill

1. Create directory: `.claude/skills/my-new-skill/`
2. Create `SKILL.md` with frontmatter:
   ```markdown
   ---
   name: my-new-skill
   description: Brief description of when to use this skill
   ---

   # Skill content here...
   ```
3. Create `README.md` with overview
4. Update this file to reference the new skill

### Improving Existing Skills

1. Edit the `SKILL.md` file
2. Test the skill by invoking it
3. Submit a PR with improvements
4. Document any new patterns discovered

## Skill Architecture

Each skill follows this structure:

```
snowtower-<name>/
├── SKILL.md          # Main skill content (required)
├── README.md         # Overview and quick reference (recommended)
└── examples/         # Code examples (optional)
```

### SKILL.md Format

```markdown
---
name: skill-name
description: Trigger conditions and purpose
---

# Skill Title

## Who This Skill Is For
- Persona 1
- Persona 2

## Quick Command Reference
Common commands

## Detailed Sections
Topic-specific guidance

## Examples
Practical examples

## Troubleshooting
Common issues
```

## Best Practices

1. **Keep skills focused** - Each skill targets a specific persona/use case
2. **Provide examples** - Show, don't just tell
3. **Update regularly** - Keep skills in sync with codebase changes
4. **Cross-reference** - Link to related skills and documentation
5. **Test invocation** - Verify skills can be triggered correctly
6. **Use clear triggers** - Document keywords that activate the skill

## Integration with Documentation

Skills complement the main documentation:

- **Skills**: Interactive, task-oriented, persona-specific
- **Docs**: Comprehensive, reference-oriented, complete coverage

Users should:
- Use **skills** for guided workflows and common tasks
- Refer to **docs** for deep dives and complete reference

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ SnowTower Skills Quick Reference                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 🧑‍💻 Developer  → Code, Tests, PRs, Debugging          │
│ 👨‍💼 Admin     → Deploy, Users, Roles, Warehouses      │
│ 👥 User       → Access, Connect, Basic Usage           │
│ 📝 Maintainer → Docs, README, Project Structure        │
│                                                         │
│ Invoke: /snowtower-<skill-name>                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

**For more information, see individual skill README files or the main project documentation at `/docs`.**
