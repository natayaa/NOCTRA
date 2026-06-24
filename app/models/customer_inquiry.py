from sqlalchemy import String, Text, ForeignKey, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, UUIDMixin, TimestampMixin, UUID
from schemas.constants import InquiryStatus


class CustomerInquiry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_customer_inquiry"

    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vehicle_brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_license_plate: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    vehicle_condition: Mapped[str] = mapped_column(String(255), nullable=False)
    project_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    project_description: Mapped[str] = mapped_column(Text, nullable=False)
    project_target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=InquiryStatus.NEW,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # relationships
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


class CustomerInquiryPhoto(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_customer_inquiry_photos"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)

    inquiry = relationship("CustomerInquiry", back_populates="photos")


class InquiryActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inquiry_activities"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    inquiry = relationship("CustomerInquiry", back_populates="activities")


class WorkshopNote(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_workshop_notes"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note_type: Mapped[str] = mapped_column(String(50), nullable=False, default="internal")
    note: Mapped[str] = mapped_column(Text, nullable=False)

    inquiry = relationship("CustomerInquiry", back_populates="workshop_notes")