"""Invoice print document + email-to-customer.

The print view is a standalone A4 page (the browser's print dialog saves
the PDF). Emailing must never leak into the request path: the route logs
an audit row and queues delivery, while `send_invoice_email` itself owns
template rendering and `email_logs` bookkeeping.
"""

from datetime import date
from urllib.parse import unquote

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.security import hash_password
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.email.constants import EmailRelatedType, EmailStatus, EmailTemplate
from app.modules.email.models import EmailLog
from app.modules.finance.models import Invoice, InvoiceItem
from app.services.invoice_mailer import send_invoice_email

TODAY = date(2026, 10, 29)


async def _admin(client: AsyncClient, db) -> None:
    user = User(
        username="invoice_admin",
        email="invoice_admin@example.com",
        full_name="Invoice Admin",
        hashed_password=hash_password("password123"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()

    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "invoice_admin", "password": "password123"},
    )
    assert r.status_code == 200, r.text


async def _invoice(db, *, email: str | None = "budi@example.com", status="SENT"):
    customer = Customer(
        code="NOCTRA-C-2026-000888",
        name="Budi Santoso",
        phone="081234567890",
        email=email,
    )
    db.add(customer)
    await db.flush()

    invoice = Invoice(
        code="NOCTRA-I-2026-000888",
        customer_id=customer.id,
        issue_date=TODAY,
        due_date=date(2026, 11, 12),
        subtotal=8_500_000,
        total=8_500_000,
        status=status,
        kind="FINAL",
        notes="Terima kasih.",
    )
    db.add(invoice)
    await db.flush()
    db.add(
        InvoiceItem(
            invoice_id=invoice.id,
            description="Cat ulang bodi motor",
            quantity=1,
            unit_price=8_500_000,
            amount=8_500_000,
        )
    )
    await db.commit()
    return customer, invoice


async def _csrf(client: AsyncClient, path: str) -> str:
    page = await client.get(path)
    assert page.status_code == 200, page.text
    token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert token
    return token


@pytest.mark.asyncio
async def test_print_view_renders_document(client: AsyncClient, db):
    await _admin(client, db)
    _, invoice = await _invoice(db)

    page = await client.get(f"/admin/invoices/{invoice.id}/print")

    assert page.status_code == 200, page.text
    body = page.text
    assert invoice.code in body
    assert "Budi Santoso" in body
    assert "Cat ulang bodi motor" in body
    assert "Pelunasan" in body
    assert "window.print()" in body
    assert "@page" in body
    # It is a standalone document, not the admin shell.
    assert "<nav" not in body


@pytest.mark.asyncio
async def test_print_view_escapes_customer_input(client: AsyncClient, db):
    await _admin(client, db)
    customer, invoice = await _invoice(db)
    customer.name = "<script>alert(1)</script>"
    await db.commit()

    page = await client.get(f"/admin/invoices/{invoice.id}/print")

    assert page.status_code == 200
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page.text


@pytest.mark.asyncio
async def test_email_route_queues_and_audits(client: AsyncClient, db):
    await _admin(client, db)
    _, invoice = await _invoice(db)
    csrf = await _csrf(client, f"/admin/invoices/{invoice.id}")

    r = await client.post(
        f"/admin/invoices/{invoice.id}/email",
        data={"_csrf": csrf},
        follow_redirects=False,
    )

    assert r.status_code == 303, r.text
    location = unquote(r.headers["location"])
    assert "notice=Invoice email queued for budi@example.com." in location
    assert location.endswith(f"/admin/invoices/{invoice.id}?notice=Invoice email queued for budi@example.com.")

    audit = (
        await db.execute(select(AuditLog).where(AuditLog.action == "UPDATE"))
    ).scalars().all()
    assert len(audit) == 1
    assert audit[0].record_id == str(invoice.id)
    assert audit[0].new_data == {"emailed_to": "budi@example.com"}


@pytest.mark.asyncio
async def test_email_route_requires_customer_email(client: AsyncClient, db):
    await _admin(client, db)
    _, invoice = await _invoice(db, email=None)
    csrf = await _csrf(client, f"/admin/invoices/{invoice.id}")

    r = await client.post(
        f"/admin/invoices/{invoice.id}/email",
        data={"_csrf": csrf},
        follow_redirects=False,
    )

    assert r.status_code == 303
    assert "error=Customer has no email address" in unquote(r.headers["location"])


@pytest.mark.asyncio
async def test_email_route_refuses_cancelled_invoice(client: AsyncClient, db):
    await _admin(client, db)
    _, invoice = await _invoice(db, status="CANCELLED")
    csrf = await _csrf(client, f"/admin/invoices/{invoice.id}")

    r = await client.post(
        f"/admin/invoices/{invoice.id}/email",
        data={"_csrf": csrf},
        follow_redirects=False,
    )

    assert r.status_code == 303
    assert "error=Cancelled invoices cannot be emailed" in unquote(
        r.headers["location"]
    )


@pytest.mark.asyncio
async def test_send_invoice_email_logs_attempt(client: AsyncClient, db):
    _, invoice = await _invoice(db)

    log_row = await send_invoice_email(db, invoice_id=invoice.id)
    await db.commit()

    assert log_row.template == EmailTemplate.INVOICE_ISSUED.value
    assert log_row.related_type == EmailRelatedType.INVOICE.value
    assert log_row.related_id == invoice.id
    assert log_row.to_email == "budi@example.com"
    assert invoice.code in log_row.subject
    # EMAIL_ENABLED is false in tests → sender returns SKIPPED.
    assert log_row.status == EmailStatus.SKIPPED.value

    stored = (await db.execute(select(EmailLog))).scalar_one()
    assert stored.id == log_row.id


@pytest.mark.asyncio
async def test_send_invoice_email_rejects_missing_address(db):
    _, invoice = await _invoice(db, email=None)

    with pytest.raises(ValidationError):
        await send_invoice_email(db, invoice_id=invoice.id)
