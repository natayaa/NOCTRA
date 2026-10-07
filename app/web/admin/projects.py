"""Admin web routes for projects — the costing cockpit."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

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
    PROJECT_STATUSES,
    PROJECT_STATUS_LABELS,
)
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
from app.web.templates_env import templates


router = APIRouter(prefix="/admin/projects", tags=["admin-projects"])


def _catalog() -> dict:
    return {
        "statuses": PROJECT_STATUSES,
        "status_labels": PROJECT_STATUS_LABELS,
        "cost_categories": COST_CATEGORIES,
        "cost_category_labels": COST_CATEGORY_LABELS,
    }


async def _load_assignees(db):
    return list(
        (await db.execute(select(User).where(User.is_active.is_(True)).order_by(User.full_name)))
        .scalars().all()
    )


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    only_open: bool = Query(False),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = ProjectRepository(db).query(q=q, status=status_, only_open=only_open)
    rows, meta = await paginate(db, stmt, params)

    # Preload customer names
    customer_ids = {r.customer_id for r in rows if r.customer_id}
    customers = {}
    if customer_ids:
        from app.modules.customers.models import Customer
        c_rows = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        customers = {c.id: c for c in c_rows.scalars().all()}

    return templates.render(
        request,
        "admin/projects/list.html",
        {
            "title": "Projects",
            "projects": rows,
            "page_meta": meta,
            "customers_by_id": customers,
            "q": q or "",
            "status_filter": status_ or "",
            "only_open": only_open,
            **_catalog(),
        },
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
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()
    payload = ProjectCreate(
        title=(form.get("title") or "").strip() or None,
        description=(form.get("description") or "").strip() or None,
        inquiry_id=(UUID(form["inquiry_id"]) if form.get("inquiry_id") else None),
        customer_id=UUID(form["customer_id"]),
        vehicle_id=(UUID(form["vehicle_id"]) if form.get("vehicle_id") else None),
        assigned_lead_id=(UUID(form["assigned_lead_id"]) if form.get("assigned_lead_id") else None),
        priority=int(form.get("priority") or 0),
        quoted_price=(float(form["quoted_price"]) if form.get("quoted_price") else None),
        approved_price=(float(form["approved_price"]) if form.get("approved_price") else None),
        start_date=(date.fromisoformat(form["start_date"]) if form.get("start_date") else None),
        target_end_date=(date.fromisoformat(form["target_end_date"]) if form.get("target_end_date") else None),
        internal_notes=(form.get("internal_notes") or "").strip() or None,
    )
    try:
        project = await ProjectService(db).create(payload, actor=current)
    except AppError as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/projects/form.html",
            {
                "title": "New Project", "mode": "create", "project": None,
                "preselected_customer": None, "preselected_vehicle": None,
                "preselected_inquiry_id": None,
                "error": exc.message, "form_values": dict(form),
                "assignees": await _load_assignees(db),
                **_catalog(),
            },
            status_code=exc.status_code,
        )
    await db.commit()
    return RedirectResponse(url=f"/admin/projects/{project.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL — the costing cockpit
# ════════════════════════════════════════════════════════════════

@router.get("/{project_id}", response_class=HTMLResponse)
async def detail_view(
    project_id: UUID,
    request: Request,
    db: DbSession,
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
    customer = await CustomerRepository(db).get(project.customer_id) if project.customer_id else None
    vehicle = await VehicleRepository(db).get(project.vehicle_id) if project.vehicle_id else None

    materials = list(
        (await db.execute(MaterialRepository(db).query(is_active=True))).scalars().all()
    )
    employees = list(
        (await db.execute(EmployeeRepository(db).query(is_active=True))).scalars().all()
    )
    next_statuses = ALLOWED_PROJECT_TRANSITIONS.get(project.status, frozenset())
    overhead_rate = await CostingService(db).overhead_rate_per_hour()

    by_category: dict[str, list] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    # ── Pricing computation ─────────────────────────
    # Pick the HPP to use: actual if we have it, else estimated
    hpp_for_pricing = float(project.actual_hpp or project.estimated_hpp or 0)

    # Extract service + category context for rule matching
    service_interest = None
    vehicle_category = vehicle.category if vehicle else None
    if project.inquiry_id:
        inq = await InquiryRepository(db).get(project.inquiry_id)
        if inq:
            service_interest = inq.service_interest

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
            "materials": materials,
            "employees": employees,
            "next_statuses": sorted(next_statuses),
            "overhead_rate_per_hour": overhead_rate,
            "assignees": await _load_assignees(db),
            "pricing_recommendation": pricing_recommendation,
            "pricing_evaluation": pricing_evaluation,
            "payments": payments,
            "total_received": total_received,
            **_catalog(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT + STATUS
# ════════════════════════════════════════════════════════════════

@router.get("/{project_id}/edit", response_class=HTMLResponse)
async def edit_view(
    project_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    project = await ProjectRepository(db).get(project_id)
    if not project:
        raise NotFoundError("Project not found")
    customer = await CustomerRepository(db).get(project.customer_id) if project.customer_id else None
    vehicle = await VehicleRepository(db).get(project.vehicle_id) if project.vehicle_id else None
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
    project_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = ProjectUpdate(
        title=(form.get("title") or "").strip() or None,
        description=(form.get("description") or "").strip() or None,
        assigned_lead_id=(UUID(form["assigned_lead_id"]) if form.get("assigned_lead_id") else None),
        priority=(int(form["priority"]) if form.get("priority") else None),
        quoted_price=(float(form["quoted_price"]) if form.get("quoted_price") else None),
        approved_price=(float(form["approved_price"]) if form.get("approved_price") else None),
        start_date=(date.fromisoformat(form["start_date"]) if form.get("start_date") else None),
        target_end_date=(date.fromisoformat(form["target_end_date"]) if form.get("target_end_date") else None),
        actual_end_date=(date.fromisoformat(form["actual_end_date"]) if form.get("actual_end_date") else None),
        internal_notes=(form.get("internal_notes") or "").strip() or None,
    )
    try:
        await ProjectService(db).update(project_id, payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/projects/{project_id}?error={exc.message}", status_code=303
        )
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


@router.post("/{project_id}/status")
async def status_submit(
    project_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = ProjectStatusChange(
        status=(form.get("status") or "").strip(),
        note=(form.get("note") or "").strip() or None,
    )
    try:
        await ProjectService(db).change_status(
            project_id, payload.status, note=payload.note, actor=current
        )
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/projects/{project_id}?error={exc.message}", status_code=303
        )
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# ITEMS
# ════════════════════════════════════════════════════════════════

@router.post("/{project_id}/items")
async def add_item_submit(
    project_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = ProjectItemCreate(
        category=(form.get("category") or "").strip(),
        description=(form.get("description") or "").strip(),
        material_id=(UUID(form["material_id"]) if form.get("material_id") else None),
        employee_id=(UUID(form["employee_id"]) if form.get("employee_id") else None),
        unit=(form.get("unit") or "").strip() or None,
        estimated_quantity=(float(form["estimated_quantity"]) if form.get("estimated_quantity") else None),
        estimated_unit_cost=(float(form["estimated_unit_cost"]) if form.get("estimated_unit_cost") else None),
        actual_quantity=(float(form["actual_quantity"]) if form.get("actual_quantity") else None),
        actual_unit_cost=(float(form["actual_unit_cost"]) if form.get("actual_unit_cost") else None),
        notes=(form.get("notes") or "").strip() or None,
    )
    try:
        await CostingService(db).add_item(project_id, payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/projects/{project_id}?error={exc.message}", status_code=303
        )
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


@router.post("/{project_id}/items/{item_id}")
async def update_item_submit(
    project_id: UUID, item_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = ProjectItemUpdate(
        description=(form.get("description") or "").strip() or None,
        estimated_quantity=(float(form["estimated_quantity"]) if form.get("estimated_quantity") else None),
        estimated_unit_cost=(float(form["estimated_unit_cost"]) if form.get("estimated_unit_cost") else None),
        actual_quantity=(float(form["actual_quantity"]) if form.get("actual_quantity") else None),
        actual_unit_cost=(float(form["actual_unit_cost"]) if form.get("actual_unit_cost") else None),
        status=(form.get("status") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )
    try:
        await CostingService(db).update_item(project_id, item_id, payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/projects/{project_id}?error={exc.message}", status_code=303
        )
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


@router.post("/{project_id}/items/{item_id}/delete")
async def delete_item_submit(
    project_id: UUID, item_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    try:
        await CostingService(db).delete_item(project_id, item_id, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/projects/{project_id}?error={exc.message}", status_code=303
        )
    return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=303)


## SEARCH 
@router.get("/api/search-customers", response_class=HTMLResponse)
async def search_customers_fragment(
    request: Request,
    db: DbSession,
    q: str = Query("", min_length=0, max_length=100),
    current=Depends(get_current_user),
) -> HTMLResponse:
    """Returns HTML options for the customer picker dropdown."""
    from sqlalchemy import and_, or_, select
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
        {"customers": customers},
    )


@router.get("/api/search-vehicles", response_class=HTMLResponse)
async def search_vehicles_fragment(
    request: Request,
    db: DbSession,
    q: str = Query("", min_length=0, max_length=100),
    customer_id: UUID | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    from sqlalchemy import and_, or_, select
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
        {"vehicles": vehicles},
    )