"""Admin web routes for employees."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.projects.repository import EmployeeRepository
from app.modules.projects.schemas import EmployeeCreate, EmployeeUpdate
from app.modules.projects.service import EmployeeService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/employees", tags=["admin-employees"])


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = EmployeeRepository(db).query(q=q, is_active=None)
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/employees/list.html",
        {"title": "Employees", "employees": rows, "page_meta": meta, "q": q or ""},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(request: Request, current=Depends(get_current_user)) -> HTMLResponse:
    return templates.render(
        request,
        "admin/employees/form.html",
        {"title": "New Employee", "mode": "create", "employee": None},
    )


@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()
    code = (form.get("code") or "").strip() or await EmployeeRepository(db).next_code()
    payload = EmployeeCreate(
        code=code,
        name=(form.get("name") or "").strip(),
        position=(form.get("position") or "").strip() or None,
        hourly_rate=float(form.get("hourly_rate") or 0),
        monthly_salary=(float(form["monthly_salary"]) if form.get("monthly_salary") else None),
        joined_at=(date.fromisoformat(form["joined_at"]) if form.get("joined_at") else None),
        phone=(form.get("phone") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )
    try:
        emp = await EmployeeService(db).create(payload, actor=current)
    except AppError as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/employees/form.html",
            {
                "title": "New Employee", "mode": "create", "employee": None,
                "error": exc.message, "form_values": dict(form),
            },
            status_code=exc.status_code,
        )
    await db.commit()
    return RedirectResponse(url=f"/admin/employees/{emp.id}", status_code=303)


@router.get("/{employee_id}", response_class=HTMLResponse)
async def detail_view(
    employee_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    emp = await EmployeeRepository(db).get(employee_id)
    if not emp:
        raise NotFoundError("Employee not found")
    return templates.render(
        request, "admin/employees/detail.html",
        {"title": emp.name, "employee": emp},
    )


@router.get("/{employee_id}/edit", response_class=HTMLResponse)
async def edit_view(
    employee_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    emp = await EmployeeRepository(db).get(employee_id)
    if not emp:
        raise NotFoundError("Employee not found")
    return templates.render(
        request, "admin/employees/form.html",
        {"title": f"Edit {emp.name}", "mode": "edit", "employee": emp},
    )


@router.post("/{employee_id}")
async def update_submit(
    employee_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = EmployeeUpdate(
        name=(form.get("name") or "").strip() or None,
        position=(form.get("position") or "").strip() or None,
        hourly_rate=(float(form["hourly_rate"]) if form.get("hourly_rate") else None),
        monthly_salary=(float(form["monthly_salary"]) if form.get("monthly_salary") else None),
        joined_at=(date.fromisoformat(form["joined_at"]) if form.get("joined_at") else None),
        phone=(form.get("phone") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
        is_active=form.get("is_active") == "true",
    )
    await EmployeeService(db).update(employee_id, payload, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/employees/{employee_id}", status_code=303)