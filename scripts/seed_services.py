"""
Seed the service catalog.

Idempotent — safe to re-run.
Dormant until the `services` table exists (Phase 3).

Run: python -m scripts.seed_services
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.vehicles.constants import VehicleCategory

# Register every model module (uncomment services when it exists).
import app.core.models_registry  # noqa: F401
# from app.modules.services.models import Service  # ← Phase 3


SERVICES: list[dict] = [
    # ── Repaint ─────────────────────────────────────────
    {
        "code": "REPAINT-FULL",
        "name": "Full Body Repaint",
        "category": "REPAINT",
        "vehicle_category": None,        # any category
        "estimated_duration_hours": 40,
        "target_margin_pct": 55.0,
    },
    {
        "code": "REPAINT-PANEL",
        "name": "Panel Repaint",
        "category": "REPAINT",
        "vehicle_category": None,
        "estimated_duration_hours": 8,
        "target_margin_pct": 60.0,
    },
    {
        "code": "REPAINT-TANK",
        "name": "Tank Repaint",
        "category": "REPAINT",
        "vehicle_category": None,
        "estimated_duration_hours": 10,
        "target_margin_pct": 58.0,
    },
    {
        "code": "REPAINT-FENDER",
        "name": "Fender Repaint",
        "category": "REPAINT",
        "vehicle_category": None,
        "estimated_duration_hours": 6,
        "target_margin_pct": 60.0,
    },
    {
        "code": "REPAINT-FAIRING",
        "name": "Fairing Repaint",
        "category": "REPAINT",
        "vehicle_category": VehicleCategory.SPORT.value,
        "estimated_duration_hours": 14,
        "target_margin_pct": 55.0,
    },

    # ── Restoration ─────────────────────────────────────
    {
        "code": "RESTORE-MINOR",
        "name": "Minor Restoration",
        "category": "RESTORATION",
        "vehicle_category": None,
        "estimated_duration_hours": 60,
        "target_margin_pct": 50.0,
    },
    {
        "code": "RESTORE-MEDIUM",
        "name": "Medium Restoration",
        "category": "RESTORATION",
        "vehicle_category": None,
        "estimated_duration_hours": 120,
        "target_margin_pct": 48.0,
    },
    {
        "code": "RESTORE-FULL",
        "name": "Full Restoration",
        "category": "RESTORATION",
        "vehicle_category": None,
        "estimated_duration_hours": 240,
        "target_margin_pct": 45.0,
    },

    # ── Custom Paint ────────────────────────────────────
    {
        "code": "CUSTOM-AIRBRUSH",
        "name": "Custom Airbrush",
        "category": "CUSTOM_PAINT",
        "vehicle_category": None,
        "estimated_duration_hours": 50,
        "target_margin_pct": 55.0,
    },
    {
        "code": "CUSTOM-GRAPHICS",
        "name": "Custom Graphics",
        "category": "CUSTOM_PAINT",
        "vehicle_category": None,
        "estimated_duration_hours": 30,
        "target_margin_pct": 55.0,
    },
    {
        "code": "CUSTOM-PINSTRIPE",
        "name": "Pinstriping",
        "category": "CUSTOM_PAINT",
        "vehicle_category": None,
        "estimated_duration_hours": 12,
        "target_margin_pct": 60.0,
    },

    # ── Detailing ───────────────────────────────────────
    {
        "code": "DETAIL-BASIC",
        "name": "Basic Detailing",
        "category": "DETAILING",
        "vehicle_category": None,
        "estimated_duration_hours": 4,
        "target_margin_pct": 65.0,
    },
    {
        "code": "DETAIL-PREMIUM",
        "name": "Premium Detailing + Ceramic",
        "category": "DETAILING",
        "vehicle_category": None,
        "estimated_duration_hours": 8,
        "target_margin_pct": 60.0,
    },

    # ── Panel Repair ────────────────────────────────────
    {
        "code": "PANEL-DENT",
        "name": "Dent Removal",
        "category": "PANEL_REPAIR",
        "vehicle_category": None,
        "estimated_duration_hours": 4,
        "target_margin_pct": 55.0,
    },
    {
        "code": "PANEL-CRACK",
        "name": "Crack Repair",
        "category": "PANEL_REPAIR",
        "vehicle_category": None,
        "estimated_duration_hours": 6,
        "target_margin_pct": 55.0,
    },
]


async def main() -> int:
    print("Seeding service catalog...")
    try:
        # from app.modules.services.models import Service  # ← Phase 3
        pass
    except ImportError:
        print("  ! services module not yet implemented — skipping")
        return 0

    print("  (nothing to do until Phase 3 defines the Service model)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))