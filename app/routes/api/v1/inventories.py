# routers/inventories.py
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from decimal import Decimal

from database.session import SessionDep
from schemas.base_response import BaseResponse

from schemas.inventories import (
    CreateInventoryItem,
    UpdateInventoryItem,
    InventoryItemResponse,
    InventoryMaterialUsageCreate,
    InventoryStockMovementCreate,
    ProjectWorkshopCreate,
    ProjectWorkshopResponse,
    InventoryStockMovementResponse,
    InventoryMaterialUsageResponse,
    SupplierResponse,
    SupplierCreate
)

from models.inventory import InventoryItem, ProjectWorkshopTask, InventoryStockMovement

from repositories.inventory_repository import (
    InventoryRepository,
    InventoryMaterialUsageRepository,
    InventoryStockMovementRepository,
    ProjectWorkshopJobRepository,
    SupplierRepository,
)

from services.inventory_dashboard import InventoryDashboardService
from services.inventory_service import InventoryService  # <-- IMPORT YANG BENAR


inventory_router = APIRouter(
    tags=["Inventory"],
    prefix="/api/inventory",
)


# -------------------- Item CRUD --------------------
@inventory_router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    request: CreateInventoryItem,
    db: SessionDep
):
    repo = InventoryRepository(db)
    item = await repo.create(request)
    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


@inventory_router.get("/", response_model=BaseResponse)
async def list_items(
    category: str | None = Query(None, description="Filter by category"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by name or SKU"),
    low_stock_only: bool = Query(False, description="Show only low stock items"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: SessionDep = None
):
    repo = InventoryRepository(db)
    items, total = await repo.list_with_filters(
        category=category,
        status=status,
        search=search,
        low_stock_only=low_stock_only,
        limit=limit,
        offset=offset
    )
    return BaseResponse(data={
        "items": [InventoryItemResponse.model_validate(i).model_dump() for i in items],
        "total": total,
        "limit": limit,
        "offset": offset
    })


@inventory_router.get("/{item_id}", response_model=BaseResponse)
async def get_item(
    item_id: UUID,
    db: SessionDep
):
    repo = InventoryRepository(db)
    item = await repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return BaseResponse(data=InventoryItemResponse.model_validate(item).model_dump())


@inventory_router.put("/{item_id}", response_model=BaseResponse)
async def update_item(
    item_id: UUID,
    request: UpdateInventoryItem,
    db: SessionDep
):
    repo = InventoryRepository(db)
    item = await repo.update(item_id, request)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


@inventory_router.delete("/{item_id}", response_model=BaseResponse)
async def delete_item(
    item_id: UUID,
    db: SessionDep
):
    repo = InventoryRepository(db)
    success = await repo.soft_delete(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.commit()
    return BaseResponse(data={"id": str(item_id)})


# -------------------- Stock Movements --------------------
@inventory_router.post("/movement", response_model=BaseResponse)
async def create_movement(request: InventoryStockMovementCreate, db: SessionDep):
    repo = InventoryStockMovementRepository(db)
    
    # Get current stock to calculate previous and new
    inventory_repo = InventoryRepository(db)
    item = await inventory_repo.get_by_id(request.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    previous_stock = item.current_stock
    
    # Calculate new stock based on movement type
    if request.type in ["purchase", "return", "received"]:
        new_stock = previous_stock + request.quantity
    elif request.type in ["sale", "usage", "waste", "shipped"]:
        new_stock = previous_stock - request.quantity
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Insufficient stock")
    else:  # adjustment
        new_stock = request.quantity
    
    movement = InventoryStockMovement(
        item_id=request.item_id,
        type=request.type,
        quantity=request.quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        note=request.note,
        performed_by=request.performed_by or "system"
    )
    
    result = await repo.create_stock_movement(movement)
    
    # Update item stock
    item.current_stock = new_stock
    await db.flush()
    await db.commit()
    
    return BaseResponse(data={"id": str(result.id)})


@inventory_router.get("/movement/recent", response_model=BaseResponse)
async def recent_movements(
    limit: int = Query(10, ge=1, le=50),
    db: SessionDep = None
):
    repo = InventoryStockMovementRepository(db)
    data = await repo.recent_stock_movement(limit)
    return BaseResponse(data=data)


@inventory_router.get("/movement/item/{item_id}", response_model=BaseResponse)
async def get_item_movements(
    item_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: SessionDep = None
):
    repo = InventoryStockMovementRepository(db)
    movements = await repo.get_by_item(item_id, limit)
    return BaseResponse(data=[InventoryStockMovementResponse.model_validate(m).model_dump() for m in movements])


# -------------------- Material Usage --------------------
@inventory_router.post("/usage", response_model=BaseResponse)
async def record_material_usage(
    request: InventoryMaterialUsageCreate,
    db: SessionDep
):
    service = InventoryService(db)
    try:
        usage = await service.use_item_for_job(
            project_id=request.project_id,
            item_id=request.item_id,
            quantity=request.quantity,
            unit=request.unit,  # 🔥 Kirim unit yang digunakan
            note=request.note,
            job_id=request.job_id
        )
        await db.commit()
        return BaseResponse(data={"id": str(usage.id)})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@inventory_router.get("/usage/project/{project_id}", response_model=BaseResponse)
async def get_material_usage_by_project(
    project_id: UUID,
    db: SessionDep
):
    repo = InventoryMaterialUsageRepository(db)
    usages = await repo.get_by_project(project_id)
    data = []
    for u in usages:
        data.append({
            "id": str(u.id),
            "item_name": u.item.name if u.item else "Unknown",
            "quantity": float(u.quantity),
            "unit": u.item.unit if u.item else "",
            "unit_cost": float(u.unit_cost) if u.unit_cost else 0,
            "total_cost": float(u.total_cost) if u.total_cost else 0,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "note": u.note
        })
    return BaseResponse(data=data)


@inventory_router.delete("/usage/{usage_id}", response_model=BaseResponse)
async def delete_material_usage(
    usage_id: UUID,
    db: SessionDep
):
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
@inventory_router.get("/alerts", response_model=BaseResponse)
async def stock_alerts(
    db: SessionDep = None
):
    service = InventoryDashboardService(db)
    alerts = await service.get_stock_alerts()
    return BaseResponse(data=alerts)


@inventory_router.get("/dashboard/kpis", response_model=BaseResponse)
async def kpis(
    db: SessionDep = None
):
    service = InventoryDashboardService(db)
    data = await service.get_kpis()
    return BaseResponse(data=data)


@inventory_router.get("/dashboard/monthly-usage", response_model=BaseResponse)
async def monthly_usage(
    db: SessionDep = None
):
    service = InventoryDashboardService(db)
    data = await service.get_monthly_usage()
    return BaseResponse(data=data)


@inventory_router.get("/dashboard/top-used", response_model=BaseResponse)
async def top_used_items(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: SessionDep = None
):
    service = InventoryDashboardService(db)
    data = await service.get_top_used_items(days, limit)
    return BaseResponse(data=data)


# -------------------- Workshop Jobs --------------------
@inventory_router.post("/workshop", response_model=BaseResponse)
async def create_workshop_job(
    payload: ProjectWorkshopCreate,
    db: SessionDep
):
    repo = ProjectWorkshopJobRepository(db)
    job = ProjectWorkshopTask(
        project_id=payload.project_id,
        unit_name=payload.unit_name,
        status=payload.status,
        estimated_cost=payload.estimated_cost,
        start_date=payload.start_date,
        end_date=payload.end_date,
        technician_name=payload.technician_name,
        notes=payload.notes
    )
    result = await repo.create_history(job)
    await db.commit()
    await db.refresh(result)
    return BaseResponse(data={"id": str(result.id)})


@inventory_router.get("/workshop/project/{project_id}", response_model=BaseResponse)
async def get_workshop_by_project(
    project_id: UUID,
    db: SessionDep
):
    repo = ProjectWorkshopJobRepository(db)
    job = await repo.get_by_project(project_id)
    if not job:
        return BaseResponse(data=None)
    return BaseResponse(data=ProjectWorkshopResponse.model_validate(job).model_dump())


@inventory_router.get("/workshop/{job_id}", response_model=BaseResponse)
async def get_workshop_job(
    job_id: UUID,
    db: SessionDep
):
    repo = ProjectWorkshopJobRepository(db)
    job = await repo.get_project_workshop(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return BaseResponse(data=ProjectWorkshopResponse.model_validate(job).model_dump())


# -------------------- Suppliers --------------------
@inventory_router.get("/suppliers", response_model=BaseResponse)
async def list_suppliers(
    db: SessionDep = None
):
    repo = SupplierRepository(db)
    suppliers = await repo.list_active()
    return BaseResponse(data=[
        SupplierResponse.model_validate(s).model_dump() for s in suppliers
    ])


@inventory_router.post("/suppliers", response_model=BaseResponse)
async def create_supplier(
    request: SupplierCreate,
    db: SessionDep
):
    repo = SupplierRepository(db)
    supplier = await repo.create(request.model_dump())
    await db.commit()
    await db.refresh(supplier)
    return BaseResponse(data={"id": str(supplier.id)})