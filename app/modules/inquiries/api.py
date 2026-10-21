"""Inquiry REST endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.core.pagination import Page, PageParams, page_params, paginate
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.inquiries.constants import (
    COLOR_FAMILIES,
    FINISH_TYPES,
    INQUIRY_SOURCES,
    INQUIRY_STATUSES,
    PREFERENCE_KEYS,
    SORT_OPTIONS,
)
from app.modules.inquiries.repository import InquiryRepository
from app.modules.inquiries.schemas import (
    InquiryAssign,
    InquiryConvert,
    InquiryCreate,
    InquiryDetail,
    InquiryListItem,
    InquiryPhotoIn,
    InquiryPhotoOut,
    InquiryStatusChange,
    InquiryTimelineEntry,
    InquiryUpdate,
)
from app.modules.inquiries.service import InquiryService

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


def _detail(inquiry) -> InquiryDetail:
    """Build InquiryDetail from a fully-loaded Inquiry (photos via selectin)."""
    return InquiryDetail.model_validate(inquiry)


def _vehicle_label(v) -> str | None:
    """Best-effort label for a vehicle; resilient to unknown model fields."""
    if v is None:
        return None
    for attr in ("license_plate", "plate_number", "plate"):
        val = getattr(v, attr, None)
        if val:
            return str(val)
    return None


# ════════════════════════════════════════════════════════════════
# CATALOG
# ════════════════════════════════════════════════════════════════

@router.get("/catalog")
async def catalog() -> dict:
    from app.modules.inquiries.constants import (
        BUDGET_LABELS,
        BUDGET_RANGES,
        COLOR_LABELS,
        FINISH_LABELS,
        INQUIRY_STATUS_LABELS,
        SERVICE_INTERESTS,
        SERVICE_INTEREST_LABELS,
        SOURCE_LABELS,
    )
    return {
        "statuses": INQUIRY_STATUSES,
        "status_labels": INQUIRY_STATUS_LABELS,
        "sources": INQUIRY_SOURCES,
        "source_labels": SOURCE_LABELS,
        "services": SERVICE_INTERESTS,
        "service_labels": SERVICE_INTEREST_LABELS,
        "finishes": FINISH_TYPES,
        "finish_labels": FINISH_LABELS,
        "color_families": COLOR_FAMILIES,
        "color_labels": COLOR_LABELS,
        "budget_ranges": BUDGET_RANGES,
        "budget_labels": BUDGET_LABELS,
        "preference_keys": PREFERENCE_KEYS,
        "sort_options": SORT_OPTIONS,
    }


# ════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════

@router.get("", response_model=Page[InquiryListItem])
async def list_inquiries(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    status_: str | None = Query(None, alias="status"),
    assigned_to_id: UUID | None = Query(None),
    customer_id: UUID | None = Query(None),
    source: str | None = Query(None),
    color_family: str | None = Query(None),
    finish_preference: str | None = Query(None),
    only_open: bool = Query(False),
    sort: str = Query(
        "created_desc",
        description=f"One of: {', '.join(SORT_OPTIONS)}",
    ),
    _=Depends(require_permission(PermissionCode.INQUIRY_READ)),
) -> Page[InquiryListItem]:
    # Validate enum-valued query params — silent empty result is confusing.
    if status_ is not None and status_ not in INQUIRY_STATUSES:
        raise ValidationError(
            f"Invalid status {status_!r}. Choose from: {', '.join(INQUIRY_STATUSES)}"
        )
    if source is not None and source not in INQUIRY_SOURCES:
        raise ValidationError(
            f"Invalid source {source!r}. Choose from: {', '.join(INQUIRY_SOURCES)}"
        )
    if color_family is not None and color_family not in COLOR_FAMILIES:
        raise ValidationError(
            f"Invalid color_family {color_family!r}. "
            f"Choose from: {', '.join(COLOR_FAMILIES)}"
        )
    if finish_preference is not None and finish_preference not in FINISH_TYPES:
        raise ValidationError(
            f"Invalid finish_preference {finish_preference!r}. "
            f"Choose from: {', '.join(FINISH_TYPES)}"
        )
    if sort not in SORT_OPTIONS:
        raise ValidationError(
            f"Invalid sort {sort!r}. Choose from: {', '.join(SORT_OPTIONS)}"
        )

    stmt = InquiryRepository(db).query(
        q=q,
        status=status_,
        assigned_to_id=assigned_to_id,
        customer_id=customer_id,
        source=source,
        color_family=color_family,
        finish_preference=finish_preference,
        only_open=only_open,
        sort=sort,
    )
    rows, meta = await paginate(db, stmt, params)

    # Batch-fetch enrichment fields — 3 queries total for the whole page.
    from app.modules.auth.models import User
    from app.modules.customers.models import Customer
    from app.modules.vehicles.models import Vehicle

    customer_ids = {r.customer_id for r in rows if r.customer_id}
    vehicle_ids = {r.vehicle_id for r in rows if r.vehicle_id}
    user_ids = {r.assigned_to_id for r in rows if r.assigned_to_id}

    customers: dict = {}
    if customer_ids:
        c_rows = await db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        customers = {cid: name for cid, name in c_rows.all()}

    vehicles: dict = {}
    if vehicle_ids:
        v_rows = await db.execute(
            select(Vehicle).where(Vehicle.id.in_(vehicle_ids))
        )
        vehicles = {v.id: v for v in v_rows.scalars().all()}

    users: dict = {}
    if user_ids:
        u_rows = await db.execute(
            select(User.id, User.full_name).where(User.id.in_(user_ids))
        )
        users = {uid: name for uid, name in u_rows.all()}

    items: list[InquiryListItem] = []
    for r in rows:
        item = InquiryListItem.model_validate(r)
        if r.customer_id in customers:
            item.customer_name = customers[r.customer_id]
        if r.vehicle_id in vehicles:
            item.vehicle_label = _vehicle_label(vehicles[r.vehicle_id])
        if r.assigned_to_id in users:
            item.assigned_to_name = users[r.assigned_to_id]
        items.append(item)

    return Page[InquiryListItem](items=items, meta=meta)


@router.post("", response_model=InquiryDetail, status_code=status.HTTP_201_CREATED)
async def create_inquiry(
    payload: InquiryCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_CREATE)),
) -> InquiryDetail:
    inquiry = await InquiryService(db).create(payload, actor=actor)
    return _detail(inquiry)


@router.get("/{inquiry_id}", response_model=InquiryDetail)
async def get_inquiry(
    inquiry_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.INQUIRY_READ)),
) -> InquiryDetail:
    inquiry = await InquiryRepository(db).get(inquiry_id)
    if not inquiry:
        raise NotFoundError("Inquiry not found")
    return _detail(inquiry)


@router.patch("/{inquiry_id}", response_model=InquiryDetail)
async def update_inquiry(
    inquiry_id: UUID,
    payload: InquiryUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_UPDATE)),
) -> InquiryDetail:
    inquiry = await InquiryService(db).update(inquiry_id, payload, actor=actor)
    return _detail(inquiry)


# ════════════════════════════════════════════════════════════════
# WORKFLOW ACTIONS
# ════════════════════════════════════════════════════════════════

@router.post("/{inquiry_id}/assign", response_model=InquiryDetail)
async def assign_inquiry(
    inquiry_id: UUID,
    payload: InquiryAssign,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_ASSIGN)),
) -> InquiryDetail:
    inquiry = await InquiryService(db).assign(
        inquiry_id, payload.assigned_to_id, actor=actor
    )
    return _detail(inquiry)


@router.post("/{inquiry_id}/status", response_model=InquiryDetail)
async def change_status(
    inquiry_id: UUID,
    payload: InquiryStatusChange,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_UPDATE)),
) -> InquiryDetail:
    inquiry = await InquiryService(db).change_status(
        inquiry_id, payload, actor=actor
    )
    return _detail(inquiry)


@router.post("/{inquiry_id}/contacted", response_model=InquiryDetail)
async def mark_contacted(
    inquiry_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_UPDATE)),
) -> InquiryDetail:
    inquiry = await InquiryService(db).mark_contacted(inquiry_id, actor=actor)
    return _detail(inquiry)


@router.post("/{inquiry_id}/convert", response_model=InquiryDetail)
async def convert_to_project(
    inquiry_id: UUID,
    payload: InquiryConvert,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_UPDATE)),
) -> InquiryDetail:
    inquiry, _project = await InquiryService(db).convert_to_project(
        inquiry_id,
        actor=actor,
        quoted_price=payload.quoted_price,
        approved_price=payload.approved_price,
        closing_note=payload.closing_note,
    )
    return _detail(inquiry)


@router.get(
    "/{inquiry_id}/timeline",
    response_model=Page[InquiryTimelineEntry],
)
async def get_timeline(
    inquiry_id: UUID,
    db: DbSession,
    params: PageParams = Depends(page_params),
    _=Depends(require_permission(PermissionCode.INQUIRY_READ)),
) -> Page[InquiryTimelineEntry]:
    items, meta = await InquiryService(db).get_timeline(inquiry_id, params)
    return Page[InquiryTimelineEntry](
        items=[InquiryTimelineEntry.model_validate(r) for r in items],
        meta=meta,
    )


# ════════════════════════════════════════════════════════════════
# PHOTOS
# ════════════════════════════════════════════════════════════════

@router.post(
    "/{inquiry_id}/photos",
    response_model=InquiryPhotoOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_photo(
    inquiry_id: UUID,
    payload: InquiryPhotoIn,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_UPDATE)),
) -> InquiryPhotoOut:
    photo = await InquiryService(db).add_photo(inquiry_id, payload, actor=actor)
    return InquiryPhotoOut.model_validate(photo)


@router.delete(
    "/{inquiry_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_photo(
    inquiry_id: UUID,
    photo_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_UPDATE)),
) -> None:
    """Delete a photo. Service verifies the photo belongs to this inquiry."""
    await InquiryService(db).delete_photo(inquiry_id, photo_id, actor=actor)