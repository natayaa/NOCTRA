"""User data access."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Reads ─────────────────────────────────────────

    async def get(self, uid: UUID) -> User | None:
        return await self.db.get(User, uid)

    async def get_for_update(self, uid: UUID) -> User | None:
        """Load with row-level lock — used for update/deactivate."""
        stmt = select(User).where(User.id == uid).with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        role_name: str | None = None,
    ) -> Select:
        # Stable secondary sort on id for pagination.
        stmt = select(User).order_by(User.created_at.desc(), User.id.asc())

        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    User.username.ilike(like),
                    User.email.ilike(like),
                    User.full_name.ilike(like),
                )
            )
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if role_name:
            # Inner join to Role — filters to users with that specific role.
            stmt = stmt.join(UserRole, UserRole.user_id == User.id).join(
                Role, Role.id == UserRole.role_id
            ).where(Role.name == role_name)

        return stmt

    # ── Guard helpers ─────────────────────────────────

    async def count_active_superusers(self) -> int:
        """Count users with is_superuser flag OR superuser role, and is_active."""
        flag_stmt = (
            select(func.count(User.id))
            .where(User.is_superuser.is_(True))
            .where(User.is_active.is_(True))
        )
        flag_count = int((await self.db.execute(flag_stmt)).scalar_one() or 0)

        role_stmt = (
            select(func.count(User.id.distinct()))
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.name == "superuser")
            .where(User.is_active.is_(True))
        )
        role_count = int((await self.db.execute(role_stmt)).scalar_one() or 0)

        # A user with BOTH flag and role is counted once in the max.
        # Return the larger of the two — that's the effective "backdoor" count.
        return max(flag_count, role_count)

    async def count_active_with_role(self, role_name: str) -> int:
        stmt = (
            select(func.count(User.id.distinct()))
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.name == role_name)
            .where(User.is_active.is_(True))
        )
        return int((await self.db.execute(stmt)).scalar_one() or 0)

    # ── Writes ────────────────────────────────────────

    async def add(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user