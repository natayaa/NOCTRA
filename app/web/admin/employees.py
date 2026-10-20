"""Admin web routes for employees."""

from __future__ import annotations

from datetime import date
from urllib.parse import quote, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.projects.repository import EmployeeRepository
from app.modules.projects.schemas import EmployeeCreate, EmployeeUpdate
from app.modules.projects.service import EmployeeService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/employees", tags=["admin-employees"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _form_error(exc: Exception) -> str:
    return (getattr(exc, "message", None) or str(exc) or "Invalid input").strip()


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


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    is_active: bool | None = Query(None),
    _=read(PermissionCode.EMPLOYEE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = EmployeeRepository(db).query(q=q, is_active=is_active)
    rows, meta = await paginate(db, stmt, params)

    def qs(page: int | None = None, **overrides) -> str:
        base = {
            "q": q or "",
            "is_active": "" if is_active is None else ("true" if is_active else "false"),
        }
        if page is not None:
            base["page"] = str(page)
        base.update({k: ("" if v is None else str(v)) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/employees/list.html",
        {
            "title": "Employees",
            "employees": rows,
            "page_meta": meta,
            "q": q or "",
            "is_active_filter": is_active,
            "qs": qs,
        },
    )


# ════════════════════════════════════════════════════════════════
# NEW / CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    _=write(PermissionCode.EMPLOYEE_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    return templates.render(
        request,
        "admin/employees/form.html",
        {"title": "New Employee", "mode": "create", "employee": None},
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.EMPLOYEE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    async def _render_error(msg: str, status_code: int = 400):
        return templates.render(
            request,
            "admin/employees/form.html",
            {
                "title": "New Employee",
                "mode": "create",
                "employee": None,
                "error": msg,
                "form_values": dict(form),
            },
            status_code=status_code,
        )

    try:
        code = (form.get("code") or "").strip() or await EmployeeRepository(db).next_code()
        payload = EmployeeCreate(
            code=code,
            name=(form.get("name") or "").strip(),
            position=(form.get("position") or "").strip() or None,
            hourly_rate=_safe_float(form.get("hourly_rate")) or 0.0,
            monthly_salary=_safe_float(form.get("monthly_salary")),
            joined_at=_safe_date(form.get("joined_at")),
            phone=(form.get("phone") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
        )
        emp = await EmployeeService(db).create(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return await _render_error(
            _form_error(exc), getattr(exc, "status_code", 400)
        )

    return RedirectResponse(url=f"/admin/employees/{emp.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{employee_id}", response_class=HTMLResponse)
async def detail_view(
    employee_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=read(PermissionCode.EMPLOYEE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    emp = await EmployeeRepository(db).get(employee_id)
    if not emp:
        raise NotFoundError("Employee not found")
    return templates.render(
        request,
        "admin/employees/detail.html",
        {
            "title": emp.name,
            "employee": emp,
            "error": error,
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT / UPDATE
# ════════════════════════════════════════════════════════════════

@router.get("/{employee_id}/edit", response_class=HTMLResponse)
async def edit_view(
    employee_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=write(PermissionCode.EMPLOYEE_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    emp = await EmployeeRepository(db).get(employee_id)
    if not emp:
        raise NotFoundError("Employee not found")
    return templates.render(
        request,
        "admin/employees/form.html",
        {
            "title": f"Edit {emp.name}",
            "mode": "edit",
            "employee": emp,
            "error": error,
        },
    )


@router.post("/{employee_id}")
async def update_submit(
    employee_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.EMPLOYEE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
        payload = EmployeeUpdate(
            name=(form.get("name") or "").strip() or None,
            position=(form.get("position") or "").strip() or None,
            hourly_rate=_safe_float(form.get("hourly_rate")),
            monthly_salary=_safe_float(form.get("monthly_salary")),
            joined_at=_safe_date(form.get("joined_at")),
            phone=(form.get("phone") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
            # Sentinel distinguishes "user unchecked" from "form didn't submit"
            is_active=(
                form.get("is_active") == "true"
                if form.get("_has_is_active") == "1"
                else None
            ),
        )
        await EmployeeService(db).update(employee_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        emp = await EmployeeRepository(db).get(employee_id)
        fv = dict(form)
        fv["_has_is_active"] = "1"
        return templates.render(
            request,
            "admin/employees/form.html",
            {
                "title": f"Edit {emp.name}" if emp else "Edit Employee",
                "mode": "edit",
                "employee": emp,
                "error": _form_error(exc),
                "form_values": fv,
            },
            status_code=getattr(exc, "status_code", 400),
        )

    return RedirectResponse(url=f"/admin/employees/{employee_id}", status_code=303)