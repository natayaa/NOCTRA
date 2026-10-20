from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.vehicles.constants import VEHICLE_CATEGORIES

_EMPTY_VALUES = {"", "none", "null", "undefined", "nil"}


def _normalize_optional_str(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in _EMPTY_VALUES:
        return None
    return s


def _check_category(v: str | None) -> str | None:
    if v is not None and v not in VEHICLE_CATEGORIES:
        raise ValueError(f"category must be one of {VEHICLE_CATEGORIES}")
    return v


def _normalize_plate(v: str | None) -> str | None:
    """Uppercase + collapse internal whitespace."""
    if v is None:
        return None
    s = v.strip().upper()
    s = " ".join(s.split())
    return s or None


# ════════════════════════════════════════════════════════════════
# CREATE
# ════════════════════════════════════════════════════════════════

class VehicleCreate(BaseModel):
    plate_number: str | None = Field(None, max_length=20)
    brand: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=120)
    year: int | None = Field(None, ge=1900, le=2100)
    color: str | None = Field(None, max_length=64)
    category: str | None = None
    vin: str | None = Field(None, max_length=64)
    engine_number: str | None = Field(None, max_length=64)
    notes: str | None = Field(None, max_length=5000)
    brand_id: UUID | None = None
    model_id: UUID | None = None

    @field_validator("plate_number", mode="before")
    @classmethod
    def _clean_plate(cls, v):
        return _normalize_plate(v)

    @field_validator("brand", "model", mode="before")
    @classmethod
    def _strip_required(cls, v):
        return str(v).strip() if v else v

    @field_validator("color", "vin", "engine_number", "notes", mode="before")
    @classmethod
    def _clean_optional(cls, v):
        return _normalize_optional_str(v)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        return _check_category(v)

    @model_validator(mode="after")
    def _check_model_brand_consistency(self):
        # Structural check only — existence + FK consistency is enforced
        # in the service layer (needs DB access).
        if self.model_id and not self.brand_id:
            raise ValueError(
                "brand_id is required when model_id is provided"
            )
        return self


# ════════════════════════════════════════════════════════════════
# UPDATE
# ════════════════════════════════════════════════════════════════

class VehicleUpdate(BaseModel):
    plate_number: str | None = Field(None, max_length=20)
    brand: str | None = Field(None, min_length=1, max_length=100)
    model: str | None = Field(None, min_length=1, max_length=120)
    year: int | None = Field(None, ge=1900, le=2100)
    color: str | None = Field(None, max_length=64)
    category: str | None = None
    vin: str | None = Field(None, max_length=64)
    engine_number: str | None = Field(None, max_length=64)
    notes: str | None = Field(None, max_length=5000)
    brand_id: UUID | None = None
    model_id: UUID | None = None

    @field_validator("plate_number", mode="before")
    @classmethod
    def _clean_plate(cls, v):
        return _normalize_plate(v)

    @field_validator("brand", "model", mode="before")
    @classmethod
    def _strip_optional(cls, v):
        return _normalize_optional_str(v)

    @field_validator("color", "vin", "engine_number", "notes", mode="before")
    @classmethod
    def _clean_optional(cls, v):
        return _normalize_optional_str(v)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        return _check_category(v)

    # brand and model are NOT NULL in the DB — reject explicit null.
    @field_validator("brand", "model")
    @classmethod
    def _non_nullable_brand_model(cls, v):
        if v is None:
            raise ValueError("field cannot be null")
        return v


# ════════════════════════════════════════════════════════════════
# READ
# ════════════════════════════════════════════════════════════════

class VehicleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customer_id: UUID
    plate_number: str | None
    brand: str
    model: str
    year: int | None
    color: str | None
    category: str | None
    brand_id: UUID | None
    model_id: UUID | None


class VehicleDetail(VehicleListItem):
    vin: str | None
    engine_number: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class VehicleBrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    country: str | None


class VehicleModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    brand_id: UUID
    name: str
    category: str | None


class VehicleSearchResult(BaseModel):
    """Lightweight result for autocomplete pickers."""
    id: UUID
    label: str
    sublabel: str
    customer_id: UUID | None = None
    customer_name: str | None = None