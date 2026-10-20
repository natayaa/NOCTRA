"""Customer REST endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import noload

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.core.pagination import Page, PageParams, page_params, paginate
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.customers.constants import (
    CUSTOMER_SORT_OPTIONS,
    CUSTOMER_STATUSES,
)
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    CustomerContactIn,
    CustomerContactOut,
    CustomerCreate,
    CustomerDetail,
    CustomerListItem,
    CustomerSearchResult,
    CustomerUpdate,
)
from app.modules.customers.service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


def _detail(customer: Customer) -> CustomerDetail:
    """
    Build CustomerDetail from a fully-loaded Customer.

    Contract: caller guarantees `customer.contacts` is loaded
    (via selectin lazy strategy on fetch, or explicit refresh after create).
    """
    return CustomerDetail.model_validate(customer)


# ════════════════════════════════════════════════════════════════
# SEARCH — MUST be declared BEFORE /{customer_id}
# ════════════════════════════════════════════════════════════════

@router.get("/search", response_model=list[CustomerSearchResult])
async def search_customers(
    db: DbSession,
    q: str | None = Query(None, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    include_inactive: bool = Query(False),
    _=Depends(require_permission(PermissionCode.CUSTOMER_READ)),
) -> list[CustomerSearchResult]:
    """Lightweight search for autocomplete pickers."""
    conditions = []
    if q and q.strip():
        like = f"%{q.strip()}%"
        conditions.append(
            or_(
                Customer.name.ilike(like),
                Customer.code.ilike(like),
                Customer.phone.ilike(like),
                Customer.email.ilike(like),
            )
        )
    if not include_inactive:
        conditions.append(Customer.is_active.is_(True))

    stmt = (
        select(Customer)
        .options(noload(Customer.contacts))
        .where(*conditions)
        .order_by(Customer.name)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        CustomerSearchResult(
            id=c.id,
            code=c.code,
            name=c.name,
            phone=c.phone,
            city=c.city,
            label=f"{c.name} ({c.code})",
            sublabel=c.phone or c.email or "",
            is_active=c.is_active,
        )
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
    status_: str | None = Query(None, alias="status", max_length=32),
    is_active: bool | None = Query(None),
    city: str | None = Query(None, max_length=100),
    sort: str = Query(
        "created_desc",
        description=f"One of: {', '.join(CUSTOMER_SORT_OPTIONS)}",
    ),
    _=Depends(require_permission(PermissionCode.CUSTOMER_READ)),
) -> Page[CustomerListItem]:
    if status_ is not None and status_ not in CUSTOMER_STATUSES:
        raise ValidationError(
            f"Invalid status {status_!r}. Choose from: {', '.join(CUSTOMER_STATUSES)}"
        )
    if sort not in CUSTOMER_SORT_OPTIONS:
        raise ValidationError(
            f"Invalid sort {sort!r}. Choose from: {', '.join(CUSTOMER_SORT_OPTIONS)}"
        )

    stmt = CustomerRepository(db).query(
        q=q, status=status_, is_active=is_active, city=city, sort=sort,
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
    return _detail(customer)


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
    return _detail(customer)


@router.patch("/{customer_id}", response_model=CustomerDetail)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.CUSTOMER_WRITE)),
) -> CustomerDetail:
    customer = await CustomerService(db).update(customer_id, payload, actor=actor)
    return _detail(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_customer(
    customer_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.CUSTOMER_DELETE)),
) -> None:
    await CustomerService(db).deactivate(customer_id, actor=actor)


@router.post("/{customer_id}/reactivate", response_model=CustomerDetail)
async def reactivate_customer(
    customer_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.CUSTOMER_WRITE)),
) -> CustomerDetail:
    customer = await CustomerService(db).reactivate(customer_id, actor=actor)
    return _detail(customer)


# ════════════════════════════════════════════════════════════════
# CONTACTS
# ════════════════════════════════════════════════════════════════

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
    contact = await CustomerService(db).add_contact(
        customer_id, payload, actor=actor
    )
    return CustomerContactOut.model_validate(contact)


@router.delete(
    "/{customer_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contact(
    customer_id: UUID,
    contact_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.CUSTOMER_WRITE)),
) -> None:
    """Remove an additional contact. Service verifies ownership."""
    await CustomerService(db).delete_contact(
        customer_id, contact_id, actor=actor
    )