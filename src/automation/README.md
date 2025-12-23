# SnowTower Automation Module

Enterprise-grade automation system for converting GitHub issues into SnowDDL user configurations with automated PR creation.

## Quick Start

```bash
# Process a GitHub issue and create a PR
uv run github-to-snowddl --issue 123

# Dry run to preview
uv run github-to-snowddl --issue 123 --dry-run
```

## Module Components

### 1. `issue_parser.py` - GitHub Issue Parser

**Purpose**: Extract structured user data from GitHub issue markdown templates.

**Key Classes**:
- `GitHubIssueParser`: Main parser class
- `ParsedIssueData`: Structured data container
- `UserTypeSelection`, `RoleTypeSelection`, `WorkloadSize`: Enums for selections

**Usage**:
```python
from automation.issue_parser import GitHubIssueParser

parser = GitHubIssueParser()

# Parse from GitHub API
parsed_data = parser.parse_from_gh_api(issue_number=123)

# Parse from file
with open('issue.json') as f:
    issue_data = json.load(f)
parsed_data = parser.parse_issue(issue_data['body'])

# Validate
errors = parsed_data.validate()
if errors:
    print(f"Validation failed: {errors}")
```

### 2. `yaml_generator.py` - SnowDDL YAML Generator

**Purpose**: Generate valid SnowDDL YAML configurations with credentials.

**Key Classes**:
- `SnowDDLYAMLGenerator`: Configuration generator
- `GeneratedUserConfig`: Complete config with credentials

**Features**:
- Automatic username generation
- Role and warehouse mapping
- RSA key pair generation
- Encrypted password generation
- Security policy assignment

**Usage**:
```python
from automation.yaml_generator import SnowDDLYAMLGenerator

generator = SnowDDLYAMLGenerator()

config = generator.generate_from_issue_data(
    parsed_data,
    generate_rsa_keys=True,
    generate_password=True,
    password_length=16
)

# Access generated data
print(f"Username: {config.username}")
print(f"Password: {config.temp_password}")
print(f"Private Key: {config.private_key_path}")

# Get YAML config
yaml_config = config.yaml_config
```

### 3. `validator.py` - Security Validator

**Purpose**: Comprehensive security and compliance validation.

**Key Classes**:
- `UserConfigValidator`: Main validator
- `ValidationResult`: Results with findings
- `ValidationFinding`: Individual finding
- `ValidationSeverity`: ERROR, WARNING, INFO

**Validation Checks**:
- Username format and SQL injection prevention
- Email domain allowlisting
- RSA public key format
- Authentication requirements
- Security policy compliance
- MFA requirements
- Role assignment validation

**Usage**:
```python
from automation.validator import UserConfigValidator

validator = UserConfigValidator(strict_mode=True)

result = validator.validate_user_config(username, user_config)

# Check result
if result.is_valid:
    print("✓ Validation passed!")
else:
    for error in result.errors:
        print(f"ERROR: {error.message}")

    for warning in result.warnings:
        print(f"WARNING: {warning.message}")

# Print formatted summary
result.print_summary()
```

### 4. `pr_creator.py` - GitHub PR Creator

**Purpose**: Automated pull request creation with proper formatting.

**Key Classes**:
- `GitHubPRCreator`: PR automation engine
- `PRResult`: PR creation result

**Features**:
- Branch creation and management
- YAML file updates
- Commit with proper messages
- PR creation with formatted description
- Issue-PR linking
- Automatic cleanup on failure

**Usage**:
```python
from automation.pr_creator import GitHubPRCreator

pr_creator = GitHubPRCreator()

pr_result = pr_creator.create_user_deployment_pr(
    username="JOHN_DOE",
    yaml_config=config.yaml_config,
    issue_number=123,
    metadata=config.metadata,
    base_branch="main"
)

print(f"PR #{pr_result.pr_number}: {pr_result.pr_url}")
print(f"Branch: {pr_result.branch_name}")
```

## Role Mappings

The generator maps issue role selections to Snowflake business roles:

```python
ROLE_MAPPING = {
    'DATA_ANALYST': ['COMPANY_USERS'],
    'BI_DEVELOPER': ['BI_DEVELOPER_ROLE'],
    'DATA_ENGINEER': ['COMPANY_USERS', 'DATA_ENGINEER_ROLE'],
    'TRAINING': ['TRAINING_ROLE'],
    'INTEGRATION_SERVICE': ['DATA_INTEGRATION_ROLE'],
    'AI_ML_SERVICE': ['AI_ML_ROLE'],
}
```

## Warehouse Mappings

Workload sizes map to warehouses:

```python
WAREHOUSE_MAPPING = {
    'LIGHT': 'MAIN_WAREHOUSE',
    'MEDIUM': 'TRANSFORMING',
    'HEAVY': 'MAIN_WAREHOUSE',  # Requires review
    'DEVELOPMENT': 'DEV_WH',
}
```

## Security Features

### Input Validation

**SQL Injection Prevention**:
- Pattern matching for dangerous characters
- SQL keyword detection
- Character allowlisting

**Email Domain Allowlisting**:
```python
# Configure in validator.py
ALLOWED_EMAIL_DOMAINS = [
    'company.com',
    'example.com',
]
```

**Username Requirements**:
- 3-64 characters
- Alphanumeric and underscore only
- Must start with letter
- No reserved keywords (ADMIN, ROOT, etc.)

### Authentication Security

**Encrypted Passwords**:
- Fernet encryption (AES-128)
- Cryptographically secure random generation
- Configurable length (minimum 12, recommended 16+)

**RSA Key Validation**:
- Base64 format verification
- Minimum length check (2048-bit minimum)
- Proper key structure validation

## Integration with Existing Systems

The automation module integrates with:

1. **User Management System** (`src/user_management/`)
   - `UserManager` for user operations
   - `FernetEncryption` for password encryption
   - `RSAKeyManager` for key generation
   - `PasswordGenerator` for secure passwords
   - `YAMLHandler` for safe YAML operations

2. **SnowDDL Core** (`src/snowddl_core/`)
   - Uses standard SnowDDL YAML format
   - Compatible with existing workflows
   - Follows established patterns

3. **GitHub CLI** (`gh`)
   - Issue fetching
   - PR creation
   - Comment management

## Error Handling

All components use custom exceptions:

```python
from automation.issue_parser import IssueParsingError
from automation.yaml_generator import YAMLGenerationError
from automation.pr_creator import PRCreationError
from automation.validator import ValidationError

try:
    # Your automation code
    pass
except IssueParsingError as e:
    print(f"Failed to parse issue: {e}")
except YAMLGenerationError as e:
    print(f"Failed to generate YAML: {e}")
except PRCreationError as e:
    print(f"Failed to create PR: {e}")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Testing

### Unit Tests

```python
import pytest
from automation.issue_parser import GitHubIssueParser
from automation.validator import UserConfigValidator

def test_parse_valid_issue():
    parser = GitHubIssueParser()
    issue_body = """
    ### Full Name
    John Doe

    ### Email Address
    john.doe@company.com

    [x] I understand data handling
    """

    parsed = parser.parse_issue(issue_body)
    assert parsed.full_name == "John Doe"
    assert parsed.email == "john.doe@company.com"
    assert parsed.data_handling_confirmed == True

def test_validation():
    validator = UserConfigValidator()

    config = {
        'type': 'PERSON',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@company.com',
        'password': 'gAAAAABk7X2...',
        'business_roles': ['COMPANY_USERS'],
        'default_warehouse': 'MAIN_WAREHOUSE',
    }

    result = validator.validate_user_config('JOHN_DOE', config)
    assert result.is_valid == True
```

### Integration Tests

```python
def test_end_to_end_automation():
    """Test complete automation workflow"""
    # 1. Parse issue
    parser = GitHubIssueParser()
    parsed_data = parser.parse_issue(sample_issue_body)

    # 2. Generate config
    generator = SnowDDLYAMLGenerator()
    config = generator.generate_from_issue_data(parsed_data)

    # 3. Validate
    validator = UserConfigValidator()
    result = validator.validate_user_config(
        config.username,
        config.yaml_config[config.username]
    )

    assert result.is_valid == True
    assert config.temp_password is not None
    assert config.private_key_path is not None
```

## Customization

### Custom Role Mappings

Edit `src/automation/yaml_generator.py`:

```python
class SnowDDLYAMLGenerator:
    ROLE_MAPPING = {
        RoleTypeSelection.DATA_ANALYST: ['YOUR_CUSTOM_ROLE'],
        # Add your mappings
    }
```

### Custom Validation Rules

Edit `src/automation/validator.py`:

```python
class UserConfigValidator:
    ALLOWED_EMAIL_DOMAINS = ['your-domain.com']
    USERNAME_PATTERN = re.compile(r'^YOUR_PATTERN$')
```

### Custom PR Templates

Edit `src/automation/pr_creator.py`:

```python
def _generate_pr_body(self, ...):
    body = f"## Your Custom Template\n\n"
    # Customize PR format
    return body
```

## Monitoring

### Logging

All components use Rich console for beautiful output:

```python
from rich.console import Console

console = Console()
console.print("[green]✓ Success![/green]")
console.print("[red]✗ Error![/red]")
console.print("[yellow]⚠ Warning![/yellow]")
```

### Metrics

Track these metrics:
- Automation success rate
- Validation failure rate
- Average processing time
- Manual intervention rate

## Best Practices

1. **Always validate** before deployment
2. **Use dry-run** for testing
3. **Review PRs** before merging
4. **Rotate credentials** regularly
5. **Audit regularly** for compliance
6. **Monitor failures** and investigate
7. **Update mappings** as roles change
8. **Document exceptions** thoroughly

## Troubleshooting

See [AUTOMATION.md](../../docs/AUTOMATION.md) for comprehensive troubleshooting guide.

## Contributing

When adding features:

1. Follow existing patterns
2. Add comprehensive validation
3. Include error handling
4. Write tests
5. Update documentation
6. Use type hints
7. Follow security best practices

## Security Considerations

- Never commit credentials
- Always encrypt passwords
- Validate all inputs
- Use strict mode in production
- Regularly audit access
- Monitor for anomalies
- Keep dependencies updated

## License

Part of the SnowTower project. See main LICENSE file.
