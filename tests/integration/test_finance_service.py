"""Finance service invariants: receivables, payables, invoice edits."""

from datetime import date

import pytest

from app.core.exceptions import ConflictError, ValidationError
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.finance.schemas import (
    InvoiceCreate,
    InvoiceItemIn,
    InvoiceUpdate,
    PaymentCreate,
)
from app.modules.finance.service import (
    FinanceReportService,
    InvoiceService,
    PaymentService,
)
from app.modules.inventory.models import PurchaseOrder, Supplier


async def _actor(db) -> User:
    user = User(
        username="fin_tester",
        email="fin_tester@noctra.local",
        full_name="Finance Tester",
        hashed_password=hash_password("super-secret-1"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    return user


async def _customer(db) -> Customer:
    customer = Customer(code="NOCTRA-C-2026-000001", name="Ivan", phone="0812000001")
    db.add(customer)
    await db.commit()
    return customer


def _invoice_payload(customer_id, *, unit_price=100_000, discount=0) -> InvoiceCreate:
    return InvoiceCreate(
        customer_id=customer_id,
        issue_date=date(2026, 10, 29),
        discount_amount=discount,
        tax_rate_pct=0,
        items=[
            InvoiceItemIn(description="Body repaint", quantity=1, unit_price=unit_price)
        ],
    )


@pytest.mark.asyncio
async def test_draft_invoice_is_not_a_receivable(db):
    actor = await _actor(db)
    customer = await _customer(db)
    service = InvoiceService(db)

    invoice = await service.create(_invoice_payload(customer.id), actor=actor)
    await db.commit()

    summary = await FinanceReportService(db).receivables()
    assert summary.invoice_count == 0
    assert summary.total_outstanding == 0

    await service.change_status(invoice.id, "SENT", actor=actor)
    await db.commit()

    summary = await FinanceReportService(db).receivables()
    assert summary.invoice_count == 1
    assert summary.total_outstanding == pytest.approx(100_000)


@pytest.mark.asyncio
async def test_discount_above_subtotal_rejected(db):
    actor = await _actor(db)
    customer = await _customer(db)

    with pytest.raises(ValidationError):
        await InvoiceService(db).create(
            _invoice_payload(customer.id, unit_price=100_000, discount=150_000),
            actor=actor,
        )


@pytest.mark.asyncio
async def test_edit_cannot_drop_total_below_paid(db):
    actor = await _actor(db)
    actor_id = actor.id
    customer = await _customer(db)
    service = InvoiceService(db)

    invoice = await service.create(_invoice_payload(customer.id), actor=actor)
    invoice_id = invoice.id
    await service.change_status(invoice_id, "SENT", actor=actor)
    await db.commit()

    await PaymentService(db).record(
        PaymentCreate(
            direction="IN",
            method="CASH",
            amount=50_000,
            payment_date=date(2026, 10, 29),
            reference_type="INVOICE",
            reference_id=invoice_id,
        ),
        actor=actor,
    )
    await db.commit()

    with pytest.raises(ConflictError):
        await service.update(
            invoice_id, InvoiceUpdate(discount_amount=60_000), actor=actor
        )
    await db.rollback()
    # Rollback expires the actor; reload it before the next service call.
    actor = await db.get(User, actor_id)

    # A smaller discount keeps the total above the collected amount.
    updated = await service.update(
        invoice_id, InvoiceUpdate(discount_amount=10_000), actor=actor
    )
    await db.commit()
    assert float(updated.total) == pytest.approx(90_000)


@pytest.mark.asyncio
async def test_closed_unpaid_po_is_still_payable(db):
    supplier = Supplier(code="SUP-2026-0001", name="Paint Supply")
    db.add(supplier)
    await db.flush()

    po = PurchaseOrder(
        code="PO-2026-0001",
        supplier_id=supplier.id,
        status="CLOSED",
        order_date=date(2026, 10, 1),
        total_amount=750_000,
    )
    db.add(po)
    await db.commit()

    summary = await FinanceReportService(db).payables()
    assert summary.po_count == 1
    assert summary.total_outstanding == pytest.approx(750_000)
