from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from modules.vehicles.constants import VEHICLE_CATEGORIES


def _check_category(v: str | None) -> str | None:
    if v is not None and v not in VEHICLE_CATEGORIES:
        raise ValueError(f"category must be one of {VEHICLE_CATEGORIES}")
    return v


class VehicleCreate(BaseModel):
    plate_number: str | None = Field(None, max_length=20)
    brand: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=120)
    year: int | None = Field(None, ge=1900, le=2100)
    color: str | None = Field(None, max_length=64)
    category: str | None = None
    vin: str | None = Field(None, max_length=64)
    engine_number: str | None = Field(None, max_length=64)
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        return _check_category(v)


class VehicleUpdate(BaseModel):
    plate_number: str | None = None
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    color: str | None = None
    category: str | None = None
    vin: str | None = None
    engine_number: str | None = None
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        return _check_category(v)


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