"""Customer-facing invoice emails (issue + overdue reminder).

Both functions are safe to call from a background worker: they load
everything from the given session and never touch request state.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.customers.models import Customer
from app.modules.email.constants import EmailRelatedType, EmailTemplate
from app.modules.email.models import EmailLog
from app.modules.email.service import EmailService
from app.modules.finance.constants import INVOICE_KIND_LABELS, INVOICE_STATUS_LABELS
from app.modules.finance.models import Invoice, InvoiceItem
from app.modules.finance.repository import InvoiceRepository
from app.modules.projects.models import Project
from app.modules.settings.business import business_profile


async def invoice_context(db: AsyncSession, invoice: Invoice) -> dict:
    repo = InvoiceRepository(db)
    customer = (
        await db.get(Customer, invoice.customer_id) if invoice.customer_id else None
    )
    project = (
        await db.get(Project, invoice.project_id) if invoice.project_id else None
    )
    items = list(
        (
            await db.execute(
                select(InvoiceItem)
                .where(InvoiceItem.invoice_id == invoice.id)
                .order_by(InvoiceItem.created_at)
            )
        ).scalars().all()
    )
    paid = await repo.paid_amount(invoice.id)
    return {
        "invoice": invoice,
        "customer": customer,
        "project": project,
        "items": items,
        "paid": paid,
        "balance": float(invoice.total) - paid,
        "kind_label": INVOICE_KIND_LABELS.get(invoice.kind, invoice.kind),
        "status_label": INVOICE_STATUS_LABELS.get(invoice.status, invoice.status),
        "business": await business_profile(db),
    }


async def send_invoice_email(
    db: AsyncSession,
    *,
    invoice_id: UUID,
) -> EmailLog:
    """Email the invoice summary to the customer on file."""
    invoice = await InvoiceRepository(db).get(invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice not found")

    context = await invoice_context(db, invoice)
    customer: Customer | None = context["customer"]
    if customer is None or not customer.email:
        raise ValidationError(
            "Customer has no email address — add one on the customer record first."
        )
    if invoice.status == "CANCELLED":
        raise ValidationError("Cancelled invoices cannot be emailed")

    business = context["business"]
    return await EmailService(db).send_template(
        template=EmailTemplate.INVOICE_ISSUED,
        template_path="emails/invoice_issued.html",
        to_email=customer.email,
        to_name=customer.name,
        subject=f"Invoice {invoice.code} — {business['name']}",
        context=context,
        related_type=EmailRelatedType.INVOICE,
        related_id=invoice.id,
    )


async def send_invoice_reminder(
    db: AsyncSession,
    *,
    invoice: Invoice,
    customer: Customer,
    business: dict,
    as_of: date,
) -> EmailLog:
    """Remind the customer about an invoice that is due or overdue."""
    paid = await InvoiceRepository(db).paid_amount(invoice.id)
    days_past_due = (
        max((as_of - invoice.due_date).days, 0) if invoice.due_date else 0
    )
    return await EmailService(db).send_template(
        template=EmailTemplate.INVOICE_REMINDER,
        template_path="emails/invoice_reminder.html",
        to_email=customer.email,
        to_name=customer.name,
        subject=f"Reminder: invoice {invoice.code} — {business['name']}",
        context={
            "invoice": invoice,
            "customer": customer,
            "business": business,
            "paid": paid,
            "balance": float(invoice.total) - paid,
            "days_past_due": days_past_due,
            "as_of": as_of,
            "kind_label": INVOICE_KIND_LABELS.get(invoice.kind, invoice.kind),
        },
        related_type=EmailRelatedType.INVOICE,
        related_id=invoice.id,
    )
