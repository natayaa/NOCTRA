"""Admin web routes for the settings page."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.modules.auth.dependencies import get_current_user
from app.modules.settings.constants import KNOWN_SETTINGS, is_secret_key
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.service import SettingsService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

_FORM_ERRORS = (AppError, ValueError, KeyError)


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

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

    # Mask secret values so they never reach the HTML response body.
    # The template does NOT use `s.value` for secret fields — it renders
    # an empty input with a "(set)" placeholder. But we still mask here
    # as defense-in-depth: if a template later forgets to check
    # `is_secret`, the value won't leak.
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
            "known_settings": KNOWN_SETTINGS,
            "error": request.query_params.get("error"),
            "saved": request.query_params.get("saved") == "1",
        },
    )


# ════════════════════════════════════════════════════════════════
# UPDATE
# ════════════════════════════════════════════════════════════════

@router.post("")
async def update_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.SETTINGS_UPDATE),
    current=Depends(get_current_user),
):
    form = await request.form()
    svc = SettingsService(db)

    existing_keys = {
        s.key
        for s in (await db.execute(SettingsRepository(db).query())).scalars().all()
    }

    try:
        for key, value in form.items():
            if key.startswith("_") or key not in existing_keys:
                continue

            raw = str(value) if value is not None else ""
            str_value = raw.strip() or None

            # ── CRITICAL: secret settings ──────────────────────
            # Skip submissions that would silently overwrite the real
            # secret value. Cases:
            #   - None / empty string      → user left field blank, keep
            #   - "***"                    → user saved without touching
            #                                 the masked field
            if is_secret_key(key):
                if str_value in (None, "", "***"):
                    continue  # keep existing value untouched

            await svc.upsert(key, value=str_value, actor=current)

        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(
            getattr(exc, "message", None) or str(exc) or "Invalid input",
            safe="",
        )
        return RedirectResponse(
            url=f"/admin/settings?error={msg}",
            status_code=303,
        )

    return RedirectResponse(url="/admin/settings?saved=1", status_code=303)