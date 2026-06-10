import uvicorn, asyncio, json, uuid

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Configuration
from dependencies.server_config import settings

# Routes Import
from routes.pages.pages import pages
from routes.pages.dashboard import dashboard
from routes.api.v1.customer_inquiry import customer_inquiry

# initialize server config first
app = FastAPI(
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    title=settings.API_NAME
)
app.mount("/static", StaticFiles(directory="templates/static/includes"), name="static")
templates = Jinja2Templates(directory="templates/static")

app.include_router(pages)

# dashboard
app.include_router(dashboard)

app.include_router(customer_inquiry)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOSTNAME,
        port=80,
        reload=settings.API_ENABLE_DOCS
    )