#!/usr/bin/env python3
"""
Setup script for SnowDDL GitHub Integration

This script sets up the complete GitHub integration infrastructure including:
- Snowflake tables, stages, and stored procedures
- Task scheduling
- Configuration validation
- Environment setup

Author: SnowTower Team
Date: 2025-01-14
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from snowddl_core import SnowflakeConnection

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GitHubIntegrationSetup:
    """Setup manager for GitHub integration"""

    def __init__(self, snowflake_connection=None):
        """Initialize with optional Snowflake connection"""
        self.connection = snowflake_connection or self._create_connection()
        self.sql_scripts_dir = Path(__file__).parent.parent / "sql"

    def _create_connection(self):
        """Create Snowflake connection using environment variables"""
        try:
            return SnowflakeConnection(
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                user=os.getenv("SNOWFLAKE_USER"),
                password=os.getenv("SNOWFLAKE_PASSWORD"),
                private_key_path=os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"),
                role=os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
                database=os.getenv("SNOWFLAKE_DATABASE", "SNOWDDL_CONFIG"),
                schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
            )
        except Exception as e:
            logger.error(f"Failed to create Snowflake connection: {e}")
            raise

    def validate_environment(self) -> bool:
        """Validate that all required environment variables are set"""
        logger.info("Validating environment configuration...")

        required_vars = [
            "SNOWFLAKE_ACCOUNT",
            "SNOWFLAKE_USER",
            "GITHUB_TOKEN",
            "GITHUB_REPO_OWNER",
            "GITHUB_REPO_NAME",
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
            return False

        # Check authentication method
        if not (
            os.getenv("SNOWFLAKE_PASSWORD") or os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
        ):
            logger.error(
                "Either SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH must be provided"
            )
            return False

        logger.info("✅ Environment validation passed")
        return True

    def run_sql_script(self, script_path: Path) -> bool:
        """Run a SQL script file"""
        logger.info(f"Executing SQL script: {script_path.name}")

        try:
            with open(script_path, "r") as f:
                sql_content = f.read()

            # Split script into individual statements
            statements = [
                stmt.strip() for stmt in sql_content.split(";") if stmt.strip()
            ]

            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                for i, statement in enumerate(statements, 1):
                    # Skip comments and empty statements
                    if statement.startswith("--") or not statement:
                        continue

                    try:
                        logger.debug(f"Executing statement {i}/{len(statements)}")
                        cursor.execute(statement)
                        logger.debug(f"Statement {i} completed successfully")

                    except Exception as e:
                        logger.error(f"Failed to execute statement {i}: {e}")
                        logger.debug(f"Failed statement: {statement[:200]}...")
                        raise

                cursor.close()

            logger.info(f"✅ Successfully executed {script_path.name}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to execute {script_path.name}: {e}")
            return False

    def setup_infrastructure(self) -> bool:
        """Set up the Snowflake infrastructure"""
        logger.info("Setting up Snowflake infrastructure...")

        scripts_to_run = [
            "01_create_stage_infrastructure.sql",
            "02_create_stored_procedures.sql",
            "03_create_task_scheduler.sql",
        ]

        for script_name in scripts_to_run:
            script_path = self.sql_scripts_dir / script_name

            if not script_path.exists():
                logger.error(f"SQL script not found: {script_path}")
                return False

            if not self.run_sql_script(script_path):
                logger.error(f"Failed to execute {script_name}")
                return False

        logger.info("✅ Infrastructure setup completed")
        return True

    def configure_github_settings(self) -> bool:
        """Configure GitHub settings in Snowflake"""
        logger.info("Configuring GitHub settings...")

        settings = {
            "GITHUB_REPO_OWNER": os.getenv("GITHUB_REPO_OWNER"),
            "GITHUB_REPO_NAME": os.getenv("GITHUB_REPO_NAME"),
            "GITHUB_BASE_BRANCH": os.getenv("GITHUB_BASE_BRANCH", "main"),
            "GITHUB_API_URL": os.getenv("GITHUB_API_URL", "https://api.github.com"),
            "PR_AUTO_MERGE": os.getenv("GITHUB_AUTO_MERGE", "false"),
            "PR_REVIEWER_TEAMS": os.getenv("GITHUB_REVIEWER_TEAMS", "[]"),
            "PROCESSOR_INTERVAL_MINUTES": os.getenv("PROCESSOR_INTERVAL_MINUTES", "5"),
            "MAX_FILES_PER_PR": os.getenv("GITHUB_MAX_FILES_PER_PR", "10"),
        }

        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                for key, value in settings.items():
                    update_sql = """
                        UPDATE SNOWDDL_GITHUB_CONFIG
                        SET CONFIG_VALUE = %s,
                            UPDATED_AT = CURRENT_TIMESTAMP(),
                            UPDATED_BY = %s
                        WHERE CONFIG_KEY = %s
                    """

                    cursor.execute(
                        update_sql, (value, os.getenv("SNOWFLAKE_USER"), key)
                    )

                cursor.close()

            logger.info("✅ GitHub settings configured")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to configure GitHub settings: {e}")
            return False

    def verify_setup(self) -> bool:
        """Verify that the setup was successful"""
        logger.info("Verifying setup...")

        verification_queries = [
            (
                "Stage exists",
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.STAGES WHERE STAGE_NAME = 'SNOWDDL_CONFIG_STAGE'",
            ),
            (
                "Requests table exists",
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SNOWDDL_CONFIG_REQUESTS'",
            ),
            (
                "Procedures exist",
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.PROCEDURES WHERE PROCEDURE_NAME LIKE 'SP_%'",
            ),
            (
                "Tasks exist",
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TASKS WHERE NAME LIKE 'TASK_%'",
            ),
            ("Configuration loaded", "SELECT COUNT(*) FROM SNOWDDL_GITHUB_CONFIG"),
        ]

        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                for description, query in verification_queries:
                    cursor.execute(query)
                    result = cursor.fetchone()
                    count = result[0] if result else 0

                    if count > 0:
                        logger.info(f"✅ {description}: {count} found")
                    else:
                        logger.error(f"❌ {description}: No items found")
                        return False

                cursor.close()

            logger.info("✅ Setup verification completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Setup verification failed: {e}")
            return False

    def enable_tasks(self) -> bool:
        """Enable the Snowflake tasks"""
        logger.info("Enabling Snowflake tasks...")

        tasks = [
            "TASK_PROCESS_GITHUB_REQUESTS",
            "TASK_CLEANUP_OLD_REQUESTS",
            "TASK_MONITOR_GITHUB_HEALTH",
        ]

        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                for task in tasks:
                    cursor.execute(f"ALTER TASK {task} RESUME")
                    logger.info(f"✅ Enabled task: {task}")

                cursor.close()

            logger.info("✅ All tasks enabled")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to enable tasks: {e}")
            return False

    def create_sample_request(self) -> bool:
        """Create a sample PR request for testing"""
        logger.info("Creating sample PR request...")

        sample_yaml = """
version: 1.0
# Sample SnowDDL configuration for testing GitHub integration
databases:
  GITHUB_INTEGRATION_TEST:
    comment: "Test database for GitHub integration"
    schemas:
      PUBLIC:
        comment: "Public schema for testing"

users:
  GITHUB_TEST_USER:
    login_name: "github_test_user"
    comment: "Test user for GitHub integration"
    must_change_password: false
    disabled: false
    type: "PERSON"
"""

        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                cursor.callproc(
                    "SP_SUBMIT_PR_REQUEST",
                    [
                        "test/github-integration-setup",
                        "Test GitHub Integration Setup",
                        "This PR tests the GitHub integration system setup",
                        "test_github_integration.yaml",
                        sample_yaml,
                        os.getenv("SNOWFLAKE_USER", "setup_script"),
                        "main",
                        7,  # High priority for testing
                    ],
                )

                result = cursor.fetchone()
                cursor.close()

                if result and result[0].startswith("SUCCESS"):
                    logger.info(f"✅ Sample request created: {result[0]}")
                    return True
                else:
                    logger.error(
                        f"❌ Failed to create sample request: {result[0] if result else 'Unknown error'}"
                    )
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to create sample request: {e}")
            return False

    def run_complete_setup(
        self, enable_tasks: bool = False, create_sample: bool = False
    ) -> bool:
        """Run the complete setup process"""
        logger.info("🚀 Starting GitHub integration setup...")

        steps = [
            ("Validate environment", self.validate_environment),
            ("Setup infrastructure", self.setup_infrastructure),
            ("Configure GitHub settings", self.configure_github_settings),
            ("Verify setup", self.verify_setup),
        ]

        if enable_tasks:
            steps.append(("Enable tasks", self.enable_tasks))

        if create_sample:
            steps.append(("Create sample request", self.create_sample_request))

        for step_name, step_func in steps:
            logger.info(f"📋 {step_name}...")
            if not step_func():
                logger.error(f"❌ Setup failed at step: {step_name}")
                return False

        logger.info("🎉 GitHub integration setup completed successfully!")
        return True

    def cleanup(self) -> bool:
        """Clean up the GitHub integration infrastructure"""
        logger.info("🧹 Cleaning up GitHub integration infrastructure...")

        cleanup_statements = [
            "DROP TASK IF EXISTS TASK_PROCESS_GITHUB_REQUESTS",
            "DROP TASK IF EXISTS TASK_CLEANUP_OLD_REQUESTS",
            "DROP TASK IF EXISTS TASK_MONITOR_GITHUB_HEALTH",
            "DROP PROCEDURE IF EXISTS SP_SUBMIT_PR_REQUEST(STRING, STRING, STRING, STRING, STRING, STRING, STRING, INTEGER)",
            "DROP PROCEDURE IF EXISTS SP_GET_NEXT_PENDING_REQUEST(STRING)",
            "DROP PROCEDURE IF EXISTS SP_UPDATE_REQUEST_STATUS(STRING, STRING, STRING, STRING, INTEGER, STRING, STRING)",
            "DROP PROCEDURE IF EXISTS SP_CLEANUP_OLD_REQUESTS(INTEGER)",
            "DROP PROCEDURE IF EXISTS SP_GET_REQUEST_STATUS(STRING, STRING)",
            "DROP PROCEDURE IF EXISTS SP_PROCESS_GITHUB_REQUESTS()",
            "DROP PROCEDURE IF EXISTS SP_MONITOR_GITHUB_HEALTH()",
            "DROP VIEW IF EXISTS V_PENDING_REQUESTS",
            "DROP VIEW IF EXISTS V_FAILED_REQUESTS",
            "DROP VIEW IF EXISTS V_REQUEST_SUMMARY",
            "DROP VIEW IF EXISTS V_TASK_HISTORY",
            "DROP TABLE IF EXISTS SNOWDDL_CONFIG_PROCESSING_LOG",
            "DROP TABLE IF EXISTS SNOWDDL_CONFIG_REQUESTS",
            "DROP TABLE IF EXISTS SNOWDDL_GITHUB_CONFIG",
            "DROP STAGE IF EXISTS SNOWDDL_CONFIG_STAGE",
        ]

        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                for statement in cleanup_statements:
                    try:
                        cursor.execute(statement)
                        logger.debug(f"Executed: {statement}")
                    except Exception as e:
                        logger.warning(
                            f"Cleanup statement failed (may not exist): {statement} - {e}"
                        )

                cursor.close()

            logger.info("✅ Cleanup completed")
            return True

        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Setup SnowDDL GitHub Integration")
    parser.add_argument(
        "--cleanup", action="store_true", help="Clean up existing installation"
    )
    parser.add_argument(
        "--enable-tasks", action="store_true", help="Enable Snowflake tasks after setup"
    )
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create a sample PR request for testing",
    )
    parser.add_argument(
        "--verify-only", action="store_true", help="Only run verification checks"
    )

    args = parser.parse_args()

    try:
        setup = GitHubIntegrationSetup()

        if args.cleanup:
            success = setup.cleanup()
        elif args.verify_only:
            success = setup.verify_setup()
        else:
            success = setup.run_complete_setup(
                enable_tasks=args.enable_tasks, create_sample=args.create_sample
            )

        if success:
            logger.info("🎉 Operation completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Operation failed!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Setup script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
