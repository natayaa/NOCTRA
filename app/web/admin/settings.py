"""Admin web routes for the settings page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.modules.auth.dependencies import get_current_user
from app.modules.settings.constants import KNOWN_SETTINGS
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.service import SettingsService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

_FORM_ERRORS = (AppError, ValueError, KeyError)


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    _=read(PermissionCode.SETTINGS_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    rows = list((await db.execute(SettingsRepository(db).query())).scalars().all())

    grouped: dict[str, list] = {}
    for s in rows:
        grouped.setdefault(s.category or "general", []).append(s)

    # Mask secret values in the view. Reveal is only possible through the
    # API endpoint with SETTINGS_UPDATE + ?reveal=true.
    for group in grouped.values():
        for s in group:
            if s.is_secret and s.value:
                s.value = "***"  # type: ignore[misc]

    return templates.render(
        request,
        "admin/settings/list.html",
        {
            "title": "Settings",
            "settings_groups": grouped,
            "total": len(rows),
            "known_settings": KNOWN_SETTINGS,   # for help text
        },
    )


@router.post("")
async def update_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.SETTINGS_UPDATE),
    current=Depends(get_current_user),
):
    form = await request.form()
    svc = SettingsService(db)

    # Only update keys that already exist in the DB. Prevents mass-assign
    # of arbitrary setting keys via the form (the "unknown key is a create"
    # behaviour is only reachable via the API when intentionally used).
    existing_keys = {
        s.key
        for s in (await db.execute(SettingsRepository(db).query())).scalars().all()
    }

    try:
        for key, value in form.items():
            if key.startswith("_") or key not in existing_keys:
                continue
            str_value = str(value).strip() if value is not None else None
            await svc.upsert(
                key,
                value=str_value if str_value else None,
                actor=current,                 # ← was missing
            )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        # Re-render list with error banner
        rows = list(
            (await db.execute(SettingsRepository(db).query())).scalars().all()
        )
        grouped: dict[str, list] = {}
        for s in rows:
            if s.is_secret and s.value:
                s.value = "***"  # type: ignore[misc]
            grouped.setdefault(s.category or "general", []).append(s)
        return templates.render(
            request,
            "admin/settings/list.html",
            {
                "title": "Settings",
                "settings_groups": grouped,
                "total": len(rows),
                "known_settings": KNOWN_SETTINGS,
                "error": getattr(exc, "message", str(exc)),
            },
            status_code=getattr(exc, "status_code", 400),
        )

    return RedirectResponse(url="/admin/settings", status_code=303)