from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.customers.repository import CustomerRepository
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import (
    VehicleBrandOut,
    VehicleCreate,
    VehicleDetail,
    VehicleListItem,
    VehicleModelOut,
    VehicleUpdate,
)
from app.modules.vehicles.service import VehicleService

customer_vehicles_router = APIRouter(
    prefix="/customers/{customer_id}/vehicles",
    tags=["vehicles"],
)
vehicles_router = APIRouter(prefix="/vehicles", tags=["vehicles"])


# ── Nested list + create ────────────────────────────────────
@customer_vehicles_router.get("", response_model=Page[VehicleListItem])
async def list_customer_vehicles(
    customer_id: UUID,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.VEHICLE_READ)),
) -> Page[VehicleListItem]:
    if not await CustomerRepository(db).get(customer_id):
        raise NotFoundError("Customer not found")

    stmt = VehicleRepository(db).query(customer_id=customer_id, q=q, category=category)
    rows, meta = await paginate(db, stmt, params)
    return Page[VehicleListItem](
        items=[VehicleListItem.model_validate(r) for r in rows],
        meta=meta,
    )


@customer_vehicles_router.post(
    "", response_model=VehicleDetail, status_code=status.HTTP_201_CREATED
)
async def create_customer_vehicle(
    customer_id: UUID,
    payload: VehicleCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.VEHICLE_WRITE)),
) -> VehicleDetail:
    vehicle = await VehicleService(db).create(customer_id, payload, actor=actor)
    return VehicleDetail.model_validate(vehicle)


# ── Global list ─────────────────────────────────────────────
@vehicles_router.get("", response_model=Page[VehicleListItem])
async def list_vehicles(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.VEHICLE_READ)),
) -> Page[VehicleListItem]:
    stmt = VehicleRepository(db).query(q=q, category=category)
    rows, meta = await paginate(db, stmt, params)
    return Page[VehicleListItem](
        items=[VehicleListItem.model_validate(r) for r in rows],
        meta=meta,
    )


# ── Static paths BEFORE /{vehicle_id} ───────────────────────
@vehicles_router.get("/search", response_model=list[dict])
async def search_vehicles(
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=100),  # ← FIX: required
    customer_id: UUID | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    _=Depends(require_permission(PermissionCode.VEHICLE_READ)),
) -> list[dict]:
    from sqlalchemy import and_, or_, select
    from app.modules.customers.models import Customer
    from app.modules.vehicles.models import Vehicle

    like = f"%{q.strip()}%"
    conds = [
        or_(
            Vehicle.brand.ilike(like),
            Vehicle.model.ilike(like),
            Vehicle.plate_number.ilike(like),
        )
    ]
    if customer_id:
        conds.append(Vehicle.customer_id == customer_id)

    stmt = (
        select(Vehicle)
        .where(and_(*conds))
        .order_by(Vehicle.brand, Vehicle.model)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    cust_ids = {v.customer_id for v in rows if v.customer_id}
    customers: dict = {}
    if cust_ids:
        c_rows = await db.execute(select(Customer).where(Customer.id.in_(cust_ids)))
        customers = {c.id: c for c in c_rows.scalars().all()}

    return [
        {
            "id": str(v.id),
            "label": f"{v.brand} {v.model}" + (f" — {v.plate_number}" if v.plate_number else ""),
            "sublabel": f"{v.year or ''} {v.category or ''}".strip(),
            "customer_id": str(v.customer_id) if v.customer_id else None,
            "customer_name": customers[v.customer_id].name if v.customer_id in customers else None,
        }
        for v in rows
    ]


@vehicles_router.get("/catalog/brands", response_model=list[VehicleBrandOut])
async def list_brands(
    db: DbSession,
    _=Depends(require_permission(PermissionCode.VEHICLE_READ)),
) -> list[VehicleBrandOut]:
    return [
        VehicleBrandOut.model_validate(b)
        for b in await VehicleRepository(db).list_brands()
    ]


@vehicles_router.get("/catalog/models", response_model=list[VehicleModelOut])
async def list_models(
    db: DbSession,
    brand_id: UUID | None = Query(None),
    _=Depends(require_permission(PermissionCode.VEHICLE_READ)),
) -> list[VehicleModelOut]:
    return [
        VehicleModelOut.model_validate(m)
        for m in await VehicleRepository(db).list_models(brand_id)
    ]


# ── Dynamic path LAST ───────────────────────────────────────
@vehicles_router.get("/{vehicle_id}", response_model=VehicleDetail)
async def get_vehicle(
    vehicle_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.VEHICLE_READ)),
) -> VehicleDetail:
    vehicle = await VehicleRepository(db).get(vehicle_id)
    if not vehicle:
        raise NotFoundError("Vehicle not found")
    return VehicleDetail.model_validate(vehicle)


@vehicles_router.patch("/{vehicle_id}", response_model=VehicleDetail)
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.VEHICLE_WRITE)),
) -> VehicleDetail:
    vehicle = await VehicleService(db).update(vehicle_id, payload, actor=actor)
    return VehicleDetail.model_validate(vehicle)