from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ════════════════════════════════════════════════════════════════
# READ
# ════════════════════════════════════════════════════════════════

class SettingItem(BaseModel):
    """
    Safe view of a setting. For `is_secret=True` rows, `value` is
    replaced with "***" unless the caller explicitly reveals it.
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    value: str | None
    category: str
    description: str | None
    is_secret: bool


class SettingItemRaw(SettingItem):
    """Same shape — used only when the caller has requested raw values."""
    pass


# ════════════════════════════════════════════════════════════════
# WRITE
# ════════════════════════════════════════════════════════════════

class SettingUpdate(BaseModel):
    """
    Update an existing setting or create a new one.

    All fields except `value` are optional. When `is_secret` is True
    on the resulting row, the raw value is:
      - masked in API responses
      - redacted in the audit log
    """
    value: str | None = Field(None, max_length=10_000)
    category: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=255)
    is_secret: bool | None = None

    @field_validator("value")
    @classmethod
    def _strip_value(cls, v):
        if isinstance(v, str) and v == "":
            return None
        return v


class SettingBulkUpdateItem(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str | None = Field(None, max_length=10_000)

    @field_validator("value")
    @classmethod
    def _strip_value(cls, v):
        if isinstance(v, str) and v == "":
            return None
        return v


class SettingBulkUpdate(BaseModel):
    items: list[SettingBulkUpdateItem] = Field(..., min_length=1, max_length=200)


# ════════════════════════════════════════════════════════════════
# CATALOG
# ════════════════════════════════════════════════════════════════

class KnownSettingInfo(BaseModel):
    key: str
    category: str
    description: str
    is_secret: bool


class SettingsCatalog(BaseModel):
    known_settings: list[KnownSettingInfo]
    categories: list[str]