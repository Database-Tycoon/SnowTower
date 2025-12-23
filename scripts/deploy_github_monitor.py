#!/usr/bin/env python3
"""
Deployment script for GitHub Monitor process

This script helps deploy the GitHub monitor as various execution methods:
- Local daemon process
- AWS Lambda function
- Docker container
- Systemd service

Author: SnowTower Team
Date: 2025-01-14
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GitHubMonitorDeployment:
    """Deployment manager for GitHub monitor"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.src_dir = self.project_root / "src"
        self.scripts_dir = self.project_root / "scripts"

    def create_requirements_file(self) -> Path:
        """Create requirements.txt for the monitor"""
        requirements = [
            "snowflake-connector-python[pandas]>=3.0.0",
            "requests>=2.28.0",
            "python-dotenv>=0.19.0",
            "cryptography>=3.4.0",
            "pandas>=1.3.0",
        ]

        requirements_path = self.project_root / "requirements-github-monitor.txt"
        with open(requirements_path, "w") as f:
            f.write("\n".join(requirements))

        logger.info(f"Created requirements file: {requirements_path}")
        return requirements_path

    def create_docker_setup(self) -> Dict[str, Path]:
        """Create Docker deployment files"""
        logger.info("Creating Docker deployment files...")

        # Dockerfile
        dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements-github-monitor.txt .
RUN pip install --no-cache-dir -r requirements-github-monitor.txt

# Copy source code
COPY src/ ./src/
COPY scripts/github_monitor_runner.py ./

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONPATH=/app/src
ENV LOG_LEVEL=INFO

# Run as non-root user
RUN useradd -m -u 1000 monitor && chown -R monitor:monitor /app
USER monitor

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Default command
CMD ["python", "github_monitor_runner.py", "--continuous", "--interval", "300"]
"""

        # Docker Compose
        docker_compose_content = """
version: '3.8'

services:
  github-monitor:
    build: .
    container_name: snowddl-github-monitor
    restart: unless-stopped
    environment:
      - SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT}
      - SNOWFLAKE_USER=${SNOWFLAKE_USER}
      - SNOWFLAKE_PASSWORD=${SNOWFLAKE_PASSWORD}
      - SNOWFLAKE_PRIVATE_KEY_PATH=${SNOWFLAKE_PRIVATE_KEY_PATH}
      - SNOWFLAKE_ROLE=${SNOWFLAKE_ROLE:-SNOWDDL_CONFIG_MANAGER}
      - SNOWFLAKE_WAREHOUSE=${SNOWFLAKE_WAREHOUSE:-COMPUTE_WH}
      - SNOWFLAKE_DATABASE=${SNOWFLAKE_DATABASE:-SNOWDDL_CONFIG}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_REPO_OWNER=${GITHUB_REPO_OWNER}
      - GITHUB_REPO_NAME=${GITHUB_REPO_NAME}
      - GITHUB_BASE_BRANCH=${GITHUB_BASE_BRANCH:-main}
      - GITHUB_REVIEWER_TEAMS=${GITHUB_REVIEWER_TEAMS:-[]}
      - PROCESSOR_INTERVAL_MINUTES=${PROCESSOR_INTERVAL_MINUTES:-5}
    volumes:
      - ./logs:/app/logs
      - ./keys:/app/keys:ro  # Mount SSH keys if using key auth
    ports:
      - "8000:8000"  # For health checks
    healthcheck:
      test: ["CMD", "python", "-c", "import os; exit(0 if os.path.exists('/app/logs/github_monitor.log') else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # Optional: Add a monitoring dashboard
  monitor-dashboard:
    image: grafana/grafana:latest
    container_name: monitor-dashboard
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
"""

        # Create files
        files = {}
        files["dockerfile"] = self.project_root / "Dockerfile"
        files["docker_compose"] = self.project_root / "docker-compose.yml"

        with open(files["dockerfile"], "w") as f:
            f.write(dockerfile_content)

        with open(files["docker_compose"], "w") as f:
            f.write(docker_compose_content)

        logger.info("✅ Docker files created")
        return files

    def create_systemd_service(self) -> Path:
        """Create systemd service file"""
        logger.info("Creating systemd service file...")

        service_content = f"""
[Unit]
Description=SnowDDL GitHub Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=snowddl
Group=snowddl
WorkingDirectory={self.project_root}
Environment=PYTHONPATH={self.src_dir}
EnvironmentFile={self.project_root}/.env
ExecStart=/usr/bin/python3 {self.project_root}/src/github_integration/github_monitor.py --continuous --interval 300
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=snowddl-github-monitor

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={self.project_root}/logs

[Install]
WantedBy=multi-user.target
"""

        service_path = self.project_root / "snowddl-github-monitor.service"
        with open(service_path, "w") as f:
            f.write(service_content)

        logger.info(f"✅ Systemd service file created: {service_path}")
        return service_path

    def create_lambda_package(self) -> Path:
        """Create AWS Lambda deployment package"""
        logger.info("Creating AWS Lambda deployment package...")

        # Lambda handler
        lambda_handler_content = '''
import json
import logging
import os
from src.github_integration.github_monitor import GitHubMonitor, load_config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda handler for GitHub monitor
    """
    try:
        # Load configuration
        snowflake_config, github_config = load_config()

        # Create and run monitor
        monitor = GitHubMonitor(snowflake_config, github_config)
        stats = monitor.run_once()

        # Return results
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'GitHub monitor executed successfully',
                'stats': stats
            })
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'GitHub monitor execution failed',
                'error': str(e)
            })
        }
'''

        # SAM template
        sam_template_content = """
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: SnowDDL GitHub Monitor Lambda Function

Parameters:
  SnowflakeAccount:
    Type: String
    Description: Snowflake account identifier
  SnowflakeUser:
    Type: String
    Description: Snowflake username
  SnowflakePassword:
    Type: String
    NoEcho: true
    Description: Snowflake password (optional if using keys)
    Default: ""
  GitHubToken:
    Type: String
    NoEcho: true
    Description: GitHub personal access token
  GitHubRepoOwner:
    Type: String
    Description: GitHub repository owner
  GitHubRepoName:
    Type: String
    Description: GitHub repository name

Resources:
  GitHubMonitorFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: lambda_handler.lambda_handler
      Runtime: python3.11
      Timeout: 900
      MemorySize: 512
      Environment:
        Variables:
          SNOWFLAKE_ACCOUNT: !Ref SnowflakeAccount
          SNOWFLAKE_USER: !Ref SnowflakeUser
          SNOWFLAKE_PASSWORD: !Ref SnowflakePassword
          SNOWFLAKE_ROLE: SNOWDDL_CONFIG_MANAGER
          SNOWFLAKE_WAREHOUSE: COMPUTE_WH
          SNOWFLAKE_DATABASE: SNOWDDL_CONFIG
          GITHUB_TOKEN: !Ref GitHubToken
          GITHUB_REPO_OWNER: !Ref GitHubRepoOwner
          GITHUB_REPO_NAME: !Ref GitHubRepoName
          GITHUB_BASE_BRANCH: main
      Events:
        ScheduleEvent:
          Type: Schedule
          Properties:
            Schedule: rate(5 minutes)
            Description: Run GitHub monitor every 5 minutes
      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - logs:CreateLogGroup
                - logs:CreateLogStream
                - logs:PutLogEvents
              Resource:
                - !Sub "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/*"

  GitHubMonitorLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${GitHubMonitorFunction}"
      RetentionInDays: 30

Outputs:
  GitHubMonitorFunction:
    Description: GitHub Monitor Lambda Function ARN
    Value: !GetAtt GitHubMonitorFunction.Arn
  GitHubMonitorFunctionIamRole:
    Description: Implicit IAM Role created for GitHub Monitor function
    Value: !GetAtt GitHubMonitorFunctionRole.Arn
"""

        # Create files
        lambda_dir = self.project_root / "lambda_deployment"
        lambda_dir.mkdir(exist_ok=True)

        handler_path = lambda_dir / "lambda_handler.py"
        template_path = lambda_dir / "template.yaml"

        with open(handler_path, "w") as f:
            f.write(lambda_handler_content)

        with open(template_path, "w") as f:
            f.write(sam_template_content)

        logger.info(f"✅ Lambda package created in: {lambda_dir}")
        return lambda_dir

    def create_runner_script(self) -> Path:
        """Create a simple runner script"""
        runner_content = '''#!/usr/bin/env python3
"""
GitHub Monitor Runner Script

Simple wrapper script for running the GitHub monitor with proper logging
and error handling.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from github_integration.github_monitor import main

if __name__ == '__main__':
    # Configure logging for production
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/github_monitor.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Create logs directory
    Path('logs').mkdir(exist_ok=True)

    # Run the monitor
    main()
'''

        runner_path = self.project_root / "github_monitor_runner.py"
        with open(runner_path, "w") as f:
            f.write(runner_content)

        # Make executable
        runner_path.chmod(0o755)

        logger.info(f"✅ Runner script created: {runner_path}")
        return runner_path

    def create_deployment_guide(self) -> Path:
        """Create deployment guide documentation"""
        guide_content = """# GitHub Monitor Deployment Guide

This guide covers different deployment options for the SnowDDL GitHub Monitor.

## Prerequisites

1. **Environment Variables**: Ensure all required environment variables are set
2. **Snowflake Setup**: Run the setup script to create infrastructure
3. **GitHub Token**: Create a GitHub personal access token with repo permissions

## Deployment Options

### 1. Local Development/Testing

```bash
# Install dependencies
pip install -r requirements-github-monitor.txt

# Run once
python src/github_integration/github_monitor.py --once

# Run continuously
python src/github_integration/github_monitor.py --interval 300
```

### 2. Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f github-monitor

# Stop
docker-compose down
```

### 3. Systemd Service (Linux)

```bash
# Copy service file
sudo cp snowddl-github-monitor.service /etc/systemd/system/

# Create user and setup permissions
sudo useradd -m -s /bin/bash snowddl
sudo chown -R snowddl:snowddl /path/to/snowddl-project

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable snowddl-github-monitor
sudo systemctl start snowddl-github-monitor

# Check status
sudo systemctl status snowddl-github-monitor
sudo journalctl -u snowddl-github-monitor -f
```

### 4. AWS Lambda Deployment

```bash
# Using SAM CLI
cd lambda_deployment
sam build
sam deploy --guided

# Or using AWS CLI with zip package
pip install -r requirements-github-monitor.txt -t lambda_package/
cp -r src/ lambda_package/
cd lambda_package && zip -r ../github-monitor.zip .
aws lambda create-function --function-name snowddl-github-monitor --runtime python3.11 --zip-file fileb://../github-monitor.zip
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password  # OR use private key
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/private_key.pem
SNOWFLAKE_ROLE=SNOWDDL_CONFIG_MANAGER
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SNOWDDL_CONFIG

# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=snowddl-config
GITHUB_BASE_BRANCH=main
GITHUB_REVIEWER_TEAMS=["data-team", "devops-team"]
```

### Monitoring and Alerts

1. **Logs**: Monitor application logs for errors and performance
2. **Snowflake**: Use the V_REQUEST_SUMMARY view for metrics
3. **GitHub**: Monitor repository for PR creation activity
4. **Health Checks**: Implement monitoring for process health

### Security Best Practices

1. **Secrets Management**: Store sensitive values in secure secret stores
2. **Network Security**: Restrict network access where possible
3. **User Permissions**: Use minimal required Snowflake permissions
4. **Token Rotation**: Regularly rotate GitHub tokens
5. **Audit Logging**: Enable comprehensive audit logging

### Troubleshooting

1. **Connection Issues**: Check Snowflake and GitHub connectivity
2. **Permission Errors**: Verify Snowflake roles and GitHub permissions
3. **Rate Limiting**: Monitor GitHub API rate limits
4. **Queue Backup**: Check for stuck requests in PROCESSING status

### Performance Tuning

1. **Interval Adjustment**: Tune processing interval based on volume
2. **Batch Size**: Adjust batch processing parameters
3. **Resource Allocation**: Scale compute resources as needed
4. **Cleanup**: Regular cleanup of old requests and logs
"""

        guide_path = self.project_root / "docs" / "GITHUB_DEPLOYMENT_GUIDE.md"
        guide_path.parent.mkdir(exist_ok=True)

        with open(guide_path, "w") as f:
            f.write(guide_content)

        logger.info(f"✅ Deployment guide created: {guide_path}")
        return guide_path

    def deploy_all(self) -> Dict[str, Any]:
        """Create all deployment artifacts"""
        logger.info("🚀 Creating all deployment artifacts...")

        results = {}

        try:
            results["requirements"] = self.create_requirements_file()
            results["docker"] = self.create_docker_setup()
            results["systemd"] = self.create_systemd_service()
            results["lambda"] = self.create_lambda_package()
            results["runner"] = self.create_runner_script()
            results["guide"] = self.create_deployment_guide()

            logger.info("✅ All deployment artifacts created successfully!")
            return results

        except Exception as e:
            logger.error(f"❌ Failed to create deployment artifacts: {e}")
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Deploy GitHub Monitor")
    parser.add_argument(
        "--docker", action="store_true", help="Create Docker deployment files"
    )
    parser.add_argument(
        "--systemd", action="store_true", help="Create systemd service file"
    )
    parser.add_argument(
        "--lambda",
        dest="lambda_deploy",
        action="store_true",
        help="Create Lambda deployment package",
    )
    parser.add_argument(
        "--all", action="store_true", help="Create all deployment artifacts"
    )

    args = parser.parse_args()

    try:
        deployment = GitHubMonitorDeployment()

        if args.all:
            deployment.deploy_all()
        else:
            if args.docker:
                deployment.create_docker_setup()
            if args.systemd:
                deployment.create_systemd_service()
            if args.lambda_deploy:
                deployment.create_lambda_package()

            # Always create requirements and runner
            deployment.create_requirements_file()
            deployment.create_runner_script()

        logger.info("🎉 Deployment setup completed!")

    except Exception as e:
        logger.error(f"❌ Deployment setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
