"""
Seed starter pricing rules.

Idempotent — matches on (name) to avoid duplicates.

Run: python -m scripts.seed_pricing_rules
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.pricing.models import PricingRule

import app.core.models_registry  # noqa: F401


RULES: list[dict] = [
    {
        "name": "Default (any service)",
        "service_interest": None,
        "vehicle_category": None,
        "target_margin_pct": 50,
        "min_margin_pct": 30,
        "complexity_factor": 1.0,
        "notes": "Fallback rule. Applied when no specific rule matches.",
    },
    {
        "name": "Full body repaint — Scooter",
        "service_interest": "REPAINT",
        "vehicle_category": "SCOOTER",
        "target_margin_pct": 55,
        "min_margin_pct": 35,
        "complexity_factor": 1.0,
        "notes": "High-volume, competitive segment.",
    },
    {
        "name": "Full body repaint — Underbone",
        "service_interest": "REPAINT",
        "vehicle_category": "UNDERBONE",
        "target_margin_pct": 55,
        "min_margin_pct": 35,
        "complexity_factor": 1.0,
    },
    {
        "name": "Full body repaint — Sport",
        "service_interest": "REPAINT",
        "vehicle_category": "SPORT",
        "target_margin_pct": 60,
        "min_margin_pct": 40,
        "complexity_factor": 1.15,
        "notes": "Fairings and graphics add complexity.",
    },
    {
        "name": "Full body repaint — Big Bike",
        "service_interest": "REPAINT",
        "vehicle_category": "BIG_BIKE",
        "target_margin_pct": 60,
        "min_margin_pct": 40,
        "complexity_factor": 1.25,
    },
    {
        "name": "Panel repaint",
        "service_interest": "PANEL_REPAINT",
        "vehicle_category": None,
        "target_margin_pct": 60,
        "min_margin_pct": 40,
        "complexity_factor": 1.0,
        "notes": "Small jobs with fixed overhead — require higher margin.",
    },
    {
        "name": "Restoration",
        "service_interest": "RESTORATION",
        "vehicle_category": None,
        "target_margin_pct": 50,
        "min_margin_pct": 35,
        "complexity_factor": 1.1,
        "notes": "Long duration, unpredictable scope.",
    },
    {
        "name": "Custom paint",
        "service_interest": "CUSTOM_PAINT",
        "vehicle_category": None,
        "target_margin_pct": 65,
        "min_margin_pct": 45,
        "complexity_factor": 1.2,
        "notes": "High-skill work — charge accordingly.",
    },
    {
        "name": "Detailing",
        "service_interest": "DETAILING",
        "vehicle_category": None,
        "target_margin_pct": 70,
        "min_margin_pct": 50,
        "complexity_factor": 1.0,
        "notes": "Low material cost, high margin.",
    },
]


async def main() -> int:
    print("Seeding pricing rules...")
    created = 0
    skipped = 0

    async with SessionLocal() as db:
        try:
            for item in RULES:
                existing = (
                    await db.execute(
                        select(PricingRule).where(PricingRule.name == item["name"])
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    skipped += 1
                    continue
                db.add(PricingRule(**item))
                created += 1
                print(f"  + {item['name']}")

            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print(f"\n✅ Pricing rules seed complete. Created: {created}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))