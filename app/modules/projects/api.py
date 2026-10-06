"""REST endpoints for the projects module."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.projects.constants import (
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
    EmployeeCreate,
    EmployeeDetail,
    EmployeeListItem,
    EmployeeUpdate,
    OverheadRateInfo,
    ProjectCatalog,
    ProjectCostBreakdown,
    ProjectCreate,
    ProjectDetail,
    ProjectItemCreate,
    ProjectItemOut,
    ProjectItemUpdate,
    ProjectListItem,
    ProjectStatusChange,
    ProjectUpdate,
)
from app.modules.projects.service import (
    CostingService,
    EmployeeService,
    ProjectService,
)

projects_router = APIRouter(prefix="/projects", tags=["projects"])
employees_router = APIRouter(prefix="/employees", tags=["employees"])


# ════════════════════════════════════════════════════════════════
# CATALOG
# ════════════════════════════════════════════════════════════════

@projects_router.get("/catalog", response_model=ProjectCatalog)
async def catalog() -> ProjectCatalog:
    return ProjectCatalog(
        statuses=PROJECT_STATUSES,
        status_labels=PROJECT_STATUS_LABELS,
        cost_categories=COST_CATEGORIES,
        cost_category_labels=COST_CATEGORY_LABELS,
    )


@projects_router.get("/overhead-rate", response_model=OverheadRateInfo)
async def overhead_rate(
    db: DbSession,
    _=Depends(require_permission(PermissionCode.PROJECT_READ)),
) -> OverheadRateInfo:
    svc = CostingService(db)
    from app.modules.projects.constants import (
        SETTING_MONTHLY_LABOR_HOURS,
        SETTING_MONTHLY_OVERHEAD,
    )
    from app.modules.settings.service import SettingsService
    o = float(await SettingsService(db).get_value(SETTING_MONTHLY_OVERHEAD, "0") or 0)
    h = float(await SettingsService(db).get_value(SETTING_MONTHLY_LABOR_HOURS, "0") or 0)
    return OverheadRateInfo(
        monthly_overhead=o,
        monthly_labor_hours=h,
        overhead_rate_per_hour=await svc.overhead_rate_per_hour(),
    )


# ════════════════════════════════════════════════════════════════
# PROJECTS
# ════════════════════════════════════════════════════════════════

@projects_router.get("", response_model=Page[ProjectListItem])
async def list_projects(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    status_: str | None = Query(None, alias="status"),
    customer_id: UUID | None = Query(None),
    only_open: bool = Query(False),
    _=Depends(require_permission(PermissionCode.PROJECT_READ)),
) -> Page[ProjectListItem]:
    stmt = ProjectRepository(db).query(
        q=q, status=status_, customer_id=customer_id, only_open=only_open,
    )
    rows, meta = await paginate(db, stmt, params)
    items = []
    for r in rows:
        item = ProjectListItem.model_validate(r)
        item.variance = r.hpp_variance
        item.gross_margin_pct = r.actual_gross_margin_pct
        items.append(item)
    return Page[ProjectListItem](items=items, meta=meta)


@projects_router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PROJECT_CREATE)),
) -> ProjectDetail:
    project = await ProjectService(db).create(payload, actor=actor)
    return ProjectDetail.model_validate(project)


@projects_router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.PROJECT_READ)),
) -> ProjectDetail:
    project = await ProjectRepository(db).get(project_id)
    if not project:
        raise NotFoundError("Project not found")

    detail = ProjectDetail.model_validate(project)
    items = await ProjectRepository(db).list_items(project_id)
    detail.items = [_item_out(i) for i in items]

    detail.variance = project.hpp_variance
    detail.gross_margin_pct = project.actual_gross_margin_pct

    detail.cost_breakdown = ProjectCostBreakdown(
        estimated_materials=float(project.estimated_materials),
        estimated_parts=float(project.estimated_parts),
        estimated_labor=float(project.estimated_labor),
        estimated_outsource=float(project.estimated_outsource),
        estimated_overhead=float(project.estimated_overhead),
        estimated_misc=float(project.estimated_misc),
        actual_materials=float(project.actual_materials),
        actual_parts=float(project.actual_parts),
        actual_labor=float(project.actual_labor),
        actual_outsource=float(project.actual_outsource),
        actual_overhead=float(project.actual_overhead),
        actual_misc=float(project.actual_misc),
        estimated_hpp=float(project.estimated_hpp),
        actual_hpp=float(project.actual_hpp),
        variance=project.hpp_variance,
        variance_pct=(
            (project.hpp_variance / float(project.estimated_hpp)) * 100
            if project.estimated_hpp else 0.0
        ),
    )

    # Populate snapshots
    from app.modules.customers.repository import CustomerRepository
    from app.modules.vehicles.repository import VehicleRepository
    if project.customer_id:
        c = await CustomerRepository(db).get(project.customer_id)
        if c:
            detail.customer_name = c.name
            detail.customer_code = c.code
    if project.vehicle_id:
        v = await VehicleRepository(db).get(project.vehicle_id)
        if v:
            detail.vehicle_label = f"{v.brand} {v.model}" + (f" — {v.plate_number}" if v.plate_number else "")

    return detail


@projects_router.patch("/{project_id}", response_model=ProjectDetail)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PROJECT_UPDATE)),
) -> ProjectDetail:
    project = await ProjectService(db).update(project_id, payload, actor=actor)
    return ProjectDetail.model_validate(project)


@projects_router.post("/{project_id}/status", response_model=ProjectDetail)
async def change_status(
    project_id: UUID,
    payload: ProjectStatusChange,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PROJECT_APPROVE)),
) -> ProjectDetail:
    project = await ProjectService(db).change_status(
        project_id, payload.status, note=payload.note, actor=actor
    )
    return ProjectDetail.model_validate(project)


# ════════════════════════════════════════════════════════════════
# PROJECT ITEMS
# ════════════════════════════════════════════════════════════════

@projects_router.post(
    "/{project_id}/items",
    response_model=ProjectItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    project_id: UUID,
    payload: ProjectItemCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PROJECT_COST)),
) -> ProjectItemOut:
    item = await CostingService(db).add_item(project_id, payload, actor=actor)
    return _item_out(item)


@projects_router.patch(
    "/{project_id}/items/{item_id}",
    response_model=ProjectItemOut,
)
async def update_item(
    project_id: UUID,
    item_id: UUID,
    payload: ProjectItemUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PROJECT_COST)),
) -> ProjectItemOut:
    item = await CostingService(db).update_item(project_id, item_id, payload, actor=actor)
    return _item_out(item)


@projects_router.delete(
    "/{project_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_item(
    project_id: UUID,
    item_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PROJECT_COST)),
) -> None:
    await CostingService(db).delete_item(project_id, item_id, actor=actor)


# ════════════════════════════════════════════════════════════════
# EMPLOYEES
# ════════════════════════════════════════════════════════════════

@employees_router.get("", response_model=Page[EmployeeListItem])
async def list_employees(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    is_active: bool | None = Query(True),
    _=Depends(require_permission(PermissionCode.EMPLOYEE_READ)),
) -> Page[EmployeeListItem]:
    stmt = EmployeeRepository(db).query(q=q, is_active=is_active)
    rows, meta = await paginate(db, stmt, params)
    return Page[EmployeeListItem](
        items=[EmployeeListItem.model_validate(r) for r in rows], meta=meta
    )


@employees_router.post("", response_model=EmployeeDetail, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.EMPLOYEE_WRITE)),
) -> EmployeeDetail:
    emp = await EmployeeService(db).create(payload, actor=actor)
    return EmployeeDetail.model_validate(emp)


@employees_router.get("/{employee_id}", response_model=EmployeeDetail)
async def get_employee(
    employee_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.EMPLOYEE_READ)),
) -> EmployeeDetail:
    emp = await EmployeeRepository(db).get(employee_id)
    if not emp:
        raise NotFoundError("Employee not found")
    return EmployeeDetail.model_validate(emp)


@employees_router.patch("/{employee_id}", response_model=EmployeeDetail)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.EMPLOYEE_WRITE)),
) -> EmployeeDetail:
    emp = await EmployeeService(db).update(employee_id, payload, actor=actor)
    return EmployeeDetail.model_validate(emp)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _item_out(item) -> ProjectItemOut:
    out = ProjectItemOut.model_validate(item)
    est = float(item.estimated_cost or 0)
    act = float(item.actual_cost or 0)
    out.variance = est - act
    out.variance_pct = (out.variance / est * 100) if est else 0.0
    return out