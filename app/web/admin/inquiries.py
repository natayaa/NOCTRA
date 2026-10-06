"""Admin web routes for the inquiries module.

Handles:
- List with filters (status, assignee, source, color, finish)
- Detail view with workflow actions
- Manual create/edit form
- Status transitions (with server-side validation)
- Assignment
- Photo attachment (URL-based for now; file upload comes in 2c)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.core.deps import DbSession
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.customers.repository import CustomerRepository
from app.modules.inquiries.constants import (
    BUDGET_LABELS,
    BUDGET_RANGES,
    COLOR_FAMILIES,
    COLOR_LABELS,
    FINISH_LABELS,
    FINISH_TYPES,
    INQUIRY_SOURCES,
    INQUIRY_STATUSES,
    PREFERENCE_KEYS,
    SERVICE_INTEREST_LABELS,
    SERVICE_INTERESTS,
    InquiryStatus,
)
from app.modules.inquiries.repository import InquiryRepository
from app.modules.inquiries.schemas import (
    InquiryAssign,
    InquiryCreate,
    InquiryPhotoIn,
    InquiryStatusChange,
    InquiryUpdate,
)
from app.modules.inquiries.service import InquiryService
from app.modules.vehicles.repository import VehicleRepository
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/inquiries", tags=["admin-inquiries"])


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _catalog_context() -> dict:
    """Dropdown options + label maps for templates."""
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


async def _load_assignees(db) -> list[User]:
    """Users eligible to be assigned an inquiry."""
    stmt = (
        select(User)
        .where(User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return list((await db.execute(stmt)).scalars().all())


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
    assigned_to_id: UUID | None = Query(None),
    source: str | None = Query(None),
    color_family: str | None = Query(None),
    finish_preference: str | None = Query(None),
    only_open: bool = Query(False),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = InquiryRepository(db).query(
        q=q,
        status=status_,
        assigned_to_id=assigned_to_id,
        source=source,
        color_family=color_family,
        finish_preference=finish_preference,
        only_open=only_open,
    )
    rows, meta = await paginate(db, stmt, params)

    # Pre-fetch names for display (avoid N+1 in template)
    customer_ids = {r.customer_id for r in rows if r.customer_id}
    vehicle_ids = {r.vehicle_id for r in rows if r.vehicle_id}
    assignee_ids = {r.assigned_to_id for r in rows if r.assigned_to_id}

    customers_by_id: dict = {}
    vehicles_by_id: dict = {}
    users_by_id: dict = {}

    if customer_ids:
        from app.modules.customers.models import Customer
        rows_c = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        customers_by_id = {c.id: c for c in rows_c.scalars().all()}

    if vehicle_ids:
        from app.modules.vehicles.models import Vehicle
        rows_v = await db.execute(select(Vehicle).where(Vehicle.id.in_(vehicle_ids)))
        vehicles_by_id = {v.id: v for v in rows_v.scalars().all()}

    if assignee_ids:
        rows_u = await db.execute(select(User).where(User.id.in_(assignee_ids)))
        users_by_id = {u.id: u for u in rows_u.scalars().all()}

    return templates.render(
        request,
        "admin/inquiries/list.html",
        {
            "title": "Inquiries",
            "inquiries": rows,
            "page_meta": meta,
            "customers_by_id": customers_by_id,
            "vehicles_by_id": vehicles_by_id,
            "users_by_id": users_by_id,
            "assignees": await _load_assignees(db),
            "q": q or "",
            "status_filter": status_ or "",
            "assigned_filter": assigned_to_id,
            "source_filter": source or "",
            "color_filter": color_family or "",
            "finish_filter": finish_preference or "",
            "only_open": only_open,
            **_catalog_context(),
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
    vehicle_id: UUID | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    preselected_customer = None
    preselected_vehicle = None

    if customer_id:
        preselected_customer = await CustomerRepository(db).get(customer_id)
    if vehicle_id:
        preselected_vehicle = await VehicleRepository(db).get(vehicle_id)
        if preselected_vehicle and not preselected_customer:
            preselected_customer = await CustomerRepository(db).get(
                preselected_vehicle.customer_id
            )

    return templates.render(
        request,
        "admin/inquiries/form.html",
        {
            "title": "New Inquiry",
            "mode": "create",
            "inquiry": None,
            "preselected_customer": preselected_customer,
            "preselected_vehicle": preselected_vehicle,
            **_catalog_context(),
        },
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()

    payload = InquiryCreate(
        customer_id=(UUID(str(form["customer_id"])) if form.get("customer_id") else None),
        vehicle_id=(UUID(str(form["vehicle_id"])) if form.get("vehicle_id") else None),
        service_interest=(form.get("service_interest") or "").strip() or None,
        description=(form.get("description") or "").strip(),
        color_preference=(form.get("color_preference") or "").strip() or None,
        color_family=(form.get("color_family") or "").strip() or None,
        finish_preference=(form.get("finish_preference") or "").strip() or None,
        has_custom_graphics=form.get("has_custom_graphics") == "true",
        preferences=_collect_preferences(form),
        source=(form.get("source") or "ADMIN").strip(),
        budget_range=(form.get("budget_range") or "").strip() or None,
        desired_date=(form.get("desired_date") or "").strip() or None,
        follow_up_date=(form.get("follow_up_date") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )

    try:
        inquiry = await InquiryService(db).create(payload, actor=current)
    except AppError as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/inquiries/form.html",
            {
                "title": "New Inquiry",
                "mode": "create",
                "inquiry": None,
                "preselected_customer": None,
                "preselected_vehicle": None,
                "error": exc.message,
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=exc.status_code,
        )

    await db.commit()
    return RedirectResponse(url=f"/admin/inquiries/{inquiry.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{inquiry_id}", response_class=HTMLResponse)
async def detail_view(
    inquiry_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
) -> HTMLResponse:
    repo = InquiryRepository(db)
    inquiry = await repo.get(inquiry_id)
    if not inquiry:
        raise NotFoundError("Inquiry not found")

    customer = (
        await CustomerRepository(db).get(inquiry.customer_id)
        if inquiry.customer_id
        else None
    )
    vehicle = (
        await VehicleRepository(db).get(inquiry.vehicle_id)
        if inquiry.vehicle_id
        else None
    )
    assignee = None
    if inquiry.assigned_to_id:
        from app.modules.auth.models import User as UserModel
        assignee = await db.get(UserModel, inquiry.assigned_to_id)

    photos = await repo.list_photos(inquiry_id)

    # Compute next allowed statuses
    from app.modules.inquiries.constants import ALLOWED_TRANSITIONS
    next_statuses = ALLOWED_TRANSITIONS.get(inquiry.status, frozenset())

    return templates.render(
        request,
        "admin/inquiries/detail.html",
        {
            "title": inquiry.code,
            "inquiry": inquiry,
            "customer": customer,
            "vehicle": vehicle,
            "assignee": assignee,
            "photos": photos,
            "next_statuses": sorted(next_statuses),
            "assignees": await _load_assignees(db),
            **_catalog_context(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT
# ════════════════════════════════════════════════════════════════

@router.get("/{inquiry_id}/edit", response_class=HTMLResponse)
async def edit_view(
    inquiry_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
) -> HTMLResponse:
    inquiry = await InquiryRepository(db).get(inquiry_id)
    if not inquiry:
        raise NotFoundError("Inquiry not found")

    customer = (
        await CustomerRepository(db).get(inquiry.customer_id)
        if inquiry.customer_id
        else None
    )
    vehicle = (
        await VehicleRepository(db).get(inquiry.vehicle_id)
        if inquiry.vehicle_id
        else None
    )

    return templates.render(
        request,
        "admin/inquiries/form.html",
        {
            "title": f"Edit {inquiry.code}",
            "mode": "edit",
            "inquiry": inquiry,
            "preselected_customer": customer,
            "preselected_vehicle": vehicle,
            **_catalog_context(),
        },
    )


@router.post("/{inquiry_id}")
async def update_submit(
    inquiry_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()

    payload = InquiryUpdate(
        customer_id=(UUID(str(form["customer_id"])) if form.get("customer_id") else None),
        vehicle_id=(UUID(str(form["vehicle_id"])) if form.get("vehicle_id") else None),
        service_interest=(form.get("service_interest") or "").strip() or None,
        description=(form.get("description") or "").strip() or None,
        color_preference=(form.get("color_preference") or "").strip() or None,
        color_family=(form.get("color_family") or "").strip() or None,
        finish_preference=(form.get("finish_preference") or "").strip() or None,
        has_custom_graphics=form.get("has_custom_graphics") == "true",
        preferences=_collect_preferences(form),
        budget_range=(form.get("budget_range") or "").strip() or None,
        desired_date=(form.get("desired_date") or "").strip() or None,
        follow_up_date=(form.get("follow_up_date") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )

    try:
        await InquiryService(db).update(inquiry_id, payload, actor=current)
    except AppError as exc:
        await db.rollback()
        inquiry = await InquiryRepository(db).get(inquiry_id)
        return templates.render(
            request,
            "admin/inquiries/form.html",
            {
                "title": f"Edit {inquiry.code if inquiry else 'Inquiry'}",
                "mode": "edit",
                "inquiry": inquiry,
                "preselected_customer": None,
                "preselected_vehicle": None,
                "error": exc.message,
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=exc.status_code,
        )

    await db.commit()
    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# WORKFLOW ACTIONS
# ════════════════════════════════════════════════════════════════

@router.post("/{inquiry_id}/status")
async def change_status_submit(
    inquiry_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()
    target = (form.get("status") or "").strip()
    closing_note = (form.get("closing_note") or "").strip() or None

    try:
        await InquiryService(db).change_status(
            inquiry_id,
            InquiryStatusChange(status=target, closing_note=closing_note),
            actor=current,
        )
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/inquiries/{inquiry_id}?error={exc.code}",
            status_code=303,
        )

    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


@router.post("/{inquiry_id}/assign")
async def assign_submit(
    inquiry_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()
    raw = (form.get("assigned_to_id") or "").strip()
    assignee_id = UUID(raw) if raw else None

    try:
        await InquiryService(db).assign(inquiry_id, assignee_id, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/inquiries/{inquiry_id}?error={exc.code}",
            status_code=303,
        )

    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


@router.post("/{inquiry_id}/photos")
async def add_photo_submit(
    inquiry_id: UUID,
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    """Add a photo by URL. File upload lands in Phase 2c."""
    form = await request.form()

    payload = InquiryPhotoIn(
        file_path=(form.get("file_path") or "").strip(),
        file_name=(form.get("file_name") or "").strip() or None,
        caption=(form.get("caption") or "").strip() or None,
        is_primary=form.get("is_primary") == "true",
    )

    try:
        await InquiryService(db).add_photo(inquiry_id, payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()

    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# PREFERENCES HELPER
# ════════════════════════════════════════════════════════════════

def _collect_preferences(form) -> dict | None:
    """Gather the `pref_*` form fields into a JSONB-ready dict."""
    prefs: dict = {}
    for key_meta in PREFERENCE_KEYS:
        field = f"pref_{key_meta['key']}"
        raw = form.get(field)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue

        kind = key_meta["type"]
        if kind == "bool":
            prefs[key_meta["key"]] = raw == "true"
        elif kind == "list":
            prefs[key_meta["key"]] = [s.strip() for s in str(raw).split(",") if s.strip()]
        else:
            prefs[key_meta["key"]] = str(raw).strip()

    return prefs or None