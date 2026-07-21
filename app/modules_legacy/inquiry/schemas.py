# modules/inquiry/schemas.py
from fastapi import UploadFile
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, computed_field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from core.constants import InquiryStatus


# ============================================================================
# BASE SCHEMAS
# ============================================================================

class InquiryBase(BaseModel):
    """Base schema untuk inquiry dengan field validasi."""

    # Customer Information
    customer_name: str = Field(..., min_length=3, max_length=100, description="Nama lengkap customer")
    customer_phone_number: str = Field(..., min_length=8, max_length=20, description="Nomor WhatsApp/telepon")
    customer_email: Optional[EmailStr] = Field(None, description="Email customer (opsional)")
    province: Optional[str] = Field(None, max_length=100, description="Provinsi")
    city: Optional[str] = Field(None, max_length=100, description="Kota/Kabupaten")
    address: Optional[str] = Field(None, max_length=500, description="Alamat")
    # Vehicle Information
    vehicle_brand: str = Field(..., min_length=2, max_length=50, description="Merk kendaraan")
    vehicle_model: str = Field(..., min_length=2, max_length=100,description="Model kendaraan")
    vehicle_year: Optional[int] = Field(None, ge=1950, le=2050, description="Tahun kendaraan")
    vehicle_license_plate: Optional[str] = Field(None, max_length=20, description="Plat nomor")
    previous_repaint: Optional[str] = Field(None, max_length=50, description="Riwayat repaint")
    bike_modified: Optional[str] = Field(None, max_length=10, description="Status modifikasi")
    vehicle_condition: Optional[str] = Field(None, max_length=500, description="Kondisi kendaraan")

    # Project Information
    project_type: str = Field(..., min_length=2, max_length=50, description="Tipe project")
    services: Optional[str] = Field(None, max_length=500, description="Layanan yang dipilih")
    desired_finish: Optional[str] = Field(None, max_length=50, description="Finish yang diinginkan")
    desired_color: Optional[str] = Field(None, max_length=100, description="Warna yang diinginkan")
    estimated_budget: Optional[int] = Field(None, ge=0, description="Estimasi budget (dalam Rupiah)")
    deadline: Optional[str] = Field(None, max_length=50, description="Target waktu")
    priority: Optional[str] = Field(None, max_length=50, description="Prioritas utama")
    project_description: str = Field(..., min_length=20, max_length=5000, description="Deskripsi project")
    reference_link: Optional[str] = Field(None, description="Link referensi")
    source: Optional[str] = Field(None, max_length=50, description="Sumber inquiry")

    # ============ Validators ============

    @field_validator("customer_phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate Indonesian phone number format."""
        import re
        # Clean the phone number
        cleaned = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not re.match(r'^(\+62|62|08)\d{8,13}$', cleaned):
            raise ValueError('Format nomor telepon tidak valid. '
                'Gunakan format: 081234567890 atau +6281234567890'
            )
        return v

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email if provided."""
        if v:
            # EmailStr already validates format
            return v.lower().strip()
        return v

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value: Any) -> Any:
        """Strip whitespace from all string values."""
        if isinstance(value, str):
            return value.strip()
        return value

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class CustomerInquiryCreate(InquiryBase):
    """Schema untuk membuat inquiry baru."""
    pass


class CustomerInquiryUpdate(BaseModel):
    """Schema untuk update inquiry."""
    customer_name: Optional[str] = Field(None, min_length=3, max_length=100)
    customer_phone_number: Optional[str] = Field(
        None, min_length=8, max_length=20)
    customer_email: Optional[EmailStr] = None
    province: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    address: str = Field(None, min_length=2, max_length=500)
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
    project_description: Optional[str] = Field(None, min_length=20, max_length=5000)
    reference_link: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    source: Optional[str] = Field(None, max_length=50)

    @field_validator("customer_phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            import re
            cleaned = v.replace(' ', '').replace(
                '-', '').replace('(', '').replace(')', '')
            if not re.match(r'^(\+62|62|08)\d{8,13}$', cleaned):
                raise ValueError(
                    'Format nomor telepon tidak valid. '
                    'Gunakan format: 081234567890 atau +6281234567890'
                )
        return v

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid"
    )


# ============================================================================
# ACTION SCHEMAS
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

    model_config = ConfigDict(extra="forbid")


class InquiryReject(BaseModel):
    """Schema untuk menolak inquiry."""
    reason: str = Field(..., min_length=1, max_length=500, description="Alasan penolakan")
    note: Optional[str] = Field(
        None, max_length=500, description="Catatan tambahan")

    model_config = ConfigDict(extra="forbid")


class InquirySendQuotation(BaseModel):
    """Schema untuk mengirim quotation."""
    estimated_cost: Decimal = Field(..., gt=0, description="Estimasi biaya")
    notes: Optional[str] = Field(None, max_length=500, description="Catatan quotation")

    @field_validator("estimated_cost")
    @classmethod
    def validate_cost(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Estimated cost must be greater than 0")
        return v

    model_config = ConfigDict(extra="forbid")


class InquiryConvertToProject(BaseModel):
    """Schema untuk convert inquiry ke project."""
    project_name: Optional[str] = Field(None, min_length=3, max_length=255, description="Nama project")
    project_start_date: Optional[datetime] = Field(None, description="Tanggal mulai project")
    project_target_delivery: Optional[datetime] = Field(None, description="Target delivery")
    estimated_cost: Optional[Decimal] = Field(None, ge=0, description="Estimasi biaya")

    @field_validator("estimated_cost")
    @classmethod
    def validate_cost(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("Estimated cost cannot be negative")
        return v

    model_config = ConfigDict(extra="forbid")


class InquiryClose(BaseModel):
    """Schema untuk menutup inquiry."""
    reason: str = Field(..., min_length=1, max_length=500, description="Alasan penutupan")
    note: Optional[str] = Field(None, max_length=500, description="Catatan tambahan")

    model_config = ConfigDict(extra="forbid")


class NoteCreate(BaseModel):
    """Schema untuk membuat catatan."""
    note: str = Field(..., min_length=1, max_length=2000, description="Catatan")
    note_type: str = Field(default="internal", description="Tipe catatan")
    is_private: bool = Field(default=False, description="Catatan privat")

    @field_validator("note_type")
    @classmethod
    def validate_note_type(cls, v: str) -> str:
        valid_types = ["internal", "customer", "rejection",
                       "quotation", "follow_up", "general"]
        if v not in valid_types:
            raise ValueError(f"Note type must be one of: {valid_types}")
        return v

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# FOLLOW-UP SCHEMAS
# ============================================================================

class InquiryFollowUpCreate(BaseModel):
    """Schema untuk membuat follow-up."""
    scheduled_at: datetime = Field(..., description="Jadwal follow-up")
    note: Optional[str] = Field(None, max_length=500, description="Catatan")
    assigned_to: Optional[str] = Field(None, max_length=100, description="Ditugaskan ke")

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, v: datetime) -> datetime:
        from datetime import timedelta
        if v < datetime.now() - timedelta(minutes=5):
            raise ValueError("Scheduled time cannot be in the past")
        return v

    model_config = ConfigDict(extra="forbid")


class InquiryFollowUpUpdate(BaseModel):
    """Schema untuk update follow-up."""
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = Field(None, description="pending, done, missed, cancelled")
    note: Optional[str] = None
    result: Optional[str] = None
    assigned_to: Optional[str] = Field(None, max_length=100)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v:
            valid_statuses = ["pending", "done", "missed", "cancelled"]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {valid_statuses}")
        return v

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v:
            from datetime import timedelta
            if v < datetime.now() - timedelta(minutes=5):
                raise ValueError("Scheduled time cannot be in the past")
        return v

    model_config = ConfigDict(extra="forbid")


class InquiryFollowUpComplete(BaseModel):
    """Schema untuk menyelesaikan follow-up."""
    result: str = Field(..., min_length=1, max_length=500, description="Hasil follow-up")
    note: Optional[str] = Field(None, max_length=500, description="Catatan tambahan")

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# RESPONSE SCHEMAS
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
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InquiryActivityResponse(BaseModel):
    """Response untuk aktivitas inquiry."""
    id: UUID
    activity: str
    activity_type: Optional[str] = None
    performed_by: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
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
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentMinimalResponse(BaseModel):
    """Minimal response untuk payment."""
    id: UUID
    payment_type: str
    amount: Decimal
    status: str
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectMinimalResponse(BaseModel):
    """Minimal response untuk project."""
    id: UUID
    name: str
    status: str
    progress: int
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    deposit_amount: Optional[float] = None
    estimated_revenue: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    updated_at: datetime
    project: Optional[ProjectMinimalResponse] = None

    @computed_field
    @property
    def vehicle_info(self) -> str:
        return f"{self.vehicle_brand} {self.vehicle_model}".strip()

    @computed_field
    @property
    def display_name(self) -> str:
        return f"{self.customer_name} - {self.vehicle_info}"

    model_config = ConfigDict(from_attributes=True)


class CustomerInquiryResponse(BaseModel):
    """Detail inquiry untuk single view."""
    # ID & Timestamps
    id: UUID
    created_at: datetime
    updated_at: datetime

    # Customer Information
    customer_name: str
    customer_phone_number: str
    customer_email: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None

    # Vehicle Information
    vehicle_brand: str
    vehicle_model: str
    vehicle_year: Optional[int] = None
    vehicle_license_plate: Optional[str] = None
    previous_repaint: Optional[str] = None
    bike_modified: Optional[str] = None
    vehicle_condition: Optional[str] = None

    # Project Information
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

    # Status & Metadata
    status: str
    note: Optional[str] = None
    source: Optional[str] = None
    conversion_rate: Optional[Decimal] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Tracking
    contacted_at: Optional[datetime] = None
    quoted_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    closed_reason: Optional[str] = None

    # Financial
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

    # ============ Computed Fields ============

    @computed_field
    @property
    def vehicle_info(self) -> str:
        """Vehicle brand + model."""
        return f"{self.vehicle_brand} {self.vehicle_model}".strip()

    @computed_field
    @property
    def display_name(self) -> str:
        """Display name for UI."""
        return f"{self.customer_name} - {self.vehicle_info}"

    @computed_field
    @property
    def is_converted(self) -> bool:
        """Check if inquiry has been converted."""
        return self.project is not None

    @computed_field
    @property
    def estimated_cost(self) -> float:
        """Estimated cost from project or inquiry."""
        if self.project and self.project.estimated_cost is not None:
            return float(self.project.estimated_cost)
        return float(self.estimated_budget or 0)

    @computed_field
    @property
    def deposit_amount(self) -> float:
        """Deposit amount from project or inquiry."""
        if self.project and self.project.deposit_amount is not None:
            return float(self.project.deposit_amount)
        return float(self.deposit_required or 0)

    @computed_field
    @property
    def actual_cost(self) -> float:
        """Actual cost from project or 0."""
        if self.project and self.project.actual_cost is not None:
            return float(self.project.actual_cost)
        return 0.0

    @computed_field
    @property
    def estimated_revenue(self) -> float:
        """Estimated revenue from project."""
        if self.project and self.project.estimated_revenue is not None:
            return float(self.project.estimated_revenue)
        return 0.0

    @computed_field
    @property
    def actual_revenue(self) -> float:
        """Actual revenue from completed payments."""
        if self.payments:
            total = sum(float(p.amount)
                        for p in self.payments if p.status == "completed")
            return total
        return 0.0

    @computed_field
    @property
    def total_payments_count(self) -> int:
        """Total number of payments."""
        return len(self.payments)

    @computed_field
    @property
    def total_photos_count(self) -> int:
        """Total number of photos."""
        return len(self.photos)

    @computed_field
    @property
    def days_since_created(self) -> int:
        """Days since inquiry was created."""
        if self.created_at:
            delta = datetime.now() - self.created_at
            return delta.days
        return 0

    @computed_field
    @property
    def is_stale(self) -> bool:
        """Check if inquiry is stale (not updated for 30 days)."""
        if self.status in ["new", "under_review", "contacted"]:
            return self.days_since_created > 30
        return False

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# INQUIRY STATISTICS
# ============================================================================

class InquiryStatisticsResponse(BaseModel):
    """Response untuk inquiry statistics."""
    total: int
    by_status: Dict[str, int]
    by_brand: Dict[str, int]
    by_source: Dict[str, int]
    converted: int
    rejected: int
    conversion_rate: float
    recent: List[CustomerInquirySummary]

    @computed_field
    @property
    def active_count(self) -> int:
        """Count of active inquiries."""
        active_statuses = ["new", "under_review",
                           "contacted", "quoted", "approved"]
        return sum(self.by_status.get(s, 0) for s in active_statuses)

    @computed_field
    @property
    def completion_rate(self) -> float:
        """Rate of completed/converted inquiries."""
        completed = self.by_status.get("completed", 0) + self.converted
        total = self.total or 1
        return round((completed / total * 100), 2)

    model_config = ConfigDict(from_attributes=True)


class InquiryListResponse(BaseModel):
    """Response untuk list inquiry dengan pagination."""
    items: List[CustomerInquirySummary]
    total: int
    limit: int
    offset: int
    page: int
    total_pages: int

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.offset + self.limit < self.total

    @computed_field
    @property
    def has_previous(self) -> bool:
        return self.offset > 0

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PROJECT TIMELINE SCHEMAS
# ============================================================================

class ProjectTimelineCreate(BaseModel):
    """Schema untuk membuat timeline project."""
    milestone_name: str = Field(..., min_length=1,
                                max_length=255, description="Nama milestone")
    description: Optional[str] = Field(
        None, max_length=1000, description="Deskripsi")
    due_date: datetime = Field(..., description="Tanggal deadline")
    sort_order: int = Field(default=0, description="Urutan")

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: datetime) -> datetime:
        if v < datetime.now():
            raise ValueError("Due date cannot be in the past")
        return v

    model_config = ConfigDict(extra="forbid")


class ProjectTimelineUpdate(BaseModel):
    """Schema untuk update timeline project."""
    milestone_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(
        None, description="pending, in_progress, completed, overdue, cancelled")
    sort_order: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v:
            valid_statuses = ["pending", "in_progress",
                              "completed", "overdue", "cancelled"]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {valid_statuses}")
        return v

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v < datetime.now():
            raise ValueError("Due date cannot be in the past")
        return v

    model_config = ConfigDict(extra="forbid")


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

    @computed_field
    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @computed_field
    @property
    def is_in_progress(self) -> bool:
        return self.status == "in_progress"

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PROJECT DOCUMENT SCHEMAS
# ============================================================================

class ProjectDocumentCreate(BaseModel):
    """Schema untuk membuat dokumen project."""
    name: str = Field(..., min_length=1, max_length=255,
                      description="Nama dokumen")
    document_type: str = Field(...,
                               description="spk, bast, invoice, design, photo, other")
    description: Optional[str] = Field(
        None, max_length=1000, description="Deskripsi")
    is_public: bool = Field(default=True, description="Dapat dilihat semua")

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        valid_types = ["spk", "bast", "invoice", "design", "photo", "other"]
        if v not in valid_types:
            raise ValueError(f"Document type must be one of: {valid_types}")
        return v

    model_config = ConfigDict(extra="forbid")


class ProjectDocumentUpdate(BaseModel):
    """Schema untuk update dokumen project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_public: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


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

    @computed_field
    @property
    def file_size_kb(self) -> Optional[float]:
        if self.file_size:
            return round(self.file_size / 1024, 2)
        return None

    @computed_field
    @property
    def file_size_mb(self) -> Optional[float]:
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None

    model_config = ConfigDict(from_attributes=True)


class ProjectDocumentUpload(BaseModel):
    """Schema untuk upload dokumen."""
    file: UploadFile
    name: str = Field(..., min_length=1, max_length=255)
    document_type: str = Field(...,
                               description="spk, bast, invoice, design, photo, other")
    description: Optional[str] = Field(None, max_length=1000)
    is_public: bool = True

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# INQUIRY FILTER SCHEMAS
# ============================================================================

class InquiryFilterParams(BaseModel):
    """Schema untuk filter inquiry."""
    status: Optional[str] = None
    search: Optional[str] = None
    brand: Optional[str] = None
    project_status: Optional[str] = None
    has_project: Optional[bool] = None
    source: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_budget: Optional[int] = None
    max_budget: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class InquirySortParams(BaseModel):
    """Schema untuk sorting inquiry."""
    sort_by: str = Field(default="created_at",
                         description="Field untuk sorting")
    sort_order: str = Field(default="desc", description="asc or desc")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        valid_fields = [
            "created_at", "updated_at", "customer_name",
            "vehicle_brand", "vehicle_model", "status",
            "estimated_budget", "project_type"
        ]
        if v not in valid_fields:
            raise ValueError(f"Sort by must be one of: {valid_fields}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        if v not in ["asc", "desc"]:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# BULK OPERATIONS SCHEMAS
# ============================================================================

class InquiryBulkStatusUpdate(BaseModel):
    """Schema untuk bulk update status."""
    inquiry_ids: List[UUID] = Field(..., min_length=1,
                                    description="List of inquiry IDs")
    status: str = Field(..., description="New status")
    note: Optional[str] = Field(
        None, max_length=500, description="Note for all")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [e.value for e in InquiryStatus]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v

    @field_validator("inquiry_ids")
    @classmethod
    def validate_ids(cls, v: List[UUID]) -> List[UUID]:
        if len(v) > 100:
            raise ValueError("Maximum 100 inquiries per bulk operation")
        return v

    model_config = ConfigDict(extra="forbid")


class InquiryBulkDelete(BaseModel):
    """Schema untuk bulk delete inquiry."""
    inquiry_ids: List[UUID] = Field(..., min_length=1,
                                    description="List of inquiry IDs")
    permanent: bool = Field(
        default=False, description="Permanent delete or soft delete")

    @field_validator("inquiry_ids")
    @classmethod
    def validate_ids(cls, v: List[UUID]) -> List[UUID]:
        if len(v) > 100:
            raise ValueError("Maximum 100 inquiries per bulk operation")
        return v

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# EXPORT SCHEMAS
# ============================================================================

class InquiryExportParams(BaseModel):
    """Schema untuk export inquiry."""
    status: Optional[str] = None
    search: Optional[str] = None
    brand: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    format: str = Field(default="csv", description="Export format: csv, excel")
    max_records: int = Field(
        default=10000, ge=1, le=50000, description="Max records to export")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ["csv", "excel"]:
            raise ValueError("Format must be 'csv' or 'excel'")
        return v

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# WHATSAPP MESSAGE SCHEMAS
# ============================================================================

class WhatsAppMessageResponse(BaseModel):
    """Response untuk WhatsApp message."""
    message: str
    phone: str
    template_id: Optional[str] = None

    @computed_field
    @property
    def whatsapp_url(self) -> str:
        """Generate WhatsApp URL."""
        import urllib.parse
        encoded_message = urllib.parse.quote(self.message)
        phone = self.phone.replace('+', '').replace(' ', '').replace('-', '')
        return f"https://wa.me/{phone}?text={encoded_message}"

    model_config = ConfigDict(from_attributes=True)
