"""Finance schema validation — Phase 6."""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.finance.constants import (
    ACCOUNT_TYPES,
    EXPENSE_CATEGORIES,
    INVOICE_STATUSES,
    PAYMENT_DIRECTIONS,
    PAYMENT_METHODS,
)
from app.modules.finance.schemas import (
    ExpenseCreate,
    InvoiceCreate,
    InvoiceItemIn,
    PaymentCreate,
)


def test_account_types_complete():
    assert set(ACCOUNT_TYPES) == {"ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"}


def test_invoice_statuses_cover_states():
    for s in ("DRAFT", "SENT", "PARTIALLY_PAID", "PAID", "OVERDUE", "CANCELLED"):
        assert s in INVOICE_STATUSES


def test_payment_directions():
    assert set(PAYMENT_DIRECTIONS) == {"IN", "OUT"}


def test_payment_methods():
    assert "CASH" in PAYMENT_METHODS
    assert "BANK_TRANSFER" in PAYMENT_METHODS
    assert "QRIS" in PAYMENT_METHODS


def test_expense_categories():
    for c in ("RENT", "UTILITIES", "SALARIES", "MARKETING", "SUPPLIES"):
        assert c in EXPENSE_CATEGORIES


def test_payment_minimal_in():
    p = PaymentCreate(
        direction="IN", method="CASH", amount=100_000, payment_date=date.today(),
    )
    assert p.amount == 100_000


def test_payment_rejects_invalid_direction():
    with pytest.raises(ValidationError):
        PaymentCreate(
            direction="SIDEWAYS", method="CASH",
            amount=100_000, payment_date=date.today(),
        )


def test_payment_rejects_invalid_method():
    with pytest.raises(ValidationError):
        PaymentCreate(
            direction="IN", method="BITCOIN",
            amount=100_000, payment_date=date.today(),
        )


def test_payment_rejects_zero_amount():
    with pytest.raises(ValidationError):
        PaymentCreate(
            direction="IN", method="CASH",
            amount=0, payment_date=date.today(),
        )


def test_payment_rejects_negative_amount():
    with pytest.raises(ValidationError):
        PaymentCreate(
            direction="IN", method="CASH",
            amount=-500, payment_date=date.today(),
        )


def test_expense_minimal():
    e = ExpenseCreate(
        category="RENT", description="Workshop rent",
        amount=3_000_000, expense_date=date.today(),
    )
    assert e.amount == 3_000_000


def test_expense_rejects_invalid_category():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            category="BOATS", description="X",
            amount=100_000, expense_date=date.today(),
        )


def test_expense_rejects_zero_amount():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            category="RENT", description="X",
            amount=0, expense_date=date.today(),
        )


def test_invoice_minimal():
    i = InvoiceCreate(
        customer_id=uuid4(),
        issue_date=date.today(),
        items=[InvoiceItemIn(description="Repaint", quantity=1, unit_price=1_800_000)],
    )
    assert i.tax_rate_pct == 0


def test_invoice_item_requires_description():
    with pytest.raises(ValidationError):
        InvoiceItemIn(description="", quantity=1, unit_price=100)


def test_invoice_item_requires_positive_qty():
    with pytest.raises(ValidationError):
        InvoiceItemIn(description="X", quantity=0, unit_price=100)


def test_invoice_rejects_100pct_tax():
    with pytest.raises(ValidationError):
        InvoiceCreate(
            customer_id=uuid4(),
            issue_date=date.today(),
            tax_rate_pct=100,
        )