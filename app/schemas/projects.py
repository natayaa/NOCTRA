from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from typing import Optional

from schemas.customer_inquiry import CustomerInquirySummary

class ProjectCreate(BaseModel):
    inquiry_id: Optional[UUID] = None
    name: str
    customer_name: str
    vehicle_brand: str
    vehicle_model: str
    estimated_cost: Decimal = Decimal(0)
    estimated_revenue: Decimal = Decimal(0)

class ProjectResponse(BaseModel):
    id: UUID
    inquiry_id: Optional[UUID] = None   # typo fixed
    inquiry: Optional[CustomerInquirySummary] = None
    name: str
    customer_name: str
    vehicle_brand: str
    vehicle_model: str
    status: str
    progress: int
    estimated_cost: Decimal
    actual_cost: Decimal
    estimated_revenue: Decimal
    actual_revenue: Decimal = Decimal(0)
    created_at: datetime

    model_config = {"from_attributes": True}

class ProjectUpdateStatus(BaseModel):
    status: str

class ProjectKanbanResponse(ProjectResponse):
    inquiry: Optional[CustomerInquirySummary] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    license_plate: Optional[str] = None
    estimated_cost: Optional[Decimal] = None
    estimated_revenue: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    actual_revenue: Optional[Decimal] = None
    start_date: Optional[date] = None
    target_delivery: Optional[date] = None
    notes: Optional[str] = None

class ProjectLaborCreate(BaseModel):
    labor_type: str = Field(..., description="Jenis pekerjaan, misal: Painter, Mechanic, Assembler")
    hours: float = Field(..., gt=0, description="Jumlah jam kerja")
    rate_per_hour: Optional[float] = Field(None, description="Opsional, jika tidak diisi akan diambil dari price list")

class ProjectLaborResponse(BaseModel):
    id: UUID
    project_id: UUID
    labor_type: str
    hours: Decimal
    rate_per_hour: Decimal
    total_cost: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}

class ProjectLaborSummary(BaseModel):
    id: UUID
    labor_type: str
    hours: Decimal
    rate_per_hour: Decimal
    total_cost: Decimal

    model_config = {"from_attributes": True}

class ProjectMaterialSummary(BaseModel):
    id: UUID
    item_name: Optional[str] = None
    quantity: int
    unit: Optional[str] = None
    total_cost: Optional[Decimal] = None

class ProjectFinancialSummary(BaseModel):
    estimated_cost: Decimal
    actual_cost: Decimal
    estimated_revenue: Decimal
    actual_revenue: Decimal
    material_cost: Decimal
    labor_cost: Decimal
    expenses: Decimal
    profit: Decimal
    margin: Decimal

class ProjectDetailResponse(BaseModel):
    project: ProjectResponse
    financial_summary: ProjectFinancialSummary
    labor_items: list[ProjectLaborSummary] = []
    material_usages: list[ProjectMaterialSummary] = []

    model_config = {"from_attributes": True}