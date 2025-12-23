-- Fix table permissions for ALL tables in PROJ_STRIPE.PROJ_STRIPE schema
-- This script grants permissions on all existing AND future tables to DBT_STRIPE_ROLE__T_ROLE

-- Use ACCOUNTADMIN role (required for granting permissions)
USE ROLE ACCOUNTADMIN;
USE DATABASE PROJ_STRIPE;
USE SCHEMA PROJ_STRIPE;

-- Step 1: Grant ALL privileges on ALL EXISTING tables in the schema to dbt role
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE;

-- Step 2: Grant ALL privileges on ALL EXISTING views in the schema to dbt role
GRANT ALL PRIVILEGES ON ALL VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE;

-- Step 3: Set up FUTURE GRANTS for tables to prevent this issue from recurring
-- This ensures any NEW tables created in PROJ_STRIPE.PROJ_STRIPE automatically grant permissions to dbt
GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE;

-- Step 4: Set up FUTURE GRANTS for views to prevent this issue from recurring
GRANT ALL PRIVILEGES ON FUTURE VIEWS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE TO ROLE DBT_STRIPE_ROLE__T_ROLE;

-- Verify the grants were applied
SHOW GRANTS ON SCHEMA PROJ_STRIPE.PROJ_STRIPE;

-- Check if there are any tables with ownership issues
SELECT
    table_catalog,
    table_schema,
    table_name,
    table_type,
    table_owner
FROM PROJ_STRIPE.INFORMATION_SCHEMA.TABLES
WHERE table_schema = 'PROJ_STRIPE'
  AND table_type IN ('BASE TABLE', 'VIEW')
ORDER BY table_type, table_name;

-- Show all grants on the schema to verify everything is correct
SHOW FUTURE GRANTS IN SCHEMA PROJ_STRIPE.PROJ_STRIPE;
