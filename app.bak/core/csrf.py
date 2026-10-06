import hmac
import secrets
from base64 import b64encode

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from core.config import settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
EXEMPT_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh", "/health", "/healthz"}
EXEMPT_PREFIXES = ("/static/", "/favicon")


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Double-submit cookie CSRF for browser sessions.
    API calls authenticated with Bearer tokens are exempt
    (they cannot be triggered by cross-site form posts).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            self._ensure_cookie(request, response)
            return response

        if self._is_exempt(request) or self._is_bearer_auth(request):
            return await call_next(request)

        cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
        header = request.headers.get(settings.CSRF_HEADER_NAME)
        if not cookie or not header or not hmac.compare_digest(cookie, header):
            return JSONResponse(
                {"error": {"code": "csrf_failed", "message": "CSRF token invalid or missing"}},
                status_code=403,
            )

        return await call_next(request)

    @staticmethod
    def _is_exempt(request: Request) -> bool:
        path = request.url.path
        return path in EXEMPT_PATHS or any(path.startswith(p) for p in EXEMPT_PREFIXES)

    @staticmethod
    def _is_bearer_auth(request: Request) -> bool:
        return request.headers.get("authorization", "").lower().startswith("bearer ")

    @staticmethod
    def _ensure_cookie(request: Request, response: Response) -> None:
        if settings.CSRF_COOKIE_NAME in request.cookies:
            return
        token = b64encode(secrets.token_bytes(settings.CSRF_TOKEN_BYTES)).decode()
        response.set_cookie(
            settings.CSRF_COOKIE_NAME,
            token,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=False,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            max_age=settings.SESSION_MAX_AGE_SECONDS,
        )