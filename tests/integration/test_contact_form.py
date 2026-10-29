"""Public contact form — multipart submissions must reach the route intact.

The CSRF middleware parses multipart bodies to read `_csrf`; under
BaseHTTPMiddleware that consumed stream is not replayed downstream, so
the route used to receive an empty form ("Name is required").
"""

import time
from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select

import app.core.upload as upload
from app.core.form_guard import make_form_timestamp
from app.modules.customers.models import Customer
from app.modules.inquiries.models import Inquiry, InquiryPhoto


def _form_ts(*, age_seconds: int = 10) -> str:
    """A render timestamp old enough to pass the min-fill-time check."""
    return make_form_timestamp(now=time.time() - age_seconds)


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (16, 16), (20, 20, 20)).save(buf, format="JPEG")
    return buf.getvalue()


def _form(csrf: str) -> dict[str, str]:
    return {
        "_csrf": csrf,
        "_form_ts": _form_ts(),
        "name": "Budi Santoso",
        "phone": "081234567890",
        "email": "budi@example.com",
        "vehicle_brand": "Yamaha",
        "vehicle_model": "Mio",
        "vehicle_year": "2018",
        "service_interest": "REPAINT",
        "description": "Cat ulang bodi motor dengan warna hitam doff.",
    }


async def _csrf_token(client: AsyncClient) -> str:
    page = await client.get("/contact")
    assert page.status_code == 200
    token = page.cookies.get("noctra_csrf")
    assert token
    return token


@pytest.mark.asyncio
async def test_multipart_fields_reach_validation(client: AsyncClient):
    csrf = await _csrf_token(client)
    data = _form(csrf) | {"description": "too short"}
    files = {"photo_1": ("bike.jpg", b"not-an-image", "image/jpeg")}

    r = await client.post("/contact", data=data, files=files)

    assert r.status_code == 422
    assert "Description must be at least 20 characters" in r.text
    assert "Name is required" not in r.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("vehicle_year", "not-a-year"),
        ("vehicle_year", "3000"),
        ("desired_date", "31-12-2026"),
    ],
)
async def test_malformed_payload_returns_400_without_inquiry(
    client: AsyncClient, db, field, value
):
    """Garbage year/date must not escape as a 500 on a public endpoint."""
    csrf = await _csrf_token(client)
    data = _form(csrf) | {field: value}

    r = await client.post("/contact", data=data)

    assert r.status_code == 400, r.text
    assert "periksa kembali" in r.text
    assert (await db.execute(select(Inquiry))).scalars().all() == []


@pytest.mark.asyncio
async def test_contact_submission_with_photo_creates_inquiry(
    client: AsyncClient, db, tmp_path, monkeypatch
):
    monkeypatch.setattr(upload, "MEDIA_ROOT", tmp_path)
    monkeypatch.setattr(upload, "INQUIRY_UPLOAD_DIR", tmp_path / "inquiries")

    csrf = await _csrf_token(client)
    files = {"photo_1": ("bike.jpg", _jpeg_bytes(), "image/jpeg")}

    r = await client.post("/contact", data=_form(csrf), files=files)

    assert r.status_code == 303, r.text
    assert r.headers["location"].startswith("/contact/success?ref=NOCTRA-I-")

    customer = (await db.execute(select(Customer))).scalar_one()
    inquiry = (await db.execute(select(Inquiry))).scalar_one()
    photo = (await db.execute(select(InquiryPhoto))).scalar_one()

    assert customer.name == "Budi Santoso"
    assert customer.source == "WEBSITE"
    assert inquiry.customer_id == customer.id
    assert inquiry.source == "WEBSITE"
    assert inquiry.description.startswith("Cat ulang")
    assert photo.inquiry_id == inquiry.id
    assert photo.is_primary is True
    assert photo.file_path.startswith("/media/inquiries/")


@pytest.mark.asyncio
async def test_instant_submission_is_silently_dropped(client: AsyncClient, db):
    """A form filled in milliseconds is a bot. Answer success, store nothing."""
    csrf = await _csrf_token(client)
    data = _form(csrf) | {"_form_ts": make_form_timestamp()}

    r = await client.post("/contact", data=data)

    assert r.status_code == 303
    assert r.headers["location"] == "/contact/success"
    assert (await db.execute(select(Inquiry))).scalars().all() == []


@pytest.mark.asyncio
async def test_missing_timestamp_is_silently_dropped(client: AsyncClient, db):
    csrf = await _csrf_token(client)
    data = _form(csrf)
    data.pop("_form_ts")

    r = await client.post("/contact", data=data)

    assert r.status_code == 303
    assert (await db.execute(select(Inquiry))).scalars().all() == []


@pytest.mark.asyncio
async def test_double_submit_returns_same_inquiry(client: AsyncClient, db):
    """Retries and double-clicks must not create a second inquiry."""
    csrf = await _csrf_token(client)
    data = _form(csrf)

    first = await client.post("/contact", data=data)
    second = await client.post("/contact", data=data)

    assert first.status_code == 303 and second.status_code == 303
    assert first.headers["location"] == second.headers["location"]
    assert first.headers["location"].startswith("/contact/success?ref=NOCTRA-I-")
    inquiries = (await db.execute(select(Inquiry))).scalars().all()
    assert len(inquiries) == 1
