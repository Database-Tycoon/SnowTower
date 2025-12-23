#!/usr/bin/env python3
"""
Parse SnowDDL plan output to identify missing schema grants.

This script runs snowddl plan and extracts all REVOKE statements on schemas,
then outputs the grants that need to be added to tech_role.yaml.
"""

from dotenv import load_dotenv

load_dotenv()

import os
import re
import subprocess
import sys
from collections import defaultdict


def main():
    print("🔍 Running SnowDDL plan to identify missing schema grants...\n")

    result = subprocess.run(
        [
            "snowddl",
            "-c",
            "snowddl",
            "-r",
            "ACCOUNTADMIN",
            "--exclude-object-types",
            "PIPE,STREAM,TASK",  # SCHEMA now managed by SnowDDL
            "plan",
        ],
        capture_output=True,
        text=True,
        env=os.environ,
    )

    if result.returncode != 0:
        print(f"❌ Plan failed: {result.stderr}")
        sys.exit(1)

    # Parse REVOKE statements on SCHEMA
    # Structure: role -> privilege -> set of schemas
    revokes = defaultdict(lambda: defaultdict(set))

    for line in result.stdout.split("\n"):
        if "REVOKE" in line and "SCHEMA" in line and "FROM ROLE" in line:
            # Extract: REVOKE <privilege> ON SCHEMA "<db>"."<schema>" FROM ROLE "<role>";
            match = re.search(
                r'REVOKE (.+?) ON SCHEMA "(.+?)"."(.+?)" FROM ROLE "(.+?)"', line
            )
            if match:
                privilege, db, schema, role = match.groups()
                # Remove __T_ROLE or __B_ROLE suffix for the YAML key
                role_key = role.replace("__T_ROLE", "").replace("__B_ROLE", "")
                schema_full = f"{db}.{schema}"

                revokes[role_key][privilege].add(schema_full)

    if not revokes:
        print("✅ No missing schema grants found!")
        sys.exit(0)

    # Print summary
    total_grants = sum(
        len(schemas) for privs in revokes.values() for schemas in privs.values()
    )
    print(f"Found {total_grants} missing schema grants across {len(revokes)} roles:\n")

    # Print in YAML format for easy copy-paste
    print("=" * 60)
    print("Add the following to tech_role.yaml under each role's 'grants' section:")
    print("=" * 60)

    for role in sorted(revokes.keys()):
        privs = revokes[role]
        print(f"\n{role}:")
        print("  grants:")

        # Group privileges that apply to the same schemas
        schema_to_privs = defaultdict(set)
        for priv, schemas in privs.items():
            for schema in schemas:
                schema_to_privs[schema].add(priv)

        # Find common privilege sets
        priv_set_to_schemas = defaultdict(set)
        for schema, priv_set in schema_to_privs.items():
            priv_key = ",".join(sorted(priv_set))
            priv_set_to_schemas[priv_key].add(schema)

        # Output grouped by privilege set
        for priv_key, schemas in sorted(priv_set_to_schemas.items()):
            print(f"    SCHEMA:{priv_key}:")
            for schema in sorted(schemas):
                print(f"      - {schema}")

    print("\n" + "=" * 60)
    print(f"Total: {len(revokes)} roles, {total_grants} grants")
    print("=" * 60)


if __name__ == "__main__":
    main()
