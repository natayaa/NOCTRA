from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from modules.auth.models import User
from web.templates_env import templates

router = APIRouter(prefix="/admin", tags=["admin-web"])


@router.get("", response_class=RedirectResponse)
async def admin_root() -> RedirectResponse:
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "admin/login.html", {"title": "Sign In"})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    # Placeholder until Phase 2+; will pull real KPIs
    stats = {
        "active_projects": 0,
        "pending_inquiries": 0,
        "revenue_month": 0,
        "hpp_month": 0,
        "gross_margin_pct": 0.0,
    }
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"title": "Dashboard", "stats": stats},
    )