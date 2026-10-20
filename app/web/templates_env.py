"""Jinja2 templates environment for the admin & public web UI.

Templates are configured with:
- The app's shared filters (`rupiah`, `dt_id`, `date_id`, `pct`, `number`).
- Globals for app metadata, CSRF tokens, and helpers.
- `today()` / `today_local()` that respect `APP_TIMEZONE`, not system TZ.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.core.config import settings
from app.web.filters import register_filters

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = APP_DIR / "templates"

if not TEMPLATES_DIR.is_dir():
    raise RuntimeError(f"Templates directory not found: {TEMPLATES_DIR}")


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _today_local() -> date:
    """
    Today's date in the app's configured timezone.

    `date.today()` returns the system-local date — wrong on any host whose
    clock is UTC (e.g., container). Between 00:00–07:00 WIB this returns
    "yesterday", which breaks comparisons like
    `{% if project.target_end_date < today() %}`.
    """
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


def _csrf_value(request: Request | None) -> str:
    """
    Get the CSRF token for a request.

    Reads `request.state.csrf_token` first (set by CsrfTokenMiddleware).
    Falls back to the cookie — useful in fragments rendered before the
    middleware has run (rare but defensive).
    """
    if request is None:
        return ""
    token = getattr(request.state, "csrf_token", "") or ""
    if not token:
        raw = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
        token = raw.strip('"') if raw else ""
    return token


# ════════════════════════════════════════════════════════════════
# TEMPLATES
# ════════════════════════════════════════════════════════════════

class NoctraTemplates(Jinja2Templates):
    """
    Templates class that seeds request-scoped context automatically.

    Every `render()` call guarantees these context keys exist (unless the
    caller overrode them explicitly):
      - current_path   — request.url.path, for active nav highlighting
      - csrf_token     — for `<input name="_csrf">` and `X-CSRF-Token`
      - current_user   — the authenticated user (or None)
      - flash_messages — list of flash dicts (empty until middleware adds them)
    """

    def render(self, request, name, context=None, *, status_code=200):
        ctx = dict(context or {})

        ctx.setdefault("current_path", request.url.path if request else "")
        ctx.setdefault("csrf_token", _csrf_value(request))
        ctx.setdefault(
            "current_user",
            getattr(request.state, "user", None) if request else None,
        )
        ctx.setdefault(
            "flash_messages",
            getattr(request.state, "flashes", []) if request else [],
        )

        return self.TemplateResponse(
            request, name, ctx, status_code=status_code,
        )


templates = NoctraTemplates(directory=str(TEMPLATES_DIR))


# ════════════════════════════════════════════════════════════════
# GLOBALS
# ════════════════════════════════════════════════════════════════

templates.env.globals.update(
    # ── Time ────────────────────────────────────────────
    today=_today_local,
    today_local=_today_local,
    # ── App metadata ────────────────────────────────────
    app_name=settings.APP_NAME,
    app_env=settings.APP_ENV,
    # Convenience booleans — cleaner than `{% if app_env == "..." %}`.
    app_env_is_production=settings.is_production,
    app_env_is_development=(settings.APP_ENV == "development"),
    # ── CSRF ────────────────────────────────────────────
    csrf_cookie_name=settings.CSRF_COOKIE_NAME,
    csrf_header_name=settings.CSRF_HEADER_NAME,
    csrf_value=_csrf_value,
)


# Filters — imported from filters.py
register_filters(templates)