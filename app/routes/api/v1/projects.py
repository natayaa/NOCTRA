from uuid import UUID
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from database.session import SessionDep
from schemas.base_response import BaseResponse, ErrorResponse

from schemas.projects import ProjectCreate, ProjectUpdateStatus, ProjectResponse

from repositories.projects import ProjectRepository
from services.projects import ProjectService


project_router = APIRouter(
    tags=["Projects"],
    prefix="/api/projects"
)

@project_router.post("/", response_class=JSONResponse)
async def create_project(request: ProjectCreate, db: SessionDep):
    service = ProjectService()

    project = await service.create(db, request.model_dump())

    await db.commit()
    await db.refresh(project)

    return BaseResponse(data={"id": str(project.id)})

@project_router.get("/")
async def list_projects(db: SessionDep):
    repo = ProjectRepository()

    data = await repo.list(db)

    return BaseResponse(
        data=[
            ProjectResponse.model_validate(p)
            for p in data
        ]
    )

@project_router.get("/kanban")
async def kanban(db: SessionDep):
    service = ProjectService()
    data = await service.kanban(db)

    return BaseResponse(data=data)

@project_router.patch("/{project_id}/status")
async def update_status(project_id: UUID, request: ProjectUpdateStatus, db: SessionDep):
    repo = ProjectRepository()

    await repo.update_status(db, str(project_id), request.status)

    await db.commit()

    return BaseResponse(data={"id": str(project_id), "status": request.status})

@project_router.delete("/{project_id}")
async def delete_project(project_id: UUID, db: SessionDep):
    repo = ProjectRepository()

    await repo.delete(db, str(project_id))

    await db.commit()

    return BaseResponse(data={"id": str(project_id)})

@project_router.get("/revenue")
async def revenue(db: SessionDep):
    service = ProjectService()

    data = await service.revenue_summary(db)

    return BaseResponse(data=data)