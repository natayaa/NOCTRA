from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import PermissionCode
from modules.rbac.models import Permission, Role, RolePermission, UserRole


async def permissions_for_user(db: AsyncSession, user_id: UUID) -> set[str]:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleAlias, UserRoleAlias.role_id == Role.id)  # type: ignore[name-defined]  # noqa: F821
        .where(UserRoleAlias.user_id == user_id)  # type: ignore[name-defined]  # noqa: F821
    )
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)


async def has_all(db: AsyncSession, user_id: UUID, codes: Iterable[PermissionCode]) -> bool:
    needed = {c.value for c in codes}
    have = await permissions_for_user(db, user_id)
    return needed.issubset(have)


async def has_any(db: AsyncSession, user_id: UUID, codes: Iterable[PermissionCode]) -> bool:
    needed = {c.value for c in codes}
    have = await permissions_for_user(db, user_id)
    return bool(needed & have)