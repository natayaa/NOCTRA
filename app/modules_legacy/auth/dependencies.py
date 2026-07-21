# modules/auth/dependencies.py
from typing import Optional, List
from uuid import UUID

from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.models import User
from core.database import get_db
from core.exceptions import UnauthorizedError, ForbiddenError
from .services import AuthService, TokenService


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from token."""
    if not credentials:
        raise UnauthorizedError("Authentication required")

    token = credentials.credentials

    # Validate token
    token_service = TokenService(db)
    user_id = token_service.validate_access_token(token)

    if not user_id:
        raise UnauthorizedError("Invalid or expired token")

    # Get user
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(user_id)

    if not user:
        raise UnauthorizedError("User not found")

    if user.status != "active":
        raise UnauthorizedError("Account is not active")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if current_user.status != "active":
        raise UnauthorizedError("Account is not active")
    return current_user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None

    token = credentials.credentials
    token_service = TokenService(db)
    user_id = token_service.validate_access_token(token)

    if not user_id:
        return None

    auth_service = AuthService(db)
    user = await auth_service.get_current_user(user_id)

    return user


# ============================================================================
# Authorization Dependencies
# ============================================================================

def require_role(roles: List[str]):
    """Dependency untuk memeriksa role."""
    async def _require_role(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        user_roles = [ur.role.name for ur in current_user.roles if ur.role]
        if not any(role in user_roles for role in roles):
            raise ForbiddenError(
                f"Requires one of roles: {', '.join(roles)}"
            )
        return current_user
    return _require_role


def require_permission(permission: str):
    """Dependency untuk memeriksa permission."""
    async def _require_permission(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        auth_service = AuthService(db)
        has_perm = await auth_service.has_permission(current_user.id, permission)

        if not has_perm:
            raise ForbiddenError(
                f"Requires permission: {permission}"
            )
        return current_user
    return _require_permission


def require_permissions(permissions: List[str], require_all: bool = True):
    """Dependency untuk memeriksa multiple permissions."""
    async def _require_permissions(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        auth_service = AuthService(db)
        user_perms = await auth_service.user_repo.get_user_permissions(current_user.id)

        if require_all:
            missing = [p for p in permissions if p not in user_perms]
            if missing:
                raise ForbiddenError(
                    f"Requires permissions: {', '.join(missing)}"
                )
        else:
            if not any(p in user_perms for p in permissions):
                raise ForbiddenError(
                    f"Requires at least one of: {', '.join(permissions)}"
                )
        return current_user
    return _require_permissions


def require_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency untuk memeriksa superuser."""
    if not current_user.is_superuser:
        raise ForbiddenError("Requires superuser privileges")
    return current_user


# ============================================================================
# Helper Functions
# ============================================================================

def get_token_from_request(request: Request) -> Optional[str]:
    """Extract token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


async def get_user_from_token(
    token: str,
    db: AsyncSession
) -> Optional[User]:
    """Get user from token string."""
    token_service = TokenService(db)
    user_id = token_service.validate_access_token(token)

    if not user_id:
        return None

    auth_service = AuthService(db)
    return await auth_service.get_current_user(user_id)
