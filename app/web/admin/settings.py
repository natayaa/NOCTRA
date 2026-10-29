"""Admin web routes for the settings page."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.datastructures import FormData

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.modules.auth.dependencies import get_current_user
from app.modules.settings.constants import KNOWN_SETTINGS, is_secret_key
from app.modules.settings.models import AppSetting
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.service import SettingsService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

_FORM_ERRORS = (AppError, ValueError, KeyError)

# Only category slugs survive the round-trip; anything else is dropped so
# the redirect can never echo arbitrary user input back into the URL.
_TAB_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


def _tab_suffix(form: FormData) -> str:
    """Return `&tab=<category>` when the form carried a valid active tab."""
    tab = str(form.get("_tab") or "")
    return f"&tab={tab}" if _TAB_RE.fullmatch(tab) else ""


@dataclass(frozen=True, slots=True)
class SettingView:
    key: str
    value: str | None
    category: str
    description: str | None
    is_secret: bool


def to_setting_view(row: AppSetting) -> SettingView:
    """Return a detached, masked copy of a settings row."""
    is_secret = bool(row.is_secret)
    return SettingView(
        key=row.key,
        value="***" if is_secret and row.value else row.value,
        category=row.category or "general",
        description=row.description,
        is_secret=is_secret,
    )


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

    # Build masked copies instead of mutating the ORM rows: the
    # request-scoped session commits on teardown, so assigning "***"
    # here used to overwrite the stored secret.
    grouped: dict[str, list[SettingView]] = {}
    for s in rows:
        view = to_setting_view(s)
        grouped.setdefault(view.category, []).append(view)

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
    tab_suffix = _tab_suffix(form)

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
            url=f"/admin/settings?error={msg}{tab_suffix}",
            status_code=303,
        )

    return RedirectResponse(url=f"/admin/settings?saved=1{tab_suffix}", status_code=303)
