from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select

from app.core.deps import DbSession
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.customers.constants import (
    CUSTOMER_SORT_OPTIONS,
    CUSTOMER_SOURCE_LABELS,
    CUSTOMER_SOURCES,
    CUSTOMER_STATUS_LABELS,
    CUSTOMER_STATUSES,
    STATUS_TONE,
)
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    CustomerContactIn,
    CustomerCreate,
    CustomerUpdate,
)
from app.modules.customers.service import CustomerService
from app.modules.vehicles.repository import VehicleRepository
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/customers", tags=["admin-customers"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _catalog_context() -> dict:
    return {
        "statuses": CUSTOMER_STATUSES,
        "status_labels": CUSTOMER_STATUS_LABELS,
        "status_tone": STATUS_TONE,
        "sources": CUSTOMER_SOURCES,
        "source_labels": CUSTOMER_SOURCE_LABELS,
        "sort_options": CUSTOMER_SORT_OPTIONS,
    }


def _qs_factory(q, status_, is_active, source, sort):
    from urllib.parse import urlencode

    def _qs(**overrides) -> str:
        base = {
            "q": q or "",
            "status": status_ or "",
            "is_active": "" if is_active is None else ("true" if is_active else "false"),
            "source": source or "",
            "sort": sort,
        }
        base.update({k: ("" if v is None else v) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return _qs


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    status_: str | None = Query(None, alias="status"),
    is_active: bool | None = Query(None),
    source: str | None = Query(None),
    sort: str = Query("created_desc"),
    current=Depends(get_current_user),
) -> HTMLResponse:
    repo = CustomerRepository(db)
    stmt = repo.query(
        q=q, status=status_, is_active=is_active, source=source,
        sort=sort if sort in CUSTOMER_SORT_OPTIONS else "created_desc",
    )
    rows, meta = await paginate(db, stmt, params)
    stats = await repo.stats()

    return templates.render(
        request,
        "admin/customers/list.html",
        {
            "title": "Customers",
            "customers": rows,
            "page_meta": meta,
            "stats": stats,
            "q": q or "",
            "status_filter": status_ or "",
            "is_active_filter": is_active,
            "source_filter": source or "",
            "sort": sort,
            "qs": _qs_factory(q, status_, is_active, source, sort),
            **_catalog_context(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EXPORT CSV
# ════════════════════════════════════════════════════════════════

@router.get("/export.csv")
async def export_csv(
    db: DbSession,
    q: str | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    is_active: bool | None = Query(None),
    source: str | None = Query(None),
    current=Depends(get_current_user),
):
    stmt = CustomerRepository(db).query(
        q=q, status=status_, is_active=is_active, source=source,
    )
    rows = (await db.execute(stmt)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "code", "name", "email", "phone", "alt_phone",
        "city", "province", "postal_code", "country",
        "status", "source", "tax_id", "is_active", "created_at",
    ])
    for c in rows:
        writer.writerow([
            c.code, c.name, c.email or "", c.phone or "", c.alt_phone or "",
            c.city or "", c.province or "", c.postal_code or "", c.country or "",
            c.status, c.source or "", c.tax_id or "",
            "yes" if c.is_active else "no",
            c.created_at.isoformat() if c.created_at else "",
        ])

    buf.seek(0)
    filename = f"customers-{datetime.utcnow().strftime('%Y%m%d-%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ════════════════════════════════════════════════════════════════
# NEW / CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(request: Request, current=Depends(get_current_user)) -> HTMLResponse:
    return templates.render(
        request,
        "admin/customers/form.html",
        {
            "title": "New Customer",
            "mode": "create",
            "customer": None,
            **_catalog_context(),
        },
    )


@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
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
    except _FORM_ERRORS as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/customers/form.html",
            {
                "title": "New Customer",
                "mode": "create",
                "customer": None,
                "error": getattr(exc, "message", str(exc)),
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=getattr(exc, "status_code", 400),
        )

    await db.commit()
    return RedirectResponse(url=f"/admin/customers/{customer.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{customer_id}", response_class=HTMLResponse)
async def detail_view(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.modules.inquiries.models import Inquiry
    from app.modules.inquiries.constants import (
        SERVICE_INTEREST_LABELS, STATUS_TONE as INQ_STATUS_TONE,
    )

    repo = CustomerRepository(db)
    customer = await repo.get(customer_id)
    if not customer:
        raise NotFoundError("Customer not found")

    contacts = await repo.list_contacts(customer_id)
    vehicles, _ = await paginate(
        db,
        VehicleRepository(db).query(customer_id=customer_id),
        PageParams(page=1, size=100),
    )

    # Related inquiries — most recent first
    inq_rows = (
        await db.execute(
            select(Inquiry)
            .where(Inquiry.customer_id == customer_id)
            .order_by(Inquiry.created_at.desc())
            .limit(15)
        )
    ).scalars().all()
    open_inq_count = sum(
        1 for i in inq_rows if i.status not in ("CONVERTED", "LOST")
    )

    return templates.render(
        request,
        "admin/customers/detail.html",
        {
            "title": customer.name,
            "customer": customer,
            "contacts": contacts,
            "vehicles": vehicles,
            "inquiries": inq_rows,
            "open_inq_count": open_inq_count,
            "service_labels": SERVICE_INTEREST_LABELS,
            "inq_status_tone": INQ_STATUS_TONE,
            **_catalog_context(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT
# ════════════════════════════════════════════════════════════════

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
            **_catalog_context(),
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
    except _FORM_ERRORS as exc:
        await db.rollback()
        customer = await CustomerRepository(db).get(customer_id)
        return templates.render(
            request,
            "admin/customers/form.html",
            {
                "title": f"Edit {customer.name if customer else 'Customer'}",
                "mode": "edit",
                "customer": customer,
                "error": getattr(exc, "message", str(exc)),
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=getattr(exc, "status_code", 400),
        )

    await db.commit()
    return RedirectResponse(url=f"/admin/customers/{customer_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# CONTACTS
# ════════════════════════════════════════════════════════════════

@router.post("/{customer_id}/contacts", response_class=HTMLResponse)
async def add_contact_submit(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()
    try:
        payload = CustomerContactIn(
            name=(form.get("contact_name") or "").strip(),
            role=(form.get("contact_role") or "").strip() or None,
            phone=(form.get("contact_phone") or "").strip() or None,
            email=(form.get("contact_email") or "").strip() or None,
            notes=(form.get("contact_notes") or "").strip() or None,
        )
        await CustomerService(db).add_contact(customer_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        from urllib.parse import quote
        msg = quote(getattr(exc, "message", str(exc)), safe="")
        return RedirectResponse(
            url=f"/admin/customers/{customer_id}?error={msg}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/customers/{customer_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# ACTIVATE / DEACTIVATE
# ════════════════════════════════════════════════════════════════

@router.post("/{customer_id}/deactivate")
async def deactivate_submit(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    await CustomerService(db).deactivate(customer_id, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/customers/{customer_id}", status_code=303)


@router.post("/{customer_id}/reactivate")
async def reactivate_submit(
    customer_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    await CustomerService(db).reactivate(customer_id, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/customers/{customer_id}", status_code=303)