from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.models import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, uid: UUID) -> User | None:
        return await self.db.get(User, uid)

    async def by_username(self, username: str) -> User | None:
        return (await self.db.execute(select(User).where(User.username == username))).scalar_one_or_none()

    async def by_email(self, email: str) -> User | None:
        return (await self.db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    def query(self):
        return select(User).order_by(User.created_at.desc())