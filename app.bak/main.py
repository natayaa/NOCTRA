import uvicorn

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.csrf import CSRFMiddleware
from core.error_handlers import register_error_handlers
from core.health import router as health_router
from core.jobs import queue
from core.logging import configure_logging, log
from core.rate_limit import RateLimitMiddleware
from core.request_id import RequestIdMiddleware
from core.template_context import TemplateContextMiddleware

from modules.audit.api import router as audit_router
from modules.auth.api import router as auth_router
from modules.settings.api import router as settings_router
from modules.users.api import router as users_router
from modules.customers.api import router as customers_router
from modules.vehicles.api import (
    customer_vehicles_router,
    vehicles_router,
)

from web.admin import routes as admin_routes
from web.public import routes as public_routes
from web.admin import customers as admin_customers
from web.admin import vehicles as admin_vehicles


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("app_starting", name=settings.APP_NAME, env=settings.APP_ENV)
    await queue.start()
    yield
    await queue.stop()
    log.info("app_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        debug=settings.APP_DEBUG,
        lifespan=lifespan,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
    )

    # ── Middleware (order matters: outermost first) ────
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(TemplateContextMiddleware)  # ← new
    if settings.TRUSTED_HOSTS:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # ── Errors ─────────────────────────────────────────
    register_error_handlers(app)

    # ── Static ─────────────────────────────────────────
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # ── Health ─────────────────────────────────────────
    app.include_router(health_router)

    # ── API v1 ─────────────────────────────────────────
    API = "/api/v1"
    app.include_router(auth_router, prefix=API)
    app.include_router(users_router, prefix=API)
    app.include_router(audit_router, prefix=API)
    app.include_router(settings_router, prefix=API)
    app.include_router(customers_router, prefix=API)          # ← new
    app.include_router(customer_vehicles_router, prefix=API)  # ← new
    app.include_router(vehicles_router, prefix=API)           # ← new

    # ── Web ────────────────────────────────────────────
    app.include_router(public_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(admin_customers.router)   # ← new
    app.include_router(admin_vehicles.router)    # ← new

    return app


app = create_app()


if __name__ == "__main__": 
    uvicorn.run("main:app", reload=True)