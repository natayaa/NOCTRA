"""Browser-equivalent flow: admin creates an inquiry through the web form."""

from datetime import date, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.inquiries.models import Inquiry
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


@pytest.mark.asyncio
async def test_admin_web_create_inquiry_validation_error_renders_form(
    client: AsyncClient, db
):
    """A rejected form must re-render, not 500 with MissingGreenlet.

    The error path rolls back before rendering; that expires the ORM user,
    and the topbar reads it synchronously.
    """
    csrf = await _login_admin(client, db)

    r = await client.post(
        "/admin/inquiries",
        data={
            "_csrf": csrf,
            "description": "Repaint with a past target date.",
            "service_interest": "REPAINT",
            "source": "ADMIN",
            "desired_date": (date.today() - timedelta(days=5)).isoformat(),
        },
        follow_redirects=False,
    )
    assert r.status_code == 400, r.text
    assert "desired_date cannot be in the past" in r.text


@pytest.mark.asyncio
async def test_admin_web_create_inquiry_follow_up_after_desired(
    client: AsyncClient, db
):
    """A follow-up may be scheduled after the customer's target date."""
    csrf = await _login_admin(client, db)

    desired = date.today() + timedelta(days=30)
    follow_up = desired + timedelta(days=10)

    r = await client.post(
        "/admin/inquiries",
        data={
            "_csrf": csrf,
            "description": "Repaint, chased up after the target date.",
            "service_interest": "REPAINT",
            "source": "ADMIN",
            "desired_date": desired.isoformat(),
            "follow_up_date": follow_up.isoformat(),
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text

    detail = await client.get(r.headers["location"])
    assert detail.status_code == 200, detail.text

    inquiry_id = UUID(r.headers["location"].rstrip("/").split("/")[-1])
    stored = (
        await db.execute(select(Inquiry).where(Inquiry.id == inquiry_id))
    ).scalar_one()
    assert stored.desired_date == desired
    assert stored.follow_up_date == follow_up
