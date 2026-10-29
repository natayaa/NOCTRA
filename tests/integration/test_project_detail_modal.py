"""Project detail: add-item modal.

The add form used to live in a panel at the bottom of a long page, so an
operator adding paint materials had to scroll past the whole cost ledger.
It now opens in a native <dialog>. A rejected POST re-opens the modal via
`?error=…&add=1` so the operator lands back in the form.
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.inventory.models import Material
from app.modules.projects.models import Project, ProjectItem


async def _login(client: AsyncClient, db) -> None:
    user = User(
        username="modal_admin",
        email="modal_admin@example.com",
        full_name="Modal Admin",
        hashed_password=hash_password("password123"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()

    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "modal_admin", "password": "password123"},
    )
    assert r.status_code == 200, r.text


async def _project(db):
    customer = Customer(
        code="NOCTRA-C-2026-002000", name="Modal Customer", phone="081200002000"
    )
    db.add(customer)
    await db.flush()
    project = Project(
        code="NOCTRA-P-2026-002000",
        title="Modal repaint",
        customer_id=customer.id,
        status="IN_PROGRESS",
        start_date=date(2026, 10, 1),
    )
    db.add(project)
    material = Material(
        code="MAT-2K-CLEAR",
        name="Belkote 2100 clear coat",
        category="PAINT",
        purchase_unit="liter",
        stock_unit="ml",
        stock_units_per_purchase=1000,
        current_purchase_price=120_000,
    )
    db.add(material)
    await db.commit()
    return project, material


async def _csrf(client: AsyncClient, path: str) -> str:
    page = await client.get(path)
    assert page.status_code == 200, page.text
    token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert token
    return token


@pytest.mark.asyncio
async def test_detail_renders_add_item_modal(client: AsyncClient, db):
    await _login(client, db)
    project, material = await _project(db)

    page = await client.get(f"/admin/projects/{project.id}")

    assert page.status_code == 200, page.text
    body = page.text
    assert 'id="add-item-dialog"' in body
    assert 'class="form-dialog' in body
    assert 'aria-labelledby="add-item-title"' in body
    assert 'data-auto-open="0"' in body
    assert body.count("data-open-add-item") >= 3
    assert f'action="/admin/projects/{project.id}/items"' in body
    assert "Belkote 2100 clear coat" in body
    # The old always-visible panel at the bottom is gone.
    assert "Add the first one below" not in body


@pytest.mark.asyncio
async def test_rejected_add_reopens_modal_with_error(client: AsyncClient, db):
    await _login(client, db)
    project, _ = await _project(db)
    csrf = await _csrf(client, f"/admin/projects/{project.id}")

    r = await client.post(
        f"/admin/projects/{project.id}/items",
        data={
            "_csrf": csrf,
            "category": "MATERIAL",
            "description": "Clear coat",
            "estimated_quantity": "1",
        },
        follow_redirects=False,
    )

    assert r.status_code == 303, r.text
    assert "add=1" in r.headers["location"]

    page = await client.get(r.headers["location"])
    assert page.status_code == 200
    assert 'data-auto-open="1"' in page.text
    assert "data-add-error" in page.text
    assert "material_id is required for MATERIAL items" in page.text
    # The modal shows the readable message, not the raw Pydantic dump.
    assert "validation error for ProjectItemCreate" not in page.text

    assert (await db.execute(select(ProjectItem))).scalars().all() == []


@pytest.mark.asyncio
async def test_add_item_from_modal_persists(client: AsyncClient, db):
    await _login(client, db)
    project, material = await _project(db)
    csrf = await _csrf(client, f"/admin/projects/{project.id}")

    r = await client.post(
        f"/admin/projects/{project.id}/items",
        data={
            "_csrf": csrf,
            "category": "MATERIAL",
            "description": "Belkote 2100 clear coat",
            "material_id": str(material.id),
            "unit": "ml",
            "estimated_quantity": "750",
        },
        follow_redirects=False,
    )

    assert r.status_code == 303, r.text
    assert "add=1" not in r.headers["location"]

    stored = (await db.execute(select(ProjectItem))).scalar_one()
    assert stored.description == "Belkote 2100 clear coat"
    assert stored.category == "MATERIAL"
    assert stored.material_id == material.id
    # Unit cost is resolved from the material, not the typed value.
    assert float(stored.estimated_unit_cost) == pytest.approx(120.0)
    assert float(stored.estimated_cost) == pytest.approx(750 * 120.0)

    page = await client.get(r.headers["location"])
    assert page.status_code == 200
    assert 'data-auto-open="0"' in page.text
