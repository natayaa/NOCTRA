"""Settings API tests."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole


async def _make_superuser(db) -> User:
    user = User(
        username="settingsadmin",
        email="settingsadmin@noctra.local",
        full_name="Settings Admin",
        hashed_password=hash_password("supersecret1"),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    return user


@pytest.mark.asyncio
async def test_settings_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/settings")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_settings_requires_superuser(client: AsyncClient, db):
    user = User(
        username="regular",
        email="regular@noctra.local",
        full_name="Regular",
        hashed_password=hash_password("supersecret1"),
        is_active=True,
    )
    db.add(user)
    await db.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "regular", "password": "supersecret1"},
    )
    token = login.json()["access_token"]

    r = await client.get(
        "/api/v1/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_superuser_can_list_settings(client: AsyncClient, db):
    await _make_superuser(db)

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "settingsadmin", "password": "supersecret1"},
    )
    token = login.json()["access_token"]

    r = await client.get(
        "/api/v1/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)