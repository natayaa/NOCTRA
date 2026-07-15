from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

html = APIRouter(
    prefix="/management", include_in_schema=False,
    tags=["Management"],
)
template = Jinja2Templates(directory="templates/dashboard/")


@html.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    context = {
        "request": request
    }
    return template.TemplateResponse(name="login.html", request=request, context=context, status_code=200)


@html.get("/", response_class=HTMLResponse)
def read_dashboard(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="dashboard.html", request=request, context=context, status_code=200)


@html.get("/projects", response_class=HTMLResponse)
def read_projects(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="projects.html", request=request, context=context, status_code=200)


@html.get("/inquiries", response_class=HTMLResponse)
def read_inquiries(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="inquiries.html", request=request, context=context, status_code=200)


@html.get("/budgeting", response_class=HTMLResponse)
def read_budgeting(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="budgeting.html", request=request, context=context, status_code=200)


@html.get("/analytics", response_class=HTMLResponse)
def read_analytics(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="analytics.html", request=request, context=context, status_code=200)


@html.get("/inventories", response_class=HTMLResponse)
def read_inventories(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="inventories.html", request=request, context=context, status_code=200)


@html.get("/settings", response_class=HTMLResponse)
def read_settings(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="settings.html", request=request, context=context, status_code=200)


@html.get("/price-list", response_class=HTMLResponse)
def read_price_list(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="price_list.html", request=request, context=context, status_code=200)


@html.get("/reports", response_class=HTMLResponse)
def read_reports(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="reports.html", request=request, context=context, status_code=200)


@html.get("/quotations", response_class=HTMLResponse)
def read_quotations(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="quotations.html", request=request, context=context, status_code=200)


@html.get("/invoices", response_class=HTMLResponse)
def read_invoices(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="invoice_management.html", request=request, context=context, status_code=200)


@html.get("/calendars", response_class=HTMLResponse)
def read_calendar(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="calendars.html", request=request, context=context, status_code=200)


@html.get("/customers", response_class=HTMLResponse)
def read_customers(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="customers.html", request=request, context=context, status_code=200)


@html.get("/documents", response_class=HTMLResponse)
def read_documents(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="documents.html", request=request, context=context, status_code=200)


@html.get("/payments", response_class=HTMLResponse)
def read_payments(request: Request):
    context = {
        "request": request
    }
    return template.TemplateResponse(name="payments.html", request=request, context=context, status_code=200)


@html.get("/billing-quotaitions", response_class=HTMLResponse)
async def read_billing_quotations(request: Request):
    context = {
        "request": request
    }

    return template.TemplateResponse(name="billing.html", request=request, context=context, status_code=200)


@html.get("/restored-bikes", response_class=HTMLResponse)
async def get_restored_bikes(request: Request):
    context = {
        "request": request
    }

    return template.TemplateResponse(name="restored-bikes.html", request=request, context=context, status_code=200)
