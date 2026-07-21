# modules/project/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from fastapi import UploadFile

from core.constants import ProjectStatus, ProjectPriority


# ============================================================================
# Project Response
# ============================================================================

class ProjectResponse(BaseModel):
    """Response untuk project."""
    id: UUID
    inquiry_id: Optional[UUID] = None
    name: str
    project_code: Optional[str] = None
         
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_license_plate: Optional[str] = None
    source: Optional[str] = None
    
    # CORE
    status: str
    priority: str
    progress: int
    
    # Financial
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    
    # Timeline
    project_start_date: Optional[datetime] = None
    project_target_delivery: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    # Metadata
    notes: Optional[str] = None
    final_notes: Optional[str] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectMinimalResponse(BaseModel):
    """Minimal response project untuk list/inquiry."""
    id: UUID
    inquiry_id: Optional[UUID] = None
    name: str
    project_code: Optional[str] = None
    customer_name: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    status: str
    priority: str
    progress: int
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    project_start_date: Optional[datetime] = None
    project_target_delivery: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Create/Update
# ============================================================================

class ProjectCreate(BaseModel):
    """Schema untuk membuat project."""
    inquiry_id: Optional[UUID] = Field(None, description="ID Inquiry (akan auto-complete data customer/vehicle)")
    name: str = Field(..., min_length=1, max_length=255, description="Nama project")
    
    # Opsional: Bisa diisi manual jika tidak dari inquiry
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Nama customer")
    customer_phone: Optional[str] = Field(None, max_length=20, description="Nomor telp customer")
    customer_email: Optional[str] = Field(None, max_length=255, description="Email customer")
    vehicle_brand: Optional[str] = Field(None, min_length=1, max_length=50, description="Brand kendaraan")
    vehicle_model: Optional[str] = Field(None, min_length=1, max_length=100, description="Model kendaraan")
    vehicle_year: Optional[int] = Field(None, ge=1950, le=2035, description="Tahun kendaraan")
    vehicle_license_plate: Optional[str] = Field(None, max_length=20, description="Plat nomor")
    source: Optional[str] = Field(None, max_length=500)
    
    estimated_cost: Decimal = Field(default=0, ge=0, description="Estimasi biaya")
    priority: str = Field(default=ProjectPriority.MEDIUM, description="Prioritas")
    project_start_date: Optional[datetime] = Field(None, description="Tanggal mulai project")
    project_target_delivery: Optional[datetime] = Field(None, description="Target delivery project")
    notes: Optional[str] = Field(None, description="Catatan")
    stage_id: Optional[UUID] = Field(None, description="ID Stage")
    price_list_item_ids: Optional[List[UUID]] = Field(None, description="ID price list items untuk di-include")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid_priorities = [e.value for e in ProjectPriority]
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v


class ProjectUpdate(BaseModel):
    """Schema untuk update project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_address: Optional[str] = Field(None, max_length=500)
    
    vehicle_brand: Optional[str] = Field(None, min_length=1, max_length=50)
    vehicle_model: Optional[str] = Field(None, min_length=1, max_length=100)
    vehicle_year: Optional[int] = Field(None, ge=1950, le=2035)
    vehicle_license_plate: Optional[str] = Field(None, max_length=20)
    source: Optional[str] = Field(None, max_length=500)
    
    estimated_cost: Optional[Decimal] = Field(None, ge=0)
    actual_cost: Optional[Decimal] = Field(None, ge=0)
    
    priority: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    project_start_date: Optional[datetime] = None
    project_target_delivery: Optional[datetime] = None
    notes: Optional[str] = None
    stage_id: Optional[UUID] = None
    is_archived: Optional[bool] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v:
            valid_priorities = [e.value for e in ProjectPriority]
            if v not in valid_priorities:
                raise ValueError(
                    f"Priority must be one of: {valid_priorities}")
        return v


class ProjectUpdateStatus(BaseModel):
    """Schema untuk update status project."""
    status: str = Field(..., description="Status baru")
    note: Optional[str] = Field(None, description="Catatan perubahan status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [e.value for e in ProjectStatus]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class ProjectUpdateProgress(BaseModel):
    """Schema untuk update progress project."""
    progress: int = Field(..., ge=0, le=100, description="Progress (0-100)")


class ProjectCancel(BaseModel):
    """Schema untuk cancel project."""
    reason: str = Field(..., min_length=1, description="Alasan pembatalan")


# ============================================================================
# Project Task Schemas
# ============================================================================

class ProjectTaskCreate(BaseModel):
    """Schema untuk membuat task project."""
    title: str = Field(..., min_length=1, max_length=200, description="Judul task")
    description: Optional[str] = Field(None, max_length=500, description="Deskripsi")
    assigned_to: Optional[str] = Field(None, max_length=100, description="Ditugaskan ke")
    due_date: Optional[datetime] = Field(None, description="Tanggal deadline")
    priority: str = Field(default="medium", description="Prioritas task")
    sort_order: int = Field(default=0, description="Urutan")
    estimated_hours: Optional[Decimal] = Field(None, ge=0, description="Estimasi jam")
    actual_hours: Optional[Decimal] = Field(None, ge=0, description="Jam aktual")


class ProjectTaskUpdate(BaseModel):
    """Schema untuk update task project."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
    assigned_to: Optional[str] = Field(None, max_length=100)
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    sort_order: Optional[int] = None
    estimated_hours: Optional[Decimal] = Field(None, ge=0)
    actual_hours: Optional[Decimal] = Field(None, ge=0)


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
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Labor Schemas
# ============================================================================

class ProjectLaborCreate(BaseModel):
    """Schema untuk membuat labor entry."""
    labor_type: str = Field(..., min_length=1, max_length=100, description="Jenis pekerjaan")
    hours: Decimal = Field(..., gt=0, description="Jumlah jam kerja")
    rate_per_hour: Optional[Decimal] = Field(None, gt=0, description="Rate per jam (opsional)")
    technician_name: Optional[str] = Field(None, max_length=100, description="Nama teknisi")
    description: Optional[str] = Field(None, description="Deskripsi")
    date_performed: Optional[datetime] = Field(None, description="Tanggal pengerjaan")


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
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Expense Schemas
# ============================================================================

class ProjectExpenseCreate(BaseModel):
    """Schema untuk membuat expense."""
    name: str = Field(..., min_length=1, max_length=255, description="Nama expense")
    category: str = Field(..., min_length=1, max_length=100, description="Kategori")
    amount: Decimal = Field(..., gt=0, description="Jumlah")
    description: Optional[str] = Field(None, description="Deskripsi")
    expense_date: Optional[datetime] = Field(None, description="Tanggal expense")
    is_billable: bool = Field(default=True, description="Dapat ditagih")


class ProjectExpenseResponse(BaseModel):
    """Response untuk expense."""
    id: UUID
    project_id: UUID
    name: str
    category: str
    amount: Decimal
    description: Optional[str] = None
    expense_date: datetime
    receipt_path: Optional[str] = None
    is_billable: bool
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Price List Item Schemas
# ============================================================================

class ProjectPriceListItemResponse(BaseModel):
    """Response untuk price list item yang digunakan dalam project."""
    id: UUID
    project_id: UUID
    price_list_item_id: UUID
    price_list_item_name: Optional[str] = None
    quantity: Decimal
    unit_price_at_usage: Decimal
    total_price: Decimal
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Financial Summary
# ============================================================================

class ProjectMaterialSummary(BaseModel):
    """Summary material usage per item."""
    id: UUID
    item_name: Optional[str] = None
    item_category: Optional[str] = None
    quantity: Decimal
    unit: Optional[str] = None
    unit_cost: Decimal
    total_cost: Decimal
    is_waste: bool = False


class ProjectLaborSummary(BaseModel):
    """Summary labor per type."""
    id: UUID
    labor_type: str
    hours: Decimal
    rate_per_hour: Decimal
    total_cost: Decimal
    technician: Optional[str] = None


class ProjectFinancialSummary(BaseModel):
    """
    Financial summary for a project.
    
    ✅ Data dihitung dari:
    - Project.estimated_cost, Project.actual_cost
    - Inventory material usage
    - Project labor items
    - Project expenses
    - Payment module (total_paid, deposit_paid)
    """
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    material_cost: float = 0.0
    labor_cost: float = 0.0
    expenses: float = 0.0
    
    # Payment related (dari Payment module)
    total_paid: float = 0.0
    deposit_paid: float = 0.0
    remaining_balance: float = 0.0
    
    # Derived
    profit: float = 0.0
    margin: float = 0.0
    
    # Details
    material_usages: List[ProjectMaterialSummary] = Field(default_factory=list)
    labor_items: List[ProjectLaborSummary] = Field(default_factory=list)
    
class ProjectFinancialSummaryResponse(BaseModel):
    """Response untuk financial summary all projects."""
    total_projects: int
    estimated_cost: float
    actual_cost: float
    profit: float
    negative_margin_projects: int


# ============================================================================
# Project Detail Response (Aggregate)
# ============================================================================

class ProjectDetailResponse(BaseModel):
    """Detailed project response with all related data."""
    project: ProjectResponse
    financial_summary: ProjectFinancialSummary
    tasks: List[ProjectTaskResponse] = Field(default_factory=list)
    labor_items: List[ProjectLaborResponse] = Field(default_factory=list)
    expenses: List[ProjectExpenseResponse] = Field(default_factory=list)
    price_list_items: List[ProjectPriceListItemResponse] = Field(default_factory=list)
    activities: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Kanban
# ============================================================================

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
    stage: Optional[Dict[str, Any]] = None


class ProjectKanbanResponse(BaseModel):
    """Response untuk kanban board."""
    draft: List[ProjectKanbanItem] = Field(default_factory=list)
    active: List[ProjectKanbanItem] = Field(default_factory=list)
    in_progress: List[ProjectKanbanItem] = Field(default_factory=list)
    on_hold: List[ProjectKanbanItem] = Field(default_factory=list)
    completed: List[ProjectKanbanItem] = Field(default_factory=list)
    cancelled: List[ProjectKanbanItem] = Field(default_factory=list)


# ============================================================================
# Project Stage Schemas
# ============================================================================

class ProjectStageCreate(BaseModel):
    """Schema untuk membuat stage."""
    name: str = Field(..., min_length=1, max_length=100,
                      description="Nama stage")
    color: Optional[str] = Field(None, max_length=50, description="Warna")
    sort_order: int = Field(default=0, description="Urutan")
    description: Optional[str] = Field(None, description="Deskripsi")
    is_default: bool = Field(default=False, description="Stage default")


class ProjectStageUpdate(BaseModel):
    """Schema untuk update stage."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class ProjectStageResponse(BaseModel):
    """Response untuk stage."""
    id: UUID
    name: str
    color: Optional[str] = None
    sort_order: int
    description: Optional[str] = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Statistics
# ============================================================================

class ProjectStatisticsResponse(BaseModel):
    """Response untuk project statistics."""
    total: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    financial: Dict[str, float]
    active_projects: List[Dict[str, Any]]


class ProjectFinancialSummaryResponse(BaseModel):
    """Response untuk financial summary."""
    total_projects: int
    estimated_cost: float
    actual_cost: float
    estimated_revenue: float
    actual_revenue: float
    total_deposit: float
    negative_margin_projects: int
    profit: float


class ProjectDocumentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    document_type: str = Field(..., description="spk, bast, invoice, etc")
    description: Optional[str] = None



class ProjectDocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    document_type: str
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    uploaded_by: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

# ============================================================================
# Project Team Schemas
# ============================================================================

class ProjectTeamCreate(BaseModel):
    """Schema untuk membuat team member."""
    user_id: UUID = Field(..., description="User ID")
    role: str = Field(..., description="project_manager, supervisor, technician")


class ProjectTeamResponse(BaseModel):
    """Response untuk team member."""
    id: UUID
    project_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    role: str
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# Project Timeline Schemas
# ============================================================================

class ProjectTimelineCreate(BaseModel):
    """Schema untuk membuat timeline project."""
    milestone_name: str = Field(..., min_length=1, max_length=255, description="Nama milestone")
    description: Optional[str] = Field(None, description="Deskripsi")
    due_date: datetime = Field(..., description="Tanggal deadline")
    sort_order: int = Field(default=0, description="Urutan")


class ProjectTimelineUpdate(BaseModel):
    """Schema untuk update timeline project."""
    milestone_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(None, description="pending, in_progress, completed, overdue, cancelled")
    sort_order: Optional[int] = None


class ProjectTimelineResponse(BaseModel):
    """Response untuk timeline project."""
    id: UUID
    project_id: UUID
    milestone_name: str
    description: Optional[str] = None
    due_date: datetime
    completed_at: Optional[datetime] = None
    status: str
    sort_order: int
    reminder_sent: bool = False
    is_overdue: bool = False
    days_until_due: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Project Document Schemas
# ============================================================================

class ProjectDocumentCreate(BaseModel):
    """Schema untuk membuat dokumen project."""
    name: str = Field(..., min_length=1, max_length=255, description="Nama dokumen")
    document_type: str = Field(..., description="spk, bast, invoice, design, photo, other")
    description: Optional[str] = Field(None, description="Deskripsi")
    is_public: bool = Field(default=True, description="Dapat dilihat semua")


class ProjectDocumentUpdate(BaseModel):
    """Schema untuk update dokumen project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None


class ProjectDocumentResponse(BaseModel):
    """Response untuk dokumen project."""
    id: UUID
    project_id: UUID
    name: str
    document_type: str
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_by: Optional[str] = None
    description: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDocumentUpload(BaseModel):
    """Schema untuk upload dokumen."""
    file: UploadFile
    name: str = Field(..., min_length=1, max_length=255)
    document_type: str = Field(..., description="spk, bast, invoice, design, photo, other")
    description: Optional[str] = None
    is_public: bool = True
    
    
    
    
# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectMinimalResponse",
    "ProjectUpdateStatus",
    "ProjectUpdateProgress",
    "ProjectCancel",
    "ProjectDetailResponse",
    
    # Task
    "ProjectTaskCreate",
    "ProjectTaskUpdate",
    "ProjectTaskResponse",
    
    # Labor
    "ProjectLaborCreate",
    "ProjectLaborResponse",
    
    # Expense
    "ProjectExpenseCreate",
    "ProjectExpenseResponse",
    
    # Price List
    "ProjectPriceListItemResponse",
    
    # Stage
    "ProjectStageCreate",
    "ProjectStageUpdate",
    "ProjectStageResponse",
    
    # Timeline
    "ProjectTimelineCreate",
    "ProjectTimelineUpdate",
    "ProjectTimelineResponse",
    
    # Document
    "ProjectDocumentCreate",
    "ProjectDocumentUpdate",
    "ProjectDocumentResponse",
    "ProjectDocumentUpload",
    
    # Team
    "ProjectTeamCreate",
    "ProjectTeamResponse",
    
    # Financial Summary (✅ TETAP ADA)
    "ProjectMaterialSummary",
    "ProjectLaborSummary",
    "ProjectFinancialSummary",
    "ProjectFinancialSummaryResponse",
    
    # Kanban
    "ProjectKanbanItem",
    "ProjectKanbanResponse",
    
    # Statistics
    "ProjectStatisticsResponse",
]