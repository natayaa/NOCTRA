"""Pydantic schemas for the inquiries module."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.inquiries.constants import (
    BUDGET_RANGES,
    COLOR_FAMILIES,
    FINISH_TYPES,
    INQUIRY_SOURCES,
    INQUIRY_STATUSES,
    SERVICE_INTERESTS,
)


# ════════════════════════════════════════════════════════════════
# PHOTOS
# ════════════════════════════════════════════════════════════════

class InquiryPhotoIn(BaseModel):
    file_path: str = Field(..., min_length=1, max_length=500)
    file_name: str | None = Field(None, max_length=255)
    caption: str | None = None
    is_primary: bool = False


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
    """The 'what they want' fields. Shared by Create and Update."""

    color_preference: str | None = Field(None, max_length=64)
    color_family: str | None = None
    finish_preference: str | None = None
    # `None` means "not provided" so PATCH doesn't reset it.
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
    notes: str | None = None

    @field_validator("service_interest")
    @classmethod
    def _validate_service(cls, v):
        if v is not None and v not in SERVICE_INTERESTS:
            if len(v) > 32:
                raise ValueError("service_interest must be <= 32 chars")
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


class InquiryUpdate(CustomerRequestMixin):
    """Partial update. All fields optional."""

    customer_id: UUID | None = None
    vehicle_id: UUID | None = None

    service_interest: str | None = Field(None, max_length=32)
    description: str | None = Field(None, min_length=20, max_length=5000)

    budget_range: str | None = None
    desired_date: date | None = None
    follow_up_date: date | None = None
    notes: str | None = None

    @field_validator("budget_range")
    @classmethod
    def _validate_budget(cls, v):
        if v is not None and v not in BUDGET_RANGES:
            raise ValueError(f"budget_range must be one of {BUDGET_RANGES}")
        return v


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


class InquiryDetail(InquiryListItem):
    description: str
    preferences: dict | None
    budget_range: str | None
    desired_date: date | None
    notes: str | None
    closing_note: str | None
    updated_at: datetime
    photos: list[InquiryPhotoOut] = Field(default_factory=list)