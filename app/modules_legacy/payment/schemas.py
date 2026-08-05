# modules/payment/schemas.py
"""
Payment Module Schemas - REFACTORED

✅ Request/Response schemas untuk Payment, Invoice, InvoiceItem
✅ Financial summary schemas
✅ Reconciliation, Reminder, PDF schemas
✅ Validasi dengan Pydantic field_validator
✅ price_list_item_id UNCOMMENTED
✅ InvoiceReminderRequest ADDED
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.constants import PaymentType, PaymentStatus, PaymentMethod, InvoiceStatus


# =============================================================================
# Payment Schemas
# =============================================================================

class PaymentCreate(BaseModel):
    """Schema untuk membuat payment."""
    inquiry_id: UUID = Field(..., description="ID inquiry")
    project_id: Optional[UUID] = Field(None, description="ID project (opsional)")
    invoice_id: Optional[UUID] = Field(None, description="ID invoice (opsional)")
    payment_type: str = Field(
        default=PaymentType.DEPOSIT,
        description="Jenis payment (deposit, payment, refund, installment)"
    )
    amount: Decimal = Field(..., gt=0, description="Jumlah pembayaran")
    payment_method: str = Field(..., description="Metode pembayaran")
    reference_number: Optional[str] = Field(None, max_length=100, description="Nomor referensi")
    notes: Optional[str] = Field(None, description="Catatan")
    paid_at: Optional[datetime] = Field(None, description="Tanggal pembayaran")
    due_date: Optional[datetime] = Field(None, description="Tanggal jatuh tempo")
    payment_proof: Optional[str] = Field(None, max_length=500, description="Bukti pembayaran")

    @field_validator("payment_type")
    @classmethod
    def validate_payment_type(cls, v: str) -> str:
        valid_types = [e.value for e in PaymentType]
        if v not in valid_types:
            raise ValueError(f"Payment type must be one of: {valid_types}")
        return v

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        valid_methods = [e.value for e in PaymentMethod]
        if v not in valid_methods:
            raise ValueError(f"Payment method must be one of: {valid_methods}")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class PaymentUpdate(BaseModel):
    """Schema untuk update payment."""
    status: Optional[str] = Field(None, description="Status pembayaran")
    notes: Optional[str] = Field(None, description="Catatan")
    reference_number: Optional[str] = Field(None, max_length=100, description="Nomor referensi")
    payment_proof: Optional[str] = Field(None, max_length=500, description="Bukti pembayaran")
    confirmed_by: Optional[str] = Field(None, max_length=100, description="Dikonfirmasi oleh")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v:
            valid_statuses = [e.value for e in PaymentStatus]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class PaymentResponse(BaseModel):
    """Response untuk payment."""
    id: UUID
    inquiry_id: UUID
    project_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    project_name: Optional[str] = None
    inquiry_vehicle: Optional[str] = None
    customer_name: Optional[str] = None  # ✅ TAMBAHKAN
    payment_type: str
    amount: Decimal
    payment_method: str
    reference_number: Optional[str] = None
    status: str
    notes: Optional[str] = None
    paid_at: datetime
    due_date: Optional[datetime] = None
    payment_proof: Optional[str] = None
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepositCreate(BaseModel):
    """Schema untuk membuat deposit."""
    inquiry_id: UUID = Field(..., description="ID inquiry")
    project_id: Optional[UUID] = Field(None, description="ID project (opsional)")
    amount: Decimal = Field(..., gt=0, description="Jumlah deposit")
    payment_method: str = Field(..., description="Metode pembayaran")
    reference_number: Optional[str] = Field(None, max_length=100, description="Nomor referensi")
    notes: Optional[str] = Field(None, description="Catatan")

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        valid_methods = [e.value for e in PaymentMethod]
        if v not in valid_methods:
            raise ValueError(f"Payment method must be one of: {valid_methods}")
        return v


# =============================================================================
# Invoice Item Schemas
# =============================================================================

class InvoiceItemCreate(BaseModel):
    """Schema untuk membuat invoice item."""
    description: str = Field(..., description="Deskripsi item")
    quantity: Decimal = Field(default=1, gt=0, description="Jumlah")
    unit: Optional[str] = Field(None, max_length=20, description="Satuan")
    unit_price: Decimal = Field(..., gt=0, description="Harga per unit")
    tax_rate: Decimal = Field(default=0, ge=0, le=100, description="Rate pajak (%)")
    discount_percentage: Decimal = Field(default=0, ge=0, le=100, description="Diskon (%)")
    notes: Optional[str] = Field(None, description="Catatan")
    sort_order: int = Field(default=0, description="Urutan")
    price_list_item_id: Optional[UUID] = Field(None, description="ID price list item")  # ✅ UNCOMMENT

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Unit price cannot be negative")
        return v


class InvoiceItemResponse(BaseModel):
    """Response untuk invoice item."""
    id: UUID
    invoice_id: UUID
    description: str
    quantity: Decimal
    unit: Optional[str] = None
    unit_price: Decimal
    total_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_percentage: Decimal
    discount_amount: Decimal
    final_price: Decimal  # ✅ TAMBAHKAN
    notes: Optional[str] = None
    sort_order: int
    price_list_item_id: Optional[UUID] = None
    price_list_item_name: Optional[str] = None  # ✅ TAMBAHKAN
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Invoice Schemas
# =============================================================================

class InvoiceCreate(BaseModel):
    """Schema untuk membuat invoice."""
    inquiry_id: UUID = Field(..., description="ID inquiry")
    project_id: Optional[UUID] = Field(None, description="ID project (opsional)")
    invoice_number: str = Field(..., max_length=50, description="Nomor invoice")
    invoice_date: Optional[datetime] = Field(None, description="Tanggal invoice")
    due_date: Optional[datetime] = Field(None, description="Tanggal jatuh tempo")
    payment_terms: Optional[str] = Field(None, max_length=255, description="Syarat pembayaran")
    notes: Optional[str] = Field(None, description="Catatan")
    items: List[InvoiceItemCreate] = Field(..., min_length=1, description="Item invoice")

    @field_validator("invoice_number")
    @classmethod
    def validate_invoice_number(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Invoice number cannot be empty")
        return v.strip().upper()

    @model_validator(mode="after")
    def validate_dates(self) -> "InvoiceCreate":
        if self.invoice_date and self.due_date:
            if self.due_date < self.invoice_date:
                raise ValueError("Due date cannot be before invoice date")
        return self


class InvoiceUpdate(BaseModel):
    """Schema untuk update invoice."""
    status: Optional[str] = Field(None, description="Status invoice")
    due_date: Optional[datetime] = Field(None, description="Tanggal jatuh tempo")
    notes: Optional[str] = Field(None, description="Catatan")
    file_path: Optional[str] = Field(None, max_length=500, description="Path file")
    payment_terms: Optional[str] = Field(None, max_length=255, description="Syarat pembayaran")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v:
            valid_statuses = [e.value for e in InvoiceStatus]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class InvoiceResponse(BaseModel):
    """Response untuk invoice."""
    id: UUID
    inquiry_id: UUID
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    customer_name: Optional[str] = None  # ✅ TAMBAHKAN
    vehicle_info: Optional[str] = None  # ✅ TAMBAHKAN
    invoice_number: str
    invoice_date: datetime
    due_date: Optional[datetime] = None
    subtotal_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    status: str
    notes: Optional[str] = None
    file_path: Optional[str] = None
    payment_terms: Optional[str] = None
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    reminder_sent_at: Optional[datetime] = None
    reminder_count: int = 0
    is_overdue: bool = False
    is_paid: bool = False  # ✅ TAMBAHKAN
    payment_progress: float = 0.0  # ✅ TAMBAHKAN
    items: List[InvoiceItemResponse] = Field(default_factory=list)
    payments: List[PaymentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceMarkPaid(BaseModel):
    """Schema untuk menandai invoice sebagai lunas."""
    payment_method: str = Field(..., description="Metode pembayaran")
    reference_number: Optional[str] = Field(None, max_length=100, description="Nomor referensi")
    notes: Optional[str] = Field(None, description="Catatan")

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        valid_methods = [e.value for e in PaymentMethod]
        if v not in valid_methods:
            raise ValueError(f"Payment method must be one of: {valid_methods}")
        return v


class InvoiceSendReminder(BaseModel):
    """Schema untuk mengirim reminder invoice."""
    note: Optional[str] = Field(None, description="Catatan tambahan untuk reminder")
    sent_via: str = Field(default="email", description="email, whatsapp, sms")

    @field_validator("sent_via")
    @classmethod
    def validate_sent_via(cls, v: str) -> str:
        valid_via = ["email", "whatsapp", "sms"]
        if v not in valid_via:
            raise ValueError(f"sent_via must be one of: {valid_via}")
        return v


# =============================================================================
# Invoice Reminder Request (ADDED)
# =============================================================================

class InvoiceReminderRequest(BaseModel):
    """Request untuk mengirim reminder invoice."""
    note: Optional[str] = Field(None, description="Catatan tambahan untuk reminder")
    sent_via: str = Field(default="email", description="email, whatsapp, sms")

    @field_validator("sent_via")
    @classmethod
    def validate_sent_via(cls, v: str) -> str:
        valid_via = ["email", "whatsapp", "sms"]
        if v not in valid_via:
            raise ValueError(f"sent_via must be one of: {valid_via}")
        return v


# =============================================================================
# Financial Summary Schemas
# =============================================================================

class PaymentStatisticsResponse(BaseModel):
    """Response untuk statistik payment."""
    total_payments: int
    total_amount: float
    by_type: Dict[str, Dict[str, Any]]
    by_status: Dict[str, Dict[str, Any]]
    by_method: Dict[str, Dict[str, Any]]


class InvoiceSummaryResponse(BaseModel):
    """Response untuk summary invoice."""
    total_invoices: int
    total_amount: float
    unpaid_amount: float
    by_status: Dict[str, Dict[str, Any]]


class InquiryFinancialSummaryResponse(BaseModel):
    """Response untuk financial summary inquiry."""
    inquiry_id: UUID
    customer_name: str
    vehicle_info: str

    # Budget & Cost
    estimated_budget: float = 0.0
    total_cost: float = 0.0

    # Payments
    total_deposit: float = 0.0
    total_paid: float = 0.0
    total_pending: float = 0.0
    remaining_payment: float = 0.0

    # Status
    deposit_paid: bool = False
    is_paid_off: bool = False
    has_invoices: bool = False

    # History
    payments: List[PaymentResponse] = Field(default_factory=list)
    invoices: List[InvoiceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Payment Reconciliation Schemas
# =============================================================================

class PaymentReconciliationCreate(BaseModel):
    """Schema untuk membuat reconciliation."""
    bank_name: str = Field(..., max_length=100, description="Nama bank")
    bank_account: str = Field(..., max_length=50, description="Nomor rekening")
    reference_number: str = Field(..., max_length=100, description="Nomor referensi")
    reconciled_at: datetime = Field(..., description="Tanggal rekonsiliasi")
    reconciled_by: str = Field(..., max_length=100, description="Direkonsiliasi oleh")
    notes: Optional[str] = Field(None, description="Catatan")


class PaymentReconciliationUpdate(BaseModel):
    """Schema untuk update reconciliation."""
    status: Optional[str] = Field(None, description="Status (pending, matched, unmatched)")
    notes: Optional[str] = Field(None, description="Catatan")


class PaymentReconciliationResponse(BaseModel):
    """Response untuk reconciliation."""
    id: UUID
    payment_id: UUID
    bank_name: str
    bank_account: str
    reference_number: str
    reconciled_at: datetime
    reconciled_by: str
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Invoice PDF Schemas
# =============================================================================

class InvoicePDFResponse(BaseModel):
    """Response untuk invoice PDF."""
    id: UUID
    invoice_id: UUID
    file_path: str
    file_name: str
    generated_at: datetime
    generated_by: Optional[str] = None
    version: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Payment Reminder Schemas
# =============================================================================

class PaymentReminderCreate(BaseModel):
    """Schema untuk membuat reminder."""
    invoice_id: UUID = Field(..., description="ID invoice")
    reminder_type: str = Field(default="auto", description="auto, manual")
    sent_via: str = Field(..., description="email, whatsapp, sms")
    recipient: str = Field(..., max_length=255, description="Penerima")
    subject: Optional[str] = Field(None, max_length=255, description="Subjek")
    message: Optional[str] = Field(None, description="Pesan")

    @field_validator("reminder_type")
    @classmethod
    def validate_reminder_type(cls, v: str) -> str:
        valid_types = ["auto", "manual"]
        if v not in valid_types:
            raise ValueError(f"reminder_type must be one of: {valid_types}")
        return v


class PaymentReminderResponse(BaseModel):
    """Response untuk reminder."""
    id: UUID
    invoice_id: UUID
    reminder_type: str
    sent_at: datetime
    sent_via: str
    recipient: str
    subject: Optional[str] = None
    message: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Project Financial Summary (ADDED)
# =============================================================================

class ProjectPaymentSummaryResponse(BaseModel):
    """Response untuk financial summary project."""
    project_id: UUID
    project_name: str
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    total_deposit: float = 0.0
    total_paid: float = 0.0
    remaining: float = 0.0
    is_paid_off: bool = False
    payment_count: int = 0


# =============================================================================
# DEPRECATED / ALIAS (untuk backward compatibility)
# =============================================================================

# InvoiceSendReminder sudah ada, tambahkan alias jika perlu
# InvoiceReminderRequest = InvoiceSendReminder  # optional


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Payment
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
    "DepositCreate",
    
    # Invoice
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoiceResponse",
    "InvoiceMarkPaid",
    "InvoiceSendReminder",
    "InvoiceReminderRequest",  # ✅ ADDED
    
    # Invoice Items
    "InvoiceItemCreate",
    "InvoiceItemResponse",
    
    # Reconciliation
    "PaymentReconciliationCreate",
    "PaymentReconciliationUpdate",
    "PaymentReconciliationResponse",
    
    # Reminder
    "PaymentReminderCreate",
    "PaymentReminderResponse",
    
    # PDF
    "InvoicePDFResponse",
    
    # Financial Summary
    "PaymentStatisticsResponse",
    "InvoiceSummaryResponse",
    "InquiryFinancialSummaryResponse",
    "ProjectPaymentSummaryResponse",  # ✅ ADDED
]