from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SettingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    value: str | None
    category: str
    description: str | None
    is_secret: bool


class SettingUpdate(BaseModel):
    value: str | None = Field(None, max_length=10_000)