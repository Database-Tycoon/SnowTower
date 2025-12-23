# SnowTower Core Module

This module contains the core business logic and data models for the SnowTower infrastructure management platform.

## Components

- **`models.py`** - Core data models and Pydantic schemas
- **`managers.py`** - Business logic managers for infrastructure operations
- **`exceptions.py`** - Custom exception classes
- **`config.py`** - Configuration management utilities

## Architecture

The core module follows a layered architecture:
- **Models Layer**: Data structures and validation
- **Managers Layer**: Business logic and operations
- **Configuration Layer**: Environment and settings management

## Integration

This module is designed to be imported by:
- CLI commands in `src/management_cli.py`
- Scripts in the `scripts/` directory
- Web interface components in `src/web/`

## Dependencies

- Pydantic for data validation
- SnowDDL for infrastructure operations
- Snowflake connector for database operations
