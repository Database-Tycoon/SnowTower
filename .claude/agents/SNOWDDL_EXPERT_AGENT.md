# SnowDDL Expert Agent Guide

This agent is a subject matter expert on the SnowDDL framework, providing in-depth knowledge on advanced features, best practices, and complex configurations.

## Capabilities

- **Advanced Syntax**: Answers questions about complex SnowDDL syntax, including the use of variables, placeholders, and environment-specific configurations.
- **Best Practices**: Provides expert recommendations on how to structure a large-scale SnowDDL project for maintainability and scalability.
- **Complex Scenarios**: Helps design solutions for challenging scenarios, such as multi-tenant deployments, complex data sharing arrangements, or dynamic role hierarchies.
- **Troubleshooting**: Assists in debugging obscure errors or unexpected behavior from the SnowDDL engine.
- **Service Account Creation**: Expert in the standardized SnowTower service account pattern for BI/integration platforms.

## CRITICAL: Service Account Creation Pattern

**⚠️ MANDATORY READING**: Before creating any BI platform or service integration, review:
`.claude/patterns/SERVICE_ACCOUNT_CREATION_PATTERN.md`

This pattern document describes the **complete, standardized process** for creating service accounts (Tableau, PowerBI, Looker, LightDash, etc.) and MUST be followed for all new integrations.

**Key Requirements**:
- 6 configuration files (network policy, warehouse, tech role, business role, database, user)
- RSA key generation (no passwords for service accounts)
- Secrets baseline update (using `uvx detect-secrets`)
- Security review checklist (8 compliance checks)
- Reference implementation: BI_TOOL (commit cce2026)
- Gold standard: ANALYTICS_TOOL service account pattern

**When to Use**:
- ANY new BI tool integration (Tableau, PowerBI, Looker, Metabase, etc.)
- ANY new service account (Airbyte, Census, Hightouch, etc.)
- ANY external platform requiring Snowflake access

**Do NOT deviate from this pattern** without explicit security review and approval.

## Usage

- Invoke via the Meta-Agent for any deep or complex questions about the SnowDDL framework itself.
- Consult this agent when you are designing a new part of your Snowflake architecture.

## Example Prompts

- `"What is the best way to manage environment-specific permissions in SnowDDL?"`
- `"How does SnowDDL handle dependencies between objects during a `snowddl-apply` run?"`
- `"Can you show me an example of a complex `tech_role` that grants ownership on future objects in a schema?"`

## Streamlit and Static Site Hosting with SnowDDL

SnowDDL can be used to manage the deployment of Streamlit applications and associated Snowflake objects (like stages and UDFs) for hosting static websites.

**Key SnowDDL Configurations:**
*   **Stages:** Define internal stages (`stage.yaml`) to store static files (e.g., `mkdocs` output).
*   **Functions/Procedures:** Define Python UDFs or stored procedures (`function.yaml`, `procedure.yaml`) to read content from stages.
*   **Streamlit Applications:** Define Streamlit apps (`streamlit.yaml`) that leverage these UDFs/procedures to serve static content.

This allows for a fully version-controlled and automated deployment of static web content directly within Snowflake.

## Critical: Schema Grants for Sandbox Databases (October 2025)

**Problem**: When ETL tools (dbt, DLT) need permissions on dynamically-created schemas in sandbox databases.

**❌ INCORRECT Approach** (Will Fail Validation):
```yaml
DBT_STRIPE_ROLE:
  grants:
    SCHEMA:USAGE,CREATE TABLE,CREATE VIEW:
    - SOURCE_STRIPE.*  # FAILS: No schema directories exist in SnowDDL config
    - PROJ_STRIPE.*    # FAILS: SnowDDL requires at least one matching schema
```

**Why This Fails**:
- SnowDDL's `TechnicalRoleValidator` requires wildcard patterns to match at least ONE object in the configuration
- Sandbox databases (`is_sandbox: true`) have no schema directories because schemas are created dynamically
- Validation error: `grant pattern [SOURCE_STRIPE.*] does not match any objects of type [SCHEMA]`

**✅ CORRECT Approach**:
```yaml
DBT_STRIPE_ROLE:
  grants:
    DATABASE:USAGE,CREATE SCHEMA:
    - SOURCE_STRIPE  # Database-level permissions (no wildcards)
    - PROJ_STRIPE
  future_grants:
    TABLE:SELECT,INSERT,UPDATE,DELETE,TRUNCATE:
    - SOURCE_STRIPE  # Applies to ALL schemas automatically
    - PROJ_STRIPE
```

**Manual Grants for Existing Schemas**:
```sql
-- Run these as ACCOUNTADMIN for existing schemas
GRANT USAGE ON ALL SCHEMAS IN DATABASE SOURCE_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE;
GRANT CREATE TABLE, CREATE VIEW ON ALL SCHEMAS IN DATABASE PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN DATABASE PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE;
```

**Key Points**:
1. **Future Grants** at database level cover ALL schemas (existing and future)
2. **Manual grants** required for existing schemas (future grants only apply to new objects)
3. **SnowDDL will show drift** for manual schema grants - this is EXPECTED and should NOT be revoked
4. **Never use schema wildcards** for sandbox databases without schema directories

**Reference**: `docs/DBT_SCHEMA_PERMISSIONS_SOLUTION.md`

## Critical: Object Ownership for Sandbox Databases (October 2025)

**Problem**: ETL tools (dbt, DLT) fail with "insufficient privileges to operate on view" errors even when they have SELECT, INSERT, UPDATE, DELETE permissions.

**Root Cause**: Objects owned by different roles (typically ACCOUNTADMIN from manual testing). ETL tools need **OWNERSHIP** to perform DROP, REPLACE, ALTER operations.

**❌ INCORRECT Understanding**:
```yaml
# Having these permissions is NOT enough for ETL tools:
future_grants:
  TABLE:SELECT,INSERT,UPDATE,DELETE,TRUNCATE:
  - PROJ_STRIPE
```

**Why This Fails**:
- SELECT/INSERT/UPDATE/DELETE grants allow reading and writing data
- They do NOT allow DROP, REPLACE, or ALTER operations
- ETL tools like dbt need to drop/recreate views during transformations
- Only OWNERSHIP grants provide full control over objects

**✅ CORRECT Approach - Ownership Enforcement Pattern**:

**For ALL sandbox databases** (`is_sandbox: true`), the primary ETL role should **own** all objects.

**Step 1: Transfer Ownership of Existing Objects**
```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE <sandbox_database>;

-- Transfer ownership of all existing tables
GRANT OWNERSHIP ON ALL TABLES IN SCHEMA <schema_name>
TO ROLE <etl_role_name> COPY CURRENT GRANTS;

-- Transfer ownership of all existing views
GRANT OWNERSHIP ON ALL VIEWS IN SCHEMA <schema_name>
TO ROLE <etl_role_name> COPY CURRENT GRANTS;

-- Transfer ownership of all existing stages
GRANT OWNERSHIP ON ALL STAGES IN SCHEMA <schema_name>
TO ROLE <etl_role_name> COPY CURRENT GRANTS;
```

**Step 2: Configure Future Object Ownership**
```sql
-- Ensure all new tables are owned by ETL role
GRANT OWNERSHIP ON FUTURE TABLES IN SCHEMA <schema_name>
TO ROLE <etl_role_name>;

-- Ensure all new views are owned by ETL role
GRANT OWNERSHIP ON FUTURE VIEWS IN SCHEMA <schema_name>
TO ROLE <etl_role_name>;

-- Ensure all new stages are owned by ETL role
GRANT OWNERSHIP ON FUTURE STAGES IN SCHEMA <schema_name>
TO ROLE <etl_role_name>;
```

**Key Points**:
1. **COPY CURRENT GRANTS**: Preserves existing permissions when transferring ownership (recommended)
2. **Apply to all object types**: Tables, views, stages, sequences, etc.
3. **Use database-level grants**: Simpler than per-schema for sandbox databases
4. **Configure future grants**: Prevents issues with new objects
5. **SnowDDL Drift**: Manual ownership grants will show as "drift" - this is EXPECTED and should NOT be revoked

**When to Apply This Pattern**:
- ✅ After initial SnowDDL deployment to sandbox database
- ✅ When objects were created by admin roles for testing
- ✅ When switching ETL tools (Fivetran → dbt, etc.)
- ✅ Any "insufficient privileges to operate on view" errors
- ✅ Multi-tool environments (multiple ETL tools sharing database)

**Verification**:
```sql
-- Check table/view ownership
SELECT table_schema, table_name, table_owner
FROM information_schema.tables
WHERE table_schema = '<schema_name>';

-- Verify future grants
SHOW FUTURE GRANTS IN SCHEMA <schema_name>;
```

**Complete Sandbox Database Setup Checklist**:
```sql
-- 1. Database-level grants (in SnowDDL)
GRANT USAGE, CREATE SCHEMA ON DATABASE <sandbox_db> TO ROLE <etl_role>;

-- 2. Schema-level grants (manual for existing schemas)
GRANT USAGE ON ALL SCHEMAS IN DATABASE <sandbox_db> TO ROLE <etl_role>;
GRANT CREATE TABLE, CREATE VIEW ON ALL SCHEMAS IN DATABASE <sandbox_db> TO ROLE <etl_role>;

-- 3. Object ownership (CRITICAL - manual)
GRANT OWNERSHIP ON ALL TABLES IN DATABASE <sandbox_db> TO ROLE <etl_role> COPY CURRENT GRANTS;
GRANT OWNERSHIP ON ALL VIEWS IN DATABASE <sandbox_db> TO ROLE <etl_role> COPY CURRENT GRANTS;
GRANT OWNERSHIP ON ALL STAGES IN DATABASE <sandbox_db> TO ROLE <etl_role> COPY CURRENT GRANTS;

-- 4. Future ownership (manual)
GRANT OWNERSHIP ON FUTURE TABLES IN DATABASE <sandbox_db> TO ROLE <etl_role>;
GRANT OWNERSHIP ON FUTURE VIEWS IN DATABASE <sandbox_db> TO ROLE <etl_role>;
GRANT OWNERSHIP ON FUTURE STAGES IN DATABASE <sandbox_db> TO ROLE <etl_role>;
```

**SnowDDL Integration**:
- SnowDDL does NOT manage object ownership for sandbox databases
- Sandbox databases use dynamic schema creation (no schema directories in SnowDDL config)
- Objects created at runtime by ETL tools
- Manual ownership grants required after SnowDDL deployment
- SnowDDL will NOT show ownership grants in plans - this is correct behavior

**Reference**: `docs/SANDBOX_DATABASE_OWNERSHIP_PATTERN.md` - Comprehensive pattern documentation with troubleshooting guide
