"""Fixtures for integration tests.

These require a live PostgreSQL database (name: <POSTGRES_DB>_test).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

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

# Disable debug re-raise so error handlers return JSON bodies in tests
settings.APP_DEBUG = False

from app.core.database import Base, get_session  # noqa: E402
from app.main import create_app  # noqa: E402

# Import every model module so Base.metadata is fully populated
import app.core.models_registry  # noqa: F401,E402


# Dedicated test database — NOCTRADB_test by default
TEST_DB_URL = settings.database_url.replace(
    f"/{settings.POSTGRES_DB}",
    f"/{settings.POSTGRES_DB}_test",
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    """
    Session-scoped engine. NullPool prevents connections from being
    reused across different event loops (the classic asyncpg issue).
    """
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


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    """
    httpx AsyncClient wired to the FastAPI app, with the app's
    `get_session` dependency overridden to use the test engine.
    """
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
        base_url="http://localhost",   # must match TRUSTED_HOSTS
    ) as ac:
        yield ac

    app.dependency_overrides.clear()