"""HTTP security surface: headers, throttling buckets, logout method."""

import pytest
from httpx import AsyncClient
from starlette.requests import Request

from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_headers import build_security_headers


def _request(path: str) -> Request:
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("203.0.113.7", 4444),
        "server": ("localhost", 80),
    })


@pytest.mark.asyncio
async def test_html_pages_carry_security_headers(client: AsyncClient):
    r = await client.get("/contact")

    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in r.headers["permissions-policy"]

    csp = r.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "script-src 'self' 'unsafe-inline'" in csp


@pytest.mark.asyncio
async def test_json_and_error_responses_carry_headers(client: AsyncClient):
    r = await client.get("/definitely-not-a-page")

    assert r.status_code == 404
    assert r.headers["x-frame-options"] == "DENY"
    # CSP is document-only; JSON responses skip it.
    assert "content-security-policy" not in r.headers


def test_hsts_is_production_only():
    dev = build_security_headers(is_production=False)
    prod = build_security_headers(is_production=True)

    assert "Strict-Transport-Security" not in dev
    assert prod["Strict-Transport-Security"].startswith("max-age=")
    assert "includeSubDomains" in prod["Strict-Transport-Security"]


def test_login_endpoints_use_the_login_bucket():
    for path in (
        "/admin/login",
        "/admin/forgot-password",
        "/admin/reset-password",
        "/api/v1/auth/login",
        "/api/v1/auth/token",
    ):
        limit, window, key = RateLimitMiddleware._bucket_for(
            _request(path), "203.0.113.7"
        )
        assert limit == settings.RATE_LIMIT_LOGIN_PER_MINUTE, path
        assert window == 60
        assert key == "login:203.0.113.7"

    limit, _, key = RateLimitMiddleware._bucket_for(
        _request("/admin/dashboard"), "203.0.113.7"
    )
    assert limit == settings.RATE_LIMIT_PUBLIC_PER_MINUTE
    assert key == "public:203.0.113.7"


@pytest.mark.asyncio
async def test_logout_is_post_only(client: AsyncClient):
    r = await client.get("/admin/logout", follow_redirects=False)
    assert r.status_code == 405
