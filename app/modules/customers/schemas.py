from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PHONE_PATTERN = r"^[0-9+\-\s()]{6,32}$"

_EMPTY_VALUES = {"", "none", "null", "undefined", "nil"}


def _normalize_optional_str(v):
    """Convert null-ish inputs to real None. Reject nothing else."""
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in _EMPTY_VALUES:
        return None


# ── Customer Contacts ───────────────────────────────────────
class CustomerContactIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    role: str | None = Field(None, max_length=64)
    phone: str | None = Field(None, pattern=PHONE_PATTERN)
    email: EmailStr | None = None
    notes: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def _blank_email_to_none(cls, v):
        return v or None


class CustomerContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    role: str | None
    phone: str | None
    email: EmailStr | None
    notes: str | None
    created_at: datetime


# ── Create / Update ─────────────────────────────────────────
class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, pattern=PHONE_PATTERN)
    alt_phone: str | None = Field(None, pattern=PHONE_PATTERN)

    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    province: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str = Field("Indonesia", max_length=64)

    tax_id: str | None = Field(None, max_length=64)
    notes: str | None = None
    source: str | None = Field(None, max_length=32)

    @field_validator("email", mode="before")
    @classmethod
    def _blank_email_to_none(cls, v):
        return v or None
    
    @field_validator("email", "phone", "alt_phone", "tax_id", mode="before")
    @classmethod
    def _clean_optional(cls, v):
        return _normalize_optional_str(v)


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, pattern=PHONE_PATTERN)
    alt_phone: str | None = Field(None, pattern=PHONE_PATTERN)

    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    country: str | None = None

    tax_id: str | None = None
    notes: str | None = None
    status: str | None = None
    is_active: bool | None = None

    @field_validator("email", "phone", "alt_phone", "tax_id", mode="before")
    @classmethod
    def _clean_optional(cls, v):
        return _normalize_optional_str(v)


# ── Output ──────────────────────────────────────────────────
class CustomerListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    email: EmailStr | None
    phone: str | None
    city: str | None
    status: str
    is_active: bool
    created_at: datetime


class CustomerDetail(CustomerListItem):
    alt_phone: str | None
    address_line1: str | None
    address_line2: str | None
    province: str | None
    postal_code: str | None
    country: str
    tax_id: str | None
    notes: str | None
    source: str | None
    updated_at: datetime
    contacts: list[CustomerContactOut] = Field(default_factory=list)