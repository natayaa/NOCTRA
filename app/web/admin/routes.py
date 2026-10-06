"""Admin web routes: login, logout, dashboard.

The POST /admin/login handler is the only way a browser session becomes
authenticated. It sets a JWT in an HttpOnly cookie.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.service import AuthService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin", tags=["admin-web"])

ACCESS_COOKIE_NAME = "noctra_access_token"
ACCESS_COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours


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
        {"title": "Sign In"},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    db: DbSession,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
):
    """
    Validate credentials, set a JWT in a cookie, redirect.

    On failure, re-render the login form with an error message.
    """
    payload = LoginRequest(username=username, password=password)

    try:
        user, tokens = await AuthService(db).login(
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

    # Sanitize `next`: only allow same-origin relative paths.
    target = "/admin/dashboard"
    if next and next.startswith("/") and not next.startswith("//"):
        target = next

    response = RedirectResponse(url=target, status_code=303)
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        tokens.access_token,
        httponly=True,
        secure=False,          # flip to True in production (HTTPS)
        samesite="lax",
        max_age=ACCESS_COOKIE_MAX_AGE,
        path="/",
    )
    return response


# ════════════════════════════════════════════════════════════════
# LOGOUT
# ════════════════════════════════════════════════════════════════

@router.post("/logout")
async def logout_submit() -> RedirectResponse:
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    return response


@router.get("/logout")
async def logout_get() -> RedirectResponse:
    """Convenience GET logout — same effect, idempotent."""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    return response


# ════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    stats = {
        "active_projects": 0,
        "pending_inquiries": 0,
        "revenue_month": 0,
        "hpp_month": 0,
        "gross_margin_pct": 0.0,
    }
    return templates.render(
        request,
        "admin/dashboard.html",
        {"title": "Dashboard", "stats": stats},
    )