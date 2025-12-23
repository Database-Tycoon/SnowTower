# Security Notice - RSA Keys

## Key Storage Best Practices

RSA private keys should NEVER be stored in the project directory, even if they are gitignored.

### Secure Key Locations

All RSA keys have been moved to secure locations:

- **Service Keys**: `~/.snowflake/keys/`
- **User Keys**: `~/.ssh/`

### Key Files Status

✅ **No keys are tracked in git** - Verified with `git ls-files`
✅ **All .p8 and .pub files are gitignored** - See lines 40-41 in .gitignore
✅ **Keys have been moved to secure locations** - No keys remain in project directory

### For Developers

1. **Never store keys in the project directory**
2. **Always use absolute paths to keys** in your .env file:
   ```
   SNOWFLAKE_PRIVATE_KEY_PATH=/Users/username/.snowflake/keys/snowddl_service_key.p8
   ```
3. **Set restrictive permissions** on private keys:
   ```bash
   chmod 400 ~/.snowflake/keys/*.p8
   ```

### Verification Commands

To verify no keys are exposed:
```bash
# Check for any key files in project
find . -name "*.p8" -o -name "*.pub" | grep -v ".venv"

# Verify gitignore is working
git check-ignore *.p8 *.pub

# Check if any keys are tracked
git ls-files | grep -E "\.(p8|pub)$"
```

All commands should return empty or confirm files are ignored.

---
Last Security Audit: September 28, 2025
Status: ✅ SECURE - No keys exposed
