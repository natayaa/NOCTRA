from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    # Login must NOT enforce password strength — registration does that.
    # A legacy user with a 6-char password would otherwise be locked out
    # with a 422 before the service ever runs.
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    # Optional: browser clients send the refresh token via HttpOnly cookie.
    refresh_token: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    full_name: str


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None
    roles: list[str] = []
    permissions: list[str] = []

    @field_validator("roles", mode="before")
    @classmethod
    def _roles_to_names(cls, v):
        if not v:
            return []
        if hasattr(v[0], "name"):
            return [r.name for r in v]
        return v