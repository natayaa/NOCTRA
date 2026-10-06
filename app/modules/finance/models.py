"""Finance models: accounts, invoices, payments, expenses."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.modules.finance.constants import (
    InvoiceStatus,
    PaymentDirection,
)


# ════════════════════════════════════════════════════════════════
# CHART OF ACCOUNTS
# ════════════════════════════════════════════════════════════════

class Account(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_type_code", "account_type", "code"),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default="true",
    )

    def __repr__(self) -> str:
        return f"<Account {self.code} {self.name}>"


# ════════════════════════════════════════════════════════════════
# INVOICES — bills sent to customers
# ════════════════════════════════════════════════════════════════

class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_status_issue", "status", "issue_date"),
        Index("ix_invoices_customer", "customer_id"),
        Index("ix_invoices_project", "project_id"),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)

    # Money (IDR)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False, server_default="0")
    discount_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False, server_default="0")
    tax_rate_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False, server_default="0")
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False, server_default="0")
    total: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False, server_default="0")

    status: Mapped[str] = mapped_column(
        String(20),
        default=InvoiceStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(Text)
    terms: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceItem.created_at",
        lazy="selectin",  
    )

    def __repr__(self) -> str:
        return f"<Invoice {self.code} {self.status} total={self.total}>"


class InvoiceItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoice_items"
    __table_args__ = (Index("ix_invoice_items_invoice", "invoice_id"),)

    invoice_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), default=1, nullable=False, server_default="1")
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False, server_default="0")
    amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False, server_default="0")

    invoice: Mapped[Invoice] = relationship(back_populates="items")


# ════════════════════════════════════════════════════════════════
# PAYMENTS — every money movement (in or out)
# ════════════════════════════════════════════════════════════════

class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_direction_date", "direction", "payment_date"),
        Index("ix_payments_reference", "reference_type", "reference_id"),
        Index("ix_payments_customer", "customer_id"),
        Index("ix_payments_supplier", "supplier_id"),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    direction: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Optional link to who paid / who was paid
    customer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
    )

    # Reference to what this payment is against
    reference_type: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    # Which account the money moved through
    account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
    )

    reference_number: Mapped[str | None] = mapped_column(String(100))  # bank ref
    notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    def __repr__(self) -> str:
        return f"<Payment {self.code} {self.direction} {self.amount}>"


# ════════════════════════════════════════════════════════════════
# EXPENSES — operational spending
# ════════════════════════════════════════════════════════════════

class Expense(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_category_date", "category", "expense_date"),
        Index("ix_expenses_date", "expense_date"),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Optional: link to an account for reporting
    account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
    )

    # Optional: link to a payment if it was paid via the payments flow
    payment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
    )

    reference_number: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    def __repr__(self) -> str:
        return f"<Expense {self.code} {self.category} {self.amount}>"