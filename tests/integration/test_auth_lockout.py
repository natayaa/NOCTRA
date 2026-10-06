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
    assert user.failed_login_attempts == 3, (
        f"expected 3 failed attempts, got {user.failed_login_attempts}"
    )