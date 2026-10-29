"""Regression coverage for the project-wide polish batch.

Covers the fixes that are easy to break silently: list pagination,
filter-preserving links, the profile page, CSV formula neutralisation,
authenticated-page caching, and media cleanup.
"""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.csv_export import csv_cell
from app.core.security import hash_password
from app.core.config import settings
from app.modules.auth.dependencies import ACCESS_COOKIE_NAME
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.inquiries.models import Inquiry, InquiryPhoto
from app.modules.inventory.models import PurchaseOrder, Supplier
from app.modules.vehicles.models import Vehicle

PASSWORD = "password123"


async def _login(client: AsyncClient, db, *, username: str = "polish_admin") -> str:
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name="Polish Admin",
        hashed_password=hash_password(PASSWORD),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()

    r = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert r.status_code == 200, r.text

    r = await client.get("/admin/users")
    assert r.status_code == 200, r.text
    token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert token
    return token


@pytest.mark.asyncio
async def test_users_list_shows_pagination_and_page_size(client: AsyncClient, db):
    await _login(client, db, username="polish_admin_users")
    for i in range(2):
        db.add(
            User(
                username=f"polish_member_{i}",
                email=f"polish_member_{i}@example.com",
                full_name=f"Member {i}",
                hashed_password=hash_password(PASSWORD),
            )
        )
    await db.commit()

    page = await client.get("/admin/users?per_page=2")
    assert page.status_code == 200, page.text
    body = page.text

    # The pager used to sit outside `{% block content %}` and was dropped.
    assert 'aria-label="Pagination"' in body
    assert "Next page" in body
    assert 'id="per_page_users"' in body
    assert "No users yet" not in body


@pytest.mark.asyncio
async def test_purchase_order_chips_preserve_search_and_page_size(
    client: AsyncClient, db
):
    await _login(client, db, username="polish_admin_po")

    supplier = Supplier(code="SUP-POLISH", name="Polish Paint Supply")
    db.add(supplier)
    await db.flush()
    db.add(
        PurchaseOrder(
            code="PO-POLISH-1",
            supplier_id=supplier.id,
            status="DRAFT",
            order_date=date.today(),
        )
    )
    await db.commit()

    page = await client.get(
        "/admin/purchase-orders?q=POLISH&status=DRAFT&per_page=25"
    )
    assert page.status_code == 200, page.text
    body = page.text

    # Chips are real links now, keeping q/per_page instead of resetting them.
    assert "q=POLISH" in body
    assert "per_page=25" in body
    assert "?status={{ s }}" not in body
    # Search box exists and is bound to the handler's q filter.
    assert 'id="po-q"' in body


@pytest.mark.asyncio
async def test_vehicle_clear_filters_url_is_rendered(client: AsyncClient, db):
    await _login(client, db, username="polish_admin_vehicle")

    customer = Customer(code="CUS-POLISH", name="Filter Owner")
    db.add(customer)
    await db.flush()
    db.add(
        Vehicle(
            customer_id=customer.id,
            brand="Honda",
            model="Civic",
            plate_number="B 9999 POL",
        )
    )
    await db.commit()

    page = await client.get(
        f"/admin/vehicles?customer_id={customer.id}&q=does-not-match"
    )
    assert page.status_code == 200, page.text
    body = page.text

    assert "No vehicles match your filters" in body
    assert f"/admin/vehicles?customer_id={customer.id}" in body
    assert "%7B" not in body
    assert "{%" not in body


@pytest.mark.asyncio
async def test_profile_page_and_self_service_password_change(
    client: AsyncClient, db
):
    csrf = await _login(client, db, username="polish_profile")

    page = await client.get("/admin/profile")
    assert page.status_code == 200, page.text
    assert "Change password" in page.text
    assert 'action="/admin/profile/password"' in page.text
    assert "data-guard" in page.text

    # Wrong current password: bounced back with a message, still signed in.
    r = await client.post(
        "/admin/profile/password",
        data={
            "_csrf": csrf,
            "old_password": "wrong-password",
            "new_password": "new-password-456",
            "confirm_password": "new-password-456",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    error_page = await client.get(r.headers["location"])
    assert "Old password is incorrect" in error_page.text

    # Mismatched confirmation is rejected before touching the service.
    token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    r = await client.post(
        "/admin/profile/password",
        data={
            "_csrf": token,
            "old_password": PASSWORD,
            "new_password": "new-password-456",
            "confirm_password": "different-456",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "match" in r.headers["location"]

    # Successful change clears the session cookies and forces a re-login.
    token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    r = await client.post(
        "/admin/profile/password",
        data={
            "_csrf": token,
            "old_password": PASSWORD,
            "new_password": "new-password-456",
            "confirm_password": "new-password-456",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/admin/login?reset=1"
    assert client.cookies.get(ACCESS_COOKIE_NAME) is None

    relogin = await client.post(
        "/api/v1/auth/login",
        json={"username": "polish_profile", "password": "new-password-456"},
    )
    assert relogin.status_code == 200, relogin.text


@pytest.mark.asyncio
async def test_csv_export_neutralises_formulas(client: AsyncClient, db):
    await _login(client, db, username="polish_admin_csv")

    db.add(
        Customer(
            code="CUS-CSV-1",
            name="=cmd|' /C calc'!A0",
            phone="+62 812-3456",
            notes="-2+3",
        )
    )
    await db.commit()

    r = await client.get("/admin/customers/export.csv")
    assert r.status_code == 200, r.text
    body = r.text

    assert "'=cmd" in body          # formula neutralised
    assert "'' /C calc" not in body
    assert "'+62 812-3456" in body  # phone starting with + is text, not a sum
    assert "\n+62 812-3456" not in body


def test_csv_cell_helper_edges():
    assert csv_cell("=1+1") == "'=1+1"
    assert csv_cell("@SUM(A1)") == "'@SUM(A1)"
    assert csv_cell("\tTAB") == "'\tTAB"
    assert csv_cell("+62 812-3456") == "'+62 812-3456"
    assert csv_cell("-12.5") == "-12.5"
    assert csv_cell("+7") == "+7"
    assert csv_cell("-2+3") == "'-2+3"
    assert csv_cell("plain") == "plain"
    assert csv_cell(42) == 42
    assert csv_cell(None) is None


@pytest.mark.asyncio
async def test_admin_html_is_not_cached(client: AsyncClient, db):
    login = await client.get("/admin/login")
    assert login.status_code == 200
    assert login.headers["cache-control"] == "no-store, private"

    await _login(client, db, username="polish_admin_cache")
    page = await client.get("/admin/profile")
    assert page.headers["cache-control"] == "no-store, private"

    # Public pages may still be cached by the browser/proxy.
    public = await client.get("/")
    assert public.headers.get("cache-control") != "no-store, private"


@pytest.mark.asyncio
async def test_deleting_an_inquiry_photo_removes_the_file(
    client: AsyncClient, db, monkeypatch, tmp_path
):
    from app.core import upload as upload_module

    media_root = tmp_path / "media"
    photo_file = media_root / "inquiries" / "photo.png"
    photo_file.parent.mkdir(parents=True)
    photo_file.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    monkeypatch.setattr(upload_module, "MEDIA_ROOT", media_root)

    csrf = await _login(client, db, username="polish_admin_media")

    customer = Customer(code="CUS-MEDIA", name="Media Owner")
    db.add(customer)
    await db.flush()
    inquiry = Inquiry(
        code="INQ-MEDIA-1",
        customer_id=customer.id,
        description="Photo cleanup regression.",
    )
    db.add(inquiry)
    await db.flush()
    photo = InquiryPhoto(
        inquiry_id=inquiry.id,
        file_path="/media/inquiries/photo.png",
        file_name="photo.png",
        is_primary=True,
    )
    db.add(photo)
    await db.commit()

    detail = await client.get(f"/admin/inquiries/{inquiry.id}")
    assert detail.status_code == 200, detail.text

    r = await client.post(
        f"/admin/inquiries/{inquiry.id}/photos/{photo.id}/delete",
        data={"_csrf": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    assert not photo_file.exists()
    assert (
        await db.execute(select(InquiryPhoto).where(InquiryPhoto.id == photo.id))
    ).scalar_one_or_none() is None


def test_rate_limit_buckets_by_authentication_state():
    from starlette.requests import Request

    from app.core.config import settings
    from app.core.rate_limit import RateLimitMiddleware
    from app.modules.auth.dependencies import ACCESS_COOKIE_NAME

    def make(path: str, *, signed_in: bool) -> Request:
        headers = []
        if signed_in:
            headers.append((b"cookie", f"{ACCESS_COOKIE_NAME}=token".encode()))
            headers.append((b"cookie", b"noctra_refresh_token=refresh"))
        return Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": headers,
                "server": ("testserver", 80),
                "client": ("203.0.113.9", 12345),
            }
        )

    limit, _, key = RateLimitMiddleware._bucket_for(make("/admin/users", signed_in=True), "203.0.113.9")
    assert (limit, key) == (settings.RATE_LIMIT_API_PER_MINUTE, "admin:203.0.113.9")

    limit, _, key = RateLimitMiddleware._bucket_for(make("/admin/users", signed_in=False), "203.0.113.9")
    assert (limit, key) == (settings.RATE_LIMIT_PUBLIC_PER_MINUTE, "public:203.0.113.9")

    # Login stays on its own tight bucket whether or not a cookie is present.
    limit, _, key = RateLimitMiddleware._bucket_for(make("/admin/login", signed_in=True), "203.0.113.9")
    assert (limit, key) == (settings.RATE_LIMIT_LOGIN_PER_MINUTE, "login:203.0.113.9")


# ════════════════════════════════════════════════════════════════
# Admin UI refresh — breadcrumbs + filter tabs
# ════════════════════════════════════════════════════════════════

def test_admin_crumbs_cover_sections_and_detail_pages():
    from app.web.templates_env import _admin_crumbs

    def labels(path: str) -> list[str]:
        return [c["label"] for c in _admin_crumbs(path)]

    assert labels("/admin/inquiries") == ["Main", "Inquiries"]
    assert labels("/admin/inquiries/6f1c2f0e-8a3b-4c5d-9e7f-0a1b2c3d4e5f") == [
        "Main", "Inquiries", "Inquiry"
    ]
    assert labels("/admin/inquiries/new") == ["Main", "Inquiries", "New"]
    assert labels("/admin/inventory/transactions") == [
        "Workshop", "Inventory", "Stock movements"
    ]
    assert labels("/admin/reports/payables") == ["Finance", "Payables"]
    assert labels("/admin/email-logs") == ["System", "Email Log"]
    assert labels("/admin/customers/export.csv") == ["Main", "Customers", "Export"]

    # Detail page link points back at the list, never at itself.
    detail = _admin_crumbs("/admin/customers/123")
    assert detail[1]["href"] == "/admin/customers"
    assert detail[-1]["href"] is None

    # Non-admin paths render no breadcrumbs.
    assert _admin_crumbs("/") == []
    assert _admin_crumbs("/services") == []


@pytest.mark.asyncio
async def test_list_pages_use_filter_tabs_and_header_quick_create(
    client: AsyncClient, db
):
    await _login(client, db, username="polish_admin_ui")

    r = await client.get("/admin/inquiries")
    assert r.status_code == 200, r.text
    assert 'class="filter-tabs"' in r.text
    assert "filter-tab is-active" in r.text
    assert 'class="topbar-crumbs"' in r.text
    assert "quick-create" in r.text

    # Filter links reset to page 1 and keep the active parameter.
    r = await client.get("/admin/invoices?only_unpaid=true")
    assert r.status_code == 200, r.text
    assert "filter-tab is-active" in r.text

    # Every converted list page renders the tab component.
    for path in (
        "/admin/inventory/transactions",
        "/admin/materials",
        "/admin/customers",
        "/admin/employees",
        "/admin/users",
        "/admin/pricing-rules",
        "/admin/purchase-orders",
        "/admin/payments",
        "/admin/projects",
        "/admin/vehicles",
        "/admin/email-logs",
    ):
        r = await client.get(path)
        assert r.status_code == 200, (path, r.text[:300])
        assert 'class="filter-tabs"' in r.text, path
        assert "filter-tab is-active" in r.text, path


def test_materials_active_filter_is_tri_state():
    from app.web.admin.materials import _active_filter

    assert _active_filter(None) is None
    assert _active_filter("") is None
    assert _active_filter("all") is None
    assert _active_filter("true") is True
    assert _active_filter("1") is True
    assert _active_filter("false") is False
    assert _active_filter("0") is False
    assert _active_filter("bogus") is None
