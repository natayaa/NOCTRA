from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.settings.models import AppSetting


class SettingsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def query(self, category: str | None = None):
        stmt = select(AppSetting).order_by(AppSetting.category, AppSetting.key)
        if category:
            stmt = stmt.where(AppSetting.category == category)
        return stmt

    async def by_key(self, key: str) -> AppSetting | None:
        return (
            await self.db.execute(select(AppSetting).where(AppSetting.key == key))
        ).scalar_one_or_none()