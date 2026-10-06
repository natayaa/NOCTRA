"""Admin web route for viewing sent emails."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.core.deps import DbSession
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.email.constants import EMAIL_STATUSES
from app.modules.email.repository import EmailLogRepository
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/email-logs", tags=["admin-email"])


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    status_: str | None = Query(None, alias="status"),
    template: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = EmailLogRepository(db).query(status=status_, template=template)
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/email_logs/list.html",
        {
            "title": "Email Log",
            "emails": rows,
            "page_meta": meta,
            "statuses": EMAIL_STATUSES,
            "status_filter": status_ or "",
            "template_filter": template or "",
        },
    )