"""Shared pytest fixtures for NOCTRA tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_session
from app.main import create_app

# Register every model so Base.metadata is fully populated.
import app.core.models_registry  # noqa: F401


# ── Dedicated test database: <POSTGRES_DB>_test
TEST_DB_URL = settings.database_url.replace(
    f"/{settings.POSTGRES_DB}",
    f"/{settings.POSTGRES_DB}_test",
)


# ── Session-scoped engine (NullPool prevents cross-loop reuse) ──
@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(
        TEST_DB_URL,
        poolclass=NullPool,
        future=True,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


# ── Function-scoped DB session ──────────────────────────────────
@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


# ── Function-scoped HTTP client (via ASGI transport) ────────────
@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_session():
        async with Session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()