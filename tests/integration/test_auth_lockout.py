"""Lockout behavior after repeated failed logins."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.auth.models import User


@pytest.mark.asyncio
async def test_failed_login_increments_counter(client: AsyncClient, db):
    user = User(
        username="locktest",
        email="locktest@noctra.local",
        full_name="Lock Test",
        hashed_password=hash_password("correctpass1"),
        is_active=True,
    )
    db.add(user)
    await db.commit()

    for _ in range(3):
        r = await client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": "wrongpass1"},
        )
        assert r.status_code == 401

    await db.refresh(user)
    assert user.failed_login_attempts == 3


@pytest.mark.asyncio
async def test_account_locks_after_max_attempts(client: AsyncClient, db):
    from datetime import UTC, datetime, timedelta

    user = User(
        username="locktest2",
        email="locktest2@noctra.local",
        full_name="Lock Test 2",
        hashed_password=hash_password("correctpass1"),
        is_active=True,
    )
    db.add(user)
    await db.commit()

    # 5 failed attempts triggers the lock
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"username": "locktest2", "password": "wrongpass1"},
        )

    await db.refresh(user)
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(UTC)

    # Even correct password is rejected while locked
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "locktest2", "password": "correctpass1"},
    )
    assert r.status_code == 401
    assert "locked" in r.json()["error"]["message"].lower()