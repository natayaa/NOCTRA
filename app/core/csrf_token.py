"""Ensures request.state.csrf_token and the CSRF cookie exist.

This is the *only* place the CSRF cookie is written.
"""

from __future__ import annotations

import secrets
from base64 import b64encode

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    return v


class CsrfTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cookie_token = _clean(request.cookies.get(settings.CSRF_COOKIE_NAME))
        token = cookie_token or b64encode(
            secrets.token_bytes(settings.CSRF_TOKEN_BYTES)
        ).decode()

        request.state.csrf_token = token

        response = await call_next(request)

        # Only set the cookie if the client didn't already have a valid one.
        if not cookie_token:
            response.set_cookie(
                settings.CSRF_COOKIE_NAME,
                token,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=False,  # must be JS-readable for double-submit
                samesite=settings.SESSION_COOKIE_SAMESITE,
                max_age=settings.SESSION_MAX_AGE_SECONDS,
                path="/",
            )
        return response