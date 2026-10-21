from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def by_username(
        self, username: str, *, for_update: bool = False
    ) -> User | None:
        """Lookup by username.

        `for_update=True` acquires a row-level lock (`SELECT ... FOR UPDATE`)
        and refreshes the ORM object's attributes from the DB, preventing
        lost updates on `failed_login_attempts` when concurrent login
        attempts race. See `AuthService.login`.
        """
        stmt = select(User).where(User.username == username)
        if for_update:
            stmt = stmt.with_for_update().execution_options(
                populate_existing=True
            )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_email(self, email: str) -> User | None:
        return (
            await self.db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

    async def add(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user