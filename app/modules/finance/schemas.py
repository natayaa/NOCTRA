"""Pydantic schemas for the finance module."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.modules.finance.constants import (
    EXPENSE_CATEGORIES,
    INVOICE_KINDS,
    INVOICE_STATUSES,
    PAYMENT_DIRECTIONS,
    PAYMENT_METHODS,
    PAYMENT_REFERENCE_TYPES,
    InvoiceKind,
)


_EMPTY = {"", "none", "null", "undefined", "nil"}


def _clean_optional(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in _EMPTY:
        return None
    return s


def _reject_null(v):
    if v is None:
        raise ValueError("field cannot be null")
    return v


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
    kind: str = InvoiceKind.OTHER.value
    issue_date: date
    due_date: date | None = None

    discount_amount: float = Field(0, ge=0)
    tax_rate_pct: float = Field(0, ge=0, lt=100)

    notes: str | None = None
    terms: str | None = None

    # Require at least one line item — there is no endpoint for adding items
    # after creation, so an empty invoice would be dead data.
    items: list[InvoiceItemIn] = Field(..., min_length=1)

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, v):
        if v not in INVOICE_KINDS:
            raise ValueError(f"kind must be one of {INVOICE_KINDS}")
        return v


class InvoiceFromProject(BaseModel):
    project_id: UUID
    kind: str = InvoiceKind.FINAL.value
    # Exactly one of these picks the billed amount. When both are omitted:
    # DP falls back to DEFAULT_DP_PERCENT of the contract, FINAL bills
    # whatever is still uninvoiced.
    amount: float | None = Field(None, gt=0)
    percent: float | None = Field(None, gt=0, le=100)
    issue_date: date | None = None
    due_date: date | None = None
    tax_rate_pct: float = Field(0, ge=0, lt=100)

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, v):
        if v not in INVOICE_KINDS:
            raise ValueError(f"kind must be one of {INVOICE_KINDS}")
        return v

    @model_validator(mode="after")
    def _amount_or_percent(self):
        if self.amount is not None and self.percent is not None:
            raise ValueError("Provide either amount or percent, not both")
        return self


class InvoiceUpdate(BaseModel):
    issue_date: date | None = None
    due_date: date | None = None
    discount_amount: float | None = Field(None, ge=0)
    tax_rate_pct: float | None = Field(None, ge=0, lt=100)
    notes: str | None = None
    terms: str | None = None

    # Full replacement of line items. Omit the field to leave items alone.
    # `[]` is rejected by min_length=1 — an invoice must have >=1 item.
    # Replacing items is only permitted while the invoice has no payments
    # (enforced in the service layer).
    items: list[InvoiceItemIn] | None = Field(None, min_length=1)

    # issue_date / discount_amount / tax_rate_pct are NON-nullable in the DB.
    # Reject explicit null so it becomes 422, not a 500 constraint error.
    @field_validator("issue_date", "discount_amount", "tax_rate_pct")
    @classmethod
    def _non_nullable(cls, v):
        return _reject_null(v)

    @model_validator(mode="after")
    def _items_not_explicit_null(self):
        # `items: null` is ambiguous — it could mean "clear" (which we
        # forbid) or "no change" (which the field's absence conveys).
        # Reject it so callers get an explicit 422.
        if "items" in self.model_fields_set and self.items is None:
            raise ValueError(
                "items cannot be null; omit the field to leave items unchanged"
            )
        return self


class InvoiceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    status: str
    kind: str
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
            raise ValueError(
                f"reference_type must be one of {PAYMENT_REFERENCE_TYPES}"
            )
        return v

    @model_validator(mode="after")
    def _check_reference_consistency(self):
        has_type = self.reference_type is not None
        has_id = self.reference_id is not None
        if has_type != has_id:
            raise ValueError(
                "reference_type and reference_id must be provided together"
            )
        return self


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

    @field_validator("category", "description", "amount", "expense_date")
    @classmethod
    def _non_nullable(cls, v):
        return _reject_null(v)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        if v is not None and v not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {EXPENSE_CATEGORIES}")
        return v

    @field_validator("description")
    @classmethod
    def _validate_description(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("description cannot be blank")
        return v


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