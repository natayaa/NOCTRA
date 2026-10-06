from fastapi import APIRouter, Depends, Query

from core.constants import PermissionCode
from core.deps import DbSession
from modules.auth.dependencies import CurrentUser, require_permission
from modules.settings.schemas import SettingItem, SettingUpdate
from modules.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingItem])
async def list_settings(
    db: DbSession,
    category: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.SETTINGS_READ)),
) -> list[SettingItem]:
    rows = await SettingsService(db).list(category)
    return [SettingItem.model_validate(r) for r in rows]


@router.put("/{key}", response_model=SettingItem)
async def update_setting(
    key: str,
    payload: SettingUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.SETTINGS_UPDATE)),
) -> SettingItem:
    setting = await SettingsService(db).upsert(key, payload.value, actor=actor)
    return SettingItem.model_validate(setting)