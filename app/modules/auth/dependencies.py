from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.deps import DbSession
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.tokens import decode_token
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.rbac.permissions import permissions_for_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

ACCESS_COOKIE_NAME = "noctra_access_token"


async def get_current_user(
    token_header: Annotated[str | None, Depends(oauth2_scheme)],
    token_cookie: Annotated[str | None, Cookie(alias=ACCESS_COOKIE_NAME)] = None,
    db: DbSession = None,
) -> User:
    """Authenticate from either a Bearer header or the access cookie."""

    token = token_header or token_cookie
    if not token:
        raise UnauthorizedError()

    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc

    if payload.typ != "access":
        raise UnauthorizedError("Invalid token type")

    user = await UserRepository(db).get(UUID(payload.sub))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


async def get_current_permissions(
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> set[str]:
    return await permissions_for_user(db, user.id)


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentPermissions = Annotated[set[str], Depends(get_current_permissions)]


def require_permission(*codes: str):
    async def _dep(user: CurrentUser, perms: CurrentPermissions) -> User:
        if user.is_superuser:
            return user
        missing = [c for c in codes if c not in perms]
        if missing:
            raise ForbiddenError(f"Missing permissions: {', '.join(missing)}")
        return user
    return _dep


def require_any_permission(*codes: str):
    async def _dep(user: CurrentUser, perms: CurrentPermissions) -> User:
        if user.is_superuser:
            return user
        if not any(c in perms for c in codes):
            raise ForbiddenError(f"Requires one of: {', '.join(codes)}")
        return user
    return _dep


async def require_superuser(user: CurrentUser) -> User:
    if not user.is_superuser:
        raise ForbiddenError("Superuser access required")
    return user


Superuser = Annotated[User, Depends(require_superuser)]