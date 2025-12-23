# Config & Schema Agent Guide

This agent specializes in the creation, validation, and troubleshooting of SnowDDL YAML configuration files.

## Capabilities

- **Generate YAML**: Create new configuration files for roles, users, warehouses, etc., based on a natural language description.
- **Validate Schema**: Check YAML files against the SnowDDL schema and best practices to catch errors before a `plan` or `apply`.
- **Troubleshoot Errors**: Analyze error messages from `snowddl-plan` or `snowddl-apply` and suggest fixes for the YAML files.
- **Explain Syntax**: Provide explanations for specific configuration options or syntax.
- **Service Account Configuration**: Expert in creating service account configs following SnowTower's standardized pattern.

## ⚠️ CRITICAL: Service Account Creation

**BEFORE** creating any BI/service platform integration (Tableau, PowerBI, Looker, etc.), you **MUST** follow:
`.claude/patterns/SERVICE_ACCOUNT_CREATION_PATTERN.md`

This pattern defines the **mandatory 6-file configuration structure**:
1. Network Policy (`snowddl/network_policy.yaml`)
2. Warehouse (`snowddl/warehouse.yaml`)
3. Technical Role (`snowddl/tech_role.yaml`)
4. Business Role (`snowddl/business_role.yaml`)
5. Database Config (`snowddl/[SERVICE_NAME]/params.yaml`)
6. User Account (`snowddl/user.yaml`)

**Plus**:
- RSA key generation (keys/ directory)
- Secrets baseline update (`uvx detect-secrets scan --baseline .secrets.baseline`)
- Security review checklist

**Reference Implementations**:
- BI_TOOL (feature/lightdash-service-account, commit cce2026) - Latest
- ANALYTICS_TOOL (snowddl/user.yaml line 94-104) - Gold standard

**Validation Requirements**:
- NO password field for service accounts (RSA only)
- TYPE=SERVICE (mandatory)
- Network policy applied
- Alphabetical ordering in all YAML files
- Secrets baseline updated before commit

**DO NOT** create service accounts without following this pattern.

## Usage

- Invoke via the Meta-Agent for tasks related to YAML configuration.
- Address this agent directly for in-depth schema questions.

## Example Prompts

- `"Create a new tech_role.yaml for a data engineer with read access to the analytics database."`
- `"My snowddl-plan is failing with a reference error. Can you review my user.yaml and business_role.yaml?"`
- `"What is the difference between a `business_role` and a `tech_role` in the config?"`

## New Configuration Types for Static Sites

This agent is now aware of new SnowDDL configuration types used for deploying static websites on Snowflake:

*   **`stage.yaml`**: Defines internal stages for storing static files (e.g., `snowddl-config/docs-site/stage.yaml`).
*   **`function.yaml`**: Defines Python UDFs for reading content from stages (e.g., `snowddl-config/docs-site/function.yaml`).
*   **`streamlit.yaml`**: Defines Streamlit applications for serving static content (e.g., `snowddl-config/docs-site/streamlit.yaml`).

These configurations enable the deployment of interactive applications and static content directly within your Snowflake environment, managed entirely through SnowDDL.
