# LLM Context Configuration

This directory contains context files for LLMs (Claude, GPT, etc.) working with the SnowTower codebase.

## Files

| File | Purpose |
|------|---------|
| [CLAUDE.md](CLAUDE.md) | Detailed instructions for Claude Code |
| [CONTEXT.md](CONTEXT.md) | Project context and domain knowledge |
| [PATTERNS.md](PATTERNS.md) | Code patterns and conventions to follow |

## Quick Start

### For Claude Code Users

The root `CLAUDE.md` file is automatically loaded by Claude Code. It contains:
- Project overview and architecture
- Key commands and workflows
- Code patterns to follow
- Safety guidelines

### For Other LLMs

Copy the contents of `CLAUDE.md` into your system prompt or context window.

## Project-Specific Instructions

When working with this codebase, LLMs should:

1. **Always use UV for Python** - Never use pip directly
2. **Follow the command pattern** - Scripts go in `scripts/`, wrappers in `src/management_cli.py`
3. **Use load_dotenv()** - Every script must load environment variables
4. **Check before modifying** - Run `uv run snowddl-plan` before any changes

## Key Directories

```
snowtower-snowddl/
├── snowddl/          # YAML infrastructure definitions (MODIFY WITH CARE)
├── src/              # Python source code
│   ├── snowddl_core/ # OOP framework for SnowDDL
│   └── management_cli.py  # CLI entry points
├── scripts/          # Management scripts
├── docs/             # Documentation
└── tests/            # Test files
```

## Safety Guidelines

LLMs working with this codebase should:

- **Never run `snowddl-apply` without user confirmation**
- **Always show plan output before applying changes**
- **Never modify production credentials**
- **Always use `--dry-run` when available**
