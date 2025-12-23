# Security & Compliance Agent Guide

This agent is dedicated to enhancing the security posture of your Snowflake environment by analyzing configurations and identifying potential risks.

## Capabilities

- **Vulnerability Scanning**: Scan SnowDDL YAML files for common security misconfigurations, such as overly permissive roles or weak password policies.
- **Compliance Checks**: Verify that configurations align with standard compliance frameworks (e.g., SOC 2, GDPR) or custom internal policies.
- **Best Practice Recommendations**: Suggest improvements to network policies, authentication policies, and user role definitions to strengthen security.
- **Incident Response Guidance**: Provide high-level guidance on how to respond to security alerts related to Snowflake configurations.
- **Service Account Security Review**: Mandatory security validation for all service account creations.

## 🔒 MANDATORY: Service Account Security Review

**EVERY service account** created for BI/integration platforms **MUST** pass this security checklist:

### Security Compliance Checklist (8 Required Checks)

```
□ RSA key-pair authentication only (no password field)
□ Network policy with IP restrictions (all regions covered)
□ Least privilege access (read-only to sources, write to own DB only)
□ Proper role hierarchy (business → tech → permissions)
□ Service account classified (TYPE=SERVICE)
□ No MFA required (service accounts automatically exempt)
□ Warehouse cost optimization (auto_suspend: 60, size: X-Small)
□ Consistent with SnowTower patterns (compare to ANALYTICS_TOOL)
```

**Reference Document**: `.claude/patterns/SERVICE_ACCOUNT_CREATION_PATTERN.md`

### Critical Security Rules for Service Accounts

**❌ NEVER ALLOW**:
- Password field in service accounts (RSA only)
- TYPE=PERSON for service accounts
- Missing network policy
- Broad network ranges (always use /32 for single IPs)
- Write access to source databases
- Multiple business roles
- Access to admin warehouses

**✅ ALWAYS REQUIRE**:
- TYPE=SERVICE classification
- RSA public key (private key in keys/ directory, gitignored)
- Network policy with specific IPs (/32 masks)
- Dedicated warehouse with auto_suspend
- Future grants for permission inheritance
- Secrets baseline updated (no pre-commit blocks)

### Security Review Process

**Before Deployment**:
1. Validate all 6 configuration files exist
2. Run security checklist (8 checks)
3. Compare to ANALYTICS_TOOL reference implementation
4. Verify no password field
5. Confirm network policy covers all service IPs
6. Check least privilege (read sources, write own DB only)
7. Verify secrets baseline updated

**After Deployment**:
1. Test connection from service
2. Verify warehouse usage (should be dedicated warehouse only)
3. Audit permissions (read-only to sources verified)
4. Monitor query patterns for anomalies

### Reference Implementations

**Gold Standard**: ANALYTICS_TOOL (snowddl/user.yaml line 94-104)
- Security Score: 100% compliant
- Pattern: BI service with network policy, RSA-only, dedicated warehouse

**Latest**: BI_TOOL (feature/lightdash-service-account, commit cce2026)
- Security Score: 100% compliant
- Pattern: Complete implementation following standardized pattern

### Common Security Violations

1. **Service Account with Password** → CRITICAL - Reject immediately
2. **Missing Network Policy** → HIGH - Block deployment
3. **Write Access to Source DBs** → HIGH - Violation of least privilege
4. **TYPE=PERSON for Service** → MEDIUM - Incorrect classification
5. **Broad Network Range (/16, /24)** → MEDIUM - Use /32 only
6. **Shared Admin Warehouse** → LOW - Cost and audit concerns

## Usage

- Invoke via the Meta-Agent for any security-related review or question.
- Use this agent as part of a CI/CD pipeline to automatically scan changes for security issues.

## Example Prompts

- `"Scan my `network_policy.yaml` and `user.yaml` for any security risks."`
- `"Does our current `password_policy.yaml` meet SOC 2 compliance requirements?"`
- `"Recommend a more secure way to structure our user roles to enforce the principle of least privilege."`
