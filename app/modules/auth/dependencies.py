from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.deps import DbSession
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.tokens import decode_access_token
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.rbac.permissions import permissions_for_user

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token", auto_error=False
)

ACCESS_COOKIE_NAME = "noctra_access_token"
REFRESH_COOKIE_NAME = "noctra_refresh_token"

# Allow tokens issued up to 1s before a password change to remain valid.
# Protects against NTP skew between app servers that issue tokens and the
# server that wrote `password_changed_at`.
_CLOCK_SKEW = timedelta(seconds=1)


@dataclass(frozen=True, slots=True)
class _RoleSnapshot:
    name: str


@dataclass(frozen=True, slots=True)
class CurrentUserSnapshot:
    """Detached copy of the authenticated user for template rendering.

    Templates render synchronously, so reading an ORM attribute that a
    `rollback()` expired (form-error paths re-render after rolling back)
    performs IO outside the greenlet and raises MissingGreenlet. Capture
    the values while the instance is still loaded.
    """

    id: UUID
    username: str
    email: str | None
    full_name: str | None
    is_superuser: bool
    roles: list[_RoleSnapshot]


async def get_current_user(
    request: Request,
    token_header: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbSession,
    token_cookie: Annotated[str | None, Cookie(alias=ACCESS_COOKIE_NAME)] = None,
) -> User:
    """Authenticate from either a Bearer header or the access cookie."""
    token = token_header or token_cookie
    if not token:
        raise UnauthorizedError("Missing authentication")

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc

    user = await UserRepository(db).get(UUID(payload.sub))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    # Session invalidation: any token issued before the last password
    # change is rejected. This is our only defense after an admin
    # password reset — otherwise the attacker's session keeps working
    # until natural token expiry (up to 8 hours).
    if user.password_changed_at is not None:
        token_iat = datetime.fromtimestamp(payload.iat, tz=UTC)
        if token_iat < user.password_changed_at - _CLOCK_SKEW:
            raise UnauthorizedError(
                "Session expired — password was changed. Please log in again."
            )

    # Make the authenticated user available to downstream middleware
    # (logout, template context, request logging, etc.). Templates get a
    # detached snapshot — the ORM instance is expired by any later
    # rollback, and Jinja reads attributes synchronously.
    request.state.user = CurrentUserSnapshot(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_superuser=user.is_superuser,
        roles=[_RoleSnapshot(name=r.name) for r in user.roles],
    )
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