"""Read/write helpers for RBAC roles and permissions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.rbac.models import Permission, Role


class RoleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self) -> list[Role]:
        # `permissions` (selectin) fires automatically; `users` (raise)
        # will NOT fire. For an admin list showing role metadata + permission
        # count, this is exactly right.
        stmt = (
            select(Role)
            .order_by(Role.name.asc(), Role.id.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_with_users(self) -> list[Role]:
        """Variant that also loads `Role.users` — use sparingly."""
        stmt = (
            select(Role)
            .options(selectinload(Role.users))
            .order_by(Role.name.asc(), Role.id.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def by_names(self, names: list[str]) -> list[Role]:
        if not names:
            return []
        stmt = select(Role).where(Role.name.in_(names))
        return list((await self.db.execute(stmt)).scalars().all())

    async def get(self, rid: UUID) -> Role | None:
        return await self.db.get(Role, rid)

    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_with_permissions(self, rid: UUID) -> Role | None:
        """Explicitly load permissions — useful when `lazy` might be overridden."""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == rid)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_users_in_role(self, rid: UUID) -> list[UUID]:
        """Return user IDs assigned to a role (efficient — no ORM users loaded)."""
        from app.modules.rbac.models import UserRole

        stmt = select(UserRole.user_id).where(UserRole.role_id == rid)
        return list((await self.db.execute(stmt)).scalars().all())

    async def add(self, role: Role) -> Role:
        self.db.add(role)
        await self.db.flush()
        return role


class PermissionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def query(self) -> Select:
        # Group by code prefix (e.g. "user:*", "project:*") for admin UI,
        # with stable secondary sort.
        return (
            select(Permission)
            .order_by(Permission.code.asc(), Permission.id.asc())
        )

    async def list(self) -> list[Permission]:
        return list((await self.db.execute(self.query())).scalars().all())

    async def by_codes(self, codes: list[str]) -> list[Permission]:
        if not codes:
            return []
        stmt = select(Permission).where(Permission.code.in_(codes))
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add(self, permission: Permission) -> Permission:
        self.db.add(permission)
        await self.db.flush()
        return permission