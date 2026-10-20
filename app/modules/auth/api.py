from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.constants import AuditAction
from app.core.deps import DbSession
from app.core.exceptions import UnauthorizedError
from app.core.tokens import decode_access_token
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    CurrentPermissions,
    CurrentUser,
)
from app.modules.auth.schemas import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    TokenPair,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _set_auth_cookies(response: Response, tokens: TokenPair) -> None:
    """Persist tokens in HttpOnly cookies for browser clients.
    API clients ignore these and use the JSON body instead."""
    common = dict(
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
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


def _clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME):
        response.delete_cookie(name, path="/")


@router.post("/token", response_model=TokenPair, include_in_schema=True)
async def login_form(
    request: Request,
    response: Response,
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenPair:
    """OAuth2 password flow — used by Swagger's Authorize button."""
    payload = LoginRequest(
        username=form_data.username,
        password=form_data.password,
    )
    _, tokens = await AuthService(db).login(
        payload,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> TokenPair:
    _, tokens = await AuthService(db).login(
        payload,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    payload: RefreshRequest | None = Body(None),
) -> TokenPair:
    # Body wins, cookie is fallback (browser clients).
    token = (payload.refresh_token if payload else None) or request.cookies.get(
        REFRESH_COOKIE_NAME
    )
    if not token:
        raise UnauthorizedError("No refresh token provided")

    tokens = await AuthService(db).refresh(token, ip=_client_ip(request))
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db: DbSession,
) -> Response:
    """Clear auth cookies. Does not require a valid session so expired
    clients can still logout cleanly. Best-effort audit if a token exists."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response)

    auth_header = request.headers.get("authorization", "")
    token = (
        auth_header[7:]
        if auth_header.lower().startswith("bearer ")
        else request.cookies.get(ACCESS_COOKIE_NAME)
    )
    if token:
        try:
            payload = decode_access_token(token)
            await AuthService(db).logout(
                user_id=UUID(payload.sub),
                ip=_client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass  # never fail logout on audit errors
    return response


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser, perms: CurrentPermissions) -> MeResponse:
    return MeResponse.model_validate(user).model_copy(
        update={"permissions": sorted(perms)}
    )