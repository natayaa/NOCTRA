# modules/inquiry/models.py
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Index, String, Text, ForeignKey, Integer, JSON,
    DateTime, func, Numeric, Boolean, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
from core.constants import InquiryStatus


class CustomerInquiry(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model untuk customer inquiry.
    Semua field yang dibutuhkan dari form submission.
    """
    __tablename__ = "tb_customer_inquiry"

    # ============================================================
    # 1. CUSTOMER INFORMATION (dari form step 1)
    # ============================================================
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="Nama lengkap customer")
    customer_phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True, comment="Nomor WhatsApp/telepon")
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Email customer (opsional)")
    province: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Provinsi")
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Kota/Kabupaten")
    address: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Alamat customer secara lengkap")

    # ============================================================
    # 2. VEHICLE INFORMATION (dari form step 2)
    # ============================================================
    vehicle_brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="Merk kendaraan (Yamaha, Honda, dll)")
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False, comment="Model kendaraan (Mio, Vixion, dll)")
    vehicle_year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Tahun pembuatan kendaraan")
    vehicle_license_plate: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True, comment="Plat nomor kendaraan")
    previous_repaint: Mapped[str | None] = mapped_column(String(50), nullable=True,  comment="Riwayat repaint (belum pernah, sekali, lebih dari sekali)")
    bike_modified: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="Status modifikasi (Ya/Tidak)")
    vehicle_condition: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Kondisi kendaraan saat ini (goresan, retak, karat, dll)")

    # ============================================================
    # 3. PROJECT INFORMATION (dari form step 3)
    # ============================================================
    project_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="Tipe project (warna baru, restorasi total, dll)")
    services: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Layanan yang dipilih (full cat ulang, restorasi, repaint velk, dll)")
    desired_finish: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Finish yang diinginkan (Gloss, Matte, Satin, dll)")
    desired_color: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Warna yang diinginkan")
    estimated_budget: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Estimasi budget (dalam Rupiah)")
    deadline: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Target waktu pengerjaan")
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Prioritas utama (Kualitas Super, Cepat, Murah, Custom)")
    project_description: Mapped[str] = mapped_column(Text, nullable=False, comment="Deskripsi project secara detail")
    reference_link: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Link referensi (Instagram, Pinterest, dll)")

    # ============================================================
    # 4. FINANCIAL FIELDS
    # ============================================================
    deposit_required: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, comment="Deposit yang dibutuhkan")
    deposit_paid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=0, comment="Deposit yang sudah dibayar")
    total_paid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=0, comment="Total pembayaran")
    total_invoiced: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=0, comment="Total invoice")
    balance_due: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=0, comment="Sisa tagihan")

    # ============================================================
    # 5. CONVERSION TRACKING
    # ============================================================
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, comment="Conversion rate (%)")
    estimated_conversion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Estimasi tanggal konversi")

    # ============================================================
    # 6. STATUS & METADATA
    # ============================================================
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=InquiryStatus.NEW, index=True, comment="Status inquiry")
    note: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Catatan tambahan")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="IP address customer")
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="User agent browser")
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Sumber inquiry (website, WhatsApp, dll)")

    # ============================================================
    # 7. TIMESTAMP TRACKING
    # ============================================================
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Waktu contact customer")
    quoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Waktu kirim quotation")
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Waktu konversi ke project")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Waktu ditutup")
    closed_reason: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Alasan penutupan")

    # ============================================================
    # 8. RELATIONSHIPS
    # ============================================================
    # Project relationship (inquiry → project)
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="ID project yang terkonversi"
    )

    # Photos
    photos = relationship(
        "CustomerInquiryPhoto",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Workshop notes
    workshop_notes = relationship(
        "WorkshopNote",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Activities
    activities = relationship(
        "InquiryActivity",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        order_by="InquiryActivity.created_at.desc()",
        lazy="selectin"
    )

    # Project
    project = relationship(
        "Project",
        back_populates="inquiry",
        uselist=False,
        foreign_keys=[project_id],
        lazy="selectin"
    )

    # Payments
    payments = relationship(
        "InquiryPayment",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Invoices
    invoices = relationship(
        "InquiryInvoice",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Follow-ups
    follow_ups = relationship(
        "InquiryFollowUp",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # ============================================================
    # 9. CONSTRAINTS & INDEXES
    # ============================================================
    __table_args__ = (
        # Status validation
        CheckConstraint(
            "status IN ('new', 'under_review', 'contacted', 'quoted', 'approved', 'converted', 'rejected', 'closed', 'completed')",
            name="ck_inquiry_status_valid"
        ),
        # Conversion rate range
        CheckConstraint(
            "conversion_rate >= 0 AND conversion_rate <= 100",
            name="ck_inquiry_conversion_rate_range"
        ),
        # Phone number format (basic validation)
        # CheckConstraint(
        #     "customer_phone_number ~ '^(\+62|62|08)[0-9]{8,13}$'",
        #     name="ck_inquiry_phone_format"
        # ),

        # Indexes untuk performance
        Index("idx_inquiry_status_created", "status", "created_at"),
        Index("idx_inquiry_customer_phone", "customer_phone_number"),
        Index("idx_inquiry_vehicle_brand", "vehicle_brand"),
        Index("idx_inquiry_project_id", "project_id"),
        Index("idx_inquiry_source_created", "source", "created_at"),
        Index("idx_inquiry_phone_created",
              "customer_phone_number", "created_at"),
        Index("idx_inquiry_brand_created", "vehicle_brand", "created_at"),
        Index("idx_inquiry_deleted", "is_deleted"),  # Untuk soft delete
    )

    # ============================================================
    # 10. PROPERTIES & METHODS
    # ============================================================

    @property
    def is_converted(self) -> bool:
        """Check if inquiry has been converted to project."""
        return self.project is not None

    @property
    def full_name(self) -> str:
        """Get customer full name."""
        return self.customer_name

    @property
    def vehicle_info(self) -> str:
        """Get vehicle brand + model."""
        return f"{self.vehicle_brand} {self.vehicle_model}".strip()

    @property
    def display_name(self) -> str:
        """Display name for UI."""
        return f"{self.customer_name} - {self.vehicle_info}"

    def can_transition_to(self, new_status: str, workflow_map: Optional[Dict] = None) -> bool:
        """Check if status transition is allowed."""
        if workflow_map is None:
            transitions = {
                InquiryStatus.NEW: [InquiryStatus.UNDER_REVIEW, InquiryStatus.CONTACTED, InquiryStatus.REJECTED],
                InquiryStatus.UNDER_REVIEW: [InquiryStatus.CONTACTED, InquiryStatus.QUOTED, InquiryStatus.REJECTED],
                InquiryStatus.CONTACTED: [InquiryStatus.QUOTED, InquiryStatus.REJECTED],
                InquiryStatus.QUOTED: [InquiryStatus.APPROVED, InquiryStatus.REJECTED],
                InquiryStatus.APPROVED: [InquiryStatus.CONVERTED, InquiryStatus.REJECTED],
                InquiryStatus.CONVERTED: [InquiryStatus.COMPLETED, InquiryStatus.REJECTED],
                InquiryStatus.REJECTED: [InquiryStatus.CLOSED],
                InquiryStatus.CLOSED: [],
                InquiryStatus.COMPLETED: [],
            }
            return new_status in transitions.get(self.status, [])
        
        allowed = workflow_map.get(self.status, [])
        return new_status in allowed

    def get_allowed_transitions(self) -> List[str]:
        """Get list of allowed transitions from current status."""
        transitions = {
            InquiryStatus.NEW: [InquiryStatus.UNDER_REVIEW, InquiryStatus.CONTACTED, InquiryStatus.REJECTED],
            InquiryStatus.UNDER_REVIEW: [InquiryStatus.CONTACTED, InquiryStatus.QUOTED, InquiryStatus.REJECTED],
            InquiryStatus.CONTACTED: [InquiryStatus.QUOTED, InquiryStatus.REJECTED],
            InquiryStatus.QUOTED: [InquiryStatus.APPROVED, InquiryStatus.REJECTED],
            InquiryStatus.APPROVED: [InquiryStatus.CONVERTED, InquiryStatus.REJECTED],
            InquiryStatus.CONVERTED: [InquiryStatus.COMPLETED, InquiryStatus.REJECTED],
            InquiryStatus.REJECTED: [InquiryStatus.CLOSED],
            InquiryStatus.CLOSED: [],
            InquiryStatus.COMPLETED: [],
        }
        return transitions.get(self.status, [])

    def transition_to(self, new_status: str, note: Optional[str] = None):
        """
        Transition to new status with validation.
        Raises ValueError if transition not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from '{self.status}' to '{new_status}'. "
                f"Allowed transitions: {self.get_allowed_transitions()}"
            )

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now()

        # Track status change timestamps
        status_timestamps = {
            InquiryStatus.CONTACTED: "contacted_at",
            InquiryStatus.QUOTED: "quoted_at",
            InquiryStatus.CONVERTED: "converted_at",
            InquiryStatus.CLOSED: "closed_at",
        }
        if new_status in status_timestamps:
            setattr(self, status_timestamps[new_status], datetime.now())

        return old_status

    def __repr__(self):
        return f"<CustomerInquiry {self.id} - {self.customer_name} - {self.status}>"


# ============================================================
# CustomerInquiryPhoto Model
# ============================================================

class CustomerInquiryPhoto(Base, UUIDMixin, TimestampMixin):
    """Model untuk foto inquiry."""
    __tablename__ = "tb_customer_inquiry_photos"

    inquiry_id: Mapped[UUID] = mapped_column(ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID inquiry")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="Path file foto")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Nama file asli")
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Ukuran file (bytes)")
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="MIME type")
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="initial", comment="Stage foto (initial, progress, final)")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Urutan tampilan")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="Foto utama")

    # Relationship
    inquiry = relationship("CustomerInquiry", back_populates="photos")

    __table_args__ = (
        Index("idx_photo_inquiry_stage", "inquiry_id", "stage"),
        Index("idx_photo_inquiry_primary", "inquiry_id", "is_primary"),
        Index("idx_photo_inquiry_order", "inquiry_id", "sort_order"),
    )

    def __repr__(self):
        return f"<CustomerInquiryPhoto {self.id} - {self.file_name}>"


# ============================================================
# InquiryActivity Model
# ============================================================

class InquiryActivity(Base, UUIDMixin, TimestampMixin):
    """Model untuk aktivitas/audit trail inquiry."""
    __tablename__ = "tb_inquiry_activities"

    inquiry_id: Mapped[UUID] = mapped_column(ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"), nullable=False, index=True,  comment="ID inquiry")
    activity: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="Deskripsi aktivitas")
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Tipe aktivitas (creation, status_change, photo_upload, dll)")
    meta_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="Metadata tambahan (JSON)")
    performed_by: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Yang melakukan aktivitas")

    # Relationship
    inquiry = relationship("CustomerInquiry", back_populates="activities")

    __table_args__ = (
        Index("idx_activity_inquiry_type", "inquiry_id", "activity_type"),
        Index("idx_activity_created", "created_at"),
        Index("idx_activity_performed_by", "performed_by"),
    )

    def __repr__(self):
        return f"<InquiryActivity {self.id} - {self.activity}>"


# ============================================================
# WorkshopNote Model
# ============================================================

class WorkshopNote(Base, UUIDMixin, TimestampMixin):
    """Model untuk catatan workshop internal."""
    __tablename__ = "tb_workshop_notes"

    inquiry_id: Mapped[UUID] = mapped_column(ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID inquiry")
    note_type: Mapped[str] = mapped_column(String(50), nullable=False, default="internal", comment="Tipe catatan (internal, customer, rejection, dll)")
    note: Mapped[str] = mapped_column(Text, nullable=False, comment="Isi catatan")
    author: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Penulis catatan")
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="Catatan privat (hanya untuk internal)")

    # Relationship
    inquiry = relationship("CustomerInquiry", back_populates="workshop_notes")

    __table_args__ = (
        Index("idx_note_inquiry_type", "inquiry_id", "note_type"),
        Index("idx_note_inquiry_private", "inquiry_id", "is_private"),
        Index("idx_note_author", "author"),
    )

    def __repr__(self):
        return f"<WorkshopNote {self.id} - {self.note_type}>"


# ============================================================
# InquiryFollowUp Model
# ============================================================

class InquiryFollowUp(Base, UUIDMixin, TimestampMixin):
    """Model untuk follow-up schedule."""
    __tablename__ = "tb_inquiry_follow_ups"

    inquiry_id: Mapped[UUID] = mapped_column(ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID inquiry")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="Jadwal follow-up")
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Waktu follow-up dilakukan")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", comment="Status (pending, done, missed, cancelled)")
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Catatan follow-up")
    result: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Hasil follow-up")
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Ditugaskan ke")
    reminder_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="Reminder sudah dikirim")
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Waktu reminder dikirim")

    # Relationship
    inquiry = relationship("CustomerInquiry", back_populates="follow_ups")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'done', 'missed', 'cancelled')",
            name="ck_followup_status"
        ),
        Index("idx_followup_inquiry_status", "inquiry_id", "status"),
        Index("idx_followup_scheduled_at", "scheduled_at"),
        Index("idx_followup_assigned_to", "assigned_to"),
        Index("idx_followup_status_scheduled", "status", "scheduled_at"),
    )

    @property
    def is_overdue(self) -> bool:
        """Check if follow-up is overdue."""
        if self.status != "pending":
            return False
        return datetime.now() > self.scheduled_at

    @property
    def days_until_due(self) -> int | None:
        """Get days until due."""
        if self.status != "pending":
            return None
        delta = self.scheduled_at - datetime.now()
        return max(0, delta.days)

    def __repr__(self):
        return f"<InquiryFollowUp {self.id} - {self.inquiry_id} - {self.status}>"

