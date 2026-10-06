"""Inquiry REST endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.inquiries.constants import (
    COLOR_FAMILIES,
    FINISH_TYPES,
    INQUIRY_SOURCES,
    INQUIRY_STATUSES,
    PREFERENCE_KEYS,
)
from app.modules.inquiries.repository import InquiryRepository
from app.modules.inquiries.schemas import (
    InquiryAssign,
    InquiryCreate,
    InquiryDetail,
    InquiryListItem,
    InquiryPhotoIn,
    InquiryPhotoOut,
    InquiryStatusChange,
    InquiryUpdate,
)
from app.modules.inquiries.service import InquiryService

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


# ════════════════════════════════════════════════════════════════
# CATALOG — static reference data for the UI
# ════════════════════════════════════════════════════════════════

@router.get("/catalog")
async def catalog() -> dict:
    """Return all dropdown options and label mappings the UI needs."""
    from app.modules.inquiries.constants import (
        BUDGET_LABELS,
        BUDGET_RANGES,
        COLOR_LABELS,
        FINISH_LABELS,
        SERVICE_INTERESTS,
        SERVICE_INTEREST_LABELS,
    )
    return {
        "statuses": INQUIRY_STATUSES,
        "sources": INQUIRY_SOURCES,
        "services": SERVICE_INTERESTS,
        "service_labels": SERVICE_INTEREST_LABELS,
        "finishes": FINISH_TYPES,
        "finish_labels": FINISH_LABELS,
        "color_families": COLOR_FAMILIES,
        "color_labels": COLOR_LABELS,
        "budget_ranges": BUDGET_RANGES,
        "budget_labels": BUDGET_LABELS,
        "preference_keys": PREFERENCE_KEYS,
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
    _=Depends(require_permission(PermissionCode.INQUIRY_READ)),
) -> Page[InquiryListItem]:
    stmt = InquiryRepository(db).query(
        q=q,
        status=status_,
        assigned_to_id=assigned_to_id,
        customer_id=customer_id,
        source=source,
        color_family=color_family,
        finish_preference=finish_preference,
        only_open=only_open,
    )
    rows, meta = await paginate(db, stmt, params)
    return Page[InquiryListItem](
        items=[InquiryListItem.model_validate(r) for r in rows],
        meta=meta,
    )


@router.post("", response_model=InquiryDetail, status_code=status.HTTP_201_CREATED)
async def create_inquiry(
    payload: InquiryCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_CREATE)),
) -> InquiryDetail:
    inquiry = await InquiryService(db).create(payload, actor=actor)
    return InquiryDetail.model_validate(inquiry)


@router.get("/{inquiry_id}", response_model=InquiryDetail)
async def get_inquiry(
    inquiry_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.INQUIRY_READ)),
) -> InquiryDetail:
    repo = InquiryRepository(db)
    inquiry = await repo.get(inquiry_id)
    if not inquiry:
        raise NotFoundError("Inquiry not found")
    detail = InquiryDetail.model_validate(inquiry)
    detail.photos = [
        InquiryPhotoOut.model_validate(p)
        for p in await repo.list_photos(inquiry_id)
    ]
    return detail


@router.patch("/{inquiry_id}", response_model=InquiryDetail)
async def update_inquiry(
    inquiry_id: UUID,
    payload: InquiryUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_UPDATE)),
) -> InquiryDetail:
    inquiry = await InquiryService(db).update(inquiry_id, payload, actor=actor)
    return InquiryDetail.model_validate(inquiry)


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
    return InquiryDetail.model_validate(inquiry)


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
    return InquiryDetail.model_validate(inquiry)


@router.post("/{inquiry_id}/contacted", response_model=InquiryDetail)
async def mark_contacted(
    inquiry_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INQUIRY_UPDATE)),
) -> InquiryDetail:
    inquiry = await InquiryService(db).mark_contacted(inquiry_id, actor=actor)
    return InquiryDetail.model_validate(inquiry)


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