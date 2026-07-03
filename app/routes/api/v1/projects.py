# routers/projects.py
from uuid import UUID
from fastapi import APIRouter, HTTPException, Body, Query, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from database.session import SessionDep
from schemas.base_response import BaseResponse, ErrorResponse

from schemas.projects import (
    ProjectCreate, 
    ProjectUpdateStatus, 
    ProjectResponse, 
    ProjectUpdate, 
    ProjectLaborCreate, 
    ProjectLaborResponse,
    ProjectTaskCreate,
    ProjectTaskUpdate,
    ProjectTaskResponse,
    ProjectDetailResponse,
    ProjectKanbanResponse,
    ProjectUpdateProgress
)
from services.projects import ProjectService


project_router = APIRouter(
    tags=["Projects"],
    prefix="/api/projects"
)


# =============================================================================
# CRUD Operations
# =============================================================================

@project_router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    db: SessionDep
):
    service = ProjectService(db)
    project = await service.create(request)
    await db.commit()
    await db.refresh(project)
    return BaseResponse(data={"id": str(project.id)})


@project_router.get("/", response_model=BaseResponse)
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    brand: Optional[str] = Query(None, description="Filter by vehicle brand"),
    search: Optional[str] = Query(None, description="Search by name, customer, vehicle"),
    is_archived: bool = Query(False, description="Show archived projects"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: SessionDep = None
):
    service = ProjectService(db)
    projects, total = await service.list_all(
        status=status,
        priority=priority,
        brand=brand,
        search=search,
        is_archived=is_archived,
        limit=limit,
        offset=offset
    )
    return BaseResponse(data={
        "items": [ProjectResponse.model_validate(p).model_dump() for p in projects],
        "total": total,
        "limit": limit,
        "offset": offset
    })


@project_router.get("/kanban", response_model=BaseResponse)
async def kanban(
    db: SessionDep = None
):
    service = ProjectService(db)
    data = await service.kanban()
    return BaseResponse(data=data)


@project_router.get("/statistics", response_model=BaseResponse)
async def get_statistics(
    db: SessionDep = None
):
    service = ProjectService(db)
    data = await service.get_statistics()
    return BaseResponse(data=data)


# routers/projects.py
@project_router.get("/{project_id}", response_model=BaseResponse)
async def get_project(
    project_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    project = await service.get(project_id)  # <-- PASTIKAN ADA await
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    financials = await service.get_project_financials(project_id)  # <-- PASTIKAN ADA await
    
    # Serialize dengan aman - semua data sudah di-load secara eager
    response_data = {
        "project": ProjectResponse.model_validate(project).model_dump(),
        "financial_summary": {
            "estimated_cost": float(financials["estimated_cost"]) if financials else 0,
            "actual_cost": float(financials["actual_cost"]) if financials else 0,
            "estimated_revenue": float(financials["estimated_revenue"]) if financials else 0,
            "actual_revenue": float(financials["actual_revenue"]) if financials else 0,
            "material_cost": float(financials["material_cost"]) if financials else 0,
            "labor_cost": float(financials["labor_cost"]) if financials else 0,
            "expenses": float(financials["expenses"]) if financials else 0,
            "profit": float(financials["profit"]) if financials else 0,
            "margin": float(financials["margin"]) if financials else 0,
        },
        "material_usages": financials.get("material_usages", []) if financials else [],
        "labor_items": financials.get("labor_items", []) if financials else [],
        "tasks": [ProjectTaskResponse.model_validate(t).model_dump() for t in project.tasks] if project.tasks else [],
        "activities": [
            {"id": str(a.id), "activity": a.activity, "activity_type": a.activity_type, 
             "performed_by": a.performed_by, "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in project.activities
        ] if project.activities else []
    }
    
    return BaseResponse(data=response_data)

@project_router.patch("/{project_id}", response_model=BaseResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    db: SessionDep
):
    service = ProjectService(db)
    project = await service.update(project_id, request)
    if not project:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return BaseResponse(data={"id": str(project.id)})


@project_router.patch("/{project_id}/progress", response_model=BaseResponse)
async def update_progress(
    project_id: UUID,
    request: ProjectUpdateProgress,
    db: SessionDep
):
    service = ProjectService(db)
    project = await service.update_progress(project_id, request.progress)
    if not project:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return BaseResponse(data={"id": str(project.id), "progress": request.progress})


@project_router.patch("/{project_id}/status", response_model=BaseResponse)
async def update_status(
    project_id: UUID,
    request: ProjectUpdateStatus,
    db: SessionDep
):
    service = ProjectService(db)
    project = await service.update_status(project_id, request.status, request.note)
    if not project:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return BaseResponse(data={"id": str(project_id), "status": request.status})


@project_router.post("/{project_id}/complete", response_model=BaseResponse)
async def complete_project(
    project_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    project = await service.complete_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return BaseResponse(data={"id": str(project.id), "status": "completed"})


@project_router.post("/{project_id}/archive", response_model=BaseResponse)
async def archive_project(
    project_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    result = await service.archive(project_id)
    if not result:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return BaseResponse(data={"id": str(project_id), "archived": True})


@project_router.delete("/{project_id}", response_model=BaseResponse)
async def delete_project(
    project_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    deleted = await service.delete(project_id)
    if not deleted:
        raise HTTPException(404, "Project not found")
    await db.commit()
    return BaseResponse(data={"id": str(project_id)})


# =============================================================================
# Project Tasks
# =============================================================================

@project_router.post("/{project_id}/tasks", response_model=BaseResponse)
async def add_task(
    project_id: UUID,
    request: ProjectTaskCreate,
    db: SessionDep
):
    service = ProjectService(db)
    task = await service.add_task(project_id, request.model_dump())
    await db.commit()
    return BaseResponse(data={"id": str(task.id)})


@project_router.get("/{project_id}/tasks", response_model=BaseResponse)
async def get_tasks(
    project_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    tasks = await service.get_tasks(project_id)
    return BaseResponse(data=[ProjectTaskResponse.model_validate(t).model_dump() for t in tasks])


@project_router.patch("/tasks/{task_id}", response_model=BaseResponse)
async def update_task(
    task_id: UUID,
    request: ProjectTaskUpdate,
    db: SessionDep
):
    service = ProjectService(db)
    task = await service.update_task(task_id, request.model_dump(exclude_unset=True))
    if not task:
        raise HTTPException(404, "Task not found")
    await db.commit()
    return BaseResponse(data={"id": str(task.id)})


@project_router.delete("/tasks/{task_id}", response_model=BaseResponse)
async def delete_task(
    task_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    deleted = await service.delete_task(task_id)
    if not deleted:
        raise HTTPException(404, "Task not found")
    await db.commit()
    return BaseResponse(data={"id": str(task_id)})


# =============================================================================
# Project Labor
# =============================================================================

@project_router.post("/{project_id}/labor", response_model=BaseResponse)
async def add_labor_to_project(
    project_id: UUID,
    payload: ProjectLaborCreate,
    db: SessionDep
):
    service = ProjectService(db)
    try:
        labor = await service.add_labor(
            project_id,
            payload.labor_type,
            Decimal(str(payload.hours)),
            payload.rate_per_hour,
            payload.technician_name,
            payload.description
        )
        await db.commit()
        return BaseResponse(data={"id": str(labor.id)})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@project_router.get("/{project_id}/labor", response_model=BaseResponse)
async def get_project_labor(
    project_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    labor_list = await service.get_labor_items(project_id)
    return BaseResponse(data=[ProjectLaborResponse.model_validate(l).model_dump() for l in labor_list])


@project_router.delete("/labor/{labor_id}", response_model=BaseResponse)
async def delete_labor(
    labor_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    deleted = await service.delete_labor(labor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Labor entry not found")
    await db.commit()
    return BaseResponse(data={"id": str(labor_id)})


# =============================================================================
# Project Activities
# =============================================================================

@project_router.get("/{project_id}/activities", response_model=BaseResponse)
async def get_project_activities(
    project_id: UUID,
    db: SessionDep
):
    service = ProjectService(db)
    activities = await service.get_activities(project_id)
    return BaseResponse(data=[
        {
            "id": str(a.id),
            "activity": a.activity,
            "activity_type": a.activity_type,
            "performed_by": a.performed_by,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in activities
    ])


# =============================================================================
# Project Stages
# =============================================================================

@project_router.get("/stages", response_model=BaseResponse)
async def get_stages(
    db: SessionDep
):
    service = ProjectService(db)
    stages = await service.get_stages()
    return BaseResponse(data=stages)


# =============================================================================
# Convert from Inquiry
# =============================================================================

@project_router.post("/from-inquiry/{inquiry_id}", response_model=BaseResponse)
async def create_project_from_inquiry(
    inquiry_id: UUID,
    db: SessionDep
):
    from repositories.customer_inquiry import InquiryRepo

    # Fetch inquiry
    inquiry_repo = InquiryRepo(db)
    inquiry = await inquiry_repo.get_with_details(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    # Create project payload
    project_data = ProjectCreate(
        inquiry_id=inquiry.id,
        name=f"{inquiry.vehicle_brand} {inquiry.vehicle_model} - {inquiry.customer_name}",
        customer_name=inquiry.customer_name,
        customer_phone=inquiry.customer_phone_number,
        customer_email=inquiry.customer_email,
        vehicle_brand=inquiry.vehicle_brand,
        vehicle_model=inquiry.vehicle_model,
        vehicle_year=inquiry.vehicle_year,
        vehicle_license_plate=inquiry.vehicle_license_plate,
        estimated_cost=Decimal(inquiry.estimated_budget or 0),
        estimated_revenue=Decimal(0),
        project_start_date=datetime.now(),
        project_target_delivery=datetime.now() + timedelta(days=30),
        notes=f"Converted from inquiry {inquiry_id}"
    )

    # Create project
    project_service = ProjectService(db)
    project = await project_service.create(project_data)

    # Update inquiry status
    inquiry.status = "converted"
    inquiry.converted_at = datetime.now()
    await inquiry_repo.add_activity(inquiry_id, f"Converted to project: {project.name}", "conversion", performed_by="system")
    await db.commit()

    return BaseResponse(data={"project_id": str(project.id), "inquiry_id": str(inquiry_id)})