"""Admin web routes for the inquiries module."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy import select
from urllib.parse import quote
from pydantic import ValidationError as PydanticValidationError

from app.core.deps import DbSession
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.customers.repository import CustomerRepository
from app.modules.inquiries.constants import (
    BUDGET_LABELS, BUDGET_RANGES,
    COLOR_FAMILIES, COLOR_LABELS, COLOR_SWATCH,
    FINISH_LABELS, FINISH_TYPES,
    INQUIRY_SOURCES, INQUIRY_STATUSES,
    PREFERENCE_KEYS,
    SERVICE_INTEREST_LABELS, SERVICE_INTERESTS,
    SOURCE_LABELS, STATUS_TONE,
    InquiryStatus,
)
from app.modules.inquiries.repository import InquiryRepository, SORT_OPTIONS
from app.modules.inquiries.schemas import (
    InquiryAssign, InquiryCreate, InquiryPhotoIn,
    InquiryStatusChange, InquiryUpdate,
)
from app.modules.inquiries.service import InquiryService
from app.modules.vehicles.repository import VehicleRepository
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/inquiries", tags=["admin-inquiries"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _catalog_context() -> dict:
    return {
        "statuses": INQUIRY_STATUSES,
        "status_labels": {s: s for s in INQUIRY_STATUSES},  # placeholder if labels added
        "status_tone": STATUS_TONE,
        "sources": INQUIRY_SOURCES,
        "source_labels": SOURCE_LABELS,
        "services": SERVICE_INTERESTS,
        "service_labels": SERVICE_INTEREST_LABELS,
        "finishes": FINISH_TYPES,
        "finish_labels": FINISH_LABELS,
        "color_families": COLOR_FAMILIES,
        "color_labels": COLOR_LABELS,
        "color_swatch": COLOR_SWATCH,
        "budget_ranges": BUDGET_RANGES,
        "budget_labels": BUDGET_LABELS,
        "preference_keys": PREFERENCE_KEYS,
        "sort_options": SORT_OPTIONS,
    }


async def _load_assignees(db) -> list[User]:
    stmt = select(User).where(User.is_active.is_(True)).order_by(User.full_name)
    return list((await db.execute(stmt)).scalars().all())


def _form_error(exc: Exception) -> str:
    msg = getattr(exc, "message", None) or str(exc)
    return msg.strip() or "Invalid input"


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
    sort: str = Query("created_desc"),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.modules.customers.models import Customer
    from app.modules.vehicles.models import Vehicle
    from app.modules.auth.models import User

    repo = InquiryRepository(db)
    stmt = repo.query(
        q=q, status=status_, assigned_to_id=assigned_to_id,
        source=source, color_family=color_family,
        finish_preference=finish_preference,
        only_open=only_open, sort=sort if sort in SORT_OPTIONS else "created_desc",
    )
    rows, meta = await paginate(db, stmt, params)

    customer_ids = {r.customer_id for r in rows if r.customer_id}
    vehicle_ids = {r.vehicle_id for r in rows if r.vehicle_id}
    assignee_ids = {r.assigned_to_id for r in rows if r.assigned_to_id}

    customers_by_id = {}
    vehicles_by_id = {}
    users_by_id = {}
    if customer_ids:
        c_rows = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        customers_by_id = {c.id: c for c in c_rows.scalars().all()}
    if vehicle_ids:
        v_rows = await db.execute(select(Vehicle).where(Vehicle.id.in_(vehicle_ids)))
        vehicles_by_id = {v.id: v for v in v_rows.scalars().all()}
    if assignee_ids:
        u_rows = await db.execute(select(User).where(User.id.in_(assignee_ids)))
        users_by_id = {u.id: u for u in u_rows.scalars().all()}

    stats = await repo.stats(assigned_to_id=assigned_to_id)

    # Build a query-string helper for chips that preserves active filters
    def _qs(**overrides) -> str:
        from urllib.parse import urlencode
        base = {
            "q": q or "", "status": status_ or "",
            "assigned_to_id": str(assigned_to_id) if assigned_to_id else "",
            "source": source or "", "color_family": color_family or "",
            "finish_preference": finish_preference or "",
            "only_open": "true" if only_open else "",
            "sort": sort,
        }
        base.update({k: ("" if v is None else v) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/inquiries/list.html",
        {
            "title": "Inquiries",
            "inquiries": rows,
            "page_meta": meta,
            "stats": stats,
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
            "sort": sort,
            "qs": _qs,
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
    assigned_to_id: UUID | None = Query(None),
    source: str | None = Query(None),
    color_family: str | None = Query(None),
    finish_preference: str | None = Query(None),
    only_open: bool = Query(False),
    current=Depends(get_current_user),
):
    repo = InquiryRepository(db)
    stmt = repo.query(
        q=q, status=status_, assigned_to_id=assigned_to_id,
        source=source, color_family=color_family,
        finish_preference=finish_preference, only_open=only_open,
    )
    rows = (await db.execute(stmt)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "code", "status", "source", "service_interest",
        "color_preference", "color_family", "finish_preference",
        "has_custom_graphics", "budget_range",
        "desired_date", "follow_up_date", "created_at", "description",
    ])
    for r in rows:
        writer.writerow([
            r.code, r.status, r.source, r.service_interest or "",
            r.color_preference or "", r.color_family or "",
            r.finish_preference or "", "yes" if r.has_custom_graphics else "no",
            r.budget_range or "",
            r.desired_date.isoformat() if r.desired_date else "",
            r.follow_up_date.isoformat() if r.follow_up_date else "",
            r.created_at.isoformat() if r.created_at else "",
            (r.description or "").replace("\n", " "),
        ])

    buf.seek(0)
    filename = f"inquiries-{datetime.utcnow().strftime('%Y%m%d-%H%M')}.csv"
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
            preselected_customer = await CustomerRepository(db).get(preselected_vehicle.customer_id)

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
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
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
    except _FORM_ERRORS as exc:
        await db.rollback()
        return templates.render(
            request, "admin/inquiries/form.html",
            {
                "title": "New Inquiry", "mode": "create", "inquiry": None,
                "preselected_customer": None, "preselected_vehicle": None,
                "error": _form_error(exc),
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=getattr(exc, "status_code", 400),
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
    error: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.modules.customers.models import Customer
    from app.modules.vehicles.models import Vehicle
    from app.modules.auth.models import User as UserModel
    from app.modules.inquiries.constants import ALLOWED_TRANSITIONS
    from app.modules.projects.models import Project

    repo = InquiryRepository(db)
    inquiry = await repo.get(inquiry_id)
    if not inquiry:
        raise NotFoundError("Inquiry not found")

    customer = await db.get(Customer, inquiry.customer_id) if inquiry.customer_id else None
    vehicle = await db.get(Vehicle, inquiry.vehicle_id) if inquiry.vehicle_id else None
    assignee = await db.get(UserModel, inquiry.assigned_to_id) if inquiry.assigned_to_id else None
    photos = await repo.list_photos(inquiry_id)
    next_statuses = ALLOWED_TRANSITIONS.get(inquiry.status, frozenset())

    project = None
    if inquiry.status == InquiryStatus.CONVERTED.value:
        project = (
            await db.execute(select(Project).where(Project.inquiry_id == inquiry.id))
        ).scalar_one_or_none()

    timeline = await InquiryService(db).get_timeline(inquiry_id, limit=25)

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
            "project": project,
            "timeline": timeline,
            "next_statuses": sorted(next_statuses),
            "assignees": await _load_assignees(db),
            "error": error,
            **_catalog_context(),
        },
    )


# ════════════════════════════════════════════════════════════════
# CONVERT
# ════════════════════════════════════════════════════════════════

@router.post("/{inquiry_id}/convert")
async def convert_submit(
    inquiry_id: UUID, request: Request, db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()
    raw_price = (form.get("quoted_price") or "").strip()
    try:
        quoted_price = float(raw_price) if raw_price else None
    except ValueError:
        quoted_price = None

    try:
        _inquiry, project = await InquiryService(db).convert_to_project(
            inquiry_id, actor=current,
            quoted_price=quoted_price, approved_price=quoted_price,
        )
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/inquiries/{inquiry_id}?error={quote(exc.message, safe='')}",
            status_code=303,
        )

    return RedirectResponse(url=f"/admin/projects/{project.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# EDIT
# ════════════════════════════════════════════════════════════════

@router.get("/{inquiry_id}/edit", response_class=HTMLResponse)
async def edit_view(inquiry_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)):
    inquiry = await InquiryRepository(db).get(inquiry_id)
    if not inquiry:
        raise NotFoundError("Inquiry not found")

    customer = await CustomerRepository(db).get(inquiry.customer_id) if inquiry.customer_id else None
    vehicle = await VehicleRepository(db).get(inquiry.vehicle_id) if inquiry.vehicle_id else None

    return templates.render(
        request, "admin/inquiries/form.html",
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
async def update_submit(inquiry_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)):
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
    except _FORM_ERRORS as exc:
        await db.rollback()
        inquiry = await InquiryRepository(db).get(inquiry_id)
        return templates.render(
            request, "admin/inquiries/form.html",
            {
                "title": f"Edit {inquiry.code if inquiry else 'Inquiry'}",
                "mode": "edit", "inquiry": inquiry,
                "preselected_customer": None, "preselected_vehicle": None,
                "error": _form_error(exc),
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=getattr(exc, "status_code", 400),
        )

    await db.commit()
    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# WORKFLOW ACTIONS
# ════════════════════════════════════════════════════════════════

@router.post("/{inquiry_id}/status")
async def change_status_submit(inquiry_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)):
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
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/inquiries/{inquiry_id}?error={msg}", status_code=303,
        )

    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


@router.post("/{inquiry_id}/assign")
async def assign_submit(inquiry_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()
    raw = (form.get("assigned_to_id") or "").strip()
    assignee_id = UUID(raw) if raw else None

    try:
        await InquiryService(db).assign(inquiry_id, assignee_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/inquiries/{inquiry_id}?error={msg}", status_code=303,
        )

    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


@router.post("/{inquiry_id}/photos")
async def add_photo_submit(inquiry_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)):
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
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/inquiries/{inquiry_id}?error={msg}", status_code=303,
        )
    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


@router.post("/{inquiry_id}/photos/{photo_id}/delete")
async def delete_photo_submit(
    inquiry_id: UUID, photo_id: UUID, db: DbSession,
    current=Depends(get_current_user),
):
    try:
        await InquiryService(db).delete_photo(photo_id, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/inquiries/{inquiry_id}?error={quote(exc.message, safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/inquiries/{inquiry_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# PREFERENCES HELPER
# ════════════════════════════════════════════════════════════════

def _collect_preferences(form) -> dict | None:
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