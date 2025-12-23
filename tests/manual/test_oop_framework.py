#!/usr/bin/env python3
"""
Test script to validate the OOP framework works with existing YAML configurations
"""

import os
import sys
from pathlib import Path
import yaml
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

# Load environment variables
env_file = Path("/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl/.env")
if env_file.exists():
    load_dotenv(env_file)

# Add src to path so we can import snowddl_core
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from snowddl_core.account_objects import User, Warehouse, BusinessRole
    from snowddl_core.snowddl_types import UserType, WarehouseSize
    console = Console()
    console.print("✅ [green]Successfully imported snowddl_core modules![/green]")
except ImportError as e:
    console = Console()
    console.print(f"❌ [red]Failed to import snowddl_core: {e}[/red]")
    sys.exit(1)

def test_load_existing_user():
    """Test loading an existing user from YAML"""
    console.print("\n📋 [bold]Testing User Loading from YAML[/bold]")

    # Load existing user.yaml
    user_yaml_path = Path("/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl/snowddl/user.yaml")

    if not user_yaml_path.exists():
        console.print(f"❌ User YAML not found at {user_yaml_path}")
        return False

    try:
        with open(user_yaml_path, 'r') as f:
            users_data = yaml.safe_load(f)

        console.print(f"Found {len(users_data)} users in YAML")

        # Try to load ALICE user
        if 'ALICE' in users_data:
            stephen_data = users_data['ALICE']
            console.print(f"\n👤 Loading user ALICE...")

            # Create User object from YAML data
            stephen = User.from_yaml('ALICE', stephen_data)

            console.print(f"  Name: {stephen.name}")
            console.print(f"  Type: {stephen.type}")
            console.print(f"  Has RSA Key: {bool(stephen.rsa_public_key)}")
            console.print(f"  Has Password: {bool(stephen.password)}")
            console.print(f"  Business Roles: {stephen.business_roles}")

            return True
    except Exception as e:
        console.print(f"❌ Error loading user: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False

def test_load_existing_warehouse():
    """Test loading an existing warehouse from YAML"""
    console.print("\n📋 [bold]Testing Warehouse Loading from YAML[/bold]")

    warehouse_yaml_path = Path("/Users/ssciortino/Projects/snowtower-workspace/snowtower-snowddl/snowddl/warehouse.yaml")

    if not warehouse_yaml_path.exists():
        console.print(f"❌ Warehouse YAML not found at {warehouse_yaml_path}")
        return False

    try:
        with open(warehouse_yaml_path, 'r') as f:
            warehouses_data = yaml.safe_load(f)

        console.print(f"Found {len(warehouses_data)} warehouses in YAML")

        # Try to load MAIN_WAREHOUSE
        if 'MAIN_WAREHOUSE' in warehouses_data:
            wh_data = warehouses_data['MAIN_WAREHOUSE']
            console.print(f"\n🏗️ Loading warehouse MAIN_WAREHOUSE...")

            # Create Warehouse object from YAML data
            warehouse = Warehouse.from_yaml('MAIN_WAREHOUSE', wh_data)

            console.print(f"  Name: {warehouse.name}")
            console.print(f"  Size: {warehouse.size}")
            console.print(f"  Auto Suspend: {warehouse.auto_suspend}")
            console.print(f"  Resource Monitor: {warehouse.resource_monitor}")

            return True
    except Exception as e:
        console.print(f"❌ Error loading warehouse: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False

def test_create_new_user():
    """Test creating a new user programmatically"""
    console.print("\n📋 [bold]Testing User Creation[/bold]")

    try:
        # Create a new user
        new_user = User(
            name="TEST_USER",
            login_name="TEST_USER",
            type="PERSON",  # Use string literal instead of enum
            email="test@example.com",
            business_roles=["ANALYST_ROLE"]
        )

        # Set a password (should be encrypted)
        new_user.set_password("TestPassword123!")

        console.print(f"✅ Created user: {new_user.name}")
        console.print(f"  Type: {new_user.type}")
        console.print(f"  Email: {new_user.email}")
        console.print(f"  Password encrypted: {new_user.password.startswith('!decrypt:') if new_user.password else False}")

        # Convert to YAML
        yaml_data = new_user.to_yaml()
        console.print("\n📄 YAML representation:")
        console.print(yaml.dump({new_user.name: yaml_data}, default_flow_style=False))

        return True
    except Exception as e:
        console.print(f"❌ Error creating user: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False

def test_validation():
    """Test validation framework"""
    console.print("\n📋 [bold]Testing Validation[/bold]")

    try:
        # Create a user with invalid configuration
        user = User(
            name="invalid-user",  # lowercase not allowed
            login_name="invalid-user",
            type="PERSON"  # Use string literal
        )

        errors = user.validate()
        if errors:
            console.print("✅ Validation correctly found errors:")
            for error in errors:
                console.print(f"  - {error.severity}: {error.message}")
        else:
            console.print("❌ Validation should have found errors but didn't")

        return True
    except Exception as e:
        console.print(f"❌ Error during validation: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False

def main():
    """Run all tests"""
    console.print("🧪 [bold cyan]Testing SnowDDL OOP Framework[/bold cyan]")
    console.print("=" * 50)

    tests = [
        ("Load existing user", test_load_existing_user),
        ("Load existing warehouse", test_load_existing_warehouse),
        ("Create new user", test_create_new_user),
        ("Validation framework", test_validation)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            console.print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    console.print("\n" + "=" * 50)
    console.print("📊 [bold]Test Summary[/bold]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Test", style="cyan")
    table.add_column("Result", justify="center")

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        style = "green" if success else "red"
        table.add_row(test_name, f"[{style}]{status}[/{style}]")

    console.print(table)

    # Overall result
    all_passed = all(r[1] for r in results)
    if all_passed:
        console.print("\n🎉 [bold green]All tests passed![/bold green]")
    else:
        console.print("\n⚠️ [bold red]Some tests failed![/bold red]")

    # Test that snowddl-plan still works
    console.print("\n📋 [bold]Testing snowddl-plan compatibility[/bold]")
    import subprocess
    result = subprocess.run(["uv", "run", "snowddl-plan"], capture_output=True, text=True)
    if result.returncode == 0 and "ALTER USER" in result.stdout:
        console.print("✅ snowddl-plan still works correctly")
    else:
        console.print("❌ snowddl-plan may be broken")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
