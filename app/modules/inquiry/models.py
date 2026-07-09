# modules/inquiry/models.py
from decimal import Decimal
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Index, String, Text, ForeignKey, Integer, JSON,
    DateTime, func, Numeric, Boolean, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin
from core.constants import InquiryStatus


class CustomerInquiry(Base, UUIDMixin, TimestampMixin):
    """Model untuk customer inquiry."""
    __tablename__ = "tb_customer_inquiry"

    # ============ Customer Information ============
    customer_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    customer_phone_number: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    customer_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ============ Motorcycle Information ============
    vehicle_brand: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vehicle_license_plate: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    previous_repaint: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    bike_modified: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    vehicle_condition: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ============ Project Information ============
    project_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    services: Mapped[str | None] = mapped_column(Text, nullable=True)
    desired_finish: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    desired_color: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    estimated_budget: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    deadline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_link: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ============ Financial Fields ============
    deposit_required: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    deposit_paid: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=0
    )
    total_paid: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=0
    )
    total_invoiced: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=0
    )
    balance_due: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=0
    )

    # ============ Conversion Tracking ============
    conversion_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    estimated_conversion_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ============ Metadata ============
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=InquiryStatus.NEW, index=True
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ============ Tracking ============
    contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    quoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_reason: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # ============ Relationships ============
    photos = relationship(
        "CustomerInquiryPhoto",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    workshop_notes = relationship(
        "WorkshopNote",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    activities = relationship(
        "InquiryActivity",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        order_by="InquiryActivity.created_at.desc()",
        lazy="selectin"
    )
    project = relationship(
        "Project",
        back_populates="inquiry",
        uselist=False,
        lazy="selectin"
    )
    payments = relationship(
        "InquiryPayment",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    invoices = relationship(
        "InquiryInvoice",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    follow_ups = relationship(
        "InquiryFollowUp",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # ============ Constraints ============
    __table_args__ = (
        CheckConstraint(
            "conversion_rate >= 0 AND conversion_rate <= 100",
            name="ck_inquiry_conversion_rate_range"
        ),
        CheckConstraint(
            "status IN ('new', 'under_review', 'contacted', 'quoted', 'approved', 'converted', 'rejected', 'closed', 'completed')",
            name="ck_inquiry_status_valid"
        ),
        Index("idx_inquiry_customer_phone", "customer_phone_number"),
        Index("idx_inquiry_vehicle_brand", "vehicle_brand"),
        Index("idx_inquiry_status_created", "status", "created_at"),
    )

    def __repr__(self):
        return f"<CustomerInquiry {self.id} - {self.customer_name}>"

    @property
    def is_converted(self) -> bool:
        return self.project is not None

    @property
    def full_name(self) -> str:
        return self.customer_name

    @property
    def vehicle_info(self) -> str:
        return f"{self.vehicle_brand} {self.vehicle_model}"


class CustomerInquiryPhoto(Base, UUIDMixin, TimestampMixin):
    """Model untuk foto inquiry."""
    __tablename__ = "tb_customer_inquiry_photos"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="initial"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    inquiry = relationship("CustomerInquiry", back_populates="photos")

    __table_args__ = (
        Index("idx_photo_inquiry_stage", "inquiry_id", "stage"),
        Index("idx_photo_inquiry_primary", "inquiry_id", "is_primary"),
    )

    def __repr__(self):
        return f"<CustomerInquiryPhoto {self.id} - {self.file_name}>"


class InquiryActivity(Base, UUIDMixin, TimestampMixin):
    """Model untuk aktivitas inquiry."""
    __tablename__ = "tb_inquiry_activities"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    activity: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    activity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    meta_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    inquiry = relationship("CustomerInquiry", back_populates="activities")

    __table_args__ = (
        Index("idx_activity_inquiry_type", "inquiry_id", "activity_type"),
        Index("idx_activity_created", "created_at"),
    )

    def __repr__(self):
        return f"<InquiryActivity {self.id} - {self.activity}>"


class WorkshopNote(Base, UUIDMixin, TimestampMixin):
    """Model untuk catatan workshop."""
    __tablename__ = "tb_workshop_notes"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    note_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="internal"
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_private: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    inquiry = relationship("CustomerInquiry", back_populates="workshop_notes")

    __table_args__ = (
        Index("idx_note_inquiry_type", "inquiry_id", "note_type"),
        Index("idx_note_inquiry_private", "inquiry_id", "is_private"),
    )

    def __repr__(self):
        return f"<WorkshopNote {self.id} - {self.note_type}>"


class InquiryFollowUp(Base, UUIDMixin, TimestampMixin):
    """Follow-up inquiry."""
    __tablename__ = "tb_inquiry_follow_ups"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    performed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    inquiry = relationship("CustomerInquiry", back_populates="follow_ups")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'done', 'missed', 'cancelled')",
            name="ck_followup_status"
        ),
        Index("idx_followup_inquiry_status", "inquiry_id", "status"),
        Index("idx_followup_scheduled_at", "scheduled_at"),
        Index("idx_followup_assigned_to", "assigned_to"),
    )

    def __repr__(self):
        return f"<InquiryFollowUp {self.id} - {self.inquiry_id}>"

    @property
    def is_overdue(self) -> bool:
        if self.status != "pending":
            return False
        return datetime.now() > self.scheduled_at

    @property
    def days_until_due(self) -> int | None:
        if self.status != "pending":
            return None
        delta = self.scheduled_at - datetime.now()
        return max(0, delta.days)
