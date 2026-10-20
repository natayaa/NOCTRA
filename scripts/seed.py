"""
Seed NOCTRA's permissions and roles.

Idempotent — safe to re-run. Adds anything missing; never removes.

Run: python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.constants import PermissionCode, RoleName
from app.core.database import SessionLocal
from app.modules.rbac.constants import DEFAULT_ROLE_PERMISSIONS
from app.modules.rbac.models import Permission, Role, RolePermission

# ── Register every model module before SQLAlchemy configures mappers.
# Without these, string relationship targets (e.g. `"User"` inside
# Role.users) fail to resolve.
from app.modules.auth import models as _auth_models          # noqa: F401
from app.modules.audit import models as _audit_models        # noqa: F401
from app.modules.settings import models as _settings_models  # noqa: F401


async def seed_permissions(db) -> dict[str, Permission]:
    existing = {
        p.code: p
        for p in (await db.execute(select(Permission))).scalars().all()
    }

    created = 0
    for code in PermissionCode:
        if code.value in existing:
            continue
        perm = Permission(
            code=code.value,
            description=code.name.replace("_", " ").title(),
        )
        db.add(perm)
        existing[code.value] = perm
        created += 1

    await db.flush()
    print(f"  permissions: {created} created, {len(existing)} total")
    return existing


async def seed_roles(db) -> dict[str, Role]:
    existing = {
        r.name: r
        for r in (await db.execute(select(Role))).scalars().all()
    }

    created = 0
    for role_name in RoleName:
        if role_name.value in existing:
            continue
        role = Role(
            name=role_name.value,
            description=role_name.value.replace("_", " ").title(),
            is_system=True,
        )
        db.add(role)
        existing[role_name.value] = role
        created += 1

    await db.flush()
    print(f"  roles:       {created} created, {len(existing)} total")
    return existing


async def seed_role_permissions(
    db,
    roles: dict[str, Role],
    perms: dict[str, Permission],
) -> None:
    existing = {
        (rp.role_id, rp.permission_id)
        for rp in (await db.execute(select(RolePermission))).scalars().all()
    }

    created = 0
    for role_name, codes in DEFAULT_ROLE_PERMISSIONS.items():
        role_key = role_name.value if hasattr(role_name, "value") else role_name
        role = roles.get(role_key)
        if role is None:
            print(f"  ! role not found: {role_key}", file=sys.stderr)
            continue

        for code in codes:
            perm_key = code.value if hasattr(code, "value") else code
            perm = perms.get(perm_key)
            if perm is None:
                print(f"  ! permission not found: {perm_key}", file=sys.stderr)
                continue

            key = (role.id, perm.id)
            if key in existing:
                continue

            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            existing.add(key)
            created += 1

    await db.flush()
    print(f"  grants:      {created} created, {len(existing)} total")


async def main() -> int:
    print("Seeding NOCTRA permissions and roles...")

    async with SessionLocal() as db:
        try:
            perms = await seed_permissions(db)
            roles = await seed_roles(db)
            await seed_role_permissions(db, roles, perms)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print("\n✅ Seed complete.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))