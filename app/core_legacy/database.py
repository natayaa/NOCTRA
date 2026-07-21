# core/database.py - FULL FIXED
import logging
from sqlalchemy import text  # ✅ TAMBAHKAN INI!
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from core.base import Base
from core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Database Engine
# =============================================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# =============================================================================
# Session Factory
# =============================================================================

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Database Dependency - ✅ FIXED
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dengan proper lifecycle management.

    ⚠️ CRITICAL: 
    - Session dibuat di sini
    - Commit jika sukses
    - Rollback jika error
    - Close SELALU dilakukan di finally
    """
    session = AsyncSessionLocal()
    try:
        logger.debug(f"Session created: {id(session)}")
        yield session
        # Jika tidak ada error, commit
        await session.commit()
        logger.debug(f"Session committed: {id(session)}")
    except Exception as e:
        # Jika error, rollback
        logger.error(f"Session error, rolling back: {e}")
        await session.rollback()
        raise
    finally:
        # SELALU close session
        await session.close()
        logger.debug(f"Session closed: {id(session)}")


# =============================================================================
# Type Alias
# =============================================================================

SessionDep = AsyncSession


# =============================================================================
# Health Check - ✅ FIXED (Menggunakan text())
# =============================================================================

async def check_db_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        async with engine.connect() as conn:
            # ✅ WAJIB pakai text() untuk raw SQL di SQLAlchemy 2.0
            await conn.execute(text("SELECT 1"))
            await conn.commit()
        logger.info("✅ Database health check passed")
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


# =============================================================================
# Migration Helper
# =============================================================================

async def create_tables():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tables created successfully")


async def drop_tables():
    """Drop all tables (use with caution!)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("⚠️ All tables dropped!")
