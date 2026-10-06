"""
Run all NOCTRA seed scripts in order.

Idempotent — safe to re-run.

Run: python -m scripts.seed_all
"""

from __future__ import annotations

import asyncio
import sys

from scripts import (
    seed as seed_perms_roles,
    seed_catalog as seed_vehicle_catalog,
    seed_employees as seed_employees,
    seed_materials,
    seed_services,
    seed_pricing_rules,
    seed_settings as seed_app_settings
)


STEPS = [
    ("permissions & roles", seed_perms_roles.main),
    ("app settings", seed_app_settings.main),
    ("vehicle catalog", seed_vehicle_catalog.main),
    # Phase 3+ — will be no-ops until the corresponding tables exist:
    ("service catalog", seed_services.main),
    ("material catalog", seed_materials.main),
    ("employees", seed_employees.main),
    ("pricing rules", seed_pricing_rules.main),
]


async def main() -> int:
    failures = 0
    for name, fn in STEPS:
        print(f"\n=== {name} ===")
        code = await fn() if asyncio.iscoroutinefunction(fn) else fn()
        if code != 0:
            failures += 1
            print(f"  ✗ {name} returned {code}")

    print("\n" + "=" * 50)
    if failures:
        print(f"❌ {failures} seed step(s) failed.")
        return 1
    print("✅ All seed steps completed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))