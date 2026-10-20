"""Admin web routes for viewing the audit log."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.constants import AuditAction, PermissionCode
from app.core.deps import DbSession
from app.core.pagination import PageParams, paginate, page_params
from app.modules.audit.repository import AuditRepository
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.web.admin._perms import read
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])

# Derived from the canonical enum — never drifts.
ACTIONS = sorted(a.value for a in AuditAction)

TABLES = sorted({
    "users", "roles", "permissions", "customers", "customer_contacts",
    "vehicles", "vehicle_brands", "vehicle_models",
    "inquiries", "inquiry_photos",
    "materials", "suppliers", "inventory_transactions",
    "purchase_orders", "purchase_order_items",
    "projects", "project_items", "employees",
    "invoices", "invoice_items", "payments", "expenses",
    "pricing_rules", "pricing_snapshots",
    "app_settings",
})


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    table_name: str | None = Query(None),
    since_days: int | None = Query(None, ge=1, le=365),
    _=read(PermissionCode.AUDIT_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    since = None
    if since_days:
        since = datetime.now(UTC) - timedelta(days=since_days)

    stmt = AuditRepository(db).query(
        user_id=user_id,
        action=action,
        table_name=table_name,
        since=since,
    )
    rows, meta = await paginate(db, stmt, params)

    # ── Enrich: user names for the current page ────────
    # Select specific columns (NOT the full User entity) — this avoids
    # triggering eager-load cascades like `User.roles -> Role.users`.
    uids = {r.user_id for r in rows if r.user_id}
    users: dict[UUID, str] = {}
    if uids:
        user_rows = (
            await db.execute(
                select(User.id, User.full_name, User.username)
                .where(User.id.in_(uids))
            )
        ).all()
        users = {
            uid: (full_name or username)
            for uid, full_name, username in user_rows
        }

    # ── Enrich: choices for the user-filter dropdown ───
    choice_rows = (
        await db.execute(
            select(User.id, User.full_name, User.username)
            .where(User.is_active.is_(True))
            .order_by(User.full_name)
            .limit(500)
        )
    ).all()
    user_choices: list[tuple[UUID, str]] = [
        (uid, (full_name or username))
        for uid, full_name, username in choice_rows
    ]

    # ── qs helper for pagination that preserves filters ─
    def qs(page: int | None = None, **overrides) -> str:
        base = {
            "action": action or "",
            "table_name": table_name or "",
            "since_days": str(since_days) if since_days else "",
            "user_id": str(user_id) if user_id else "",
        }
        if page is not None:
            base["page"] = str(page)
        base.update({k: ("" if v is None else str(v)) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/audit/list.html",
        {
            "title": "Audit Log",
            "entries": rows,
            "page_meta": meta,
            "users_by_id": users,
            "user_choices": user_choices,
            "actions": ACTIONS,
            "tables": TABLES,
            "action_filter": action or "",
            "table_filter": table_name or "",
            "since_days_filter": since_days,
            "user_id_filter": user_id,
            "qs": qs,
        },
    )