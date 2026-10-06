"""Health endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness(client: AsyncClient):
    r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}