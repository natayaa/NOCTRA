"""
Seed common motorcycle brands and models.

Idempotent — safe to re-run.

Run: python -m scripts.seed_catalog
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.vehicles.constants import VehicleCategory
from app.modules.vehicles.models import VehicleBrand, VehicleModel

# Register every model module before SQLAlchemy configures mappers.
import app.core.models_registry  # noqa: F401


CATALOG: dict[str, dict] = {
    "Honda": {
        "country": "Japan",
        "models": [
            ("Beat", VehicleCategory.SCOOTER.value),
            ("Vario", VehicleCategory.SCOOTER.value),
            ("PCX", VehicleCategory.SCOOTER.value),
            ("PCX160", VehicleCategory.SCOOTER.value),
            ("Scoopy", VehicleCategory.SCOOTER.value),
            ("Genio", VehicleCategory.SCOOTER.value),
            ("Supra", VehicleCategory.UNDERBONE.value),
            ("Revo", VehicleCategory.UNDERBONE.value),
            ("Blade", VehicleCategory.UNDERBONE.value),
            ("Sonic 150R", VehicleCategory.UNDERBONE.value),
            ("CB150R", VehicleCategory.NAKED.value),
            ("CB150X", VehicleCategory.NAKED.value),
            ("CB250R", VehicleCategory.NAKED.value),
            ("CBR150R", VehicleCategory.SPORT.value),
            ("CBR250RR", VehicleCategory.SPORT.value),
            ("CBR600RR", VehicleCategory.SPORT.value),
            ("CB500X", VehicleCategory.BIG_BIKE.value),
            ("CRF250 Rally", VehicleCategory.BIG_BIKE.value),
        ],
    },
    "Yamaha": {
        "country": "Japan",
        "models": [
            ("Mio", VehicleCategory.SCOOTER.value),
            ("Mio Sporty", VehicleCategory.SCOOTER.value),
            ("Mio M3", VehicleCategory.SCOOTER.value),
            ("Fino", VehicleCategory.SCOOTER.value),
            ("NMAX", VehicleCategory.SCOOTER.value),
            ("Aerox 155", VehicleCategory.SCOOTER.value),
            ("Lexi", VehicleCategory.SCOOTER.value),
            ("X-Ride", VehicleCategory.SCOOTER.value),
            ("Jupiter", VehicleCategory.UNDERBONE.value),
            ("Vega", VehicleCategory.UNDERBONE.value),
            ("MX King", VehicleCategory.UNDERBONE.value),
            ("Vixion", VehicleCategory.NAKED.value),
            ("MT-15", VehicleCategory.NAKED.value),
            ("MT-03", VehicleCategory.NAKED.value),
            ("MT-07", VehicleCategory.NAKED.value),
            ("R15", VehicleCategory.SPORT.value),
            ("R25", VehicleCategory.SPORT.value),
            ("R6", VehicleCategory.SPORT.value),
            ("XSR155", VehicleCategory.CLASSIC.value),
            ("XSR700", VehicleCategory.CLASSIC.value),
            ("Tenere 700", VehicleCategory.BIG_BIKE.value),
        ],
    },
    "Suzuki": {
        "country": "Japan",
        "models": [
            ("Address", VehicleCategory.SCOOTER.value),
            ("Nex", VehicleCategory.SCOOTER.value),
            ("Avenis", VehicleCategory.SCOOTER.value),
            ("Burgman Street", VehicleCategory.SCOOTER.value),
            ("Satria F150", VehicleCategory.UNDERBONE.value),
            ("GSX-R150", VehicleCategory.SPORT.value),
            ("GSX-S150", VehicleCategory.NAKED.value),
            ("GSX-R600", VehicleCategory.SPORT.value),
            ("V-Strom 250", VehicleCategory.BIG_BIKE.value),
        ],
    },
    "Kawasaki": {
        "country": "Japan",
        "models": [
            ("Ninja 150", VehicleCategory.SPORT.value),
            ("Ninja 250", VehicleCategory.SPORT.value),
            ("Ninja 400", VehicleCategory.SPORT.value),
            ("Ninja 650", VehicleCategory.SPORT.value),
            ("Ninja ZX-6R", VehicleCategory.SPORT.value),
            ("KLX 150", VehicleCategory.NAKED.value),
            ("KLX 250", VehicleCategory.BIG_BIKE.value),
            ("W175", VehicleCategory.CLASSIC.value),
            ("W800", VehicleCategory.CLASSIC.value),
            ("Z250", VehicleCategory.NAKED.value),
            ("Z400", VehicleCategory.NAKED.value),
            ("Z650", VehicleCategory.NAKED.value),
            ("Versys 250", VehicleCategory.BIG_BIKE.value),
            ("Versys 650", VehicleCategory.BIG_BIKE.value),
        ],
    },
    "Royal Enfield": {
        "country": "India",
        "models": [
            ("Classic 350", VehicleCategory.CLASSIC.value),
            ("Bullet 350", VehicleCategory.CLASSIC.value),
            ("Meteor 350", VehicleCategory.CLASSIC.value),
            ("Hunter 350", VehicleCategory.CLASSIC.value),
            ("Himalayan", VehicleCategory.BIG_BIKE.value),
            ("Interceptor 650", VehicleCategory.CLASSIC.value),
            ("Continental GT 650", VehicleCategory.CLASSIC.value),
        ],
    },
    "Triumph": {
        "country": "UK",
        "models": [
            ("Bonneville T100", VehicleCategory.CLASSIC.value),
            ("Bonneville T120", VehicleCategory.CLASSIC.value),
            ("Speed Twin", VehicleCategory.CLASSIC.value),
            ("Street Twin", VehicleCategory.CLASSIC.value),
            ("Street Triple", VehicleCategory.NAKED.value),
            ("Speed Triple", VehicleCategory.NAKED.value),
            ("Trident 660", VehicleCategory.NAKED.value),
            ("Tiger 900", VehicleCategory.BIG_BIKE.value),
            ("Scrambler 1200", VehicleCategory.CLASSIC.value),
        ],
    },
    "Ducati": {
        "country": "Italy",
        "models": [
            ("Monster", VehicleCategory.NAKED.value),
            ("Monster 821", VehicleCategory.NAKED.value),
            ("Scrambler Icon", VehicleCategory.CLASSIC.value),
            ("Scrambler Full Throttle", VehicleCategory.CLASSIC.value),
            ("Panigale V2", VehicleCategory.SPORT.value),
            ("Panigale V4", VehicleCategory.SPORT.value),
            ("Supersport", VehicleCategory.SPORT.value),
            ("Multistrada V4", VehicleCategory.BIG_BIKE.value),
        ],
    },
    "BMW": {
        "country": "Germany",
        "models": [
            ("G 310 R", VehicleCategory.NAKED.value),
            ("G 310 GS", VehicleCategory.BIG_BIKE.value),
            ("F 750 GS", VehicleCategory.BIG_BIKE.value),
            ("F 850 GS", VehicleCategory.BIG_BIKE.value),
            ("R 1250 GS", VehicleCategory.BIG_BIKE.value),
            ("R nineT", VehicleCategory.CLASSIC.value),
            ("S 1000 RR", VehicleCategory.SPORT.value),
        ],
    },
    "KTM": {
        "country": "Austria",
        "models": [
            ("Duke 200", VehicleCategory.NAKED.value),
            ("Duke 250", VehicleCategory.NAKED.value),
            ("Duke 390", VehicleCategory.NAKED.value),
            ("RC 200", VehicleCategory.SPORT.value),
            ("RC 390", VehicleCategory.SPORT.value),
            ("Adventure 250", VehicleCategory.BIG_BIKE.value),
            ("Adventure 390", VehicleCategory.BIG_BIKE.value),
        ],
    },
    "Harley-Davidson": {
        "country": "USA",
        "models": [
            ("Sportster Iron 883", VehicleCategory.CLASSIC.value),
            ("Forty-Eight", VehicleCategory.CLASSIC.value),
            ("Street 750", VehicleCategory.CLASSIC.value),
            ("Fat Boy", VehicleCategory.BIG_BIKE.value),
            ("Softail Standard", VehicleCategory.BIG_BIKE.value),
        ],
    },
    "Vespa": {
        "country": "Italy",
        "models": [
            ("Primavera 150", VehicleCategory.SCOOTER.value),
            ("Sprint 150", VehicleCategory.SCOOTER.value),
            ("GTS 300", VehicleCategory.SCOOTER.value),
            ("Elettrica", VehicleCategory.SCOOTER.value),
        ],
    },
    "Piaggio": {
        "country": "Italy",
        "models": [
            ("Liberty 150", VehicleCategory.SCOOTER.value),
            ("Medley 150", VehicleCategory.SCOOTER.value),
            ("Beverly 300", VehicleCategory.SCOOTER.value),
        ],
    },
    "Benelli": {
        "country": "Italy",
        "models": [
            ("TNT 150", VehicleCategory.NAKED.value),
            ("TNT 250", VehicleCategory.NAKED.value),
            ("TNT 600", VehicleCategory.NAKED.value),
            ("Leoncino 500", VehicleCategory.CLASSIC.value),
        ],
    },
    "Aprilia": {
        "country": "Italy",
        "models": [
            ("SR 160", VehicleCategory.SCOOTER.value),
            ("RS 457", VehicleCategory.SPORT.value),
            ("Tuono 457", VehicleCategory.NAKED.value),
        ],
    },
}


async def main() -> int:
    print("Seeding vehicle catalog...")
    brands_created = 0
    models_created = 0

    async with SessionLocal() as db:
        try:
            for brand_name, meta in CATALOG.items():
                brand = (
                    await db.execute(
                        select(VehicleBrand).where(VehicleBrand.name == brand_name)
                    )
                ).scalar_one_or_none()

                if brand is None:
                    brand = VehicleBrand(
                        name=brand_name,
                        country=meta.get("country"),
                    )
                    db.add(brand)
                    await db.flush()
                    brands_created += 1
                    print(f"  + brand: {brand_name}")

                existing = {
                    m
                    for m in (
                        await db.execute(
                            select(VehicleModel.name).where(
                                VehicleModel.brand_id == brand.id
                            )
                        )
                    ).scalars().all()
                }

                for model_name, category in meta["models"]:
                    if model_name in existing:
                        continue
                    db.add(
                        VehicleModel(
                            brand_id=brand.id,
                            name=model_name,
                            category=category,
                        )
                    )
                    models_created += 1

            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Catalog seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print(f"\n✅ Catalog seed complete. Brands: +{brands_created}, Models: +{models_created}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))