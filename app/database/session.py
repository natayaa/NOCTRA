from contextlib import asynccontextmanager
from typing import AsyncGenerator, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncConnection,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)

from database.base import Base


class Database:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def init(
        self,
        db_url: str,
        *,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 5,
    ) -> None:

        self._engine = create_async_engine(
            db_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=30,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args={
                "command_timeout": 30,
                "server_settings": {
                    "application_name": "NOCTRA",
                },
            },
        )

        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if self._sessionmaker is None:
            raise RuntimeError("Database not initialized")

        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_tables(self) -> None:
        if self._engine is None:
            raise RuntimeError("Database not initialized")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        if self._engine is None:
            raise RuntimeError("Database not initialized")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


session_manager = Database()


async def get_dbs() -> AsyncGenerator[AsyncSession, None]:
    async with session_manager.session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_dbs)]