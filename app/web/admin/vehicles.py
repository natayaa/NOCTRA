"""Admin web routes for vehicles."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from urllib.parse import quote, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import and_, or_, select

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.vehicles.constants import (
    CATEGORY_TONE,
    VEHICLE_CATEGORIES,
    VEHICLE_CATEGORY_LABELS,
    VEHICLE_SORT_OPTIONS,
)
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import VehicleCreate, VehicleUpdate
from app.modules.vehicles.service import VehicleService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/vehicles", tags=["admin-vehicles"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _catalog_context() -> dict:
    return {
        "categories": VEHICLE_CATEGORIES,
        "category_labels": VEHICLE_CATEGORY_LABELS,
        "category_tone": CATEGORY_TONE,
        "sort_options": VEHICLE_SORT_OPTIONS,
    }


def _form_error(exc: Exception) -> str:
    return (getattr(exc, "message", None) or str(exc) or "Invalid input").strip()


async def _list_active_customers(db, limit: int = 500) -> list[Customer]:
    stmt = (
        select(Customer)
        .where(Customer.is_active.is_(True))
        .order_by(Customer.name)
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


def _parse_year(raw) -> int | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return -1  # Let Pydantic range-check fail cleanly


def _form_payload(form) -> dict:
    return dict(
        plate_number=(form.get("plate_number") or "").strip() or None,
        brand=(form.get("brand") or "").strip(),
        model=(form.get("model") or "").strip(),
        year=_parse_year(form.get("year")),
        color=(form.get("color") or "").strip() or None,
        category=(form.get("category") or "").strip() or None,
        vin=(form.get("vin") or "").strip() or None,
        engine_number=(form.get("engine_number") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
        brand_id=(UUID(str(form["brand_id"])) if form.get("brand_id") else None),
        model_id=(UUID(str(form["model_id"])) if form.get("model_id") else None),
    )


# ════════════════════════════════════════════════════════════════
# HTMX FRAGMENT
# ════════════════════════════════════════════════════════════════

@router.get("/api/search-customers", response_class=HTMLResponse)
async def search_customers_fragment(
    request: Request,
    db: DbSession,
    q: str = Query("", max_length=100),
    _=read(PermissionCode.VEHICLE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    customers = []
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = (
            select(Customer)
            .where(
                and_(
                    Customer.is_active.is_(True),
                    or_(
                        Customer.name.ilike(like),
                        Customer.code.ilike(like),
                        Customer.phone.ilike(like),
                        Customer.email.ilike(like),
                    ),
                )
            )
            .order_by(Customer.name)
            .limit(10)
        )
        customers = (await db.execute(stmt)).scalars().all()

    return templates.render(
        request,
        "admin/vehicles/_customer_options.html",
        {"customers": customers, "q": q},
    )


# ════════════════════════════════════════════════════════════════
# LIST + EXPORT
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    customer_id: UUID | None = Query(None),
    category: str | None = Query(None),
    brand: str | None = Query(None),
    sort: str = Query("created_desc"),
    _=read(PermissionCode.VEHICLE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    repo = VehicleRepository(db)
    stmt = repo.query(
        q=q, customer_id=customer_id, category=category, brand=brand,
        sort=sort if sort in VEHICLE_SORT_OPTIONS else "created_desc",
    )
    rows, meta = await paginate(db, stmt, params)

    owner_ids = {v.customer_id for v in rows if v.customer_id}
    owners_by_id: dict = {}
    if owner_ids:
        c_rows = await db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(owner_ids))
        )
        owners_by_id = {cid: name for cid, name in c_rows.all()}

    owner = None
    if customer_id:
        owner = await CustomerRepository(db).get(customer_id)

    stats = await repo.stats(customer_id=customer_id)
    brands = await repo.list_distinct_brands(customer_id=customer_id)

    def _qs(**overrides) -> str:
        base = {
            "q": q or "",
            "customer_id": str(customer_id) if customer_id else "",
            "category": category or "",
            "brand": brand or "",
            "sort": sort,
        }
        base.update({k: ("" if v is None else v) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/vehicles/list.html",
        {
            "title": "Vehicles",
            "vehicles": rows,
            "page_meta": meta,
            "stats": stats,
            "owners_by_id": owners_by_id,
            "q": q or "",
            "customer_id": customer_id,
            "category_filter": category or "",
            "brand_filter": brand or "",
            "sort": sort,
            "owner": owner,
            "brands": brands,
            "qs": _qs,
            **_catalog_context(),
        },
    )


@router.get("/export.csv")
async def export_csv(
    db: DbSession,
    q: str | None = Query(None),
    customer_id: UUID | None = Query(None),
    category: str | None = Query(None),
    _=read(PermissionCode.VEHICLE_READ),
    current=Depends(get_current_user),
):
    stmt = VehicleRepository(db).query(
        q=q, customer_id=customer_id, category=category,
    )
    rows = (await db.execute(stmt)).scalars().all()

    owner_ids = {v.customer_id for v in rows if v.customer_id}
    owners: dict = {}
    if owner_ids:
        c_rows = await db.execute(
            select(Customer.id, Customer.name, Customer.code).where(
                Customer.id.in_(owner_ids)
            )
        )
        owners = {cid: (name, code) for cid, name, code in c_rows.all()}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "plate_number", "brand", "model", "year", "color", "category",
        "vin", "engine_number", "owner_name", "owner_code", "created_at",
    ])
    for v in rows:
        o = owners.get(v.customer_id)
        writer.writerow([
            v.plate_number or "", v.brand, v.model, v.year or "",
            v.color or "", v.category or "", v.vin or "", v.engine_number or "",
            o[0] if o else "", o[1] if o else "",
            v.created_at.isoformat() if v.created_at else "",
        ])

    buf.seek(0)
    filename = f"vehicles-{datetime.utcnow().strftime('%Y%m%d-%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ════════════════════════════════════════════════════════════════
# NEW / CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    customer_id: UUID | None = Query(None),
    _=write(PermissionCode.VEHICLE_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    preselected = None
    customers: list[Customer] = []

    if customer_id:
        preselected = await CustomerRepository(db).get(customer_id)
    else:
        customers = await _list_active_customers(db)

    return templates.render(
        request,
        "admin/vehicles/form.html",
        {
            "title": "New Vehicle",
            "mode": "create",
            "vehicle": None,
            "customer_id": customer_id,
            "preselected_customer": preselected,
            "customers": customers,
            "brands_catalog": await VehicleRepository(db).list_brands(),
            **_catalog_context(),
        },
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.VEHICLE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    async def _render_error(msg: str, status_code: int = 400):
        preselected = None
        cid = form.get("customer_id")
        if cid:
            try:
                preselected = await CustomerRepository(db).get(UUID(str(cid)))
            except (ValueError, TypeError):
                preselected = None
        return templates.render(
            request,
            "admin/vehicles/form.html",
            {
                "title": "New Vehicle",
                "mode": "create",
                "vehicle": None,
                "customer_id": preselected.id if preselected else None,
                "preselected_customer": preselected,
                "customers": [] if preselected else await _list_active_customers(db),
                "error": msg,
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=status_code,
        )

    raw_cid = form.get("customer_id")
    if not raw_cid:
        return await _render_error("Please select a customer.")
    try:
        customer_id = UUID(str(raw_cid))
    except (ValueError, TypeError):
        return await _render_error("Invalid customer selection.")

    try:
        payload = VehicleCreate(**_form_payload(form))
        vehicle = await VehicleService(db).create(
            customer_id, payload, actor=current
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return await _render_error(
            _form_error(exc), getattr(exc, "status_code", 400)
        )

    return RedirectResponse(url=f"/admin/vehicles/{vehicle.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{vehicle_id}", response_class=HTMLResponse)
async def detail_view(
    vehicle_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=read(PermissionCode.VEHICLE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.modules.inquiries.models import Inquiry
    from app.modules.inquiries.constants import (
        SERVICE_INTEREST_LABELS,
        STATUS_TONE as INQ_STATUS_TONE,
    )

    vehicle = await VehicleRepository(db).get(vehicle_id)
    if not vehicle:
        raise NotFoundError("Vehicle not found")
    owner = await CustomerRepository(db).get(vehicle.customer_id)

    inq_rows = (
        await db.execute(
            select(Inquiry)
            .where(Inquiry.vehicle_id == vehicle_id)
            .order_by(Inquiry.created_at.desc())
            .limit(15)
        )
    ).scalars().all()
    open_inq_count = sum(
        1 for i in inq_rows if i.status not in ("CONVERTED", "LOST")
    )

    return templates.render(
        request,
        "admin/vehicles/detail.html",
        {
            "title": f"{vehicle.brand} {vehicle.model}",
            "vehicle": vehicle,
            "owner": owner,
            "inquiries": inq_rows,
            "open_inq_count": open_inq_count,
            "service_labels": SERVICE_INTEREST_LABELS,
            "inq_status_tone": INQ_STATUS_TONE,
            "error": error,
            **_catalog_context(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT
# ════════════════════════════════════════════════════════════════

@router.get("/{vehicle_id}/edit", response_class=HTMLResponse)
async def edit_view(
    vehicle_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.VEHICLE_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    vehicle = await VehicleRepository(db).get(vehicle_id)
    if not vehicle:
        raise NotFoundError("Vehicle not found")
    owner = await CustomerRepository(db).get(vehicle.customer_id)

    return templates.render(
        request,
        "admin/vehicles/form.html",
        {
            "title": f"Edit {vehicle.brand} {vehicle.model}",
            "mode": "edit",
            "vehicle": vehicle,
            "customer_id": vehicle.customer_id,
            "preselected_customer": owner,
            "customers": [],
            "brands_catalog": await VehicleRepository(db).list_brands(),
            **_catalog_context(),
        },
    )


@router.post("/{vehicle_id}")
async def update_submit(
    vehicle_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.VEHICLE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    async def _render_error(msg: str, status_code: int = 400):
        vehicle = await VehicleRepository(db).get(vehicle_id)
        owner = (
            await CustomerRepository(db).get(vehicle.customer_id)
            if vehicle else None
        )
        return templates.render(
            request,
            "admin/vehicles/form.html",
            {
                "title": (
                    f"Edit {vehicle.brand} {vehicle.model}"
                    if vehicle else "Edit Vehicle"
                ),
                "mode": "edit",
                "vehicle": vehicle,
                "customer_id": vehicle.customer_id if vehicle else None,
                "preselected_customer": owner,
                "customers": [],
                "error": msg,
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=status_code,
        )

    try:
        payload = VehicleUpdate(**_form_payload(form))
        await VehicleService(db).update(vehicle_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return await _render_error(
            _form_error(exc), getattr(exc, "status_code", 400)
        )

    return RedirectResponse(url=f"/admin/vehicles/{vehicle_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DELETE
# ════════════════════════════════════════════════════════════════

@router.post("/{vehicle_id}/delete")
async def delete_submit(
    vehicle_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.VEHICLE_DELETE),
    current=Depends(get_current_user),
):
    try:
        await VehicleService(db).delete(vehicle_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/vehicles/{vehicle_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )
    return RedirectResponse(url="/admin/vehicles", status_code=303)