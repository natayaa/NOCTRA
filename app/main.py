import uvicorn

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.csrf import CSRFMiddleware
from app.core.database import DBSessionMiddleware
from app.core.csrf_token import CsrfTokenMiddleware
from app.core.error_handlers import register_error_handlers
from app.core.health import router as health_router
from app.core.jobs import queue
from app.core.logging import configure_logging, log
from app.core.rate_limit import RateLimitMiddleware
from app.core.request_id import RequestIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.template_context import TemplateContextMiddleware
from app.core.upload import MEDIA_ROOT
from app.web.templates_env import STATIC_DIR

from app.modules.audit.api import router as audit_router
from app.modules.auth.api import router as auth_router
from app.modules.settings.api import router as settings_router
from app.modules.users.api import router as users_router
from app.modules.customers.api import router as customers_router
from app.modules.vehicles.api import (
    customer_vehicles_router,
    vehicles_router,
)
from app.modules.inquiries.api import router as inquiries_router
from app.modules.inventory.api import (
    inventory_router,
    materials_router,
    purchase_orders_router,
    suppliers_router,
)
from app.modules.projects.api import (
    employees_router,
    projects_router,
)
from app.modules.pricing.api import router as pricing_router
from app.modules.finance.api import router as finance_router
from app.modules.analytics.api import router as analytics_router

from app.web.admin import routes as admin_routes
from app.web.public import routes as public_routes
from app.web.public import contact as public_contact
from app.web.admin import customers as admin_customers
from app.web.admin import vehicles as admin_vehicles
from app.web.admin import inquiries as admin_inquiries
from app.web.admin import inventory as admin_inventory
from app.web.admin import materials as admin_materials
from app.web.admin import purchase_orders as admin_purchase_orders
from app.web.admin import suppliers as admin_suppliers
from app.web.admin import email_logs as admin_email_logs
from app.web.admin import employees as admin_employees
from app.web.admin import projects as admin_projects
from app.web.admin import pricing_rules as admin_pricing_rules
from app.web.admin import pricing_analytics as admin_pricing_analytics
from app.web.admin import expenses as admin_expenses
from app.web.admin import finance_reports as admin_finance_reports
from app.web.admin import invoices as admin_invoices
from app.web.admin import payments as admin_payments
from app.web.admin import dashboard as admin_dashboard
from app.web.admin import audit as admin_audit
from app.web.admin import roles as admin_roles
from app.web.admin import settings as admin_settings
from app.web.admin import users as admin_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("app_starting", name=settings.APP_NAME, env=settings.APP_ENV)
    await queue.start()

    scheduler = None
    if settings.OVERDUE_SWEEP_ENABLED:
        from app.core.scheduler import DailyJob
        from app.modules.finance.dunning import run_overdue_sweep

        scheduler = DailyJob(
            run_overdue_sweep,
            name="overdue-sweep",
            hour_local=settings.OVERDUE_SWEEP_HOUR_LOCAL,
        )
        scheduler.start()

    yield

    if scheduler is not None:
        await scheduler.stop()
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

    # Absolute paths: a CWD-relative mount silently serves a different
    # directory when the app is started from anywhere but the repo root.
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")

    # ── Middleware ─────────────────────────────────────
    # Starlette middleware runs in REVERSE of add order.
    # Effective request flow (outermost → innermost):
    #   DBSession → TrustedHost → TemplateContext → RequestId → RateLimit
    #     → CsrfToken → CSRF → GZip → app
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(CsrfTokenMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(TemplateContextMiddleware)

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

    # DBSession is the outermost stateful layer: every inner layer
    # (including the exception handlers) has built the response before
    # commit() runs, and the app hosts exactly one session per request.
    app.add_middleware(DBSessionMiddleware)
    # Added last => truly outermost: even 404s, CSRF rejections, and
    # error-handler JSON get the security headers.
    app.add_middleware(SecurityHeadersMiddleware)

    # ── Errors ─────────────────────────────────────────
    register_error_handlers(app)

    # ── Static ─────────────────────────────────────────
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ── Health ─────────────────────────────────────────
    app.include_router(health_router)

    # ── API v1 ─────────────────────────────────────────
    API = "/api/v1"
    app.include_router(auth_router, prefix=API)
    app.include_router(users_router, prefix=API)
    app.include_router(audit_router, prefix=API)
    app.include_router(settings_router, prefix=API)
    app.include_router(customers_router, prefix=API)
    app.include_router(customer_vehicles_router, prefix=API)
    app.include_router(vehicles_router, prefix=API)
    app.include_router(inquiries_router, prefix=API)
    app.include_router(suppliers_router, prefix=API)
    app.include_router(materials_router, prefix=API)
    app.include_router(inventory_router, prefix=API)
    app.include_router(purchase_orders_router, prefix=API)
    app.include_router(projects_router, prefix=API)
    app.include_router(employees_router, prefix=API)
    app.include_router(pricing_router, prefix=API)
    app.include_router(finance_router, prefix=API)
    app.include_router(analytics_router, prefix=API)

    # ── Web ────────────────────────────────────────────
    app.include_router(public_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(admin_customers.router)
    app.include_router(admin_vehicles.router)
    app.include_router(admin_inquiries.router)
    app.include_router(admin_suppliers.router)
    app.include_router(admin_materials.router)
    app.include_router(admin_inventory.router)
    app.include_router(admin_purchase_orders.router)
    app.include_router(public_contact.router)
    app.include_router(admin_email_logs.router)
    app.include_router(admin_projects.router)
    app.include_router(admin_employees.router)
    app.include_router(admin_pricing_rules.router)
    app.include_router(admin_pricing_analytics.router)
    app.include_router(admin_invoices.router)
    app.include_router(admin_payments.router)
    app.include_router(admin_expenses.router)
    app.include_router(admin_finance_reports.router)
    app.include_router(admin_dashboard.router)
    app.include_router(admin_users.router)
    app.include_router(admin_roles.router)
    app.include_router(admin_audit.router)
    app.include_router(admin_settings.router)
        

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)