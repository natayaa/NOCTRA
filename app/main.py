# app/main.py
"""
NOKTRA Autoworks Dashboard - Main Application Entry Point

FastAPI application with:
- Core infrastructure (database, cache, logging)
- Shared components
- Background tasks (Celery, Scheduler)
- Authentication module
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from app.core.config import settings
from app.core.database import db_manager
from app.core.cache import cache_manager
from app.core.logging import setup_logging, logger, LogContext
from app.core.exceptions import setup_exception_handlers, CoreException, ErrorResponseFormatter
from app.core.middleware import setup_middleware
from app.core.constants import APIConstants

from modules.auth.api.router import 

# ==================== APPLICATION LIFECYCLE ====================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # ============ STARTUP ============
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📊 Environment: {settings.APP_ENVIRONMENT.value}")
    logger.info(f"📝 Log Level: {settings.LOG_LEVEL}")
    logger.info("=" * 60)
    
    try:
        # 1. Initialize Database
        logger.info("Initializing database connection...")
        await db_manager.initialize()
        logger.info("✅ Database connected successfully")
        
        # 2. Initialize Cache (Redis)
        if settings.CACHE_ENABLED:
            logger.info("Initializing cache...")
            await cache_manager.initialize()
            if cache_manager.is_available():
                logger.info("✅ Cache connected successfully")
            else:
                logger.warning("⚠️ Cache is disabled or not available")
        else:
            logger.info("ℹ️ Cache is disabled by configuration")
        
        # 3. Initialize Background Tasks (if not disabled)
        if settings.FEATURE_BACKGROUND_TASKS:
            try:
                from app.background.scheduler import scheduler_manager
                from app.background.cron import register_cron_jobs
                
                logger.info("Initializing background scheduler...")
                await scheduler_manager.start()
                register_cron_jobs()
                logger.info("✅ Background scheduler started")
            except Exception as e:
                logger.error(f"⚠️ Failed to start background scheduler: {str(e)}")
                if settings.APP_ENVIRONMENT.value == "production":
                    logger.critical("Background tasks failed to start in production!")
        
        logger.info("✅ Application startup complete")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.critical(f"❌ Application startup failed: {str(e)}")
        raise
    
    # ============ RUNNING ============
    yield
    
    # ============ SHUTDOWN ============
    logger.info("=" * 60)
    logger.info("🛑 Shutting down application...")
    
    try:
        # 1. Stop background scheduler
        if settings.FEATURE_BACKGROUND_TASKS:
            try:
                from app.background.scheduler import scheduler_manager
                await scheduler_manager.stop()
                logger.info("✅ Background scheduler stopped")
            except Exception as e:
                logger.warning(f"⚠️ Failed to stop background scheduler: {str(e)}")
        
        # 2. Close cache connection
        if settings.CACHE_ENABLED:
            await cache_manager.close()
            logger.info("✅ Cache connection closed")
        
        # 3. Close database connection
        await db_manager.close()
        logger.info("✅ Database connection closed")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}")
    
    logger.info("✅ Application shutdown complete")
    logger.info("=" * 60)

# ==================== CREATE APPLICATION ====================

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=settings.API_DOCS_URL if settings.APP_ENVIRONMENT.value != "production" else None,
    redoc_url=settings.API_REDOC_URL if settings.APP_ENVIRONMENT.value != "production" else None,
    openapi_url=settings.API_OPENAPI_URL if settings.APP_ENVIRONMENT.value != "production" else None,
    lifespan=lifespan,
    contact={
        "name": settings.API_CONTACT_NAME,
        "email": settings.API_CONTACT_EMAIL,
    },
    license_info={
        "name": settings.API_LICENSE_NAME,
    },
)

# ==================== MIDDLEWARE ====================

# Setup custom middlewares (Request ID, Logging, CORS, Rate Limit, etc.)
setup_middleware(app)

# Add built-in middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=settings.CORS_EXPOSE_HEADERS,
    max_age=settings.CORS_MAX_AGE,
)

# Trusted Host middleware (for production)
if settings.APP_ENVIRONMENT.value == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.CORS_ALLOWED_ORIGINS,
    )

# ==================== EXCEPTION HANDLERS ====================

# Setup custom exception handlers
setup_exception_handlers(app)

# ==================== ROUTES ====================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENVIRONMENT.value,
        "status": "running",
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the status of all dependencies.
    """
    health_status = {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENVIRONMENT.value,
        },
        "services": {
            "database": {
                "status": "connected" if db_manager.is_initialized else "disconnected",
                "name": settings.DB_NAME,
                "host": settings.DB_HOST,
            },
            "cache": {
                "status": "connected" if cache_manager.is_available() else "disconnected",
                "enabled": settings.CACHE_ENABLED,
            },
            "background_tasks": {
                "enabled": settings.FEATURE_BACKGROUND_TASKS,
            },
        },
    }
    
    # Check if all critical services are connected
    is_healthy = (
        db_manager.is_initialized and
        (not settings.CACHE_ENABLED or cache_manager.is_available())
    )
    
    if not is_healthy:
        health_status["status"] = "degraded"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )
    
    return health_status

@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.
    Checks if the application is ready to serve traffic.
    """
    is_ready = (
        db_manager.is_initialized and
        (not settings.CACHE_ENABLED or cache_manager.is_available())
    )
    
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not ready",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            }
        )
    
    return {
        "status": "ready",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }

@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """
    Liveness check endpoint.
    Checks if the application is still running.
    """
    return {
        "status": "alive",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }

# ==================== API ROUTES ====================

# Import and register API routers
try:
    # Auth routes
    from app.modules.auth.api import router as auth_router
    app.include_router(
        auth_router,
        prefix=f"{settings.API_V1_PREFIX}/auth",
        tags=["Authentication"],
    )
    logger.info("✅ Auth routes registered")
    
except ImportError as e:
    logger.warning(f"⚠️ Auth routes not registered: {str(e)}")
except Exception as e:
    logger.error(f"❌ Failed to register auth routes: {str(e)}")

# Add more modules as they are created
# from app.modules.users.api import router as users_router
# app.include_router(users_router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])

# from app.modules.orders.api import router as orders_router
# app.include_router(orders_router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["Orders"])

# from app.modules.inventory.api import router as inventory_router
# app.include_router(inventory_router, prefix=f"{settings.API_V1_PREFIX}/inventory", tags=["Inventory"])

# ==================== DEBUG INFORMATION ====================

if settings.APP_ENVIRONMENT.value == "development":
    @app.get("/debug/routes", tags=["Debug"])
    async def debug_routes():
        """List all registered routes (development only)"""
        routes = []
        for route in app.routes:
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if hasattr(route, "methods") else [],
                "name": route.name,
            })
        return {"routes": routes}
    
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Show configuration (development only, sensitive info redacted)"""
        config = {
            "APP_NAME": settings.APP_NAME,
            "APP_VERSION": settings.APP_VERSION,
            "APP_ENVIRONMENT": settings.APP_ENVIRONMENT.value,
            "DEBUG": settings.DEBUG,
            "DB_HOST": settings.DB_HOST,
            "DB_NAME": settings.DB_NAME,
            "REDIS_HOST": settings.REDIS_HOST,
            "CACHE_ENABLED": settings.CACHE_ENABLED,
            "FEATURE_BACKGROUND_TASKS": settings.FEATURE_BACKGROUND_TASKS,
        }
        return {"config": config}
    
    @app.get("/debug/database", tags=["Debug"])
    async def debug_database():
        """Show database status (development only)"""
        return {
            "initialized": db_manager.is_initialized,
            "db_name": settings.DB_NAME,
            "db_host": settings.DB_HOST,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
        }

# ==================== APPLICATION STARTUP LOGGING ====================

# Log all registered routes
if settings.APP_ENVIRONMENT.value == "development":
    logger.debug("Registered routes:")
    for route in app.routes:
        if hasattr(route, "methods"):
            logger.debug(f"  {route.path} -> {list(route.methods)}")

# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    # Setup logging first
    setup_logging()
    
    # Run application
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True if settings.DEBUG else False,
        timeout_keep_alive=settings.TIMEOUT_KEEP_ALIVE,
        backlog=settings.BACKLOG,
        limit_max_requests=settings.MAX_REQUESTS,
        limit_max_requests_jitter=settings.MAX_REQUESTS_JITTER,
    )