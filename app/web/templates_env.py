from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from datetime import date

from app.core.config import settings
from app.web.filters import register_filters

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = APP_DIR / "templates"

if not TEMPLATES_DIR.is_dir():
    raise RuntimeError(f"Templates directory not found: {TEMPLATES_DIR}")


def _csrf_value(request: Request | None) -> str:
    if request is None:
        return ""
    token = getattr(request.state, "csrf_token", "") or ""
    if not token:
        raw = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
        token = raw.strip('"') if raw else ""
    return token


class NoctraTemplates(Jinja2Templates):
    def render(self, request, name, context=None, *, status_code=200):
        ctx = dict(context or {})
        ctx.setdefault("csrf_token", getattr(request.state, "csrf_token", ""))
        ctx.setdefault("current_user", getattr(request.state, "user", None))
        ctx.setdefault("flash_messages", getattr(request.state, "flashes", []))
        return self.TemplateResponse(request, name, ctx, status_code=status_code)


templates = NoctraTemplates(directory=str(TEMPLATES_DIR))
templates.env.globals["today"] = lambda: date.today()
register_filters(templates)

templates.env.globals.update(
    app_name=settings.APP_NAME,
    app_env=settings.APP_ENV,
    csrf_cookie_name=settings.CSRF_COOKIE_NAME,
    csrf_header_name=settings.CSRF_HEADER_NAME,
)
templates.env.globals["csrf_value"] = _csrf_value