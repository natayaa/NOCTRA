"""
Seed the initial material catalog.

Idempotent — safe to re-run. Only creates missing entries; never overwrites.

Run: python -m scripts.seed_materials
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.inventory.constants import MaterialCategory, Unit
from app.modules.inventory.models import Material

import app.core.models_registry  # noqa: F401


MATERIALS: list[dict] = [
    # ── Primers ─────────────────────────────────────────
    {
        "code": "PRIMER-EPOXY-1L",
        "name": "Epoxy Primer",
        "brand": "Nippon",
        "category": MaterialCategory.PRIMER.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 180_000,
    },
    {
        "code": "PRIMER-FILLER-1L",
        "name": "Polyester Filler Primer",
        "brand": "Nippon",
        "category": MaterialCategory.PRIMER.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 150_000,
    },
    {
        "code": "PRIMER-SURFACER-1L",
        "name": "Surfacer Primer",
        "brand": "Sikkens",
        "category": MaterialCategory.PRIMER.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 220_000,
    },

    # ── Basecoats ───────────────────────────────────────
    {
        "code": "BASE-BLACK-1L",
        "name": "Base Coat Black",
        "brand": "Sikkens",
        "category": MaterialCategory.BASECOAT.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 320_000,
    },
    {
        "code": "BASE-WHITE-1L",
        "name": "Base Coat White",
        "brand": "Sikkens",
        "category": MaterialCategory.BASECOAT.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 320_000,
    },
    {
        "code": "BASE-RED-1L",
        "name": "Base Coat Red",
        "brand": "Sikkens",
        "category": MaterialCategory.BASECOAT.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 340_000,
    },
    {
        "code": "BASE-BLUE-1L",
        "name": "Base Coat Blue",
        "brand": "Sikkens",
        "category": MaterialCategory.BASECOAT.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 340_000,
    },
    {
        "code": "BASE-METALLIC-SILVER-1L",
        "name": "Metallic Silver Base",
        "brand": "Sikkens",
        "category": MaterialCategory.BASECOAT.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 420_000,
    },

    # ── Clearcoats ──────────────────────────────────────
    {
        "code": "CLEAR-BELKOTE-2100-1L",
        "name": "Belkote 2100 Clear",
        "brand": "Belkote",
        "category": MaterialCategory.CLEARCOAT.value,
        "purchase_unit": Unit.BOTTLE.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 450_000,
    },
    {
        "code": "CLEAR-BELKOTE-3000-1L",
        "name": "Belkote 3000 High-Solid Clear",
        "brand": "Belkote",
        "category": MaterialCategory.CLEARCOAT.value,
        "purchase_unit": Unit.BOTTLE.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 620_000,
    },
    {
        "code": "CLEAR-SIKKENS-1L",
        "name": "Sikkens Autoclear Plus",
        "brand": "Sikkens",
        "category": MaterialCategory.CLEARCOAT.value,
        "purchase_unit": Unit.CAN.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 580_000,
    },

    # ── Thinners ────────────────────────────────────────
    {
        "code": "THINNER-STD-1L",
        "name": "Standard Thinner",
        "brand": "Generic",
        "category": MaterialCategory.THINNER.value,
        "purchase_unit": Unit.BOTTLE.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 45_000,
    },
    {
        "code": "THINNER-PU-1L",
        "name": "PU Thinner",
        "brand": "Sikkens",
        "category": MaterialCategory.THINNER.value,
        "purchase_unit": Unit.BOTTLE.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 85_000,
    },
    {
        "code": "THINNER-SLOW-1L",
        "name": "Slow Evaporating Thinner",
        "brand": "Sikkens",
        "category": MaterialCategory.THINNER.value,
        "purchase_unit": Unit.BOTTLE.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 110_000,
    },

    # ── Chemicals / Hardeners ───────────────────────────
    {
        "code": "CHEM-HARDENER-CLEAR-100G",
        "name": "Clearcoat Hardener",
        "brand": "Belkote",
        "category": MaterialCategory.CHEMICAL.value,
        "purchase_unit": Unit.BOTTLE.value,
        "stock_unit": Unit.GR.value,
        "stock_units_per_purchase": 100,
        "current_purchase_price": 60_000,
    },
    {
        "code": "CHEM-WAX-GREASE-1L",
        "name": "Wax & Grease Remover",
        "brand": "3M",
        "category": MaterialCategory.CHEMICAL.value,
        "purchase_unit": Unit.BOTTLE.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 1000,
        "current_purchase_price": 95_000,
    },
    {
        "code": "CHEM-POLISH-500ML",
        "name": "Cutting Compound",
        "brand": "3M",
        "category": MaterialCategory.CHEMICAL.value,
        "purchase_unit": Unit.BOTTLE.value,
        "stock_unit": Unit.ML.value,
        "stock_units_per_purchase": 500,
        "current_purchase_price": 140_000,
    },

    # ── Consumables ─────────────────────────────────────
    {
        "code": "CONS-SANDING-P320",
        "name": "Sanding Paper 320 grit",
        "brand": "3M",
        "category": MaterialCategory.CONSUMABLE.value,
        "purchase_unit": Unit.PIECE.value,
        "stock_unit": Unit.PIECE.value,
        "stock_units_per_purchase": 1,
        "current_purchase_price": 5_000,
    },
    {
        "code": "CONS-SANDING-P600",
        "name": "Sanding Paper 600 grit",
        "brand": "3M",
        "category": MaterialCategory.CONSUMABLE.value,
        "purchase_unit": Unit.PIECE.value,
        "stock_unit": Unit.PIECE.value,
        "stock_units_per_purchase": 1,
        "current_purchase_price": 6_000,
    },
    {
        "code": "CONS-SANDING-P1000",
        "name": "Sanding Paper 1000 grit",
        "brand": "3M",
        "category": MaterialCategory.CONSUMABLE.value,
        "purchase_unit": Unit.PIECE.value,
        "stock_unit": Unit.PIECE.value,
        "stock_units_per_purchase": 1,
        "current_purchase_price": 7_500,
    },
    {
        "code": "CONS-MASKING-TAPE-24MM",
        "name": "Masking Tape 24mm",
        "brand": "3M",
        "category": MaterialCategory.CONSUMABLE.value,
        "purchase_unit": Unit.ROLL.value,
        "stock_unit": Unit.ROLL.value,
        "stock_units_per_purchase": 1,
        "current_purchase_price": 12_000,
    },
    {
        "code": "CONS-MASKING-PAPER",
        "name": "Masking Paper",
        "brand": "3M",
        "category": MaterialCategory.CONSUMABLE.value,
        "purchase_unit": Unit.ROLL.value,
        "stock_unit": Unit.ROLL.value,
        "stock_units_per_purchase": 1,
        "current_purchase_price": 25_000,
    },
    {
        "code": "CONS-TACK-CLOTH",
        "name": "Tack Cloth",
        "brand": "3M",
        "category": MaterialCategory.CONSUMABLE.value,
        "purchase_unit": Unit.PIECE.value,
        "stock_unit": Unit.PIECE.value,
        "stock_units_per_purchase": 1,
        "current_purchase_price": 8_000,
    },
]


async def main() -> int:
    print("Seeding material catalog...")
    created = 0
    skipped = 0

    async with SessionLocal() as db:
        try:
            for item in MATERIALS:
                existing = (
                    await db.execute(
                        select(Material).where(Material.code == item["code"])
                    )
                ).scalar_one_or_none()

                if existing is not None:
                    skipped += 1
                    continue

                db.add(Material(**item))
                created += 1
                print(f"  + {item['code']}: {item['name']}")

            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print(f"\n✅ Material seed complete. Created: {created}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))