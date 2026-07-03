# schemas/projects.py
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List

from schemas.customer_inquiry import CustomerInquirySummary
from schemas.constants import ProjectStatus, ProjectPriority


# =============================================================================
# Project Response (Tanpa inquiry untuk menghindari lazy loading)
# =============================================================================

class ProjectResponse(BaseModel):
    """Response untuk project detail - tanpa inquiry untuk menghindari lazy loading."""
    id: UUID
    inquiry_id: Optional[UUID] = None
    name: str
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    vehicle_brand: str
    vehicle_model: str
    vehicle_year: Optional[int] = None
    vehicle_license_plate: Optional[str] = None
    status: str
    priority: str
    progress: int
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    estimated_revenue: Optional[Decimal] = None
    actual_revenue: Optional[Decimal] = None
    deposit_amount: Decimal
    deposit_paid: bool
    deposit_paid_at: Optional[datetime] = None
    project_start_date: Optional[datetime] = None
    project_target_delivery: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    final_notes: Optional[str] = None
    is_archived: bool
    stage_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectResponseWithInquiry(BaseModel):
    """Response untuk project detail dengan data inquiry (gunakan dengan hati-hati)."""
    id: UUID
    inquiry_id: Optional[UUID] = None
    inquiry: Optional[CustomerInquirySummary] = None
    name: str
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    vehicle_brand: str
    vehicle_model: str
    vehicle_year: Optional[int] = None
    vehicle_license_plate: Optional[str] = None
    status: str
    priority: str
    progress: int
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    estimated_revenue: Optional[Decimal] = None
    actual_revenue: Optional[Decimal] = None
    deposit_amount: Decimal
    deposit_paid: bool
    deposit_paid_at: Optional[datetime] = None
    project_start_date: Optional[datetime] = None
    project_target_delivery: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    final_notes: Optional[str] = None
    is_archived: bool
    stage_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectMinimalResponse(BaseModel):
    """Minimal project response untuk list/inquiry."""
    id: UUID
    name: str
    status: str
    progress: int
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    estimated_revenue: Optional[Decimal] = None
    actual_revenue: Optional[Decimal] = None
    project_start_date: Optional[datetime] = None
    project_target_delivery: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Project Create/Update
# =============================================================================

class ProjectCreate(BaseModel):
    """Schema untuk membuat project baru."""
    inquiry_id: Optional[UUID] = Field(None, description="ID inquiry (opsional)")
    name: str = Field(..., min_length=1, max_length=255, description="Nama project")
    customer_name: str = Field(..., min_length=1, max_length=255, description="Nama customer")
    customer_phone: Optional[str] = Field(None, max_length=20, description="No telepon customer")
    customer_email: Optional[str] = Field(None, max_length=255, description="Email customer")
    vehicle_brand: str = Field(..., min_length=1, max_length=50, description="Brand kendaraan")
    vehicle_model: str = Field(..., min_length=1, max_length=100, description="Model kendaraan")
    vehicle_year: Optional[int] = Field(None, description="Tahun kendaraan")
    vehicle_license_plate: Optional[str] = Field(None, max_length=20, description="Plat nomor")
    estimated_cost: Decimal = Field(default=0, ge=0, description="Estimasi biaya")
    estimated_revenue: Decimal = Field(default=0, ge=0, description="Estimasi pendapatan")
    priority: str = Field(default=ProjectPriority.MEDIUM, description="Prioritas")
    project_start_date: Optional[datetime] = Field(None, description="Tanggal mulai project")
    project_target_delivery: Optional[datetime] = Field(None, description="Target delivery")
    notes: Optional[str] = Field(None, description="Catatan")
    stage_id: Optional[UUID] = Field(None, description="ID stage")


class ProjectUpdate(BaseModel):
    """Schema untuk update project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[str] = Field(None, max_length=255)
    vehicle_brand: Optional[str] = Field(None, min_length=1, max_length=50)
    vehicle_model: Optional[str] = Field(None, min_length=1, max_length=100)
    vehicle_year: Optional[int] = None
    vehicle_license_plate: Optional[str] = Field(None, max_length=20)
    estimated_cost: Optional[Decimal] = Field(None, ge=0)
    estimated_revenue: Optional[Decimal] = Field(None, ge=0)
    actual_cost: Optional[Decimal] = Field(None, ge=0)
    actual_revenue: Optional[Decimal] = Field(None, ge=0)
    priority: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    project_start_date: Optional[datetime] = None
    project_target_delivery: Optional[datetime] = None
    notes: Optional[str] = None
    stage_id: Optional[UUID] = None
    is_archived: Optional[bool] = None


class ProjectUpdateStatus(BaseModel):
    """Schema untuk update status project."""
    status: str = Field(..., description="Status baru")
    note: Optional[str] = Field(None, description="Catatan perubahan status")


class ProjectUpdateProgress(BaseModel):
    """Schema untuk update progress project."""
    progress: int = Field(..., ge=0, le=100, description="Progress (0-100)")


# =============================================================================
# Project Task Schemas
# =============================================================================

class ProjectTaskCreate(BaseModel):
    """Schema untuk membuat task project."""
    title: str = Field(..., min_length=1, max_length=200, description="Judul task")
    description: Optional[str] = Field(None, max_length=500, description="Deskripsi")
    assigned_to: Optional[str] = Field(None, max_length=100, description="Ditugaskan ke")
    due_date: Optional[datetime] = Field(None, description="Tanggal deadline")
    priority: str = Field(default="medium", description="Prioritas task")
    sort_order: int = Field(default=0, description="Urutan")


class ProjectTaskUpdate(BaseModel):
    """Schema untuk update task project."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
    assigned_to: Optional[str] = Field(None, max_length=100)
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    sort_order: Optional[int] = None


class ProjectTaskResponse(BaseModel):
    """Response untuk task project."""
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str] = None
    status: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: str
    sort_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Project Labor Schemas
# =============================================================================

class ProjectLaborCreate(BaseModel):
    """Schema untuk membuat labor entry."""
    labor_type: str = Field(..., min_length=1, max_length=100, description="Jenis pekerjaan")
    hours: Decimal = Field(..., gt=0, description="Jumlah jam kerja")
    rate_per_hour: Optional[Decimal] = Field(None, gt=0, description="Rate per jam (opsional)")
    technician_name: Optional[str] = Field(None, max_length=100, description="Nama teknisi")
    description: Optional[str] = Field(None, description="Deskripsi")


class ProjectLaborResponse(BaseModel):
    """Response untuk labor entry."""
    id: UUID
    project_id: UUID
    labor_type: str
    hours: Decimal
    rate_per_hour: Decimal
    total_cost: Decimal
    technician_name: Optional[str] = None
    description: Optional[str] = None
    date_performed: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Project Financial Summary
# =============================================================================

class ProjectMaterialSummary(BaseModel):
    """Summary material usage per item."""
    id: UUID
    item_name: Optional[str] = None
    item_category: Optional[str] = None
    quantity: Decimal
    unit: Optional[str] = None
    unit_cost: Decimal
    total_cost: Decimal


class ProjectLaborSummary(BaseModel):
    """Summary labor per type."""
    id: UUID
    labor_type: str
    hours: Decimal
    rate_per_hour: Decimal
    total_cost: Decimal


class ProjectFinancialSummary(BaseModel):
    """Financial summary for a project."""
    estimated_cost: Decimal
    actual_cost: Decimal
    estimated_revenue: Decimal
    actual_revenue: Decimal
    material_cost: Decimal
    labor_cost: Decimal
    expenses: Decimal
    profit: Decimal
    margin: Decimal
    material_usages: List[ProjectMaterialSummary] = Field(default_factory=list)
    labor_items: List[ProjectLaborSummary] = Field(default_factory=list)


class ProjectDetailResponse(BaseModel):
    """Detailed project response with financial summary."""
    project: ProjectResponse
    financial_summary: ProjectFinancialSummary
    tasks: List[ProjectTaskResponse] = Field(default_factory=list)
    activities: List[dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Project Kanban
# =============================================================================

class ProjectKanbanItem(BaseModel):
    """Item untuk kanban board."""
    id: UUID
    name: str
    customer_name: str
    vehicle_brand: str
    vehicle_model: str
    status: str
    priority: str
    progress: int
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    created_at: datetime
    project_target_delivery: Optional[datetime] = None


class ProjectKanbanResponse(BaseModel):
    """Response untuk kanban board."""
    draft: List[ProjectKanbanItem] = Field(default_factory=list)
    active: List[ProjectKanbanItem] = Field(default_factory=list)
    in_progress: List[ProjectKanbanItem] = Field(default_factory=list)
    on_hold: List[ProjectKanbanItem] = Field(default_factory=list)
    completed: List[ProjectKanbanItem] = Field(default_factory=list)
    cancelled: List[ProjectKanbanItem] = Field(default_factory=list)


# =============================================================================
# Project Stage Schemas
# =============================================================================

class ProjectStageCreate(BaseModel):
    """Schema untuk membuat stage."""
    name: str = Field(..., min_length=1, max_length=100, description="Nama stage")
    color: Optional[str] = Field(None, max_length=50, description="Warna")
    sort_order: int = Field(default=0, description="Urutan")
    description: Optional[str] = Field(None, description="Deskripsi")
    is_default: bool = Field(default=False, description="Stage default")


class ProjectStageResponse(BaseModel):
    """Response untuk stage."""
    id: UUID
    name: str
    color: Optional[str] = None
    sort_order: int
    description: Optional[str] = None
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)