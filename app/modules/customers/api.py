from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    CustomerContactIn,
    CustomerContactOut,
    CustomerCreate,
    CustomerDetail,
    CustomerListItem,
    CustomerUpdate,
)
from app.modules.customers.service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


# ════════════════════════════════════════════════════════════════
# SEARCH — MUST be declared BEFORE /{customer_id}
# ════════════════════════════════════════════════════════════════

@router.get("/search", response_model=list[dict])
async def search_customers(
    db: DbSession,
    q: str = Query("", min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    _=Depends(require_permission(PermissionCode.CUSTOMER_READ)),
) -> list[dict]:
    """Lightweight search for autocomplete pickers."""
    from sqlalchemy import and_, or_, select
    from app.modules.customers.models import Customer

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
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "phone": c.phone,
            "city": c.city,
            "label": f"{c.name} ({c.code})",
            "sublabel": c.phone or c.email or "",
        }
        for c in rows
    ]


# ════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════

@router.get("", response_model=Page[CustomerListItem])
async def list_customers(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    status_: str | None = Query(None, alias="status"),
    is_active: bool | None = Query(None),
    city: str | None = Query(None, max_length=100),
    _=Depends(require_permission(PermissionCode.CUSTOMER_READ)),
) -> Page[CustomerListItem]:
    stmt = CustomerRepository(db).query(
        q=q, status=status_, is_active=is_active, city=city
    )
    rows, meta = await paginate(db, stmt, params)
    return Page[CustomerListItem](
        items=[CustomerListItem.model_validate(r) for r in rows],
        meta=meta,
    )


@router.post("", response_model=CustomerDetail, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.CUSTOMER_WRITE)),
) -> CustomerDetail:
    customer = await CustomerService(db).create(payload, actor=actor)
    return CustomerDetail.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerDetail)
async def get_customer(
    customer_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.CUSTOMER_READ)),
) -> CustomerDetail:
    repo = CustomerRepository(db)
    customer = await repo.get(customer_id)
    if not customer:
        raise NotFoundError("Customer not found")
    detail = CustomerDetail.model_validate(customer)
    detail.contacts = [
        CustomerContactOut.model_validate(c)
        for c in await repo.list_contacts(customer_id)
    ]
    return detail


@router.patch("/{customer_id}", response_model=CustomerDetail)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.CUSTOMER_WRITE)),
) -> CustomerDetail:
    customer = await CustomerService(db).update(customer_id, payload, actor=actor)
    return CustomerDetail.model_validate(customer)


@router.post(
    "/{customer_id}/contacts",
    response_model=CustomerContactOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_contact(
    customer_id: UUID,
    payload: CustomerContactIn,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.CUSTOMER_WRITE)),
) -> CustomerContactOut:
    contact = await CustomerService(db).add_contact(customer_id, payload, actor=actor)
    return CustomerContactOut.model_validate(contact)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_customer(
    customer_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.CUSTOMER_DELETE)),
) -> None:
    await CustomerService(db).deactivate(customer_id, actor=actor)