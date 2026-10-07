"""CSRF protection for browser sessions.

Double-submit cookie pattern.

Token sources (in order):
    1. X-CSRF-Token header  (fetch / XHR / HTMX)
    2. `_csrf` form field   (urlencoded OR multipart)

IMPORTANT: We buffer the raw request body once and re-inject it via
request._receive so downstream handlers can parse the form themselves.
Calling `request.form()` here would consume the stream and leave the
route handler with an empty form (the classic BaseHTTPMiddleware trap).
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


def _extract_multipart_field(body: bytes, field_name: str) -> str | None:
    """
    Extract a single text field value from a raw multipart body.

    Looks for:
        Content-Disposition: form-data; name="<field_name>"

        <value>

    Returns the value as a string, or None if not found.
    """
    marker = f'name="{field_name}"'.encode("ascii")
    idx = body.find(marker)
    if idx == -1:
        return None

    # Value starts after the next CRLFCRLF
    header_end = body.find(b"\r\n\r\n", idx)
    if header_end == -1:
        return None
    value_start = header_end + 4

    # Value ends at the next CRLF
    value_end = body.find(b"\r\n", value_start)
    if value_end == -1:
        return None

    return body[value_start:value_end].decode("utf-8", errors="replace")


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
        if header and hmac.compare_digest(cookie, header):
            return await call_next(request)

        form_token = _clean(await self._read_form_token(request))
        if form_token and hmac.compare_digest(cookie, form_token):
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
        """
        Read `_csrf` from the request body.

        Buffers the raw body once, extracts the token, then re-injects
        the body so the route handler can parse it again with
        `await request.form()`. This works for both urlencoded and
        multipart — the route always sees the original body.
        """
        cached = getattr(request.state, "_csrf_form_token", None)
        if cached is not None:
            return cached

        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()

        if content_type not in (URLENCODED, MULTIPART):
            return None

        # Buffer the raw body ONCE
        body = await request.body()

        if content_type == URLENCODED:
            parsed = parse_qs(body.decode("utf-8", errors="replace"))
            token = (parsed.get("_csrf") or [None])[0]
        else:  # multipart
            token = _extract_multipart_field(body, "_csrf")

        # Re-inject the raw body so downstream handlers can read it
        async def _receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = _receive  # type: ignore[attr-defined]

        request.state._csrf_form_token = token
        return token