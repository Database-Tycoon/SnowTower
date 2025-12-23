# State Comparison Agent Guide

This agent specializes in comparing the live state of your Snowflake account with the declarative configuration defined in your SnowDDL files.

## Capabilities

- **Detect Drift**: Explains how to run `snowddl-plan` to detect any manual changes or "drift" in the remote Snowflake environment that is not captured in your configuration.
- **Interpret Plans**: Analyzes the output of a `snowddl-plan` and provides a clear, human-readable summary of the proposed changes (creations, alterations, drops).
- **Investigate Differences**: Helps you understand *why* a certain change is being proposed by pointing to the relevant lines in your YAML configuration.
- **Safe Application**: Provides guidance on how to safely apply changes and what to do if a plan contains unexpected or destructive actions.

## Usage

- Invoke via the Meta-Agent to understand the differences between your code and the live environment.
- Use this agent before running `snowddl-apply` to ensure you fully understand the changes that will be made.

## Example Prompts

- `"How can I check if our Snowflake roles have been modified manually?"`
- `"My `snowddl-plan` shows that a warehouse is going to be dropped, but I didn't change it. Can you help me figure out why?"`
- `"Explain this plan output to me in simple terms."`
