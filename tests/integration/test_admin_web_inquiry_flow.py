"""Browser-equivalent flow: admin creates an inquiry through the web form."""

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.vehicles.models import Vehicle


async def _login_admin(client: AsyncClient, db) -> str:
    user = User(
        username="admin_web",
        email="admin_web@example.com",
        full_name="Admin Web",
        hashed_password=hash_password("password123"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()

    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_web", "password": "password123"},
    )
    assert r.status_code == 200, r.text

    r = await client.get("/admin/inquiries/new")
    assert r.status_code == 200, r.text
    csrf = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert csrf
    return csrf


@pytest.mark.asyncio
async def test_admin_web_create_inquiry(client: AsyncClient, db):
    csrf = await _login_admin(client, db)

    r = await client.post(
        "/admin/inquiries",
        data={
            "_csrf": csrf,
            "description": "Full body repaint with pearl white finish.",
            "service_interest": "REPAINT",
            "source": "ADMIN",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text

    detail = await client.get(r.headers["location"])
    assert detail.status_code == 200, detail.text


@pytest.mark.asyncio
async def test_admin_web_create_inquiry_with_customer_and_vehicle(
    client: AsyncClient, db
):
    csrf = await _login_admin(client, db)

    customer = Customer(
        code="NOCTRA-C-WEB-1",
        name="Web Flow Customer",
        phone="081200000099",
    )
    db.add(customer)
    await db.flush()
    vehicle = Vehicle(
        customer_id=customer.id,
        brand="Honda",
        model="Civic",
        plate_number="B 1234 WEB",
    )
    db.add(vehicle)
    await db.commit()

    form = await client.get(
        f"/admin/inquiries/new?customer_id={customer.id}&vehicle_id={vehicle.id}"
    )
    assert form.status_code == 200, form.text

    r = await client.post(
        "/admin/inquiries",
        data={
            "_csrf": csrf,
            "customer_id": str(customer.id),
            "vehicle_id": str(vehicle.id),
            "description": "Civic repaint in championship white.",
            "service_interest": "REPAINT",
            "source": "ADMIN",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text

    detail = await client.get(r.headers["location"])
    assert detail.status_code == 200, detail.text
