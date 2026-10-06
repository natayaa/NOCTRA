"""
Seed a starter set of workshop employees.

Idempotent — safe to re-run.

Run: python -m scripts.seed_employees
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.projects.models import Employee

import app.core.models_registry  # noqa: F401


EMPLOYEES: list[dict] = [
    {
        "code": "EMP-001",
        "name": "Budi Santoso",
        "position": "Head Painter",
        "hourly_rate": 35_000,
        "monthly_salary": 6_500_000,
    },
    {
        "code": "EMP-002",
        "name": "Andi Wijaya",
        "position": "Painter",
        "hourly_rate": 25_000,
        "monthly_salary": 4_500_000,
    },
    {
        "code": "EMP-003",
        "name": "Siti Rahayu",
        "position": "Prep Technician",
        "hourly_rate": 20_000,
        "monthly_salary": 3_500_000,
    },
    {
        "code": "EMP-004",
        "name": "Rudi Hartono",
        "position": "Body Technician",
        "hourly_rate": 28_000,
        "monthly_salary": 5_000_000,
    },
    {
        "code": "EMP-005",
        "name": "Dewi Lestari",
        "position": "Detailing",
        "hourly_rate": 18_000,
        "monthly_salary": 3_200_000,
    },
]


async def main() -> int:
    print("Seeding employees...")
    created = 0
    skipped = 0

    async with SessionLocal() as db:
        try:
            for item in EMPLOYEES:
                existing = (
                    await db.execute(
                        select(Employee).where(Employee.code == item["code"])
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    skipped += 1
                    continue
                db.add(Employee(**item))
                created += 1
                print(f"  + {item['code']}: {item['name']} ({item['position']})")

            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print(f"\n✅ Employee seed complete. Created: {created}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))