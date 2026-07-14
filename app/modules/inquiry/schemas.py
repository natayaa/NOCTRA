# modules/inquiry/schemas.py
from fastapi import UploadFile
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, computed_field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from core.constants import InquiryStatus


# ============================================================================
# Nested Response Schemas
# ============================================================================

class InquiryPhotoResponse(BaseModel):
    """Response untuk foto inquiry."""
    id: UUID
    file_path: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    stage: str
    is_primary: bool = False
    sort_order: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InquiryActivityResponse(BaseModel):
    """Response untuk aktivitas inquiry."""
    id: UUID
    activity: str
    activity_type: Optional[str] = None
    performed_by: Optional[str] = None
    meta_data: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkshopNoteResponse(BaseModel):
    """Response untuk workshop note."""
    id: UUID
    note: str
    note_type: str
    author: Optional[str] = None
    is_private: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectMinimalResponse(BaseModel):
    id: UUID
    name: str
    status: str
    progress: int
    estimated_cost: Optional[float] = None      # ✅ TAMBAHKAN
    actual_cost: Optional[float] = None
    deposit_amount: Optional[float] = None      # ✅ TAMBAHKAN
    estimated_revenue: Optional[float] = None   # ✅ TAMBAHKAN
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentMinimalResponse(BaseModel):
    """Minimal response untuk payment."""
    id: UUID
    payment_type: str
    amount: Decimal
    status: str
    paid_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request Schemas
# ============================================================================

class CustomerInquiryCreate(BaseModel):
    """Schema untuk membuat inquiry baru."""
    customer_name: str = Field(..., min_length=3,
                               max_length=100, description="Nama lengkap customer")
    customer_phone_number: str = Field(..., min_length=8,
                                       max_length=20, description="Nomor WhatsApp")
    customer_email: Optional[EmailStr] = Field(
        None, description="Email customer")
    province: Optional[str] = Field(
        None, max_length=100, description="Provinsi")
    city: Optional[str] = Field(
        None, max_length=100, description="Kota/Kabupaten")

    vehicle_brand: str = Field(..., min_length=2,
                               max_length=50, description="Merk kendaraan")
    vehicle_model: str = Field(..., min_length=2,
                               max_length=100, description="Model kendaraan")
    vehicle_year: Optional[int] = Field(
        None, ge=1950, le=2035, description="Tahun kendaraan")
    vehicle_license_plate: Optional[str] = Field(
        None, max_length=20, description="Plat nomor")
    previous_repaint: Optional[str] = Field(
        None, max_length=50, description="Riwayat repaint")
    bike_modified: Optional[str] = Field(
        None, max_length=10, description="Status modifikasi")
    vehicle_condition: Optional[str] = Field(
        None, max_length=500, description="Kondisi kendaraan")

    project_type: str = Field(..., min_length=2,
                              max_length=50, description="Tipe project")
    services: Optional[str] = Field(
        None, max_length=500, description="Layanan yang dipilih")
    desired_finish: Optional[str] = Field(
        None, max_length=50, description="Finish yang diinginkan")
    desired_color: Optional[str] = Field(
        None, max_length=100, description="Warna yang diinginkan")
    estimated_budget: Optional[int] = Field(
        None, ge=0, description="Estimasi budget")
    deadline: Optional[str] = Field(
        None, max_length=50, description="Target waktu")
    priority: Optional[str] = Field(
        None, max_length=50, description="Prioritas utama")
    project_description: str = Field(..., min_length=20,
                                     max_length=5000, description="Deskripsi project")
    reference_link: Optional[str] = Field(None, description="Link referensi")
    source: Optional[str] = Field(
        None, max_length=50, description="Sumber inquiry")

    @field_validator("customer_phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r'^(\+62|62|08)\d{8,13}$', v):
            raise ValueError('Format nomor telepon tidak valid')
        return v

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("project_type")
    @classmethod
    async def validate_project_type(cls, v: str) -> str:
        # Validasi akan dilakukan di service layer
        return v


class CustomerInquiryUpdate(BaseModel):
    """Schema untuk update inquiry."""
    customer_name: Optional[str] = Field(None, min_length=3, max_length=100)
    customer_phone_number: Optional[str] = Field(
        None, min_length=8, max_length=20)
    customer_email: Optional[EmailStr] = None
    province: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    vehicle_brand: Optional[str] = Field(None, min_length=2, max_length=50)
    vehicle_model: Optional[str] = Field(None, min_length=2, max_length=100)
    vehicle_year: Optional[int] = Field(None, ge=1950, le=2035)
    vehicle_license_plate: Optional[str] = Field(None, max_length=20)
    previous_repaint: Optional[str] = Field(None, max_length=50)
    bike_modified: Optional[str] = Field(None, max_length=10)
    vehicle_condition: Optional[str] = Field(None, max_length=500)
    project_type: Optional[str] = Field(None, min_length=2, max_length=50)
    services: Optional[str] = Field(None, max_length=500)
    desired_finish: Optional[str] = Field(None, max_length=50)
    desired_color: Optional[str] = Field(None, max_length=100)
    estimated_budget: Optional[int] = Field(None, ge=0)
    deadline: Optional[str] = Field(None, max_length=50)
    priority: Optional[str] = Field(None, max_length=50)
    project_description: Optional[str] = Field(
        None, min_length=20, max_length=5000)
    reference_link: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    source: Optional[str] = Field(None, max_length=50)


# ============================================================================
# Action Schemas
# ============================================================================

class InquiryStatusUpdate(BaseModel):
    """Schema untuk update status inquiry."""
    status: str = Field(..., description="Status baru")
    note: Optional[str] = Field(None, description="Catatan perubahan status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [e.value for e in InquiryStatus]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class InquiryReject(BaseModel):
    """Schema untuk menolak inquiry."""
    reason: str = Field(..., min_length=1, description="Alasan penolakan")


class InquirySendQuotation(BaseModel):
    """Schema untuk mengirim quotation."""
    estimated_cost: Decimal = Field(..., gt=0, description="Estimasi biaya")
    notes: Optional[str] = Field(None, description="Catatan quotation")


class InquiryConvertToProject(BaseModel):
    """Schema untuk convert inquiry ke project."""
    project_name: Optional[str] = Field(
        None, description="Nama project (opsional)")
    project_start_date: Optional[datetime] = Field(
        None, description="Tanggal mulai project")
    project_target_delivery: Optional[datetime] = Field(
        None, description="Target delivery")
    estimated_cost: Optional[Decimal] = Field(
        None, ge=0, description="Estimasi biaya")


class InquiryClose(BaseModel):
    """Schema untuk menutup inquiry."""
    reason: str = Field(..., min_length=1, description="Alasan penutupan")
    note: Optional[str] = Field(None, description="Catatan tambahan")


class NoteCreate(BaseModel):
    """Schema untuk membuat catatan."""
    note: str = Field(..., min_length=1, description="Catatan")
    note_type: str = Field(default="internal", description="Tipe catatan")
    is_private: bool = Field(default=False, description="Catatan privat")


# ============================================================================
# Response Schemas
# ============================================================================

class CustomerInquirySummary(BaseModel):
    """Ringkasan inquiry untuk list view."""
    id: UUID
    customer_name: str
    customer_phone_number: str
    vehicle_brand: str
    vehicle_model: str
    project_type: str
    status: str
    source: Optional[str] = None
    created_at: datetime
    project: Optional[ProjectMinimalResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerInquiryResponse(BaseModel):
    """Detail inquiry untuk single view."""
    id: UUID
    customer_name: str
    customer_phone_number: str
    customer_email: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None

    vehicle_brand: str
    vehicle_model: str
    vehicle_year: Optional[int] = None
    vehicle_license_plate: Optional[str] = None
    previous_repaint: Optional[str] = None
    bike_modified: Optional[str] = None
    vehicle_condition: Optional[str] = None

    project_type: str
    services: Optional[str] = None
    desired_finish: Optional[str] = None
    desired_color: Optional[str] = None
    estimated_budget: Optional[int] = None
    deposit_required: Optional[Decimal] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    project_description: str
    reference_link: Optional[str] = None

    status: str
    note: Optional[str] = None
    source: Optional[str] = None
    conversion_rate: Optional[Decimal] = None

    # Tracking
    contacted_at: Optional[datetime] = None
    quoted_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    closed_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    # Financial
    deposit_required: Optional[Decimal] = None
    deposit_paid: Optional[Decimal] = None
    total_paid: Optional[Decimal] = None
    total_invoiced: Optional[Decimal] = None
    balance_due: Optional[Decimal] = None

    # Relationships
    photos: List[InquiryPhotoResponse] = Field(default_factory=list)
    activities: List[InquiryActivityResponse] = Field(default_factory=list)
    workshop_notes: List[WorkshopNoteResponse] = Field(default_factory=list)
    project: Optional[ProjectMinimalResponse] = None
    payments: List[PaymentMinimalResponse] = Field(default_factory=list)

    # COMPUTED FIELD - > Frontend consistency
    @computed_field
    @property
    def estimated_cost(self) -> float:
        """Nilai estimasi cost dari project atau inquiry"""
        if self.project and self.project.estimated_cost is not None:
            return float(self.project.estimated_cost)

        return float(self.project.estimated_cost or 0)

    @computed_field
    @property
    def deposit_amount(self) -> float:
        """Nilai deposit dari project atau inquiry"""
        if self.project and hasattr(self.project, 'deposit_amount') and self.project.deposit_amount is not None:
            return float(self.project.deposit_amount)
        return float(self.deposit_required or 0)

    @computed_field
    @property
    def actual_cost(self) -> float:
        """Actual cost - bisa dihitung dari labor + material."""
        # Ini akan dihitung dari data terkait, default 0
        return 0.0

    @computed_field
    @property
    def estimated_revenue(self) -> float:
        """Estimasi revenue - dari project atau inquiry."""
        if self.project and hasattr(self.project, 'estimated_revenue') and self.project.estimated_revenue is not None:
            return float(self.project.estimated_revenue)
        return 0.0

    @computed_field
    @property
    def actual_revenue(self) -> float:
        """Actual revenue - dari total payment yang sudah completed."""
        if self.payments:
            total = sum(float(p.amount)
                        for p in self.payments if p.status == "completed")
            return total
        return 0.0

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Inquiry Statistics
# ============================================================================

class InquiryStatisticsResponse(BaseModel):
    """Response untuk inquiry statistics."""
    total: int
    by_status: Dict[str, int]
    by_brand: Dict[str, int]
    converted: int
    conversion_rate: float
    recent: List[CustomerInquirySummary]


class InquiryListResponse(BaseModel):
    """Response untuk list inquiry dengan pagination."""
    items: List[CustomerInquirySummary]
    total: int
    limit: int
    offset: int


# ============================================================================
# Project Timeline Schemas
# ============================================================================

class ProjectTimelineCreate(BaseModel):
    """Schema untuk membuat timeline project."""
    milestone_name: str = Field(..., min_length=1,
                                max_length=255, description="Nama milestone")
    description: Optional[str] = Field(None, description="Deskripsi")
    due_date: datetime = Field(..., description="Tanggal deadline")
    sort_order: int = Field(default=0, description="Urutan")


class ProjectTimelineUpdate(BaseModel):
    """Schema untuk update timeline project."""
    milestone_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(
        None, description="pending, in_progress, completed, overdue, cancelled")
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
    name: str = Field(..., min_length=1, max_length=255,
                      description="Nama dokumen")
    document_type: str = Field(...,
                               description="spk, bast, invoice, design, photo, other")
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
    document_type: str = Field(...,
                               description="spk, bast, invoice, design, photo, other")
    description: Optional[str] = None
    is_public: bool = True


# modules/inquiry/schemas.py - TAMBAHAN

# ============================================================================
# Inquiry Follow-Up Schemas
# ============================================================================

class InquiryFollowUpCreate(BaseModel):
    """Schema untuk membuat follow-up."""
    scheduled_at: datetime = Field(..., description="Jadwal follow-up")
    note: Optional[str] = Field(None, description="Catatan")
    assigned_to: Optional[str] = Field(
        None, max_length=100, description="Ditugaskan ke")


class InquiryFollowUpUpdate(BaseModel):
    """Schema untuk update follow-up."""
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = Field(
        None, description="pending, done, missed, cancelled")
    note: Optional[str] = None
    result: Optional[str] = None
    assigned_to: Optional[str] = Field(None, max_length=100)


class InquiryFollowUpComplete(BaseModel):
    """Schema untuk menyelesaikan follow-up."""
    result: str = Field(..., min_length=1, description="Hasil follow-up")
    note: Optional[str] = None


class InquiryFollowUpResponse(BaseModel):
    """Response untuk follow-up."""
    id: UUID
    inquiry_id: UUID
    scheduled_at: datetime
    performed_at: Optional[datetime] = None
    status: str
    note: Optional[str] = None
    result: Optional[str] = None
    assigned_to: Optional[str] = None
    reminder_sent: bool = False
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
