from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.settings.models import AppSetting
from app.modules.settings.repository import SettingsRepository


class SettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SettingsRepository(db)
        self.audit = AuditService(db)

    async def list(self, category: str | None = None) -> list[AppSetting]:
        return list((await self.db.execute(self.repo.query(category))).scalars().all())

    async def upsert(self, key: str, value: str | None, *, actor: User) -> AppSetting:
        existing = await self.repo.by_key(key)
        if existing is None:
            setting = AppSetting(key=key, value=value, category=key.split(".", 1)[0])
            self.db.add(setting)
            await self.db.flush()
            await self.audit.log(
                action=AuditAction.CREATE,
                table_name="app_settings",
                record_id=setting.id,
                user_id=actor.id,
                new_data={"key": key, "value": value},
            )
            return setting

        old_value = existing.value
        existing.value = value
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="app_settings",
            record_id=existing.id,
            user_id=actor.id,
            old_data={"value": old_value},
            new_data={"value": value},
        )
        return existing

    async def get_value(self, key: str, default: str | None = None) -> str | None:
        setting = await self.repo.by_key(key)
        return setting.value if setting and setting.value is not None else default