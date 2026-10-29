"""Admin web routes: login, logout, dashboard root.

The POST /admin/login handler is the only way a browser session becomes
authenticated. It sets JWT cookies (access + refresh) in HttpOnly cookies.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import log
from app.modules.auth.dependencies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    get_current_user,
)
from app.modules.auth.password_reset import PasswordResetService
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.service import AuthService
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import SelfPasswordChange
from app.modules.users.service import UserService
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
    # A backslash is normalized to "/" by some browsers, re-enabling the
    # `//host` bypass after the checks above; refuse it outright.
    if "\\" in s:
        return "/admin/dashboard"
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
            "reset_done": request.query_params.get("reset") == "1",
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
    # POST only: a GET logout can be triggered cross-site with an <img>
    # or a link, which is a forced-logout nuisance and hides real intent.
    response = RedirectResponse(url="/admin/login", status_code=303)
    _clear_auth_cookies(response)
    return response


# ════════════════════════════════════════════════════════════════
# PASSWORD RESET
# ════════════════════════════════════════════════════════════════

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request) -> HTMLResponse:
    return templates.render(
        request,
        "admin/forgot_password.html",
        {
            "title": "Reset password",
            "sent": request.query_params.get("sent") == "1",
            "enabled": settings.PASSWORD_RESET_ENABLED,
            "expires_minutes": settings.PASSWORD_RESET_TTL_MINUTES,
        },
    )


@router.post("/forgot-password")
async def forgot_password_submit(request: Request, db: DbSession) -> RedirectResponse:
    form = await request.form()
    identifier = (form.get("identifier") or "").strip()

    # Always the same answer. Whether an account exists, is inactive, or
    # has no email must not be observable from the outside.
    if identifier:
        try:
            await PasswordResetService(db).request_reset(
                identifier,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            # A failure to queue an email must not reveal which side failed.
            log.exception("password_reset_request_failed")
            await db.rollback()

    return RedirectResponse(url="/admin/forgot-password?sent=1", status_code=303)


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request) -> HTMLResponse:
    return templates.render(
        request,
        "admin/reset_password.html",
        {
            "title": "Choose a new password",
            "token": request.query_params.get("token", ""),
            "enabled": settings.PASSWORD_RESET_ENABLED,
        },
    )


@router.post("/reset-password")
async def reset_password_submit(request: Request, db: DbSession):
    form = await request.form()
    token = (form.get("token") or "").strip()
    new_password = form.get("new_password") or ""
    confirm = form.get("confirm_password") or ""

    error: str | None = None
    if not token:
        error = "This reset link is missing its token. Request a new link."
    elif new_password != confirm:
        error = "Passwords do not match."
    elif len(new_password) < 8:
        error = "Password must be at least 8 characters."
    elif len(new_password) > 128:
        error = "Password must be at most 128 characters."

    if error is None:
        try:
            await PasswordResetService(db).reset_password(
                token,
                new_password,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            await db.commit()
            return RedirectResponse(url="/admin/login?reset=1", status_code=303)
        except AppError as exc:
            await db.rollback()
            error = exc.message

    return templates.render(
        request,
        "admin/reset_password.html",
        {
            "title": "Choose a new password",
            "token": token,
            "enabled": True,
            "error": error,
        },
        status_code=400,
    )


# ════════════════════════════════════════════════════════════════
# MY PROFILE
# ════════════════════════════════════════════════════════════════

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError)


def _profile_error(message: str) -> str:
    return f"/admin/profile?error={quote(message.strip(), safe='')}"


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: DbSession,
    notice: str | None = Query(None),
    error: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    """Account overview + self-service password change for the signed-in user."""
    user = await UserRepository(db).get(current.id)
    if user is None:
        raise NotFoundError("Account no longer exists")
    return templates.render(
        request,
        "admin/profile.html",
        {
            "title": "My Profile",
            "user_obj": user,
            "notice": notice,
            "error": error,
        },
    )


@router.post("/profile/password")
async def profile_password_submit(
    request: Request,
    db: DbSession,
    current=Depends(get_current_user),
):
    form = await request.form()
    old_password = form.get("old_password") or ""
    new_password = form.get("new_password") or ""
    confirm = form.get("confirm_password") or ""

    if new_password != confirm:
        return RedirectResponse(
            url=_profile_error("New passwords do not match."), status_code=303
        )
    if len(new_password) < 8:
        return RedirectResponse(
            url=_profile_error("Password must be at least 8 characters."),
            status_code=303,
        )

    try:
        payload = SelfPasswordChange(
            old_password=old_password,
            new_password=new_password,
        )
        await UserService(db).change_own_password(
            current.id, payload, actor=current
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        message = getattr(exc, "message", None) or str(exc) or "Invalid input"
        return RedirectResponse(url=_profile_error(message), status_code=303)

    # `change_own_password` bumps `password_changed_at`, which invalidates
    # the current access/refresh tokens. Clear the cookies and send the
    # user to sign in again with the new password.
    response = RedirectResponse(url="/admin/login?reset=1", status_code=303)
    _clear_auth_cookies(response)
    return response