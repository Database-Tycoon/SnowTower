-- ==============================================================================
-- STREAMLIT VIEWER ROLE CREATION SCRIPT
-- ==============================================================================
-- Purpose: Create a read-only infrastructure viewer role for Streamlit app users
-- Author: SnowTower Security Team
-- Date: 2025-09-26
-- ==============================================================================

-- Use ACCOUNTADMIN role to create and grant privileges
USE ROLE ACCOUNTADMIN;

-- ==============================================================================
-- STEP 1: CREATE THE VIEWER ROLE
-- ==============================================================================
CREATE ROLE IF NOT EXISTS STREAMLIT_VIEWER
COMMENT = 'Read-only infrastructure viewer role for Streamlit app users - provides minimal metadata access without data privileges';

-- Grant to SYSADMIN for role management
GRANT ROLE STREAMLIT_VIEWER TO ROLE SYSADMIN;

-- ==============================================================================
-- STEP 2: CREATE DEDICATED WAREHOUSE
-- ==============================================================================
CREATE WAREHOUSE IF NOT EXISTS STREAMLIT_VIEWER_WH
WITH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  MIN_CLUSTER_COUNT = 1
  MAX_CLUSTER_COUNT = 1
  INITIALLY_SUSPENDED = FALSE
COMMENT = 'Dedicated warehouse for Streamlit viewer metadata queries - minimal resources for cost efficiency';

-- Grant usage on warehouse
GRANT USAGE ON WAREHOUSE STREAMLIT_VIEWER_WH TO ROLE STREAMLIT_VIEWER;

-- ==============================================================================
-- STEP 3: GRANT METADATA ACCESS PRIVILEGES
-- ==============================================================================

-- Grant imported privileges on SNOWFLAKE database for ACCOUNT_USAGE access
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE STREAMLIT_VIEWER;

-- Grant monitor privilege on account for viewing resource metadata
GRANT MONITOR USAGE ON ACCOUNT TO ROLE STREAMLIT_VIEWER;

-- Grant usage on all current databases (metadata discovery only)
GRANT USAGE ON ALL DATABASES IN ACCOUNT TO ROLE STREAMLIT_VIEWER;

-- Grant usage on all current schemas (metadata discovery only)
GRANT USAGE ON ALL SCHEMAS IN ACCOUNT TO ROLE STREAMLIT_VIEWER;

-- Future grants for new databases and schemas
GRANT USAGE ON FUTURE DATABASES IN ACCOUNT TO ROLE STREAMLIT_VIEWER;
GRANT USAGE ON FUTURE SCHEMAS IN ACCOUNT TO ROLE STREAMLIT_VIEWER;

-- Grant monitor on all warehouses (view status, not operate)
GRANT MONITOR ON ALL WAREHOUSES IN ACCOUNT TO ROLE STREAMLIT_VIEWER;

-- ==============================================================================
-- STEP 4: GRANT TO BUSINESS ROLES
-- ==============================================================================

-- Grant to existing business roles
GRANT ROLE STREAMLIT_VIEWER TO ROLE COMPANY_USERS;
GRANT ROLE STREAMLIT_VIEWER TO ROLE ADMIN_ROLE;
GRANT ROLE STREAMLIT_VIEWER TO ROLE BI_DEVELOPER_ROLE;

-- Optional: Grant to additional roles as needed
-- GRANT ROLE STREAMLIT_VIEWER TO ROLE DATA_INTEGRATION_ROLE;
-- GRANT ROLE STREAMLIT_VIEWER TO ROLE DBT_ANALYTICS_ROLE;

-- ==============================================================================
-- STEP 5: VERIFY ROLE CREATION
-- ==============================================================================

-- Show granted privileges
SHOW GRANTS TO ROLE STREAMLIT_VIEWER;

-- Show role grants
SHOW GRANTS OF ROLE STREAMLIT_VIEWER;

-- ==============================================================================
-- STEP 6: TEST THE ROLE
-- ==============================================================================

-- Switch to the new role to test
USE ROLE STREAMLIT_VIEWER;
USE WAREHOUSE STREAMLIT_VIEWER_WH;

-- Test basic metadata queries
SHOW USERS;       -- Should work
SHOW ROLES;       -- Should work
SHOW WAREHOUSES;  -- Should work
SHOW DATABASES;   -- Should work

-- Test ACCOUNT_USAGE access
SELECT COUNT(*) FROM SNOWFLAKE.ACCOUNT_USAGE.USERS;
SELECT COUNT(*) FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSES;
SELECT COUNT(*) FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP());

-- Test that data access is denied (should fail)
-- SELECT * FROM <any_user_table>; -- This should fail with insufficient privileges

-- ==============================================================================
-- VERIFICATION QUERIES
-- ==============================================================================

-- Switch back to ACCOUNTADMIN for verification
USE ROLE ACCOUNTADMIN;

-- Verify role hierarchy
SELECT
    GRANTEE_NAME,
    ROLE as GRANTED_ROLE,
    GRANTED_BY,
    CREATED_ON
FROM TABLE(INFORMATION_SCHEMA.APPLICABLE_ROLES(ROLE_NAME => 'STREAMLIT_VIEWER'))
ORDER BY CREATED_ON DESC;

-- Verify warehouse grants
SELECT
    PRIVILEGE,
    GRANTED_ON,
    NAME as OBJECT_NAME,
    GRANTED_TO,
    GRANTEE_NAME,
    GRANT_OPTION
FROM TABLE(INFORMATION_SCHEMA.OBJECT_PRIVILEGES(OBJECT_TYPE => 'WAREHOUSE'))
WHERE GRANTEE_NAME = 'STREAMLIT_VIEWER';

-- Verify database grants
SELECT
    PRIVILEGE,
    GRANTED_ON,
    NAME as OBJECT_NAME,
    GRANTED_TO,
    GRANTEE_NAME,
    GRANT_OPTION
FROM TABLE(INFORMATION_SCHEMA.OBJECT_PRIVILEGES(OBJECT_TYPE => 'DATABASE'))
WHERE GRANTEE_NAME = 'STREAMLIT_VIEWER';

-- ==============================================================================
-- ROLLBACK SCRIPT (IF NEEDED)
-- ==============================================================================
/*
-- To rollback this implementation, run:

USE ROLE ACCOUNTADMIN;

-- Revoke from business roles
REVOKE ROLE STREAMLIT_VIEWER FROM ROLE COMPANY_USERS;
REVOKE ROLE STREAMLIT_VIEWER FROM ROLE ADMIN_ROLE;
REVOKE ROLE STREAMLIT_VIEWER FROM ROLE BI_DEVELOPER_ROLE;

-- Drop warehouse
DROP WAREHOUSE IF EXISTS STREAMLIT_VIEWER_WH;

-- Drop role
DROP ROLE IF EXISTS STREAMLIT_VIEWER;

*/

-- ==============================================================================
-- USAGE MONITORING QUERIES
-- ==============================================================================

-- Monitor usage by the STREAMLIT_VIEWER role (run periodically)
/*
SELECT
    USER_NAME,
    ROLE_NAME,
    QUERY_TEXT,
    WAREHOUSE_NAME,
    START_TIME,
    TOTAL_ELAPSED_TIME,
    CREDITS_USED_CLOUD_SERVICES
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE ROLE_NAME = 'STREAMLIT_VIEWER'
  AND START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
ORDER BY START_TIME DESC
LIMIT 100;
*/

-- ==============================================================================
-- END OF SCRIPT
-- ==============================================================================
