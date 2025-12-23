-- ================================================================
-- SnowDDL GitHub Integration - Task Scheduler
-- ================================================================
-- Purpose: Create Snowflake tasks for automated GitHub PR processing
-- Author: SnowTower Team
-- Date: 2025-01-14
-- ================================================================

USE ROLE SYSADMIN;
USE DATABASE SNOWDDL_CONFIG;
USE SCHEMA PUBLIC;

-- ================================================================
-- 1. Create Task for Processing GitHub PR Requests
-- ================================================================

-- First, create a stored procedure that will be called by the task
CREATE OR REPLACE PROCEDURE SP_PROCESS_GITHUB_REQUESTS()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Process pending GitHub PR requests - called by Snowflake task'
AS
$$
DECLARE
    v_pending_count INTEGER;
    v_processing_count INTEGER;
    v_failed_count INTEGER;
    v_stale_count INTEGER;
    v_result STRING;
    v_config_value STRING;
    v_max_processing_time INTEGER DEFAULT 30; -- minutes
    v_stale_cutoff TIMESTAMP_NTZ;
BEGIN
    -- Get configuration for stale request handling
    SELECT CONFIG_VALUE INTO v_config_value
    FROM SNOWDDL_GITHUB_CONFIG
    WHERE CONFIG_KEY = 'PROCESSOR_INTERVAL_MINUTES';

    IF (v_config_value IS NOT NULL) THEN
        v_max_processing_time := v_config_value::INTEGER * 6; -- 6 intervals = stale
    END IF;

    v_stale_cutoff := DATEADD('minute', -v_max_processing_time, CURRENT_TIMESTAMP());

    -- Count current request states
    SELECT
        SUM(CASE WHEN STATUS = 'PENDING' THEN 1 ELSE 0 END),
        SUM(CASE WHEN STATUS = 'PROCESSING' THEN 1 ELSE 0 END),
        SUM(CASE WHEN STATUS = 'FAILED' AND RETRY_COUNT >= MAX_RETRIES THEN 1 ELSE 0 END)
    INTO v_pending_count, v_processing_count, v_failed_count
    FROM SNOWDDL_CONFIG_REQUESTS
    WHERE CREATED_AT >= DATEADD('day', -1, CURRENT_TIMESTAMP());

    -- Reset stale processing requests back to pending
    UPDATE SNOWDDL_CONFIG_REQUESTS
    SET STATUS = 'PENDING',
        PROCESSOR_ID = NULL,
        ERROR_MESSAGE = 'Reset from stale PROCESSING state after ' || v_max_processing_time || ' minutes'
    WHERE STATUS = 'PROCESSING'
      AND PROCESSED_AT < v_stale_cutoff;

    GET RESULT_SCAN(LAST_QUERY_ID()) INTO :v_stale_count;

    -- Log stale request resets if any
    IF (v_stale_count > 0) THEN
        INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
            LEVEL,
            MESSAGE,
            DETAILS,
            PROCESSOR_ID
        ) VALUES (
            'WARN',
            'Reset ' || v_stale_count || ' stale processing requests back to pending',
            PARSE_JSON('{"stale_count": ' || v_stale_count || ', "max_processing_minutes": ' || v_max_processing_time || '}'),
            'SP_PROCESS_GITHUB_REQUESTS'
        );
    END IF;

    -- Log current status
    INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
        LEVEL,
        MESSAGE,
        DETAILS,
        PROCESSOR_ID
    ) VALUES (
        'INFO',
        'GitHub request processing task executed',
        PARSE_JSON('{"pending": ' || v_pending_count || ', "processing": ' || v_processing_count || ', "failed": ' || v_failed_count || ', "stale_reset": ' || v_stale_count || '}'),
        'SP_PROCESS_GITHUB_REQUESTS'
    );

    v_result := 'Task executed - Pending: ' || v_pending_count || ', Processing: ' || v_processing_count || ', Failed: ' || v_failed_count || ', Stale Reset: ' || v_stale_count;

    RETURN v_result;

EXCEPTION
    WHEN OTHER THEN
        -- Log the error
        INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
            LEVEL,
            MESSAGE,
            DETAILS,
            PROCESSOR_ID
        ) VALUES (
            'ERROR',
            'GitHub processing task failed: ' || SQLERRM,
            PARSE_JSON('{"sql_state": "' || SQLSTATE || '", "error_code": "' || SQLCODE || '"}'),
            'SP_PROCESS_GITHUB_REQUESTS'
        );

        RETURN 'ERROR: Task execution failed - ' || SQLERRM;
END;
$$;

-- ================================================================
-- 2. Create the Snowflake Task
-- ================================================================

-- Create task to process GitHub requests every 5 minutes
CREATE OR REPLACE TASK TASK_PROCESS_GITHUB_REQUESTS
    WAREHOUSE = 'COMPUTE_WH'
    SCHEDULE = 'USING CRON 0/5 * * * * UTC'  -- Every 5 minutes
    COMMENT = 'Process pending GitHub PR requests and reset stale processing requests'
AS
    CALL SP_PROCESS_GITHUB_REQUESTS();

-- ================================================================
-- 3. Create Task for Cleanup (Daily)
-- ================================================================

-- Create task to cleanup old requests daily at 2 AM UTC
CREATE OR REPLACE TASK TASK_CLEANUP_OLD_REQUESTS
    WAREHOUSE = 'COMPUTE_WH'
    SCHEDULE = 'USING CRON 0 2 * * * UTC'  -- Daily at 2 AM UTC
    COMMENT = 'Clean up old completed and failed GitHub PR requests'
AS
    CALL SP_CLEANUP_OLD_REQUESTS(30);  -- Keep 30 days of history

-- ================================================================
-- 4. Create Task for Health Monitoring (Hourly)
-- ================================================================

CREATE OR REPLACE PROCEDURE SP_MONITOR_GITHUB_HEALTH()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Monitor GitHub integration health and alert on issues'
AS
$$
DECLARE
    v_old_pending_count INTEGER;
    v_high_retry_count INTEGER;
    v_recent_errors INTEGER;
    v_alert_level STRING DEFAULT 'INFO';
    v_alert_message STRING;
    v_details VARIANT;
    v_result STRING;
BEGIN
    -- Check for requests pending too long (> 1 hour)
    SELECT COUNT(*)
    INTO v_old_pending_count
    FROM SNOWDDL_CONFIG_REQUESTS
    WHERE STATUS = 'PENDING'
      AND CREATED_AT < DATEADD('hour', -1, CURRENT_TIMESTAMP());

    -- Check for requests with high retry counts
    SELECT COUNT(*)
    INTO v_high_retry_count
    FROM SNOWDDL_CONFIG_REQUESTS
    WHERE RETRY_COUNT >= 2
      AND STATUS IN ('PENDING', 'PROCESSING')
      AND CREATED_AT >= DATEADD('day', -1, CURRENT_TIMESTAMP());

    -- Check for recent errors in processing logs
    SELECT COUNT(*)
    INTO v_recent_errors
    FROM SNOWDDL_CONFIG_PROCESSING_LOG
    WHERE LEVEL = 'ERROR'
      AND TIMESTAMP >= DATEADD('hour', -1, CURRENT_TIMESTAMP());

    -- Determine alert level and message
    IF (v_old_pending_count > 0 OR v_high_retry_count > 3 OR v_recent_errors > 5) THEN
        v_alert_level := 'ERROR';
        v_alert_message := 'GitHub integration health issues detected';
    ELSIF (v_high_retry_count > 0 OR v_recent_errors > 0) THEN
        v_alert_level := 'WARN';
        v_alert_message := 'GitHub integration performance degraded';
    ELSE
        v_alert_level := 'INFO';
        v_alert_message := 'GitHub integration healthy';
    END IF;

    -- Create details object
    v_details := PARSE_JSON('{"old_pending": ' || v_old_pending_count || ', "high_retry": ' || v_high_retry_count || ', "recent_errors": ' || v_recent_errors || '}');

    -- Log the health check
    INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
        LEVEL,
        MESSAGE,
        DETAILS,
        PROCESSOR_ID
    ) VALUES (
        v_alert_level,
        v_alert_message,
        v_details,
        'SP_MONITOR_GITHUB_HEALTH'
    );

    v_result := v_alert_level || ': ' || v_alert_message || ' - Old Pending: ' || v_old_pending_count || ', High Retry: ' || v_high_retry_count || ', Recent Errors: ' || v_recent_errors;

    RETURN v_result;

EXCEPTION
    WHEN OTHER THEN
        RETURN 'ERROR: Health monitoring failed - ' || SQLERRM;
END;
$$;

-- Create health monitoring task (hourly)
CREATE OR REPLACE TASK TASK_MONITOR_GITHUB_HEALTH
    WAREHOUSE = 'COMPUTE_WH'
    SCHEDULE = 'USING CRON 0 * * * * UTC'  -- Every hour
    COMMENT = 'Monitor GitHub integration health and log alerts'
AS
    CALL SP_MONITOR_GITHUB_HEALTH();

-- ================================================================
-- 5. Grant Permissions and Start Tasks
-- ================================================================

-- Grant permissions on tasks
GRANT MONITOR ON TASK TASK_PROCESS_GITHUB_REQUESTS TO ROLE SNOWDDL_CONFIG_READER;
GRANT MONITOR ON TASK TASK_CLEANUP_OLD_REQUESTS TO ROLE SNOWDDL_CONFIG_READER;
GRANT MONITOR ON TASK TASK_MONITOR_GITHUB_HEALTH TO ROLE SNOWDDL_CONFIG_READER;

GRANT OPERATE ON TASK TASK_PROCESS_GITHUB_REQUESTS TO ROLE SNOWDDL_CONFIG_MANAGER;
GRANT OPERATE ON TASK TASK_CLEANUP_OLD_REQUESTS TO ROLE SNOWDDL_CONFIG_MANAGER;
GRANT OPERATE ON TASK TASK_MONITOR_GITHUB_HEALTH TO ROLE SNOWDDL_CONFIG_MANAGER;

-- Grant usage on procedures
GRANT USAGE ON PROCEDURE SP_PROCESS_GITHUB_REQUESTS() TO ROLE SNOWDDL_CONFIG_MANAGER;
GRANT USAGE ON PROCEDURE SP_MONITOR_GITHUB_HEALTH() TO ROLE SNOWDDL_CONFIG_MANAGER;

-- ================================================================
-- 6. Task Management Commands
-- ================================================================

-- Start the tasks (uncomment when ready to activate)
/*
ALTER TASK TASK_PROCESS_GITHUB_REQUESTS RESUME;
ALTER TASK TASK_CLEANUP_OLD_REQUESTS RESUME;
ALTER TASK TASK_MONITOR_GITHUB_HEALTH RESUME;
*/

-- ================================================================
-- 7. Monitoring Queries
-- ================================================================

-- Create view for task monitoring
CREATE OR REPLACE VIEW V_TASK_HISTORY AS
SELECT
    NAME AS TASK_NAME,
    DATABASE_NAME,
    SCHEMA_NAME,
    STATE,
    SCHEDULED_TIME,
    COMPLETED_TIME,
    RETURN_VALUE,
    ERROR_CODE,
    ERROR_MESSAGE,
    DATEDIFF('second', SCHEDULED_TIME, COMPLETED_TIME) AS DURATION_SECONDS
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE DATABASE_NAME = 'SNOWDDL_CONFIG'
  AND NAME IN ('TASK_PROCESS_GITHUB_REQUESTS', 'TASK_CLEANUP_OLD_REQUESTS', 'TASK_MONITOR_GITHUB_HEALTH')
ORDER BY SCHEDULED_TIME DESC;

GRANT SELECT ON VIEW V_TASK_HISTORY TO ROLE SNOWDDL_CONFIG_READER;

-- ================================================================
-- Verification and Status Queries
-- ================================================================

-- Check task status
SELECT
    NAME,
    STATE,
    SCHEDULE,
    WAREHOUSE,
    COMMENT
FROM INFORMATION_SCHEMA.TASKS
WHERE DATABASE_NAME = 'SNOWDDL_CONFIG'
  AND SCHEMA_NAME = 'PUBLIC'
  AND NAME LIKE 'TASK_%'
ORDER BY NAME;

-- Show recent task executions
SELECT * FROM V_TASK_HISTORY
WHERE SCHEDULED_TIME >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
ORDER BY SCHEDULED_TIME DESC;

-- Show current request queue status
SELECT
    STATUS,
    COUNT(*) AS COUNT,
    MIN(CREATED_AT) AS OLDEST_REQUEST,
    MAX(CREATED_AT) AS NEWEST_REQUEST
FROM SNOWDDL_CONFIG_REQUESTS
WHERE CREATED_AT >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY STATUS
ORDER BY STATUS;
