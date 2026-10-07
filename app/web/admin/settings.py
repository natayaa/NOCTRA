"""Admin web routes for the settings page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.modules.auth.dependencies import get_current_user
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.service import SettingsService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    rows = list((await db.execute(SettingsRepository(db).query())).scalars().all())

    grouped: dict[str, list] = {}
    for s in rows:
        grouped.setdefault(s.category or "general", []).append(s)

    return templates.render(
        request,
        "admin/settings/list.html",
        {"title": "Settings", "settings_groups": grouped, "total": len(rows)},
    )


@router.post("")
async def update_submit(
    request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    svc = SettingsService(db)

    # Every form field is a setting key
    for key, value in form.items():
        if key.startswith("_"):
            continue
        await svc.upsert(key, value)

    await db.commit()
    return RedirectResponse(url="/admin/settings", status_code=303)