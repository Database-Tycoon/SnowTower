"""
GitHub PR Creator for SnowDDL Deployments

Automates the creation of pull requests with generated user configurations.
Handles branch creation, file commits, and PR submission via gh CLI.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from rich.console import Console

console = Console()


class PRCreationError(Exception):
    """Raised when PR creation fails"""

    pass


@dataclass
class PRResult:
    """Result of PR creation"""

    pr_number: int
    pr_url: str
    branch_name: str
    commit_sha: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "branch_name": self.branch_name,
            "commit_sha": self.commit_sha,
        }


class GitHubPRCreator:
    """
    Creates pull requests for SnowDDL user configurations.

    Uses gh CLI for all GitHub operations including branch creation,
    commits, and PR submission with proper metadata.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize PR creator.

        Args:
            repo_path: Path to git repository (defaults to current directory)
        """
        self.repo_path = repo_path or Path.cwd()
        self._verify_gh_cli()
        self._verify_git_repo()

    def _verify_gh_cli(self) -> None:
        """Verify gh CLI is installed and authenticated"""
        try:
            subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError:
            raise PRCreationError("gh CLI not authenticated. Run: gh auth login")
        except FileNotFoundError:
            raise PRCreationError(
                "gh CLI not found. Install from: https://cli.github.com/"
            )

    def _verify_git_repo(self) -> None:
        """Verify we're in a git repository"""
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError:
            raise PRCreationError(f"{self.repo_path} is not a git repository")

    def create_user_deployment_pr(
        self,
        username: str,
        yaml_config: Dict[str, Any],
        issue_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        base_branch: str = "main",
    ) -> PRResult:
        """
        Create a pull request for user deployment.

        Args:
            username: Username being deployed
            yaml_config: YAML configuration dictionary
            issue_number: GitHub issue number that triggered this
            metadata: Additional metadata for PR description
            base_branch: Base branch for PR (default: main)

        Returns:
            PRResult with PR details

        Raises:
            PRCreationError: If PR creation fails
        """
        branch_name = (
            f"user/{username.lower()}/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        try:
            # 1. Create and checkout new branch
            console.print(f"[cyan]Creating branch: {branch_name}[/cyan]")
            self._create_branch(branch_name, base_branch)

            # 2. Update user.yaml file
            console.print(
                f"[cyan]Updating user.yaml with {username} configuration[/cyan]"
            )
            self._update_user_yaml(yaml_config)

            # 3. Commit changes
            console.print("[cyan]Committing changes[/cyan]")
            commit_message = self._generate_commit_message(username, issue_number)
            commit_sha = self._commit_changes(commit_message)

            # 4. Push branch
            console.print(f"[cyan]Pushing branch to remote[/cyan]")
            self._push_branch(branch_name)

            # 5. Create pull request
            console.print("[cyan]Creating pull request[/cyan]")
            pr_title = f"Add user: {username}"
            pr_body = self._generate_pr_body(
                username, yaml_config, issue_number, metadata
            )

            pr_result = self._create_pr(
                branch_name=branch_name,
                base_branch=base_branch,
                title=pr_title,
                body=pr_body,
                issue_number=issue_number,
            )

            pr_result.commit_sha = commit_sha

            console.print(f"[green]✓ Pull request created successfully![/green]")
            console.print(
                f"[green]  PR #{pr_result.pr_number}: {pr_result.pr_url}[/green]"
            )

            return pr_result

        except Exception as e:
            # Attempt cleanup on failure
            try:
                self._cleanup_branch(branch_name, base_branch)
            except Exception:
                pass  # Best effort cleanup

            raise PRCreationError(f"Failed to create PR: {e}")

    def _create_branch(self, branch_name: str, base_branch: str) -> None:
        """Create and checkout a new branch"""
        try:
            # Ensure we're on the base branch and up to date
            subprocess.run(
                ["git", "checkout", base_branch],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            subprocess.run(
                ["git", "pull", "origin", base_branch],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            # Create new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

        except subprocess.CalledProcessError as e:
            raise PRCreationError(f"Failed to create branch {branch_name}: {e.stderr}")

    def _update_user_yaml(self, yaml_config: Dict[str, Any]) -> None:
        """Update user.yaml file with new configuration"""
        import yaml
        from user_management.yaml_handler import YAMLHandler

        try:
            # Use YAMLHandler for safe updates
            yaml_handler = YAMLHandler(self.repo_path / "snowddl")

            # Merge the new user configuration
            for username, user_data in yaml_config.items():
                yaml_handler.merge_user(username, user_data, backup=False)

        except Exception as e:
            raise PRCreationError(f"Failed to update user.yaml: {e}")

    def _commit_changes(self, message: str) -> str:
        """Commit staged changes and return commit SHA"""
        try:
            # Stage changes
            subprocess.run(
                ["git", "add", "snowddl/user.yaml"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            # Commit
            subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            # Get commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            raise PRCreationError(f"Failed to commit changes: {e.stderr}")

    def _push_branch(self, branch_name: str) -> None:
        """Push branch to remote"""
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise PRCreationError(f"Failed to push branch {branch_name}: {e.stderr}")

    def _create_pr(
        self,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
        issue_number: Optional[int] = None,
    ) -> PRResult:
        """Create pull request using gh CLI"""
        try:
            cmd = [
                "gh",
                "pr",
                "create",
                "--base",
                base_branch,
                "--head",
                branch_name,
                "--title",
                title,
                "--body",
                body,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, cwd=self.repo_path
            )

            pr_url = result.stdout.strip()

            # Extract PR number from URL
            pr_number = int(pr_url.split("/")[-1])

            # If this is related to an issue, link them
            if issue_number:
                try:
                    self._link_issue_to_pr(pr_number, issue_number)
                except Exception as e:
                    console.print(
                        f"[yellow]⚠ Could not link to issue #{issue_number}: {e}[/yellow]"
                    )

            return PRResult(pr_number=pr_number, pr_url=pr_url, branch_name=branch_name)

        except subprocess.CalledProcessError as e:
            raise PRCreationError(f"Failed to create PR: {e.stderr}")

    def _link_issue_to_pr(self, pr_number: int, issue_number: int) -> None:
        """Link issue to PR by adding a comment"""
        try:
            comment = f"Automated user deployment PR created for this access request.\n\nCloses #{issue_number}"

            subprocess.run(
                ["gh", "pr", "comment", str(pr_number), "--body", comment],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise PRCreationError(f"Failed to link issue to PR: {e.stderr}")

    def _cleanup_branch(self, branch_name: str, base_branch: str) -> None:
        """Clean up branch on failure"""
        try:
            # Switch back to base branch
            subprocess.run(
                ["git", "checkout", base_branch],
                capture_output=True,
                text=True,
                check=False,
                cwd=self.repo_path,
            )

            # Delete local branch
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                capture_output=True,
                text=True,
                check=False,
                cwd=self.repo_path,
            )

        except Exception:
            pass  # Best effort cleanup

    def _generate_commit_message(
        self, username: str, issue_number: Optional[int] = None
    ) -> str:
        """Generate commit message"""
        message = f"Add user configuration for {username}\n\n"

        if issue_number:
            message += f"Automated deployment from GitHub issue #{issue_number}\n"

        message += "Generated by SnowTower automation system"

        return message

    def _generate_pr_body(
        self,
        username: str,
        yaml_config: Dict[str, Any],
        issue_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate PR description body"""
        user_data = yaml_config.get(username, {})
        metadata = metadata or {}

        body = f"## User Deployment: {username}\n\n"

        # Summary section
        body += "### Summary\n"
        body += f"Automated deployment of user configuration for **{username}**\n\n"

        if issue_number:
            body += f"**Related Issue:** #{issue_number}\n\n"

        # User details
        body += "### User Details\n"
        body += f"- **Name:** {user_data.get('display_name', 'N/A')}\n"
        body += f"- **Email:** {user_data.get('email', 'N/A')}\n"
        body += f"- **Type:** {user_data.get('type', 'N/A')}\n"
        body += f"- **Roles:** {', '.join(user_data.get('business_roles', []))}\n"
        body += f"- **Warehouse:** {user_data.get('default_warehouse', 'N/A')}\n\n"

        # Authentication
        body += "### Authentication\n"
        auth_methods = []
        if user_data.get("password"):
            auth_methods.append("Password (encrypted)")
        if user_data.get("rsa_public_key"):
            auth_methods.append("RSA Key Pair")
        body += (
            f"- {', '.join(auth_methods) if auth_methods else 'None configured'}\n\n"
        )

        # Business justification
        if metadata.get("business_justification"):
            body += "### Business Justification\n"
            body += f"{metadata['business_justification']}\n\n"

        # Project/Team
        if metadata.get("project_team"):
            body += f"**Project/Team:** {metadata['project_team']}\n\n"

        # Deployment checklist
        body += "### Deployment Checklist\n"
        body += "- [ ] Review user configuration\n"
        body += "- [ ] Verify role assignments are appropriate\n"
        body += "- [ ] Confirm business justification\n"
        body += "- [ ] Run `uv run snowddl-plan` to preview changes\n"
        body += "- [ ] Merge PR to deploy to Snowflake\n"
        body += "- [ ] Deliver credentials to user securely\n"
        body += "- [ ] Verify user can authenticate\n\n"

        # Metadata
        body += "---\n"
        body += f"🤖 Generated by SnowTower Automation on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        return body
