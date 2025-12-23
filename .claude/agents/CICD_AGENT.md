# CI/CD & Automation Agent Guide

This agent assists with creating, maintaining, and troubleshooting CI/CD pipelines and other automation workflows for the SnowTower-SnowDDL project.

## Capabilities

- **Pipeline Generation**: Generate starter CI/CD pipeline configurations (e.g., for GitHub Actions, GitLab CI) that automate `snowddl-plan` and `snowddl-apply`.
- **Scripting Assistance**: Help write shell or Python scripts for automation tasks, such as pre-validation checks or notifications.
- **Troubleshooting**: Analyze failed pipeline runs and suggest fixes for the CI/CD configuration or related scripts.
- **Workflow Optimization**: Recommend ways to improve the speed and reliability of your automation workflows.

## Usage

- Invoke via the Meta-Agent for tasks related to CI/CD and automation.
- Use this agent when setting up a new repository or improving an existing automation process.

## Example Prompts

- `"Generate a GitHub Actions workflow that runs `snowddl-plan` on every pull request."`
- `"My GitLab CI pipeline is failing at the `snowddl-apply` step. Here are the logs, can you help me debug it?"`
- `"Write a script to send a Slack notification after a successful deployment."`

## Current GitHub Actions Status

### ✅ Successfully Implemented Workflows (Sept 22, 2025)

#### PR Validation Workflow (`pr-validation.yml`)
- **Triggers**: Pull requests to main branch, manual dispatch
- **Security Scans**: Bandit (Python), Safety (dependencies), YAML security
- **SnowDDL Integration**: Automated plan generation and validation
- **Features**:
  - Automatic PR commenting with plan output
  - Artifact upload for review
  - Error handling with detailed diagnostics

#### Common Issues Resolved
1. **Safety command syntax**: Use `-o json > file.json` not `--output file.json`
2. **Module imports**: Run Python scripts with `uv run python` for environment access
3. **Exit codes**: Add `|| true` or `|| echo` to continue on non-zero exits
4. **Private key format**: Ensure PEM format with proper headers/footers in secrets
5. **PR context**: Use `if: github.event_name == 'pull_request'` for PR-specific steps

### Troubleshooting Guide

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: yaml` | Use `uv run python script.py` |
| `ValueError: Unable to load PEM file` | Check private key format in GitHub secrets |
| `HttpError: Not Found` on PR comment | Add condition for pull_request events |
| `exit code 64` from safety | Add error handling, vulnerabilities are warnings |
