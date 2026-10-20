"""User schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ════════════════════════════════════════════════════════════════
# CREATE
# ════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    username: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[a-z0-9_\.]+$"
    )
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    is_active: bool = True
    # Service layer forbids non-superuser actors from setting this to True.
    # Kept in the schema so superuser actor CAN create superusers.
    is_superuser: bool = False
    role_names: list[str] = Field(default_factory=list)

    @field_validator("full_name")
    @classmethod
    def _strip_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("full_name cannot be blank")
        return v


# ════════════════════════════════════════════════════════════════
# UPDATE
# ════════════════════════════════════════════════════════════════

class UserUpdate(BaseModel):
    """
    Partial update. `is_superuser` is intentionally NOT here — privilege
    elevation must go through the dedicated `/users/{id}/promote` endpoint
    (not implemented yet) or migration. Username is also immutable.
    """
    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=2, max_length=255)
    is_active: bool | None = None
    role_names: list[str] | None = None

    @field_validator("full_name")
    @classmethod
    def _non_nullable_full_name(cls, v):
        if v is None:
            raise ValueError("full_name cannot be null")
        v = v.strip()
        if not v:
            raise ValueError("full_name cannot be blank")
        return v

    @field_validator("is_active")
    @classmethod
    def _non_nullable_is_active(cls, v):
        if v is None:
            raise ValueError("is_active cannot be null")
        return v


# ════════════════════════════════════════════════════════════════
# PASSWORD
# ════════════════════════════════════════════════════════════════

class SelfPasswordChange(BaseModel):
    """
    Self-service password change. Requires old_password to prevent
    session-hijacking users from locking out the real owner.
    Served by POST /users/me/password.
    """
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _must_differ(cls, v: str, info) -> str:
        old = info.data.get("old_password")
        if old is not None and v == old:
            raise ValueError("new_password must differ from old_password")
        return v


class AdminPasswordReset(BaseModel):
    """
    Admin-driven password reset. No old_password required — the actor's
    USER_UPDATE permission is the authorization.
    Served by POST /users/{id}/reset-password.
    """
    new_password: str = Field(..., min_length=8, max_length=128)


# ════════════════════════════════════════════════════════════════
# READ
# ════════════════════════════════════════════════════════════════

class UserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None
    created_at: datetime


class UserDetail(UserListItem):
    roles: list[str] = Field(default_factory=list)