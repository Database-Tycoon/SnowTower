# Cost Management Agent Guide

This agent is focused on analyzing Snowflake configurations to identify opportunities for cost optimization.

## Capabilities

- **Warehouse Analysis**: Review `warehouse.yaml` configurations and suggest adjustments to `size`, `auto_suspend`, and scaling policies to reduce credit usage.
- **Resource Monitor Review**: Analyze `resource_monitor.yaml` files to ensure they are effectively preventing budget overruns.
- **Query Cost Estimation**: (Experimental) Provide high-level cost estimates for SQL queries based on warehouse size and query complexity.
- **Best Practice Recommendations**: Offer general advice on Snowflake cost management, such as using separate warehouses for different workloads.

## Usage

- Invoke via the Meta-Agent to get cost-saving recommendations.
- Use this agent periodically to review your configurations and control Snowflake spending.

## Example Prompts

- `"Analyze my `warehouse.yaml` and suggest changes to optimize for cost."`
- `"Is the resource monitor we've defined in `resource_monitor.yaml` adequate for a monthly budget of $5,000?"`
- `"What's the most cost-effective warehouse size for our nightly ETL jobs?"`
