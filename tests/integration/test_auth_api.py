"""Auth API tests."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.auth.models import User


@pytest.fixture
async def user(db):
    u = User(
        username="testuser",
        email="testuser@noctra.local",
        full_name="Test User",
        hashed_password=hash_password("supersecret1"),
        is_active=True,
    )
    db.add(u)
    await db.commit()
    return u


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, user):
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "supersecret1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, user):
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "wrongpass1"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "whatever1"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient, user):
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "supersecret1"},
    )
    token = login.json()["access_token"]

    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "testuser"