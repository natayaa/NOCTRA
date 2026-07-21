# modules/auth/schemas.py
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List

from core.constants import UserStatus


# ============================================================================
# User Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Schema untuk membuat user baru."""
    username: str = Field(..., min_length=3, max_length=50,
                          description="Username")
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., min_length=8,
                          max_length=100, description="Password")
    full_name: str = Field(..., min_length=1,
                           max_length=100, description="Nama lengkap")
    phone: Optional[str] = Field(
        None, max_length=20, description="Nomor telepon")
    department: Optional[str] = Field(
        None, max_length=100, description="Departemen")
    position: Optional[str] = Field(
        None, max_length=100, description="Jabatan")
    role_ids: Optional[List[UUID]] = Field(None, description="ID roles")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v.isalnum() and "_" not in v:
            raise ValueError(
                "Username must be alphanumeric or contain underscore")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError(
                "Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError(
                "Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserUpdate(BaseModel):
    """Schema untuk update user."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None)
    status: Optional[str] = Field(
        None, description="active, inactive, suspended")
    role_ids: Optional[List[UUID]] = None


class UserResponse(BaseModel):
    """Response untuk user."""
    id: UUID
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    status: str
    is_superuser: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    roles: List["RoleResponse"] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserLogin(BaseModel):
    """Schema untuk login."""
    username_or_email: str = Field(..., description="Username atau Email")
    password: str = Field(..., description="Password")


class UserRegister(BaseModel):
    """Schema untuk registrasi user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v.isalnum() and "_" not in v:
            raise ValueError(
                "Username must be alphanumeric or contain underscore")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError(
                "Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError(
                "Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class TokenResponse(BaseModel):
    """Response untuk token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Request untuk refresh token."""
    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Request untuk change password."""
    old_password: str = Field(..., description="Password lama")
    new_password: str = Field(..., min_length=8,
                              max_length=100, description="Password baru")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError(
                "Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError(
                "Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class ForgotPasswordRequest(BaseModel):
    """Request untuk forgot password."""
    email: EmailStr = Field(..., description="Email")


class ResetPasswordRequest(BaseModel):
    """Request untuk reset password."""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8,
                              max_length=100, description="Password baru")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError(
                "Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError(
                "Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


# ============================================================================
# Role & Permission Schemas
# ============================================================================

class RoleCreate(BaseModel):
    """Schema untuk membuat role."""
    name: str = Field(..., min_length=2, max_length=50,
                      description="Nama role")
    display_name: str = Field(..., min_length=1,
                              max_length=100, description="Nama tampilan")
    description: Optional[str] = Field(None, description="Deskripsi")
    permission_ids: Optional[List[UUID]] = Field(
        None, description="ID permissions")


class RoleUpdate(BaseModel):
    """Schema untuk update role."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[UUID]] = None


class RoleResponse(BaseModel):
    """Response untuk role."""
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime
    permissions: List["PermissionResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PermissionCreate(BaseModel):
    """Schema untuk membuat permission."""
    name: str = Field(..., min_length=2, max_length=100,
                      description="Format: module:action")
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    module: str = Field(..., min_length=2, max_length=50)
    action: str = Field(..., min_length=2, max_length=50)


class PermissionResponse(BaseModel):
    """Response untuk permission."""
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    module: str
    action: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleCreate(BaseModel):
    """Schema untuk assign role ke user."""
    role_id: UUID = Field(..., description="ID role")


class UserRoleUpdate(BaseModel):
    """Schema untuk update role assignment."""
    role_id: UUID = Field(..., description="ID role baru")


class UserRoleResponse(BaseModel):
    """Response untuk role assignment."""
    id: UUID
    user_id: UUID
    role_id: UUID
    role_name: Optional[str] = None
    assigned_at: datetime
    assigned_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Update forward references
# ============================================================================

UserResponse.model_rebuild()
RoleResponse.model_rebuild()
