# app/modules/rbac/repository.py
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.rbac.models import Permission, Role


class RoleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self) -> list[Role]:
        stmt = select(Role).order_by(Role.name)
        return list((await self.db.execute(stmt)).scalars().all())

    async def by_names(self, names: list[str]) -> list[Role]:
        if not names:
            return []
        stmt = select(Role).where(Role.name.in_(names))
        return list((await self.db.execute(stmt)).scalars().all())

    async def get(self, rid: UUID) -> Role | None:
        return await self.db.get(Role, rid)


class PermissionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.code)
        return list((await self.db.execute(stmt)).scalars().all())