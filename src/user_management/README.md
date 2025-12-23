# User Management Module (Consolidated)

This module provides comprehensive user lifecycle management for Snowflake accounts within the SnowTower infrastructure. All user management functionality has been consolidated into this unified system.

## Architecture

```
src/user_management/
├── cli.py                  # Comprehensive Click-based CLI (user-manage command)
├── manager.py              # Central UserManager orchestrator (all operations)
├── password_generator.py   # Secure password generation with encryption
├── encryption.py           # Fernet-based password encryption/decryption
├── rsa_keys.py            # RSA key pair generation and management
├── yaml_handler.py         # YAML configuration file manipulation
└── snowddl_account.py      # SnowDDL service account management
```

## Primary Commands

### 1. User Creation (Recommended)
```bash
# Interactive mode (easiest)
uv run user-create

# Non-interactive mode
uv run user-create -f John -l Doe -e john.doe@company.com

# With custom options
uv run user-create -f John -l Doe -e john@company.com -t PERSON --default-role ANALYST
```

### 2. Comprehensive Management
```bash
# Full interactive CLI
uv run user-manage

# Specific operations
uv run user-manage create                    # Create user
uv run user-manage list                      # List all users
uv run user-manage show USERNAME             # Show user details
uv run user-manage update USERNAME           # Update user
uv run user-manage delete USERNAME           # Delete user
uv run user-manage validate-all              # Validate all configs
```

### 3. Password Operations
```bash
# Generate password for user
uv run user-manage generate-password USERNAME

# Regenerate existing password
uv run user-manage regenerate-password USERNAME

# Bulk password generation
uv run user-manage bulk-generate-passwords --usernames "USER1,USER2,USER3"

# Encrypt a password
uv run user-manage encrypt-password
```

### 4. RSA Key Operations
```bash
# Generate RSA keys
uv run user-manage generate-keys USERNAME

# Rotate existing keys
uv run user-manage rotate-keys USERNAME

# List all keys
uv run user-manage list-keys
```

## Key Features

- **Unified Interface**: Single `user-create` command for all user creation needs
- **Secure Password Generation**: Automatic generation with configurable complexity
- **Automatic Encryption**: All passwords encrypted with Fernet before storage
- **RSA Key Management**: Generate, rotate, and manage RSA key pairs
- **Interactive & Non-Interactive**: Support for both CLI wizard and batch operations
- **Validation**: Comprehensive validation of user configurations
- **Bulk Operations**: Import from CSV, bulk password generation
- **Service Account Support**: Special handling for service accounts

## Consolidation Notes

This module consolidates functionality from multiple previous scripts:
- ✅ **Replaced**: `scripts/generate_passwords.py` → Use `user-manage generate-password`
- ✅ **Replaced**: `scripts/manage_users.py` (OOP version) → Use `user-manage`
- ✅ **Integrated**: `src/encrypt_password.py` → Use `user-manage encrypt-password`
- ✅ **Integrated**: `src/verify_password.py` → Available as standalone tool
- ⚡ **New**: `user-create` - Primary unified command for user creation

**Legacy commands are still available but deprecated. Use the new unified commands instead.**

## Security

- All password operations use Fernet encryption with keys from `SNOWFLAKE_CONFIG_FERNET_KEYS`
- RSA key pairs are preferred for production authentication
- Automatic MFA compliance checks for PERSON type users
- Network policy enforcement for human users
- Service accounts get unrestricted access patterns

## Environment Variables

Required:
- `SNOWFLAKE_CONFIG_FERNET_KEYS` - Fernet encryption key(s) for password encryption

Optional:
- `SNOWFLAKE_PRIVATE_KEY_PATH` - Path to RSA private key for authentication

## Examples

### Example 1: Create a new analyst user
```bash
uv run user-create
# Follow prompts: first name, last name, email, etc.
# Automatically generates password + RSA keys
# Outputs YAML configuration and credentials
```

### Example 2: Batch create service account
```bash
uv run user-create \\
  --first-name ETL \\
  --last-name Service \\
  --email etl@company.com \\
  --username ETL_SERVICE \\
  --user-type SERVICE \\
  --default-role ETL_ROLE \\
  --no-password \\
  --batch
```

### Example 3: Regenerate password for existing user
```bash
uv run user-manage regenerate-password JOHN_DOE
# Generates new password
# Updates YAML configuration
# Displays plain password for secure delivery
```

### Example 4: Bulk import users from CSV
```bash
# CSV format: first_name,last_name,email,user_type
uv run user-manage import-csv users.csv
```

## Migration Guide

If you were using old commands, here's the migration path:

| Old Command | New Unified Command |
|------------|---------------------|
| `scripts/generate_passwords.py` | `uv run user-manage generate-password USERNAME` |
| `scripts/manage_users.py add` | `uv run user-create` |
| `src/encrypt_password.py` | `uv run user-manage encrypt-password` |
| Multiple password scripts | `uv run user-manage` (all-in-one) |

## Testing

```bash
# Test password generation
uv run user-manage generate-password TEST_USER

# Validate all user configs
uv run user-manage validate-all

# Test RSA key generation
uv run user-manage generate-keys TEST_USER
```

## Support

For issues or questions:
1. Run with `--help` flag: `uv run user-create --help`
2. Check documentation: `docs/MANAGEMENT_COMMANDS.md`
3. Review examples: `docs/NEW_USER_GUIDE.md`
