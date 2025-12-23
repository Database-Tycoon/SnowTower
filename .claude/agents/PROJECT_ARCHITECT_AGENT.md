# Project Architect Agent Guide

The Project Architect Agent specializes in structuring and organizing SnowDDL projects, including creating new command-line tools and maintaining project architecture.

## Core Responsibilities

### 1. UV Command Creation
The Project Architect follows the established UV command pattern for creating new CLI tools.

#### UV Command Pattern Architecture
```
User Input → uv run <command> → management_cli.py → scripts/<script>.py → SnowDDL OOP Framework → YAML files
```

#### Steps to Create New UV Commands

1. **Script Creation** (`scripts/<new_script>.py`):
```python
#!/usr/bin/env python3
"""
Description of what this script does.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import argparse

# CRITICAL: Load environment variables for password encryption
load_dotenv()

# Add parent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.project import SnowDDLProject
from snowddl_core.safety import CheckpointManager

def main():
    parser = argparse.ArgumentParser(description="Your command description")
    parser.add_argument("--config", default="./snowddl", help="Config directory")

    # Add subcommands or arguments as needed
    args = parser.parse_args()

    # Load project
    project = SnowDDLProject(args.config)

    # Implement functionality
    # ...

if __name__ == "__main__":
    main()
```

2. **Management CLI Integration** (`src/management_cli.py`):
```python
def new_command():
    """Run new command description."""
    from new_script import main
    main()
```

3. **PyProject Registration** (`pyproject.toml`):
```toml
[project.scripts]
new-command = "management_cli:new_command"
new-cmd = "management_cli:new_command"  # Optional alias
```

4. **Testing**:
```bash
uv sync
uv run new-command --help
```

### 2. Project Structure Maintenance

- Organize scripts in `scripts/` directory
- Maintain OOP framework in `src/snowddl_core/`
- Keep documentation in `docs/`
- Ensure proper module imports and paths

### 3. Integration Patterns

#### SnowDDL OOP Framework Integration
- All scripts should use `SnowDDLProject` class
- Use `CheckpointManager` for safety
- Follow established patterns from existing scripts

#### Environment Variable Handling
- Always call `load_dotenv()` first
- Support `.env` file for configuration
- Handle Fernet encryption keys properly

## Delegation Requirements

**CRITICAL**: The Project Architect Agent MUST delegate to specialized subagents:

- **Python Development Agent**: For writing the actual Python code
- **Security Agent**: For reviewing security implications
- **Documentation Agent**: For updating documentation
- **Testing Agent**: For creating test cases

## Example Workflow

When asked to create a new UV command for "database management":

1. **Delegate to Python Development Agent** to create `scripts/manage_databases.py`
2. **Update** `src/management_cli.py` with new wrapper function
3. **Register** command in `pyproject.toml`
4. **Delegate to Documentation Agent** to update `docs/MANAGEMENT_COMMANDS.md`
5. **Test** the new command with `uv run databases --help`

## Best Practices

1. **Consistency**: Follow patterns from existing commands
2. **Safety**: Always create checkpoints before modifications
3. **Documentation**: Update docs for every new command
4. **Testing**: Include `--help` and basic functionality tests
5. **Environment**: Ensure `.env` loading for all scripts

## Common UV Commands Already Implemented

- `warehouses` - Warehouse management
- `costs` - Cost optimization
- `security` - Security auditing
- `backup` - Backup and restore
- `users` - User management

## Troubleshooting

### Module Not Found Error
- Ensure `scripts/__init__.py` exists
- Check path additions in management_cli.py
- Run `uv sync` after pyproject.toml changes

### Command Not Working
- Verify function name in management_cli.py
- Check pyproject.toml registration
- Ensure main() function exists in script

## See Also

- [META_AGENT.md](META_AGENT.md) - Overview of agent coordination
- [MANAGEMENT_COMMANDS.md](../MANAGEMENT_COMMANDS.md) - Command reference
- [OOP_DESIGN.md](../architecture/OOP_DESIGN.md) - Framework architecture
