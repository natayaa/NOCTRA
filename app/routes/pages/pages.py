from fastapi import APIRouter, status, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response


pages = APIRouter(tags=["HTML Pages"])
templates = Jinja2Templates("templates/")

@pages.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    konteks = {
        "request": request, "title": "",
    }
    return templates.TemplateResponse("ui.html", context=konteks, status_code=status.HTTP_200_OK)

@pages.get("/inquiry", response_class=HTMLResponse)
async def inquiry_page(request: Request):
    context = {
        "request": request
    }
    return templates.TemplateResponse("inquiry.html", context=context, status_code=status.HTTP_200_OK)