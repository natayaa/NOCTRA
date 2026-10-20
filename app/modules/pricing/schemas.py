"""Pydantic schemas for the pricing module."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.inquiries.constants import SERVICE_INTERESTS
from app.modules.vehicles.constants import VEHICLE_CATEGORIES


_EMPTY = {"", "none", "null", "undefined", "nil"}


def _clean_optional(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in _EMPTY:
        return None
    return s


# ════════════════════════════════════════════════════════════════
# RULES
# ════════════════════════════════════════════════════════════════

class PricingRuleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    notes: str | None = Field(None, max_length=5000)

    service_interest: str | None = None
    vehicle_category: str | None = None

    target_margin_pct: float = Field(50, ge=0, lt=100)
    min_margin_pct: float = Field(30, ge=0, lt=100)
    complexity_factor: float = Field(1.0, gt=0, le=10)
    min_price_floor: float | None = Field(None, ge=0)

    @field_validator("service_interest")
    @classmethod
    def _validate_service(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in SERVICE_INTERESTS:
            raise ValueError(f"service_interest must be one of {SERVICE_INTERESTS}")
        return v

    @field_validator("vehicle_category")
    @classmethod
    def _validate_category(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in VEHICLE_CATEGORIES:
            raise ValueError(f"vehicle_category must be one of {VEHICLE_CATEGORIES}")
        return v

    @field_validator("min_margin_pct")
    @classmethod
    def _validate_min_below_target(cls, v, info):
        target = info.data.get("target_margin_pct")
        if target is not None and v >= target:
            raise ValueError("min_margin_pct must be less than target_margin_pct")
        return v


class PricingRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    notes: str | None = Field(None, max_length=5000)
    service_interest: str | None = None
    vehicle_category: str | None = None
    target_margin_pct: float | None = Field(None, ge=0, lt=100)
    min_margin_pct: float | None = Field(None, ge=0, lt=100)
    complexity_factor: float | None = Field(None, gt=0, le=10)
    min_price_floor: float | None = Field(None, ge=0)
    is_active: bool | None = None

    @field_validator("service_interest")
    @classmethod
    def _validate_service(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in SERVICE_INTERESTS:
            raise ValueError(f"service_interest must be one of {SERVICE_INTERESTS}")
        return v

    @field_validator("vehicle_category")
    @classmethod
    def _validate_category(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in VEHICLE_CATEGORIES:
            raise ValueError(f"vehicle_category must be one of {VEHICLE_CATEGORIES}")
        return v

    # Non-nullable in DB — reject explicit null (500 → 422).
    @field_validator(
        "name", "target_margin_pct", "min_margin_pct",
        "complexity_factor", "is_active",
    )
    @classmethod
    def _non_nullable(cls, v):
        if v is None:
            raise ValueError("field cannot be null")
        return v

    @model_validator(mode="after")
    def _validate_margins_when_both_present(self):
        # Cross-field validation when BOTH are in the payload.
        # When only one is provided, service layer validates against the
        # current DB value to prevent min > target.
        if (
            self.target_margin_pct is not None
            and self.min_margin_pct is not None
            and self.min_margin_pct >= self.target_margin_pct
        ):
            raise ValueError("min_margin_pct must be less than target_margin_pct")
        return self


class PricingRuleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    service_interest: str | None
    vehicle_category: str | None
    target_margin_pct: float
    min_margin_pct: float
    complexity_factor: float
    is_active: bool


class PricingRuleDetail(PricingRuleListItem):
    notes: str | None
    min_price_floor: float | None
    created_at: datetime
    updated_at: datetime
    specificity: int = 0


# ════════════════════════════════════════════════════════════════
# RECOMMENDATION
# ════════════════════════════════════════════════════════════════

class PricingRecommendation(BaseModel):
    hpp: float
    complexity_factor: float
    adjusted_hpp: float

    target_margin_pct: float
    min_margin_pct: float

    recommended_price: float
    minimum_price: float
    recommended_markup_pct: float

    rule_id: UUID | None = None
    rule_name: str | None = None


class MarginEvaluation(BaseModel):
    """Analysis of a specific selling price against a target."""

    hpp: float
    adjusted_hpp: float              # NEW — hpp * complexity_factor

    selling_price: float
    gross_profit: float
    margin_pct: float                # against raw hpp (real profit)
    adjusted_margin_pct: float       # NEW — against adjusted_hpp (pricing basis)
    markup_pct: float

    target_margin_pct: float
    min_margin_pct: float

    health: str                      # "loss" | "below_minimum" | "acceptable" | "good" | "excellent"
    meets_minimum: bool
    meets_target: bool

    price_vs_target: float
    price_vs_minimum: float


# ════════════════════════════════════════════════════════════════
# SNAPSHOTS
# ════════════════════════════════════════════════════════════════

class PricingSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    inquiry_id: UUID | None
    project_id: UUID | None
    service_interest: str | None
    vehicle_category: str | None
    hpp_estimate: float
    rule_id: UUID | None
    rule_name: str | None
    target_margin_pct: float
    min_margin_pct: float
    complexity_factor: float
    recommended_price: float
    minimum_price: float
    actual_quoted_price: float | None
    actual_margin_pct: float | None
    notes: str | None
    created_at: datetime


class PricingSnapshotCreate(BaseModel):
    inquiry_id: UUID | None = None
    project_id: UUID | None = None
    service_interest: str | None = None
    vehicle_category: str | None = None
    hpp_estimate: float = Field(..., ge=0)
    actual_quoted_price: float | None = Field(None, ge=0)
    notes: str | None = Field(None, max_length=2000)

    @field_validator("service_interest")
    @classmethod
    def _validate_service(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in SERVICE_INTERESTS:
            raise ValueError(f"service_interest must be one of {SERVICE_INTERESTS}")
        return v

    @field_validator("vehicle_category")
    @classmethod
    def _validate_category(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in VEHICLE_CATEGORIES:
            raise ValueError(f"vehicle_category must be one of {VEHICLE_CATEGORIES}")
        return v


# ════════════════════════════════════════════════════════════════
# PREVIEW
# ════════════════════════════════════════════════════════════════

class PricingPreviewRequest(BaseModel):
    hpp: float = Field(..., ge=0)
    service_interest: str | None = None
    vehicle_category: str | None = None
    proposed_price: float | None = Field(None, ge=0)

    @field_validator("service_interest")
    @classmethod
    def _validate_service(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in SERVICE_INTERESTS:
            raise ValueError(f"service_interest must be one of {SERVICE_INTERESTS}")
        return v

    @field_validator("vehicle_category")
    @classmethod
    def _validate_category(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in VEHICLE_CATEGORIES:
            raise ValueError(f"vehicle_category must be one of {VEHICLE_CATEGORIES}")
        return v


class PricingPreviewResponse(BaseModel):
    recommendation: PricingRecommendation
    evaluation: MarginEvaluation | None = None