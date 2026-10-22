"""Shared pytest fixtures for NOCTRA tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Disable debug re-raise so error handlers return JSON
settings.APP_DEBUG = False

from app.core.database import Base, get_session  # noqa: E402
from app.main import create_app  # noqa: E402

# Register every SQLAlchemy model
import app.core.models_registry  # noqa: F401,E402


# Dedicated test DB: <POSTGRES_DB>_test
TEST_DB_URL = settings.database_url.replace(
    f"/{settings.POSTGRES_DB}",
    f"/{settings.POSTGRES_DB}_test",
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Session-scoped engine with NullPool — no cross-loop connection reuse."""
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


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(engine):
    """Truncate every table after each test — keeps tests isolated."""
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The sliding-window limiter is module-global; reset it per test.

    Without this, login calls accumulate across the suite (10/min per IP)
    and later tests receive 429 instead of a token.
    """
    from app.core.rate_limit import limiter

    limiter._buckets.clear()
    yield
    limiter._buckets.clear()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


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

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()