# modules/project/router.py
"""
Project Router - COMPLETE

✅ Semua endpoint untuk Project management
✅ CRUD operations
✅ Status & Progress management
✅ Tasks, Labor, Expenses, Price List Items
✅ Timeline, Documents, Team
✅ Financial Summary
✅ Dashboard (Statistics, Kanban, Stages)
"""

from uuid import UUID
from decimal import Decimal
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Body, Query, UploadFile, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.base import BaseResponse, PaginatedResponse
from core.dependencies import get_service, ProjectQueryParams, success_response
from core.exceptions import NotFoundError, ValidationError, BusinessError
from core.constants import InquiryStatus, ProjectStatus, ProjectPriority

from .schemas import (
    # Project
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectMinimalResponse, ProjectUpdateStatus,
    ProjectUpdateProgress, ProjectCancel,
    ProjectDetailResponse,
    # Tasks
    ProjectTaskCreate, ProjectTaskUpdate,
    ProjectTaskResponse,
    # Labor
    ProjectLaborCreate, ProjectLaborResponse,
    # Expense
    ProjectExpenseCreate, ProjectExpenseResponse,
    # Price List
    ProjectPriceListItemResponse,
    # Timeline
    ProjectTimelineCreate, ProjectTimelineUpdate, ProjectTimelineResponse,
    # Document
    ProjectDocumentCreate, ProjectDocumentUpdate,
    ProjectDocumentResponse,ProjectDocumentUpload,
    # Team
    ProjectTeamCreate,
    ProjectTeamResponse,
    # Stage
    ProjectStageCreate,
    ProjectStageUpdate,
    ProjectStageResponse,
    # Financial
    ProjectFinancialSummary,
    # Kanban
    ProjectKanbanItem,
    ProjectKanbanResponse,
    # Statistics
    ProjectStatisticsResponse,
    ProjectFinancialSummaryResponse,
)
from .services import ProjectService


project_router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"]
)


# =============================================================================
# ⚠️ URUTAN PENTING!
# Route STATIS (tanpa {parameter}) harus di ATAS route dengan path parameter
# =============================================================================


# =============================================================================
# 1. ROUTE STATIS (tanpa path parameter) - DULUAN
# =============================================================================

@project_router.get("/statistics", response_model=BaseResponse)
async def get_project_statistics(
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Get project statistics for dashboard.
    
    Returns:
    - Total projects
    - By status
    - By priority
    - Financial summary
    - Top 5 active projects
    """
    try:
        data = await service.get_statistics()
        return success_response(data, message="Statistics retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/financial-summary", response_model=BaseResponse)
async def get_financial_summary(
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Get financial summary for all projects.
    
    Returns:
    - Total projects
    - Estimated cost (total)
    - Actual cost (total)
    - Profit/Loss
    - Number of negative margin projects
    """
    try:
        data = await service.get_financial_summary_all()
        return success_response(data, message="Financial summary retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/kanban", response_model=BaseResponse)
async def get_kanban(
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Get Kanban board data.
    
    Returns projects grouped by status:
    - draft
    - active
    - in_progress
    - on_hold
    - completed
    - cancelled
    """
    try:
        data = await service.kanban()
        return success_response(data, message="Kanban data retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/stages", response_model=BaseResponse)
async def get_stages(
    active_only: bool = Query(True, description="Only active stages"),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all project stages."""
    try:
        stages = await service.get_stages(active_only)
        return success_response(stages, message="Stages retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post("/stages", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_stage(
    request: ProjectStageCreate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Create a new project stage."""
    try:
        stage = await service.create_stage(request.model_dump())
        return success_response(
            {"id": str(stage.id)},
            message="Stage created successfully"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.patch("/stages/{stage_id}", response_model=BaseResponse)
async def update_stage(
    stage_id: UUID,
    request: ProjectStageUpdate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Update a project stage."""
    try:
        stage = await service.repo.update_stage(stage_id, request.model_dump(exclude_unset=True))
        if not stage:
            raise HTTPException(status_code=404, detail="Stage not found")
        await service.db.commit()
        return success_response(
            {"id": str(stage.id)},
            message="Stage updated successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/stages/{stage_id}", response_model=BaseResponse)
async def delete_stage(
    stage_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Delete a project stage."""
    try:
        result = await service.repo.delete_stage(stage_id)
        if not result:
            raise HTTPException(status_code=404, detail="Stage not found")
        await service.db.commit()
        return success_response(
            {"id": str(stage_id)},
            message="Stage deleted successfully"
        )
    except ValueError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 2. PROJECT CRUD ROUTES
# =============================================================================

@project_router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Create a new project.
    
    If inquiry_id is provided:
    - Auto-populate customer/vehicle data from inquiry
    - Update inquiry status to CONVERTED
    - Auto-create workshop job
    
    If price_list_item_ids provided:
    - Auto-calculate estimated_cost
    - Link price list items to project
    """
    try:
        project = await service.create(request)
        return success_response(
            {
                "id": str(project.id),
                "project_code": project.project_code,
                "inquiry_id": str(project.inquiry_id) if project.inquiry_id else None
            },
            message=f"Project created successfully: {project.project_code}"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/", response_model=PaginatedResponse[ProjectMinimalResponse])
async def list_projects(
    params: ProjectQueryParams = Depends(),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    List all projects with filters.
    
    Filters:
    - status: project status
    - priority: priority level
    - brand: vehicle brand
    - search: search by name, customer, vehicle, project_code
    - is_archived: include archived
    - stage_id: filter by stage
    - limit, offset: pagination
    """
    try:
        projects, total = await service.list_all(
            status=params.status,
            priority=params.priority,
            brand=params.brand,
            search=params.search,
            is_archived=params.is_archived,
            stage_id=params.stage_id,
            limit=params.limit,
            offset=params.offset
        )

        total_pages = (total + params.limit - 1) // params.limit if total > 0 else 0

        return PaginatedResponse(
            success=True,
            message="Projects retrieved successfully",
            data=[ProjectMinimalResponse.model_validate(p).model_dump() for p in projects],
            total=total,
            page=params.page,
            page_size=params.limit,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/inquiry/{inquiry_id}", response_model=BaseResponse)
async def get_project_by_inquiry(
    inquiry_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get project by inquiry ID."""
    try:
        project = await service.get_by_inquiry(inquiry_id)
        if not project:
            return success_response(
                None,
                message="No project found for this inquiry"
            )
        return success_response(
            ProjectResponse.model_validate(project).model_dump(),
            message="Project retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/code/{project_code}", response_model=BaseResponse)
async def get_project_by_code(
    project_code: str,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get project by project code."""
    try:
        project = await service.get_by_code(project_code)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            ProjectResponse.model_validate(project).model_dump(),
            message="Project retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/{project_id}", response_model=BaseResponse)
async def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Get project detail with all related data.
    
    Includes:
    - Project data
    - Financial summary
    - Tasks
    - Labor items
    - Expenses
    - Price list items
    - Activities
    """
    try:
        project = await service.get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get financial summary
        financials = await service.get_financial_summary(project_id)

        # Get sub-resources
        tasks = await service.get_tasks(project_id)
        labor_items = await service.get_labor_items(project_id)
        expenses = await service.get_expenses(project_id)
        price_list_items = await service.get_price_list_items(project_id)
        activities = await service.get_activities(project_id)

        response_data = {
            "project": ProjectResponse.model_validate(project).model_dump(),
            "financial_summary": financials.model_dump(),
            "tasks": [ProjectTaskResponse.model_validate(t).model_dump() for t in tasks],
            "labor_items": [ProjectLaborResponse.model_validate(l).model_dump() for l in labor_items],
            "expenses": [ProjectExpenseResponse.model_validate(e).model_dump() for e in expenses],
            "price_list_items": [ProjectPriceListItemResponse.model_validate(p).model_dump() for p in price_list_items],
            "activities": [
                {
                    "id": str(a.id),
                    "activity": a.activity,
                    "activity_type": a.activity_type,
                    "performed_by": a.performed_by,
                    "meta_data": a.meta_data,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in activities
            ]
        }

        return success_response(response_data, message="Project retrieved successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.patch("/{project_id}", response_model=BaseResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Update a project."""
    try:
        project = await service.update(project_id, request)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            {"id": str(project.id)},
            message="Project updated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/{project_id}", response_model=BaseResponse)
async def delete_project(
    project_id: UUID,
    permanent: bool = Query(False, description="Permanent delete (cannot be undone)"),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Delete a project (soft delete by default)."""
    try:
        if permanent:
            result = await service.repo.hard_delete(project_id)
            message = "Project permanently deleted"
        else:
            result = await service.delete(project_id)
            message = "Project deleted successfully"
        
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            {"id": str(project_id)},
            message=message
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post("/{project_id}/archive", response_model=BaseResponse)
async def archive_project(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Archive a project."""
    try:
        result = await service.archive(project_id)
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            {"id": str(project_id)},
            message="Project archived successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post("/{project_id}/unarchive", response_model=BaseResponse)
async def unarchive_project(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Unarchive a project."""
    try:
        result = await service.unarchive(project_id)
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            {"id": str(project_id)},
            message="Project unarchived successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 3. STATUS & PROGRESS
# =============================================================================

@project_router.patch("/{project_id}/status", response_model=BaseResponse)
async def update_project_status(
    project_id: UUID,
    request: ProjectUpdateStatus,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Update project status.
    
    Allowed transitions based on status flow.
    """
    try:
        project = await service.update_status(project_id, request.status, request.note)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            {"id": str(project.id), "status": project.status},
            message=f"Status updated to {project.status}"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.patch("/{project_id}/progress", response_model=BaseResponse)
async def update_project_progress(
    project_id: UUID,
    request: ProjectUpdateProgress,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Update project progress (0-100).
    
    Auto-updates status:
    - 100% → COMPLETED
    - > 0% from DRAFT → ACTIVE
    """
    try:
        project = await service.update_progress(project_id, request.progress)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            {"id": str(project.id), "progress": project.progress, "status": project.status},
            message=f"Progress updated to {request.progress}%"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post("/{project_id}/complete", response_model=BaseResponse)
async def complete_project(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Mark project as completed.
    
    ✅ Updates project status to COMPLETED
    ✅ Updates inquiry status to COMPLETED
    ✅ Does not handle payment/invoice (handled by Payment module)
    """
    try:
        project = await service.complete_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            {"id": str(project.id), "status": "completed", "completed_at": project.completed_at.isoformat()},
            message="Project completed successfully"
        )
    except BusinessError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post("/{project_id}/cancel", response_model=BaseResponse)
async def cancel_project(
    project_id: UUID,
    request: ProjectCancel,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Cancel a project with reason."""
    try:
        project = await service.cancel_project(project_id, request.reason)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return success_response(
            {"id": str(project.id), "status": "cancelled"},
            message="Project cancelled successfully"
        )
    except BusinessError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 4. FINANCIAL
# =============================================================================

@project_router.get("/{project_id}/financials", response_model=BaseResponse)
async def get_project_financials(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """
    Get detailed financial breakdown for a project.
    
    Includes:
    - estimated_cost, actual_cost
    - material_cost (from inventory)
    - labor_cost (from project labor)
    - expenses
    - total_paid, deposit_paid (from payment module)
    - profit, margin
    - material usage details
    - labor items details
    """
    try:
        financials = await service.get_financial_summary(project_id)
        return success_response(
            financials.model_dump(),
            message="Financials retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 5. TASKS
# =============================================================================

@project_router.post("/{project_id}/tasks", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_task(
    project_id: UUID,
    request: ProjectTaskCreate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Add a task to a project."""
    try:
        task = await service.add_task(project_id, request.model_dump())
        return success_response(
            {"id": str(task.id)},
            message="Task added successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/{project_id}/tasks", response_model=BaseResponse)
async def get_tasks(
    project_id: UUID,
    status: Optional[str] = Query(None, description="Filter by task status (todo, in_progress, done)"),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all tasks for a project."""
    try:
        tasks = await service.get_tasks(project_id, status)
        return success_response(
            [ProjectTaskResponse.model_validate(t).model_dump() for t in tasks],
            message="Tasks retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.patch("/tasks/{task_id}", response_model=BaseResponse)
async def update_task(
    task_id: UUID,
    request: ProjectTaskUpdate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Update a task."""
    try:
        task = await service.update_task(task_id, request.model_dump(exclude_unset=True))
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return success_response(
            {"id": str(task.id)},
            message="Task updated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/tasks/{task_id}", response_model=BaseResponse)
async def delete_task(
    task_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Delete a task."""
    try:
        result = await service.delete_task(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        return success_response(
            {"id": str(task_id)},
            message="Task deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post("/tasks/{task_id}/complete", response_model=BaseResponse)
async def complete_task(
    task_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Mark a task as completed."""
    try:
        task = await service.complete_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return success_response(
            {"id": str(task.id), "status": "completed"},
            message="Task completed successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 6. LABOR
# =============================================================================

@project_router.post("/{project_id}/labor", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_labor(
    project_id: UUID,
    payload: ProjectLaborCreate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Add labor to a project."""
    try:
        labor = await service.add_labor(
            project_id=project_id,
            labor_type=payload.labor_type,
            hours=payload.hours,
            rate_per_hour=payload.rate_per_hour,
            technician_name=payload.technician_name,
            description=payload.description,
            date_performed=payload.date_performed
        )
        return success_response(
            {"id": str(labor.id)},
            message="Labor added successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/{project_id}/labor", response_model=BaseResponse)
async def get_labor(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all labor entries for a project."""
    try:
        labor_list = await service.get_labor_items(project_id)
        return success_response(
            [ProjectLaborResponse.model_validate(l).model_dump() for l in labor_list],
            message="Labor items retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/labor/{labor_id}", response_model=BaseResponse)
async def delete_labor(
    labor_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Delete a labor entry."""
    try:
        result = await service.delete_labor(labor_id)
        if not result:
            raise HTTPException(status_code=404, detail="Labor entry not found")
        return success_response(
            {"id": str(labor_id)},
            message="Labor deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 7. EXPENSES
# =============================================================================

@project_router.post("/{project_id}/expenses", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_expense(
    project_id: UUID,
    payload: ProjectExpenseCreate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Add an expense to a project."""
    try:
        expense = await service.add_expense(
            project_id=project_id,
            name=payload.name,
            category=payload.category,
            amount=payload.amount,
            description=payload.description,
            expense_date=payload.expense_date,
            is_billable=payload.is_billable
        )
        return success_response(
            {"id": str(expense.id)},
            message="Expense added successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/{project_id}/expenses", response_model=BaseResponse)
async def get_expenses(
    project_id: UUID,
    category: Optional[str] = Query(None, description="Filter by category"),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all expenses for a project."""
    try:
        expenses = await service.get_expenses(project_id, category)
        return success_response(
            [ProjectExpenseResponse.model_validate(e).model_dump() for e in expenses],
            message="Expenses retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post("/expenses/{expense_id}/approve", response_model=BaseResponse)
async def approve_expense(
    expense_id: UUID,
    approved_by: str = Body(..., embed=True, description="Nama yang menyetujui"),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Approve an expense."""
    try:
        expense = await service.approve_expense(expense_id, approved_by)
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        return success_response(
            {"id": str(expense.id), "approved_by": expense.approved_by},
            message="Expense approved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/expenses/{expense_id}", response_model=BaseResponse)
async def delete_expense(
    expense_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Delete an expense."""
    try:
        result = await service.repo.delete_expense(expense_id)
        if not result:
            raise HTTPException(status_code=404, detail="Expense not found")
        await service.db.commit()
        return success_response(
            {"id": str(expense_id)},
            message="Expense deleted successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 8. PRICE LIST ITEMS
# =============================================================================

@project_router.post("/{project_id}/price-list-items", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_price_list_item(
    project_id: UUID,
    price_list_item_id: UUID = Body(..., embed=True),
    quantity: Decimal = Body(Decimal(1), embed=True),
    notes: Optional[str] = Body(None, embed=True),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Add a price list item to a project."""
    try:
        item = await service.add_price_list_item(
            project_id=project_id,
            price_list_item_id=price_list_item_id,
            quantity=quantity,
            notes=notes
        )
        return success_response(
            {"id": str(item.id)},
            message="Price list item added successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/{project_id}/price-list-items", response_model=BaseResponse)
async def get_price_list_items(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all price list items for a project."""
    try:
        items = await service.get_price_list_items(project_id)
        return success_response(
            [ProjectPriceListItemResponse.model_validate(i).model_dump() for i in items],
            message="Price list items retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/price-list-items/{item_id}", response_model=BaseResponse)
async def remove_price_list_item(
    item_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Remove a price list item from project."""
    try:
        result = await service.remove_price_list_item(item_id)
        if not result:
            raise HTTPException(status_code=404, detail="Price list item not found")
        return success_response(
            {"id": str(item_id)},
            message="Price list item removed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 9. ACTIVITIES
# =============================================================================

@project_router.get("/{project_id}/activities", response_model=BaseResponse)
async def get_activities(
    project_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Max activities to return"),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all activities for a project."""
    try:
        activities = await service.get_activities(project_id, limit)
        return success_response([
            {
                "id": str(a.id),
                "activity": a.activity,
                "activity_type": a.activity_type,
                "performed_by": a.performed_by,
                "meta_data": a.meta_data,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in activities
        ], message="Activities retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 10. TIMELINE
# =============================================================================

@project_router.post("/{project_id}/timeline", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_timeline(
    project_id: UUID,
    request: ProjectTimelineCreate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Add timeline/milestone to project."""
    try:
        timeline = await service.add_timeline(project_id, request)
        return success_response(
            {"id": str(timeline.id)},
            message="Timeline added successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/{project_id}/timeline", response_model=BaseResponse)
async def get_timelines(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all timelines for a project."""
    try:
        timelines = await service.get_timelines(project_id)
        return success_response(
            [ProjectTimelineResponse.model_validate(t).model_dump() for t in timelines],
            message="Timelines retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.patch("/timeline/{timeline_id}", response_model=BaseResponse)
async def update_timeline(
    timeline_id: UUID,
    request: ProjectTimelineUpdate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Update timeline."""
    try:
        timeline = await service.update_timeline(timeline_id, request)
        if not timeline:
            raise HTTPException(status_code=404, detail="Timeline not found")
        return success_response(
            {"id": str(timeline.id)},
            message="Timeline updated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/timeline/{timeline_id}", response_model=BaseResponse)
async def delete_timeline(
    timeline_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Delete timeline."""
    try:
        result = await service.delete_timeline(timeline_id)
        if not result:
            raise HTTPException(status_code=404, detail="Timeline not found")
        return success_response(
            {"id": str(timeline_id)},
            message="Timeline deleted"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post("/timeline/{timeline_id}/complete", response_model=BaseResponse)
async def complete_timeline(
    timeline_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Mark timeline as completed."""
    try:
        timeline = await service.complete_timeline(timeline_id)
        if not timeline:
            raise HTTPException(status_code=404, detail="Timeline not found")
        return success_response(
            {"id": str(timeline.id), "status": "completed"},
            message="Timeline completed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 11. DOCUMENTS
# =============================================================================

@project_router.post("/{project_id}/documents", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: UUID,
    file: UploadFile,
    name: str = Body(..., embed=True),
    document_type: str = Body(..., embed=True),
    description: Optional[str] = Body(None, embed=True),
    is_public: bool = Body(True, embed=True),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Upload document to project."""
    try:
        document_data = ProjectDocumentUpload(
            file=file,
            name=name,
            document_type=document_type,
            description=description,
            is_public=is_public
        )
        document = await service.upload_document(project_id, file, document_data)
        return success_response(
            {
                "id": str(document.id),
                "file_path": document.file_path,
                "file_name": document.file_name
            },
            message="Document uploaded successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/{project_id}/documents", response_model=BaseResponse)
async def get_documents(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all documents for a project."""
    try:
        documents = await service.get_documents(project_id)
        return success_response(
            [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "document_type": d.document_type,
                    "file_path": d.file_path,
                    "file_name": d.file_name,
                    "file_size": d.file_size,
                    "mime_type": d.mime_type,
                    "uploaded_by": d.uploaded_by,
                    "description": d.description,
                    "is_public": d.is_public,
                    "created_at": d.created_at.isoformat() if d.created_at else None
                }
                for d in documents
            ],
            message="Documents retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/documents/{document_id}", response_model=BaseResponse)
async def delete_document(
    document_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Delete document."""
    try:
        result = await service.delete_document(document_id)
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        return success_response(
            {"id": str(document_id)},
            message="Document deleted"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 12. TEAM
# =============================================================================

@project_router.post("/{project_id}/team", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    project_id: UUID,
    request: ProjectTeamCreate,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Add team member to project."""
    try:
        team_member = await service.add_team_member(project_id, request)
        return success_response(
            {"id": str(team_member.id)},
            message="Team member added successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.get("/{project_id}/team", response_model=BaseResponse)
async def get_team_members(
    project_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Get all team members for a project."""
    try:
        team_members = await service.get_team_members(project_id)
        return success_response(
            [
                {
                    "id": str(t.id),
                    "user_id": str(t.user_id),
                    "role": t.role,
                    "assigned_at": t.assigned_at.isoformat() if t.assigned_at else None
                }
                for t in team_members
            ],
            message="Team members retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.delete("/team/{team_member_id}", response_model=BaseResponse)
async def remove_team_member(
    team_member_id: UUID,
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Remove team member from project."""
    try:
        result = await service.remove_team_member(team_member_id)
        if not result:
            raise HTTPException(status_code=404, detail="Team member not found")
        return success_response(
            {"id": str(team_member_id)},
            message="Team member removed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.patch("/team/{team_member_id}/role", response_model=BaseResponse)
async def update_team_member_role(
    team_member_id: UUID,
    role: str = Body(..., embed=True, description="project_manager, supervisor, technician"),
    service: ProjectService = Depends(get_service(ProjectService))
):
    """Update team member role."""
    try:
        team_member = await service.update_team_member_role(team_member_id, role)
        if not team_member:
            raise HTTPException(status_code=404, detail="Team member not found")
        return success_response(
            {"id": str(team_member.id), "role": team_member.role},
            message="Team member role updated"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))