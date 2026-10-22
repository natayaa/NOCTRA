"""Regression tests: create endpoints serialize empty selectin collections.

Both paths used to raise MissingGreenlet because the response schema reads a
relationship that was never loaded on a freshly flushed instance.
"""

from uuid import UUID

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.vehicles.models import Vehicle


@pytest.fixture
async def admin_headers(client: AsyncClient, db):
    user = User(
        username="admin_g",
        email="admin_g@noctra.local",
        full_name="Admin Greenlet",
        hashed_password=hash_password("password123"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_g", "password": "password123"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_customer(client: AsyncClient, headers: dict) -> str:
    r = await client.post(
        "/api/v1/customers",
        headers=headers,
        json={"name": "Greenlet Cust", "phone": "081200000001"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_inquiry_returns_empty_photos(
    client: AsyncClient, admin_headers, db
):
    customer_id = await _create_customer(client, admin_headers)
    customer = await db.get(Customer, UUID(customer_id))
    vehicle = Vehicle(
        customer_id=customer.id,
        brand="Toyota",
        model="Supra",
        plate_number="B 4321 XYZ",
    )
    db.add(vehicle)
    await db.commit()

    r = await client.post(
        "/api/v1/inquiries",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "vehicle_id": str(vehicle.id),
            "description": "Full body repaint with custom graphics.",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"].startswith("NOCTRA-I-")
    assert body["photos"] == []
    assert body["vehicle_id"] == str(vehicle.id)


@pytest.mark.asyncio
async def test_create_project_returns_empty_items(client: AsyncClient, admin_headers):
    customer_id = await _create_customer(client, admin_headers)
    r = await client.post(
        "/api/v1/projects",
        headers=admin_headers,
        json={"customer_id": customer_id, "title": "Repaint Build"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"].startswith("NOCTRA-P-")
    assert body["items"] == []
