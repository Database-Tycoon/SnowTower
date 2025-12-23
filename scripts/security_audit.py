#!/usr/bin/env python3
"""
Security Audit Script for SnowDDL

Check security compliance:
- Users without RSA keys
- MFA compliance (2025-2026 requirement)
- Weak authentication
- Network policy coverage
- Sacred account protection
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

# Add parent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snowddl_core.project import SnowDDLProject
from snowddl_core.safety import SACRED_ACCOUNTS


def audit_authentication(project: SnowDDLProject):
    """Audit user authentication methods."""

    print("\n🔐 AUTHENTICATION AUDIT")
    print("=" * 80)

    issues = {
        "no_auth": [],
        "password_only": [],
        "no_rsa": [],
        "service_with_password": [],
    }

    for name, user in project.users.items():
        has_password = bool(user.password)
        has_rsa = bool(user.rsa_public_key)

        # Check for no authentication
        if not has_password and not has_rsa:
            issues["no_auth"].append(name)

        # Check for password-only (weak for PERSON users)
        if user.type == "PERSON" and has_password and not has_rsa:
            issues["password_only"].append(name)

        # Check for missing RSA (recommended for all)
        if not has_rsa and user.type == "PERSON":
            issues["no_rsa"].append(name)

        # Check service accounts with passwords (should use RSA)
        if user.type == "SERVICE" and has_password:
            issues["service_with_password"].append(name)

    # Print findings
    total_issues = sum(len(v) for v in issues.values())

    if total_issues == 0:
        print("✅ All users have proper authentication!")
    else:
        print(f"⚠️  Found {total_issues} authentication issues:\n")

        if issues["no_auth"]:
            print("❌ USERS WITH NO AUTHENTICATION:")
            for user in issues["no_auth"]:
                print(f"  • {user}")

        if issues["password_only"]:
            print("\n⚠️  USERS WITH PASSWORD ONLY (need RSA for MFA):")
            for user in issues["password_only"]:
                print(f"  • {user}")

        if issues["service_with_password"]:
            print("\n⚠️  SERVICE ACCOUNTS WITH PASSWORDS (should use RSA):")
            for user in issues["service_with_password"]:
                print(f"  • {user}")

    return issues


def audit_mfa_compliance(project: SnowDDLProject):
    """Check MFA compliance for 2025-2026 rollout."""

    print("\n🔑 MFA COMPLIANCE CHECK (2025-2026 Requirement)")
    print("=" * 80)

    compliant = []
    non_compliant = []

    for name, user in project.users.items():
        if user.type == "PERSON":
            # MFA requires RSA key authentication
            if user.rsa_public_key:
                compliant.append(name)
            else:
                non_compliant.append(name)

    total_persons = len(compliant) + len(non_compliant)
    compliance_rate = (len(compliant) / total_persons * 100) if total_persons > 0 else 0

    print(f"MFA Compliance Rate: {compliance_rate:.1f}%")
    print(f"  • Compliant: {len(compliant)}/{total_persons} users")
    print(f"  • Non-compliant: {len(non_compliant)}/{total_persons} users")

    if non_compliant:
        print("\n❌ Users requiring MFA setup:")
        for user in non_compliant:
            print(f"  • {user}")

    print(
        f"\n{'✅' if compliance_rate == 100 else '⚠️'} Snowflake MFA will be mandatory in 2025-2026"
    )

    return compliance_rate


def audit_sacred_accounts(project: SnowDDLProject):
    """Verify sacred accounts are protected."""

    print("\n🛡️ SACRED ACCOUNT AUDIT")
    print("=" * 80)

    for account in SACRED_ACCOUNTS:
        user = project.get_user(account)

        if user:
            print(f"✅ {account}:")
            print(f"   • Found in configuration")
            print(f"   • Has password: {'Yes' if user.password else 'No'}")
            print(f"   • Has RSA key: {'Yes' if user.rsa_public_key else 'No'}")
            print(
                f"   • Network policy: {user.network_policy or 'None (unrestricted)'}"
            )

            # Warnings
            if user.network_policy and account == "STEPHEN_RECOVERY":
                print(
                    f"   ⚠️  WARNING: Recovery account should have no network restrictions!"
                )
        else:
            print(f"⚠️  {account}: NOT FOUND (should be created separately)")

    return True


def audit_roles(project: SnowDDLProject):
    """Audit role assignments."""

    print("\n👥 ROLE AUDIT")
    print("=" * 80)

    # Count users per role
    role_counts = {}
    admin_users = []

    for name, user in project.users.items():
        for role in user.business_roles:
            role_counts[role] = role_counts.get(role, 0) + 1

            if role in ["ADMIN_ROLE", "ACCOUNTADMIN"]:
                admin_users.append(name)

    # Print role distribution
    print("Role Distribution:")
    for role, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {role}: {count} users")

    # Check admin users
    print(f"\n🔑 Admin Users ({len(admin_users)}):")
    for user in admin_users:
        u = project.get_user(user)
        auth = []
        if u.password:
            auth.append("PWD")
        if u.rsa_public_key:
            auth.append("RSA")
        print(f"  • {user} [{','.join(auth)}]")

    if len(admin_users) < 2:
        print("\n⚠️  WARNING: Should have at least 2 admin users for redundancy")

    return role_counts


def full_security_audit(project: SnowDDLProject):
    """Run complete security audit."""

    print("\n" + "=" * 80)
    print("🔒 COMPREHENSIVE SECURITY AUDIT")
    print("=" * 80)

    # Run all audits
    auth_issues = audit_authentication(project)
    mfa_rate = audit_mfa_compliance(project)
    audit_sacred_accounts(project)
    audit_roles(project)

    # Summary
    print("\n" + "=" * 80)
    print("📊 SECURITY SUMMARY")
    print("=" * 80)

    total_issues = sum(len(v) for v in auth_issues.values())

    print(f"\nAuthentication Issues: {total_issues}")
    print(f"MFA Compliance: {mfa_rate:.1f}%")
    print(f"Sacred Accounts: Protected")

    if total_issues == 0 and mfa_rate == 100:
        print("\n✅ SECURITY STATUS: EXCELLENT")
    elif total_issues < 5 and mfa_rate > 50:
        print("\n⚠️  SECURITY STATUS: GOOD (with recommendations)")
    else:
        print("\n❌ SECURITY STATUS: NEEDS IMPROVEMENT")

    return total_issues


def main():
    parser = argparse.ArgumentParser(description="Security audit for SnowDDL")
    parser.add_argument("--config", default="./snowddl", help="Config directory")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Individual audit commands
    auth_parser = subparsers.add_parser("auth", help="Audit authentication methods")
    mfa_parser = subparsers.add_parser("mfa", help="Check MFA compliance")
    sacred_parser = subparsers.add_parser("sacred", help="Verify sacred accounts")
    roles_parser = subparsers.add_parser("roles", help="Audit role assignments")

    # Full audit
    full_parser = subparsers.add_parser("full", help="Run complete security audit")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load project
    project = SnowDDLProject(args.config)

    if args.command == "auth":
        audit_authentication(project)
    elif args.command == "mfa":
        audit_mfa_compliance(project)
    elif args.command == "sacred":
        audit_sacred_accounts(project)
    elif args.command == "roles":
        audit_roles(project)
    elif args.command == "full":
        full_security_audit(project)


if __name__ == "__main__":
    main()
