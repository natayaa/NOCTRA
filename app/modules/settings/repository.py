from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.models import AppSetting


class SettingsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def query(self, category: str | None = None) -> Select:
        # Stable secondary sort on id for defensive pagination.
        stmt = select(AppSetting).order_by(
            AppSetting.category.asc(),
            AppSetting.key.asc(),
            AppSetting.id.asc(),
        )
        if category:
            stmt = stmt.where(AppSetting.category == category)
        return stmt

    async def by_key(self, key: str) -> AppSetting | None:
        stmt = select(AppSetting).where(AppSetting.key == key).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def delete(self, setting: AppSetting) -> None:
        await self.db.delete(setting)
        await self.db.flush()