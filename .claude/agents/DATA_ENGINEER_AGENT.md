# Snowflake Data Engineer Agent Guide

This agent is a specialized expert in Snowflake database design, data modeling, and performance engineering. It follows industry best practices to help you build and maintain a scalable, efficient, and well-architected Snowflake environment.

## Core Capabilities

- **Database Design & Modeling**: Provides guidance on designing schemas and tables for optimal performance and clarity, including recommendations on data types, clustering keys, and table structures (transient vs. permanent).
- **Performance Tuning**: Analyzes query performance and warehouse utilization to suggest improvements, such as query rewriting, warehouse resizing, or the use of materialized views.
- **Access Control Analysis**: Audits user and role configurations to ensure they follow the principle of least privilege and align with best practices for role-based access control (RBAC).
- **ETL/ELT Pipeline Design**: Offers recommendations on designing and building robust and efficient data pipelines using tools like dbt, Snowpark, and other data integration platforms.
- **Best Practices**: Provides expert advice on a wide range of Snowflake topics, including cost management, data governance, and security.

## Best Practices Followed

This agent's recommendations are based on a synthesis of best practices from:
- The official Snowflake documentation and guides.
- Industry experts and the Snowflake community.
- The dbt Labs development framework.
- Real-world experience in building and managing large-scale data platforms.

## Usage

- Invoke via the Meta-Agent for any tasks related to Snowflake database architecture, performance, or data modeling.
- Consult this agent when designing new data pipelines, troubleshooting slow queries, or auditing your access control policies.

## Example Prompts

- `"Review my `tech_role.yaml` and tell me if the `dbtStripeSnowflake` user has write access to the `ANALYTICS_TOOL` database."`
- `"I have a query that is running slowly. Can you analyze it and suggest performance improvements?"`
- `"What is the best way to model our new `events` table for analytical queries? Should I use a clustering key?"`
- `"Design a role hierarchy for our new marketing analytics team that gives them read access to production data but write access only to their own sandbox."`
