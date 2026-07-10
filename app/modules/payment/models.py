# modules/payment/models.py
"""
Payment Module Models
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import (
    String, Numeric, Text, ForeignKey, DateTime,
    func, JSON, Boolean, Integer, CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin
from core.constants import PaymentType, PaymentStatus, PaymentMethod, InvoiceStatus


class InquiryPayment(Base, UUIDMixin, TimestampMixin):
    """
    Model untuk pembayaran yang terhubung ke inquiry.
    """
    __tablename__ = "tb_inquiry_payments"

    # =========================================================================
    # Foreign Keys
    # =========================================================================
    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    invoice_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_inquiry_invoices.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # =========================================================================
    # Payment Information
    # =========================================================================
    payment_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentType.DEPOSIT, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PENDING, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # =========================================================================
    # Additional / Verification
    # =========================================================================
    payment_proof: Mapped[str | None] = mapped_column(
        String(500), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # =========================================================================
    # Relationships
    # =========================================================================
    inquiry = relationship(
        "CustomerInquiry", back_populates="payments", lazy="selectin")
    project = relationship(
        "Project", back_populates="payments", lazy="selectin", foreign_keys="[InquiryPayment.project_id]")
    invoice = relationship(
        "InquiryInvoice", back_populates="payments", lazy="selectin")
    reconciliation = relationship(
        "PaymentReconciliation", back_populates="payment", uselist=False, lazy="selectin")

    # =========================================================================
    # Constraints
    # =========================================================================
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        Index("idx_inquiry_payments_inquiry_status", "inquiry_id", "status"),
        Index("idx_inquiry_payments_paid_at", "paid_at"),
        Index("idx_inquiry_payments_reference", "reference_number"),
    )

    def __repr__(self) -> str:
        return f"<InquiryPayment {self.id} - {self.payment_type} - Rp {self.amount:,.2f} - {self.status}>"


class InquiryInvoice(Base, UUIDMixin, TimestampMixin):
    """
    Model untuk invoice customer yang terhubung ke inquiry.
    """
    __tablename__ = "tb_inquiry_invoices"

    # =========================================================================
    # Foreign Keys
    # =========================================================================
    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # =========================================================================
    # Invoice Identification
    # =========================================================================
    invoice_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    invoice_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # =========================================================================
    # Financial
    # =========================================================================
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)

    # =========================================================================
    # Status & Metadata
    # =========================================================================
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InvoiceStatus.DRAFT, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(
        String(255), nullable=True)

    # =========================================================================
    # Tracking
    # =========================================================================
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    reminder_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)

    # =========================================================================
    # Relationships
    # =========================================================================
    inquiry = relationship(
        "CustomerInquiry", back_populates="invoices", lazy="selectin")
    project = relationship(
        "Project", back_populates="invoices", lazy="selectin", foreign_keys="[InquiryInvoice.project_id]")
    items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InvoiceItem.sort_order"
    )
    payments = relationship(
        "InquiryPayment",
        back_populates="invoice",
        lazy="selectin"
    )
    reminders = relationship(
        "PaymentReminder",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    pdfs = relationship(
        "InvoicePDF",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # =========================================================================
    # Constraints
    # =========================================================================
    __table_args__ = (
        CheckConstraint("total_amount >= 0",
                        name="ck_invoice_total_amount_non_negative"),
        CheckConstraint("paid_amount >= 0",
                        name="ck_invoice_paid_amount_non_negative"),
        CheckConstraint("paid_amount <= total_amount",
                        name="ck_invoice_paid_amount_not_exceed_total"),
        Index("idx_inquiry_invoices_inquiry_status", "inquiry_id", "status"),
        Index("idx_inquiry_invoices_due_date", "due_date"),
        Index("idx_inquiry_invoices_number", "invoice_number"),
    )

    def __repr__(self) -> str:
        return f"<InquiryInvoice {self.id} - {self.invoice_number} - Rp {self.total_amount:,.2f} - {self.status}>"

    @property
    def remaining_amount(self) -> Decimal:
        return self.total_amount - self.paid_amount

    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        # ✅ FIX: Gunakan timezone-aware untuk comparison
        now = datetime.now(timezone.utc)
        # ✅ Pastikan due_date juga timezone-aware
        if self.due_date.tzinfo is None:
            # Jika naive, asumsikan UTC
            due_date = self.due_date.replace(tzinfo=timezone.utc)
        else:
            due_date = self.due_date
        return now > due_date and self.status != InvoiceStatus.PAID

    @property
    def is_paid(self) -> bool:
        return self.paid_amount >= self.total_amount

    @property
    def payment_progress(self) -> float:
        if self.total_amount == 0:
            return 0
        return float((self.paid_amount / self.total_amount) * 100)


class InvoiceItem(Base, UUIDMixin, TimestampMixin):
    """
    Model untuk item dalam invoice.
    """
    __tablename__ = "tb_invoice_items"

    # =========================================================================
    # Foreign Keys
    # =========================================================================
    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inquiry_invoices.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    price_list_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_price_list.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # =========================================================================
    # Item Information
    # =========================================================================
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=1)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False)

    # =========================================================================
    # Tax & Discount
    # =========================================================================
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)

    # =========================================================================
    # Additional
    # =========================================================================
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # =========================================================================
    # Relationships
    # =========================================================================
    invoice = relationship("InquiryInvoice", back_populates="items")
    price_list_item = relationship(
        "PriceListItem", back_populates="invoice_items")

    # =========================================================================
    # Constraints
    # =========================================================================
    __table_args__ = (
        CheckConstraint(
            "quantity > 0", name="ck_invoice_item_quantity_positive"),
        CheckConstraint("unit_price >= 0",
                        name="ck_invoice_item_unit_price_non_negative"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100",
                        name="ck_invoice_item_tax_rate_range"),
        CheckConstraint("discount_percentage >= 0 AND discount_percentage <= 100",
                        name="ck_invoice_item_discount_range"),
        Index("idx_invoice_items_invoice_sort", "invoice_id", "sort_order"),
        Index("idx_invoice_items_price_list", "price_list_item_id"),
    )

    def __repr__(self) -> str:
        return f"<InvoiceItem {self.id} - {self.description[:30]} - {self.quantity} x {self.unit_price} - Rp {self.total_price:,.2f}>"

    @property
    def final_price(self) -> Decimal:
        return self.total_price + self.tax_amount - self.discount_amount


class PaymentReconciliation(Base, UUIDMixin, TimestampMixin):
    """Reconciliation payment."""
    __tablename__ = "tb_payment_reconciliations"

    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inquiry_payments.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_account: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=False)
    reconciled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    reconciled_by: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    payment = relationship("InquiryPayment", back_populates="reconciliation")

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'matched', 'unmatched')",
                        name="ck_reconciliation_status"),
        Index("idx_reconciliation_payment", "payment_id"),
        Index("idx_reconciliation_reference", "reference_number"),
        Index("idx_reconciliation_bank", "bank_name", "bank_account"),
    )

    def __repr__(self):
        return f"<PaymentReconciliation {self.id} - {self.payment_id} - {self.status}>"


class PaymentReminder(Base, UUIDMixin, TimestampMixin):
    """Payment reminder."""
    __tablename__ = "tb_payment_reminders"

    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inquiry_invoices.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    reminder_type: Mapped[str] = mapped_column(
        String(50), nullable=False)  # auto, manual
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    sent_via: Mapped[str] = mapped_column(
        String(50), nullable=False)  # email, whatsapp, sms
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        # sent, failed, delivered, read
        String(50), nullable=False, default="sent")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    invoice = relationship("InquiryInvoice", back_populates="reminders")

    __table_args__ = (
        CheckConstraint("reminder_type IN ('auto', 'manual')",
                        name="ck_reminder_type"),
        CheckConstraint("sent_via IN ('email', 'whatsapp', 'sms')",
                        name="ck_reminder_via"),
        CheckConstraint(
            "status IN ('sent', 'failed', 'delivered', 'read')", name="ck_reminder_status"),
        Index("idx_payment_reminders_invoice", "invoice_id"),
        Index("idx_payment_reminders_sent_at", "sent_at"),
    )

    def __repr__(self):
        return f"<PaymentReminder {self.id} - {self.invoice_id}>"


class InvoicePDF(Base, UUIDMixin, TimestampMixin):
    """PDF invoice."""
    __tablename__ = "tb_invoice_pdfs"

    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inquiry_invoices.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    generated_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    invoice = relationship("InquiryInvoice", back_populates="pdfs")

    __table_args__ = (
        Index("idx_invoice_pdfs_invoice", "invoice_id"),
        Index("idx_invoice_pdfs_generated_at", "generated_at"),
    )

    def __repr__(self):
        return f"<InvoicePDF {self.id} - {self.invoice_id} - v{self.version}>"
