from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.web.templates_env import templates

router = APIRouter(tags=["public"])


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "public/landing.html",
        {"title": "NOCTRA Autoworks — Precision Motorcycle Refinishing"},
    )


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "public/about.html", {"title": "About — NOCTRA"})


@router.get("/services", response_class=HTMLResponse)
async def services(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "public/services.html", {"title": "Services — NOCTRA"}
    )


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "public/contact.html", {"title": "Contact — NOCTRA"}
    )