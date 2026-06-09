from fastapi import APIRouter, status, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response


pages = APIRouter(tags=["HTML Pages"])
templates = Jinja2Templates("templates/")

@pages.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    konteks = {
        "request": request, "page_title": "NOKTRA AUTOWORKS",
        "page_content": "Premium motorcycle restoration, repaint and custom build workshop"
    }
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=konteks,
        status_code=status.HTTP_200_OK
    )

@pages.get("/inquiry", response_class=HTMLResponse)
async def inquiry_page(request: Request):
    context = {
        "request": request
    }
    return templates.TemplateResponse(
        request=request,
        name="inquiry.html", 
        context=context, 
        status_code=status.HTTP_200_OK
    )