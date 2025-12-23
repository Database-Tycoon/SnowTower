-- ================================================================
-- SnowDDL GitHub Integration - Stored Procedures
-- ================================================================
-- Purpose: Create stored procedures for GitHub PR automation
-- Author: SnowTower Team
-- Date: 2025-01-14
-- ================================================================

USE ROLE SYSADMIN;
USE DATABASE SNOWDDL_CONFIG;
USE SCHEMA PUBLIC;

-- ================================================================
-- 1. Procedure: Submit PR Request
-- ================================================================

CREATE OR REPLACE PROCEDURE SP_SUBMIT_PR_REQUEST(
    P_BRANCH_NAME STRING,
    P_PR_TITLE STRING,
    P_PR_DESCRIPTION STRING,
    P_FILE_NAME STRING,
    P_FILE_CONTENT STRING,
    P_CREATED_BY STRING,
    P_TARGET_BRANCH STRING DEFAULT 'main',
    P_PRIORITY INTEGER DEFAULT 5
)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Submit a new GitHub PR request with YAML content'
AS
$$
DECLARE
    v_request_id STRING;
    v_stage_path STRING;
    v_file_exists BOOLEAN DEFAULT FALSE;
    v_result STRING;
BEGIN
    -- Generate unique request ID and stage path
    v_request_id := UUID_STRING();
    v_stage_path := 'pending/' || v_request_id || '/' || P_FILE_NAME;

    -- Validate inputs
    IF (P_BRANCH_NAME IS NULL OR TRIM(P_BRANCH_NAME) = '') THEN
        RETURN 'ERROR: Branch name cannot be empty';
    END IF;

    IF (P_PR_TITLE IS NULL OR TRIM(P_PR_TITLE) = '') THEN
        RETURN 'ERROR: PR title cannot be empty';
    END IF;

    IF (P_FILE_NAME IS NULL OR TRIM(P_FILE_NAME) = '') THEN
        RETURN 'ERROR: File name cannot be empty';
    END IF;

    IF (P_FILE_CONTENT IS NULL OR TRIM(P_FILE_CONTENT) = '') THEN
        RETURN 'ERROR: File content cannot be empty';
    END IF;

    -- Validate priority range
    IF (P_PRIORITY < 1 OR P_PRIORITY > 10) THEN
        RETURN 'ERROR: Priority must be between 1 and 10';
    END IF;

    -- Check if branch name already has pending request
    SELECT COUNT(*) > 0 INTO v_file_exists
    FROM SNOWDDL_CONFIG_REQUESTS
    WHERE BRANCH_NAME = P_BRANCH_NAME
      AND STATUS IN ('PENDING', 'PROCESSING');

    IF (v_file_exists) THEN
        RETURN 'ERROR: A request for branch "' || P_BRANCH_NAME || '" is already pending or processing';
    END IF;

    -- Insert the request record
    INSERT INTO SNOWDDL_CONFIG_REQUESTS (
        REQUEST_ID,
        CREATED_BY,
        REQUEST_TYPE,
        STATUS,
        BRANCH_NAME,
        PR_TITLE,
        PR_DESCRIPTION,
        TARGET_BRANCH,
        STAGE_PATH,
        FILE_NAME,
        FILE_CONTENT,
        PRIORITY
    ) VALUES (
        v_request_id,
        P_CREATED_BY,
        'CREATE_PR',
        'PENDING',
        P_BRANCH_NAME,
        P_PR_TITLE,
        P_PR_DESCRIPTION,
        P_TARGET_BRANCH,
        v_stage_path,
        P_FILE_NAME,
        PARSE_JSON('{"content": "' || ESCAPE_UNESCAPED_QUOTES(P_FILE_CONTENT) || '"}'),
        P_PRIORITY
    );

    -- Log the submission
    INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
        REQUEST_ID,
        LEVEL,
        MESSAGE,
        PROCESSOR_ID
    ) VALUES (
        v_request_id,
        'INFO',
        'PR request submitted successfully',
        'SP_SUBMIT_PR_REQUEST'
    );

    v_result := 'SUCCESS: Request submitted with ID ' || v_request_id;
    RETURN v_result;

EXCEPTION
    WHEN OTHER THEN
        -- Log the error
        INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
            REQUEST_ID,
            LEVEL,
            MESSAGE,
            DETAILS,
            PROCESSOR_ID
        ) VALUES (
            v_request_id,
            'ERROR',
            'Failed to submit PR request: ' || SQLERRM,
            PARSE_JSON('{"sql_state": "' || SQLSTATE || '", "error_code": "' || SQLCODE || '"}'),
            'SP_SUBMIT_PR_REQUEST'
        );

        RETURN 'ERROR: Failed to submit request - ' || SQLERRM;
END;
$$;

-- ================================================================
-- 2. Procedure: Get Next Pending Request
-- ================================================================

CREATE OR REPLACE PROCEDURE SP_GET_NEXT_PENDING_REQUEST(
    P_PROCESSOR_ID STRING
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Get the next pending PR request and mark it as processing'
AS
$$
DECLARE
    v_request VARIANT;
    v_request_id STRING;
    v_row_count INTEGER;
BEGIN
    -- Find the highest priority, oldest pending request
    SELECT OBJECT_CONSTRUCT(
        'REQUEST_ID', REQUEST_ID,
        'BRANCH_NAME', BRANCH_NAME,
        'PR_TITLE', PR_TITLE,
        'PR_DESCRIPTION', PR_DESCRIPTION,
        'TARGET_BRANCH', TARGET_BRANCH,
        'FILE_NAME', FILE_NAME,
        'FILE_CONTENT', FILE_CONTENT,
        'STAGE_PATH', STAGE_PATH,
        'CREATED_BY', CREATED_BY,
        'PRIORITY', PRIORITY,
        'CREATED_AT', CREATED_AT
    ), REQUEST_ID
    INTO v_request, v_request_id
    FROM SNOWDDL_CONFIG_REQUESTS
    WHERE STATUS = 'PENDING'
      AND RETRY_COUNT < MAX_RETRIES
    ORDER BY PRIORITY DESC, CREATED_AT ASC
    LIMIT 1;

    -- If no pending requests found
    IF (v_request_id IS NULL) THEN
        RETURN PARSE_JSON('{"status": "NO_PENDING_REQUESTS", "message": "No pending requests found"}');
    END IF;

    -- Mark the request as processing
    UPDATE SNOWDDL_CONFIG_REQUESTS
    SET STATUS = 'PROCESSING',
        PROCESSOR_ID = P_PROCESSOR_ID,
        PROCESSED_AT = CURRENT_TIMESTAMP()
    WHERE REQUEST_ID = v_request_id;

    GET RESULT_SCAN(LAST_QUERY_ID()) INTO :v_row_count;

    IF (v_row_count = 0) THEN
        RETURN PARSE_JSON('{"status": "ALREADY_PROCESSING", "message": "Request was already picked up by another processor"}');
    END IF;

    -- Log the processing start
    INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
        REQUEST_ID,
        LEVEL,
        MESSAGE,
        PROCESSOR_ID
    ) VALUES (
        v_request_id,
        'INFO',
        'Request picked up for processing',
        P_PROCESSOR_ID
    );

    -- Return the request details with success status
    RETURN OBJECT_INSERT(v_request, 'status', 'SUCCESS');

EXCEPTION
    WHEN OTHER THEN
        RETURN PARSE_JSON('{"status": "ERROR", "message": "' || SQLERRM || '"}');
END;
$$;

-- ================================================================
-- 3. Procedure: Update Request Status
-- ================================================================

CREATE OR REPLACE PROCEDURE SP_UPDATE_REQUEST_STATUS(
    P_REQUEST_ID STRING,
    P_STATUS STRING,
    P_GITHUB_BRANCH_URL STRING DEFAULT NULL,
    P_GITHUB_PR_URL STRING DEFAULT NULL,
    P_GITHUB_PR_NUMBER INTEGER DEFAULT NULL,
    P_ERROR_MESSAGE STRING DEFAULT NULL,
    P_PROCESSOR_ID STRING DEFAULT NULL
)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Update the status of a PR request'
AS
$$
DECLARE
    v_old_status STRING;
    v_retry_count INTEGER;
    v_max_retries INTEGER;
    v_should_retry BOOLEAN DEFAULT FALSE;
    v_result STRING;
BEGIN
    -- Validate status
    IF (P_STATUS NOT IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')) THEN
        RETURN 'ERROR: Invalid status "' || P_STATUS || '"';
    END IF;

    -- Get current status and retry info
    SELECT STATUS, RETRY_COUNT, MAX_RETRIES
    INTO v_old_status, v_retry_count, v_max_retries
    FROM SNOWDDL_CONFIG_REQUESTS
    WHERE REQUEST_ID = P_REQUEST_ID;

    IF (v_old_status IS NULL) THEN
        RETURN 'ERROR: Request ID not found';
    END IF;

    -- Determine if this is a retry scenario
    IF (P_STATUS = 'FAILED' AND v_retry_count < v_max_retries) THEN
        v_should_retry := TRUE;
        v_retry_count := v_retry_count + 1;
    END IF;

    -- Update the request
    UPDATE SNOWDDL_CONFIG_REQUESTS
    SET STATUS = CASE
                    WHEN v_should_retry THEN 'PENDING'
                    ELSE P_STATUS
                 END,
        GITHUB_BRANCH_URL = COALESCE(P_GITHUB_BRANCH_URL, GITHUB_BRANCH_URL),
        GITHUB_PR_URL = COALESCE(P_GITHUB_PR_URL, GITHUB_PR_URL),
        GITHUB_PR_NUMBER = COALESCE(P_GITHUB_PR_NUMBER, GITHUB_PR_NUMBER),
        ERROR_MESSAGE = CASE
                           WHEN P_STATUS = 'COMPLETED' THEN NULL
                           ELSE COALESCE(P_ERROR_MESSAGE, ERROR_MESSAGE)
                        END,
        PROCESSED_AT = CASE
                          WHEN P_STATUS IN ('COMPLETED', 'FAILED', 'CANCELLED') THEN CURRENT_TIMESTAMP()
                          ELSE PROCESSED_AT
                       END,
        RETRY_COUNT = v_retry_count,
        PROCESSOR_ID = COALESCE(P_PROCESSOR_ID, PROCESSOR_ID)
    WHERE REQUEST_ID = P_REQUEST_ID;

    -- Log the status change
    INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
        REQUEST_ID,
        LEVEL,
        MESSAGE,
        DETAILS,
        PROCESSOR_ID
    ) VALUES (
        P_REQUEST_ID,
        CASE
            WHEN P_STATUS = 'COMPLETED' THEN 'INFO'
            WHEN P_STATUS = 'FAILED' THEN 'ERROR'
            ELSE 'INFO'
        END,
        'Status changed from ' || v_old_status || ' to ' ||
        CASE WHEN v_should_retry THEN 'PENDING (retry ' || v_retry_count || ')' ELSE P_STATUS END,
        CASE
            WHEN P_ERROR_MESSAGE IS NOT NULL THEN PARSE_JSON('{"error": "' || ESCAPE_UNESCAPED_QUOTES(P_ERROR_MESSAGE) || '"}')
            WHEN P_GITHUB_PR_URL IS NOT NULL THEN PARSE_JSON('{"pr_url": "' || P_GITHUB_PR_URL || '", "pr_number": ' || COALESCE(P_GITHUB_PR_NUMBER::STRING, 'null') || '}')
            ELSE NULL
        END,
        COALESCE(P_PROCESSOR_ID, 'UNKNOWN')
    );

    v_result := 'SUCCESS: Status updated to ' ||
                CASE WHEN v_should_retry THEN 'PENDING (retry ' || v_retry_count || ')' ELSE P_STATUS END;

    RETURN v_result;

EXCEPTION
    WHEN OTHER THEN
        RETURN 'ERROR: Failed to update status - ' || SQLERRM;
END;
$$;

-- ================================================================
-- 4. Procedure: Cleanup Old Requests
-- ================================================================

CREATE OR REPLACE PROCEDURE SP_CLEANUP_OLD_REQUESTS(
    P_DAYS_TO_KEEP INTEGER DEFAULT 30
)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Clean up old completed and failed requests'
AS
$$
DECLARE
    v_deleted_requests INTEGER;
    v_deleted_logs INTEGER;
    v_cutoff_date TIMESTAMP_NTZ;
    v_result STRING;
BEGIN
    v_cutoff_date := DATEADD('day', -P_DAYS_TO_KEEP, CURRENT_TIMESTAMP());

    -- Delete old processing logs first (due to foreign key)
    DELETE FROM SNOWDDL_CONFIG_PROCESSING_LOG
    WHERE TIMESTAMP < v_cutoff_date
      AND REQUEST_ID IN (
          SELECT REQUEST_ID
          FROM SNOWDDL_CONFIG_REQUESTS
          WHERE CREATED_AT < v_cutoff_date
            AND STATUS IN ('COMPLETED', 'FAILED', 'CANCELLED')
      );

    GET RESULT_SCAN(LAST_QUERY_ID()) INTO :v_deleted_logs;

    -- Delete old requests
    DELETE FROM SNOWDDL_CONFIG_REQUESTS
    WHERE CREATED_AT < v_cutoff_date
      AND STATUS IN ('COMPLETED', 'FAILED', 'CANCELLED');

    GET RESULT_SCAN(LAST_QUERY_ID()) INTO :v_deleted_requests;

    v_result := 'SUCCESS: Deleted ' || v_deleted_requests || ' old requests and ' || v_deleted_logs || ' log entries older than ' || P_DAYS_TO_KEEP || ' days';

    -- Log the cleanup
    INSERT INTO SNOWDDL_CONFIG_PROCESSING_LOG (
        LEVEL,
        MESSAGE,
        DETAILS,
        PROCESSOR_ID
    ) VALUES (
        'INFO',
        'Cleanup completed',
        PARSE_JSON('{"deleted_requests": ' || v_deleted_requests || ', "deleted_logs": ' || v_deleted_logs || ', "days_kept": ' || P_DAYS_TO_KEEP || '}'),
        'SP_CLEANUP_OLD_REQUESTS'
    );

    RETURN v_result;

EXCEPTION
    WHEN OTHER THEN
        RETURN 'ERROR: Cleanup failed - ' || SQLERRM;
END;
$$;

-- ================================================================
-- 5. Procedure: Get Request Status
-- ================================================================

CREATE OR REPLACE PROCEDURE SP_GET_REQUEST_STATUS(
    P_REQUEST_ID STRING DEFAULT NULL,
    P_BRANCH_NAME STRING DEFAULT NULL
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Get the status of a PR request by ID or branch name'
AS
$$
DECLARE
    v_request VARIANT;
    v_where_clause STRING;
BEGIN
    -- Validate inputs
    IF (P_REQUEST_ID IS NULL AND P_BRANCH_NAME IS NULL) THEN
        RETURN PARSE_JSON('{"status": "ERROR", "message": "Either REQUEST_ID or BRANCH_NAME must be provided"}');
    END IF;

    -- Build the query based on provided parameters
    IF (P_REQUEST_ID IS NOT NULL) THEN
        SELECT OBJECT_CONSTRUCT(
            'REQUEST_ID', REQUEST_ID,
            'CREATED_AT', CREATED_AT,
            'CREATED_BY', CREATED_BY,
            'STATUS', STATUS,
            'BRANCH_NAME', BRANCH_NAME,
            'PR_TITLE', PR_TITLE,
            'PR_DESCRIPTION', PR_DESCRIPTION,
            'TARGET_BRANCH', TARGET_BRANCH,
            'FILE_NAME', FILE_NAME,
            'GITHUB_BRANCH_URL', GITHUB_BRANCH_URL,
            'GITHUB_PR_URL', GITHUB_PR_URL,
            'GITHUB_PR_NUMBER', GITHUB_PR_NUMBER,
            'PROCESSED_AT', PROCESSED_AT,
            'ERROR_MESSAGE', ERROR_MESSAGE,
            'RETRY_COUNT', RETRY_COUNT,
            'PRIORITY', PRIORITY
        ) INTO v_request
        FROM SNOWDDL_CONFIG_REQUESTS
        WHERE REQUEST_ID = P_REQUEST_ID;
    ELSE
        SELECT OBJECT_CONSTRUCT(
            'REQUEST_ID', REQUEST_ID,
            'CREATED_AT', CREATED_AT,
            'CREATED_BY', CREATED_BY,
            'STATUS', STATUS,
            'BRANCH_NAME', BRANCH_NAME,
            'PR_TITLE', PR_TITLE,
            'PR_DESCRIPTION', PR_DESCRIPTION,
            'TARGET_BRANCH', TARGET_BRANCH,
            'FILE_NAME', FILE_NAME,
            'GITHUB_BRANCH_URL', GITHUB_BRANCH_URL,
            'GITHUB_PR_URL', GITHUB_PR_URL,
            'GITHUB_PR_NUMBER', GITHUB_PR_NUMBER,
            'PROCESSED_AT', PROCESSED_AT,
            'ERROR_MESSAGE', ERROR_MESSAGE,
            'RETRY_COUNT', RETRY_COUNT,
            'PRIORITY', PRIORITY
        ) INTO v_request
        FROM SNOWDDL_CONFIG_REQUESTS
        WHERE BRANCH_NAME = P_BRANCH_NAME
        ORDER BY CREATED_AT DESC
        LIMIT 1;
    END IF;

    -- Check if request was found
    IF (v_request IS NULL) THEN
        RETURN PARSE_JSON('{"status": "NOT_FOUND", "message": "No request found with the provided criteria"}');
    END IF;

    -- Return success with request details
    RETURN OBJECT_INSERT(v_request, 'status', 'SUCCESS');

EXCEPTION
    WHEN OTHER THEN
        RETURN PARSE_JSON('{"status": "ERROR", "message": "' || SQLERRM || '"}');
END;
$$;

-- ================================================================
-- Grant Permissions on Stored Procedures
-- ================================================================

GRANT USAGE ON PROCEDURE SP_SUBMIT_PR_REQUEST(STRING, STRING, STRING, STRING, STRING, STRING, STRING, INTEGER) TO ROLE SNOWDDL_CONFIG_MANAGER;
GRANT USAGE ON PROCEDURE SP_GET_NEXT_PENDING_REQUEST(STRING) TO ROLE SNOWDDL_CONFIG_MANAGER;
GRANT USAGE ON PROCEDURE SP_UPDATE_REQUEST_STATUS(STRING, STRING, STRING, STRING, INTEGER, STRING, STRING) TO ROLE SNOWDDL_CONFIG_MANAGER;
GRANT USAGE ON PROCEDURE SP_CLEANUP_OLD_REQUESTS(INTEGER) TO ROLE SNOWDDL_CONFIG_MANAGER;
GRANT USAGE ON PROCEDURE SP_GET_REQUEST_STATUS(STRING, STRING) TO ROLE SNOWDDL_CONFIG_READER;

-- ================================================================
-- Test the Procedures
-- ================================================================

-- Test submitting a request (uncomment to test)
/*
CALL SP_SUBMIT_PR_REQUEST(
    'feature/test-branch',
    'Test PR Creation',
    'This is a test PR created by the stored procedure',
    'test_config.yaml',
    'version: 1.0\nconfig:\n  test: true',
    'system_test',
    'main',
    5
);

-- Test getting the request status
CALL SP_GET_REQUEST_STATUS(NULL, 'feature/test-branch');

-- Test getting next pending request
CALL SP_GET_NEXT_PENDING_REQUEST('test_processor');
*/
