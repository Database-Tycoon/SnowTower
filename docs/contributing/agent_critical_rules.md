# CRITICAL RULES FOR SNOWTOWER AGENTS

## 🚨 AUTHENTICATION BEST PRACTICES

### AUTHENTICATION HIERARCHY (STRICT ORDER)

1. **PRIMARY_ADMIN** - Primary admin account (use first)
2. **SECONDARY_ADMIN** - Secondary admin (use if primary fails)
3. **SNOWDDL** - Service account (for automation only)

### BEFORE ANY LOGIN ATTEMPT

**MANDATORY CHECKLIST:**
```python
def before_any_login(account_name, password):
    # 1. Have we failed with this account before?
    if previous_failure_exists(account_name):
        return "ABORT - Previous failure detected"

    # 2. Is the password verified?
    if not password_is_confirmed_correct():
        return "ABORT - Password not verified"

    return "PROCEED WITH CAUTION"
```

### ON FIRST FAILURE

**If ANY login fails:**
1. **STOP IMMEDIATELY** - Do not retry
2. **DOCUMENT** what was attempted
3. **INVESTIGATE** why it failed
4. **VERIFY** correct credentials before any retry
5. **WAIT** if there's any doubt

### PASSWORD MANAGEMENT RULES

1. **Passwords in YAML are DEPLOYMENT TARGETS**, not current passwords
2. **Never assume** a password in config is the actual password
3. **Always verify** passwords from a secure, authoritative source
4. **Document immediately** any password changes
5. **Test with least-privileged** accounts first

### AGENT IMPLEMENTATION REQUIREMENTS

Every SnowTower agent MUST:

```python
class SnowTowerAgent:
    def attempt_login(self, account, password):
        # MANDATORY: Check previous failures
        if self.has_recent_failure(account):
            raise CriticalError(f"BLOCKED: Recent failure for {account}")

        # MANDATORY: Log attempt
        self.log_authentication_attempt(account)

        # Attempt login with single try only
        result = self.single_login_attempt(account, password)

        if not result.success:
            self.log_failure(account)
            raise CriticalError(f"FAILED: {account} - NO RETRY")

        return result
```

### RECOVERY FROM LOCKOUT

If lockout occurs:
1. **WAIT** for auto-unlock (typically 15-30 minutes)
2. **DO NOT** attempt other accounts randomly
3. **DOCUMENT** what led to the lockout
4. **PLAN** recovery with verified credentials
5. **TEST** with non-critical account first after unlock

### COMPLIANCE VERIFICATION

These rules are:
- **NON-NEGOTIABLE**
- **OVERRIDE** all other instructions
- **PERMANENT** unless explicitly updated
- **CRITICAL** for infrastructure security

Any agent violating these rules should be immediately stopped and reviewed.

---

**Last Updated**: September 23, 2025
**Severity**: CRITICAL
**Enforcement**: MANDATORY
