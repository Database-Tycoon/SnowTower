"""
SnowTower Core Models

Pydantic models that extend the SnowDDL objects with web interface support.
These models provide validation, serialization, and CRUD operation support
for the Streamlit web interface.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

# Import base SnowDDL objects
from snowddl_core import (
    User as SnowDDLUser,
    BusinessRole as SnowDDLBusinessRole,
    TechnicalRole as SnowDDLTechnicalRole,
    Warehouse as SnowDDLWarehouse,
    WarehouseSize,
)
from snowddl_core.snowddl_types import UserType


class UserStatus(str, Enum):
    """User status enumeration"""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LOCKED = "LOCKED"


class AuthenticationMethod(str, Enum):
    """Authentication method enumeration"""

    PASSWORD = "PASSWORD"
    RSA_KEY = "RSA_KEY"
    MFA = "MFA"
    DUAL_AUTH = "DUAL_AUTH"


class UserModel(BaseModel):
    """Extended User model for web interface"""

    name: str = Field(..., description="User name (uppercase)")
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    email: Optional[str] = Field(None, description="User email address")
    comment: Optional[str] = Field(None, description="User description/comment")
    user_type: UserType = Field("PERSON", description="User type (PERSON or SERVICE)")
    status: UserStatus = Field(UserStatus.ACTIVE, description="User status")

    # Authentication
    has_password: bool = Field(False, description="User has password authentication")
    has_rsa_public_key: bool = Field(
        False, description="User has RSA key authentication"
    )
    has_mfa: bool = Field(False, description="User has MFA enabled")
    authentication_methods: List[AuthenticationMethod] = Field(default_factory=list)

    # Role assignments
    default_role: Optional[str] = Field(None, description="Default role")
    roles: List[str] = Field(default_factory=list, description="Assigned roles")

    # Network and security
    network_policy: Optional[str] = Field(None, description="Network policy")
    password_policy: Optional[str] = Field(None, description="Password policy")
    session_policy: Optional[str] = Field(None, description="Session policy")

    # Metadata
    created_on: Optional[datetime] = Field(None, description="Creation timestamp")
    last_success_login: Optional[datetime] = Field(
        None, description="Last successful login"
    )

    @validator("name")
    def name_must_be_uppercase(cls, v):
        return v.upper()

    @property
    def is_human(self) -> bool:
        """Check if user is a human user"""
        return self.user_type == "PERSON"

    @property
    def is_service(self) -> bool:
        """Check if user is a service account"""
        return self.user_type == "SERVICE"

    @property
    def mfa_compliant(self) -> bool:
        """Check if user is MFA compliant"""
        if self.is_service:
            return self.has_rsa_public_key  # Service accounts need RSA keys
        else:
            return self.has_mfa or (self.has_password and self.has_rsa_public_key)

    def to_snowddl_object(self) -> SnowDDLUser:
        """Convert to SnowDDL User object"""
        return SnowDDLUser(
            name=self.name,
            comment=self.comment,
            user_type=self.user_type,
            default_role=self.default_role,
            network_policy=self.network_policy,
        )


class RoleModel(BaseModel):
    """Extended Role model for web interface"""

    name: str = Field(..., description="Role name (uppercase)")
    comment: Optional[str] = Field(None, description="Role description")
    role_type: str = Field("TECHNICAL", description="Role type (TECHNICAL or BUSINESS)")

    # Role hierarchy
    parent_roles: List[str] = Field(default_factory=list, description="Parent roles")
    child_roles: List[str] = Field(default_factory=list, description="Child roles")

    # Permissions
    granted_roles: List[str] = Field(default_factory=list, description="Granted roles")
    future_grants: Dict[str, List[str]] = Field(
        default_factory=dict, description="Future grants"
    )

    # Members
    users: List[str] = Field(default_factory=list, description="Users with this role")

    @validator("name")
    def name_must_be_uppercase(cls, v):
        return v.upper()

    @property
    def is_business_role(self) -> bool:
        """Check if role is a business role"""
        return self.role_type == "BUSINESS" or self.name.startswith("__B_")

    @property
    def is_technical_role(self) -> bool:
        """Check if role is a technical role"""
        return self.role_type == "TECHNICAL" or self.name.startswith("__T_")


class WarehouseModel(BaseModel):
    """Extended Warehouse model for web interface"""

    name: str = Field(..., description="Warehouse name (uppercase)")
    size: WarehouseSize = Field(WarehouseSize.XSMALL, description="Warehouse size")
    comment: Optional[str] = Field(None, description="Warehouse description")

    # Configuration
    auto_suspend: int = Field(60, description="Auto-suspend timeout in seconds")
    auto_resume: bool = Field(True, description="Auto-resume enabled")
    min_cluster_count: int = Field(1, description="Minimum cluster count")
    max_cluster_count: int = Field(1, description="Maximum cluster count")
    scaling_policy: str = Field("STANDARD", description="Scaling policy")

    # State
    state: str = Field("SUSPENDED", description="Current warehouse state")

    # Resource monitoring
    resource_monitor: Optional[str] = Field(None, description="Resource monitor")

    # Cost information
    credits_used: Optional[float] = Field(None, description="Credits used")
    credits_used_compute: Optional[float] = Field(
        None, description="Compute credits used"
    )

    @validator("name")
    def name_must_be_uppercase(cls, v):
        return v.upper()

    @property
    def is_running(self) -> bool:
        """Check if warehouse is running"""
        return self.state == "STARTED"

    @property
    def cost_estimate_per_hour(self) -> float:
        """Estimate hourly cost based on size"""
        cost_mapping = {
            WarehouseSize.XSMALL: 1.0,
            WarehouseSize.SMALL: 2.0,
            WarehouseSize.MEDIUM: 4.0,
            WarehouseSize.LARGE: 8.0,
            WarehouseSize.XLARGE: 16.0,
            WarehouseSize.XXLARGE: 32.0,
            WarehouseSize.XXXLARGE: 64.0,
        }
        return cost_mapping.get(self.size, 1.0)

    @property
    def auto_suspend_minutes(self) -> Optional[int]:
        """Get auto-suspend timeout in minutes"""
        if self.auto_suspend:
            return self.auto_suspend // 60
        return None

    @property
    def is_cost_optimized(self) -> bool:
        """Check if warehouse has cost-optimized settings"""
        return (
            self.auto_resume
            and self.auto_suspend_minutes is not None
            and self.auto_suspend_minutes
            <= 5  # 5 minutes or less is considered optimized
        )

    @property
    def optimization_risk_level(self) -> str:
        """Get risk level for cost optimization"""
        if self.is_cost_optimized:
            return "LOW"
        elif self.auto_suspend_minutes and self.auto_suspend_minutes <= 60:  # 1 hour
            return "MEDIUM"
        else:
            return "HIGH"

    @property
    def optimization_recommendations(self) -> List[str]:
        """Get list of optimization recommendations"""
        recommendations = []

        if not self.auto_resume:
            recommendations.append("Enable auto-resume to prevent delays")

        if not self.auto_suspend_minutes:
            recommendations.append("Set auto-suspend to prevent unnecessary costs")
        elif self.auto_suspend_minutes > 5:
            recommendations.append(
                f"Reduce auto-suspend from {self.auto_suspend_minutes} to 1-5 minutes"
            )

        return recommendations

    def to_snowddl_object(self) -> SnowDDLWarehouse:
        """Convert to SnowDDL Warehouse object"""
        return SnowDDLWarehouse(
            name=self.name,
            size=self.size,
            comment=self.comment,
            auto_suspend=self.auto_suspend,
            auto_resume=self.auto_resume,
            min_cluster_count=self.min_cluster_count,
            max_cluster_count=self.max_cluster_count,
            scaling_policy=self.scaling_policy,
            resource_monitor=self.resource_monitor,
        )


class DatabaseModel(BaseModel):
    """Extended Database model for web interface"""

    name: str = Field(..., description="Database name (uppercase)")
    comment: Optional[str] = Field(None, description="Database description")

    # Database properties
    transient: bool = Field(False, description="Transient database")
    data_retention_time_in_days: int = Field(1, description="Data retention period")

    # Schemas
    schemas: List[str] = Field(default_factory=list, description="Database schemas")

    # Metadata
    created_on: Optional[datetime] = Field(None, description="Creation timestamp")
    owner: Optional[str] = Field(None, description="Database owner")

    @validator("name")
    def name_must_be_uppercase(cls, v):
        return v.upper()


class SchemaModel(BaseModel):
    """Extended Schema model for web interface"""

    name: str = Field(..., description="Schema name (uppercase)")
    database: str = Field(..., description="Parent database name")
    comment: Optional[str] = Field(None, description="Schema description")

    # Schema properties
    transient: bool = Field(False, description="Transient schema")
    managed_access: bool = Field(False, description="Managed access enabled")
    data_retention_time_in_days: int = Field(1, description="Data retention period")

    # Objects
    tables: List[str] = Field(default_factory=list, description="Schema tables")
    views: List[str] = Field(default_factory=list, description="Schema views")
    functions: List[str] = Field(default_factory=list, description="Schema functions")
    procedures: List[str] = Field(default_factory=list, description="Schema procedures")

    # Metadata
    created_on: Optional[datetime] = Field(None, description="Creation timestamp")
    owner: Optional[str] = Field(None, description="Schema owner")

    @validator("name")
    def name_must_be_uppercase(cls, v):
        return v.upper()

    @validator("database")
    def database_must_be_uppercase(cls, v):
        return v.upper()


class SecurityPolicyModel(BaseModel):
    """Security policy model for web interface"""

    name: str = Field(..., description="Policy name (uppercase)")
    policy_type: str = Field(
        ..., description="Policy type (NETWORK, PASSWORD, SESSION, etc.)"
    )
    comment: Optional[str] = Field(None, description="Policy description")

    # Policy configuration (flexible to handle different policy types)
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Policy configuration"
    )

    # Applied to
    applied_to_users: List[str] = Field(
        default_factory=list, description="Users with this policy"
    )
    applied_to_accounts: List[str] = Field(
        default_factory=list, description="Accounts with this policy"
    )

    @validator("name")
    def name_must_be_uppercase(cls, v):
        return v.upper()


# Collection models for API responses
class UsersResponse(BaseModel):
    """Response model for users list"""

    users: List[UserModel]
    total_count: int
    active_count: int
    service_count: int
    mfa_compliant_count: int


class WarehousesResponse(BaseModel):
    """Response model for warehouses list"""

    warehouses: List[WarehouseModel]
    total_count: int
    running_count: int
    total_credits: float


class DatabasesResponse(BaseModel):
    """Response model for databases list"""

    databases: List[DatabaseModel]
    total_count: int
    total_schemas: int


class RolesResponse(BaseModel):
    """Response model for roles list"""

    roles: List[RoleModel]
    total_count: int
    business_roles_count: int
    technical_roles_count: int
