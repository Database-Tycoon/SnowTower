# Python Development Agent Guide

The Python Development Agent specializes in writing Python scripts that interact with the SnowDDL OOP framework, following established patterns and best practices.

## Core Responsibilities

### 1. Script Development for UV Commands

#### Required Script Structure
Every script MUST follow this pattern:

```python
#!/usr/bin/env python3
"""
Docstring explaining the script's purpose.
Include usage examples and key features.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv  # CRITICAL: Required for all scripts
import argparse

# MANDATORY: Load environment variables first
load_dotenv()

# Add parent src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import from OOP framework
from snowddl_core.project import SnowDDLProject
from snowddl_core.safety import CheckpointManager, SafetyValidator
# Import other components as needed

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--config", default="./snowddl", help="Config directory")

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Example subcommand
    list_parser = subparsers.add_parser("list", help="List items")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load project
    project = SnowDDLProject(args.config)

    # Execute command logic
    if args.command == "list":
        # Implementation
        pass

if __name__ == "__main__":
    main()
```

### 2. SnowDDL OOP Framework Integration

#### Key Classes to Use

**SnowDDLProject**: Main project class
```python
project = SnowDDLProject("./snowddl")
project.load_all()  # Load all configurations
project.save_all()  # Save all changes
```

**Object Access Patterns**:
```python
# Users
for name, user in project.users.items():
    print(f"{name}: {user.email}")

# Warehouses
warehouse = project.get_warehouse("DEV_WH")
warehouse.auto_suspend = 60
project.save_warehouses()

# Roles
role = project.get_role("ANALYST_ROLE")
```

**Safety Components**:
```python
# Create checkpoint before changes
checkpoint_mgr = CheckpointManager(project)
checkpoint_id = checkpoint_mgr.create_checkpoint("Before changes")

# Validate changes
validator = SafetyValidator()
validation_result = validator.validate_changes(changes)
```

### 3. Common Patterns

#### Pattern 1: List and Report
```python
def list_items(project: SnowDDLProject):
    print(f"{'Name':<30} {'Type':<15} {'Status':<10}")
    print("-" * 60)

    for name, item in project.items.items():
        print(f"{name:<30} {item.type:<15} {item.status:<10}")
```

#### Pattern 2: Modify and Save
```python
def modify_items(project: SnowDDLProject, args):
    checkpoint_mgr = CheckpointManager(project)
    checkpoint_id = checkpoint_mgr.create_checkpoint("Before modification")

    modified = []
    for name, item in project.items.items():
        if meets_criteria(item):
            item.property = new_value
            modified.append(name)

    if args.save and modified:
        project.save_items()
        print(f"Saved {len(modified)} changes")
```

#### Pattern 3: Bulk Operations
```python
def bulk_update(project: SnowDDLProject, updates: dict):
    for name, changes in updates.items():
        item = project.get_item(name)
        if item:
            for key, value in changes.items():
                setattr(item, key, value)

    project.save_all()
```

### 4. Error Handling

```python
try:
    project = SnowDDLProject(args.config)
except FileNotFoundError:
    print(f"❌ Config directory not found: {args.config}")
    return 1
except Exception as e:
    print(f"❌ Error loading project: {e}")
    return 1
```

### 5. Output Formatting

Use consistent formatting:
```python
# Success messages
print(f"✅ Operation completed successfully")

# Warning messages
print(f"⚠️  Warning: {message}")

# Error messages
print(f"❌ Error: {message}")

# Info messages
print(f"📊 {info}")
```

## Integration with UV Commands

### Required Files
1. Script in `scripts/` directory
2. Wrapper in `src/management_cli.py`
3. Registration in `pyproject.toml`

### Testing Checklist
- [ ] Script has `load_dotenv()`
- [ ] Script has `main()` function
- [ ] Script handles `--help`
- [ ] Script validates arguments
- [ ] Script loads SnowDDLProject correctly
- [ ] Script creates checkpoints before changes
- [ ] Script has proper error handling

## Delegation Requirements

The Python Development Agent should delegate to:
- **Security Agent**: For security review of generated code
- **Testing Agent**: For creating test cases
- **Documentation Agent**: For updating command documentation

## Common Pitfalls to Avoid

1. **Forgetting load_dotenv()**: Always load environment variables
2. **Direct YAML manipulation**: Use OOP framework instead
3. **No checkpoints**: Always create checkpoints before changes
4. **Hardcoded paths**: Use argparse for configuration
5. **Missing validation**: Validate user input and changes

## Examples from Existing Scripts

### From `manage_warehouses.py`:
- List with formatted table output
- Resize with --save flag pattern
- Optimization recommendations

### From `security_audit.py`:
- MFA compliance checking
- Sacred account protection
- Detailed reporting

### From `backup_restore.py`:
- Timestamp-based operations
- File system operations
- Metadata management

## See Also

- [PROJECT_ARCHITECT_AGENT.md](PROJECT_ARCHITECT_AGENT.md) - Project structure
- [META_AGENT.md](META_AGENT.md) - Agent coordination
- [OOP_IMPLEMENTATION_SUMMARY.md](../implementation/OOP_IMPLEMENTATION_SUMMARY.md) - Framework details
