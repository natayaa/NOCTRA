"""Admin web routes for users."""

from __future__ import annotations

from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.rbac.repository import RoleRepository
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    AdminPasswordReset,       # ← was UserPasswordChange (removed in users module fix)
    UserCreate,
    UserUpdate,
)
from app.modules.users.service import UserService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


async def _load_roles(db):
    return await RoleRepository(db).list()


def _form_error(exc: Exception) -> str:
    return (getattr(exc, "message", None) or str(exc) or "Invalid input").strip()


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
    role_name: str | None = Query(None, max_length=50),
    _=read(PermissionCode.USER_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = UserRepository(db).query(
        q=q, is_active=is_active, role_name=role_name,
    )
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/users/list.html",
        {
            "title": "Users",
            "users": rows,
            "page_meta": meta,
            "q": q or "",
            "is_active_filter": is_active,
            "role_filter": role_name or "",
        },
    )


# ════════════════════════════════════════════════════════════════
# NEW / CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.USER_CREATE),
    current=Depends(get_current_user),
) -> HTMLResponse:
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
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.USER_CREATE),
    current=Depends(get_current_user),
):
    form = await request.form()

    async def _render_error(msg: str, status_code: int = 400):
        return templates.render(
            request,
            "admin/users/form.html",
            {
                "title": "New User",
                "mode": "create",
                "user_obj": None,
                "all_roles": await _load_roles(db),
                "error": msg,
                "form_values": dict(form),
            },
            status_code=status_code,
        )

    try:
        payload = UserCreate(
            username=(form.get("username") or "").strip(),
            email=(form.get("email") or "").strip(),
            full_name=(form.get("full_name") or "").strip(),
            password=(form.get("password") or ""),
            is_active=("is_active" in form and form.get("is_active") == "true"),
            is_superuser=("is_superuser" in form and form.get("is_superuser") == "true"),
            role_names=form.getlist("role_names"),
        )
        user = await UserService(db).create(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return await _render_error(
            _form_error(exc), getattr(exc, "status_code", 400)
        )

    return RedirectResponse(url=f"/admin/users/{user.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{user_id}", response_class=HTMLResponse)
async def detail_view(
    user_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=read(PermissionCode.USER_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    user = await UserRepository(db).get(user_id)
    if not user:
        raise NotFoundError("User not found")
    return templates.render(
        request,
        "admin/users/detail.html",
        {
            "title": user.full_name or user.username,
            "user_obj": user,
            "error": error,
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT
# ════════════════════════════════════════════════════════════════

@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_view(
    user_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=write(PermissionCode.USER_UPDATE),
    current=Depends(get_current_user),
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
            "error": error,
        },
    )


@router.post("/{user_id}")
async def update_submit(
    user_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.USER_UPDATE),
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
        payload = UserUpdate(
            email=(form.get("email") or "").strip() or None,
            full_name=(form.get("full_name") or "").strip() or None,
            is_active=("is_active" in form and form.get("is_active") == "true"),
            role_names=form.getlist("role_names"),
        )
        await UserService(db).update(user_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/users/{user_id}/edit?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )

    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# ADMIN PASSWORD RESET
# ════════════════════════════════════════════════════════════════
# NOTE: this endpoint requires the users module follow-up to have
# been applied (`AdminPasswordReset` + `UserService.reset_password`).
# If the old API is still in use (`UserPasswordChange` + `change_password`),
# this file will fail to import. In that case, revert the imports at the
# top of this file until the users module is updated.

@router.post("/{user_id}/reset-password")
async def password_submit(
    user_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.USER_UPDATE),
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
        payload = AdminPasswordReset(
            new_password=(form.get("new_password") or ""),
        )
        await UserService(db).reset_password(user_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/users/{user_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )

    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DEACTIVATE / REACTIVATE
# ════════════════════════════════════════════════════════════════

@router.post("/{user_id}/deactivate")
async def deactivate_submit(
    user_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.USER_DELETE),
    current=Depends(get_current_user),
):
    try:
        await UserService(db).deactivate(user_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/users/{user_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/reactivate")
async def reactivate_submit(
    user_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.USER_UPDATE),
    current=Depends(get_current_user),
):
    try:
        await UserService(db).reactivate(user_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/users/{user_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)