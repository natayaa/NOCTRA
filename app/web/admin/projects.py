"""Admin web routes for projects — the costing cockpit."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from urllib.parse import quote, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.customers.repository import CustomerRepository
from app.modules.inventory.repository import MaterialRepository
from app.modules.projects.constants import (
    ALLOWED_PROJECT_TRANSITIONS,
    COST_CATEGORIES,
    COST_CATEGORY_LABELS,
    PROJECT_ITEM_STATUS_LABELS,
    PROJECT_ITEM_STATUS_TONE,
    PROJECT_SORT_OPTIONS,
    PROJECT_STATUS_LABELS,
    PROJECT_STATUS_TONE,
    PROJECT_STATUSES,
)
from app.modules.finance.constants import PAYMENT_METHOD_LABELS
from app.modules.inquiries.constants import INQUIRY_STATUS_LABELS
from app.modules.projects.repository import (
    EmployeeRepository,
    ProjectRepository,
)
from app.modules.projects.schemas import (
    ProjectCreate,
    ProjectItemCreate,
    ProjectItemUpdate,
    ProjectStatusChange,
    ProjectUpdate,
)
from app.modules.projects.service import CostingService, ProjectService
from app.modules.vehicles.repository import VehicleRepository
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/projects", tags=["admin-projects"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _catalog() -> dict:
    return {
        "statuses": PROJECT_STATUSES,
        "status_labels": PROJECT_STATUS_LABELS,
        "status_tone": PROJECT_STATUS_TONE,
        "item_status_labels": PROJECT_ITEM_STATUS_LABELS,
        "item_status_tone": PROJECT_ITEM_STATUS_TONE,
        "sort_options": PROJECT_SORT_OPTIONS,
        "cost_categories": COST_CATEGORIES,
        "cost_category_labels": COST_CATEGORY_LABELS,
    }


async def _load_assignees(db) -> list[User]:
    return list(
        (await db.execute(
            select(User).where(User.is_active.is_(True)).order_by(User.full_name)
        )).scalars().all()
    )


def _form_error(exc: Exception) -> str:
    return (getattr(exc, "message", None) or str(exc) or "Invalid input").strip()


def _redirect_with_error(project_id: UUID, exc: Exception) -> RedirectResponse:
    return RedirectResponse(
        url=f"/admin/projects/{project_id}?error="
            f"{quote(_form_error(exc), safe='')}",
        status_code=303,
    )


def _safe_int(raw, default: int = 0) -> int:
    if raw is None:
        return default
    s = str(raw).strip()
    if not s:
        return default
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


def _safe_float(raw) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _safe_date(raw) -> date | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _safe_uuid(raw) -> UUID | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return UUID(s)
    except (ValueError, TypeError):
        return None


# ════════════════════════════════════════════════════════════════
# LIST + EXPORT
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    status_: str | None = Query(None, alias="status"),
    customer_id: UUID | None = Query(None),
    assigned_lead_id: UUID | None = Query(None),
    only_open: bool = Query(False),
    sort: str = Query("created_desc"),
    _=read(PermissionCode.PROJECT_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.modules.customers.models import Customer

    repo = ProjectRepository(db)
    stmt = repo.query(
        q=q, status=status_, customer_id=customer_id,
        assigned_lead_id=assigned_lead_id, only_open=only_open,
        sort=sort if sort in PROJECT_SORT_OPTIONS else "created_desc",
    )
    rows, meta = await paginate(db, stmt, params)

    customer_ids = {r.customer_id for r in rows if r.customer_id}
    customers: dict = {}
    if customer_ids:
        c_rows = await db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        customers = {cid: name for cid, name in c_rows.all()}

    stats = await repo.stats(customer_id=customer_id)

    def _qs(**overrides) -> str:
        base = {
            "q": q or "", "status": status_ or "",
            "customer_id": str(customer_id) if customer_id else "",
            "assigned_lead_id": str(assigned_lead_id) if assigned_lead_id else "",
            "only_open": "true" if only_open else "",
            "sort": sort,
        }
        base.update({k: ("" if v is None else v) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/projects/list.html",
        {
            "title": "Projects",
            "projects": rows,
            "page_meta": meta,
            "stats": stats,
            "customers_by_id": customers,
            "q": q or "",
            "status_filter": status_ or "",
            "assigned_filter": assigned_lead_id,
            "customer_id": customer_id,
            "only_open": only_open,
            "sort": sort,
            "assignees": await _load_assignees(db),
            "qs": _qs,
            **_catalog(),
        },
    )


@router.get("/export.csv")
async def export_csv(
    db: DbSession,
    q: str | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    customer_id: UUID | None = Query(None),
    assigned_lead_id: UUID | None = Query(None),
    only_open: bool = Query(False),
    _=read(PermissionCode.PROJECT_READ),
    current=Depends(get_current_user),
):
    from app.modules.customers.models import Customer

    stmt = ProjectRepository(db).query(
        q=q, status=status_, customer_id=customer_id,
        assigned_lead_id=assigned_lead_id, only_open=only_open,
    )
    rows = (await db.execute(stmt)).scalars().all()

    cust_ids = {r.customer_id for r in rows if r.customer_id}
    customers: dict = {}
    if cust_ids:
        c_rows = await db.execute(
            select(Customer.id, Customer.name, Customer.code).where(
                Customer.id.in_(cust_ids)
            )
        )
        customers = {cid: (name, code) for cid, name, code in c_rows.all()}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "code", "status", "title", "customer_name", "customer_code",
        "quoted_price", "approved_price", "estimated_hpp", "actual_hpp",
        "margin_pct", "start_date", "target_end_date", "actual_end_date",
        "created_at",
    ])
    for p in rows:
        c = customers.get(p.customer_id)
        writer.writerow([
            p.code, p.status, p.title or "",
            c[0] if c else "", c[1] if c else "",
            p.quoted_price or "", p.approved_price or "",
            p.estimated_hpp or 0, p.actual_hpp or 0,
            f"{p.actual_gross_margin_pct:.1f}",
            p.start_date.isoformat() if p.start_date else "",
            p.target_end_date.isoformat() if p.target_end_date else "",
            p.actual_end_date.isoformat() if p.actual_end_date else "",
            p.created_at.isoformat() if p.created_at else "",
        ])

    buf.seek(0)
    filename = f"projects-{datetime.utcnow().strftime('%Y%m%d-%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ════════════════════════════════════════════════════════════════
# CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    customer_id: UUID | None = Query(None),
    vehicle_id: UUID | None = Query(None),
    inquiry_id: UUID | None = Query(None),
    _=write(PermissionCode.PROJECT_CREATE),
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
        "admin/projects/form.html",
        {
            "title": "New Project",
            "mode": "create",
            "project": None,
            "preselected_customer": preselected_customer,
            "preselected_vehicle": preselected_vehicle,
            "preselected_inquiry_id": inquiry_id,
            "assignees": await _load_assignees(db),
            **_catalog(),
        },
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PROJECT_CREATE),
    current=Depends(get_current_user),
):
    form = await request.form()

    async def _render_error(msg: str, status_code: int = 400):
        preselected_customer = None
        preselected_vehicle = None
        cid = _safe_uuid(form.get("customer_id"))
        vid = _safe_uuid(form.get("vehicle_id"))
        if cid:
            preselected_customer = await CustomerRepository(db).get(cid)
        if vid:
            preselected_vehicle = await VehicleRepository(db).get(vid)
        return templates.render(
            request,
            "admin/projects/form.html",
            {
                "title": "New Project", "mode": "create", "project": None,
                "preselected_customer": preselected_customer,
                "preselected_vehicle": preselected_vehicle,
                "preselected_inquiry_id": form.get("inquiry_id"),
                "error": msg, "form_values": dict(form),
                "assignees": await _load_assignees(db),
                **_catalog(),
            },
            status_code=status_code,
        )

    customer_id = _safe_uuid(form.get("customer_id"))
    if not customer_id:
        return await _render_error("Please select a customer.")

    try:
        payload = ProjectCreate(
            title=(form.get("title") or "").strip() or None,
            description=(form.get("description") or "").strip() or None,
            inquiry_id=_safe_uuid(form.get("inquiry_id")),
            customer_id=customer_id,
            vehicle_id=_safe_uuid(form.get("vehicle_id")),
            assigned_lead_id=_safe_uuid(form.get("assigned_lead_id")),
            priority=_safe_int(form.get("priority"), 0),
            quoted_price=_safe_float(form.get("quoted_price")),
            approved_price=_safe_float(form.get("approved_price")),
            start_date=_safe_date(form.get("start_date")),
            target_end_date=_safe_date(form.get("target_end_date")),
            internal_notes=(form.get("internal_notes") or "").strip() or None,
        )
        project = await ProjectService(db).create(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return await _render_error(
            _form_error(exc), getattr(exc, "status_code", 400)
        )

    return RedirectResponse(url=f"/admin/projects/{project.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{project_id}", response_class=HTMLResponse)
async def detail_view(
    project_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=read(PermissionCode.PROJECT_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from app.modules.inquiries.repository import InquiryRepository
    from app.modules.pricing.service import PricingService
    from app.modules.finance.repository import PaymentRepository

    payments = await PaymentRepository(db).payments_for_project(project_id)
    total_received = sum(float(p.amount) for p in payments)

    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise NotFoundError("Project not found")

    items = await repo.list_items(project_id)
    customer = (
        await CustomerRepository(db).get(project.customer_id)
        if project.customer_id else None
    )
    vehicle = (
        await VehicleRepository(db).get(project.vehicle_id)
        if project.vehicle_id else None
    )

    source_inquiry = None
    if project.inquiry_id:
        source_inquiry = await InquiryRepository(db).get(project.inquiry_id)

    materials = list(
        (await db.execute(
            MaterialRepository(db).query(is_active=True)
        )).scalars().all()
    )
    employees = list(
        (await db.execute(
            EmployeeRepository(db).query(is_active=True)
        )).scalars().all()
    )
    next_statuses = ALLOWED_PROJECT_TRANSITIONS.get(project.status, frozenset())
    overhead_rate = await CostingService(db).overhead_rate_per_hour()

    by_category: dict[str, list] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    hpp_for_pricing = float(project.actual_hpp or project.estimated_hpp or 0)
    service_interest = source_inquiry.service_interest if source_inquiry else None
    vehicle_category = vehicle.category if vehicle else None

    pricing_recommendation = None
    pricing_evaluation = None
    if hpp_for_pricing > 0:
        pricing_svc = PricingService(db)
        pricing_recommendation = await pricing_svc.recommend(
            hpp=hpp_for_pricing,
            service_interest=service_interest,
            vehicle_category=vehicle_category,
        )
        proposed = project.approved_price or project.quoted_price
        if proposed:
            pricing_evaluation = await pricing_svc.evaluate(
                hpp=hpp_for_pricing,
                selling_price=float(proposed),
                service_interest=service_interest,
                vehicle_category=vehicle_category,
            )

    return templates.render(
        request,
        "admin/projects/detail.html",
        {
            "title": project.code,
            "project": project,
            "items": items,
            "items_by_category": by_category,
            "customer": customer,
            "vehicle": vehicle,
            "source_inquiry": source_inquiry,
            "materials": materials,
            "employees": employees,
            "next_statuses": sorted(next_statuses),
            "overhead_rate_per_hour": overhead_rate,
            "assignees": await _load_assignees(db),
            "pricing_recommendation": pricing_recommendation,
            "pricing_evaluation": pricing_evaluation,
            "payments": payments,
            "total_received": total_received,
            "error": error,
            "payment_method_labels": PAYMENT_METHOD_LABELS,      # ← NEW
            "inquiry_status_labels": INQUIRY_STATUS_LABELS,      # ← NEW
            **_catalog(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT / UPDATE / STATUS
# ════════════════════════════════════════════════════════════════

@router.get("/{project_id}/edit", response_class=HTMLResponse)
async def edit_view(
    project_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PROJECT_UPDATE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    project = await ProjectRepository(db).get(project_id)
    if not project:
        raise NotFoundError("Project not found")
    customer = (
        await CustomerRepository(db).get(project.customer_id)
        if project.customer_id else None
    )
    vehicle = (
        await VehicleRepository(db).get(project.vehicle_id)
        if project.vehicle_id else None
    )
    return templates.render(
        request,
        "admin/projects/form.html",
        {
            "title": f"Edit {project.code}",
            "mode": "edit",
            "project": project,
            "preselected_customer": customer,
            "preselected_vehicle": vehicle,
            "preselected_inquiry_id": project.inquiry_id,
            "assignees": await _load_assignees(db),
            **_catalog(),
        },
    )


@router.post("/{project_id}")
async def update_submit(
    project_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PROJECT_UPDATE),
    current=Depends(get_current_user),
):
    form = await request.form()
    try:
        payload = ProjectUpdate(
            title=(form.get("title") or "").strip() or None,
            description=(form.get("description") or "").strip() or None,
            assigned_lead_id=_safe_uuid(form.get("assigned_lead_id")),
            priority=_safe_int(form.get("priority"), 0),
            quoted_price=_safe_float(form.get("quoted_price")),
            approved_price=_safe_float(form.get("approved_price")),
            start_date=_safe_date(form.get("start_date")),
            target_end_date=_safe_date(form.get("target_end_date")),
            actual_end_date=_safe_date(form.get("actual_end_date")),
            internal_notes=(form.get("internal_notes") or "").strip() or None,
        )
        await ProjectService(db).update(project_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(project_id, exc)
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


@router.post("/{project_id}/status")
async def status_submit(
    project_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PROJECT_APPROVE),
    current=Depends(get_current_user),
):
    form = await request.form()
    try:
        payload = ProjectStatusChange(
            status=(form.get("status") or "").strip(),
            note=(form.get("note") or "").strip() or None,
        )
        await ProjectService(db).change_status(
            project_id, payload.status, note=payload.note, actor=current
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(project_id, exc)
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# ITEMS
# ════════════════════════════════════════════════════════════════

@router.post("/{project_id}/items")
async def add_item_submit(
    project_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PROJECT_COST),
    current=Depends(get_current_user),
):
    form = await request.form()
    try:
        payload = ProjectItemCreate(
            category=(form.get("category") or "").strip(),
            description=(form.get("description") or "").strip(),
            material_id=_safe_uuid(form.get("material_id")),
            employee_id=_safe_uuid(form.get("employee_id")),
            unit=(form.get("unit") or "").strip() or None,
            estimated_quantity=_safe_float(form.get("estimated_quantity")),
            estimated_unit_cost=_safe_float(form.get("estimated_unit_cost")),
            actual_quantity=_safe_float(form.get("actual_quantity")),
            actual_unit_cost=_safe_float(form.get("actual_unit_cost")),
            notes=(form.get("notes") or "").strip() or None,
        )
        await CostingService(db).add_item(project_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(project_id, exc)
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


@router.post("/{project_id}/items/{item_id}")
async def update_item_submit(
    project_id: UUID,
    item_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PROJECT_COST),
    current=Depends(get_current_user),
):
    form = await request.form()
    try:
        payload = ProjectItemUpdate(
            description=(form.get("description") or "").strip() or None,
            estimated_quantity=_safe_float(form.get("estimated_quantity")),
            estimated_unit_cost=_safe_float(form.get("estimated_unit_cost")),
            actual_quantity=_safe_float(form.get("actual_quantity")),
            actual_unit_cost=_safe_float(form.get("actual_unit_cost")),
            status=(form.get("status") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
        )
        await CostingService(db).update_item(
            project_id, item_id, payload, actor=current
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(project_id, exc)
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


@router.post("/{project_id}/items/{item_id}/delete")
async def delete_item_submit(
    project_id: UUID,
    item_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PROJECT_COST),
    current=Depends(get_current_user),
):
    try:
        await CostingService(db).delete_item(project_id, item_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(project_id, exc)
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# SEARCH FRAGMENTS
# ════════════════════════════════════════════════════════════════

@router.get("/api/search-customers", response_class=HTMLResponse)
async def search_customers_fragment(
    request: Request,
    db: DbSession,
    q: str = Query("", max_length=100),
    _=read(PermissionCode.PROJECT_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from sqlalchemy import and_, or_
    from app.modules.customers.models import Customer

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
        "admin/projects/_customer_options.html",
        {"customers": customers, "q": q},
    )


@router.get("/api/search-vehicles", response_class=HTMLResponse)
async def search_vehicles_fragment(
    request: Request,
    db: DbSession,
    q: str = Query("", max_length=100),
    customer_id: UUID | None = Query(None),
    _=read(PermissionCode.PROJECT_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from sqlalchemy import and_, or_
    from app.modules.vehicles.models import Vehicle

    vehicles = []
    if customer_id:
        like = f"%{q.strip()}%" if q.strip() else "%"
        stmt = (
            select(Vehicle)
            .where(
                and_(
                    Vehicle.customer_id == customer_id,
                    or_(
                        Vehicle.brand.ilike(like),
                        Vehicle.model.ilike(like),
                        Vehicle.plate_number.ilike(like),
                    ),
                )
            )
            .order_by(Vehicle.brand, Vehicle.model)
            .limit(10)
        )
        vehicles = (await db.execute(stmt)).scalars().all()

    return templates.render(
        request,
        "admin/projects/_vehicle_options.html",
        {"vehicles": vehicles, "q": q, "customer_id": customer_id},
    )