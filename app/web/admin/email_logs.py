"""Admin web route for viewing sent emails."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.email.constants import EMAIL_STATUSES
from app.modules.email.models import EmailLog
from app.modules.email.repository import EmailLogRepository
from app.web.admin._perms import read
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/email-logs", tags=["admin-email"])


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    status_: str | None = Query(None, alias="status"),
    template: str | None = Query(None),
    _=read(PermissionCode.AUDIT_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = EmailLogRepository(db).query(status=status_, template=template)
    rows, meta = await paginate(db, stmt, params)

    # Distinct template names actually present in the log — data-driven
    # dropdown so admins see what was really sent, not a hardcoded enum.
    template_rows = (
        await db.execute(
            select(EmailLog.template)
            .distinct()
            .where(EmailLog.template.isnot(None))
            .order_by(EmailLog.template)
        )
    ).scalars().all()
    template_choices = [t for t in template_rows if t]

    # ── qs helper that preserves filters ──────────────
    def qs(page: int | None = None, **overrides) -> str:
        base = {
            "status": status_ or "",
            "template": template or "",
        }
        if page is not None:
            base["page"] = str(page)
        base.update({k: ("" if v is None else str(v)) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

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
            "template_choices": template_choices,
            "qs": qs,
        },
    )