# models/customer_inquiry.py
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Integer, JSON, DateTime, func, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, UUIDMixin, TimestampMixin, UUID
from schemas.constants import InquiryStatus


class CustomerInquiry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_customer_inquiry"

    # ============ STEP 1: Customer Information ============
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ============ STEP 2: Motorcycle Information ============
    vehicle_brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vehicle_license_plate: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    previous_repaint: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bike_modified: Mapped[str | None] = mapped_column(String(10), nullable=True)
    vehicle_condition: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ============ STEP 3: Project Information ============
    project_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    services: Mapped[str | None] = mapped_column(Text, nullable=True)
    desired_finish: Mapped[str | None] = mapped_column(String(50), nullable=True)
    desired_color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estimated_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # ============ Metadata ============
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=InquiryStatus.NEW,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Tracking
    contacted_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    quoted_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    converted_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    
    # ============ Financial Fields ============
    estimated_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deposit_required: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    deposit_paid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=0)
    total_paid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=0)

    # ============ Relationships ============
    payments = relationship("InquiryPayment", back_populates="inquiry", cascade="all, delete-orphan")
    financial_history = relationship("InquiryFinancialHistory", back_populates="inquiry", cascade="all, delete-orphan")
    invoices = relationship("InquiryInvoice", back_populates="inquiry", cascade="all, delete-orphan")

    # ============ Relationships ============
    photos = relationship(
        "CustomerInquiryPhoto",
        back_populates="inquiry",
        cascade="all, delete-orphan",
    )

    workshop_notes = relationship(
        "WorkshopNote",
        back_populates="inquiry",
        cascade="all, delete-orphan",
    )

    activities = relationship(
        "InquiryActivity",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        order_by="InquiryActivity.created_at.desc()",
    )
    
    project = relationship(
        "Project",
        back_populates="inquiry",
        uselist=False,
    )
    
    payments = relationship(
        "InquiryPayment",
        back_populates="inquiry",
        cascade="all, delete-orphan",
    )
    
    financial_history = relationship(
        "InquiryFinancialHistory",
        back_populates="inquiry",
        cascade="all, delete-orphan",
    )
    
    invoices = relationship(
        "InquiryInvoice",
        back_populates="inquiry",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<CustomerInquiry {self.id} - {self.customer_name} - {self.vehicle_brand} {self.vehicle_model}>"


class CustomerInquiryPhoto(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_customer_inquiry_photos"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="initial")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    inquiry = relationship("CustomerInquiry", back_populates="photos")

    def __repr__(self):
        return f"<CustomerInquiryPhoto {self.id} - {self.file_name}>"


class InquiryActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inquiry_activities"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    inquiry = relationship("CustomerInquiry", back_populates="activities")

    def __repr__(self):
        return f"<InquiryActivity {self.id} - {self.activity}>"


class WorkshopNote(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_workshop_notes"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note_type: Mapped[str] = mapped_column(String(50), nullable=False, default="internal")
    note: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_private: Mapped[bool] = mapped_column(nullable=False, default=False)

    inquiry = relationship("CustomerInquiry", back_populates="workshop_notes")

    def __repr__(self):
        return f"<WorkshopNote {self.id} - {self.note_type}>"