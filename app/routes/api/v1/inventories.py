from uuid import UUID
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from database.session import SessionDep
from schemas.base_response import BaseResponse, ErrorResponse

# Schemas (diperbaiki sesuai file schemas yang diberikan)
from schemas.inventories import (
    CreateInventoryItem,
    UpdateInventoryItem,
    InventoryItemResponse,
    CreateInventoryMaterialUsage,
    CreateInventoryStockMovement,
    ProjectWorkshopCreate,
    ProjectWorkshopResponse,
)

# Models (gunakan model yang benar)
from models.inventory import InventoryItem, ProjectWorkshopTask

# Repositories (gunakan nama kelas yang tepat)
from repositories.inventory_repository import (
    InventoryRepository,
    InventoryMaterialUsageRepository,
    InventoryStockMovementRepository,
    ProjectWorkshopJobRepository,
)

# Services (gunakan InventoryServices dari inventory_dashboard)
from services.inventory_dashboard import InventoryServices, InventoryDashboardService


inventory_router = APIRouter(
    tags=["Inventory"],
    prefix="/api/inventory",
)


# -------------------- Item CRUD --------------------
@inventory_router.post("/", response_class=JSONResponse, response_model=BaseResponse)
async def create_item(request: CreateInventoryItem, db: SessionDep):
    repo = InventoryRepository(db)
    item = await repo.create(request)          # repo.create menerima CreateInventoryItem
    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


@inventory_router.get("/", response_model=BaseResponse)
async def list_items(db: SessionDep):
    repo = InventoryRepository(db)
    items = await repo.list_active()           # gunakan list_active
    return BaseResponse(
        data=[InventoryItemResponse.model_validate(i) for i in items]
    )


@inventory_router.delete("/{item_id}", response_class=JSONResponse, response_model=BaseResponse)
async def delete_item(item_id: UUID, db: SessionDep):
    repo = InventoryRepository(db)
    success = await repo.soft_delete(item_id)  # soft delete
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.commit()
    return BaseResponse(data={"id": str(item_id)})


@inventory_router.put("/{item_id}", response_class=JSONResponse, response_model=BaseResponse)
async def update_item(item_id: UUID, request: UpdateInventoryItem, db: SessionDep):
    repo = InventoryRepository(db)
    item = await repo.update(item_id, request)  # update menerima UpdateInventoryItem
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


# -------------------- Stock Movements --------------------
@inventory_router.post("/movement", response_class=JSONResponse, response_model=BaseResponse)
async def create_movement(request: CreateInventoryStockMovement, db: SessionDep):
    # Buat objek movement dari request
    from models.inventory import InventoryStockMovement
    movement = InventoryStockMovement(
        item_id=request.item_id,
        type=request.type,
        quantity=request.quantity,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        note=request.note,
    )
    repo = InventoryStockMovementRepository(db)
    result = await repo.create_stock_movement(db, movement)
    await db.commit()
    return BaseResponse(data={"id": str(result.id)})


@inventory_router.get("/movement/recent", response_class=JSONResponse)
async def recent_movements(db: SessionDep, limit: int = 10):
    repo = InventoryStockMovementRepository(db)
    data = await repo.recent_stock_movement(limit)  # method menerima db dan limit
    return BaseResponse(data=data)


# -------------------- Material Usage --------------------
@inventory_router.post("/usage", response_model=BaseResponse)
async def record_material_usage(request: CreateInventoryMaterialUsage, db: SessionDep):
    service = InventoryServices(db)
    try:
        usage = await service.use_item_for_job(
            project_id=str(request.project_id),
            item_id=str(request.item_id),
            quantity=request.quantity,
            note=request.note,
        )
        await db.commit()
        return BaseResponse(data={"id": str(usage.id)})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@inventory_router.get("/usage/project/{project_id}", response_model=BaseResponse)
async def get_material_usage_by_project(project_id: UUID, db: SessionDep):
    repo = InventoryMaterialUsageRepository(db)
    usages = await repo.get_by_project(str(project_id))
    data = []
    for u in usages:
        data.append({
            "id": str(u.id),
            "item_name": u.item.name if u.item else "Unknown",
            "quantity": u.quantity,
            "unit": u.item.unit if u.item else "",
            "cost_price": float(u.item.cost_price) if u.item else 0,
            "total_cost": float(u.quantity * u.item.cost_price) if u.item else 0,
            "created_at": u.created_at.isoformat(),
            "note": u.note
        })
    return BaseResponse(data=data)


@inventory_router.delete("/usage/{usage_id}", response_model=BaseResponse)
async def delete_material_usage(usage_id: UUID, db: SessionDep):
    repo = InventoryMaterialUsageRepository(db)
    usage = await repo.get_by_id(usage_id)
    if not usage:
        raise HTTPException(status_code=404, detail="Material usage not found")
    deleted = await repo.delete_usage_material(usage_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Material usage not found")
    await db.commit()
    return BaseResponse(data={"id": str(usage_id)})


# -------------------- Alerts & Dashboard --------------------
@inventory_router.get("/alerts")
async def stock_alerts(db: SessionDep):
    service = InventoryDashboardService(db)
    alerts = await service.get_stock_alerts()
    return BaseResponse(data=alerts)


@inventory_router.get("/dashboard/kpis", response_class=JSONResponse)
async def kpis(db: SessionDep):
    service = InventoryDashboardService(db)
    data = await service.get_kpis()
    return BaseResponse(data=data)


@inventory_router.get("/dashboard/monthly-usage", response_class=JSONResponse)
async def monthly_usage(db: SessionDep):
    service = InventoryDashboardService(db)
    data = await service.get_monthly_usage()
    return BaseResponse(data=data)


# -------------------- Workshop Jobs --------------------
@inventory_router.post("/workshop", response_class=JSONResponse, response_model=BaseResponse)
async def create_workshop_job(payload: ProjectWorkshopCreate, db: SessionDep):
    repo = ProjectWorkshopJobRepository(db)
    job = ProjectWorkshopTask(
        unit_name=payload.unit_name,
        status=payload.status,
        estimated_cost=payload.estimated_cost,
    )
    result = await repo.create_history(job)
    await db.commit()
    await db.refresh(result)
    return BaseResponse(data={"id": str(result.id)})


@inventory_router.get("/workshop/{job_id}", response_class=JSONResponse)
async def get_workshop_job(job_id: UUID, db: SessionDep):
    repo = ProjectWorkshopJobRepository(db)
    job = await repo.get_project_workshop(str(job_id))
    if not job:
        return ErrorResponse(message="Job not found")
    # Konversi ke response schema
    return BaseResponse(data=ProjectWorkshopResponse.model_validate(job))