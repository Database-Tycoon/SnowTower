#!/usr/bin/env python3
"""
GitHub Integration Management Script

This script provides a unified interface for managing the GitHub integration system:
- Setup and teardown infrastructure
- Monitor request processing
- Deploy the monitor process
- Check system health

Author: SnowTower Team
Date: 2025-01-14
"""

import os
import sys
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


def setup_infrastructure(args):
    """Setup GitHub integration infrastructure"""
    from setup_github_integration import GitHubIntegrationSetup

    logger.info("🚀 Setting up GitHub integration infrastructure...")

    try:
        setup = GitHubIntegrationSetup()
        success = setup.run_complete_setup(
            enable_tasks=args.enable_tasks, create_sample=args.create_sample
        )

        if success:
            logger.info("✅ Infrastructure setup completed successfully!")
            return 0
        else:
            logger.error("❌ Infrastructure setup failed!")
            return 1

    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return 1


def teardown_infrastructure(args):
    """Teardown GitHub integration infrastructure"""
    from setup_github_integration import GitHubIntegrationSetup

    logger.info("🧹 Tearing down GitHub integration infrastructure...")

    if not args.confirm:
        response = input(
            "This will delete all GitHub integration infrastructure. Continue? (y/N): "
        )
        if response.lower() != "y":
            logger.info("Operation cancelled")
            return 0

    try:
        setup = GitHubIntegrationSetup()
        success = setup.cleanup()

        if success:
            logger.info("✅ Infrastructure teardown completed successfully!")
            return 0
        else:
            logger.error("❌ Infrastructure teardown failed!")
            return 1

    except Exception as e:
        logger.error(f"❌ Teardown failed: {e}")
        return 1


def monitor_requests(args):
    """Monitor GitHub PR requests"""
    try:
        connection = SnowflakeConnection(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            private_key_path=os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"),
            role=os.getenv("SNOWFLAKE_ROLE", "SNOWDDL_CONFIG_MANAGER"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SNOWDDL_CONFIG"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
        )

        with connection.get_connection() as conn:
            cursor = conn.cursor()

            if args.pending:
                logger.info("📋 Pending Requests:")
                cursor.execute(
                    "SELECT * FROM V_PENDING_REQUESTS ORDER BY PRIORITY DESC, CREATED_AT ASC"
                )
                results = cursor.fetchall()

                if results:
                    print(
                        f"{'Request ID':<40} {'Branch Name':<30} {'Priority':<8} {'Age (min)':<10}"
                    )
                    print("-" * 100)
                    for row in results:
                        print(f"{row[0]:<40} {row[2]:<30} {row[7]:<8} {row[8]:<10}")
                else:
                    print("No pending requests found.")

            elif args.failed:
                logger.info("❌ Failed Requests:")
                cursor.execute(
                    "SELECT * FROM V_FAILED_REQUESTS ORDER BY CREATED_AT DESC LIMIT 20"
                )
                results = cursor.fetchall()

                if results:
                    print(
                        f"{'Request ID':<40} {'Branch Name':<30} {'Status':<12} {'Error':<50}"
                    )
                    print("-" * 140)
                    for row in results:
                        error = (
                            (row[6] or "")[:47] + "..."
                            if row[6] and len(row[6]) > 50
                            else (row[6] or "")
                        )
                        print(f"{row[0]:<40} {row[2]:<30} {row[4]:<12} {error:<50}")
                else:
                    print("No failed requests found.")

            elif args.summary:
                logger.info("📊 Request Summary:")
                cursor.execute(
                    """
                    SELECT
                        STATUS,
                        COUNT(*) as COUNT,
                        MIN(CREATED_AT) as OLDEST,
                        MAX(CREATED_AT) as NEWEST
                    FROM SNOWDDL_CONFIG_REQUESTS
                    WHERE CREATED_AT >= DATEADD('day', -7, CURRENT_TIMESTAMP())
                    GROUP BY STATUS
                    ORDER BY STATUS
                """
                )
                results = cursor.fetchall()

                if results:
                    print(f"{'Status':<12} {'Count':<8} {'Oldest':<20} {'Newest':<20}")
                    print("-" * 68)
                    for row in results:
                        oldest = (
                            row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else "N/A"
                        )
                        newest = (
                            row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else "N/A"
                        )
                        print(f"{row[0]:<12} {row[1]:<8} {oldest:<20} {newest:<20}")
                else:
                    print("No requests found in the last 7 days.")

            elif args.status and args.request_id:
                logger.info(f"🔍 Request Status for ID: {args.request_id}")
                cursor.callproc("SP_GET_REQUEST_STATUS", [args.request_id, None])
                result = cursor.fetchone()

                if result:
                    import json

                    status_data = (
                        json.loads(result[0])
                        if isinstance(result[0], str)
                        else result[0]
                    )

                    if status_data.get("status") == "SUCCESS":
                        print(f"Request ID: {status_data['REQUEST_ID']}")
                        print(f"Status: {status_data['STATUS']}")
                        print(f"Branch: {status_data['BRANCH_NAME']}")
                        print(f"PR Title: {status_data['PR_TITLE']}")
                        print(f"Created: {status_data['CREATED_AT']}")
                        print(f"Created By: {status_data['CREATED_BY']}")

                        if status_data.get("GITHUB_PR_URL"):
                            print(f"GitHub PR: {status_data['GITHUB_PR_URL']}")

                        if status_data.get("ERROR_MESSAGE"):
                            print(f"Error: {status_data['ERROR_MESSAGE']}")
                    else:
                        print(f"Error: {status_data.get('message', 'Unknown error')}")
                else:
                    print("No result returned from status query.")

            cursor.close()

        return 0

    except Exception as e:
        logger.error(f"❌ Failed to monitor requests: {e}")
        return 1


def run_monitor(args):
    """Run the GitHub monitor process"""
    from github_integration.github_monitor import main as monitor_main

    logger.info("🔄 Starting GitHub monitor process...")

    try:
        # Set up arguments for the monitor
        monitor_args = []

        if args.once:
            monitor_args.append("--once")
        else:
            monitor_args.extend(["--interval", str(args.interval)])

        if args.debug:
            monitor_args.append("--debug")

        # Save original argv and replace with our arguments
        original_argv = sys.argv
        sys.argv = ["github_monitor.py"] + monitor_args

        try:
            monitor_main()
            return 0
        finally:
            # Restore original argv
            sys.argv = original_argv

    except Exception as e:
        logger.error(f"❌ Monitor process failed: {e}")
        return 1


def deploy_monitor(args):
    """Deploy the GitHub monitor process"""
    from deploy_github_monitor import GitHubMonitorDeployment

    logger.info("🚀 Deploying GitHub monitor...")

    try:
        deployment = GitHubMonitorDeployment()

        if args.docker:
            deployment.create_docker_setup()
            logger.info("✅ Docker deployment files created")

        if args.systemd:
            deployment.create_systemd_service()
            logger.info("✅ Systemd service file created")

        if args.lambda_deploy:
            deployment.create_lambda_package()
            logger.info("✅ Lambda deployment package created")

        if args.all_deploy:
            deployment.deploy_all()
            logger.info("✅ All deployment artifacts created")

        if not any([args.docker, args.systemd, args.lambda_deploy, args.all_deploy]):
            # Default: create requirements and runner
            deployment.create_requirements_file()
            deployment.create_runner_script()
            deployment.create_deployment_guide()
            logger.info("✅ Basic deployment files created")

        return 0

    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        return 1


def health_check(args):
    """Check system health"""
    logger.info("🏥 Running health check...")

    try:
        # Check Snowflake connection
        logger.info("Checking Snowflake connection...")
        connection = SnowflakeConnection(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            private_key_path=os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"),
            role=os.getenv("SNOWFLAKE_ROLE", "SNOWDDL_CONFIG_MANAGER"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SNOWDDL_CONFIG"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
        )

        with connection.get_connection() as conn:
            cursor = conn.cursor()

            # Check infrastructure
            logger.info("Checking infrastructure...")
            checks = [
                (
                    "SNOWDDL_CONFIG_STAGE",
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.STAGES WHERE STAGE_NAME = 'SNOWDDL_CONFIG_STAGE'",
                ),
                (
                    "SNOWDDL_CONFIG_REQUESTS",
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SNOWDDL_CONFIG_REQUESTS'",
                ),
                (
                    "Stored Procedures",
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.PROCEDURES WHERE PROCEDURE_NAME LIKE 'SP_%'",
                ),
                (
                    "Tasks",
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TASKS WHERE NAME LIKE 'TASK_%'",
                ),
            ]

            all_good = True
            for name, query in checks:
                cursor.execute(query)
                result = cursor.fetchone()
                count = result[0] if result else 0

                if count > 0:
                    print(f"✅ {name}: {count} found")
                else:
                    print(f"❌ {name}: Not found")
                    all_good = False

            # Check pending requests
            cursor.execute("SELECT COUNT(*) FROM V_PENDING_REQUESTS")
            pending_count = cursor.fetchone()[0]
            print(f"📋 Pending requests: {pending_count}")

            # Check failed requests
            cursor.execute("SELECT COUNT(*) FROM V_FAILED_REQUESTS")
            failed_count = cursor.fetchone()[0]
            print(f"❌ Failed requests: {failed_count}")

            # Check GitHub configuration
            logger.info("Checking GitHub configuration...")
            github_token = os.getenv("GITHUB_TOKEN")
            github_repo_owner = os.getenv("GITHUB_REPO_OWNER")
            github_repo_name = os.getenv("GITHUB_REPO_NAME")

            if github_token:
                print("✅ GitHub token configured")
            else:
                print("❌ GitHub token not configured")
                all_good = False

            if github_repo_owner and github_repo_name:
                print(f"✅ GitHub repository: {github_repo_owner}/{github_repo_name}")
            else:
                print("❌ GitHub repository not configured")
                all_good = False

            cursor.close()

        if all_good:
            logger.info("✅ Health check passed!")
            return 0
        else:
            logger.warning("⚠️ Health check found issues")
            return 1

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GitHub Integration Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser(
        "setup", help="Setup GitHub integration infrastructure"
    )
    setup_parser.add_argument(
        "--enable-tasks", action="store_true", help="Enable Snowflake tasks"
    )
    setup_parser.add_argument(
        "--create-sample", action="store_true", help="Create sample PR request"
    )

    # Teardown command
    teardown_parser = subparsers.add_parser(
        "teardown", help="Teardown GitHub integration infrastructure"
    )
    teardown_parser.add_argument(
        "--confirm", action="store_true", help="Skip confirmation prompt"
    )

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor GitHub PR requests")
    monitor_group = monitor_parser.add_mutually_exclusive_group(required=True)
    monitor_group.add_argument(
        "--pending", action="store_true", help="Show pending requests"
    )
    monitor_group.add_argument(
        "--failed", action="store_true", help="Show failed requests"
    )
    monitor_group.add_argument(
        "--summary", action="store_true", help="Show request summary"
    )
    monitor_group.add_argument(
        "--status", action="store_true", help="Show specific request status"
    )
    monitor_parser.add_argument("--request-id", help="Request ID for status check")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run GitHub monitor process")
    run_parser.add_argument("--once", action="store_true", help="Run once and exit")
    run_parser.add_argument(
        "--interval", type=int, default=300, help="Interval between runs (seconds)"
    )
    run_parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy GitHub monitor")
    deploy_parser.add_argument(
        "--docker", action="store_true", help="Create Docker deployment"
    )
    deploy_parser.add_argument(
        "--systemd", action="store_true", help="Create systemd service"
    )
    deploy_parser.add_argument(
        "--lambda",
        dest="lambda_deploy",
        action="store_true",
        help="Create Lambda deployment",
    )
    deploy_parser.add_argument(
        "--all",
        dest="all_deploy",
        action="store_true",
        help="Create all deployment types",
    )

    # Health command
    health_parser = subparsers.add_parser("health", help="Check system health")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate function
    command_map = {
        "setup": setup_infrastructure,
        "teardown": teardown_infrastructure,
        "monitor": monitor_requests,
        "run": run_monitor,
        "deploy": deploy_monitor,
        "health": health_check,
    }

    return command_map[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
