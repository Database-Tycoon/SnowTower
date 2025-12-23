# Test Suite

This directory contains the comprehensive test suite for the SnowTower SnowDDL project.

## Structure

- **`conftest.py`** - Pytest configuration and shared fixtures
- **`fixtures/`** - Test data and configuration templates
- **`integration/`** - Integration tests for core functionality
- **`manual/`** - Manual test scripts and procedures
- **`test_*.py`** - Unit test files

## Running Tests

### All Tests
```bash
uv run pytest
```

### Specific Test Categories
```bash
# Unit tests only
uv run pytest tests/test_*.py

# Integration tests
uv run pytest tests/integration/

# With coverage
uv run pytest --cov=src
```

## Test Categories

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **Manual Tests**: Scripts for manual verification and debugging

## Configuration

Test configuration is managed through:
- `pytest.ini` in the project root
- `conftest.py` for shared fixtures
- Environment variables for test credentials (use `.env.test`)
