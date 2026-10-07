"""Pydantic schemas for the finance module."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.finance.constants import (
    ACCOUNT_TYPES,
    EXPENSE_CATEGORIES,
    INVOICE_STATUSES,
    PAYMENT_DIRECTIONS,
    PAYMENT_METHODS,
    PAYMENT_REFERENCE_TYPES,
)


_EMPTY = {"", "none", "null", "undefined", "nil"}


def _clean_optional(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in _EMPTY:
        return None
    return s


# ════════════════════════════════════════════════════════════════
# ACCOUNTS
# ════════════════════════════════════════════════════════════════

class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    account_type: str
    parent_id: UUID | None
    description: str | None
    is_active: bool


# ════════════════════════════════════════════════════════════════
# INVOICES
# ════════════════════════════════════════════════════════════════

class InvoiceItemIn(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: float = Field(1, gt=0)
    unit_price: float = Field(0, ge=0)


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    description: str
    quantity: float
    unit_price: float
    amount: float


class InvoiceCreate(BaseModel):
    customer_id: UUID
    project_id: UUID | None = None
    issue_date: date
    due_date: date | None = None

    discount_amount: float = Field(0, ge=0)
    tax_rate_pct: float = Field(0, ge=0, lt=100)

    notes: str | None = None
    terms: str | None = None
    items: list[InvoiceItemIn] = Field(default_factory=list)


class InvoiceFromProject(BaseModel):
    """Auto-generate an invoice from an approved project."""
    project_id: UUID
    issue_date: date | None = None
    due_date: date | None = None
    tax_rate_pct: float = Field(0, ge=0, lt=100)


class InvoiceUpdate(BaseModel):
    issue_date: date | None = None
    due_date: date | None = None
    discount_amount: float | None = Field(None, ge=0)
    tax_rate_pct: float | None = Field(None, ge=0, lt=100)
    notes: str | None = None
    terms: str | None = None


class InvoiceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    status: str
    customer_id: UUID
    project_id: UUID | None
    issue_date: date
    due_date: date | None
    total: float
    balance_due: float = 0.0
    paid_amount: float = 0.0
    customer_name: str | None = None
    is_overdue: bool = False


class InvoiceDetail(InvoiceListItem):
    subtotal: float
    discount_amount: float
    tax_rate_pct: float
    tax_amount: float
    notes: str | None
    terms: str | None
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemOut] = Field(default_factory=list)


class InvoiceStatusChange(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _validate(cls, v):
        if v not in INVOICE_STATUSES:
            raise ValueError(f"status must be one of {INVOICE_STATUSES}")
        return v


# ════════════════════════════════════════════════════════════════
# PAYMENTS
# ════════════════════════════════════════════════════════════════

class PaymentCreate(BaseModel):
    direction: str
    method: str
    amount: float = Field(..., gt=0)
    payment_date: date

    customer_id: UUID | None = None
    supplier_id: UUID | None = None
    account_id: UUID | None = None

    reference_type: str | None = None
    reference_id: UUID | None = None
    reference_number: str | None = Field(None, max_length=100)
    notes: str | None = None

    @field_validator("direction")
    @classmethod
    def _validate_direction(cls, v):
        if v not in PAYMENT_DIRECTIONS:
            raise ValueError(f"direction must be one of {PAYMENT_DIRECTIONS}")
        return v

    @field_validator("method")
    @classmethod
    def _validate_method(cls, v):
        if v not in PAYMENT_METHODS:
            raise ValueError(f"method must be one of {PAYMENT_METHODS}")
        return v

    @field_validator("reference_type")
    @classmethod
    def _validate_reference(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in PAYMENT_REFERENCE_TYPES:
            raise ValueError(f"reference_type must be one of {PAYMENT_REFERENCE_TYPES}")
        return v


class PaymentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    direction: str
    method: str
    amount: float
    payment_date: date
    customer_id: UUID | None
    supplier_id: UUID | None
    reference_type: str | None
    reference_id: UUID | None
    reference_number: str | None
    customer_name: str | None = None
    supplier_name: str | None = None


class PaymentDetail(PaymentListItem):
    account_id: UUID | None
    notes: str | None
    created_at: datetime


class PaymentReverse(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


# ════════════════════════════════════════════════════════════════
# EXPENSES
# ════════════════════════════════════════════════════════════════

class ExpenseCreate(BaseModel):
    category: str
    description: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(..., gt=0)
    expense_date: date
    account_id: UUID | None = None
    reference_number: str | None = Field(None, max_length=100)
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        if v not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {EXPENSE_CATEGORIES}")
        return v


class ExpenseUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    amount: float | None = Field(None, gt=0)
    expense_date: date | None = None
    account_id: UUID | None = None
    reference_number: str | None = None
    notes: str | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    category: str
    description: str
    amount: float
    expense_date: date
    account_id: UUID | None
    reference_number: str | None
    notes: str | None
    created_at: datetime


# ════════════════════════════════════════════════════════════════
# REPORTS
# ════════════════════════════════════════════════════════════════

class PnLLine(BaseModel):
    label: str
    amount: float
    pct_of_revenue: float = 0.0


class PnLReport(BaseModel):
    period_start: date
    period_end: date

    revenue_lines: list[PnLLine]
    total_revenue: float

    cogs_lines: list[PnLLine]
    total_cogs: float

    gross_profit: float
    gross_margin_pct: float

    opex_lines: list[PnLLine]
    total_opex: float

    net_profit: float
    net_margin_pct: float


class CashFlowSummary(BaseModel):
    period_start: date
    period_end: date
    total_inflow: float
    total_outflow: float
    net_cash_flow: float


class ReceivablesSummary(BaseModel):
    total_outstanding: float
    total_overdue: float
    invoice_count: int
    overdue_count: int


class PayablesSummary(BaseModel):
    total_outstanding: float
    po_count: int