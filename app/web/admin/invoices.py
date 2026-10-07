"""Admin web routes for invoices."""

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
from app.modules.customers.repository import CustomerRepository
from app.modules.finance.constants import (
    INVOICE_STATUSES,
    INVOICE_STATUS_LABELS,
    PAYMENT_METHODS,
    PAYMENT_METHOD_LABELS,
    PaymentDirection,
    PaymentReferenceType,
)
from app.modules.finance.repository import (
    AccountRepository,
    InvoiceRepository,
)
from app.modules.finance.schemas import (
    InvoiceCreate,
    InvoiceItemIn,
    InvoiceUpdate,
    PaymentCreate,
)
from app.modules.finance.service import InvoiceService, PaymentService
from app.modules.projects.repository import ProjectRepository
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/invoices", tags=["admin-invoices"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


def _form_error(exc: Exception) -> str:
    msg = getattr(exc, "message", None) or str(exc)
    return msg.strip() or "Invalid input"


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    only_unpaid: bool = Query(False),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = InvoiceRepository(db).query(q=q, status=status_, only_unpaid=only_unpaid)
    rows, meta = await paginate(db, stmt, params)

    from app.modules.customers.models import Customer
    customer_ids = {r.customer_id for r in rows if r.customer_id}
    customers = {}
    if customer_ids:
        c_rows = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        customers = {c.id: c for c in c_rows.scalars().all()}

    repo = InvoiceRepository(db)
    enriched = []
    today = datetime.now(UTC).date()
    for inv in rows:
        paid = await repo.paid_amount(inv.id)
        enriched.append({
            "invoice": inv,
            "customer": customers.get(inv.customer_id),
            "paid": paid,
            "balance": float(inv.total) - paid,
            "is_overdue": (
                inv.due_date is not None
                and today > inv.due_date
                and inv.status not in ("PAID", "CANCELLED")
            ),
        })

    return templates.render(
        request,
        "admin/invoices/list.html",
        {
            "title": "Invoices",
            "rows": enriched,
            "page_meta": meta,
            "q": q or "",
            "status_filter": status_ or "",
            "only_unpaid": only_unpaid,
            "statuses": INVOICE_STATUSES,
            "status_labels": INVOICE_STATUS_LABELS,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    customer_id: UUID | None = Query(None),
    project_id: UUID | None = Query(None),
    error: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    preselected_customer = None
    preselected_project = None

    if customer_id:
        preselected_customer = await CustomerRepository(db).get(customer_id)
    if project_id:
        preselected_project = await ProjectRepository(db).get(project_id)
        if preselected_project and not preselected_customer:
            preselected_customer = await CustomerRepository(db).get(
                preselected_project.customer_id
            )

    return templates.render(
        request,
        "admin/invoices/form.html",
        {
            "title": "New Invoice",
            "mode": "create",
            "invoice": None,
            "preselected_customer": preselected_customer,
            "preselected_project": preselected_project,
            "today": datetime.now(UTC).date(),
            "error": error,
            "form_values": {},
        },
    )


@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()

    items = []
    descriptions = form.getlist("item_description")
    quantities = form.getlist("item_quantity")
    prices = form.getlist("item_unit_price")
    for i, desc in enumerate(descriptions):
        desc = (desc or "").strip()
        if not desc:
            continue
        items.append(InvoiceItemIn(
            description=desc,
            quantity=float(quantities[i] or 1) if i < len(quantities) else 1,
            unit_price=float(prices[i] or 0) if i < len(prices) else 0,
        ))

    try:
        payload = InvoiceCreate(
            customer_id=UUID(form["customer_id"]),
            project_id=(UUID(form["project_id"]) if form.get("project_id") else None),
            issue_date=date.fromisoformat(form["issue_date"]),
            due_date=(date.fromisoformat(form["due_date"]) if form.get("due_date") else None),
            discount_amount=float(form.get("discount_amount") or 0),
            tax_rate_pct=float(form.get("tax_rate_pct") or 0),
            notes=(form.get("notes") or "").strip() or None,
            terms=(form.get("terms") or "").strip() or None,
            items=items,
        )
        inv = await InvoiceService(db).create(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/invoices/form.html",
            {
                "title": "New Invoice",
                "mode": "create",
                "invoice": None,
                "preselected_customer": None,
                "preselected_project": None,
                "today": datetime.now(UTC).date(),
                "error": _form_error(exc),
                "form_values": dict(form),
            },
            status_code=getattr(exc, "status_code", 400),
        )
    return RedirectResponse(url=f"/admin/invoices/{inv.id}", status_code=303)


@router.get("/{invoice_id}", response_class=HTMLResponse)
async def detail_view(
    invoice_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    repo = InvoiceRepository(db)
    inv = await repo.get(invoice_id)
    if not inv:
        raise NotFoundError("Invoice not found")

    customer = await CustomerRepository(db).get(inv.customer_id) if inv.customer_id else None
    project = await ProjectRepository(db).get(inv.project_id) if inv.project_id else None

    from app.modules.finance.models import InvoiceItem

    items = (await db.execute(
        select(InvoiceItem)
        .where(InvoiceItem.invoice_id == invoice_id)
        .order_by(InvoiceItem.created_at)
    )).scalars().all()

    payments = await repo.payments_for(invoice_id)
    paid = sum(float(p.amount) for p in payments)
    balance = float(inv.total) - paid

    accounts = (await db.execute(AccountRepository(db).query())).scalars().all()

    return templates.render(
        request,
        "admin/invoices/detail.html",
        {
            "title": inv.code,
            "invoice": inv,
            "customer": customer,
            "project": project,
            "items": items,
            "payments": payments,
            "paid": paid,
            "balance": balance,
            "accounts": accounts,
            "payment_methods": PAYMENT_METHODS,
            "payment_method_labels": PAYMENT_METHOD_LABELS,
            "status_labels": INVOICE_STATUS_LABELS,
        },
    )


@router.post("/{invoice_id}/status")
async def status_submit(
    invoice_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    new_status = (form.get("status") or "").strip()
    try:
        await InvoiceService(db).change_status(invoice_id, new_status, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/invoices/{invoice_id}?error={msg}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/invoices/{invoice_id}", status_code=303)


@router.post("/{invoice_id}/payments")
async def record_payment_submit(
    invoice_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    inv = await InvoiceRepository(db).get(invoice_id)
    if not inv:
        raise NotFoundError("Invoice not found")

    try:
        payload = PaymentCreate(
            direction=PaymentDirection.IN.value,
            method=(form.get("method") or "BANK_TRANSFER").strip(),
            amount=float(form.get("amount") or 0),
            payment_date=date.fromisoformat(form["payment_date"]),
            customer_id=inv.customer_id,
            account_id=(UUID(form["account_id"]) if form.get("account_id") else None),
            reference_type=PaymentReferenceType.INVOICE.value,
            reference_id=inv.id,
            reference_number=(form.get("reference_number") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
        )
        await PaymentService(db).record(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/invoices/{invoice_id}?error={msg}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/invoices/{invoice_id}", status_code=303)


@router.get("/{invoice_id}/edit", response_class=HTMLResponse)
async def edit_view(
    invoice_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    inv = await InvoiceRepository(db).get(invoice_id)
    if not inv:
        raise NotFoundError("Invoice not found")
    customer = await CustomerRepository(db).get(inv.customer_id)
    return templates.render(
        request,
        "admin/invoices/form.html",
        {
            "title": f"Edit {inv.code}",
            "mode": "edit",
            "invoice": inv,
            "preselected_customer": customer,
            "preselected_project": None,
            "today": datetime.now(UTC).date(),
            "error": None,
            "form_values": {},
        },
    )


@router.post("/{invoice_id}")
async def update_submit(
    invoice_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    try:
        payload = InvoiceUpdate(
            issue_date=(date.fromisoformat(form["issue_date"]) if form.get("issue_date") else None),
            due_date=(date.fromisoformat(form["due_date"]) if form.get("due_date") else None),
            discount_amount=(float(form["discount_amount"]) if form.get("discount_amount") else None),
            tax_rate_pct=(float(form["tax_rate_pct"]) if form.get("tax_rate_pct") else None),
            notes=(form.get("notes") or "").strip() or None,
            terms=(form.get("terms") or "").strip() or None,
        )
        await InvoiceService(db).update(invoice_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/invoices/{invoice_id}?error={msg}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/invoices/{invoice_id}", status_code=303)