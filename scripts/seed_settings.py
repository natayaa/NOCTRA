"""
Seed default application settings.

Idempotent — safe to re-run.

Run: python -m scripts.seed_settings
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.settings.models import AppSetting

# Register every model module.
import app.core.models_registry  # noqa: F401


SETTINGS: list[dict] = [
    # ── Business identity ───────────────────────────────
    {
        "key": "business.name",
        "value": "NOCTRA Autoworks",
        "category": "business",
        "description": "Legal business name",
    },
    {
        "key": "business.tagline",
        "value": "Precision motorcycle refinishing",
        "category": "business",
        "description": "Short tagline shown on invoices",
    },
    {
        "key": "business.address",
        "value": "Jl. Contoh No. 123, Jakarta",
        "category": "business",
        "description": "Workshop address",
    },
    {
        "key": "business.phone",
        "value": "+62 812 3456 7890",
        "category": "business",
        "description": "Public contact phone",
    },
    {
        "key": "business.email",
        "value": "hello@noctra.local",
        "category": "business",
        "description": "Public contact email",
    },
    {
        "key": "business.tax_id",
        "value": "",
        "category": "business",
        "description": "NPWP / Tax ID",
    },
    {
        "key": "business.currency",
        "value": "IDR",
        "category": "business",
        "description": "Default currency code",
    },
    {
        "key": "business.timezone",
        "value": "Asia/Jakarta",
        "category": "business",
        "description": "Operational timezone",
    },

    # ── CRM ────────────────────────────────────────────
    {
        "key": "crm.lead_auto_status",
        "value": "LEAD",
        "category": "crm",
        "description": "Status assigned to new customers from public intake",
    },
    {
        "key": "crm.inquiry_auto_assign",
        "value": "false",
        "category": "crm",
        "description": "Auto-assign inquiries to sales team round-robin",
    },
    {
        "key": "crm.inquiry_followup_hours",
        "value": "24",
        "category": "crm",
        "description": "Hours before an uncontacted inquiry is flagged",
    },

    # ── Costing / Pricing ──────────────────────────────
    {
        "key": "costing.overhead_monthly",
        "value": "5500000",
        "category": "costing",
        "description": "Total monthly overhead in IDR (rent+utilities+admin)",
    },
    {
        "key": "costing.monthly_labor_hours",
        "value": "220",
        "category": "costing",
        "description": "Standard productive hours per painter per month",
    },
    {
        "key": "costing.default_target_margin_pct",
        "value": "50",
        "category": "costing",
        "description": "Default target gross margin percentage",
    },
    {
        "key": "costing.default_markup_pct",
        "value": "100",
        "category": "costing",
        "description": "Default markup percentage on HPP",
    },
    {
        "key": "costing.minimum_margin_pct",
        "value": "30",
        "category": "costing",
        "description": "Below this margin, quote requires approval",
    },

    # ── Inventory ──────────────────────────────────────
    {
        "key": "inventory.low_stock_threshold_pct",
        "value": "20",
        "category": "inventory",
        "description": "Flag materials when stock falls below this % of min_stock",
    },
    {
        "key": "inventory.waste_tolerance_pct",
        "value": "5",
        "category": "inventory",
        "description": "Acceptable material waste percentage per project",
    },

    # ── Finance ────────────────────────────────────────
    {
        "key": "finance.invoice_prefix",
        "value": "INV",
        "category": "finance",
        "description": "Invoice code prefix",
    },
    {
        "key": "finance.payment_terms_days",
        "value": "14",
        "category": "finance",
        "description": "Default payment terms in days",
    },
    {
        "key": "finance.tax_rate_pct",
        "value": "11",
        "category": "finance",
        "description": "Default VAT/PPN percentage",
    },

    # ── Public intake ──────────────────────────────────
    {
        "key": "public.inquiry_enabled",
        "value": "true",
        "category": "public",
        "description": "Whether the public inquiry form is open",
    },
    {
        "key": "public.inquiry_rate_limit_per_hour",
        "value": "5",
        "category": "public",
        "description": "Max inquiries per IP per hour",
    },
    {
        "key": "public.auto_response_enabled",
        "value": "true",
        "category": "public",
        "description": "Send confirmation email to inquiry submitters",
    },
    {
        "key": "public.auto_response_subject",
        "value": "Terima kasih atas inquiry Anda — NOCTRA Autoworks",
        "category": "public",
        "description": "Subject line for auto-response email",
    },

    # ── Notifications ──────────────────────────────────
    {
        "key": "notifications.sales_email",
        "value": "sales@noctra.local",
        "category": "notifications",
        "description": "Where new inquiries are announced",
    },
    {
        "key": "notifications.workshop_email",
        "value": "workshop@noctra.local",
        "category": "notifications",
        "description": "Where project status changes are announced",
    },
]


async def main() -> int:
    print("Seeding app settings...")
    created = 0
    updated = 0

    async with SessionLocal() as db:
        try:
            for item in SETTINGS:
                existing = (
                    await db.execute(
                        select(AppSetting).where(AppSetting.key == item["key"])
                    )
                ).scalar_one_or_none()

                if existing is None:
                    db.add(
                        AppSetting(
                            key=item["key"],
                            value=item["value"],
                            category=item["category"],
                            description=item["description"],
                            is_secret=False,
                        )
                    )
                    created += 1
                else:
                    # Don't overwrite values the operator has changed.
                    # Only fill in missing descriptions.
                    if not existing.description and item.get("description"):
                        existing.description = item["description"]
                        updated += 1

            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Settings seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print(f"\n✅ Settings seed complete. Created: {created}, updated: {updated}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))