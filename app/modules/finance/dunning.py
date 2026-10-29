"""Overdue status sweep + payment reminders.

`apply_payment_status()` keeps statuses honest when a payment or a manual
status change happens, but an invoice nobody touches stays `SENT` forever.
Reports compute overdue dynamically, so the badge and the report drifted
apart. This module reconciles the stored status once a day and nudges
customers whose invoices are due or past due.

Reminder selection is deliberately conservative: one email per invoice
per cooldown window, no reminders for paid/cancelled/zero-balance rows,
and reminders only when email delivery is actually enabled.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log
from app.modules.customers.models import Customer
from app.modules.email.constants import (
    EmailRelatedType,
    EmailTemplate,
)
from app.modules.email.models import EmailLog
from app.modules.finance.constants import InvoiceStatus, today_local
from app.modules.finance.models import Invoice
from app.modules.finance.repository import InvoiceRepository
from app.modules.settings.business import business_profile
from app.services.invoice_mailer import send_invoice_reminder

_OPEN_STATUSES = [
    InvoiceStatus.SENT.value,
    InvoiceStatus.PARTIALLY_PAID.value,
    InvoiceStatus.OVERDUE.value,
]


class InvoiceDunningService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InvoiceRepository(db)

    async def sweep(self, *, as_of: date | None = None) -> int:
        """Flip stale open invoices past their due date to OVERDUE.

        Idempotent: already-OVERDUE rows are excluded by the status filter.
        Returns the number of rows changed.
        """
        day = as_of or today_local()
        stmt = (
            update(Invoice)
            .where(
                Invoice.status.in_([
                    InvoiceStatus.SENT.value,
                    InvoiceStatus.PARTIALLY_PAID.value,
                ]),
                Invoice.due_date.isnot(None),
                Invoice.due_date < day,
            )
            .values(status=InvoiceStatus.OVERDUE.value)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return int(result.rowcount or 0)

    async def pending_reminders(
        self,
        *,
        as_of: date | None = None,
        window_days: int | None = None,
        cooldown_hours: int | None = None,
    ) -> list[dict[str, Any]]:
        """Invoices that deserve a reminder right now."""
        day = as_of or today_local()
        window = (
            settings.OVERDUE_REMINDER_WINDOW_DAYS
            if window_days is None
            else window_days
        )
        cooldown = (
            settings.OVERDUE_REMINDER_COOLDOWN_HOURS
            if cooldown_hours is None
            else cooldown_hours
        )
        cutoff = datetime.now(UTC) - timedelta(hours=cooldown)

        # Any attempt inside the cooldown suppresses another attempt —
        # including a failed one, so a broken SMTP config cannot turn
        # into a retry storm against every customer.
        recent = (
            select(EmailLog.related_id)
            .where(
                EmailLog.related_type == EmailRelatedType.INVOICE.value,
                EmailLog.template == EmailTemplate.INVOICE_REMINDER.value,
                EmailLog.created_at >= cutoff,
                EmailLog.related_id.isnot(None),
            )
        )

        stmt = (
            select(Invoice, Customer)
            .join(Customer, Customer.id == Invoice.customer_id)
            .where(
                Invoice.status.in_(_OPEN_STATUSES),
                Invoice.due_date.isnot(None),
                Invoice.due_date <= day + timedelta(days=window),
                Customer.email.isnot(None),
                Invoice.id.not_in(recent),
            )
            .order_by(Invoice.due_date, Invoice.created_at)
            .limit(100)
        )
        rows = (await self.db.execute(stmt)).all()
        if not rows:
            return []

        paid_map = await self.repo.batch_paid_amount([inv.id for inv, _ in rows])
        reminders: list[dict[str, Any]] = []
        for invoice, customer in rows:
            balance = float(invoice.total) - paid_map.get(invoice.id, 0.0)
            if balance <= 0.01:
                continue
            reminders.append({
                "invoice": invoice,
                "customer": customer,
                "balance": balance,
            })
        return reminders


async def run_overdue_sweep(db: AsyncSession) -> dict[str, int]:
    """Entry point used by the daily scheduler and by tests."""
    svc = InvoiceDunningService(db)
    marked = await svc.sweep()

    reminders_sent = 0
    if settings.OVERDUE_REMINDER_ENABLED and settings.EMAIL_ENABLED:
        business = await business_profile(db)
        as_of = today_local()
        for row in await svc.pending_reminders(as_of=as_of):
            try:
                await send_invoice_reminder(
                    db,
                    invoice=row["invoice"],
                    customer=row["customer"],
                    business=business,
                    as_of=as_of,
                )
                reminders_sent += 1
            except Exception:
                log.exception(
                    "overdue_reminder_failed",
                    invoice_id=str(row["invoice"].id),
                )

    log.info(
        "overdue_sweep_complete",
        marked_overdue=marked,
        reminders=reminders_sent,
    )
    return {"marked_overdue": marked, "reminders": reminders_sent}
