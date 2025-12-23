"""
User Authentication Health Check Module

Evaluates Snowflake user authentication compliance against 2025-2026 requirements.
Provides health scores, compliance status, and actionable recommendations.

Snowflake MFA Rollout Timeline:
- Sep 2025 - Jan 2026: MFA required for Snowsight
- Feb 2026 - Apr 2026: MFA for all new users
- May 2026 - Jul 2026: MFA for all existing users
- Jun 2026 - Aug 2026: No passwords for service accounts

Compliant Authentication Methods:
- PERSON users: RSA key (preferred) OR Password + MFA
- SERVICE users: RSA key only (no password)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


class HealthStatus(Enum):
    """Health status levels"""

    COMPLIANT = "compliant"  # 🟢 Ready for 2026
    WARNING = "warning"  # 🟡 Action needed
    CRITICAL = "critical"  # 🔴 Non-compliant


class AuthMethod(Enum):
    """Available authentication methods"""

    RSA_KEY = "rsa_key"
    PASSWORD = "password"
    MFA = "mfa"


@dataclass
class HealthCheckResult:
    """Individual user health check result"""

    username: str
    user_type: str
    health_score: int  # 0-100
    status: HealthStatus
    auth_methods: List[AuthMethod]
    issues: List[str]
    recommendations: List[str]
    last_login: Optional[datetime]
    disabled: bool

    @property
    def status_emoji(self) -> str:
        """Get emoji for status"""
        return {
            HealthStatus.COMPLIANT: "🟢",
            HealthStatus.WARNING: "🟡",
            HealthStatus.CRITICAL: "🔴",
        }[self.status]

    @property
    def status_text(self) -> str:
        """Get text description of status"""
        return {
            HealthStatus.COMPLIANT: "Compliant",
            HealthStatus.WARNING: "Action Required",
            HealthStatus.CRITICAL: "Non-Compliant",
        }[self.status]

    @property
    def auth_icons(self) -> str:
        """Get icons representing auth methods"""
        icons = []
        if AuthMethod.RSA_KEY in self.auth_methods:
            icons.append("🔑")
        if AuthMethod.PASSWORD in self.auth_methods:
            icons.append("🔒")
        if AuthMethod.MFA in self.auth_methods:
            icons.append("🛡️")
        return " ".join(icons) if icons else "❌"


@dataclass
class ComplianceSummary:
    """Account-wide compliance summary"""

    total_users: int
    compliant_count: int
    warning_count: int
    critical_count: int
    person_users: int
    service_users: int
    legacy_service_users: int
    average_score: float
    ready_for_2026: bool

    @property
    def compliance_percentage(self) -> float:
        """Percentage of compliant users"""
        return (
            (self.compliant_count / self.total_users * 100)
            if self.total_users > 0
            else 0
        )


class UserHealthChecker:
    """Evaluates user authentication health and compliance"""

    # Timeline milestones for compliance checks
    MILESTONES = {
        "snowsight_mfa": datetime(2026, 1, 31),  # Jan 2026
        "new_users_mfa": datetime(2026, 4, 30),  # Apr 2026
        "all_users_mfa": datetime(2026, 7, 31),  # Jul 2026
        "no_service_passwords": datetime(2026, 8, 31),  # Aug 2026
    }

    def check_user(self, user_data: Dict[str, Any]) -> HealthCheckResult:
        """
        Evaluate a single user's authentication health.

        Args:
            user_data: Dictionary from SHOW USERS command with fields:
                - name, type, has_password, has_rsa_public_key, has_mfa,
                - disabled, last_success_login

        Returns:
            HealthCheckResult with score, status, and recommendations
        """
        username = user_data["name"]
        user_type = user_data["type"]
        has_password = user_data.get("has_password", "false").lower() == "true"
        has_rsa = user_data.get("has_rsa_public_key", "false").lower() == "true"
        has_mfa = user_data.get("has_mfa", "false").lower() == "true"
        disabled = user_data.get("disabled", "false").lower() == "true"
        last_login_str = user_data.get("last_success_login")

        # Parse last login
        last_login = None
        if last_login_str:
            if isinstance(last_login_str, datetime):
                # Already a datetime object
                last_login = last_login_str
            elif last_login_str != "null":
                try:
                    # Handle various datetime formats
                    last_login = datetime.fromisoformat(
                        last_login_str.replace("Z", "+00:00")
                    )
                except:
                    try:
                        # Try alternate format without timezone
                        from dateutil import parser

                        last_login = parser.parse(last_login_str)
                    except:
                        pass

        # Determine auth methods
        auth_methods = []
        if has_rsa:
            auth_methods.append(AuthMethod.RSA_KEY)
        if has_password:
            auth_methods.append(AuthMethod.PASSWORD)
        if has_mfa:
            auth_methods.append(AuthMethod.MFA)

        # Calculate health score and identify issues
        score = 100
        issues = []
        recommendations = []

        if disabled:
            score = 0
            issues.append("Account is disabled")
            recommendations.append("Enable account or remove if no longer needed")
        elif user_type == "PERSON":
            score, person_issues, person_recs = self._check_person_user(
                has_password, has_rsa, has_mfa
            )
            issues.extend(person_issues)
            recommendations.extend(person_recs)
        elif user_type == "SERVICE":
            score, service_issues, service_recs = self._check_service_user(
                has_password, has_rsa
            )
            issues.extend(service_issues)
            recommendations.extend(service_recs)
        elif user_type == "LEGACY_SERVICE":
            score = 30
            issues.append("Using deprecated LEGACY_SERVICE type")
            issues.append("Must migrate to SERVICE type by June 2026")
            recommendations.append("Convert to SERVICE type immediately")
            if has_password:
                score -= 10
                issues.append(
                    "Service account has password (not allowed after Aug 2026)"
                )
                recommendations.append("Remove password authentication")
        else:
            score = 50
            issues.append(f"Unknown user type: {user_type}")

        # Check for never logged in
        if not last_login and user_type == "PERSON" and not disabled:
            score = max(0, score - 10)
            issues.append("User has never logged in")
            recommendations.append("Verify user has access and test login")

        # Determine status based on score
        if score >= 85:
            status = HealthStatus.COMPLIANT
        elif score >= 50:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.CRITICAL

        return HealthCheckResult(
            username=username,
            user_type=user_type,
            health_score=max(0, score),
            status=status,
            auth_methods=auth_methods,
            issues=issues,
            recommendations=recommendations,
            last_login=last_login,
            disabled=disabled,
        )

    def _check_person_user(
        self, has_password: bool, has_rsa: bool, has_mfa: bool
    ) -> tuple[int, List[str], List[str]]:
        """Check PERSON user compliance"""
        issues = []
        recommendations = []

        # Best: RSA + MFA + Password (triple auth for lockout prevention)
        if has_rsa and has_mfa and has_password:
            return 100, issues, recommendations

        # Excellent: RSA only (passwordless, bypasses MFA requirement)
        if has_rsa and not has_password:
            return 95, issues, recommendations

        # Good: RSA + Password (dual auth, MFA recommended but not required with RSA)
        if has_rsa and has_password and not has_mfa:
            return 95, issues, ["Consider enabling MFA as additional security layer"]

        # Good: Password + MFA (compliant but RSA recommended)
        if has_password and has_mfa and not has_rsa:
            score = 85
            recommendations.append(
                "Consider adding RSA key for passwordless authentication"
            )
            return score, issues, recommendations

        # Warning: Password only, no MFA (non-compliant after May 2026)
        if has_password and not has_mfa and not has_rsa:
            score = 40
            issues.append("MFA required by May 2026")
            issues.append("Password-only authentication will be blocked")
            recommendations.append("Enable MFA immediately")
            recommendations.append(
                "Add RSA key for passwordless authentication (preferred)"
            )
            return score, issues, recommendations

        # Warning: RSA only but previously had password
        if has_rsa and not has_password and not has_mfa:
            return 95, issues, recommendations

        # Critical: No authentication method
        score = 0
        issues.append("No authentication method configured")
        recommendations.append("Configure RSA key or password + MFA")
        return score, issues, recommendations

    def _check_service_user(
        self, has_password: bool, has_rsa: bool
    ) -> tuple[int, List[str], List[str]]:
        """Check SERVICE user compliance"""
        issues = []
        recommendations = []

        # Perfect: RSA only, no password
        if has_rsa and not has_password:
            return 100, issues, recommendations

        # Warning: Has password (not allowed after June 2026)
        if has_password:
            score = 50
            issues.append("Service accounts cannot use passwords after August 2026")
            recommendations.append("Remove password authentication")
            if not has_rsa:
                score = 30
                issues.append("No RSA key configured")
                recommendations.append("Add RSA key before removing password")
            return score, issues, recommendations

        # Critical: No authentication method
        if not has_rsa and not has_password:
            score = 0
            issues.append("No authentication method configured")
            recommendations.append("Configure RSA key immediately")
            return score, issues, recommendations

        # RSA only
        return 100, issues, recommendations

    def check_all_users(
        self, users_data: List[Dict[str, Any]]
    ) -> tuple[List[HealthCheckResult], ComplianceSummary]:
        """
        Check health for all users and generate summary.

        Args:
            users_data: List of user dictionaries from SHOW USERS

        Returns:
            Tuple of (individual results, compliance summary)
        """
        results = [self.check_user(user) for user in users_data]

        compliant = [r for r in results if r.status == HealthStatus.COMPLIANT]
        warning = [r for r in results if r.status == HealthStatus.WARNING]
        critical = [r for r in results if r.status == HealthStatus.CRITICAL]

        person_users = [r for r in results if r.user_type == "PERSON"]
        service_users = [r for r in results if r.user_type == "SERVICE"]
        legacy_service = [r for r in results if r.user_type == "LEGACY_SERVICE"]

        avg_score = (
            sum(r.health_score for r in results) / len(results) if results else 0
        )
        ready_for_2026 = len(warning) == 0 and len(critical) == 0

        summary = ComplianceSummary(
            total_users=len(results),
            compliant_count=len(compliant),
            warning_count=len(warning),
            critical_count=len(critical),
            person_users=len(person_users),
            service_users=len(service_users),
            legacy_service_users=len(legacy_service),
            average_score=avg_score,
            ready_for_2026=ready_for_2026,
        )

        return results, summary

    def print_summary(self, summary: ComplianceSummary):
        """Print compliance summary to console"""
        status_emoji = "✅" if summary.ready_for_2026 else "⚠️"

        console.print(
            Panel(
                f"[bold]AUTHENTICATION HEALTH DASHBOARD[/bold]\n\n"
                f"Overall Compliance: [bold]{summary.compliance_percentage:.1f}%[/bold] "
                f"({summary.compliant_count}/{summary.total_users} users)\n"
                f"2026 Ready: {status_emoji} {'Yes' if summary.ready_for_2026 else 'No'}",
                border_style="blue",
                box=box.ROUNDED,
            )
        )

        # Breakdown table
        table = Table(title="Compliance Breakdown", box=box.SIMPLE)
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")

        table.add_row(
            "🟢 Fully Compliant",
            str(summary.compliant_count),
            f"{summary.compliant_count/summary.total_users*100:.1f}%",
        )
        table.add_row(
            "🟡 Action Required",
            str(summary.warning_count),
            f"{summary.warning_count/summary.total_users*100:.1f}%",
        )
        table.add_row(
            "🔴 Non-Compliant",
            str(summary.critical_count),
            f"{summary.critical_count/summary.total_users*100:.1f}%",
        )

        console.print(table)

    def print_user_table(self, results: List[HealthCheckResult], show_all: bool = True):
        """Print user health check results as table"""
        table = Table(title="User Authentication Health", box=box.ROUNDED)
        table.add_column("User", style="cyan")
        table.add_column("Type")
        table.add_column("Auth", justify="center")
        table.add_column("Score", justify="right")
        table.add_column("Status")

        # Filter if needed
        if not show_all:
            results = [r for r in results if r.status != HealthStatus.COMPLIANT]

        # Sort by score (worst first)
        results = sorted(results, key=lambda r: r.health_score)

        for result in results:
            score_color = (
                "green"
                if result.health_score >= 85
                else "yellow"
                if result.health_score >= 50
                else "red"
            )

            table.add_row(
                result.username,
                result.user_type,
                result.auth_icons,
                f"[{score_color}]{result.health_score}[/{score_color}]",
                f"{result.status_emoji} {result.status_text}",
            )

        console.print(table)
        console.print("\n[dim]Legend: 🔑 RSA Key | 🔒 Password | 🛡️ MFA[/dim]")

    def print_recommendations(self, results: List[HealthCheckResult]):
        """Print actionable recommendations"""
        # Filter to only users with recommendations
        with_recs = [r for r in results if r.recommendations]

        if not with_recs:
            console.print(
                "\n✅ [green]No actions required - all users compliant![/green]"
            )
            return

        console.print("\n[bold yellow]Recommended Actions:[/bold yellow]\n")

        for i, result in enumerate(with_recs, 1):
            console.print(
                f"[bold cyan]{i}. {result.username}[/bold cyan] ({result.user_type})"
            )
            for rec in result.recommendations:
                console.print(f"   • {rec}")
            if result.issues:
                console.print(f"   [dim]Issues: {', '.join(result.issues)}[/dim]")
            console.print()
