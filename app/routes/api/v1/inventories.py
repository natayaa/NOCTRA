from uuid import UUID
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from database.session import SessionDep
from schemas.base_response import BaseResponse, ErrorResponse

# Schemas
from schemas.inventory_items import ItemCreate, ItemResponse
from schemas.inventory_stock_movement import StockMovementCreate
from schemas.inventory_material_usage import MaterialUsageCreate

# Models
from models.inventory_items import InventoryItems
from models.inventory_workshop_jobs import WorkshopJob

# Repositories
from repositories.inventory_items import InventoryRepository
from repositories.inventory_stock import StockMovementRepository
from repositories.inventory_workshop_jobs import WorkshopJobRepository
from repositories.inventory_material_usage import MaterialUsageRepository

# Services
from services.inventory_items import InventoryService
from services.inventory_dashboard import InventoryDashboardService


inventory_router = APIRouter(
    tags=["Inventory"],
    prefix="/api/inventory",
)


@inventory_router.post("/", response_class=JSONResponse, response_model=BaseResponse)
async def create_item(request: ItemCreate, db: SessionDep):
    repo = InventoryRepository(db)
    item = InventoryItems(**request.model_dump())
    result = await repo.create(item)
    await db.commit()
    await db.refresh(result)
    return BaseResponse(data={"id": str(result.id)})


@inventory_router.get("/", response_model=BaseResponse)
async def list_items(db: SessionDep):
    repo = InventoryRepository(db)
    items = await repo.list()
    return BaseResponse(
        data=[ItemResponse.model_validate(i) for i in items]
    )

@inventory_router.delete("/usage/{usage_id}", response_model=BaseResponse)
async def delete_material_usage(usage_id: UUID, db: SessionDep):
    repo = MaterialUsageRepository(db)
    usage = await repo.get_by_id(usage_id)
    if not usage:
        raise HTTPException(status_code=404, detail="Material usage not found")
    deleted = await repo.delete(usage_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Material usage not found")
    await db.commit()
    return BaseResponse(data={"id": str(usage_id)})

@inventory_router.delete("/{item_id}", response_class=JSONResponse, response_model=BaseResponse)
async def delete_item(item_id: UUID, db: SessionDep):
    service = InventoryService(db)
    try:
        item = await service.delete_item(str(item_id))
        await db.commit()
        return BaseResponse(data={"id": str(item.id)})
    except Exception as e:
        return ErrorResponse(message=str(e))


@inventory_router.put("/{item_id}", response_class=JSONResponse, response_model=BaseResponse)
async def update_item(item_id: UUID, request: ItemCreate, db: SessionDep):
    repo = InventoryRepository(db)
    item = await repo.get(str(item_id))
    if not item:
        return ErrorResponse(message="Item not found")

    for key, value in request.model_dump().items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


@inventory_router.post("/movement", response_class=JSONResponse, response_model=BaseResponse)
async def create_movement(request: StockMovementCreate, db: SessionDep):
    service = InventoryService(db)
    movement = await service.create_movement(
        item_id=str(request.item_id),
        type=request.type,
        quantity=request.quantity,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        note=request.note,
    )
    await db.commit()
    return BaseResponse(data={"id": str(movement.id)})


@inventory_router.get("/movement/recent", response_class=JSONResponse)
async def recent_movements(db: SessionDep):
    # FIX: StockMovementRepository does NOT accept db in __init__
    repo = StockMovementRepository(db)  # No arguments
    data = await repo.recent(db)      # Pass db to the method
    return BaseResponse(data=data)


@inventory_router.get("/alerts")
async def stock_alerts(db: SessionDep):
    service = InventoryDashboardService(db)
    alerts = await service.get_stock_alerts()
    return BaseResponse(data=alerts)


@inventory_router.post("/usage", response_model=BaseResponse)
async def record_material_usage(request: MaterialUsageCreate, db: SessionDep):
    service = InventoryService(db)
    try:
        usage = await service.use_item_for_job(
            job_id=str(request.job_id),
            item_id=str(request.item_id),
            quantity=request.quantity,
            note=request.note
        )
        await db.commit()
        return BaseResponse(data={"id": str(usage.id)})
    except ValueError as e:
        return ErrorResponse(message=str(e))
    
    
@inventory_router.get("/usage/project/{project_id}", response_model=BaseResponse)
async def get_material_usage_by_project(project_id: UUID, db: SessionDep):
    repo = MaterialUsageRepository(db)
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


@inventory_router.post("/workshop", response_class=JSONResponse, response_model=BaseResponse)
async def create_workshop_job(payload: dict, db: SessionDep):
    repo = WorkshopJobRepository(db)
    job = WorkshopJob(**payload)
    result = await repo.create(job)
    await db.commit()
    await db.refresh(result)
    return BaseResponse(data={"id": str(result.id)})


@inventory_router.get("/workshop/{job_id}", response_class=JSONResponse)
async def get_workshop_job(job_id: UUID, db: SessionDep):
    repo = WorkshopJobRepository(db)
    job = await repo.get(str(job_id))
    if not job:
        return ErrorResponse(message="Job not found")
    return BaseResponse(data=job)

