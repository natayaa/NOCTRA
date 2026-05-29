import uvicorn, asyncio, json, uuid

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="templates/includes"), name="static")
templates = Jinja2Templates(directory="templates/")


# Indonesia
@app.get("/")
@app.get("/id")
async def indonesia():
    return FileResponse(
        "templates/static/pages/id/index_id.html"
    )


# English
@app.get("/en")
async def english():
    return FileResponse(
        "templates/static/pages/en/index.html"
    )

# dashboard
@app.get("/dashboard")
async def dashboard():
    return FileResponse("templates/static/pages/dashboard/ui.html")

@app.get("/budgeting")
async def budgeting():
    return FileResponse("templates/static/pages/dashboard/budgeting.html")

@app.get("/inquiry")
async def inquiry():
    return FileResponse("templates/static/pages/inquiry.html")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )