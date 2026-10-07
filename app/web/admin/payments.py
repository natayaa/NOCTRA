"""Admin web routes for payments."""

from __future__ import annotations

from datetime import UTC, date, datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select

from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.customers.models import Customer
from app.modules.finance.constants import (
    PAYMENT_DIRECTIONS,
    PAYMENT_METHODS,
    PAYMENT_METHOD_LABELS,
    PAYMENT_REFERENCE_TYPES,
)
from app.modules.finance.repository import (
    AccountRepository,
    InvoiceRepository,
    PaymentRepository,
)
from app.modules.finance.schemas import PaymentCreate
from app.modules.finance.service import PaymentService
from app.modules.inventory.models import Supplier
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


def _form_error(exc: Exception) -> str:
    msg = getattr(exc, "message", None) or str(exc)
    return msg.strip() or "Invalid input"


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    direction: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = PaymentRepository(db).query(direction=direction)
    rows, meta = await paginate(db, stmt, params)

    cids = {r.customer_id for r in rows if r.customer_id}
    sids = {r.supplier_id for r in rows if r.supplier_id}
    customers, suppliers = {}, {}
    if cids:
        c_rows = await db.execute(select(Customer).where(Customer.id.in_(cids)))
        customers = {c.id: c for c in c_rows.scalars().all()}
    if sids:
        s_rows = await db.execute(select(Supplier).where(Supplier.id.in_(sids)))
        suppliers = {s.id: s for s in s_rows.scalars().all()}

    enriched = [{
        "payment": p,
        "customer": customers.get(p.customer_id),
        "supplier": suppliers.get(p.supplier_id),
    } for p in rows]

    return templates.render(
        request,
        "admin/payments/list.html",
        {
            "title": "Payments",
            "rows": enriched,
            "page_meta": meta,
            "direction_filter": direction or "",
            "directions": PAYMENT_DIRECTIONS,
            "payment_method_labels": PAYMENT_METHOD_LABELS,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    direction: str = Query("IN"),
    error: str | None = Query(None),
    reference_type: str | None = Query(None),
    reference_id: UUID | None = Query(None),
    customer_id: UUID | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.modules.finance.constants import InvoiceStatus
    from app.modules.finance.models import Invoice
    from app.modules.finance.repository import InvoiceRepository

    if direction not in PAYMENT_DIRECTIONS:
        direction = "IN"

    accounts = (await db.execute(AccountRepository(db).query())).scalars().all()

    customers: list = []
    suppliers: list = []
    open_invoices: list = []

    if direction == "IN":
        customers = (
            await db.execute(select(Customer).order_by(Customer.name))
        ).scalars().all()

        # Load every open invoice the admin might want to link against.
        # Capped at 500 rows — plenty for a workshop.
        inv_repo = InvoiceRepository(db)
        inv_rows = (
            await db.execute(
                select(Invoice)
                .where(
                    Invoice.status.not_in([
                        InvoiceStatus.PAID.value,
                        InvoiceStatus.CANCELLED.value,
                    ])
                )
                .order_by(Invoice.issue_date.desc())
                .limit(500)
            )
        ).scalars().all()

        # Enrich with customer name + outstanding balance so the UI can
        # filter by customer and auto-fill the amount.
        cust_map = {c.id: c for c in customers}
        for inv in inv_rows:
            paid = await inv_repo.paid_amount(inv.id)
            balance = float(inv.total) - paid
            open_invoices.append({
                "id": str(inv.id),
                "code": inv.code,
                "customer_id": str(inv.customer_id),
                "customer_name": (
                    cust_map[inv.customer_id].name
                    if inv.customer_id in cust_map else ""
                ),
                "total": float(inv.total),
                "balance": balance,
            })
    else:
        suppliers = (
            await db.execute(select(Supplier).order_by(Supplier.name))
        ).scalars().all()

    today = datetime.now(UTC).date()
    return templates.render(
        request,
        "admin/payments/form.html",
        {
            "title": "Record Payment",
            "direction": direction,
            "error": error,
            "reference_type": reference_type or "",
            "reference_id": reference_id,
            "customer_id": customer_id,
            "accounts": accounts,
            "customers": customers,
            "suppliers": suppliers,
            "open_invoices": open_invoices,
            "payment_methods": PAYMENT_METHODS,
            "payment_method_labels": PAYMENT_METHOD_LABELS,
            "reference_types": PAYMENT_REFERENCE_TYPES,
            "today": today,
        },
    )

@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()
    direction = (form.get("direction") or "IN").strip()
    if direction not in PAYMENT_DIRECTIONS:
        direction = "IN"

    try:
        payload = PaymentCreate(
            direction=direction,
            method=(form.get("method") or "BANK_TRANSFER").strip(),
            amount=float(form.get("amount") or 0),
            payment_date=date.fromisoformat(form["payment_date"]),
            customer_id=(UUID(form["customer_id"]) if form.get("customer_id") else None),
            supplier_id=(UUID(form["supplier_id"]) if form.get("supplier_id") else None),
            account_id=(UUID(form["account_id"]) if form.get("account_id") else None),
            reference_type=(form.get("reference_type") or "").strip() or None,
            reference_id=(UUID(form["reference_id"]) if form.get("reference_id") else None),
            reference_number=(form.get("reference_number") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
        )
        payment = await PaymentService(db).record(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/payments/new?direction={direction}&error={msg}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/payments/{payment.id}", status_code=303)


@router.get("/{payment_id}", response_class=HTMLResponse)
async def detail_view(
    payment_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.modules.finance.models import Payment as PaymentModel

    p = await PaymentRepository(db).get(payment_id)
    if not p:
        raise NotFoundError("Payment not found")

    customer = await db.get(Customer, p.customer_id) if p.customer_id else None
    supplier = await db.get(Supplier, p.supplier_id) if p.supplier_id else None
    account = await AccountRepository(db).get(p.account_id) if p.account_id else None

    invoice = None
    if p.reference_type == "INVOICE" and p.reference_id:
        invoice = await InvoiceRepository(db).get(p.reference_id)

    reversal = (
        await db.execute(
            select(PaymentModel)
            .where(PaymentModel.notes.like(f"Reversal of {p.code}%"))
            .limit(1)
        )
    ).scalar_one_or_none()

    is_reversal = bool(p.notes and p.notes.startswith("Reversal of "))
    original = None
    if is_reversal:
        original_code = p.notes.split("Reversal of ", 1)[1].split(" ", 1)[0]
        original = (
            await db.execute(
                select(PaymentModel).where(PaymentModel.code == original_code).limit(1)
            )
        ).scalar_one_or_none()

    return templates.render(
        request,
        "admin/payments/detail.html",
        {
            "title": p.code,
            "payment": p,
            "customer": customer,
            "supplier": supplier,
            "account": account,
            "invoice": invoice,
            "reversal": reversal,
            "is_reversal": is_reversal,
            "original": original,
            "error": error,
            "payment_method_labels": PAYMENT_METHOD_LABELS,
        },
    )


@router.post("/{payment_id}/reverse")
async def reverse_payment_submit(
    payment_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()
    reason = (form.get("reason") or "").strip()
    if len(reason) < 3:
        return RedirectResponse(
            url=f"/admin/payments/{payment_id}?error=Reason+is+required",
            status_code=303,
        )
    try:
        await PaymentService(db).reverse(payment_id, actor=current, reason=reason)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/payments/{payment_id}?error={msg}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/payments/{payment_id}", status_code=303)