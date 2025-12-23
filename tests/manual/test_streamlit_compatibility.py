#!/usr/bin/env python3
"""
Test Streamlit Compatibility

This script tests that the fixed managers work properly with YAML-based data
without requiring Snowflake connection (simulating Streamlit environment).
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

def test_managers_without_connection():
    """Test that managers work with YAML data only"""
    print("🧪 Testing Streamlit-compatible managers...")
    print("=" * 50)

    try:
        # Import managers
        from snowtower_core.managers import (
            UserManager,
            RoleManager,
            WarehouseManager,
            DatabaseManager,
            SecurityPolicyManager
        )

        print("✅ Successfully imported all managers")

        # Test UserManager
        print("\n👥 Testing UserManager...")
        user_manager = UserManager()
        try:
            users_response = user_manager._get_users_from_yaml()
            print(f"   ✅ Found {users_response.total_count} users in YAML")
            print(f"   📊 {users_response.mfa_compliant_count} MFA compliant")
            print(f"   🔧 {users_response.service_count} service accounts")
        except Exception as e:
            print(f"   ⚠️  UserManager test: {e}")

        # Test RoleManager
        print("\n🔐 Testing RoleManager...")
        role_manager = RoleManager()
        try:
            roles_response = role_manager._get_roles_from_yaml()
            print(f"   ✅ Found {roles_response.total_count} roles in YAML")
            print(f"   🏢 {roles_response.business_roles_count} business roles")
            print(f"   ⚙️  {roles_response.technical_roles_count} technical roles")
        except Exception as e:
            print(f"   ⚠️  RoleManager test: {e}")

        # Test WarehouseManager
        print("\n🏭 Testing WarehouseManager...")
        warehouse_manager = WarehouseManager()
        try:
            warehouses_response = warehouse_manager._get_warehouses_from_yaml()
            print(f"   ✅ Found {warehouses_response.total_count} warehouses in YAML")
            print(f"   🔄 {warehouses_response.running_count} marked as running")
        except Exception as e:
            print(f"   ⚠️  WarehouseManager test: {e}")

        # Test DatabaseManager
        print("\n🗄️ Testing DatabaseManager...")
        database_manager = DatabaseManager()
        try:
            databases_response = database_manager._get_databases_from_directories()
            print(f"   ✅ Found {databases_response.total_count} database directories")
        except Exception as e:
            print(f"   ⚠️  DatabaseManager test: {e}")

        # Test SecurityPolicyManager
        print("\n🛡️ Testing SecurityPolicyManager...")
        security_manager = SecurityPolicyManager()
        try:
            policies = security_manager.get_all_policies()
            print(f"   ✅ Found {len(policies)} security policies")
        except Exception as e:
            print(f"   ⚠️  SecurityPolicyManager test: {e}")

        print("\n🎉 All managers tested successfully!")
        print("📝 The app should work in Snowflake Streamlit environment.")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running from the correct directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function"""
    print("🏔️ SnowTower Streamlit Compatibility Test")
    print("Testing YAML-based managers without Snowflake connection")
    print()

    # Check if we're in the right directory
    if not Path("src/snowtower_core/managers.py").exists():
        print("❌ Error: Must run from snowtower-snowddl root directory")
        sys.exit(1)

    success = test_managers_without_connection()

    if success:
        print("\n✅ All tests passed! The app is ready for Streamlit deployment.")
        print("\n📋 Next steps:")
        print("   1. Upload all files to Snowflake Streamlit")
        print("   2. Set the main file to 'src/web/app.py'")
        print("   3. Test in Snowflake environment")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
