"""Inquiry and inquiry-photo models.

The inquiry captures the customer's request with a mix of fixed
columns (for things we filter/price) and a JSONB `preferences` blob
(for the long tail).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.modules.inquiries.constants import InquiryStatus


class Inquiry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inquiries"
    __table_args__ = (
        Index("ix_inquiries_status_created", "status", "created_at"),
        Index("ix_inquiries_assigned_status", "assigned_to_id", "status"),
        Index("ix_inquiries_customer_created", "customer_id", "created_at"),
        Index("ix_inquiries_color_family", "color_family"),
        Index("ix_inquiries_finish_preference", "finish_preference"),
    )

    # ── Identity ────────────────────────────────────────
    code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )

    # ── Relationships (nullable; sales may fill in later) ─
    customer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        index=True,
    )
    vehicle_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        index=True,
    )

    # ── What they want, in their own words ─────────────
    service_interest: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Customer request — fixed fields ────────────────
    color_preference: Mapped[str | None] = mapped_column(String(64))
    color_family: Mapped[str | None] = mapped_column(String(16))
    finish_preference: Mapped[str | None] = mapped_column(String(16))
    has_custom_graphics: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    # ── Customer request — flexible extras ─────────────
    preferences: Mapped[dict | None] = mapped_column(JSONB)

    # ── Workflow ────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(16),
        default=InquiryStatus.NEW.value,
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(32), default="ADMIN", nullable=False
    )
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # ── Follow-up tracking ──────────────────────────────
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    follow_up_date: Mapped[date | None] = mapped_column(Date)

    # ── Intake metadata ─────────────────────────────────
    budget_range: Mapped[str | None] = mapped_column(String(32))
    desired_date: Mapped[date | None] = mapped_column(Date)

    # ── Free-form staff notes + closing reason ─────────
    notes: Mapped[str | None] = mapped_column(Text)
    closing_note: Mapped[str | None] = mapped_column(Text)

    # ── Relationship to photos ─────────────────────────
    photos: Mapped[list["InquiryPhoto"]] = relationship(
        back_populates="inquiry",
        cascade="all, delete-orphan",
        order_by="InquiryPhoto.created_at.desc()",
        lazy="selectin",   
    )

    def __repr__(self) -> str:
        return f"<Inquiry {self.code} {self.status}>"


class InquiryPhoto(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inquiry_photos"
    __table_args__ = (
        Index("ix_inquiry_photos_inquiry_created", "inquiry_id", "created_at"),
    )

    inquiry_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("inquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    caption: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    inquiry: Mapped[Inquiry] = relationship(back_populates="photos")