"""
Example: Using the SnowDDL OOP Framework

This script demonstrates how to use the new Pythonic API for managing
SnowDDL configurations programmatically.
"""

from pathlib import Path

from snowddl_core import (
    SnowDDLProject,
    User,
    Warehouse,
    BusinessRole,
    ResourceMonitor,
)


def example_load_and_inspect():
    """Example: Load existing configuration and inspect objects"""
    print("=" * 60)
    print("Example 1: Load and Inspect Configuration")
    print("=" * 60)

    # Load existing project
    project = SnowDDLProject("./snowddl")
    project.load_all()

    print(f"\n{project}")
    print(f"\nProject Summary: {project.summary()}")

    # Get specific user
    user = project.get_user("ALICE")
    if user:
        print(f"\nUser Details:")
        print(f"  Name: {user.name}")
        print(f"  Login: {user.login_name}")
        print(f"  Type: {user.type}")
        print(f"  Email: {user.email}")
        print(f"  Business Roles: {user.business_roles}")


def example_create_user():
    """Example: Create a new user programmatically"""
    print("\n" + "=" * 60)
    print("Example 2: Create New User")
    print("=" * 60)

    # Create a new service account user
    service_user = User(
        name="DATA_PIPELINE_SERVICE",
        login_name="data_pipeline",
        type="SERVICE",
        rsa_public_key="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...",
        business_roles=["DATA_ENGINEER_ROLE"],
        default_warehouse="ETL_WH",
        comment="Service account for data pipeline automation",
    )

    print(f"\nCreated user: {service_user}")
    print(f"\nUser YAML representation:")
    import yaml

    print(yaml.dump(service_user.to_yaml(), default_flow_style=False))


def example_create_warehouse():
    """Example: Create a new warehouse with specific settings"""
    print("\n" + "=" * 60)
    print("Example 3: Create Warehouse")
    print("=" * 60)

    # Create a multi-cluster warehouse for production workloads
    prod_warehouse = Warehouse(
        name="PRODUCTION_WH",
        size="Large",
        type="STANDARD",
        min_cluster_count=1,
        max_cluster_count=5,
        scaling_policy="STANDARD",
        auto_suspend=300,  # 5 minutes
        enable_query_acceleration=True,
        query_acceleration_max_scale_factor=8,
        resource_monitor="PROD_MONITOR",
        comment="Production warehouse with auto-scaling",
    )

    print(f"\nCreated warehouse: {prod_warehouse}")
    print(f"\nWarehouse configuration:")
    print(f"  Size: {prod_warehouse.size}")
    print(
        f"  Multi-cluster: {prod_warehouse.min_cluster_count}-{prod_warehouse.max_cluster_count}"
    )
    print(f"  Auto-suspend: {prod_warehouse.auto_suspend}s")
    print(f"  Query Acceleration: {prod_warehouse.enable_query_acceleration}")


def example_create_business_role():
    """Example: Create a business role with permissions"""
    print("\n" + "=" * 60)
    print("Example 4: Create Business Role")
    print("=" * 60)

    # Create a data analyst role
    analyst_role = BusinessRole(
        name="DATA_ANALYST_ROLE",
        database_read=["ANALYTICS_DB", "REPORTING_DB"],
        schema_read=["ANALYTICS_DB.PUBLIC", "REPORTING_DB.MARTS"],
        warehouse_usage=["ANALYST_WH", "REPORTING_WH"],
        comment="Role for data analysts with read access to analytics databases",
    )

    # Add permissions using helper methods
    analyst_role.add_warehouse_usage("ADHOC_WH")
    analyst_role.grant_schema_access("ANALYTICS_DB.STAGING", "read")

    print(f"\nCreated role: {analyst_role}")
    print(f"\nRole permissions:")
    print(f"  Read databases: {analyst_role.database_read}")
    print(f"  Read schemas: {analyst_role.schema_read}")
    print(f"  Warehouse usage: {analyst_role.warehouse_usage}")


def example_resource_monitor():
    """Example: Create a resource monitor for cost control"""
    print("\n" + "=" * 60)
    print("Example 5: Create Resource Monitor")
    print("=" * 60)

    # Create a monthly resource monitor
    monitor = ResourceMonitor(
        name="DEV_TEAM_MONITOR",
        credit_quota=1000,
        frequency="MONTHLY",
        notify_at=[50, 75, 90],
        suspend_at=100,
        comment="Monthly credit monitor for dev team warehouses",
    )

    print(f"\nCreated resource monitor: {monitor}")
    print(f"  Credit quota: {monitor.credit_quota}")
    print(f"  Frequency: {monitor.frequency}")
    print(f"  Notify at: {monitor.notify_at}%")
    print(f"  Suspend at: {monitor.suspend_at}%")


def example_validation():
    """Example: Validate configuration"""
    print("\n" + "=" * 60)
    print("Example 6: Validate Configuration")
    print("=" * 60)

    # Create a user with validation issues
    invalid_user = User(
        name="TEST_USER",
        login_name="test_user",
        type="PERSON",
        # Missing email - will trigger validation error
        # Missing authentication - will trigger error
    )

    errors = invalid_user.validate()
    print(f"\nValidation errors for {invalid_user.name}:")
    for error in errors:
        print(f"  - {error}")


def example_save_configuration():
    """Example: Create and save a complete configuration"""
    print("\n" + "=" * 60)
    print("Example 7: Save Configuration (Dry Run)")
    print("=" * 60)

    # Create a new project
    project = SnowDDLProject("./test_config")

    # Add users
    admin_user = User(
        name="ADMIN_USER",
        login_name="admin",
        type="PERSON",
        first_name="Admin",
        last_name="User",
        email="admin@company.com",
        business_roles=["ADMIN_ROLE"],
        default_warehouse="ADMIN_WH",
    )
    project.add_user(admin_user)

    # Add warehouse
    admin_wh = Warehouse(
        name="ADMIN_WH",
        size="Small",
        auto_suspend=120,
        comment="Administrative warehouse",
    )
    project.add_warehouse(admin_wh)

    # Add business role
    admin_role = BusinessRole(
        name="ADMIN_ROLE",
        database_owner=["ALL_DBS"],
        warehouse_usage=["ADMIN_WH"],
        comment="Administrative role with full database access",
    )
    project.add_business_role(admin_role)

    print(f"\nCreated project: {project}")
    print(f"Summary: {project.summary()}")

    # In a real scenario, you would call:
    # project.save_all()
    print("\nNote: project.save_all() would write all configurations to YAML files")


def main():
    """Run all examples"""
    example_load_and_inspect()
    example_create_user()
    example_create_warehouse()
    example_create_business_role()
    example_resource_monitor()
    example_validation()
    example_save_configuration()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
