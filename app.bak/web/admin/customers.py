from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from core.deps import DbSession
from core.exceptions import ConflictError, NotFoundError
from core.pagination import PageParams, paginate, page_params
from modules.auth.dependencies import get_current_user
from modules.customers.constants import CUSTOMER_STATUSES
from modules.customers.repository import CustomerRepository
from modules.customers.schemas import (
    CustomerContactIn,
    CustomerCreate,
    CustomerUpdate,
)
from modules.customers.service import CustomerService
from modules.vehicles.repository import VehicleRepository
from web.templates_env import templates

router = APIRouter(prefix="/admin/customers", tags=["admin-customers"])


# ── List ────────────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    status_: str | None = Query(None, alias="status"),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = CustomerRepository(db).query(q=q, status=status_)
    rows, meta = await paginate(db, stmt, params)

    return templates.render(
        request,
        "admin/customers/list.html",
        {
            "title": "Customers",
            "customers": rows,
            "page_meta": meta,
            "q": q or "",
            "status_filter": status_ or "",
            "statuses": CUSTOMER_STATUSES,
        },
    )


# ── New ─────────────────────────────────────────────────────
@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    current=Depends(get_current_user),
) -> HTMLResponse:
    return templates.render(
        request,
        "admin/customers/form.html",
        {
            "title": "New Customer",
            "mode": "create",
            "customer": None,
            "statuses": CUSTOMER_STATUSES,
        },
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()

    payload = CustomerCreate(
        name=(form.get("name") or "").strip(),
        email=(form.get("email") or "").strip() or None,
        phone=(form.get("phone") or "").strip() or None,
        alt_phone=(form.get("alt_phone") or "").strip() or None,
        address_line1=(form.get("address_line1") or "").strip() or None,
        address_line2=(form.get("address_line2") or "").strip() or None,
        city=(form.get("city") or "").strip() or None,
        province=(form.get("province") or "").strip() or None,
        postal_code=(form.get("postal_code") or "").strip() or None,
        country=(form.get("country") or "Indonesia").strip(),
        tax_id=(form.get("tax_id") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
        source=(form.get("source") or "").strip() or None,
    )

    try:
        customer = await CustomerService(db).create(payload, actor=current)
    except ConflictError as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/customers/form.html",
            {
                "title": "New Customer",
                "mode": "create",
                "customer": None,
                "statuses": CUSTOMER_STATUSES,
                "error": exc.message,
                "form_values": dict(form),
            },
            status_code=409,
        )

    await db.commit()
    return RedirectResponse(
        url=f"/admin/customers/{customer.id}",
        status_code=303,
    )


# ── Detail ──────────────────────────────────────────────────
@router.get("/{customer_id}", response_class=HTMLResponse)
async def detail_view(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.core.pagination import PageParams as _PP, paginate as _pg

    repo = CustomerRepository(db)
    customer = await repo.get(customer_id)
    if not customer:
        raise NotFoundError("Customer not found")

    contacts = await repo.list_contacts(customer_id)
    vehicle_rows, _ = await _pg(
        db,
        VehicleRepository(db).query(customer_id=customer_id),
        _PP(page=1, size=50),
    )

    return templates.render(
        request,
        "admin/customers/detail.html",
        {
            "title": customer.name,
            "customer": customer,
            "contacts": contacts,
            "vehicles": vehicle_rows,
        },
    )


# ── Edit ────────────────────────────────────────────────────
@router.get("/{customer_id}/edit", response_class=HTMLResponse)
async def edit_view(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
) -> HTMLResponse:
    customer = await CustomerRepository(db).get(customer_id)
    if not customer:
        raise NotFoundError("Customer not found")
    return templates.render(
        request,
        "admin/customers/form.html",
        {
            "title": f"Edit {customer.name}",
            "mode": "edit",
            "customer": customer,
            "statuses": CUSTOMER_STATUSES,
        },
    )


@router.post("/{customer_id}")
async def update_submit(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()

    payload = CustomerUpdate(
        name=(form.get("name") or "").strip() or None,
        email=(form.get("email") or "").strip() or None,
        phone=(form.get("phone") or "").strip() or None,
        alt_phone=(form.get("alt_phone") or "").strip() or None,
        address_line1=(form.get("address_line1") or "").strip() or None,
        address_line2=(form.get("address_line2") or "").strip() or None,
        city=(form.get("city") or "").strip() or None,
        province=(form.get("province") or "").strip() or None,
        postal_code=(form.get("postal_code") or "").strip() or None,
        country=(form.get("country") or "").strip() or None,
        tax_id=(form.get("tax_id") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
        status=(form.get("status") or "").strip() or None,
        is_active=form.get("is_active") == "true",
    )

    try:
        await CustomerService(db).update(customer_id, payload, actor=current)
    except ConflictError as exc:
        await db.rollback()
        customer = await CustomerRepository(db).get(customer_id)
        return templates.render(
            request,
            "admin/customers/form.html",
            {
                "title": f"Edit {customer.name if customer else 'Customer'}",
                "mode": "edit",
                "customer": customer,
                "statuses": CUSTOMER_STATUSES,
                "error": exc.message,
                "form_values": dict(form),
            },
            status_code=409,
        )

    await db.commit()
    return RedirectResponse(
        url=f"/admin/customers/{customer_id}",
        status_code=303,
    )


# ── Add contact (HTMX-friendly) ─────────────────────────────
@router.post("/{customer_id}/contacts", response_class=HTMLResponse)
async def add_contact_submit(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()

    payload = CustomerContactIn(
        name=(form.get("contact_name") or "").strip(),
        role=(form.get("contact_role") or "").strip() or None,
        phone=(form.get("contact_phone") or "").strip() or None,
        email=(form.get("contact_email") or "").strip() or None,
        notes=(form.get("contact_notes") or "").strip() or None,
    )

    await CustomerService(db).add_contact(customer_id, payload, actor=current)
    await db.commit()
    return RedirectResponse(
        url=f"/admin/customers/{customer_id}",
        status_code=303,
    )


# ── Deactivate ──────────────────────────────────────────────
@router.post("/{customer_id}/deactivate")
async def deactivate_submit(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    await CustomerService(db).deactivate(customer_id, actor=current)
    await db.commit()
    return RedirectResponse(
        url=f"/admin/customers/{customer_id}",
        status_code=303,
    )