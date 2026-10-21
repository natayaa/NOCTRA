"""Pydantic schemas for the inquiries module."""
from __future__ import annotations

import json
from datetime import date, datetime
from urllib.parse import unquote, urlparse
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.config import settings
from app.modules.inquiries.constants import (
    BUDGET_RANGES,
    COLOR_FAMILIES,
    FINISH_TYPES,
    INQUIRY_SOURCES,
    INQUIRY_STATUSES,
    SERVICE_INTERESTS,
    today_local,
)

# Guard against oversized JSONB payloads. `preferences` is user-supplied
# and never needed for pricing/queries, so a generous upper bound is fine.
_MAX_PREFERENCES_KEYS = 50
_MAX_PREFERENCES_BYTES = 10_000


# ════════════════════════════════════════════════════════════════
# PHOTOS
# ════════════════════════════════════════════════════════════════

class InquiryPhotoIn(BaseModel):
    file_path: str = Field(..., min_length=1, max_length=500)
    file_name: str | None = Field(None, max_length=255)
    caption: str | None = Field(None, max_length=500)
    is_primary: bool = False

    @field_validator("file_path")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        v = v.strip()

        if v.startswith("/"):
            if not any(v.startswith(p) for p in settings.MEDIA_URL_PREFIXES):
                raise ValueError(
                    f"Internal media path must start with one of: "
                    f"{', '.join(settings.MEDIA_URL_PREFIXES)}"
                )
            decoded = unquote(v)
            if ".." in decoded.split("/"):
                raise ValueError("Path traversal is not allowed")
            if "\x00" in v:
                raise ValueError("Null byte in path")
            return v

        if v.startswith(("http://", "https://")):
            parsed = urlparse(v)
            if not parsed.hostname:
                raise ValueError("URL must include a hostname")

            if not settings.MEDIA_ALLOWED_HOSTS:
                raise ValueError(
                    "External URLs are not allowed. "
                    "Upload the file via the media pipeline instead."
                )

            host = parsed.hostname.lower()
            for allowed in settings.MEDIA_ALLOWED_HOSTS:
                allowed = allowed.lower()
                if allowed.startswith("*.") and host.endswith(allowed[1:]):
                    return v
                if host == allowed:
                    return v
            raise ValueError(
                f"Host {host!r} is not in the allowed media hosts list"
            )

        raise ValueError(
            "file_path must be an internal /media/ path or an allowlisted "
            "http(s) URL"
        )


class InquiryPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    file_path: str
    file_name: str | None
    caption: str | None
    is_primary: bool
    created_at: datetime


# ════════════════════════════════════════════════════════════════
# CUSTOMER REQUEST BLOCK
# ════════════════════════════════════════════════════════════════

class CustomerRequestMixin(BaseModel):
    color_preference: str | None = Field(None, max_length=64)
    color_family: str | None = None
    finish_preference: str | None = None
    has_custom_graphics: bool | None = None
    preferences: dict | None = None

    @field_validator("color_family")
    @classmethod
    def _validate_color_family(cls, v):
        if v is not None and v not in COLOR_FAMILIES:
            raise ValueError(f"color_family must be one of {COLOR_FAMILIES}")
        return v

    @field_validator("finish_preference")
    @classmethod
    def _validate_finish(cls, v):
        if v is not None and v not in FINISH_TYPES:
            raise ValueError(f"finish_preference must be one of {FINISH_TYPES}")
        return v

    @field_validator("has_custom_graphics")
    @classmethod
    def _non_nullable_bool(cls, v):
        if v is None:
            raise ValueError("has_custom_graphics cannot be null")
        return v

    @field_validator("preferences")
    @classmethod
    def _check_preferences_size(cls, v):
        if v is None:
            return v
        if len(v) > _MAX_PREFERENCES_KEYS:
            raise ValueError(
                f"preferences cannot have more than {_MAX_PREFERENCES_KEYS} keys"
            )
        try:
            serialized = json.dumps(v)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"preferences must be JSON-serializable: {exc}"
            ) from exc
        if len(serialized) > _MAX_PREFERENCES_BYTES:
            raise ValueError(
                f"preferences exceeds {_MAX_PREFERENCES_BYTES} bytes when serialized"
            )
        return v


# ════════════════════════════════════════════════════════════════
# CREATE / UPDATE
# ════════════════════════════════════════════════════════════════

class InquiryCreate(CustomerRequestMixin):
    customer_id: UUID | None = None
    vehicle_id: UUID | None = None

    service_interest: str | None = Field(None, max_length=32)
    description: str = Field(..., min_length=20, max_length=5000)

    source: str = "ADMIN"
    budget_range: str | None = None
    desired_date: date | None = None
    follow_up_date: date | None = None
    notes: str | None = Field(None, max_length=5000)

    @field_validator("description", mode="before")
    @classmethod
    def _strip_description(cls, v):
        # Strip BEFORE length validation — otherwise a 20-space payload
        # passes `min_length=20` and is stored as an empty string.
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("service_interest")
    @classmethod
    def _validate_service(cls, v):
        if v is not None and v not in SERVICE_INTERESTS:
            raise ValueError(f"service_interest must be one of {SERVICE_INTERESTS}")
        return v

    @field_validator("source")
    @classmethod
    def _validate_source(cls, v):
        if v not in INQUIRY_SOURCES:
            raise ValueError(f"source must be one of {INQUIRY_SOURCES}")
        return v

    @field_validator("budget_range")
    @classmethod
    def _validate_budget(cls, v):
        if v is not None and v not in BUDGET_RANGES:
            raise ValueError(f"budget_range must be one of {BUDGET_RANGES}")
        return v

    @model_validator(mode="after")
    def _validate_dates(self):
        today = today_local()
        if self.desired_date and self.desired_date < today:
            raise ValueError("desired_date cannot be in the past")
        if self.follow_up_date and self.follow_up_date < today:
            raise ValueError("follow_up_date cannot be in the past")
        if (
            self.desired_date
            and self.follow_up_date
            and self.follow_up_date > self.desired_date
        ):
            raise ValueError("follow_up_date must be on or before desired_date")
        return self


class InquiryUpdate(CustomerRequestMixin):
    """Partial update. All fields optional."""

    customer_id: UUID | None = None
    vehicle_id: UUID | None = None
    service_interest: str | None = Field(None, max_length=32)
    description: str | None = Field(None, min_length=20, max_length=5000)
    budget_range: str | None = None
    desired_date: date | None = None
    follow_up_date: date | None = None
    notes: str | None = Field(None, max_length=5000)

    @field_validator("description", mode="before")
    @classmethod
    def _strip_description(cls, v):
        # Same reasoning as InquiryCreate — strip before length check.
        # `None` is allowed (field not being updated).
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("service_interest")
    @classmethod
    def _validate_service(cls, v):
        if v is not None and v not in SERVICE_INTERESTS:
            raise ValueError(f"service_interest must be one of {SERVICE_INTERESTS}")
        return v

    @field_validator("budget_range")
    @classmethod
    def _validate_budget(cls, v):
        if v is not None and v not in BUDGET_RANGES:
            raise ValueError(f"budget_range must be one of {BUDGET_RANGES}")
        return v

    # Cross-field date ordering is checked in the service layer AFTER
    # merging with the current state — a PATCH may supply only one date,
    # and we still want to catch `follow_up_date > desired_date` against
    # the existing counterpart. Doing it in the schema would only catch
    # the case where both fields are in the payload.


class InquiryAssign(BaseModel):
    assigned_to_id: UUID | None


class InquiryStatusChange(BaseModel):
    status: str
    closing_note: str | None = Field(None, max_length=2000)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v):
        if v not in INQUIRY_STATUSES:
            raise ValueError(f"status must be one of {INQUIRY_STATUSES}")
        return v


class InquiryConvert(BaseModel):
    """Payload for POST /inquiries/{id}/convert."""
    quoted_price: float | None = Field(None, ge=0)
    approved_price: float | None = Field(None, ge=0)
    closing_note: str | None = Field(None, max_length=2000)


class InquiryTimelineEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | None = None
    action: str | None = None
    user_id: UUID | None = None
    user_name: str | None = None       # enriched by service layer
    old_data: dict | None = None
    new_data: dict | None = None
    created_at: datetime | None = None


# ════════════════════════════════════════════════════════════════
# OUTPUT
# ════════════════════════════════════════════════════════════════

class InquiryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    status: str
    source: str
    service_interest: str | None

    customer_id: UUID | None
    vehicle_id: UUID | None
    assigned_to_id: UUID | None

    color_preference: str | None
    color_family: str | None
    finish_preference: str | None
    has_custom_graphics: bool

    follow_up_date: date | None
    last_contacted_at: datetime | None

    created_at: datetime

    # Enrichment — populated by the API layer via batch joins.
    customer_name: str | None = None
    vehicle_label: str | None = None
    assigned_to_name: str | None = None


class InquiryDetail(InquiryListItem):
    description: str
    preferences: dict | None
    budget_range: str | None
    desired_date: date | None
    notes: str | None
    closing_note: str | None
    updated_at: datetime
    photos: list[InquiryPhotoOut] = Field(default_factory=list)