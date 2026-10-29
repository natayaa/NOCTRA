from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.types import Email
from app.modules.customers.constants import CUSTOMER_SOURCES, CUSTOMER_STATUSES

PHONE_PATTERN = r"^[0-9+\-\s()]{6,32}$"
_EMPTY_VALUES = {"", "none", "null", "undefined", "nil"}


def _normalize_optional_str(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in _EMPTY_VALUES:
        return None
    return s


def _strip_required_name(v):
    """Strip whitespace and reject blank names BEFORE length checks."""
    if isinstance(v, str):
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
    return v


# ── Customer Contacts ───────────────────────────────────────
class CustomerContactIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    role: str | None = Field(None, max_length=64)
    phone: str | None = Field(None, pattern=PHONE_PATTERN)
    email: Email | None = None
    notes: str | None = Field(None, max_length=2000)

    @field_validator("name", mode="before")
    @classmethod
    def _clean_name(cls, v):
        return _strip_required_name(v)

    @field_validator("email", "phone", "role", "notes", mode="before")
    @classmethod
    def _clean_optional(cls, v):
        return _normalize_optional_str(v)


class CustomerContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    role: str | None
    phone: str | None
    email: Email | None
    notes: str | None
    created_at: datetime


# ── Create / Update ─────────────────────────────────────────
class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: Email | None = None
    phone: str | None = Field(None, pattern=PHONE_PATTERN)
    alt_phone: str | None = Field(None, pattern=PHONE_PATTERN)

    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    province: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    # min_length=1 after strip — `""` and `"   "` are rejected.
    country: str = Field("Indonesia", min_length=1, max_length=64)

    tax_id: str | None = Field(None, max_length=64)
    notes: str | None = Field(None, max_length=5000)
    source: str | None = Field(None, max_length=32)

    @field_validator("name", mode="before")
    @classmethod
    def _clean_name(cls, v):
        return _strip_required_name(v)

    @field_validator(
        "email", "phone", "alt_phone", "tax_id",
        "address_line1", "address_line2", "city", "province",
        "postal_code", "notes", mode="before",
    )
    @classmethod
    def _clean_optional(cls, v):
        return _normalize_optional_str(v)

    @field_validator("country", mode="before")
    @classmethod
    def _strip_country(cls, v):
        # Let min_length=1 catch the blank-after-strip case for a 422.
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("source")
    @classmethod
    def _validate_source(cls, v):
        if v is not None and v not in CUSTOMER_SOURCES:
            raise ValueError(f"source must be one of {CUSTOMER_SOURCES}")
        return v


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    email: Email | None = None
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

    @field_validator("name", mode="before")
    @classmethod
    def _clean_name(cls, v):
        return _strip_required_name(v)

    @field_validator(
        "email", "phone", "alt_phone", "tax_id",
        "address_line1", "address_line2", "city", "province",
        "postal_code", "notes", "country", mode="before",
    )
    @classmethod
    def _clean_optional(cls, v):
        # `country=""` is normalised to `None` — the service then raises
        # "country cannot be null" rather than writing an empty string.
        return _normalize_optional_str(v)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v):
        if v is not None and v not in CUSTOMER_STATUSES:
            raise ValueError(f"status must be one of {CUSTOMER_STATUSES}")
        return v


# ── Output ──────────────────────────────────────────────────
class CustomerListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    email: Email | None
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


class CustomerSearchResult(BaseModel):
    """Lightweight shape for autocomplete pickers."""
    id: UUID
    code: str
    name: str
    phone: str | None
    city: str | None
    label: str
    sublabel: str
    is_active: bool