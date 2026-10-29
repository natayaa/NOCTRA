from fastapi import APIRouter, Depends, Query, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import ForbiddenError
from app.modules.auth.dependencies import (
    CurrentPermissions,
    CurrentUser,
    require_permission,
)
from app.modules.settings.constants import KNOWN_SETTINGS
from app.modules.settings.schemas import (
    KnownSettingInfo,
    SettingBulkUpdate,
    SettingItem,
    SettingsCatalog,
    SettingUpdate,
)
from app.modules.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_item(row, *, reveal: bool) -> SettingItem:
    item = SettingItem.model_validate(row)
    if row.is_secret and not reveal:
        item.value = "***" if row.value is not None else None
    return item


# ════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ════════════════════════════════════════════════════════════════

async def _read_guard(
    reveal: bool = Query(
        False,
        description=(
            "Show raw values for secret settings. Requires SETTINGS_UPDATE."
        ),
    ),
    user: CurrentUser = None,
    perms: CurrentPermissions = None,
) -> bool:
    """
    Requires SETTINGS_READ for any access. Additionally requires
    SETTINGS_UPDATE when `?reveal=true` is used.
    """
    have = perms or set()
    if not (user.is_superuser or PermissionCode.SETTINGS_READ.value in have):
        raise ForbiddenError("Missing SETTINGS_READ permission")
    if reveal and not (
        user.is_superuser or PermissionCode.SETTINGS_UPDATE.value in have
    ):
        raise ForbiddenError("reveal=true requires SETTINGS_UPDATE permission")
    return reveal


# ════════════════════════════════════════════════════════════════
# CATALOG
# ════════════════════════════════════════════════════════════════

@router.get("/catalog", response_model=SettingsCatalog)
async def catalog(_=Depends(_read_guard)) -> SettingsCatalog:
    return SettingsCatalog(
        known_settings=[
            KnownSettingInfo(
                key=k,
                category=s.category,
                description=s.description,
                is_secret=s.is_secret,
            )
            for k, s in sorted(KNOWN_SETTINGS.items())
        ],
        categories=sorted({s.category for s in KNOWN_SETTINGS.values()}),
    )


# ════════════════════════════════════════════════════════════════
# READ
# ════════════════════════════════════════════════════════════════

@router.get("", response_model=list[SettingItem])
async def list_settings(
    db: DbSession,
    category: str | None = Query(None, max_length=50),
    reveal: bool = Depends(_read_guard),
) -> list[SettingItem]:
    rows = await SettingsService(db).list(category)
    return [_to_item(r, reveal=reveal) for r in rows]


@router.get("/{key}", response_model=SettingItem)
async def get_setting(
    key: str,
    db: DbSession,
    reveal: bool = Depends(_read_guard),
) -> SettingItem:
    row = await SettingsService(db).get_by_key(key)
    return _to_item(row, reveal=reveal)


# ════════════════════════════════════════════════════════════════
# WRITE
# ════════════════════════════════════════════════════════════════

@router.put("/{key}", response_model=SettingItem)
async def update_setting(
    key: str,
    payload: SettingUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.SETTINGS_UPDATE)),
) -> SettingItem:
    setting = await SettingsService(db).upsert(
        key,
        value=payload.value,
        category=payload.category,
        description=payload.description,
        is_secret=payload.is_secret,
        actor=actor,
    )
    return _to_item(setting, reveal=False)


@router.post("/bulk", response_model=list[SettingItem])
async def bulk_update_settings(
    payload: SettingBulkUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.SETTINGS_UPDATE)),
) -> list[SettingItem]:
    items = [(item.key, item.value) for item in payload.items]
    results = await SettingsService(db).bulk_update(items, actor=actor)
    return [_to_item(r, reveal=False) for r in results]


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    key: str,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.SETTINGS_UPDATE)),
) -> None:
    await SettingsService(db).delete(key, actor=actor)