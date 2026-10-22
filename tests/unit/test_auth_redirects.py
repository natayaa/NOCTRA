"""Unauthorized admin page requests must reach the login page, not JSON."""

import httpx
import pytest
from fastapi import FastAPI

from app.core.error_handlers import register_error_handlers
from app.core.exceptions import UnauthorizedError


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/admin/settings")
    async def admin_page():
        raise UnauthorizedError("Invalid token")

    @app.get("/admin/login")
    async def login_page():
        return {"page": "login"}

    @app.get("/api/v1/settings")
    async def api_settings():
        raise UnauthorizedError("Invalid token")

    register_error_handlers(app)
    return app


async def _get(path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.get(path, **kwargs)


@pytest.mark.asyncio
async def test_admin_page_redirects_to_login_and_clears_cookies():
    response = await _get("/admin/settings?tab=email")

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/login?next=%2Fadmin%2Fsettings%3Ftab%3Demail"
    )

    cookies = response.headers.get_list("set-cookie")
    assert any(
        cookie.startswith("noctra_access_token=") and "Max-Age=0" in cookie
        for cookie in cookies
    )
    assert any(
        cookie.startswith("noctra_refresh_token=") and "Max-Age=0" in cookie
        for cookie in cookies
    )


@pytest.mark.asyncio
async def test_htmx_request_keeps_json_401():
    response = await _get("/admin/settings", headers={"hx-request": "true"})

    assert response.status_code == 401
    assert "location" not in response.headers
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_api_request_keeps_json_401():
    response = await _get("/api/v1/settings")

    assert response.status_code == 401
    assert "location" not in response.headers
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_login_page_is_not_redirected():
    response = await _get("/admin/login")

    assert response.status_code == 200
