from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


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

    @field_validator("roles", mode="before")
    @classmethod
    def _roles_to_names(cls, v):
        if v and hasattr(v[0], "name"):
            return [r.name for r in v]
        return v