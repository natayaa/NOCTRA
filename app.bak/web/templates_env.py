from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from core.config import settings
from web.filters import register_filters

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = APP_DIR / "templates"

if not TEMPLATES_DIR.is_dir():
    raise RuntimeError(f"Templates directory not found: {TEMPLATES_DIR}")


class NoctraTemplates(Jinja2Templates):
    """Merges per-request context automatically so routes stay terse."""

    def render(
        self,
        request: Request,
        name: str,
        context: dict[str, Any] | None = None,
        *,
        status_code: int = 200,
    ):
        ctx: dict[str, Any] = dict(context or {})
        ctx.setdefault("csrf_token", getattr(request.state, "csrf_token", ""))
        ctx.setdefault("current_user", getattr(request.state, "user", None))
        ctx.setdefault("flash_messages", getattr(request.state, "flashes", []))
        return self.TemplateResponse(
            request,
            name,
            ctx,
            status_code=status_code,
        )


templates = NoctraTemplates(directory=str(TEMPLATES_DIR))
register_filters(templates)

templates.env.globals.update(
    app_name=settings.APP_NAME,
    app_env=settings.APP_ENV,
    csrf_cookie_name=settings.CSRF_COOKIE_NAME,
    csrf_header_name=settings.CSRF_HEADER_NAME,
)