"""
Seed default application settings.

Idempotent — safe to re-run. Existing values are never overwritten;
only missing keys are created and registry metadata is reconciled.

Run: python -m scripts.seed_settings
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.settings import constants as s
from app.modules.settings.models import AppSetting

# Register every model module.
import app.core.models_registry  # noqa: F401


# Default values, keyed by the constants in app/modules/settings/constants.py.
# Category, description, secret flag, and validation all come from
# KNOWN_SETTINGS — this file only supplies the initial values.
DEFAULTS: dict[str, str] = {
    # ── Business identity ───────────────────────────────
    s.KEY_BUSINESS_NAME: "NOCTRA Autoworks",
    s.KEY_BUSINESS_TAGLINE: "Precision motorcycle refinishing",
    s.KEY_BUSINESS_ADDRESS: "Jl. Contoh No. 123, Jakarta",
    s.KEY_BUSINESS_PHONE: "+62 812 3456 7890",
    s.KEY_BUSINESS_EMAIL: "hello@noctra.local",
    s.KEY_BUSINESS_TAX_ID: "",
    s.KEY_BUSINESS_CURRENCY: "IDR",
    s.KEY_BUSINESS_TIMEZONE: "Asia/Jakarta",

    # ── CRM ─────────────────────────────────────────────
    s.KEY_CRM_LEAD_AUTO_STATUS: "LEAD",
    s.KEY_CRM_INQUIRY_AUTO_ASSIGN: "false",
    s.KEY_CRM_INQUIRY_FOLLOWUP_HOURS: "24",

    # ── Costing / pricing ───────────────────────────────
    s.KEY_COSTING_OVERHEAD_MONTHLY: "5500000",
    s.KEY_COSTING_MONTHLY_LABOR_HOURS: "220",
    s.KEY_COSTING_DEFAULT_TARGET_MARGIN: "50",
    s.KEY_COSTING_DEFAULT_MARKUP: "100",
    s.KEY_COSTING_MIN_MARGIN: "30",

    # ── Email / SMTP ────────────────────────────────────
    # Blank host/credentials mean "not configured yet". `EMAIL_ENABLED`
    # in app/core/config.py still gates actual sending.
    s.KEY_EMAIL_SMTP_HOST: "",
    s.KEY_EMAIL_SMTP_PORT: "587",
    s.KEY_EMAIL_SMTP_USERNAME: "",
    s.KEY_EMAIL_SMTP_PASSWORD: "",
    s.KEY_EMAIL_FROM_ADDRESS: "hello@noctra.local",

    # ── Finance ─────────────────────────────────────────
    s.KEY_FINANCE_INVOICE_PREFIX: "INV",
    s.KEY_FINANCE_PAYMENT_TERMS_DAYS: "14",
    s.KEY_FINANCE_TAX_RATE_PCT: "11",

    # ── Inventory ───────────────────────────────────────
    s.KEY_INVENTORY_LOW_STOCK_THRESHOLD_PCT: "20",
    s.KEY_INVENTORY_WASTE_TOLERANCE_PCT: "5",

    # ── Notifications ───────────────────────────────────
    s.KEY_NOTIFICATIONS_SALES_EMAIL: "sales@noctra.local",
    s.KEY_NOTIFICATIONS_WORKSHOP_EMAIL: "workshop@noctra.local",

    # ── Public site & intake ────────────────────────────
    s.KEY_PUBLIC_INQUIRY_ENABLED: "true",
    s.KEY_PUBLIC_INQUIRY_RATE_LIMIT: "5",
    s.KEY_PUBLIC_AUTO_RESPONSE_ENABLED: "true",
    s.KEY_PUBLIC_AUTO_RESPONSE_SUBJECT: "Terima kasih atas inquiry Anda — NOCTRA Autoworks",
    s.KEY_PUBLIC_PHONE: "+62 812 3456 7890",
    s.KEY_PUBLIC_EMAIL: "hello@noctra.local",
    s.KEY_PUBLIC_ADDRESS: "Jl. Contoh No. 123, Jakarta",
    s.KEY_PUBLIC_WHATSAPP: "+62 812 3456 7890",
}


async def main() -> int:
    print("Seeding app settings...")

    # Fail loudly if a default has no registry entry — that would mean
    # the seed and the settings registry have drifted apart.
    unregistered = sorted(set(DEFAULTS) - set(s.KNOWN_SETTINGS))
    unseeded = sorted(set(s.KNOWN_SETTINGS) - set(DEFAULTS))
    if unregistered or unseeded:
        if unregistered:
            print(
                "  ! no registry spec for: " + ", ".join(unregistered),
                file=sys.stderr,
            )
        if unseeded:
            print(
                "  ! registry keys without a default: " + ", ".join(unseeded),
                file=sys.stderr,
            )
        return 1

    validated: dict[str, str | None] = {}
    for key, raw_value in DEFAULTS.items():
        try:
            validated[key] = s.validate_value(key, raw_value)
        except ValueError as exc:
            print(f"  ! invalid default for {key}: {exc}", file=sys.stderr)
            return 1

    created = 0
    updated = 0
    unchanged = 0

    async with SessionLocal() as db:
        try:
            existing = {
                row.key: row
                for row in (await db.execute(select(AppSetting))).scalars().all()
            }

            for key, value in validated.items():
                spec = s.KNOWN_SETTINGS[key]
                row = existing.get(key)

                if row is None:
                    db.add(
                        AppSetting(
                            key=key,
                            value=value,
                            category=spec.category,
                            description=spec.description,
                            is_secret=spec.is_secret,
                        )
                    )
                    created += 1
                    print(f"  + {key}")
                    continue

                # Values belong to the operator — never overwrite them.
                # Metadata belongs to the registry, so reconcile it.
                changed = False
                if row.category != spec.category:
                    row.category = spec.category
                    changed = True
                if row.is_secret != spec.is_secret:
                    row.is_secret = spec.is_secret
                    changed = True
                if not row.description:
                    row.description = spec.description
                    changed = True

                if changed:
                    updated += 1
                else:
                    unchanged += 1

            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Settings seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print(
        f"\n✅ Settings seed complete. "
        f"Created: {created}, updated: {updated}, unchanged: {unchanged}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
