from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.modules.customers.constants import CustomerStatus


class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_status_created", "status", "created_at"),
        Index("ix_customers_name", "name"),
        # Case-insensitive uniqueness on email, enforced by the DB so
        # concurrent inserts cannot both pass the application-level
        # pre-check in `create()` / `find_or_create()`. Service catches
        # IntegrityError and re-raises as ConflictError.
        Index(
            "uq_customers_email_lower",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
        # Partial unique on phone — non-null phones must be unique, but
        # multiple customers without a phone are allowed.
        Index(
            "uq_customers_phone",
            "phone",
            unique=True,
            postgresql_where=text("phone IS NOT NULL"),
        ),
    )

    # Human-readable: NOCTRA-C-2026-000123
    code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False
    )

    # Primary contact
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # `email`/`phone` are covered by uq_customers_email_lower /
    # uq_customers_phone — no standalone index needed.
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    alt_phone: Mapped[str | None] = mapped_column(String(32))

    # Address
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    province: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(
        String(64), default="Indonesia", server_default="Indonesia", nullable=False
    )

    # Business metadata
    status: Mapped[str] = mapped_column(
        String(16),
        default=CustomerStatus.LEAD.value,
        server_default=CustomerStatus.LEAD.value,
        nullable=False,
        # Covered by ix_customers_status_created (leftmost prefix).
    )
    tax_id: Mapped[str | None] = mapped_column(String(64))       # NPWP
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    contacts: Mapped[list["CustomerContact"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerContact.created_at.desc()",
        lazy="selectin",
    )


class CustomerContact(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customer_contacts"

    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    customer: Mapped[Customer] = relationship(back_populates="contacts")