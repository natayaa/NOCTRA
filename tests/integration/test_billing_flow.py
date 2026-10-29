"""Staged project billing: DP invoice, final invoice, advances."""

from datetime import date

import pytest
from sqlalchemy import select

from app.core.exceptions import ConflictError, ValidationError
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.finance.constants import InvoiceKind, InvoiceStatus
from app.modules.finance.models import Invoice, Payment
from app.modules.finance.schemas import (
    InvoiceCreate,
    InvoiceFromProject,
    InvoiceItemIn,
    PaymentCreate,
)
from app.modules.finance.service import InvoiceService, PaymentService
from app.modules.projects.models import Project

TODAY = date(2026, 10, 29)
CONTRACT = 10_000_000


async def _actor(db) -> User:
    user = User(
        username="billing_tester",
        email="billing_tester@noctra.local",
        full_name="Billing Tester",
        hashed_password=hash_password("super-secret-1"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    return user


async def _project(db, *, price: int = CONTRACT) -> tuple[Customer, Project]:
    customer = Customer(
        code="NOCTRA-C-2026-000777", name="Billing Customer", phone="0812000777"
    )
    db.add(customer)
    await db.flush()
    project = Project(
        code="NOCTRA-P-2026-000777",
        title="Full repaint",
        customer_id=customer.id,
        status="APPROVED",
        approved_price=price,
    )
    db.add(project)
    await db.commit()
    return customer, project


async def _advance(db, project, customer, actor, amount: int) -> Payment:
    return await PaymentService(db).record(
        PaymentCreate(
            direction="IN",
            method="CASH",
            amount=amount,
            payment_date=TODAY,
            customer_id=customer.id,
            reference_type="PROJECT",
            reference_id=project.id,
        ),
        actor=actor,
    )


@pytest.mark.asyncio
async def test_dp_then_final_bills_exactly_the_contract(db):
    actor = await _actor(db)
    customer, project = await _project(db)
    service = InvoiceService(db)

    dp = await service.create_from_project(
        InvoiceFromProject(project_id=project.id, kind="DP"), actor=actor
    )
    await db.commit()
    assert dp.kind == InvoiceKind.DP.value
    assert float(dp.total) == pytest.approx(CONTRACT / 2)
    assert dp.status == InvoiceStatus.DRAFT.value

    final = await service.create_from_project(
        InvoiceFromProject(project_id=project.id, kind="FINAL"), actor=actor
    )
    await db.commit()
    assert final.kind == InvoiceKind.FINAL.value
    assert float(final.total) == pytest.approx(CONTRACT - CONTRACT / 2)

    with pytest.raises(ConflictError):
        await service.create_from_project(
            InvoiceFromProject(project_id=project.id, kind="FINAL"), actor=actor
        )


@pytest.mark.asyncio
async def test_manual_invoices_cannot_exceed_contract(db):
    actor = await _actor(db)
    actor_id = actor.id
    customer, project = await _project(db)
    customer_id, project_id = customer.id, project.id
    service = InvoiceService(db)

    over = InvoiceCreate(
        customer_id=customer_id,
        project_id=project_id,
        issue_date=TODAY,
        items=[InvoiceItemIn(description="Whole job", quantity=1, unit_price=12_000_000)],
    )
    with pytest.raises(ValidationError):
        await service.create(over, actor=actor)
    await db.rollback()
    actor = await db.get(User, actor_id)

    dp = await service.create_from_project(
        InvoiceFromProject(project_id=project_id, kind="DP", amount=4_000_000),
        actor=actor,
    )
    await db.commit()
    assert float(dp.total) == pytest.approx(4_000_000)

    too_much = InvoiceCreate(
        customer_id=customer_id,
        project_id=project_id,
        issue_date=TODAY,
        items=[InvoiceItemIn(description="Rest", quantity=1, unit_price=7_000_000)],
    )
    with pytest.raises(ValidationError):
        await service.create(too_much, actor=actor)
    await db.rollback()
    actor = await db.get(User, actor_id)

    fits = InvoiceCreate(
        customer_id=customer_id,
        project_id=project_id,
        issue_date=TODAY,
        items=[InvoiceItemIn(description="Rest", quantity=1, unit_price=6_000_000)],
    )
    rest = await service.create(fits, actor=actor)
    await db.commit()
    assert float(rest.total) == pytest.approx(6_000_000)


@pytest.mark.asyncio
async def test_advance_is_applied_to_the_dp_invoice(db):
    actor = await _actor(db)
    customer, project = await _project(db)

    advance = await _advance(db, project, customer, actor, CONTRACT // 2)
    await db.commit()
    assert advance.reference_type == "PROJECT"

    dp = await InvoiceService(db).create_from_project(
        InvoiceFromProject(project_id=project.id, kind="DP"), actor=actor
    )
    await db.commit()

    payment = await db.get(Payment, advance.id)
    await db.refresh(payment)
    assert payment.reference_type == "INVOICE"
    assert payment.reference_id == dp.id

    invoice = await db.get(Invoice, dp.id)
    await db.refresh(invoice)
    assert invoice.status == InvoiceStatus.PAID.value


@pytest.mark.asyncio
async def test_advance_larger_than_invoice_stays_at_project_level(db):
    actor = await _actor(db)
    customer, project = await _project(db)

    advance = await _advance(db, project, customer, actor, 6_000_000)
    await db.commit()

    dp = await InvoiceService(db).create_from_project(
        InvoiceFromProject(project_id=project.id, kind="DP"), actor=actor
    )
    await db.commit()

    payment = await db.get(Payment, advance.id)
    await db.refresh(payment)
    assert payment.reference_type == "PROJECT"

    invoice = await db.get(Invoice, dp.id)
    await db.refresh(invoice)
    assert invoice.status == InvoiceStatus.DRAFT.value


@pytest.mark.asyncio
async def test_payment_on_draft_invoice_issues_it(db):
    actor = await _actor(db)
    customer, project = await _project(db)
    service = InvoiceService(db)

    dp = await service.create_from_project(
        InvoiceFromProject(project_id=project.id, kind="DP"), actor=actor
    )
    await db.commit()
    assert dp.status == InvoiceStatus.DRAFT.value

    await PaymentService(db).record(
        PaymentCreate(
            direction="IN",
            method="BANK_TRANSFER",
            amount=1_000_000,
            payment_date=TODAY,
            reference_type="INVOICE",
            reference_id=dp.id,
        ),
        actor=actor,
    )
    await db.commit()

    inv = await db.get(Invoice, dp.id)
    await db.refresh(inv)
    assert inv.status == InvoiceStatus.PARTIALLY_PAID.value
    assert inv.code.startswith("INV-")


@pytest.mark.asyncio
async def test_second_final_invoice_rejected(db):
    actor = await _actor(db)
    _, project = await _project(db)
    service = InvoiceService(db)

    await service.create_from_project(
        InvoiceFromProject(
            project_id=project.id, kind="FINAL", amount=3_000_000
        ),
        actor=actor,
    )
    await db.commit()

    with pytest.raises(ConflictError):
        await service.create_from_project(
            InvoiceFromProject(
                project_id=project.id, kind="FINAL", amount=1_000_000
            ),
            actor=actor,
        )


@pytest.mark.asyncio
async def test_payment_cannot_exceed_invoice_balance(db):
    actor = await _actor(db)
    _, project = await _project(db)
    inv = await InvoiceService(db).create_from_project(
        InvoiceFromProject(project_id=project.id, kind="DP"), actor=actor
    )
    inv_id = inv.id
    await db.commit()

    with pytest.raises(ConflictError):
        await PaymentService(db).record(
            PaymentCreate(
                direction="IN",
                method="CASH",
                amount=6_000_000,
                payment_date=TODAY,
                reference_type="INVOICE",
                reference_id=inv_id,
            ),
            actor=actor,
        )
    await db.rollback()

    count = len(
        (await db.execute(select(Payment).where(Payment.reference_id == inv_id)))
        .scalars()
        .all()
    )
    assert count == 0
