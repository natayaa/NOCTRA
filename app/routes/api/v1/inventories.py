from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from schemas.base_response import BaseResponse, ErrorResponse

from schemas.inventory_items import ItemCreate, ItemResponse
from schemas.inventory_stock_movement import StockMovementCreate

from database.session import SessionDep

from models.inventory_items import InventoryItems
from models.inventory_workshop_jobs import WorkshopJob

from repositories.inventory_items import ItemRepository
from repositories.inventory_stock import StockMovementRepository
from repositories.inventory_workshop_jobs import WorkshopJobRepository

from services.inventory_items import InventoryService
from services.inventory_dashboard import DashboardService


inventory_router = APIRouter(
    tags=["Inventory"],
    prefix="/api/inventory",
)


@inventory_router.post("/", response_class=JSONResponse, response_model=BaseResponse)
async def create_item(request: ItemCreate, db: SessionDep):
    repo = ItemRepository()
    item = InventoryItems(**request.model_dump())
    result = await repo.create(db, obj=item)

    await db.commit()
    await db.refresh(result)

    return BaseResponse(data={"id": str(result.id)})


@inventory_router.get("/", response_model=BaseResponse)
async def list_items(db: SessionDep):
    repo = ItemRepository()

    items = await repo.list(db)

    return BaseResponse(
        data=[ItemResponse.model_validate(i) for i in items]
    )


@inventory_router.delete("/{item_id}", response_class=JSONResponse, response_model=BaseResponse)
async def delete_item(item_id: UUID, db: SessionDep):
    service = InventoryService()

    try:
        item = await service.delete_item(db, str(item_id))
        await db.commit()

        return BaseResponse(data={"id": str(item.id)})

    except Exception as e:
        return ErrorResponse(message=str(e))


@inventory_router.post("/movement", response_class=JSONResponse, response_model=BaseResponse)
async def create_movement(request: StockMovementCreate, db: SessionDep):
    service = InventoryService()

    movement = await service.create_movement(
        db=db,
        item_id=request.item_id,
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
    repo = StockMovementRepository()

    data = await repo.recent(db)

    return BaseResponse(data=data)


@inventory_router.get("/dashboard/kpis", response_class=JSONResponse)
async def kpis(db: SessionDep):
    service = DashboardService()

    data = await service.get_kpis(db)

    return BaseResponse(data=data)


@inventory_router.get("/dashboard/monthly-usage", response_class=JSONResponse)
async def monthly_usage(db: SessionDep):
    service = DashboardService()

    data = await service.monthly_usage(db)

    return BaseResponse(data=data)


@inventory_router.post("/workshop", response_class=JSONResponse, response_model=BaseResponse)
async def create_workshop_job(payload: dict, db: SessionDep):
    repo = WorkshopJobRepository()

    job = WorkshopJob(**payload)

    result = await repo.create(db, obj=job)

    await db.commit()
    await db.refresh(result)

    return BaseResponse(data={"id": str(result.id)})


@inventory_router.get("/workshop/{job_id}", response_class=JSONResponse)
async def get_workshop_job(job_id: UUID, db: SessionDep):
    repo = WorkshopJobRepository()

    job = await repo.get(db, str(job_id))

    if not job:
        return ErrorResponse(message="Job not found")

    return BaseResponse(data=job)
