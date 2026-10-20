"""Pydantic schemas for projects, project items, and employees."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.projects.constants import (
    COST_CATEGORIES,
    INVENTORY_CATEGORIES,
    LABOR_CATEGORIES,
    PROJECT_ITEM_STATUSES,
    PROJECT_STATUSES,
)


# ════════════════════════════════════════════════════════════════
# EMPLOYEES
# ════════════════════════════════════════════════════════════════

class EmployeeCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=32)
    name: str = Field(..., min_length=2, max_length=255)
    position: str | None = Field(None, max_length=100)
    hourly_rate: float = Field(0, ge=0)
    monthly_salary: float | None = Field(None, ge=0)
    joined_at: date | None = None
    phone: str | None = Field(None, max_length=32)
    notes: str | None = None


class EmployeeUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    position: str | None = Field(None, max_length=100)
    hourly_rate: float | None = Field(None, ge=0)
    monthly_salary: float | None = Field(None, ge=0)
    joined_at: date | None = None
    phone: str | None = Field(None, max_length=32)
    notes: str | None = None
    is_active: bool | None = None

    # Non-nullable in DB — reject explicit null.
    @field_validator("hourly_rate", "is_active")
    @classmethod
    def _non_nullable(cls, v):
        if v is None:
            raise ValueError("field cannot be null")
        return v


class EmployeeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    position: str | None
    hourly_rate: float
    is_active: bool


class EmployeeDetail(EmployeeListItem):
    monthly_salary: float | None
    joined_at: date | None
    phone: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# ════════════════════════════════════════════════════════════════
# PROJECT ITEMS
# ════════════════════════════════════════════════════════════════

def _validate_item_links(category: str, material_id, employee_id) -> None:
    """Enforce the material/employee link contract per category."""
    if category in INVENTORY_CATEGORIES:
        if not material_id:
            raise ValueError(f"material_id is required for {category} items")
        if employee_id:
            raise ValueError(f"employee_id is not allowed for {category} items")
    elif category in LABOR_CATEGORIES:
        if not employee_id:
            raise ValueError(f"employee_id is required for {category} items")
        if material_id:
            raise ValueError(f"material_id is not allowed for {category} items")
    else:
        if material_id:
            raise ValueError(f"material_id is not allowed for {category} items")
        if employee_id:
            raise ValueError(f"employee_id is not allowed for {category} items")


class ProjectItemCreate(BaseModel):
    category: str
    description: str = Field(..., min_length=1, max_length=500)

    material_id: UUID | None = None
    employee_id: UUID | None = None

    unit: str | None = Field(None, max_length=16)

    estimated_quantity: float | None = Field(None, ge=0)
    estimated_unit_cost: float | None = Field(None, ge=0)

    actual_quantity: float | None = Field(None, ge=0)
    actual_unit_cost: float | None = Field(None, ge=0)

    notes: str | None = None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        if v not in COST_CATEGORIES:
            raise ValueError(f"category must be one of {COST_CATEGORIES}")
        return v

    @model_validator(mode="after")
    def _check_links(self):
        _validate_item_links(self.category, self.material_id, self.employee_id)
        return self


class ProjectItemUpdate(BaseModel):
    description: str | None = Field(None, min_length=1, max_length=500)
    material_id: UUID | None = None
    employee_id: UUID | None = None
    unit: str | None = Field(None, max_length=16)

    estimated_quantity: float | None = Field(None, ge=0)
    estimated_unit_cost: float | None = Field(None, ge=0)

    actual_quantity: float | None = Field(None, ge=0)
    actual_unit_cost: float | None = Field(None, ge=0)

    status: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v):
        if v is not None and v not in PROJECT_ITEM_STATUSES:
            raise ValueError(f"status must be one of {PROJECT_ITEM_STATUSES}")
        return v


class ProjectItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category: str
    description: str
    material_id: UUID | None
    employee_id: UUID | None
    unit: str | None

    estimated_quantity: float | None
    estimated_unit_cost: float | None
    estimated_cost: float

    actual_quantity: float | None
    actual_unit_cost: float | None
    actual_cost: float

    status: str
    notes: str | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime

    variance: float = 0.0
    variance_pct: float = 0.0


# ════════════════════════════════════════════════════════════════
# PROJECTS
# ════════════════════════════════════════════════════════════════

class ProjectCreate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None

    inquiry_id: UUID | None = None
    customer_id: UUID
    vehicle_id: UUID | None = None
    assigned_lead_id: UUID | None = None

    priority: int = 0
    quoted_price: float | None = Field(None, ge=0)
    approved_price: float | None = Field(None, ge=0)

    start_date: date | None = None
    target_end_date: date | None = None

    internal_notes: str | None = None

    @model_validator(mode="after")
    def _validate_dates(self):
        if (
            self.start_date
            and self.target_end_date
            and self.target_end_date < self.start_date
        ):
            raise ValueError("target_end_date must be on or after start_date")
        return self


class ProjectUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    assigned_lead_id: UUID | None = None
    priority: int | None = None
    quoted_price: float | None = Field(None, ge=0)
    approved_price: float | None = Field(None, ge=0)
    start_date: date | None = None
    target_end_date: date | None = None
    actual_end_date: date | None = None
    internal_notes: str | None = None

    @field_validator("priority")
    @classmethod
    def _non_nullable_priority(cls, v):
        if v is None:
            raise ValueError("priority cannot be null")
        return v


class ProjectStatusChange(BaseModel):
    status: str
    note: str | None = Field(None, max_length=2000)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v):
        if v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {PROJECT_STATUSES}")
        return v


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    title: str | None
    status: str

    customer_id: UUID
    vehicle_id: UUID | None
    inquiry_id: UUID | None

    quoted_price: float | None
    approved_price: float | None
    estimated_hpp: float
    actual_hpp: float

    start_date: date | None
    target_end_date: date | None
    created_at: datetime

    variance: float = 0.0
    gross_margin_pct: float = 0.0

    # Enrichment — populated by API layer.
    customer_name: str | None = None


class ProjectCostBreakdown(BaseModel):
    estimated_materials: float
    estimated_parts: float
    estimated_labor: float
    estimated_outsource: float
    estimated_overhead: float
    estimated_misc: float

    actual_materials: float
    actual_parts: float
    actual_labor: float
    actual_outsource: float
    actual_overhead: float
    actual_misc: float

    estimated_hpp: float
    actual_hpp: float
    variance: float
    variance_pct: float


class ProjectDetail(ProjectListItem):
    description: str | None
    assigned_lead_id: UUID | None
    priority: int
    internal_notes: str | None
    closing_note: str | None
    actual_end_date: date | None
    updated_at: datetime

    items: list[ProjectItemOut] = Field(default_factory=list)
    cost_breakdown: ProjectCostBreakdown | None = None

    customer_name: str | None = None
    customer_code: str | None = None
    vehicle_label: str | None = None
    assigned_lead_name: str | None = None


class OverheadRateInfo(BaseModel):
    monthly_overhead: float
    monthly_labor_hours: float
    overhead_rate_per_hour: float


class ProjectCatalog(BaseModel):
    statuses: list[str]
    status_labels: dict[str, str]
    cost_categories: list[str]
    cost_category_labels: dict[str, str]