import uvicorn, asyncio, json, uuid

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routes.pages.pages import pages
from routes.pages.dashboard import dashboard

app = FastAPI()

app.mount("/static", StaticFiles(directory="templates/static/includes"), name="static")
templates = Jinja2Templates(directory="templates/static")

app.include_router(pages)

# dashboard
app.include_router(dashboard)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )