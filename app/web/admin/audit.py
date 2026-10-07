"""Admin web routes for viewing the audit log."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.deps import DbSession
from app.core.pagination import PageParams, paginate, page_params
from app.modules.audit.repository import AuditRepository
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])

ACTIONS = [
    "CREATE", "UPDATE", "DELETE",
    "LOGIN", "LOGIN_FAILED", "LOGOUT",
    "EXPORT", "STATUS_CHANGE", "ASSIGN",
    "STOCK_IN", "STOCK_OUT", "PRICE_CHANGE",
    "COST_ENTRY", "PAYMENT_RECEIVED", "PAYMENT_MADE",
    "INVOICE_SENT", "EXPENSE_RECORDED",
]

TABLES = [
    "users", "roles", "permissions", "customers", "customer_contacts",
    "vehicles", "vehicle_brands", "vehicle_models",
    "inquiries", "inquiry_photos",
    "materials", "suppliers", "inventory_transactions",
    "purchase_orders", "purchase_order_items",
    "projects", "project_items", "employees",
    "invoices", "invoice_items", "payments", "expenses",
    "pricing_rules", "pricing_snapshots",
    "app_settings",
]


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    table_name: str | None = Query(None),
    since_days: int | None = Query(None, ge=1, le=365),
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

    # Look up user names for the entries on this page
    uids = {r.user_id for r in rows if r.user_id}
    users: dict = {}
    if uids:
        user_rows = (
            await db.execute(select(User).where(User.id.in_(uids)))
        ).scalars().all()
        users = {u.id: u for u in user_rows}

    return templates.render(
        request,
        "admin/audit/list.html",
        {
            "title": "Audit Log",
            "entries": rows,
            "page_meta": meta,
            "users_by_id": users,
            "actions": ACTIONS,
            "tables": TABLES,
            "action_filter": action or "",
            "table_filter": table_name or "",
            "since_days_filter": since_days,
        },
    )