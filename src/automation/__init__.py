"""
Automation Module for SnowTower SnowDDL

Provides automation capabilities for infrastructure management including:
- GitHub issue parsing and processing
- Automated user configuration generation
- PR creation and workflow integration
- S3 configuration synchronization
- Validation and security checks
"""

from .issue_parser import GitHubIssueParser, IssueParsingError
from .yaml_generator import SnowDDLYAMLGenerator, YAMLGenerationError
from .pr_creator import GitHubPRCreator, PRCreationError
from .validator import UserConfigValidator, ValidationError

__all__ = [
    "GitHubIssueParser",
    "IssueParsingError",
    "SnowDDLYAMLGenerator",
    "YAMLGenerationError",
    "GitHubPRCreator",
    "PRCreationError",
    "UserConfigValidator",
    "ValidationError",
]
