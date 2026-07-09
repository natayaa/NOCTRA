# models/payments.py
from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from uuid import UUID

from sqlalchemy import String, Numeric, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, UUIDMixin, TimestampMixin
from schemas.constants import PaymentStatus, PaymentMethod, PaymentType


class InquiryPayment(Base, UUIDMixin, TimestampMixin):
    """
    Model untuk pembayaran yang terhubung ke inquiry.
    Bisa berupa deposit, installment, atau full payment.
    """
    __tablename__ = "tb_inquiry_payments"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentType.DEPOSIT,
        index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    inquiry = relationship("CustomerInquiry", back_populates="payments")
    project = relationship("Project", back_populates="inquiry_payments")

    def __repr__(self):
        return f"<InquiryPayment {self.id} - {self.payment_type} - {self.amount}>"


class InquiryFinancialHistory(Base, UUIDMixin, TimestampMixin):
    """
    Model untuk tracking perubahan financial inquiry/project.
    """
    __tablename__ = "tb_inquiry_financial_history"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    inquiry = relationship("CustomerInquiry", back_populates="financial_history")

    def __repr__(self):
        return f"<InquiryFinancialHistory {self.id} - {self.field_name}>"


class InquiryInvoice(Base, UUIDMixin, TimestampMixin):
    """
    Model untuk invoice customer yang terhubung ke inquiry.
    """
    __tablename__ = "tb_inquiry_invoices"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True
    )
    invoice_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    inquiry = relationship("CustomerInquiry", back_populates="invoices")
    project = relationship("Project", back_populates="inquiry_invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<InquiryInvoice {self.id} - {self.invoice_number}>"


class InvoiceItem(Base, UUIDMixin, TimestampMixin):
    """
    Model untuk item dalam invoice.
    """
    __tablename__ = "tb_invoice_items"

    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inquiry_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice = relationship("InquiryInvoice", back_populates="items")

    def __repr__(self):
        return f"<InvoiceItem {self.id} - {self.description[:30]}>"