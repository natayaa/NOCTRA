from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from core.deps import DbSession
from core.exceptions import ForbiddenError, UnauthorizedError
from core.tokens import decode_token
from modules.auth.models import User
from modules.auth.repository import UserRepository
from modules.rbac.permissions import permissions_for_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
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
    """Dependency factory: require *all* given permission codes."""

    async def _dep(
        user: CurrentUser,
        perms: CurrentPermissions,
    ) -> User:
        if user.is_superuser:
            return user
        missing = [c for c in codes if c not in perms]
        if missing:
            raise ForbiddenError(f"Missing permissions: {', '.join(missing)}")
        return user

    return _dep


def require_any_permission(*codes: str):
    async def _dep(
        user: CurrentUser,
        perms: CurrentPermissions,
    ) -> User:
        if user.is_superuser:
            return user
        if not any(c in perms for c in codes):
            raise ForbiddenError(f"Requires one of: {', '.join(codes)}")
        return user

    return _dep


Superuser = Annotated[User, Depends(require_permission())]  # placeholder; see below