"""
GitHub Issue Parser for SnowTower Access Requests

Extracts structured user data from GitHub issue markdown templates.
Supports multiple template formats and validation of parsed data.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from rich.console import Console

console = Console()


class IssueParsingError(Exception):
    """Raised when issue data cannot be parsed"""

    pass


class UserTypeSelection(str, Enum):
    """User type options from issue template"""

    PERSON = "person"
    SERVICE = "service"


class RoleTypeSelection(str, Enum):
    """Role type options from issue template"""

    DATA_ANALYST = "data_analyst"
    BI_DEVELOPER = "bi_developer"
    DATA_ENGINEER = "data_engineer"
    TRAINING = "training"
    INTEGRATION_SERVICE = "integration_service"
    AI_ML_SERVICE = "ai_ml_service"


class WorkloadSize(str, Enum):
    """Workload size options"""

    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    DEVELOPMENT = "development"


@dataclass
class ParsedIssueData:
    """Structured data parsed from GitHub issue"""

    # Basic Information
    full_name: str
    email: str
    username: Optional[str] = None

    # User Classification
    user_type: UserTypeSelection = UserTypeSelection.PERSON
    role_type: Optional[RoleTypeSelection] = None

    # Access Requirements
    warehouse_size: WorkloadSize = WorkloadSize.LIGHT
    business_justification: str = ""

    # Management Information
    manager_email: Optional[str] = None
    project_team: Optional[str] = None

    # Urgency
    urgency: str = "Standard"
    urgency_justification: Optional[str] = None

    # Compliance
    data_handling_confirmed: bool = False

    # Additional Information
    additional_comments: Optional[str] = None
    rsa_public_key: Optional[str] = None

    # Metadata
    issue_number: Optional[int] = None
    issue_url: Optional[str] = None

    def validate(self) -> List[str]:
        """
        Validate parsed data and return list of errors.

        Returns:
            List of validation error messages
        """
        errors = []

        # Required fields
        if not self.full_name or self.full_name.strip() == "":
            errors.append("Full name is required")

        if not self.email or self.email.strip() == "":
            errors.append("Email is required")

        # Email format validation
        if self.email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", self.email):
            errors.append(f"Invalid email format: {self.email}")

        # Business justification (optional - can be brief)
        # Old template: "Why do you need access?" - can be short
        # New template: "Business Justification" - should be detailed
        # We'll make this a warning, not an error
        pass  # Business justification is optional

        # Data handling confirmation
        if not self.data_handling_confirmed:
            errors.append("Data handling acknowledgment must be confirmed")

        # Urgency justification for high urgency
        if (
            self.urgency.lower() in ["high", "critical"]
            and not self.urgency_justification
        ):
            errors.append(
                "Urgency justification required for high/critical urgency requests"
            )

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "full_name": self.full_name,
            "email": self.email,
            "username": self.username,
            "user_type": (
                self.user_type.value
                if isinstance(self.user_type, Enum)
                else self.user_type
            ),
            "role_type": (
                self.role_type.value
                if isinstance(self.role_type, Enum)
                else self.role_type
            ),
            "warehouse_size": (
                self.warehouse_size.value
                if isinstance(self.warehouse_size, Enum)
                else self.warehouse_size
            ),
            "business_justification": self.business_justification,
            "manager_email": self.manager_email,
            "project_team": self.project_team,
            "urgency": self.urgency,
            "urgency_justification": self.urgency_justification,
            "data_handling_confirmed": self.data_handling_confirmed,
            "additional_comments": self.additional_comments,
            "rsa_public_key": self.rsa_public_key,
            "issue_number": self.issue_number,
            "issue_url": self.issue_url,
        }


class GitHubIssueParser:
    """
    Parser for GitHub issue bodies containing access request forms.

    Extracts user data from markdown-formatted issue templates and
    validates the extracted information.
    """

    # Field extraction patterns
    PATTERNS = {
        "full_name": r"### (?:Full Name|Name)\s*\n\s*(.+)",
        "email": r"### Email(?:\s+Address)?\s*\n\s*(.+)",
        "username": r"### (?:Preferred )?Username\s*\n\s*(.+)",
        "user_type": r"### (?:Account Type|What type of user are you\?)\s*\n\s*(.+)",
        "role_type": r"### (?:Primary Role|Role)\s*\n\s*(.+)",
        "warehouse_size": r"### (?:Expected Workload|Workload)\s*\n\s*(.+)",
        "business_justification": r"### (?:Business Justification|Why do you need access\?)\s*\n\s*((?:.|\n)*?)(?=\n### |$)",
        "manager_email": r"### (?:Manager(?:/Sponsor)? Email|Manager)\s*\n\s*(.+)",
        "project_team": r"### (?:Project/Team|Project|Team)\s*\n\s*(.+)",
        "urgency": r"### (?:Urgency Level|Urgency)\s*\n\s*(.+)",
        "urgency_justification": r"### (?:Urgency Justification|Why urgent\?)\s*\n\s*((?:.|\n)*?)(?=\n### |$)",
        "additional_comments": r"### (?:Additional Comments|Comments|Notes)\s*\n\s*((?:.|\n)*?)(?=\n### |$)",
        "rsa_public_key": r"### (?:RSA Public Key|Public Key)\s*\n\s*```(?:.*\n)?((?:.|\n)*?)```",
    }

    # Checkbox patterns (supports old and new template formats)
    CHECKBOX_PATTERNS = {
        "data_handling_confirmed": r"\[x\].*(?:I understand that I will have access to sensitive|data handling|I will follow all company data security policies)",
    }

    def __init__(self):
        """Initialize the parser"""
        self.console = Console()

    def parse_issue(
        self, issue_body: str, issue_number: Optional[int] = None
    ) -> ParsedIssueData:
        """
        Parse GitHub issue body and extract form data.

        Args:
            issue_body: Raw issue body markdown text
            issue_number: Optional issue number for metadata

        Returns:
            ParsedIssueData object with extracted information

        Raises:
            IssueParsingError: If required data cannot be extracted
        """
        if not issue_body or issue_body.strip() == "":
            raise IssueParsingError("Issue body is empty")

        # Extract text fields
        extracted_data = {}
        for field, pattern in self.PATTERNS.items():
            match = re.search(pattern, issue_body, re.MULTILINE | re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean up common form artifacts
                if value and value not in ["_No response_", "No response", "N/A", ""]:
                    extracted_data[field] = value

        # Extract checkboxes
        for field, pattern in self.CHECKBOX_PATTERNS.items():
            match = re.search(pattern, issue_body, re.IGNORECASE)
            extracted_data[field] = bool(match)

        # Build ParsedIssueData object
        try:
            parsed_data = ParsedIssueData(
                full_name=extracted_data.get("full_name", ""),
                email=extracted_data.get("email", ""),
                username=extracted_data.get("username"),
                user_type=self._parse_user_type(extracted_data.get("user_type", "")),
                role_type=self._parse_role_type(extracted_data.get("role_type")),
                warehouse_size=self._parse_workload(
                    extracted_data.get("warehouse_size", "")
                ),
                business_justification=extracted_data.get("business_justification", ""),
                manager_email=extracted_data.get("manager_email"),
                project_team=extracted_data.get("project_team"),
                urgency=extracted_data.get("urgency", "Standard"),
                urgency_justification=extracted_data.get("urgency_justification"),
                data_handling_confirmed=extracted_data.get(
                    "data_handling_confirmed", False
                ),
                additional_comments=extracted_data.get("additional_comments"),
                rsa_public_key=extracted_data.get("rsa_public_key"),
                issue_number=issue_number,
            )
        except Exception as e:
            raise IssueParsingError(f"Failed to construct parsed data: {e}")

        # Validate parsed data
        validation_errors = parsed_data.validate()
        if validation_errors:
            error_msg = "Validation errors:\n" + "\n".join(
                f"  - {err}" for err in validation_errors
            )
            raise IssueParsingError(error_msg)

        console.print(
            f"[green]✓ Successfully parsed issue data for: {parsed_data.full_name}[/green]"
        )
        return parsed_data

    def parse_from_gh_api(self, issue_number: int) -> ParsedIssueData:
        """
        Parse issue directly from GitHub API using gh CLI.

        Args:
            issue_number: GitHub issue number

        Returns:
            ParsedIssueData object

        Raises:
            IssueParsingError: If issue cannot be fetched or parsed
        """
        import subprocess
        import json

        try:
            # Fetch issue using gh CLI
            result = subprocess.run(
                ["gh", "issue", "view", str(issue_number), "--json", "body,url"],
                capture_output=True,
                text=True,
                check=True,
            )

            issue_data = json.loads(result.stdout)
            issue_body = issue_data.get("body", "")
            issue_url = issue_data.get("url", "")

            # Parse the issue
            parsed_data = self.parse_issue(issue_body, issue_number)
            parsed_data.issue_url = issue_url

            return parsed_data

        except subprocess.CalledProcessError as e:
            raise IssueParsingError(
                f"Failed to fetch issue #{issue_number} from GitHub: {e.stderr}"
            )
        except json.JSONDecodeError as e:
            raise IssueParsingError(f"Failed to parse GitHub API response: {e}")
        except Exception as e:
            raise IssueParsingError(f"Unexpected error fetching issue: {e}")

    def _parse_user_type(self, value: str) -> UserTypeSelection:
        """Parse user type from string"""
        if not value:
            return UserTypeSelection.PERSON

        value_lower = value.lower()
        if "service" in value_lower or "service account" in value_lower:
            return UserTypeSelection.SERVICE
        else:
            return UserTypeSelection.PERSON

    def _parse_role_type(self, value: Optional[str]) -> Optional[RoleTypeSelection]:
        """Parse role type from string"""
        if not value:
            return None

        value_lower = value.lower()

        # Map common patterns to role types
        if "data analyst" in value_lower or "analyst" in value_lower:
            return RoleTypeSelection.DATA_ANALYST
        elif "bi developer" in value_lower or "bi" in value_lower:
            return RoleTypeSelection.BI_DEVELOPER
        elif "data engineer" in value_lower or "engineer" in value_lower:
            return RoleTypeSelection.DATA_ENGINEER
        elif "training" in value_lower or "learning" in value_lower:
            return RoleTypeSelection.TRAINING
        elif "integration" in value_lower:
            return RoleTypeSelection.INTEGRATION_SERVICE
        elif "ai" in value_lower or "ml" in value_lower:
            return RoleTypeSelection.AI_ML_SERVICE

        return None

    def _parse_workload(self, value: str) -> WorkloadSize:
        """Parse workload size from string"""
        if not value:
            return WorkloadSize.LIGHT

        value_lower = value.lower()

        if "light" in value_lower or "small" in value_lower:
            return WorkloadSize.LIGHT
        elif "medium" in value_lower:
            return WorkloadSize.MEDIUM
        elif "heavy" in value_lower or "large" in value_lower:
            return WorkloadSize.HEAVY
        elif "dev" in value_lower:
            return WorkloadSize.DEVELOPMENT

        return WorkloadSize.LIGHT
