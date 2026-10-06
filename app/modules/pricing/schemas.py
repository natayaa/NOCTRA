"""Pydantic schemas for the pricing module."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.inquiries.constants import SERVICE_INTERESTS
from app.modules.vehicles.constants import VEHICLE_CATEGORIES


# ════════════════════════════════════════════════════════════════
# RULES
# ════════════════════════════════════════════════════════════════

def _clean_optional(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ("none", "null", "undefined", "nil", ""):
        return None
    return s


class PricingRuleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    notes: str | None = None

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
    notes: str | None = None
    service_interest: str | None = None
    vehicle_category: str | None = None
    target_margin_pct: float | None = Field(None, ge=0, lt=100)
    min_margin_pct: float | None = Field(None, ge=0, lt=100)
    complexity_factor: float | None = Field(None, gt=0, le=10)
    min_price_floor: float | None = Field(None, ge=0)
    is_active: bool | None = None

    @field_validator("service_interest", "vehicle_category")
    @classmethod
    def _clean(cls, v):
        return _clean_optional(v)


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
# RECOMMENDATION (output of the engine)
# ════════════════════════════════════════════════════════════════

class PricingRecommendation(BaseModel):
    """The engine's answer: given an HPP, what should we charge?"""

    hpp: float
    complexity_factor: float
    adjusted_hpp: float

    # Margins used
    target_margin_pct: float
    min_margin_pct: float

    # The numbers
    recommended_price: float
    minimum_price: float
    recommended_markup_pct: float      # what markup the recommended price implies

    # Which rule applied
    rule_id: UUID | None = None
    rule_name: str | None = None


class MarginEvaluation(BaseModel):
    """Analysis of a specific selling price against a target."""

    hpp: float
    selling_price: float
    gross_profit: float
    margin_pct: float
    markup_pct: float

    target_margin_pct: float
    min_margin_pct: float

    # Categorization
    health: str                        # "loss" | "below_minimum" | "acceptable" | "good" | "excellent"
    meets_minimum: bool
    meets_target: bool

    # Absolute shortfall/surplus vs target and min
    price_vs_target: float             # selling_price - recommended_price (positive = above target)
    price_vs_minimum: float            # selling_price - minimum_price


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
    notes: str | None = None


# ════════════════════════════════════════════════════════════════
# PREVIEW (from the UI — no persistence)
# ════════════════════════════════════════════════════════════════

class PricingPreviewRequest(BaseModel):
    hpp: float = Field(..., ge=0)
    service_interest: str | None = None
    vehicle_category: str | None = None
    proposed_price: float | None = Field(None, ge=0)


class PricingPreviewResponse(BaseModel):
    recommendation: PricingRecommendation
    evaluation: MarginEvaluation | None = None