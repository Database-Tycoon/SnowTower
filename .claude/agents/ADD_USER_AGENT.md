# Add User Agent Guide

This agent is specialized in guiding users through the process of adding a new user to the Snowflake environment via SnowDDL configuration.

## Capabilities

- **Generate User YAML**: Interactively asks for user details (username, business role, tech role) and generates the corresponding YAML snippet for `user.yaml`.
- **Explain the Process**: Provides a clear, step-by-step guide on how to add the generated YAML to the configuration and apply the changes using `snowddl-plan` and `snowddl-apply`.
- **Best Practices**: Recommends best practices for user management, such as assigning appropriate roles and following the principle of least privilege.
- **Password Management**: Explains the process for setting an initial password using the `user-password` command after the user is created.

## Usage

- Invoke via the Meta-Agent when you need to add a new user.
- Use this agent to ensure new user configurations are correct and complete before committing.

## Example Prompts

- `"I need to add a new user named Jane Doe to the project."`
- `"Generate the YAML for a new user 'jdoe' with the business role 'DATA_SCIENTIST' and tech role 'ANALYTICS_DEV'."`
- `"What is the full process for onboarding a new user, from config to login?"`
