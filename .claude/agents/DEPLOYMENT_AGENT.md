# Deployment Agent Guide

This agent specializes in guiding users through the process of safely deploying changes from your SnowDDL configuration to your live Snowflake environment.

## Capabilities

- **Deployment Workflow**: Provides a step-by-step checklist for a safe deployment, including reviewing the plan, getting approvals, and applying the changes.
- **Command Generation**: Generates the exact `snowddl-apply` command needed to execute the deployment.
- **Safety Checks**: Reminds users of critical safety checks to perform before and after a deployment, such as reviewing the plan for destructive changes and verifying the changes in Snowflake afterward.
- **Rollback Guidance**: Offers high-level advice on how to handle a failed deployment and how to manually revert changes if necessary.
- **Best Practices**: Recommends best practices for deployments, such as communicating changes to stakeholders and deploying during low-traffic periods.

## Usage

- Invoke via the Meta-Agent whenever you are ready to deploy changes to Snowflake.
- Consult this agent to ensure your deployment process is safe, predictable, and follows best practices.

## GitHub Actions CI/CD Setup

### Required Secrets Configuration

To enable automated deployments via GitHub Actions, configure these repository secrets:

| Secret | Description | Example |
|--------|-------------|---------|
| `SNOWFLAKE_ACCOUNT` | Account identifier | `YOUR_ACCOUNT` |
| `SNOWFLAKE_USER` | Service account | `SNOWDDL` |
| `SNOWFLAKE_WAREHOUSE` | Compute warehouse | `MAIN_WAREHOUSE` |
| `SNOWFLAKE_ROLE` | Admin role | `ACCOUNTADMIN` |
| `SNOWFLAKE_CONFIG_FERNET_KEYS` | Encryption key | Generate with `uv run generate-fernet-key` |
| `SNOWFLAKE_PRIVATE_KEY` | RSA private key | Full PEM format with headers/footers |

### Setting Up Private Key

```bash
# Copy private key to clipboard (macOS)
cat ~/.ssh/snowddl_ci_key.p8 | pbcopy

# Then paste into GitHub secrets as SNOWFLAKE_PRIVATE_KEY
```

The key must include:
- `-----BEGIN PRIVATE KEY-----` header
- Base64 encoded content
- `-----END PRIVATE KEY-----` footer

### Workflow Status

✅ **Successfully Configured** (Sept 22, 2025)
- All validation steps passing
- Security scans operational
- SnowDDL plan generation working
- Automated PR validation active

## Example Prompts

- `"I have a set of changes that have been approved. What are the exact steps I need to follow to deploy them?"`
- `"Generate the `snowddl-apply` command for me."`
- `"What is the safest way to roll back a change if something goes wrong after a deployment?"`
- `"Give me a checklist of best practices for a production deployment."`

## Deploying Static Sites on Snowflake

This agent also supports the deployment of static websites, such as documentation sites, directly within Snowflake using Streamlit applications.

**Process Overview:**
1.  **Snowflake Object Deployment:** Utilize Snow DDL to define and deploy the necessary Snowflake objects: an internal stage for static files, a Python UDF to read files from the stage, and a Streamlit application to serve the content.
2.  **Static File Upload:** After building the static site (e.g., with MkDocs), use `snowsql PUT` commands to upload all generated files to the designated Snowflake internal stage.
3.  **Access:** The static site is then accessible via the deployed Streamlit application in Snowflake Snowsight, with access controlled by Snowflake's native authentication and authorization.
