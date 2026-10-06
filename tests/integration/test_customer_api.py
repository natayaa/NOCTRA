"""Customers API tests."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.auth.models import User


@pytest.fixture
async def admin_headers(client: AsyncClient, db):
    user = User(
        username="admin_t",
        email="admin_t@noctra.local",
        full_name="Admin Test",
        hashed_password=hash_password("password123"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_t", "password": "password123"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_customer(client: AsyncClient, admin_headers):
    r = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={"name": "Ivan", "phone": "081234567890"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"].startswith("NOCTRA-C-")
    assert body["status"] == "LEAD"


@pytest.mark.asyncio
async def test_duplicate_phone_rejected(client: AsyncClient, admin_headers):
    payload = {"name": "Ivan A", "phone": "0811111111"}
    r1 = await client.post("/api/v1/customers", headers=admin_headers, json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/customers", headers=admin_headers, json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_customers_pagination(client: AsyncClient, admin_headers):
    for i in range(3):
        await client.post(
            "/api/v1/customers",
            headers=admin_headers,
            json={"name": f"Cust {i}", "phone": f"08000000{i:02d}"},
        )
    r = await client.get("/api/v1/customers?page=1&size=2", headers=admin_headers)
    body = r.json()
    assert body["meta"]["total"] >= 3
    assert len(body["items"]) == 2