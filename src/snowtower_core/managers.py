"""
SnowTower Core Managers

Business logic classes that handle CRUD operations and complex workflows
for Snowflake objects. These managers work with both the OOP models and
the actual Snowflake database through the client connection.
"""

import os
import yaml
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

from .models import (
    UserModel,
    RoleModel,
    WarehouseModel,
    DatabaseModel,
    SchemaModel,
    SecurityPolicyModel,
    UsersResponse,
    WarehousesResponse,
    DatabasesResponse,
    RolesResponse,
    UserStatus,
    AuthenticationMethod,
)
from snowddl_core import SnowDDLProject
from user_management.manager import UserManager as SnowDDLUserManager


class BaseManager:
    """Base manager class with common functionality"""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.snowddl_dir = self.project_root / "snowddl"

    def load_yaml_config(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file"""
        file_path = self.snowddl_dir / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def save_yaml_config(self, filename: str, config: Dict[str, Any]) -> None:
        """Save YAML configuration file"""
        file_path = self.snowddl_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)


class SnowflakeClientManager(BaseManager):
    """Manager for Snowflake database connections and queries"""

    def __init__(self, project_root: Optional[str] = None):
        super().__init__(project_root)
        self._client = None
        self._connection_params = None

    def get_connection(self):
        """Get Snowflake connection using environment variables"""
        if self._client is None:
            # Import here to avoid circular imports
            try:
                from snowflake.connector import connect

                # Load connection parameters from environment
                self._connection_params = {
                    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                    "user": os.getenv("SNOWFLAKE_USER"),
                    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
                    "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
                }

                # Authentication - prefer RSA key over password
                private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
                if private_key_path and os.path.exists(private_key_path):
                    from cryptography.hazmat.primitives import serialization

                    with open(private_key_path, "rb") as key_file:
                        private_key = serialization.load_pem_private_key(
                            key_file.read(),
                            password=None,
                        )
                    self._connection_params["private_key"] = private_key
                else:
                    password = os.getenv("SNOWFLAKE_PASSWORD")
                    if password:
                        self._connection_params["password"] = password
                    else:
                        raise ValueError("No authentication method configured")

                self._client = connect(**self._connection_params)

            except ImportError:
                raise ImportError("snowflake-connector-python not available")

        return self._client

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute query and return results as list of dictionaries"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            return [dict(zip(columns, row)) for row in results]

        finally:
            cursor.close()

    def execute_ddl(self, ddl: str) -> None:
        """Execute DDL statement"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(ddl)

        finally:
            cursor.close()


class UserManager(BaseManager):
    """Manager for User operations"""

    def __init__(
        self,
        project_root: Optional[str] = None,
        client: Optional[SnowflakeClientManager] = None,
    ):
        super().__init__(project_root)
        self.client = client or SnowflakeClientManager(project_root)
        self.snowddl_user_manager = SnowDDLUserManager()

    def get_all_users(self) -> UsersResponse:
        """Get all users from YAML configuration (Streamlit-compatible)"""
        try:
            # For Snowflake Streamlit, we need to use YAML-based approach
            # as SHOW commands and many information_schema queries aren't supported
            return self._get_users_from_yaml()

        except Exception as e:
            # Fallback to YAML configuration if queries fail
            return self._get_users_from_yaml()

    def _get_user_detailed_info(self, username: str) -> Dict[str, Any]:
        """Get detailed user authentication information (Streamlit-compatible)"""
        try:
            # For Streamlit deployment, we can't use DESCRIBE USER
            # Instead, return info based on YAML configuration
            config = self.load_yaml_config("user.yaml")
            user_config = config.get("users", {}).get(username, {})

            auth_info = {
                "has_rsa_public_key": "rsa_public_key" in user_config,
                "has_password": "password" in user_config,
                "has_mfa": False,
                "authentication_methods": [],
            }

            if auth_info["has_rsa_public_key"]:
                auth_info["authentication_methods"].append(AuthenticationMethod.RSA_KEY)
            if auth_info["has_password"]:
                auth_info["authentication_methods"].append(
                    AuthenticationMethod.PASSWORD
                )

            # Determine MFA based on auth methods and user type
            comment = user_config.get("comment", "")
            if (
                "TYPE=SERVICE" not in comment
                and len(auth_info["authentication_methods"]) >= 1
            ):
                auth_info["has_mfa"] = True
                auth_info["authentication_methods"].append(AuthenticationMethod.MFA)

            return auth_info

        except Exception as e:
            print(f"Error getting detailed user info for {username}: {e}")
            return {}

    def _get_users_from_yaml(self) -> UsersResponse:
        """Fallback method to get users from YAML configuration"""
        config = self.load_yaml_config("user.yaml")
        users = []

        for user_name, user_config in config.get("users", {}).items():
            user_type_str = user_config.get("type", "PERSON")

            # Parse comment to determine user type
            comment = user_config.get("comment", "")
            if "TYPE=SERVICE" in comment:
                user_type = "SERVICE"
            else:
                user_type = "PERSON"

            user = UserModel(
                name=user_name,
                comment=comment,
                user_type=user_type,
                default_role=user_config.get("default_role"),
                network_policy=user_config.get("network_policy"),
                has_password="password" in user_config,
                has_rsa_public_key="rsa_public_key" in user_config,
            )
            users.append(user)

        total_count = len(users)
        active_count = total_count  # Assume all YAML users are active
        service_count = len([u for u in users if u.is_service])
        mfa_compliant_count = len([u for u in users if u.mfa_compliant])

        return UsersResponse(
            users=users,
            total_count=total_count,
            active_count=active_count,
            service_count=service_count,
            mfa_compliant_count=mfa_compliant_count,
        )

    def create_user(self, user: UserModel) -> UserModel:
        """Create a new user"""
        # Use the existing SnowDDL user management system
        user_data = {
            "name": user.name,
            "comment": user.comment,
            "type": user.user_type.value,
            "default_role": user.default_role,
            "network_policy": user.network_policy,
        }

        # Create user through SnowDDL
        result = self.snowddl_user_manager.create_user_interactive(user_data)

        return user

    def update_user(self, user: UserModel) -> UserModel:
        """Update an existing user"""
        # Update YAML configuration
        config = self.load_yaml_config("user.yaml")
        if "users" not in config:
            config["users"] = {}

        config["users"][user.name] = {
            "comment": user.comment,
            "type": user.user_type.value,
            "default_role": user.default_role,
            "network_policy": user.network_policy,
        }

        self.save_yaml_config("user.yaml", config)
        return user

    def delete_user(self, username: str) -> bool:
        """Delete a user (remove from YAML, optionally drop from Snowflake)"""
        config = self.load_yaml_config("user.yaml")
        if "users" in config and username in config["users"]:
            del config["users"][username]
            self.save_yaml_config("user.yaml", config)
            return True
        return False


class RoleManager(BaseManager):
    """Manager for Role operations"""

    def __init__(
        self,
        project_root: Optional[str] = None,
        client: Optional[SnowflakeClientManager] = None,
    ):
        super().__init__(project_root)
        self.client = client or SnowflakeClientManager(project_root)

    def get_all_roles(self) -> RolesResponse:
        """Get all roles from YAML configurations (Streamlit-compatible)"""
        try:
            # For Streamlit deployment, use YAML-only approach
            return self._get_roles_from_yaml()

        except Exception as e:
            # Fallback to YAML only
            return self._get_roles_from_yaml()

    def _get_roles_from_yaml(self) -> RolesResponse:
        """Fallback method to get roles from YAML configurations only"""
        tech_config = self.load_yaml_config("tech_role.yaml")
        business_config = self.load_yaml_config("business_role.yaml")

        roles = []

        # Technical roles
        for role_name, role_config in tech_config.get("tech_roles", {}).items():
            role = RoleModel(
                name=role_name,
                comment=role_config.get("comment"),
                role_type="TECHNICAL",
                granted_roles=role_config.get("granted_roles", []),
                future_grants=role_config.get("future_grants", {}),
            )
            roles.append(role)

        # Business roles
        for role_name, role_config in business_config.get("business_roles", {}).items():
            role = RoleModel(
                name=role_name,
                comment=role_config.get("comment"),
                role_type="BUSINESS",
                granted_roles=role_config.get("granted_roles", []),
                future_grants=role_config.get("future_grants", {}),
            )
            roles.append(role)

        total_count = len(roles)
        business_roles_count = len([r for r in roles if r.is_business_role])
        technical_roles_count = len([r for r in roles if r.is_technical_role])

        return RolesResponse(
            roles=roles,
            total_count=total_count,
            business_roles_count=business_roles_count,
            technical_roles_count=technical_roles_count,
        )


class WarehouseManager(BaseManager):
    """Manager for Warehouse operations"""

    def __init__(
        self,
        project_root: Optional[str] = None,
        client: Optional[SnowflakeClientManager] = None,
    ):
        super().__init__(project_root)
        self.client = client or SnowflakeClientManager(project_root)

    def get_all_warehouses(self) -> WarehousesResponse:
        """Get all warehouses (Streamlit-compatible)"""
        try:
            # Try to get current warehouse info using supported functions
            current_warehouse_query = "SELECT CURRENT_WAREHOUSE() as current_warehouse"
            current_result = self.client.execute_query(current_warehouse_query)

            # Fallback to YAML with current warehouse info if available
            return self._get_warehouses_from_yaml_with_context(current_result)

        except Exception as e:
            # Fallback to YAML configuration
            return self._get_warehouses_from_yaml()

    def _get_warehouses_from_yaml(self) -> WarehousesResponse:
        """Get warehouses from YAML configuration"""
        config = self.load_yaml_config("warehouse.yaml")
        warehouses = []

        for wh_name, wh_config in config.get("warehouses", {}).items():
            from snowddl_core import WarehouseSize

            size_str = wh_config.get("size", "XSMALL")
            size = getattr(WarehouseSize, size_str.upper(), WarehouseSize.XSMALL)

            warehouse = WarehouseModel(
                name=wh_name,
                size=size,
                comment=wh_config.get("comment"),
                auto_suspend=wh_config.get("auto_suspend", 60),
                auto_resume=wh_config.get("auto_resume", True),
                min_cluster_count=wh_config.get("min_cluster_count", 1),
                max_cluster_count=wh_config.get("max_cluster_count", 1),
                scaling_policy=wh_config.get("scaling_policy", "STANDARD"),
                resource_monitor=wh_config.get("resource_monitor"),
            )
            warehouses.append(warehouse)

        return WarehousesResponse(
            warehouses=warehouses,
            total_count=len(warehouses),
            running_count=0,  # Can't determine state from YAML
            total_credits=0.0,
        )

    def _get_warehouses_from_yaml_with_context(
        self, current_result: List[Dict]
    ) -> WarehousesResponse:
        """Get warehouses from YAML with current warehouse context"""
        config = self.load_yaml_config("warehouse.yaml")
        warehouses = []
        current_warehouse = None

        if current_result and len(current_result) > 0:
            current_warehouse = current_result[0].get("CURRENT_WAREHOUSE")

        for wh_name, wh_config in config.get("warehouses", {}).items():
            from snowddl_core import WarehouseSize

            size_str = wh_config.get("size", "XSMALL")
            size = getattr(WarehouseSize, size_str.upper(), WarehouseSize.XSMALL)

            # If this is the current warehouse, assume it might be running
            state = "RUNNING" if wh_name == current_warehouse else "SUSPENDED"

            warehouse = WarehouseModel(
                name=wh_name,
                size=size,
                comment=wh_config.get("comment"),
                state=state,
                auto_suspend=wh_config.get("auto_suspend", 60),
                auto_resume=wh_config.get("auto_resume", True),
                min_cluster_count=wh_config.get("min_cluster_count", 1),
                max_cluster_count=wh_config.get("max_cluster_count", 1),
                scaling_policy=wh_config.get("scaling_policy", "STANDARD"),
                resource_monitor=wh_config.get("resource_monitor"),
            )
            warehouses.append(warehouse)

        running_count = len([w for w in warehouses if w.state == "RUNNING"])

        return WarehousesResponse(
            warehouses=warehouses,
            total_count=len(warehouses),
            running_count=running_count,
            total_credits=0.0,
        )

    def suspend_warehouse(self, warehouse_name: str) -> bool:
        """Suspend a warehouse"""
        try:
            self.client.execute_ddl(f"ALTER WAREHOUSE {warehouse_name} SUSPEND")
            return True
        except Exception as e:
            print(f"Error suspending warehouse {warehouse_name}: {e}")
            return False

    def resume_warehouse(self, warehouse_name: str) -> bool:
        """Resume a warehouse"""
        try:
            self.client.execute_ddl(f"ALTER WAREHOUSE {warehouse_name} RESUME")
            return True
        except Exception as e:
            print(f"Error resuming warehouse {warehouse_name}: {e}")
            return False

    def update_auto_suspend(
        self, warehouse_name: str, auto_suspend_minutes: int
    ) -> bool:
        """Update auto-suspend timeout for a warehouse"""
        try:
            # Convert minutes to seconds for Snowflake
            auto_suspend_seconds = auto_suspend_minutes * 60
            self.client.execute_ddl(
                f"ALTER WAREHOUSE {warehouse_name} SET AUTO_SUSPEND = {auto_suspend_seconds}"
            )
            return True
        except Exception as e:
            print(f"Error updating auto-suspend for warehouse {warehouse_name}: {e}")
            return False

    def update_auto_resume(self, warehouse_name: str, auto_resume: bool) -> bool:
        """Update auto-resume setting for a warehouse"""
        try:
            auto_resume_str = "TRUE" if auto_resume else "FALSE"
            self.client.execute_ddl(
                f"ALTER WAREHOUSE {warehouse_name} SET AUTO_RESUME = {auto_resume_str}"
            )
            return True
        except Exception as e:
            print(f"Error updating auto-resume for warehouse {warehouse_name}: {e}")
            return False

    def update_warehouse_settings(
        self,
        warehouse_name: str,
        auto_suspend_minutes: int = None,
        auto_resume: bool = None,
    ) -> bool:
        """Update multiple warehouse settings at once"""
        try:
            settings = []
            if auto_suspend_minutes is not None:
                auto_suspend_seconds = auto_suspend_minutes * 60
                settings.append(f"AUTO_SUSPEND = {auto_suspend_seconds}")
            if auto_resume is not None:
                auto_resume_str = "TRUE" if auto_resume else "FALSE"
                settings.append(f"AUTO_RESUME = {auto_resume_str}")

            if settings:
                settings_str = ", ".join(settings)
                self.client.execute_ddl(
                    f"ALTER WAREHOUSE {warehouse_name} SET {settings_str}"
                )
                return True
            return False
        except Exception as e:
            print(f"Error updating warehouse settings for {warehouse_name}: {e}")
            return False

    def optimize_all_warehouses(
        self, target_suspend_minutes: int = 1, enable_auto_resume: bool = True
    ) -> Dict[str, bool]:
        """Optimize all warehouses with cost-saving settings"""
        results = {}
        warehouses_response = self.get_all_warehouses()

        for warehouse in warehouses_response.warehouses:
            success = self.update_warehouse_settings(
                warehouse.name,
                auto_suspend_minutes=target_suspend_minutes,
                auto_resume=enable_auto_resume,
            )
            results[warehouse.name] = success

        return results

    def get_cost_optimization_analysis(self) -> Dict[str, Any]:
        """Analyze warehouses for cost optimization opportunities"""
        warehouses_response = self.get_all_warehouses()
        analysis = {
            "total_warehouses": warehouses_response.total_count,
            "running_warehouses": warehouses_response.running_count,
            "optimized_warehouses": 0,
            "warehouses_needing_optimization": 0,
            "potential_savings": 0.0,
            "warehouse_details": [],
        }

        for warehouse in warehouses_response.warehouses:
            # Convert auto_suspend from seconds to minutes for display
            auto_suspend_minutes = (
                warehouse.auto_suspend // 60 if warehouse.auto_suspend else None
            )

            # Determine optimization status
            is_optimized = (
                warehouse.auto_resume
                and auto_suspend_minutes
                and auto_suspend_minutes
                <= 5  # 5 minutes or less is considered optimized
            )

            if is_optimized:
                analysis["optimized_warehouses"] += 1
                risk_level = "LOW"
            elif auto_suspend_minutes and auto_suspend_minutes <= 60:  # 1 hour
                risk_level = "MEDIUM"
            elif not auto_suspend_minutes or auto_suspend_minutes > 60:
                analysis["warehouses_needing_optimization"] += 1
                risk_level = "HIGH"
            else:
                risk_level = "MEDIUM"

            # Calculate potential savings (rough estimate)
            if warehouse.is_running and not is_optimized:
                # Estimate potential savings based on warehouse size and inefficient settings
                hourly_cost = warehouse.cost_estimate_per_hour
                if auto_suspend_minutes and auto_suspend_minutes > 5:
                    # Assume warehouse runs 2 extra hours per day due to poor auto-suspend
                    daily_waste = hourly_cost * 2
                    analysis["potential_savings"] += daily_waste * 30  # Monthly savings

            warehouse_analysis = {
                "name": warehouse.name,
                "size": (
                    warehouse.size.value
                    if hasattr(warehouse.size, "value")
                    else str(warehouse.size)
                ),
                "state": warehouse.state,
                "auto_suspend_minutes": auto_suspend_minutes,
                "auto_resume": warehouse.auto_resume,
                "is_optimized": is_optimized,
                "risk_level": risk_level,
                "hourly_cost_estimate": warehouse.cost_estimate_per_hour,
                "optimization_recommendations": [],
            }

            # Add recommendations
            if not warehouse.auto_resume:
                warehouse_analysis["optimization_recommendations"].append(
                    "Enable auto-resume to prevent delays"
                )
            if not auto_suspend_minutes:
                warehouse_analysis["optimization_recommendations"].append(
                    "Set auto-suspend to prevent unnecessary costs"
                )
            elif auto_suspend_minutes > 5:
                warehouse_analysis["optimization_recommendations"].append(
                    f"Reduce auto-suspend from {auto_suspend_minutes} to 1-5 minutes"
                )

            analysis["warehouse_details"].append(warehouse_analysis)

        return analysis


class DatabaseManager(BaseManager):
    """Manager for Database operations"""

    def __init__(
        self,
        project_root: Optional[str] = None,
        client: Optional[SnowflakeClientManager] = None,
    ):
        super().__init__(project_root)
        self.client = client or SnowflakeClientManager(project_root)

    def get_all_databases(self) -> DatabasesResponse:
        """Get all databases (Streamlit-compatible)"""
        try:
            # Try to get current database info
            current_db_query = "SELECT CURRENT_DATABASE() as current_database"
            current_result = self.client.execute_query(current_db_query)

            # Use directory-based discovery with current database context
            return self._get_databases_from_directories_with_context(current_result)

        except Exception as e:
            # Fallback to directory-based discovery
            return self._get_databases_from_directories()

    def _get_database_schemas(self, database_name: str) -> List[str]:
        """Get schemas for a specific database (Streamlit-compatible)"""
        try:
            # For Streamlit, we can't query information_schema reliably
            # Return empty list or try to determine from YAML structure
            return []

        except Exception:
            return []

    def _get_databases_from_directories(self) -> DatabasesResponse:
        """Get databases from directory structure"""
        databases = []
        total_schemas = 0

        # Look for database directories in snowddl/
        for item in self.snowddl_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # Check if it has a params.yaml file (indicates database)
                params_file = item / "params.yaml"
                if params_file.exists():
                    database = DatabaseModel(
                        name=item.name,
                        comment=f"Database directory: {item.name}",
                    )
                    databases.append(database)

        return DatabasesResponse(
            databases=databases,
            total_count=len(databases),
            total_schemas=total_schemas,
        )

    def _get_databases_from_directories_with_context(
        self, current_result: List[Dict]
    ) -> DatabasesResponse:
        """Get databases from directory structure with current database context"""
        databases = []
        total_schemas = 0
        current_database = None

        if current_result and len(current_result) > 0:
            current_database = current_result[0].get("CURRENT_DATABASE")

        # Always include current database if known
        if current_database:
            database = DatabaseModel(
                name=current_database,
                comment=f"Current database: {current_database}",
                owner="Current User",
            )
            databases.append(database)

        # Look for database directories in snowddl/
        for item in self.snowddl_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # Check if it has a params.yaml file (indicates database)
                params_file = item / "params.yaml"
                if params_file.exists() and item.name != current_database:
                    database = DatabaseModel(
                        name=item.name,
                        comment=f"Database directory: {item.name}",
                    )
                    databases.append(database)

        return DatabasesResponse(
            databases=databases,
            total_count=len(databases),
            total_schemas=total_schemas,
        )


class SchemaManager(BaseManager):
    """Manager for Schema operations"""

    def __init__(
        self,
        project_root: Optional[str] = None,
        client: Optional[SnowflakeClientManager] = None,
    ):
        super().__init__(project_root)
        self.client = client or SnowflakeClientManager(project_root)


class SecurityPolicyManager(BaseManager):
    """Manager for Security Policy operations"""

    def __init__(
        self,
        project_root: Optional[str] = None,
        client: Optional[SnowflakeClientManager] = None,
    ):
        super().__init__(project_root)
        self.client = client or SnowflakeClientManager(project_root)

    def get_all_policies(self) -> List[SecurityPolicyModel]:
        """Get all security policies"""
        policies = []

        # Load different policy types
        policy_files = {
            "network_policy.yaml": "NETWORK",
            "password_policy.yaml": "PASSWORD",
            "session_policy.yaml": "SESSION",
            "authentication_policy.yaml": "AUTHENTICATION",
        }

        for filename, policy_type in policy_files.items():
            config = self.load_yaml_config(filename)

            # Handle different YAML structures
            if policy_type == "NETWORK":
                for policy_name, policy_config in config.get(
                    "network_policies", {}
                ).items():
                    policy = SecurityPolicyModel(
                        name=policy_name,
                        policy_type=policy_type,
                        comment=policy_config.get("comment"),
                        config=policy_config,
                    )
                    policies.append(policy)

            elif policy_type == "PASSWORD":
                for policy_name, policy_config in config.get(
                    "password_policies", {}
                ).items():
                    policy = SecurityPolicyModel(
                        name=policy_name,
                        policy_type=policy_type,
                        comment=policy_config.get("comment"),
                        config=policy_config,
                    )
                    policies.append(policy)

        return policies
