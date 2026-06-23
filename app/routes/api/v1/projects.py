from uuid import UUID
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from typing_extensions import List
from decimal import Decimal

from database.session import SessionDep
from schemas.base_response import BaseResponse, ErrorResponse

from schemas.projects import (
    ProjectCreate, 
    ProjectUpdateStatus, 
    ProjectResponse, 
    ProjectUpdate, 
    ProjectLaborCreate, 
    ProjectLaborResponse
)
from repositories.projects import ProjectRepository
from services.projects import ProjectService


project_router = APIRouter(
    tags=["Projects"],
    prefix="/api/projects"
)

@project_router.post("/", response_model=BaseResponse)
async def create_project(request: ProjectCreate, db: SessionDep):
    service = ProjectService()
    project = await service.create(db, request.model_dump())
    await db.commit()
    await db.refresh(project)
    return BaseResponse(data={"id": str(project.id)})

@project_router.get("/", response_model=BaseResponse[List[ProjectResponse]])
async def list_projects(db: SessionDep):
    repo = ProjectRepository()
    projects = await repo.list(db)
    return BaseResponse(data=[ProjectResponse.model_validate(p) for p in projects])

@project_router.get("/kanban", response_model=BaseResponse[dict])
async def kanban(db: SessionDep):
    service = ProjectService()
    data = await service.kanban(db)
    return BaseResponse(data=data)

@project_router.get("/revenue")
async def revenue(db: SessionDep):
    service = ProjectService()
    total = await service.revenue_summary(db)  # returns a Decimal
    return BaseResponse(data={"total_estimated_revenue": total})

"""@project_router.get("/{project_id}", response_model=BaseResponse[ProjectResponse])
async def get_project(project_id: UUID, db: SessionDep):
    service = ProjectService()
    project = await service.repo.get(db, str(project_id))
    if not project: 
        raise HTTPException(status_code=404, detail="project not found")
    
    financials = await service.get_project_financials(db, str(project_id))
    response_data = {
        **ProjectResponse.model_validate(project).model_dump(),
        "financial_summary": financials
    }
    
    return BaseResponse(data=response_data)"""

@project_router.patch("/{project_id}", response_model=BaseResponse)
async def update_project(project_id: UUID, request: ProjectUpdate, db: SessionDep):
    repo = ProjectRepository()
    project = await repo.get(db, str(project_id))
    if not project:
        raise HTTPException(404, "Project not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(project, key):
            setattr(project, key, value)
    
    await db.commit()
    await db.refresh(project)
    return BaseResponse(data={"id": str(project.id)})


@project_router.patch("/{project_id}/progress")
async def update_progress(project_id: UUID, db: SessionDep, request: dict = Body(...)):
    progress = request.get("progress")
    if progress is None:
        raise HTTPException(400, "Missing 'progress' field")
    if not isinstance(progress, int) or progress < 0 or progress > 100:
        raise HTTPException(400, "Progress must be integer between 0 and 100")
    repo = ProjectRepository()
    project = await repo.get(db, str(project_id))
    if not project:
        raise HTTPException(404, "Project not found")
    project.progress = progress
    await db.commit()
    await db.refresh(project)
    return BaseResponse(data={"id": str(project.id), "progress": progress})

@project_router.patch("/{project_id}/notes")
async def update_notes(project_id: UUID, db: SessionDep, request: dict = Body(...)):
    notes = request.get("notes")
    if notes is None:
        raise HTTPException(400, "Missing 'notes' field")
    repo = ProjectRepository()
    project = await repo.get(db, str(project_id))
    if not project:
        raise HTTPException(404, "Project not found")
    project.notes = notes   # assuming you have a notes column in Project model
    await db.commit()
    await db.refresh(project)
    return BaseResponse(data={"id": str(project.id)})


@project_router.patch("/{project_id}/status", response_model=BaseResponse)
async def update_status(project_id: UUID, request: ProjectUpdateStatus, db: SessionDep):
    repo = ProjectRepository()
    project = await repo.update_status(db, str(project_id), request.status)
    if not project:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return BaseResponse(data={"id": str(project_id), "status": request.status})

@project_router.delete("/{project_id}", response_model=BaseResponse)
async def delete_project(project_id: UUID, db: SessionDep):
    repo = ProjectRepository()
    deleted = await repo.delete(db, str(project_id))
    if not deleted:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return BaseResponse(data={"id": str(project_id)})


@project_router.post("/from-inquiry/{inquiry_id}", response_class=JSONResponse)
async def create_project_from_inquiry(inquiry_id: UUID, db: SessionDep):
    from repositories.customer_inquiry import InquiryRepo
    from services.projects import ProjectService
    from schemas.projects import ProjectCreate

    # Fetch inquiry
    inquiry_repo = InquiryRepo(db)
    inquiry = await inquiry_repo.get_with_details(inquiry_id)
    if not inquiry:
        return JSONResponse(status_code=404, content={"detail": "Inquiry not found"})

    # Create project payload
    project_data = ProjectCreate(
        inquiry_id=inquiry.id,
        name=f"{inquiry.vehicle_brand} {inquiry.vehicle_model} - {inquiry.customer_name}",
        customer_name=inquiry.customer_name,
        vehicle_brand=inquiry.vehicle_brand,
        vehicle_model=inquiry.vehicle_model,
        estimated_cost=0,   # you can set from inquiry if you have quoted amount
        estimated_revenue=0
    )

    # Create project
    project_service = ProjectService()
    project = await project_service.create(db, project_data.model_dump())

    # Update inquiry status
    inquiry.status = "converted"
    await db.flush()
    await db.commit()

    return BaseResponse(data={"project_id": str(project.id), "inquiry_id": str(inquiry_id)})


@project_router.post("/{project_id}/labor", response_model=BaseResponse)
async def add_labor_to_project(
    project_id: UUID,
    payload: ProjectLaborCreate,
    db: SessionDep
):
    service = ProjectService()
    try:
        # Konversi hours ke Decimal
        hours_decimal = Decimal(str(payload.hours))
        
        labor = await service.add_labor(
            db,
            str(project_id),
            payload.labor_type,
            hours_decimal,
            payload.rate_per_hour  # ini bisa None atau Decimal
        )
        await db.commit()
        return BaseResponse(data={"id": str(labor.id)})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@project_router.get("/{project_id}/labor", response_model=BaseResponse)
async def get_project_labor(project_id: UUID, db: SessionDep):
    service = ProjectService()
    labor_list = await service.get_labor_list(db, str(project_id))
    return BaseResponse(data=[ProjectLaborResponse.model_validate(l) for l in labor_list])


@project_router.delete("/{project_id}/labor/{labor_id}", response_model=BaseResponse)
async def delete_labor(project_id: UUID, labor_id: UUID, db: SessionDep):
    service = ProjectService()
    deleted = await service.delete_labor(db, str(labor_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Labor entry not found")
    await db.commit()
    return BaseResponse(data={"id": str(labor_id)})


# Perbaiki GET /{project_id} agar mengembalikan data lengkap dengan financials
@project_router.get("/{project_id}", response_model=BaseResponse)
async def get_project(project_id: UUID, db: SessionDep):
    service = ProjectService()
    data = await service.get_project_financials(db, str(project_id))
    if not data:
        raise HTTPException(status_code=404, detail="Project not found")

    return BaseResponse(data={
        "project": ProjectResponse.model_validate(data["project"]),
        "financial_summary": {
            "material_cost": str(data["material_cost"]),
            "labor_cost": str(data["labor_cost"]),
            "actual_cost": str(data["actual_cost"]),
            "profit": str(data["profit"]),
            "margin": str(data["margin"])
        },
        "material_usages": data["material_usages"],   # ✅ sudah ada
        "labor_items": data["labor_items"]            # ✅ sudah ada
    })
    
@project_router.post("/{project_id}/complete", response_model=BaseResponse)
async def complete_project(project_id: UUID, db: SessionDep):
    service = ProjectService()
    project = await service.complete_project(db, str(project_id))
    if not project:
        raise HTTPException(404, "Project not found")

    # Jika project memiliki inquiry, update status inquiry menjadi 'completed'
    if project.inquiry_id:
        from repositories.customer_inquiry import InquiryRepo
        inquiry_repo = InquiryRepo(db)
        inquiry = await inquiry_repo.get(project.inquiry_id)
        if inquiry:
            inquiry.status = "completed"  # atau "done"
            await inquiry_repo.add_activity(project.inquiry_id, "Project completed")
            await db.flush()

    await db.commit()
    return BaseResponse(data={"id": str(project.id), "status": "completed"})