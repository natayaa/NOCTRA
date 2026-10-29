"""Self-service password reset.

The link is a signed token carrying a fingerprint of the current password
hash, so a successful reset burns the link without any server-side table.
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.core.tokens import create_password_reset_token
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.password_reset import password_fingerprint


async def _make_user(db, *, username="reset_user", email="reset@example.com"):
    user = User(
        username=username,
        email=email,
        full_name="Reset User",
        hashed_password=hash_password("old-password-1"),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    return user


def _token_for(user: User) -> str:
    return create_password_reset_token(
        str(user.id), password_fingerprint(user.hashed_password)
    )


async def _csrf(client: AsyncClient, path: str) -> str:
    page = await client.get(path)
    assert page.status_code == 200, page.text
    token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert token
    return token


@pytest.mark.asyncio
async def test_forgot_password_is_generic_for_unknown_accounts(client: AsyncClient):
    csrf = await _csrf(client, "/admin/forgot-password")

    r = await client.post(
        "/admin/forgot-password",
        data={"_csrf": csrf, "identifier": "nobody@example.com"},
        follow_redirects=False,
    )

    assert r.status_code == 303
    assert r.headers["location"].endswith("/admin/forgot-password?sent=1")

    page = await client.get("/admin/forgot-password?sent=1")
    assert "If that account exists" in page.text


@pytest.mark.asyncio
async def test_forgot_password_queues_audit_for_known_account(client: AsyncClient, db):
    user = await _make_user(db)
    csrf = await _csrf(client, "/admin/forgot-password")

    r = await client.post(
        "/admin/forgot-password",
        data={"_csrf": csrf, "identifier": user.email.upper()},
        follow_redirects=False,
    )
    assert r.status_code == 303

    audit = (await db.execute(select(AuditLog))).scalars().all()
    assert [a.action for a in audit] == ["PASSWORD_RESET"]
    assert audit[0].new_data["stage"] == "requested"


@pytest.mark.asyncio
async def test_reset_password_then_new_password_logs_in(client: AsyncClient, db):
    user = await _make_user(db)
    token = _token_for(user)

    page = await client.get(f"/admin/reset-password?token={token}")
    assert page.status_code == 200
    csrf = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert csrf

    r = await client.post(
        "/admin/reset-password",
        data={
            "_csrf": csrf,
            "token": token,
            "new_password": "brand-new-pass-2",
            "confirm_password": "brand-new-pass-2",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    assert r.headers["location"] == "/admin/login?reset=1"

    await db.refresh(user)
    assert verify_password("brand-new-pass-2", user.hashed_password)
    assert not verify_password("old-password-1", user.hashed_password)
    assert user.password_changed_at is not None
    assert user.failed_login_attempts == 0
    assert user.locked_until is None

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "reset_user", "password": "brand-new-pass-2"},
    )
    assert login.status_code == 200, login.text


@pytest.mark.asyncio
async def test_reset_link_is_single_use(client: AsyncClient, db):
    user = await _make_user(db)
    token = _token_for(user)

    csrf = await _csrf(client, f"/admin/reset-password?token={token}")
    first = await client.post(
        "/admin/reset-password",
        data={
            "_csrf": csrf,
            "token": token,
            "new_password": "brand-new-pass-2",
            "confirm_password": "brand-new-pass-2",
        },
        follow_redirects=False,
    )
    assert first.status_code == 303

    # Same link again — the stored hash (and therefore fingerprint) changed.
    csrf = await _csrf(client, f"/admin/reset-password?token={token}")
    second = await client.post(
        "/admin/reset-password",
        data={
            "_csrf": csrf,
            "token": token,
            "new_password": "another-pass-3",
            "confirm_password": "another-pass-3",
        },
        follow_redirects=False,
    )
    assert second.status_code == 400
    assert "already been used" in second.text

    await db.refresh(user)
    assert verify_password("brand-new-pass-2", user.hashed_password)


@pytest.mark.asyncio
async def test_reset_clears_lockout(client: AsyncClient, db):
    from datetime import UTC, datetime

    user = await _make_user(db, username="locked_user", email="locked@example.com")
    user.failed_login_attempts = 5
    user.locked_until = datetime.now(UTC) + timedelta(minutes=10)
    await db.commit()

    token = _token_for(user)
    csrf = await _csrf(client, f"/admin/reset-password?token={token}")
    r = await client.post(
        "/admin/reset-password",
        data={
            "_csrf": csrf,
            "token": token,
            "new_password": "fresh-password-4",
            "confirm_password": "fresh-password-4",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text

    await db.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


@pytest.mark.asyncio
async def test_reset_rejects_mismatched_passwords(client: AsyncClient, db):
    user = await _make_user(db)
    token = _token_for(user)

    csrf = await _csrf(client, f"/admin/reset-password?token={token}")
    r = await client.post(
        "/admin/reset-password",
        data={
            "_csrf": csrf,
            "token": token,
            "new_password": "brand-new-pass-2",
            "confirm_password": "typo-pass-2",
        },
        follow_redirects=False,
    )

    assert r.status_code == 400
    assert "do not match" in r.text
    await db.refresh(user)
    assert verify_password("old-password-1", user.hashed_password)


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["garbage-token", ""])
async def test_reset_rejects_bad_token(client: AsyncClient, db, token):
    user = await _make_user(db)
    csrf = await _csrf(client, "/admin/reset-password")

    r = await client.post(
        "/admin/reset-password",
        data={
            "_csrf": csrf,
            "token": token,
            "new_password": "brand-new-pass-2",
            "confirm_password": "brand-new-pass-2",
        },
        follow_redirects=False,
    )

    assert r.status_code == 400
    assert "invalid" in r.text.lower() or "missing" in r.text.lower()
    await db.refresh(user)
    assert verify_password("old-password-1", user.hashed_password)


@pytest.mark.asyncio
async def test_forgot_password_page_hides_form_when_disabled(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(settings, "PASSWORD_RESET_ENABLED", False)

    page = await client.get("/admin/forgot-password")

    assert page.status_code == 200
    assert "Self-service reset is off" in page.text
    assert 'action="/admin/forgot-password"' not in page.text
