# Deployment Troubleshooting Agent Guide

This agent is a specialized expert for diagnosing and resolving issues with the `deploy-production.yml` GitHub Action workflow. It encapsulates the lessons learned from past failures to provide a rapid and accurate diagnosis.

## Core Capabilities

- **Log Analysis**: Analyzes workflow logs to identify the root cause of failures.
- **Configuration Validation**: Checks the workflow file for common errors and bugs.
- **Secret Management Guidance**: Provides clear instructions on how to configure secrets for the deployment workflow.

## Common Failure Scenarios & Resolutions

This section serves as a knowledge base of known issues and their solutions.

### 1. Error: `Missing required environment variable: SNOWFLAKE_ACCOUNT`

-   **Symptom**: The "Validate Environment Variables" step fails with this error.
-   **Root Cause**: The workflow script cannot access the secrets it needs. This is caused by a bug in the workflow file where the step using the secret is missing an `env` block to explicitly map the secret to an environment variable.
-   **Resolution**: Ensure the step that uses the secret has a correctly formatted `env` block (e.g., `SNOWFLAKE_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}`).

### 2. Error: `JWT token is invalid`

-   **Symptom**: The `snowddl-plan` command fails with a `snowflake.connector.errors.DatabaseError` related to an invalid JWT token.
-   **Root Cause**: The public key configured for the service user in Snowflake does not match the private key being used in the GitHub Actions secret.
-   **Resolution**:
    1.  Use a dedicated, non-personal key pair for the service account (e.g., `snowflake_dlt.p8`).
    2.  Extract the public key from the correct private key: `openssl rsa -in ~/.ssh/snowflake_dlt.p8 -pubout`.
    3.  Update the Snowflake user with the new public key: `ALTER USER SNOWDDL SET RSA_PUBLIC_KEY='your_public_key';`.
    4.  Update the `SNOWFLAKE_PRIVATE_KEY` GitHub secret with the base64-encoded version of the correct private key: `cat ~/.ssh/snowflake_dlt.p8 | base64`.

### 3. Error: `Could not deserialize key data`

-   **Symptom**: The `snowddl-plan` command fails with a cryptography error when trying to read the private key.
-   **Root Cause**: The `SNOWFLAKE_PRIVATE_KEY` secret is not a valid, PEM-formatted RSA private key, likely due to a copy-paste error or formatting issues.
-   **Resolution**: Always store the private key secret in GitHub as a base64-encoded string. The workflow is designed to decode it.

### 4. Error: `Plan blocked by safety checks`

-   **Symptom**: The "Safety Analysis" step fails, blocking the deployment.
-   **Root Cause**: The `plan-safety-checker.py` script has detected a potentially destructive or high-risk operation in the deployment plan.
-   **Resolution**:
    1.  Carefully review the `deployment-plan.txt` artifact from the failed workflow run.
    2.  If the changes are intentional, re-run the workflow with the `force_apply` input set to `true`.
    3.  If the changes are unintentional, correct your SnowDDL configuration.

## Advanced Troubleshooting Techniques

### Fetching Workflow Logs Securely and Efficiently

To avoid interactive pagers and get the full log output directly, use this two-step process:

1.  **Get the exact Run ID**:
    ```bash
    gh run list --workflow="deploy-production.yml" --limit 1 --json databaseId | jq -r '.[0].databaseId'
    ```
2.  **Fetch the logs using the ID**:
    ```bash
    gh run view <RUN_ID> --log | cat
    ```

### Securely Validating the Private Key in the Workflow

To verify the integrity of the private key within the workflow without exposing it, use the following `openssl` command. This was added as a debugging step.

```yaml
- name: "Validate Private Key Integrity"
  run: |
    if openssl rsa -in /tmp/snowflake_key.p8 -check -noout; then
      echo "✅ Private key is a valid RSA key."
    else
      echo "❌ Private key is NOT a valid RSA key."
      exit 1
    fi
```
