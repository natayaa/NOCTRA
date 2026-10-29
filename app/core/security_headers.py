"""HTTP security headers.

The admin is cookie-authenticated, so a page that can be framed is a
clickjacking target and any injected script runs with full session
authority. These headers are the second line of defense behind Jinja's
autoescaping:

- `Content-Security-Policy` — restricts scripts, styles, fonts, and
  framing. Inline scripts remain allowed because the templates rely on
  them; that is weaker than a nonce policy but still blocks arbitrary
  third-party origins. The CDN allowlist comes from settings; emptying
  it after vendoring the assets tightens the policy to `'self'`.
- `X-Frame-Options: DENY` — covers browsers that ignore `frame-ancestors`.
- `X-Content-Type-Options: nosniff` — stops MIME-sniffed execution of
  uploaded media (inquiry photos are served from `/media`).
- `Referrer-Policy` — reset-password tokens travel in a query string;
  never leak them cross-origin.
- `Permissions-Policy` — the app uses none of the powerful browser APIs.
- HSTS in production only; sending it over plain HTTP is meaningless.

Applied as the OUTERMOST middleware so error responses (404, CSRF 403,
validation JSON) carry the headers too.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


def build_csp() -> str:
    script = " ".join(["'self'", "'unsafe-inline'", *settings.SECURITY_CSP_SCRIPT_ORIGINS])
    style = " ".join(["'self'", "'unsafe-inline'", *settings.SECURITY_CSP_STYLE_ORIGINS])
    font = " ".join(["'self'", "data:", *settings.SECURITY_CSP_FONT_ORIGINS])
    return "; ".join([
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        f"script-src {script}",
        f"style-src {style}",
        f"font-src {font}",
        "img-src 'self' data: blob:",
        "media-src 'self' blob:",
        "connect-src 'self'",
        "worker-src 'self' blob:",
        "manifest-src 'self'",
    ])


def build_security_headers(*, is_production: bool) -> dict[str, str]:
    """Headers applied to every response. Pure function — easy to test."""
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        ),
        "Cross-Origin-Opener-Policy": "same-origin",
    }
    if settings.SECURITY_CSP_ENABLED:
        headers["Content-Security-Policy"] = build_csp()
    if is_production:
        headers["Strict-Transport-Security"] = (
            f"max-age={settings.SECURITY_HSTS_MAX_AGE}; includeSubDomains"
        )
    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if not settings.SECURITY_HEADERS_ENABLED:
            return response

        headers = build_security_headers(is_production=settings.is_production)
        is_html = response.headers.get("content-type", "").startswith("text/html")

        # Authenticated admin pages contain customer data and CSRF tokens.
        # Never let a browser or shared proxy keep them after sign-out.
        if is_html and request.url.path.startswith("/admin"):
            response.headers.setdefault("Cache-Control", "no-store, private")

        for name, value in headers.items():
            # CSP is only meaningful for documents; skip it on images,
            # JSON, and static assets to keep responses lean.
            if name == "Content-Security-Policy" and not is_html:
                continue
            response.headers.setdefault(name, value)
        return response
