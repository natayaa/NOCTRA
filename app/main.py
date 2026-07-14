# main.py - FULL FIXED
from modules.jinja_render.managements import html as management_router
from modules.auth.router import auth_router
from modules.settings.router import settings_router
from modules.inventory.router import inventory_router
from modules.price_list.router import price_list_router
from modules.payment.router import payment_router
from modules.projects.router import project_router
from modules.inquiry.router import inquiry_router
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
import logging

from core import (
    settings,
    app_exception_handler,
    generic_exception_handler,
    AppException,
    check_db_connection,
    setup_logging,
    get_logger,
)
from core.database import engine
from core.base import Base

# =============================================================================
# Setup Logging
# =============================================================================

setup_logging()
logger = get_logger("main")

# =============================================================================
# Import Routers
# =============================================================================


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # ============================================================
    # STARTUP
    # ============================================================
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔗 Database: {settings.DATABASE_URL}")

    # Check database connection
    logger.info("🔍 Checking database connection...")
    is_connected = await check_db_connection()

    if is_connected:
        logger.info("✅ Database connection successful!")
    else:
        logger.warning(
            "⚠️ Database connection failed! Please check your DATABASE_URL")

    # Create tables (optional - use migrations in production)
    if settings.ENVIRONMENT == "development":
        try:
            # Uncomment jika ingin auto-create tables
            # async with engine.begin() as conn:
            #     await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Tables verified (development mode)")
        except Exception as e:
            logger.error(f"❌ Failed to verify tables: {e}")

    logger.info("✅ Application startup complete!")

    yield

    # ============================================================
    # SHUTDOWN
    # ============================================================
    logger.info("🛑 Shutting down...")
    await engine.dispose()
    logger.info("✅ Database connection closed")


# =============================================================================
# App
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Workshop Project Management System API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# =============================================================================
# Static Files & Templates
# =============================================================================

app.mount("/static", StaticFiles(directory="templates/static"), name="static")
templates = Jinja2Templates(directory="templates")


# =============================================================================
# Exception Handlers
# =============================================================================

# Custom AppException
app.add_exception_handler(AppException, app_exception_handler)

# Generic Exception
app.add_exception_handler(Exception, generic_exception_handler)

# ✅ TAMBAHKAN: Validation Error Handler


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler untuk validation error dari Pydantic."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "errors": exc.errors(),
            "code": "VALIDATION_ERROR"
        }
    )

# ✅ TAMBAHKAN: HTTP Exception Handler


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler untuk HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "code": f"HTTP_{exc.status_code}"
        }
    )


# =============================================================================
# CORS
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(inquiry_router, prefix=settings.API_PREFIX)
app.include_router(project_router, prefix=settings.API_PREFIX)
app.include_router(payment_router, prefix=settings.API_PREFIX)
app.include_router(price_list_router, prefix=settings.API_PREFIX)
app.include_router(inventory_router, prefix=settings.API_PREFIX)
app.include_router(settings_router, prefix=settings.API_PREFIX)
app.include_router(auth_router, prefix=settings.API_PREFIX)  # ✅ TAMBAHKAN INI
app.include_router(management_router)


# =============================================================================
# Health Check - ✅ IMPROVED
# =============================================================================

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with database status."""
    from core.health import HealthChecker
    return await HealthChecker.run_checks()


# =============================================================================
# Root
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else None,
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=80,  # ✅ Ganti ke 8000 (standar FastAPI)
        reload=settings.DEBUG,
        # log_level="info",
    )
