"""Permission resolution and assertion helpers."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PermissionCode
from app.modules.rbac.models import Permission, RolePermission, UserRole


def _normalize_codes(codes: Iterable[PermissionCode | str]) -> set[str]:
    """Accept either enum or string; return set of string codes."""
    return {
        c.value if isinstance(c, PermissionCode) else str(c)
        for c in codes
    }


async def permissions_for_user(db: AsyncSession, user_id: UUID) -> set[str]:
    """
    Resolve the full set of permission codes granted to a user via roles.

    `Role` is intentionally NOT joined — RolePermission.role_id is already
    an FK to Role.id, and joining Role adds a roundtrip with zero benefit.
    """
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    return set((await db.execute(stmt)).scalars().all())


async def permissions_for_roles(
    db: AsyncSession, role_ids: Iterable[UUID]
) -> dict[UUID, set[str]]:
    """
    Batch resolve permissions for many roles at once.
    Useful for admin UI ("show permissions per role") without N+1.
    """
    ids = list(role_ids)
    if not ids:
        return {}

    stmt = (
        select(RolePermission.role_id, Permission.code)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_id.in_(ids))
    )
    rows = (await db.execute(stmt)).all()

    result: dict[UUID, set[str]] = {rid: set() for rid in ids}
    for role_id, code in rows:
        result[role_id].add(code)
    return result


async def has_all(
    db: AsyncSession,
    user_id: UUID,
    codes: Iterable[PermissionCode | str],
) -> bool:
    needed = _normalize_codes(codes)
    if not needed:
        return True
    have = await permissions_for_user(db, user_id)
    return needed.issubset(have)


async def has_any(
    db: AsyncSession,
    user_id: UUID,
    codes: Iterable[PermissionCode | str],
) -> bool:
    needed = _normalize_codes(codes)
    if not needed:
        return False
    have = await permissions_for_user(db, user_id)
    return bool(needed & have)