# routers/price_list.py
from fastapi import APIRouter, Query, HTTPException
from uuid import UUID
from database.session import SessionDep
from schemas.base_response import BaseResponse, PaginatedResponse, ErrorResponse
from schemas.price_list import PriceListItemCreate, PriceListItemUpdate, PriceListItemResponse
from services.price_list import PriceListService

price_list = APIRouter(prefix="/api/price-list", tags=["Price List"])


@price_list.post("/", response_model=BaseResponse)
async def create_price_item(request: PriceListItemCreate, db: SessionDep):
    service = PriceListService(db)
    item = await service.create(request)
    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


@price_list.get("/", response_model=PaginatedResponse[PriceListItemResponse])
async def list_price_items(
    db: SessionDep,
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search by name or description"),
    active_only: bool = Query(True, description="Only active items"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    service = PriceListService(db)
    items, total = await service.list_paginated(
        category=category,
        search=search,
        active_only=active_only,
        page=page,
        limit=limit
    )
    return PaginatedResponse(
        data=[PriceListItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=limit
    )


@price_list.get("/{item_id}", response_model=BaseResponse)
async def get_price_item(item_id: UUID, db: SessionDep):
    service = PriceListService(db)
    item = await service.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Price item not found")
    return BaseResponse(data=PriceListItemResponse.model_validate(item))


@price_list.put("/{item_id}", response_model=BaseResponse)
async def update_price_item(item_id: UUID, request: PriceListItemUpdate, db: SessionDep):
    service = PriceListService(db)
    item = await service.update(item_id, request)
    if not item:
        raise HTTPException(status_code=404, detail="Price item not found")
    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


@price_list.delete("/{item_id}", response_model=BaseResponse)
async def delete_price_item(item_id: UUID, db: SessionDep):
    service = PriceListService(db)
    success = await service.delete(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Price item not found")
    await db.commit()
    return BaseResponse(data={"id": str(item_id)})