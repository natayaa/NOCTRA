"""Business identity used on documents (invoices, reminder emails).

Values live in `app_settings` so the owner can change them without a
deploy; env-based PUBLIC_* values are the fallback for a fresh install.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.settings.constants import (
    KEY_BUSINESS_ADDRESS,
    KEY_BUSINESS_EMAIL,
    KEY_BUSINESS_NAME,
    KEY_BUSINESS_PHONE,
    KEY_BUSINESS_TAGLINE,
    KEY_BUSINESS_TAX_ID,
)
from app.modules.settings.service import SettingsService


async def business_profile(db: AsyncSession) -> dict[str, str | None]:
    svc = SettingsService(db)

    async def value(key: str, default: str | None) -> str | None:
        return await svc.get_value(key, default)

    return {
        "name": await value(KEY_BUSINESS_NAME, settings.APP_NAME),
        "tagline": await value(KEY_BUSINESS_TAGLINE, None),
        "address": await value(KEY_BUSINESS_ADDRESS, settings.PUBLIC_ADDRESS),
        "phone": await value(KEY_BUSINESS_PHONE, settings.PUBLIC_PHONE),
        "email": await value(KEY_BUSINESS_EMAIL, settings.PUBLIC_EMAIL),
        "tax_id": await value(KEY_BUSINESS_TAX_ID, None),
    }
