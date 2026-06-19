import uvicorn, asyncio, json, uuid

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from contextlib import asynccontextmanager

# Configuration
from dependencies.server_config import settings

from database.session import session_manager

# Routes Import
from routes.pages.pages import pages
from routes.pages.dashboard import dashboard
from routes.api.v1.customer_inquiry import customer_inquiry
from routes.api.v1.inventories import inventory_router
from routes.api.v1.projects import project_router
from routes.api.v1.price_list import price_list
from routes.api.v1.analytics import analytics
from routes.api.v1.budgeting import budgeting


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_manager.init(
        db_url=settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW
    )
    yield
    await session_manager.close()

# initialize server config first
app = FastAPI(
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    title=settings.API_NAME,
    lifespan=lifespan
)
app.mount("/static", StaticFiles(directory="templates/static/includes"), name="static")
templates = Jinja2Templates(directory="templates/static")

app.include_router(pages)

# dashboard
app.include_router(dashboard)

app.include_router(customer_inquiry)

app.include_router(inventory_router)

app.include_router(project_router)

app.include_router(price_list)

app.include_router(analytics)

app.include_router(budgeting)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOSTNAME,
        port=80,
        reload=settings.API_ENABLE_DOCS
    )