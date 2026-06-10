from fastapi import APIRouter, status, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response

dashboard = APIRouter(tags=["Dashboard"], prefix="/management", include_in_schema=False)
template = Jinja2Templates("templates/dashboard")

@dashboard.get("/", response_class=HTMLResponse)
async def get_base(request: Request):
    return template.TemplateResponse(
        name="dashboard.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/analytics", response_class=HTMLResponse)
async def get_analytics(request: Request):
    return template.TemplateResponse(
        name="analytics.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )

    
@dashboard.get("/projects", response_class=HTMLResponse)
async def get_projects(request: Request):
    return template.TemplateResponse(
        name="projects.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/inquiries", response_class=HTMLResponse)
async def get_inquiries(request: Request):
    return template.TemplateResponse(
        name="inquiries.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/inventories", response_class=HTMLResponse)
async def get_invetories(request: Request):
    return template.TemplateResponse(
        name="inventories.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/budgeting", response_class=HTMLResponse)
async def get_budgeting(request: Request):
    return template.TemplateResponse(
        name="budgeting.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request):
    return template.TemplateResponse(
        name="settings.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/customers", response_class=HTMLResponse)
async def get_customers(request: Request):
    return template.TemplateResponse(
        name="customers.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/reports", response_class=HTMLResponse)
async def get_reports(request: Request):
    return template.TemplateResponse(
        name="reports.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/calendars", response_class=HTMLResponse)
async def get_calendar(request: Request):
    return template.TemplateResponse(
        name="calendars.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/documents", response_class=HTMLResponse)
async def get_documents(request: Request):
    return template.TemplateResponse(
        name="documents.html",
        context={},
        request=request,
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/quotations", response_class=HTMLResponse)
async def get_quotations(request: Request):
    return template.TemplateResponse(
        name="quotations.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )
    
@dashboard.get("/invoices", response_class=HTMLResponse)
async def get_invoices(request: Request):
    return template.TemplateResponse(
        name="invoice_management.html",
        request=request,
        context={},
        status_code=status.HTTP_200_OK
    )