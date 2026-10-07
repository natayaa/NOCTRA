"""Admin web routes for users."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.rbac.repository import RoleRepository
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    UserCreate,
    UserPasswordChange,
    UserUpdate,
)
from app.modules.users.service import UserService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


async def _load_roles(db):
    return await RoleRepository(db).list()


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = UserRepository(db).query()
    if q:
        from sqlalchemy import or_, and_
        from app.modules.auth.models import User
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            User.username.ilike(like),
            User.email.ilike(like),
            User.full_name.ilike(like),
        ))
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/users/list.html",
        {"title": "Users", "users": rows, "page_meta": meta, "q": q or ""},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(request: Request, db: DbSession, current=Depends(get_current_user)) -> HTMLResponse:
    return templates.render(
        request,
        "admin/users/form.html",
        {
            "title": "New User",
            "mode": "create",
            "user_obj": None,
            "all_roles": await _load_roles(db),
        },
    )


@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()
    payload = UserCreate(
        username=(form.get("username") or "").strip(),
        email=(form.get("email") or "").strip(),
        full_name=(form.get("full_name") or "").strip(),
        password=(form.get("password") or ""),
        is_active=form.get("is_active") == "true",
        is_superuser=form.get("is_superuser") == "true",
        role_names=form.getlist("role_names"),
    )
    try:
        user = await UserService(db).create(payload, actor=current)
    except AppError as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/users/form.html",
            {
                "title": "New User", "mode": "create", "user_obj": None,
                "all_roles": await _load_roles(db),
                "error": exc.message, "form_values": dict(form),
            },
            status_code=exc.status_code,
        )
    await db.commit()
    return RedirectResponse(url=f"/admin/users/{user.id}", status_code=303)


@router.get("/{user_id}", response_class=HTMLResponse)
async def detail_view(
    user_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    user = await UserRepository(db).get(user_id)
    if not user:
        raise NotFoundError("User not found")
    return templates.render(
        request,
        "admin/users/detail.html",
        {"title": user.full_name or user.username, "user_obj": user},
    )


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_view(
    user_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    user = await UserRepository(db).get(user_id)
    if not user:
        raise NotFoundError("User not found")
    return templates.render(
        request,
        "admin/users/form.html",
        {
            "title": f"Edit {user.username}",
            "mode": "edit",
            "user_obj": user,
            "all_roles": await _load_roles(db),
        },
    )


@router.post("/{user_id}")
async def update_submit(
    user_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = UserUpdate(
        email=(form.get("email") or "").strip() or None,
        full_name=(form.get("full_name") or "").strip() or None,
        is_active=form.get("is_active") == "true",
        role_names=form.getlist("role_names"),
    )
    try:
        await UserService(db).update(user_id, payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(url=f"/admin/users/{user_id}/edit?error={exc.message}", status_code=303)
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/password")
async def password_submit(
    user_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = UserPasswordChange(
        old_password=(form.get("old_password") or ""),
        new_password=(form.get("new_password") or ""),
    )
    try:
        await UserService(db).change_password(user_id, payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(url=f"/admin/users/{user_id}?error={exc.message}", status_code=303)
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/deactivate")
async def deactivate_submit(
    user_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    await UserService(db).deactivate(user_id, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)