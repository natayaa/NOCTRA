"""Settings service — read, write, cache, audit."""

from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import log
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.settings.constants import (
    SETTINGS_CACHE_TTL_SECONDS,
    is_secret_key,
    validate_value,
)
from app.modules.settings.models import AppSetting
from app.modules.settings.repository import SettingsRepository


# ════════════════════════════════════════════════════════════════
# IN-PROCESS CACHE
#
# Small TTL cache for `get_value`. Invalidated on write. In a multi-
# worker deployment each worker has its own cache; values propagate
# within SETTINGS_CACHE_TTL_SECONDS (default 60s).
# ════════════════════════════════════════════════════════════════

_cache: dict[str, tuple[str | None, float]] = {}


def _cache_get(key: str) -> tuple[bool, str | None]:
    entry = _cache.get(key)
    if entry is None:
        return False, None
    value, expires = entry
    if time.monotonic() > expires:
        _cache.pop(key, None)
        return False, None
    return True, value


def _cache_set(key: str, value: str | None) -> None:
    _cache[key] = (value, time.monotonic() + SETTINGS_CACHE_TTL_SECONDS)


def cache_invalidate(key: str | None = None) -> None:
    """Invalidate one key or the whole cache (after bulk write)."""
    if key is None:
        _cache.clear()
    else:
        _cache.pop(key, None)


# ════════════════════════════════════════════════════════════════
# SERVICE
# ════════════════════════════════════════════════════════════════

class SettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SettingsRepository(db)
        self.audit = AuditService(db)

    # ── Read ────────────────────────────────────────────

    async def list(self, category: str | None = None) -> list[AppSetting]:
        return list((await self.db.execute(self.repo.query(category))).scalars().all())

    async def get_by_key(self, key: str) -> AppSetting:
        setting = await self.repo.by_key(key)
        if setting is None:
            raise NotFoundError(f"Setting {key!r} not found")
        return setting

    async def get_value(self, key: str, default: str | None = None) -> str | None:
        """
        Read a setting value. Cached for up to SETTINGS_CACHE_TTL_SECONDS.
        Returns `default` if the key does not exist or has a NULL value.
        """
        hit, cached = _cache_get(key)
        if hit:
            return cached if cached is not None else default

        setting = await self.repo.by_key(key)
        raw = setting.value if setting and setting.value is not None else None
        _cache_set(key, raw)
        return raw if raw is not None else default

    async def get_float(self, key: str, default: float = 0.0) -> float:
        raw = await self.get_value(key)
        if raw is None:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            log.warning(
                "setting_not_numeric",
                key=key,
                value=raw,
                expected="float",
            )
            return default

    async def get_int(self, key: str, default: int = 0) -> int:
        raw = await self.get_value(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except (TypeError, ValueError):
            log.warning(
                "setting_not_numeric",
                key=key,
                value=raw,
                expected="int",
            )
            return default

    async def get_bool(self, key: str, default: bool = False) -> bool:
        raw = await self.get_value(key)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    # ── Write ───────────────────────────────────────────

    async def upsert(
        self,
        key: str,
        *,
        value: str | None,
        category: str | None = None,
        description: str | None = None,
        is_secret: bool | None = None,
        actor: User,
    ) -> AppSetting:
        """
        Create or update a setting.

        - Validates `value` against KNOWN_SETTINGS registry (raises 422).
        - Computes an effective `is_secret` (True if the key is a known
          secret OR the caller set it explicitly).
        - Redacts the value in the audit log whenever EITHER state is secret.
        - Invalidates the cache for this key.
        """
        # Validate BEFORE touching the DB so failures are clean 422s.
        try:
            validated_value = validate_value(key, value)
        except ValueError as exc:
            raise ValidationError(f"{key}: {exc}") from exc

        existing = await self.repo.by_key(key)

        # Effective is_secret: sticky — once True, stays True unless the
        # caller explicitly sets it to False AND the key isn't registered
        # as secret. Registered secrets can never be demoted.
        known_secret = is_secret_key(key)
        if existing is not None:
            if existing.is_secret and is_secret is False and known_secret:
                raise ValidationError(
                    f"{key} is a registered secret and cannot be un-marked"
                )
            effective_secret = (
                is_secret if is_secret is not None else existing.is_secret
            )
        else:
            effective_secret = (
                is_secret if is_secret is not None else known_secret
            )

        # Derive category from key prefix when not specified (only on create).
        derived_category = category
        if derived_category is None:
            if existing is not None:
                derived_category = existing.category
            else:
                derived_category = (
                    key.split(".", 1)[0] if "." in key else "general"
                )

        if existing is None:
            setting = AppSetting(
                key=key,
                value=validated_value,
                category=derived_category,
                description=description,
                is_secret=effective_secret,
            )
            self.db.add(setting)
            await self.db.flush()

            await self.audit.log(
                action=AuditAction.CREATE,
                table_name="app_settings",
                record_id=setting.id,
                user_id=actor.id,
                new_data=_audit_payload(
                    key=key,
                    value=validated_value,
                    is_secret=effective_secret,
                    category=derived_category,
                ),
            )
            cache_invalidate(key)
            return setting

        old_value = existing.value
        old_secret = existing.is_secret
        existing.value = validated_value
        existing.is_secret = effective_secret
        existing.category = derived_category
        if description is not None:
            existing.description = description

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="app_settings",
            record_id=existing.id,
            user_id=actor.id,
            old_data=_audit_payload(
                key=key,
                value=old_value,
                is_secret=old_secret or effective_secret,
                category=existing.category,
            ),
            new_data=_audit_payload(
                key=key,
                value=validated_value,
                is_secret=effective_secret,
                category=derived_category,
            ),
        )
        cache_invalidate(key)
        return existing

    async def bulk_update(
        self,
        items: list[tuple[str, str | None]],
        *,
        actor: User,
    ) -> list[AppSetting]:
        """
        Update many settings in one transaction. Each item goes through
        the same validation as `upsert`; a single failure aborts the batch.
        """
        results: list[AppSetting] = []
        for key, value in items:
            setting = await self.upsert(
                key, value=value, actor=actor,
            )
            results.append(setting)
        # One cache flush for the whole batch.
        cache_invalidate()
        return results

    async def delete(self, key: str, *, actor: User) -> None:
        setting = await self.repo.by_key(key)
        if setting is None:
            raise NotFoundError(f"Setting {key!r} not found")

        old_data = _audit_payload(
            key=setting.key,
            value=setting.value,
            is_secret=setting.is_secret,
            category=setting.category,
        )
        await self.repo.delete(setting)
        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="app_settings",
            record_id=setting.id,
            user_id=actor.id,
            old_data=old_data,
        )
        cache_invalidate(key)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _audit_payload(
    *,
    key: str,
    value: str | None,
    is_secret: bool,
    category: str,
) -> dict:
    """
    Build an audit-log payload with the value redacted when the setting
    is secret. `AuditService` also redacts on the way out; this ensures
    the raw value is never even written into `old_data` / `new_data` JSONB.
    """
    return {
        "key": key,
        "value": "***" if is_secret and value is not None else value,
        "is_secret": is_secret,
        "category": category,
    }