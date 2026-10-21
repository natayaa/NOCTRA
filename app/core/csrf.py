"""CSRF protection — double-submit cookie pattern.

Token sources (in order):
    1. X-CSRF-Token header   (fetch / XHR / HTMX)
    2. `_csrf` form field    (urlencoded OR multipart)

Body handling:
    For `x-www-form-urlencoded` we read the (small) body. For multipart
    we go straight to `request.form()`, which streams into Starlette's
    spooled temp files (~1 MB threshold) instead of buffering the whole
    upload in RAM. The resulting `FormData` is cached on the request, so
    the downstream route can call `request.form()` again and gets the
    same object.

    We deliberately use Starlette's parser for multipart rather than
    substring-searching for `name="_csrf"` — the latter also matches
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
from app.core.request_id import get_request_id

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
EXEMPT_PATHS = {
    "/health",
    "/healthz",
    "/readyz",
    "/api/v1/auth/login",
    "/api/v1/auth/token",
    # /api/v1/auth/refresh is intentionally NOT exempt: the refresh token
    # is cookie-borne, so a cross-site POST would rotate the session.
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
            request_id=get_request_id(),
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
                headers={
                    "HX-Retarget": "body",
                    "HX-Reswap": "afterbegin",
                    "X-Request-ID": get_request_id(),
                },
            )
        return JSONResponse(
            {
                "error": {
                    "code": "csrf_failed",
                    "message": reason,
                    "request_id": get_request_id(),
                }
            },
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
        if hasattr(request.state, "_csrf_form_token"):
            return request.state._csrf_form_token

        content_type = (
            request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        )
        token: str | None = None

        if content_type == URLENCODED:
            body = await request.body()
            if body:
                try:
                    parsed = parse_qs(body.decode("utf-8", errors="replace"))
                    values = parsed.get("_csrf") or []
                    token = values[0] if values else None
                except Exception as exc:
                    log.warning("csrf_urlencoded_parse_error", error=str(exc))
        elif content_type == MULTIPART:
            # Starlette streams multipart parts to SpooledTemporaryFile,
            # so a 10 MB upload costs ~1 MB RAM per request, not 10 MB.
            try:
                form = await request.form()
                raw = form.get("_csrf")
                if isinstance(raw, str):  # ignore uploaded-file masquerade
                    token = raw
            except Exception as exc:
                log.warning("csrf_multipart_parse_error", error=str(exc))

        request.state._csrf_form_token = token
        return token