"""Admin web routes for roles and permissions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import get_current_user
from app.modules.rbac.models import Permission, Role, RolePermission
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/roles", tags=["admin-roles"])


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    rows = list((await db.execute(select(Role).order_by(Role.name))).scalars().all())

    # Permission counts per role
    counts = {}
    for r in rows:
        c = (
            await db.execute(
                select(__import__("sqlalchemy").func.count())
                .select_from(RolePermission)
                .where(RolePermission.role_id == r.id)
            )
        ).scalar_one()
        counts[r.id] = c

    return templates.render(
        request,
        "admin/roles/list.html",
        {"title": "Roles", "roles": rows, "permission_counts": counts},
    )


@router.get("/{role_id}", response_class=HTMLResponse)
async def detail_view(
    role_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    role = await db.get(Role, role_id)
    if not role:
        raise NotFoundError("Role not found")

    # All permissions grouped by prefix (e.g. "user", "customer")
    all_perms = list((await db.execute(
        select(Permission).order_by(Permission.code)
    )).scalars().all())

    grouped: dict[str, list[Permission]] = {}
    for p in all_perms:
        prefix = p.code.split(":", 1)[0]
        grouped.setdefault(prefix, []).append(p)

    assigned = {p.code for p in role.permissions}

    return templates.render(
        request,
        "admin/roles/detail.html",
        {
            "title": role.name,
            "role": role,
            "permission_groups": grouped,
            "assigned_codes": assigned,
        },
    )


@router.post("/{role_id}")
async def update_submit(
    role_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    role = await db.get(Role, role_id)
    if not role:
        raise NotFoundError("Role not found")

    form = await request.form()
    selected_codes = set(form.getlist("permission_codes"))

    # Load permissions
    all_perms = list((await db.execute(select(Permission))).scalars().all())
    by_code = {p.code: p for p in all_perms}

    # Current assignments
    current_assignments = {
        rp.permission_id for rp in (
            await db.execute(select(RolePermission).where(RolePermission.role_id == role.id))
        ).scalars().all()
    }

    # Add new
    for code in selected_codes:
        perm = by_code.get(code)
        if perm and perm.id not in current_assignments:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    # Remove old
    for code, perm in by_code.items():
        if code not in selected_codes and perm.id in current_assignments:
            rp = await db.get(RolePermission, (role.id, perm.id))
            if rp:
                await db.delete(rp)

    await db.flush()
    await AuditService(db).log(
        action="UPDATE",
        table_name="roles",
        record_id=role.id,
        user_id=current.id,
        new_data={"permission_count": len(selected_codes)},
    )
    await db.commit()
    return RedirectResponse(url=f"/admin/roles/{role_id}", status_code=303)