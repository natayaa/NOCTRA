"""Admin web routes for invoices."""

from __future__ import annotations

from datetime import date
from urllib.parse import quote, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select

from app.core.constants import AuditAction, PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.jobs import queue
from app.core.logging import log
from app.core.pagination import PageParams, paginate, page_params
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import get_current_user
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.finance.constants import (
    DEFAULT_DP_PERCENT,
    INVOICE_KIND_LABELS,
    INVOICE_KINDS,
    INVOICE_STATUSES,
    INVOICE_STATUS_LABELS,
    PAYMENT_METHODS,
    PAYMENT_METHOD_LABELS,
    InvoiceKind,
    PaymentDirection,
    PaymentReferenceType,
    today_local,
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
from app.modules.projects.constants import TERMINAL_PROJECT_STATUSES
from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository
from app.modules.settings.business import business_profile
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/invoices", tags=["admin-invoices"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


def _form_error(exc: Exception) -> str:
    return (getattr(exc, "message", None) or str(exc) or "Invalid input").strip()


def _net_paid(payments) -> float:
    """Net amount paid by a list of already-loaded payments."""
    total = sum(
        p.amount if p.direction == PaymentDirection.IN.value else -p.amount
        for p in payments
    )
    return float(total or 0)


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    only_unpaid: bool = Query(False),
    _=read(PermissionCode.FINANCE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    repo = InvoiceRepository(db)
    stmt = repo.query(q=q, status=status_, only_unpaid=only_unpaid)
    rows, meta = await paginate(db, stmt, params)

    customer_ids = {r.customer_id for r in rows if r.customer_id}
    customers: dict = {}
    if customer_ids:
        c_rows = await db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        customers = {cid: name for cid, name in c_rows.all()}

    # Batch paid amount — 1 query for the whole page
    paid_map = await repo.batch_paid_amount([inv.id for inv in rows])
    today = today_local()

    enriched = []
    for inv in rows:
        paid = paid_map.get(inv.id, 0.0)
        enriched.append({
            "invoice": inv,
            "customer_name": customers.get(inv.customer_id),
            "paid": paid,
            "balance": float(inv.total) - paid,
            "is_overdue": (
                inv.due_date is not None
                and today > inv.due_date
                and inv.status not in ("PAID", "CANCELLED")
            ),
        })

    # qs helper for chip/pagination — preserves active filters
    def qs(page: int | None = None, **overrides) -> str:
        base = {
            "q": q or "",
            "status": status_ or "",
            "only_unpaid": "true" if only_unpaid else "",
        }
        if page is not None:
            base["page"] = str(page)
        base.update({k: ("" if v is None else str(v)) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

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
            "qs": qs,
        },
    )


# ════════════════════════════════════════════════════════════════
# NEW / CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    customer_id: UUID | None = Query(None),
    project_id: UUID | None = Query(None),
    kind: str | None = Query(None),
    error: str | None = Query(None),
    _=write(PermissionCode.INVOICE_WRITE),
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

    if kind not in INVOICE_KINDS:
        kind = (
            InvoiceKind.FINAL.value
            if preselected_project
            else InvoiceKind.OTHER.value
        )

    # FIX (B1): load dropdown data — only when NOT preselecting, since
    # preselect path uses hidden inputs. Empty when preselected.
    customers: list = []
    projects: list = []
    if not preselected_customer:
        customers = list(
            (
                await db.execute(
                    select(Customer)
                    .where(Customer.is_active.is_(True))
                    .order_by(Customer.name)
                    .limit(500)
                )
            ).scalars().all()
        )
        projects = list(
            (
                await db.execute(
                    select(Project)
                    .where(Project.status.not_in(TERMINAL_PROJECT_STATUSES))
                    .order_by(Project.created_at.desc())
                    .limit(500)
                )
            ).scalars().all()
        )

    # Contract context + smart prefill when invoicing a project stage.
    billing = None
    form_values: dict = {}
    if preselected_project:
        from app.modules.finance.models import Invoice

        active = list(
            (
                await db.execute(
                    select(Invoice)
                    .where(Invoice.project_id == preselected_project.id)
                    .where(Invoice.status != "CANCELLED")
                )
            ).scalars().all()
        )
        contract = InvoiceService._contract_value(preselected_project) or 0.0
        invoiced = sum(
            float(i.subtotal or 0) - float(i.discount_amount or 0)
            for i in active
        )
        remaining = max(contract - invoiced, 0.0)
        billing = {
            "contract": contract,
            "invoiced": invoiced,
            "remaining": remaining,
            "invoices": active,
        }

        title = preselected_project.title or f"Project {preselected_project.code}"
        if kind == InvoiceKind.DP.value:
            amount = round(
                min(contract * DEFAULT_DP_PERCENT / 100.0, remaining), 2
            )
            description = f"DP — {title}"
        elif kind == InvoiceKind.FINAL.value:
            amount = round(remaining, 2)
            description = f"Pelunasan — {title}"
        else:
            amount = round(remaining, 2)
            description = title
        form_values = {
            "item_description": description,
            "item_quantity": "1",
            "item_unit_price": str(amount),
        }

    return templates.render(
        request,
        "admin/invoices/form.html",
        {
            "title": "New Invoice",
            "mode": "create",
            "invoice": None,
            "kind": kind,
            "invoice_kinds": INVOICE_KINDS,
            "invoice_kind_labels": INVOICE_KIND_LABELS,
            "preselected_customer": preselected_customer,
            "preselected_project": preselected_project,
            "billing": billing,
            "customers": customers,
            "projects": projects,
            "today": today_local(),
            "error": error,
            "form_values": form_values,
        },
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVOICE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
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

        payload = InvoiceCreate(
            customer_id=UUID(form["customer_id"]),
            project_id=(UUID(form["project_id"]) if form.get("project_id") else None),
            kind=(form.get("kind") or "").strip() or InvoiceKind.OTHER.value,
            issue_date=date.fromisoformat(form["issue_date"]),
            due_date=(
                date.fromisoformat(form["due_date"])
                if form.get("due_date") else None
            ),
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
        # Re-render with dropdown data
        customers = list(
            (
                await db.execute(
                    select(Customer)
                    .where(Customer.is_active.is_(True))
                    .order_by(Customer.name)
                    .limit(500)
                )
            ).scalars().all()
        )
        projects = list(
            (
                await db.execute(
                    select(Project)
                    .where(Project.status.not_in(TERMINAL_PROJECT_STATUSES))
                    .order_by(Project.created_at.desc())
                    .limit(500)
                )
            ).scalars().all()
        )
        return templates.render(
            request,
            "admin/invoices/form.html",
            {
                "title": "New Invoice",
                "mode": "create",
                "invoice": None,
                "kind": (form.get("kind") or InvoiceKind.OTHER.value),
                "invoice_kinds": INVOICE_KINDS,
                "invoice_kind_labels": INVOICE_KIND_LABELS,
                "preselected_customer": None,
                "preselected_project": None,
                "billing": None,
                "customers": customers,
                "projects": projects,
                "today": today_local(),
                "error": _form_error(exc),
                "form_values": dict(form),
            },
            status_code=getattr(exc, "status_code", 400),
        )

    return RedirectResponse(url=f"/admin/invoices/{inv.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{invoice_id}", response_class=HTMLResponse)
async def detail_view(
    invoice_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    notice: str | None = Query(None),
    _=read(PermissionCode.FINANCE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    repo = InvoiceRepository(db)
    inv = await repo.get(invoice_id)
    if not inv:
        raise NotFoundError("Invoice not found")

    customer = (
        await CustomerRepository(db).get(inv.customer_id) if inv.customer_id else None
    )
    project = (
        await ProjectRepository(db).get(inv.project_id) if inv.project_id else None
    )

    # `repo.get` eager-loads items in creation order; do not re-query them.
    items = inv.items

    payments = await repo.payments_for(invoice_id)
    paid = _net_paid(payments)
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
            "kind_labels": INVOICE_KIND_LABELS,
            "today": today_local(),
            "error": error,
            "notice": notice,
        },
    )


# ════════════════════════════════════════════════════════════════
# PRINT / EMAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{invoice_id}/print", response_class=HTMLResponse)
async def print_view(
    invoice_id: UUID,
    request: Request,
    db: DbSession,
    _=read(PermissionCode.FINANCE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    """Print-optimized A4 document. The browser's print dialog saves PDF."""
    repo = InvoiceRepository(db)
    inv = await repo.get(invoice_id)
    if not inv:
        raise NotFoundError("Invoice not found")

    customer = (
        await CustomerRepository(db).get(inv.customer_id) if inv.customer_id else None
    )
    project = (
        await ProjectRepository(db).get(inv.project_id) if inv.project_id else None
    )
    items = inv.items
    payments = await repo.payments_for(invoice_id)
    paid = _net_paid(payments)

    return templates.render(
        request,
        "admin/invoices/print.html",
        {
            "title": inv.code,
            "invoice": inv,
            "customer": customer,
            "project": project,
            "items": items,
            "payments": payments,
            "paid": paid,
            "balance": float(inv.total) - paid,
            "business": await business_profile(db),
            "kind_label": INVOICE_KIND_LABELS.get(inv.kind, inv.kind),
            "status_label": INVOICE_STATUS_LABELS.get(inv.status, inv.status),
        },
    )


@router.post("/{invoice_id}/email")
async def email_invoice_submit(
    invoice_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVOICE_WRITE),
    current=Depends(get_current_user),
):
    """Queue the invoice email. Delivery is logged in `email_logs`."""
    inv = await InvoiceRepository(db).get(invoice_id)
    if not inv:
        raise NotFoundError("Invoice not found")

    customer = (
        await CustomerRepository(db).get(inv.customer_id) if inv.customer_id else None
    )
    if customer is None or not customer.email:
        return RedirectResponse(
            url=f"/admin/invoices/{invoice_id}?error="
                + quote(
                    "Customer has no email address — add one on the customer record first.",
                    safe="",
                ),
            status_code=303,
        )
    if inv.status == "CANCELLED":
        return RedirectResponse(
            url=f"/admin/invoices/{invoice_id}?error="
                + quote("Cancelled invoices cannot be emailed", safe=""),
            status_code=303,
        )

    target_email = customer.email
    actor_id = current.id

    await AuditService(db).log(
        action=AuditAction.UPDATE,
        table_name="invoices",
        record_id=invoice_id,
        user_id=actor_id,
        new_data={"emailed_to": target_email},
    )
    await db.commit()

    async def _dispatch():
        from app.core.database import SessionLocal
        from app.services.invoice_mailer import send_invoice_email

        async with SessionLocal() as session:
            try:
                await send_invoice_email(session, invoice_id=invoice_id)
                await session.commit()
            except Exception:
                await session.rollback()
                log.exception("invoice_email_failed", invoice_id=str(invoice_id))

    await queue.enqueue(_dispatch)

    return RedirectResponse(
        url=f"/admin/invoices/{invoice_id}?notice="
            + quote(f"Invoice email queued for {target_email}.", safe=""),
        status_code=303,
    )


# ════════════════════════════════════════════════════════════════
# STATUS / PAYMENTS / EDIT
# ════════════════════════════════════════════════════════════════

@router.post("/{invoice_id}/status")
async def status_submit(
    invoice_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVOICE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()
    new_status = (form.get("status") or "").strip()
    try:
        await InvoiceService(db).change_status(invoice_id, new_status, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/invoices/{invoice_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/invoices/{invoice_id}", status_code=303)


@router.post("/{invoice_id}/payments")
async def record_payment_submit(
    invoice_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PAYMENT_WRITE),
    current=Depends(get_current_user),
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
        return RedirectResponse(
            url=f"/admin/invoices/{invoice_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/invoices/{invoice_id}", status_code=303)


@router.get("/{invoice_id}/edit", response_class=HTMLResponse)
async def edit_view(
    invoice_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=write(PermissionCode.INVOICE_WRITE),
    current=Depends(get_current_user),
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
            "kind": inv.kind,
            "invoice_kinds": INVOICE_KINDS,
            "invoice_kind_labels": INVOICE_KIND_LABELS,
            "preselected_customer": customer,
            "preselected_project": None,
            "billing": None,
            "customers": [],
            "projects": [],
            "today": today_local(),
            "error": error,
            "form_values": {},
        },
    )


@router.post("/{invoice_id}")
async def update_submit(
    invoice_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVOICE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()
    try:
        payload = InvoiceUpdate(
            issue_date=(
                date.fromisoformat(form["issue_date"])
                if form.get("issue_date") else None
            ),
            due_date=(
                date.fromisoformat(form["due_date"])
                if form.get("due_date") else None
            ),
            discount_amount=(
                float(form["discount_amount"])
                if form.get("discount_amount") else None
            ),
            tax_rate_pct=(
                float(form["tax_rate_pct"])
                if form.get("tax_rate_pct") else None
            ),
            notes=(form.get("notes") or "").strip() or None,
            terms=(form.get("terms") or "").strip() or None,
        )
        await InvoiceService(db).update(invoice_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/invoices/{invoice_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/invoices/{invoice_id}", status_code=303)