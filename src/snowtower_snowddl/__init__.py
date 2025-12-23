"""
SnowTower SnowDDL Configuration Repository

This package provides configuration management and validation for SnowDDL infrastructure as code.
"""

__version__ = "0.1.0"

# Expose CLI module
try:
    from . import cli
except ImportError:
    # Handle cases where dependencies might not be installed
    cli = None

# Expose main CLI functions for direct import
try:
    from .cli import (
        plan,
        apply,
        validate_config,
        diff,
        lint_config,
        update_user_password,
    )
except ImportError:
    # Handle cases where dependencies might not be installed
    pass
