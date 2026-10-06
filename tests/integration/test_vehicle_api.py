"""Vehicles API tests."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.auth.models import User


@pytest.fixture
async def admin_headers(client: AsyncClient, db):
    user = User(
        username="admin_v",
        email="admin_v@noctra.local",
        full_name="Admin V",
        hashed_password=hash_password("password123"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_v", "password": "password123"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_vehicle(client: AsyncClient, admin_headers):
    c = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={"name": "Vehicle Owner", "phone": "0800999988"},
    )
    cid = c.json()["id"]

    r = await client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=admin_headers,
        json={"brand": "Yamaha", "model": "Mio", "category": "SCOOTER"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["brand"] == "Yamaha"


@pytest.mark.asyncio
async def test_invalid_category_rejected(client: AsyncClient, admin_headers):
    c = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={"name": "Bad Cat", "phone": "0800777766"},
    )
    cid = c.json()["id"]
    r = await client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=admin_headers,
        json={"brand": "X", "model": "Y", "category": "NOT_A_CATEGORY"},
    )
    assert r.status_code == 422