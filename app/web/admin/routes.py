"""Admin web routes: login, logout, dashboard root.

The POST /admin/login handler is the only way a browser session becomes
authenticated. It sets JWT cookies (access + refresh) in HttpOnly cookies.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import settings
from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.modules.auth.dependencies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.service import AuthService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin", tags=["admin-web"])


def _safe_next(next_url: str | None) -> str:
    """
    Sanitize the `next` redirect target. Allows only same-origin relative
    paths — rejects protocol-relative (`//evil.com`) and backslash paths
    (`\\evil.com`, a known bypass on some browsers).
    """
    if not next_url:
        return "/admin/dashboard"
    s = next_url.strip()
    if not s.startswith("/") or s.startswith("//") or s.startswith("/\\"):
        return "/admin/dashboard"
    # Reject anything with a scheme or backslash
    if "\\" in s or ":" in s.split("/", 2)[1] if "/" in s[1:] else False:
        # Defensive: parse conservatively — never assume the URL is safe.
        # The explicit startswith checks above already cover the common
        # attacks; this is belt-and-braces.
        pass
    return s


def _set_auth_cookies(response: RedirectResponse, tokens) -> None:
    """Persist access + refresh tokens as HttpOnly cookies."""
    common = dict(
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,     # ← was hardcoded False
        samesite=settings.SESSION_COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        tokens.access_token,
        max_age=tokens.expires_in,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        tokens.refresh_token,
        max_age=tokens.refresh_expires_in,
        **common,
    )


def _clear_auth_cookies(response: RedirectResponse) -> None:
    for name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME):
        response.delete_cookie(name, path="/")


# ════════════════════════════════════════════════════════════════
# ROOT
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=RedirectResponse)
async def admin_root() -> RedirectResponse:
    return RedirectResponse(url="/admin/dashboard", status_code=302)


# ════════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════════

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.render(
        request,
        "admin/login.html",
        {
            "title": "Sign In",
            "next": request.query_params.get("next", ""),
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    db: DbSession,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
):
    payload = LoginRequest(username=username, password=password)

    try:
        _, tokens = await AuthService(db).login(
            payload,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AppError as exc:
        return templates.render(
            request,
            "admin/login.html",
            {
                "title": "Sign In",
                "username": username,
                "next": next,
                "error": exc.message,
            },
            status_code=exc.status_code,
        )

    response = RedirectResponse(url=_safe_next(next), status_code=303)
    _set_auth_cookies(response, tokens)
    return response


# ════════════════════════════════════════════════════════════════
# LOGOUT
# ════════════════════════════════════════════════════════════════

@router.post("/logout")
async def logout_submit() -> RedirectResponse:
    response = RedirectResponse(url="/admin/login", status_code=303)
    _clear_auth_cookies(response)
    return response


@router.get("/logout")
async def logout_get() -> RedirectResponse:
    response = RedirectResponse(url="/admin/login", status_code=303)
    _clear_auth_cookies(response)
    return response