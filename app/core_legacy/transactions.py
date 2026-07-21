# core/transaction.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Transaction context manager.

    Usage:
        async with transaction(db) as session:
            # operasi database
            # auto commit jika sukses, auto rollback jika error
    """
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def in_transaction(session: AsyncSession, func, *args, **kwargs):
    """Execute function in transaction."""
    try:
        result = await func(*args, **kwargs)
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise
