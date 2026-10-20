"""CSRF protection — double-submit cookie pattern.

Token sources (in order):
    1. X-CSRF-Token header   (fetch / XHR / HTMX)
    2. `_csrf` form field    (urlencoded OR multipart)

Body handling:
    `await request.body()` caches `_body` on the Request. Any subsequent
    `await request.form()` or `await request.body()` in the route reuses it,
    so parsing the token here never starves the downstream handler.

    We deliberately use Starlette's `request.form()` for multipart rather
    than substring-searching for `name="_csrf"` — the latter also matches
    `filename="_csrf"`, allowing a file upload to spoof the token.
"""

from __future__ import annotations

import hmac
from urllib.parse import parse_qs, unquote

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import log

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
EXEMPT_PATHS = {
    "/health",
    "/healthz",
    "/readyz",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/token",
}
EXEMPT_PREFIXES = ("/static/", "/favicon", "/media/")

URLENCODED = "application/x-www-form-urlencoded"
MULTIPART = "multipart/form-data"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    return unquote(v)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)

        if self._is_exempt(request) or self._is_bearer_auth(request):
            return await call_next(request)

        cookie = _clean(request.cookies.get(settings.CSRF_COOKIE_NAME))
        if not cookie:
            return self._reject(request, "cookie_missing")

        header = _clean(request.headers.get(settings.CSRF_HEADER_NAME))
        if header and hmac.compare_digest(cookie.encode(), header.encode()):
            return await call_next(request)

        form_token = _clean(await self._read_form_token(request))
        if form_token and hmac.compare_digest(cookie.encode(), form_token.encode()):
            return await call_next(request)

        log.warning(
            "csrf_rejected",
            path=request.url.path,
            method=request.method,
            has_cookie=bool(cookie),
            has_header=bool(header),
            has_form=bool(form_token),
            content_type=request.headers.get("content-type", "")[:64],
            ip=request.client.host if request.client else None,
            request_id=getattr(request.state, "request_id", None),
        )
        return self._reject(request, "token_invalid")

    @staticmethod
    def _reject(request: Request, reason: str) -> Response:
        is_htmx = request.headers.get("hx-request", "").lower() == "true"
        if is_htmx:
            html = (
                '<div class="flash flash-error" role="alert">'
                "Your session expired or the form was tampered with. "
                "Please refresh the page and try again."
                "</div>"
            )
            return Response(
                html,
                status_code=403,
                media_type="text/html",
                headers={"HX-Retarget": "body", "HX-Reswap": "afterbegin"},
            )
        return JSONResponse(
            {"error": {"code": "csrf_failed", "message": reason}},
            status_code=403,
        )

    @staticmethod
    def _is_exempt(request: Request) -> bool:
        path = request.url.path
        return path in EXEMPT_PATHS or any(path.startswith(p) for p in EXEMPT_PREFIXES)

    @staticmethod
    def _is_bearer_auth(request: Request) -> bool:
        return request.headers.get("authorization", "").lower().startswith("bearer ")

    @staticmethod
    async def _read_form_token(request: Request) -> str | None:
        """Read `_csrf` from the body without starving the route handler."""
        cached = getattr(request.state, "_csrf_form_token", None)
        if cached is not None:
            return cached

        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
        if content_type not in (URLENCODED, MULTIPART):
            request.state._csrf_form_token = None
            return None

        # Cache the body ONCE. Starlette's stream() re-serves `_body`
        # to any subsequent form()/body() call in the route.
        body = await request.body()
        if not body:
            request.state._csrf_form_token = None
            return None

        token: str | None = None
        try:
            if content_type == URLENCODED:
                parsed = parse_qs(body.decode("utf-8", errors="replace"))
                values = parsed.get("_csrf") or []
                token = values[0] if values else None
            else:  # multipart — Starlette's parser handles filename vs field correctly
                form = await request.form()
                raw = form.get("_csrf")
                if isinstance(raw, str):        # ignore uploaded-file masquerade
                    token = raw
        except Exception as exc:                # malformed multipart
            log.warning("csrf_form_parse_error", error=str(exc))

        request.state._csrf_form_token = token
        return token