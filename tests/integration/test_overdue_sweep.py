"""Daily dunning: stored status reconciliation + payment reminders.

Reports already compute "overdue" dynamically, but the stored status was
only updated when someone touched the invoice. The sweep keeps the badge
honest; reminders are rate-limited per invoice via `email_logs` so a
broken SMTP config cannot become a retry storm.
"""

from datetime import UTC, datetime, timedelta

import hashlib

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.modules.customers.models import Customer
from app.modules.email.constants import EmailRelatedType, EmailStatus, EmailTemplate
from app.modules.email.models import EmailLog
from app.modules.finance.constants import InvoiceStatus, today_local
from app.modules.finance.dunning import InvoiceDunningService, run_overdue_sweep
from app.modules.finance.models import Invoice, Payment

TODAY = today_local()


async def _customer(db, *, code="NOCTRA-C-2026-001000", email="budi@example.com"):
    digest = int(hashlib.sha1(code.encode()).hexdigest(), 16) % 10**8
    customer = Customer(
        code=code,
        name="Budi Santoso",
        phone=f"0812{digest:08d}",
        email=email,
    )
    db.add(customer)
    await db.commit()
    return customer


async def _invoice(
    db,
    customer,
    *,
    code="NOCTRA-I-2026-001000",
    status="SENT",
    due_in_days=-1,
    total=5_000_000,
):
    invoice = Invoice(
        code=code,
        customer_id=customer.id,
        issue_date=TODAY - timedelta(days=30),
        due_date=TODAY + timedelta(days=due_in_days),
        subtotal=total,
        total=total,
        status=status,
        kind="OTHER",
    )
    db.add(invoice)
    await db.commit()
    return invoice


@pytest.mark.asyncio
async def test_sweep_flips_only_stale_open_invoices(db):
    customer = await _customer(db)
    stale_sent = await _invoice(db, customer, code="NOCTRA-I-1", status="SENT")
    stale_partial = await _invoice(
        db,
        customer,
        code="NOCTRA-I-2",
        status="PARTIALLY_PAID",
        due_in_days=-5,
    )
    future = await _invoice(db, customer, code="NOCTRA-I-3", due_in_days=5)
    paid = await _invoice(db, customer, code="NOCTRA-I-4", status="PAID")
    draft = await _invoice(db, customer, code="NOCTRA-I-5", status="DRAFT")
    no_due = await _invoice(db, customer, code="NOCTRA-I-6")
    no_due.due_date = None
    await db.commit()

    changed = await InvoiceDunningService(db).sweep(as_of=TODAY)
    await db.commit()

    assert changed == 2
    for inv in (stale_sent, stale_partial):
        await db.refresh(inv)
        assert inv.status == InvoiceStatus.OVERDUE.value
    for inv in (future, paid, draft, no_due):
        await db.refresh(inv)
        assert inv.status not in (InvoiceStatus.OVERDUE.value,)


@pytest.mark.asyncio
async def test_sweep_is_idempotent(db):
    customer = await _customer(db)
    await _invoice(db, customer)
    svc = InvoiceDunningService(db)

    assert await svc.sweep(as_of=TODAY) == 1
    assert await svc.sweep(as_of=TODAY) == 0


@pytest.mark.asyncio
async def test_pending_reminders_window_email_and_balance(db):
    with_email = await _customer(db, code="NOCTRA-C-1", email="a@example.com")
    without_email = await _customer(db, code="NOCTRA-C-2", email=None)

    due_soon = await _invoice(db, with_email, code="NOCTRA-I-10", due_in_days=2)
    overdue = await _invoice(db, with_email, code="NOCTRA-I-11", due_in_days=-3)
    far_future = await _invoice(db, with_email, code="NOCTRA-I-12", due_in_days=30)
    no_mail = await _invoice(db, without_email, code="NOCTRA-I-13", due_in_days=-1)
    settled = await _invoice(db, with_email, code="NOCTRA-I-14", due_in_days=-1)
    db.add(
        Payment(
            code="NOCTRA-PAY-1",
            direction="IN",
            method="CASH",
            amount=settled.total,
            payment_date=TODAY,
            customer_id=with_email.id,
            reference_type="INVOICE",
            reference_id=settled.id,
        )
    )
    cancelled = await _invoice(
        db, with_email, code="NOCTRA-I-15", status="CANCELLED", due_in_days=-1
    )
    await db.commit()

    reminders = await InvoiceDunningService(db).pending_reminders(as_of=TODAY)
    ids = {r["invoice"].id for r in reminders}

    assert ids == {due_soon.id, overdue.id}
    assert no_mail.id not in ids and far_future.id not in ids
    assert settled.id not in ids and cancelled.id not in ids


@pytest.mark.asyncio
async def test_pending_reminders_respects_cooldown(db):
    customer = await _customer(db)
    invoice = await _invoice(db, customer)
    now = datetime.now(UTC)

    db.add(
        EmailLog(
            to_email="Budi@example.com",
            subject="Reminder",
            template=EmailTemplate.INVOICE_REMINDER.value,
            status=EmailStatus.SENT.value,
            related_type=EmailRelatedType.INVOICE.value,
            related_id=invoice.id,
            created_at=now - timedelta(hours=2),
        )
    )
    await db.commit()

    svc = InvoiceDunningService(db)
    assert await svc.pending_reminders(as_of=TODAY, cooldown_hours=72) == []

    # Once the last attempt is outside the window, the invoice qualifies again.
    fresh = await svc.pending_reminders(as_of=TODAY, cooldown_hours=1)
    assert [r["invoice"].id for r in fresh] == [invoice.id]


@pytest.mark.asyncio
async def test_run_overdue_sweep_sends_when_enabled(db, monkeypatch):
    customer = await _customer(db)
    invoice = await _invoice(db, customer)
    monkeypatch.setattr(settings, "OVERDUE_REMINDER_ENABLED", True)
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)

    result = await run_overdue_sweep(db)
    await db.commit()

    assert result == {"marked_overdue": 1, "reminders": 1}
    await db.refresh(invoice)
    assert invoice.status == InvoiceStatus.OVERDUE.value

    mail = (await db.execute(select(EmailLog))).scalar_one()
    assert mail.template == EmailTemplate.INVOICE_REMINDER.value
    assert mail.related_id == invoice.id
    assert mail.to_email == customer.email


@pytest.mark.asyncio
async def test_run_overdue_sweep_skips_email_when_disabled(db, monkeypatch):
    customer = await _customer(db)
    await _invoice(db, customer)
    monkeypatch.setattr(settings, "OVERDUE_REMINDER_ENABLED", False)

    result = await run_overdue_sweep(db)
    await db.commit()

    assert result == {"marked_overdue": 1, "reminders": 0}
    assert (await db.execute(select(EmailLog))).scalars().all() == []
