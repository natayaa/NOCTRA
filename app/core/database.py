from typing import AsyncGenerator, Optional, Dict, Any
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy.pool import AsyncAdaptedQueuePool
from contextlib import asynccontextmanager
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# ==================== BASE MODEL ====================

class BaseModel:
    """Base model with common conventions"""
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name"""
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return name

# Create declarative base
Base = declarative_base(cls=BaseModel)

# ==================== DATABASE MANAGER ====================

class DatabaseManager:
    """Core database manager for connection and session management"""
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connection pool"""
        if self._initialized:
            return
        
        try:
            # Build database URL
            database_url = settings.DATABASE_URL
            
            # Create engine
            self._engine = create_async_engine(
                database_url,
                echo=settings.DB_ECHO,
                echo_pool=settings.DB_ECHO_POOL,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=settings.DB_POOL_PRE_PING,
                poolclass=AsyncAdaptedQueuePool,
                connect_args={
                    "timeout": settings.DB_POOL_TIMEOUT,
                    "command_timeout": 60,
                    "server_settings": {
                        "application_name": settings.APP_NAME
                    }
                }
            )
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            
            self._initialized = True
            logger.info(f"Database initialized: {settings.DB_NAME} on {settings.DB_HOST}:{settings.DB_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close database connection pool"""
        if self._engine:
            await self._engine.dispose()
            self._initialized = False
            logger.info("Database connection closed")
    
    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return self._initialized
    
    @property
    def engine(self) -> AsyncEngine:
        """Get database engine"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """Get session factory"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session as context manager.
        Automatically handles commit/rollback.
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()
    
    async def get_raw_session(self) -> AsyncSession:
        """
        Get raw session without automatic commit.
        Caller is responsible for commit/rollback.
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory()
    
    async def create_tables(self) -> None:
        """Create all tables (development/testing only)"""
        if not self._initialized:
            await self.initialize()
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def drop_tables(self) -> None:
        """Drop all tables (development/testing only)"""
        if not self._initialized:
            await self.initialize()
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")

# ==================== SINGLETON INSTANCE ====================

db_manager = DatabaseManager()

# ==================== DEPENDENCIES FOR FASTAPI ====================

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI endpoints"""
    if not db_manager.is_initialized:
        await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        yield session

async def get_raw_db_session() -> AsyncSession:
    """
    Dependency for FastAPI endpoints that need raw session.
    Caller must manage commit/rollback.
    """
    if not db_manager.is_initialized:
        await db_manager.initialize()
    return await db_manager.get_raw_session()

# ==================== EXPORTS ====================

__all__ = [
    "Base",
    "db_manager",
    "get_db_session",
    "get_raw_db_session",
    "DatabaseManager",
]