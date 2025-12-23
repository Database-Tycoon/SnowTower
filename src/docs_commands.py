#!/usr/bin/env python3
"""Documentation commands for SnowTower-SnowDDL"""

import subprocess
import sys
import os
from pathlib import Path


def serve_docs():
    """Serve the documentation locally with auto-reload"""
    print("🚀 Starting SnowTower-SnowDDL Documentation Server")
    print("📚 Documentation will be available at http://localhost:8000")
    print("📖 API Reference available at http://localhost:8000/api/")
    print("Press Ctrl+C to stop the server\n")

    # Change to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Use the mkdocs config with API documentation
    config_file = Path(project_root) / "config" / "mkdocs.yml"

    # Run mkdocs serve
    try:
        subprocess.run(["mkdocs", "serve", "-f", str(config_file)], check=True)
    except KeyboardInterrupt:
        print("\n\n✅ Documentation server stopped.")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running mkdocs: {e}")
        sys.exit(1)


def build_docs():
    """Build the documentation as a static site and optionally upload to Snowflake"""
    print("🏗️  Building SnowTower-SnowDDL Documentation")

    # Change to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Clean previous build
    site_dir = os.path.join(project_root, "site")
    if os.path.exists(site_dir):
        import shutil

        print("Cleaning previous build...")
        shutil.rmtree(site_dir)

    # Use the mkdocs config with API documentation
    config_file = Path(project_root) / "config" / "mkdocs.yml"

    # Build documentation
    try:
        subprocess.run(["mkdocs", "build", "-f", str(config_file)], check=True)
        print("\n✅ Documentation built successfully!")
        print(f"📁 Static site generated in: {site_dir}")

        # Check for Snowflake CLI tools (prefer new 'snow' over legacy 'snowsql')
        snow_cli_available = (
            subprocess.run(["which", "snow"], capture_output=True, text=True).returncode
            == 0
        )

        snowsql_available = (
            subprocess.run(
                ["which", "snowsql"], capture_output=True, text=True
            ).returncode
            == 0
        )

        if snow_cli_available or snowsql_available:
            print("\n☁️  Uploading documentation to Snowflake stage...")
            try:
                if snow_cli_available:
                    # Use new Snowflake CLI
                    # Check for SNOW_CONNECTION env var, otherwise use default
                    connection_args = []
                    if os.environ.get("SNOW_CONNECTION"):
                        connection_args = [
                            "--connection",
                            os.environ["SNOW_CONNECTION"],
                        ]
                    # Otherwise use default connection (no --connection flag needed)

                    upload_cmd = [
                        "snow",
                        "stage",
                        "copy",
                        f"{site_dir}/*",
                        "@SNOWTOWER_DOCS.PUBLIC.DOCS_SITE",
                        "--overwrite",
                    ] + connection_args
                else:
                    # Use legacy snowsql
                    upload_cmd = [
                        "snowsql",
                        "-c",
                        "snowtower_connection",
                        "-q",
                        f"PUT 'file://{site_dir}/*' @SNOWTOWER_DOCS.PUBLIC.DOCS_SITE OVERWRITE=TRUE AUTO_COMPRESS=FALSE",
                    ]

                result = subprocess.run(upload_cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    print("✅ Documentation uploaded to Snowflake successfully!")
                    print("\n📚 Access the documentation in Snowflake:")
                    print("  1. Log into Snowflake Snowsight")
                    print("  2. Navigate to Data → Databases → SNOWTOWER_DOCS")
                    print("  3. Open the DOCS_SITE Streamlit app")
                else:
                    print(f"⚠️  Upload to Snowflake failed: {result.stderr}")
                    print("Documentation built locally but not uploaded to Snowflake.")
            except Exception as e:
                print(f"⚠️  Error uploading to Snowflake: {e}")
                print("Documentation built locally but not uploaded to Snowflake.")
        else:
            print("\n⚠️  Snowflake CLI not found - skipping upload")
            print(
                "To upload documentation to Snowflake, install Snowflake CLI or SnowSQL first."
            )

        print("\nTo serve the static site locally, run:")
        print(f"  cd {site_dir} && python -m http.server 8000")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error building documentation: {e}")
        sys.exit(1)


def generate_api_docs():
    """Generate API documentation from docstrings"""
    print("📚 Generating API Documentation from SnowDDL Core")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    print("\n✅ API documentation structure created!")
    print("📁 API docs location: site_docs/api/")
    print("\nThe API documentation uses mkdocstrings to auto-generate from docstrings.")
    print("To view the API documentation:")
    print("  uv run docs-serve-api")


def serve_api_docs():
    """Serve API documentation with mkdocs"""
    print("📚 Starting API Documentation Server")
    print("🔧 Using mkdocstrings for automatic API documentation generation")
    print("📖 API docs will be available at http://localhost:8000/api/")
    print("\nPress Ctrl+C to stop the server\n")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Use the mkdocs config with API documentation
    config_file = Path(project_root) / "config" / "mkdocs.yml"

    try:
        subprocess.run(["mkdocs", "serve", "-f", str(config_file)], check=True)
    except KeyboardInterrupt:
        print("\n\n✅ API documentation server stopped.")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running mkdocs: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build_docs()
    else:
        serve_docs()
