"""RBAC permission resolution tests."""

import pytest
from sqlalchemy import select

from app.core.constants import PermissionCode
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole
from app.modules.rbac.permissions import permissions_for_user


async def _make_role(db, name: str, codes: list[PermissionCode]) -> Role:
    role = Role(name=name, description=name, is_system=True)
    db.add(role)
    await db.flush()

    for code in codes:
        perm = (
            await db.execute(select(Permission).where(Permission.code == code.value))
        ).scalar_one_or_none()
        if perm is None:
            perm = Permission(code=code.value, description=code.name)
            db.add(perm)
            await db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await db.flush()
    return role


@pytest.mark.asyncio
async def test_permissions_for_user(db):
    role = await _make_role(
        db,
        "test-sales",
        [PermissionCode.CUSTOMER_READ, PermissionCode.VEHICLE_READ],
    )
    user = User(
        username="rbacuser",
        email="rbacuser@noctra.local",
        full_name="RBAC User",
        hashed_password=hash_password("supersecret1"),
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()

    perms = await permissions_for_user(db, user.id)
    assert PermissionCode.CUSTOMER_READ.value in perms
    assert PermissionCode.VEHICLE_READ.value in perms
    assert PermissionCode.USER_DELETE.value not in perms


@pytest.mark.asyncio
async def test_user_with_no_roles_has_no_permissions(db):
    user = User(
        username="noroleuser",
        email="norole@noctra.local",
        full_name="No Role",
        hashed_password=hash_password("supersecret1"),
    )
    db.add(user)
    await db.commit()

    perms = await permissions_for_user(db, user.id)
    assert perms == set()