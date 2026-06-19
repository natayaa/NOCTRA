# routers/price_list.py
from uuid import UUID

from fastapi import APIRouter, Query, HTTPException, status

from database.session import SessionDep
from schemas.base_response import BaseResponse, PaginatedResponse
from schemas.price_list import (
    PriceListItemCreate,
    PriceListItemUpdate,
    PriceListItemResponse,
)
from services.price_list import PriceListService

# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------

price_list = APIRouter(
    prefix="/api/price-list",
    tags=["Price List"],
)


@price_list.post(
    "/",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new price list item",
)
async def create_price_item(
    request: PriceListItemCreate,
    db: SessionDep,
) -> BaseResponse:
    """
    Create a new price list item (service, material, labor, or bike model).
    """
    service = PriceListService(db)
    item = await service.create(request)
    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


@price_list.get(
    "/",
    response_model=PaginatedResponse[PriceListItemResponse],
    summary="List price list items with pagination and filters",
)
async def list_price_items(
    db: SessionDep,
    category: str | None = Query(None, description="Filter by category (service, material, labor, bike_model)"),
    search: str | None = Query(None, description="Search by name or description"),
    active_only: bool = Query(True, description="Only include active items"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginatedResponse[PriceListItemResponse]:
    """
    Retrieve a paginated list of price list items with optional filtering.
    """
    service = PriceListService(db)
    items, total = await service.list_paginated(
        category=category,
        search=search,
        active_only=active_only,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(
        data=[PriceListItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=limit,
    )


@price_list.get(
    "/{item_id}",
    response_model=BaseResponse,
    summary="Get a single price list item by ID",
)
async def get_price_item(
    item_id: UUID,
    db: SessionDep,
) -> BaseResponse:
    """
    Retrieve detailed information about a specific price list item.
    """
    service = PriceListService(db)
    item = await service.get(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Price list item with ID '{item_id}' not found",
        )
    return BaseResponse(data=PriceListItemResponse.model_validate(item))


@price_list.put(
    "/{item_id}",
    response_model=BaseResponse,
    summary="Update an existing price list item",
)
async def update_price_item(
    item_id: UUID,
    request: PriceListItemUpdate,
    db: SessionDep,
) -> BaseResponse:
    """
    Update one or more fields of a price list item.
    Only provided fields will be updated (partial update).
    """
    service = PriceListService(db)
    item = await service.update(item_id, request)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Price list item with ID '{item_id}' not found",
        )
    await db.commit()
    await db.refresh(item)
    return BaseResponse(data={"id": str(item.id)})


@price_list.delete(
    "/{item_id}",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a price list item",
)
async def delete_price_item(
    item_id: UUID,
    db: SessionDep,
) -> BaseResponse:
    """
    Soft-delete a price list item by setting `is_active = False`.
    The item remains in the database for audit purposes.
    """
    service = PriceListService(db)
    success = await service.delete(item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Price list item with ID '{item_id}' not found",
        )
    await db.commit()
    return BaseResponse(data={"id": str(item_id)})