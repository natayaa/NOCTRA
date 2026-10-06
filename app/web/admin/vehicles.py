from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.vehicles.constants import VEHICLE_CATEGORIES
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import VehicleCreate, VehicleUpdate
from app.modules.vehicles.service import VehicleService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/vehicles", tags=["admin-vehicles"])


# ── List ────────────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    customer_id: UUID | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = VehicleRepository(db).query(q=q, customer_id=customer_id)
    rows, meta = await paginate(db, stmt, params)

    owner = None
    if customer_id:
        owner = await CustomerRepository(db).get(customer_id)

    return templates.render(
        request,
        "admin/vehicles/list.html",
        {
            "title": "Vehicles",
            "vehicles": rows,
            "page_meta": meta,
            "q": q or "",
            "customer_id": customer_id,
            "owner": owner,
        },
    )


# ── New ─────────────────────────────────────────────────────
@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    customer_id: UUID | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    preselected = None
    customers: list[Customer] = []

    if customer_id:
        preselected = await CustomerRepository(db).get(customer_id)
    else:
        stmt = select(Customer).where(Customer.is_active.is_(True)).order_by(Customer.name).limit(500)
        customers = list((await db.execute(stmt)).scalars().all())

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
            "categories": VEHICLE_CATEGORIES,
        },
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
        customer_id = UUID(str(form["customer_id"]))
    except (KeyError, ValueError):
        return templates.render(
            request,
            "admin/vehicles/form.html",
            {
                "title": "New Vehicle",
                "mode": "create",
                "vehicle": None,
                "customer_id": None,
                "preselected_customer": None,
                "customers": list(
                    (await db.execute(
                        select(Customer).where(Customer.is_active.is_(True)).order_by(Customer.name).limit(500)
                    )).scalars().all()
                ),
                "categories": VEHICLE_CATEGORIES,
                "error": "Please select a customer.",
                "form_values": dict(form),
            },
            status_code=400,
        )

    payload = VehicleCreate(
        plate_number=(form.get("plate_number") or "").strip() or None,
        brand=(form.get("brand") or "").strip(),
        model=(form.get("model") or "").strip(),
        year=int(form["year"]) if form.get("year") else None,
        color=(form.get("color") or "").strip() or None,
        category=(form.get("category") or "").strip() or None,
        vin=(form.get("vin") or "").strip() or None,
        engine_number=(form.get("engine_number") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )

    vehicle = await VehicleService(db).create(customer_id, payload, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/vehicles/{vehicle.id}", status_code=303)


# ── Detail ──────────────────────────────────────────────────
@router.get("/{vehicle_id}", response_class=HTMLResponse)
async def detail_view(
    vehicle_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
) -> HTMLResponse:
    vehicle = await VehicleRepository(db).get(vehicle_id)
    if not vehicle:
        raise NotFoundError("Vehicle not found")
    owner = await CustomerRepository(db).get(vehicle.customer_id)

    return templates.render(
        request,
        "admin/vehicles/detail.html",
        {
            "title": f"{vehicle.brand} {vehicle.model}",
            "vehicle": vehicle,
            "owner": owner,
        },
    )


# ── Edit ────────────────────────────────────────────────────
@router.get("/{vehicle_id}/edit", response_class=HTMLResponse)
async def edit_view(
    vehicle_id: UUID,
    request: Request,
    db: DbSession,
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
            "categories": VEHICLE_CATEGORIES,
        },
    )


@router.post("/{vehicle_id}")
async def update_submit(
    vehicle_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()

    payload = VehicleUpdate(
        plate_number=(form.get("plate_number") or "").strip() or None,
        brand=(form.get("brand") or "").strip() or None,
        model=(form.get("model") or "").strip() or None,
        year=int(form["year"]) if form.get("year") else None,
        color=(form.get("color") or "").strip() or None,
        category=(form.get("category") or "").strip() or None,
        vin=(form.get("vin") or "").strip() or None,
        engine_number=(form.get("engine_number") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )

    await VehicleService(db).update(vehicle_id, payload, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/vehicles/{vehicle_id}", status_code=303)