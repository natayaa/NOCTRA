"""Admin web routes for roles and permissions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select

from app.core.constants import AuditAction, PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import get_current_user
from app.modules.rbac.models import Permission, Role, RolePermission
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/roles", tags=["admin-roles"])

_FORM_ERRORS = (AppError, ValueError, KeyError)


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    _=read(PermissionCode.ROLE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    rows = list((await db.execute(select(Role).order_by(Role.name))).scalars().all())

    # Batch permission counts — 1 query instead of N.
    counts: dict[UUID, int] = {}
    if rows:
        role_ids = [r.id for r in rows]
        count_rows = (
            await db.execute(
                select(
                    RolePermission.role_id,
                    func.count(RolePermission.permission_id).label("n"),
                )
                .where(RolePermission.role_id.in_(role_ids))
                .group_by(RolePermission.role_id)
            )
        ).all()
        counts = {rid: int(n) for rid, n in count_rows}

    return templates.render(
        request,
        "admin/roles/list.html",
        {"title": "Roles", "roles": rows, "permission_counts": counts},
    )


@router.get("/{role_id}", response_class=HTMLResponse)
async def detail_view(
    role_id: UUID,
    request: Request,
    db: DbSession,
    _=read(PermissionCode.ROLE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    role = await db.get(Role, role_id)
    if not role:
        raise NotFoundError("Role not found")

    all_perms = list(
        (await db.execute(select(Permission).order_by(Permission.code)))
        .scalars()
        .all()
    )

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
    role_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.ROLE_UPDATE),
    current=Depends(get_current_user),
):
    role = await db.get(Role, role_id)
    if not role:
        raise NotFoundError("Role not found")

    try:
        form = await request.form()
        selected_codes = set(form.getlist("permission_codes"))

        all_perms = list((await db.execute(select(Permission))).scalars().all())
        by_code = {p.code: p for p in all_perms}

        current_rows = (
            await db.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            )
        ).scalars().all()
        current_ids = {rp.permission_id for rp in current_rows}

        added: list[str] = []
        removed: list[str] = []

        # Add
        for code in selected_codes:
            perm = by_code.get(code)
            if perm and perm.id not in current_ids:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                added.append(code)

        # Remove
        for rp in current_rows:
            # Look up code for audit
            for code, perm in by_code.items():
                if perm.id == rp.permission_id and code not in selected_codes:
                    await db.delete(rp)
                    removed.append(code)
                    break

        await db.flush()

        await AuditService(db).log(
            action=AuditAction.UPDATE,          # ← was raw string
            table_name="roles",
            record_id=role.id,
            user_id=current.id,
            old_data={"permission_count": len(current_ids)},
            new_data={
                "permission_count": len(selected_codes),
                "added": added,
                "removed": removed,
            },
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/roles/{role_id}?error={getattr(exc, 'message', str(exc))}",
            status_code=303,
        )

    return RedirectResponse(url=f"/admin/roles/{role_id}", status_code=303)