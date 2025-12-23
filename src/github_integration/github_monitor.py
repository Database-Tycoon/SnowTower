#!/usr/bin/env python3
"""
GitHub PR Monitor for SnowDDL Configuration Manager

This module monitors Snowflake stages for pending PR requests and automatically
creates GitHub branches and pull requests.

Author: SnowTower Team
Date: 2025-01-14
"""

import os
import sys
import json
import time
import logging
import argparse
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

import snowflake.connector
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("github_monitor.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class GitHubConfig:
    """Configuration for GitHub integration"""

    token: str
    repo_owner: str
    repo_name: str
    api_url: str = "https://api.github.com"
    base_branch: str = "main"
    auto_merge: bool = False
    reviewer_teams: List[str] = None
    max_files_per_pr: int = 10

    def __post_init__(self):
        if self.reviewer_teams is None:
            self.reviewer_teams = []


@dataclass
class SnowflakeConfig:
    """Configuration for Snowflake connection"""

    account: str
    user: str
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    role: str = "SNOWDDL_CONFIG_MANAGER"
    warehouse: str = "COMPUTE_WH"
    database: str = "SNOWDDL_CONFIG"
    schema: str = "PUBLIC"


@dataclass
class PRRequest:
    """Data class for PR request"""

    request_id: str
    branch_name: str
    pr_title: str
    pr_description: str
    target_branch: str
    file_name: str
    file_content: str
    created_by: str
    priority: int
    created_at: datetime
    stage_path: str


class GitHubIntegrationError(Exception):
    """Custom exception for GitHub integration errors"""

    pass


class SnowflakeConnector:
    """Handle Snowflake database operations"""

    def __init__(self, config: SnowflakeConfig):
        self.config = config
        self.connection = None

    def connect(self) -> None:
        """Establish connection to Snowflake"""
        try:
            connection_params = {
                "account": self.config.account,
                "user": self.config.user,
                "role": self.config.role,
                "warehouse": self.config.warehouse,
                "database": self.config.database,
                "schema": self.config.schema,
            }

            # Use RSA key authentication if available, otherwise password
            if self.config.private_key_path and os.path.exists(
                self.config.private_key_path
            ):
                logger.info("Using RSA key authentication")
                with open(self.config.private_key_path, "rb") as key_file:
                    private_key = key_file.read()

                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.serialization import (
                    load_pem_private_key,
                )

                if self.config.private_key_passphrase:
                    passphrase = self.config.private_key_passphrase.encode()
                else:
                    passphrase = None

                pkey = load_pem_private_key(private_key, password=passphrase)
                pkb = pkey.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                connection_params["private_key"] = pkb
            elif self.config.password:
                logger.info("Using password authentication")
                connection_params["password"] = self.config.password
            else:
                raise GitHubIntegrationError(
                    "No valid authentication method configured"
                )

            self.connection = snowflake.connector.connect(**connection_params)
            logger.info("Successfully connected to Snowflake")

        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise GitHubIntegrationError(f"Snowflake connection failed: {e}")

    def disconnect(self) -> None:
        """Close Snowflake connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from Snowflake")

    def execute_procedure(self, procedure_name: str, params: List[Any] = None) -> Any:
        """Execute a stored procedure"""
        if not self.connection:
            raise GitHubIntegrationError("Not connected to Snowflake")

        try:
            cursor = self.connection.cursor()

            if params:
                cursor.callproc(procedure_name, params)
            else:
                cursor.callproc(procedure_name)

            result = cursor.fetchone()
            cursor.close()

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Failed to execute procedure {procedure_name}: {e}")
            raise GitHubIntegrationError(f"Procedure execution failed: {e}")

    def get_next_pending_request(self, processor_id: str) -> Optional[PRRequest]:
        """Get the next pending PR request"""
        try:
            result = self.execute_procedure(
                "SP_GET_NEXT_PENDING_REQUEST", [processor_id]
            )

            if not result:
                return None

            # Parse the JSON result
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result

            if data.get("status") != "SUCCESS":
                if data.get("status") == "NO_PENDING_REQUESTS":
                    return None
                else:
                    logger.warning(
                        f"Get next request returned: {data.get('message', 'Unknown error')}"
                    )
                    return None

            # Create PRRequest object
            return PRRequest(
                request_id=data["REQUEST_ID"],
                branch_name=data["BRANCH_NAME"],
                pr_title=data["PR_TITLE"],
                pr_description=data.get("PR_DESCRIPTION", ""),
                target_branch=data["TARGET_BRANCH"],
                file_name=data["FILE_NAME"],
                file_content=data["FILE_CONTENT"]["content"],
                created_by=data["CREATED_BY"],
                priority=data["PRIORITY"],
                created_at=datetime.fromisoformat(
                    data["CREATED_AT"].replace("Z", "+00:00")
                ),
                stage_path=data["STAGE_PATH"],
            )

        except Exception as e:
            logger.error(f"Failed to get next pending request: {e}")
            raise GitHubIntegrationError(f"Failed to get pending request: {e}")

    def update_request_status(
        self,
        request_id: str,
        status: str,
        github_branch_url: str = None,
        github_pr_url: str = None,
        github_pr_number: int = None,
        error_message: str = None,
        processor_id: str = None,
    ) -> None:
        """Update the status of a PR request"""
        try:
            params = [
                request_id,
                status,
                github_branch_url,
                github_pr_url,
                github_pr_number,
                error_message,
                processor_id,
            ]

            result = self.execute_procedure("SP_UPDATE_REQUEST_STATUS", params)

            if not result or not result.startswith("SUCCESS"):
                raise GitHubIntegrationError(f"Status update failed: {result}")

            logger.info(f"Updated request {request_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update request status: {e}")
            raise GitHubIntegrationError(f"Status update failed: {e}")


class GitHubClient:
    """Handle GitHub API operations"""

    def __init__(self, config: GitHubConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {config.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "SnowDDL-GitHub-Monitor/1.0",
            }
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request to GitHub"""
        url = f"{self.config.api_url}/{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise GitHubIntegrationError(f"GitHub API error: {e}")

    def get_repository_info(self) -> Dict[str, Any]:
        """Get repository information"""
        response = self._make_request(
            "GET", f"repos/{self.config.repo_owner}/{self.config.repo_name}"
        )
        return response.json()

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists"""
        try:
            self._make_request(
                "GET",
                f"repos/{self.config.repo_owner}/{self.config.repo_name}/branches/{branch_name}",
            )
            return True
        except GitHubIntegrationError:
            return False

    def create_branch(
        self, branch_name: str, base_branch: str = None
    ) -> Dict[str, Any]:
        """Create a new branch"""
        if base_branch is None:
            base_branch = self.config.base_branch

        # Get the SHA of the base branch
        response = self._make_request(
            "GET",
            f"repos/{self.config.repo_owner}/{self.config.repo_name}/git/refs/heads/{base_branch}",
        )
        base_sha = response.json()["object"]["sha"]

        # Create the new branch
        data = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}

        response = self._make_request(
            "POST",
            f"repos/{self.config.repo_owner}/{self.config.repo_name}/git/refs",
            json=data,
        )
        result = response.json()

        logger.info(f"Created branch {branch_name} from {base_branch}")
        return result

    def create_or_update_file(
        self, branch_name: str, file_path: str, content: str, commit_message: str
    ) -> Dict[str, Any]:
        """Create or update a file in the repository"""
        import base64

        # Encode content to base64
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # Check if file exists to get its SHA
        file_sha = None
        try:
            response = self._make_request(
                "GET",
                f"repos/{self.config.repo_owner}/{self.config.repo_name}/contents/{file_path}?ref={branch_name}",
            )
            file_sha = response.json()["sha"]
        except GitHubIntegrationError:
            # File doesn't exist, which is fine for creation
            pass

        # Prepare the data
        data = {
            "message": commit_message,
            "content": encoded_content,
            "branch": branch_name,
        }

        if file_sha:
            data["sha"] = file_sha

        # Create or update the file
        response = self._make_request(
            "PUT",
            f"repos/{self.config.repo_owner}/{self.config.repo_name}/contents/{file_path}",
            json=data,
        )
        result = response.json()

        logger.info(
            f"{'Updated' if file_sha else 'Created'} file {file_path} in branch {branch_name}"
        )
        return result

    def create_pull_request(
        self, branch_name: str, title: str, description: str, base_branch: str = None
    ) -> Dict[str, Any]:
        """Create a pull request"""
        if base_branch is None:
            base_branch = self.config.base_branch

        data = {
            "title": title,
            "body": description,
            "head": branch_name,
            "base": base_branch,
        }

        response = self._make_request(
            "POST",
            f"repos/{self.config.repo_owner}/{self.config.repo_name}/pulls",
            json=data,
        )
        result = response.json()

        logger.info(f"Created PR #{result['number']}: {title}")
        return result

    def add_reviewers_to_pr(
        self, pr_number: int, reviewer_teams: List[str] = None
    ) -> None:
        """Add team reviewers to a pull request"""
        if not reviewer_teams:
            reviewer_teams = self.config.reviewer_teams

        if not reviewer_teams:
            return

        data = {"team_reviewers": reviewer_teams}

        try:
            self._make_request(
                "POST",
                f"repos/{self.config.repo_owner}/{self.config.repo_name}/pulls/{pr_number}/requested_reviewers",
                json=data,
            )
            logger.info(f"Added team reviewers {reviewer_teams} to PR #{pr_number}")
        except GitHubIntegrationError as e:
            logger.warning(f"Failed to add reviewers to PR #{pr_number}: {e}")


class GitHubMonitor:
    """Main monitor class that processes PR requests"""

    def __init__(self, snowflake_config: SnowflakeConfig, github_config: GitHubConfig):
        self.snowflake_config = snowflake_config
        self.github_config = github_config
        self.processor_id = f"github-monitor-{os.getpid()}-{int(time.time())}"

        self.snowflake = SnowflakeConnector(snowflake_config)
        self.github = GitHubClient(github_config)

    def run_once(self) -> Dict[str, Any]:
        """Process one batch of pending requests"""
        stats = {"processed": 0, "succeeded": 0, "failed": 0, "errors": []}

        try:
            # Connect to Snowflake
            self.snowflake.connect()

            # Process requests until no more pending
            while True:
                request = self.snowflake.get_next_pending_request(self.processor_id)

                if not request:
                    logger.debug("No more pending requests")
                    break

                stats["processed"] += 1
                logger.info(
                    f"Processing request {request.request_id}: {request.pr_title}"
                )

                try:
                    self._process_request(request)
                    stats["succeeded"] += 1
                    logger.info(f"Successfully processed request {request.request_id}")

                except Exception as e:
                    stats["failed"] += 1
                    error_msg = f"Failed to process request {request.request_id}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

                    # Update request status to failed
                    try:
                        self.snowflake.update_request_status(
                            request.request_id,
                            "FAILED",
                            error_message=str(e),
                            processor_id=self.processor_id,
                        )
                    except Exception as update_error:
                        logger.error(f"Failed to update request status: {update_error}")

        except Exception as e:
            error_msg = f"Monitor execution failed: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

        finally:
            # Ensure Snowflake connection is closed
            try:
                self.snowflake.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from Snowflake: {e}")

        return stats

    def _process_request(self, request: PRRequest) -> None:
        """Process a single PR request"""
        try:
            # Validate branch name
            if self.github.branch_exists(request.branch_name):
                raise GitHubIntegrationError(
                    f"Branch {request.branch_name} already exists"
                )

            # Create the branch
            branch_result = self.github.create_branch(
                request.branch_name, request.target_branch
            )
            branch_url = f"https://github.com/{self.github_config.repo_owner}/{self.github_config.repo_name}/tree/{request.branch_name}"

            # Create or update the file
            commit_message = f"Add {request.file_name} for SnowDDL configuration\n\nCreated by: {request.created_by}\nRequest ID: {request.request_id}"

            self.github.create_or_update_file(
                request.branch_name,
                request.file_name,
                request.file_content,
                commit_message,
            )

            # Create the pull request
            pr_description = self._build_pr_description(request)
            pr_result = self.github.create_pull_request(
                request.branch_name,
                request.pr_title,
                pr_description,
                request.target_branch,
            )

            # Add reviewers if configured
            if self.github_config.reviewer_teams:
                self.github.add_reviewers_to_pr(
                    pr_result["number"], self.github_config.reviewer_teams
                )

            # Update request status to completed
            self.snowflake.update_request_status(
                request.request_id,
                "COMPLETED",
                github_branch_url=branch_url,
                github_pr_url=pr_result["html_url"],
                github_pr_number=pr_result["number"],
                processor_id=self.processor_id,
            )

        except Exception as e:
            logger.error(f"Error processing request {request.request_id}: {e}")
            raise

    def _build_pr_description(self, request: PRRequest) -> str:
        """Build the pull request description"""
        description = request.pr_description or "Automated SnowDDL configuration update"

        description += f"""

---
**Automated PR Details:**
- Created by: {request.created_by}
- Request ID: `{request.request_id}`
- Priority: {request.priority}
- Created: {request.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
- File: `{request.file_name}`

This PR was automatically created by the SnowDDL GitHub integration system.
"""
        return description

    def run_continuous(self, interval_seconds: int = 300) -> None:
        """Run the monitor continuously"""
        logger.info(f"Starting continuous monitoring with {interval_seconds}s interval")

        while True:
            try:
                stats = self.run_once()

                if stats["processed"] > 0:
                    logger.info(
                        f"Batch completed: {stats['succeeded']} succeeded, {stats['failed']} failed"
                    )
                else:
                    logger.debug("No requests processed this cycle")

                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in continuous run: {e}")
                logger.error(traceback.format_exc())
                time.sleep(interval_seconds)


def load_config() -> tuple[SnowflakeConfig, GitHubConfig]:
    """Load configuration from environment variables"""

    # Snowflake configuration
    snowflake_config = SnowflakeConfig(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        private_key_path=os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"),
        private_key_passphrase=os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"),
        role=os.getenv("SNOWFLAKE_ROLE", "SNOWDDL_CONFIG_MANAGER"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "SNOWDDL_CONFIG"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    )

    # GitHub configuration
    reviewer_teams_str = os.getenv("GITHUB_REVIEWER_TEAMS", "[]")
    try:
        reviewer_teams = json.loads(reviewer_teams_str)
    except json.JSONDecodeError:
        reviewer_teams = []

    github_config = GitHubConfig(
        token=os.getenv("GITHUB_TOKEN"),
        repo_owner=os.getenv("GITHUB_REPO_OWNER"),
        repo_name=os.getenv("GITHUB_REPO_NAME"),
        api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
        base_branch=os.getenv("GITHUB_BASE_BRANCH", "main"),
        auto_merge=os.getenv("GITHUB_AUTO_MERGE", "false").lower() == "true",
        reviewer_teams=reviewer_teams,
        max_files_per_pr=int(os.getenv("GITHUB_MAX_FILES_PER_PR", "10")),
    )

    # Validate required configuration
    required_snowflake = ["account", "user"]
    for field in required_snowflake:
        if not getattr(snowflake_config, field):
            raise ValueError(f"Missing required Snowflake configuration: {field}")

    if not (snowflake_config.password or snowflake_config.private_key_path):
        raise ValueError(
            "Either SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH must be provided"
        )

    required_github = ["token", "repo_owner", "repo_name"]
    for field in required_github:
        if not getattr(github_config, field):
            raise ValueError(f"Missing required GitHub configuration: {field}")

    return snowflake_config, github_config


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GitHub PR Monitor for SnowDDL")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval between runs in seconds (default: 300)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load configuration
        snowflake_config, github_config = load_config()

        # Create and run monitor
        monitor = GitHubMonitor(snowflake_config, github_config)

        if args.once:
            stats = monitor.run_once()
            print(
                f"Processed: {stats['processed']}, Succeeded: {stats['succeeded']}, Failed: {stats['failed']}"
            )
            if stats["errors"]:
                print("Errors:")
                for error in stats["errors"]:
                    print(f"  - {error}")
        else:
            monitor.run_continuous(args.interval)

    except Exception as e:
        logger.error(f"Failed to start monitor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
