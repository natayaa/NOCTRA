from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin, UUIDMixin
from modules.customers.constants import CustomerStatus


class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_status_created", "status", "created_at"),
        Index("ix_customers_name", "name"),
    )

    # Human-readable: NOCTRA-C-2026-000123
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    # Primary contact
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    alt_phone: Mapped[str | None] = mapped_column(String(32))

    # Address
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    province: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(64), default="Indonesia", nullable=False)

    # Business metadata
    status: Mapped[str] = mapped_column(
        String(16), default=CustomerStatus.LEAD.value, nullable=False, index=True
    )
    tax_id: Mapped[str | None] = mapped_column(String(64))       # NPWP
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    contacts: Mapped[list["CustomerContact"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerContact.created_at.desc()",
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