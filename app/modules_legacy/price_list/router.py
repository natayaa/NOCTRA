# modules/price_list/router.py
from decimal import Decimal
from uuid import UUID
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.base import BaseResponse, PaginatedResponse
from core.dependencies import success_response, get_service
from core.exceptions import NotFoundError, ValidationError, BusinessError
from modules.price_list.schemas import (
    PriceListItemCreate,
    PriceListItemUpdate,
    PriceListItemResponse,
    PriceListCategoryCreate,
    PriceListCategoryUpdate,
    PriceListCategoryResponse,
    PriceListDiscountCreate,
    PriceListDiscountUpdate,
    PriceListDiscountResponse,
    PriceListBulkUpdate,
    PriceChangeRequest,
    PriceRevertRequest,
    CustomPriceCreate,
    CustomPriceUpdate,
    CustomPriceResponse,
    PriceHistoryResponse,
    PriceCalculationResponse,
    PriceListStatisticsResponse,
    PriceListItemListResponse,
)
from modules.price_list.services import PriceListService


price_list_router = APIRouter(
    prefix="/api/price-list",
    tags=["Price List"]
)


# =============================================================================
# Price List Items
# =============================================================================

@price_list_router.post("/items", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_price_item(
    request: PriceListItemCreate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Create a new price list item."""
    try:
        item = await service.create_item(request)
        await service.db.commit()
        return success_response(
            PriceListItemResponse.model_validate(item).model_dump(),
            message="Price item created successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/items", response_model=BaseResponse)
async def list_price_items(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    active_only: bool = Query(True, description="Only include active items"),
    vehicle_brand: Optional[str] = Query(None, description="Filter by vehicle brand"),
    vehicle_model: Optional[str] = Query(None, description="Filter by vehicle model"),
    include_deleted: bool = Query(False, description="Include soft-deleted items"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort field (name, price, category, effective_date)"),
    sort_order: str = Query("asc", description="Sort order (asc, desc)"),
    service: PriceListService = Depends(get_service(PriceListService))
):
    """List price items with pagination and filters."""
    try:
        items, total = await service.list_items(
            category=category,
            search=search,
            active_only=active_only,
            vehicle_brand=vehicle_brand,
            vehicle_model=vehicle_model,
            include_deleted=include_deleted,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )

        serialized_items = [
            PriceListItemResponse.model_validate(item).model_dump()
            for item in items
        ]

        total_pages = (total + limit - 1) // limit if total > 0 else 0

        return success_response(
            {
                "items": serialized_items,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            },
            message="Price items retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/items/{item_id}", response_model=BaseResponse)
async def get_price_item(
    item_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get price list item by ID."""
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price item not found"
        )

    return success_response(
        PriceListItemResponse.model_validate(item).model_dump(),
        message="Price item retrieved successfully"
    )


@price_list_router.get("/items/{item_id}/details", response_model=BaseResponse)
async def get_price_item_details(
    item_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get price list item with all related data (history, custom prices)."""
    try:
        item = await service.get_item_with_details(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price item not found"
            )

        return success_response(
            PriceListItemResponse.model_validate(item).model_dump(),
            message="Price item details retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.patch("/items/{item_id}", response_model=BaseResponse)
async def update_price_item(
    item_id: UUID,
    request: PriceListItemUpdate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Update price list item."""
    try:
        item = await service.update_item(item_id, request)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price item not found"
            )
        await service.db.commit()
        return success_response(
            PriceListItemResponse.model_validate(item).model_dump(),
            message="Price item updated successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.delete("/items/{item_id}", response_model=BaseResponse)
async def delete_price_item(
    item_id: UUID,
    permanent: bool = Query(False, description="Permanent delete (cannot be undone)"),
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Delete price list item (soft delete by default)."""
    try:
        if permanent:
            result = await service.hard_delete_item(item_id)
        else:
            result = await service.delete_item(item_id)
            
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price item not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(item_id)},
            message=f"Price item {'permanently ' if permanent else ''}deleted successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.post("/items/{item_id}/toggle", response_model=BaseResponse)
async def toggle_price_item(
    item_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Toggle active status of a price list item."""
    try:
        item = await service.toggle_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price item not found"
            )
        await service.db.commit()
        return success_response(
            {
                "id": str(item.id),
                "is_active": item.is_active,
                "name": item.name
            },
            message=f"Price item {'activated' if item.is_active else 'deactivated'} successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# Price Management
# =============================================================================

@price_list_router.post("/items/{item_id}/change-price", response_model=BaseResponse)
async def change_price_item_price(
    item_id: UUID,
    request: PriceChangeRequest,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Change price with history tracking."""
    try:
        item = await service.change_price(item_id, request, changed_by="system")
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price item not found"
            )
        await service.db.commit()
        return success_response(
            {
                "id": str(item.id),
                "old_price": float(request.new_price),  # Actually this is new price
                "new_price": float(item.price),
                "name": item.name
            },
            message="Price changed successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.post("/items/{item_id}/revert-price", response_model=BaseResponse)
async def revert_price_item_price(
    item_id: UUID,
    request: PriceRevertRequest,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Revert price to historical price."""
    try:
        item = await service.revert_price(item_id, request, changed_by="system")
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price item not found"
            )
        await service.db.commit()
        return success_response(
            {
                "id": str(item.id),
                "price": float(item.price),
                "name": item.name,
                "history_id": str(request.history_id)
            },
            message="Price reverted successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/items/{item_id}/price-history", response_model=BaseResponse)
async def get_price_item_history(
    item_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Limit"),
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get price history for an item."""
    try:
        history = await service.get_price_history(item_id, limit)
        return success_response(
            [PriceHistoryResponse.model_validate(h).model_dump() for h in history],
            message="Price history retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/items/{item_id}/price-summary", response_model=BaseResponse)
async def get_price_item_summary(
    item_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get price change summary for an item."""
    try:
        summary = await service.get_price_change_summary(item_id)
        return success_response(
            summary,
            message="Price summary retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# Price Calculation
# =============================================================================

@price_list_router.post("/calculate", response_model=BaseResponse)
async def calculate_price(
    item_id: UUID = Query(..., description="Item ID"),
    quantity: Decimal = Query(1, description="Quantity", ge=0.01),
    customer_id: Optional[UUID] = Query(None, description="Customer ID for custom pricing"),
    project_id: Optional[UUID] = Query(None, description="Project ID for custom pricing"),
    discount_code: Optional[str] = Query(None, description="Discount code"),
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Calculate final price with all applicable discounts."""
    try:
        result = await service.calculate_price(
            item_id=item_id,
            quantity=quantity,
            customer_id=customer_id,
            project_id=project_id,
            discount_code=discount_code
        )
        return success_response(
            result,
            message="Price calculated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# Categories
# =============================================================================

@price_list_router.post("/categories", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_price_category(
    request: PriceListCategoryCreate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Create a new price list category."""
    try:
        category = await service.create_category(request)
        await service.db.commit()
        return success_response(
            PriceListCategoryResponse.model_validate(category).model_dump(),
            message="Category created successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/categories", response_model=BaseResponse)
async def list_price_categories(
    service: PriceListService = Depends(get_service(PriceListService))
):
    """List all active categories."""
    try:
        categories = await service.list_categories()
        return success_response(
            [PriceListCategoryResponse.model_validate(c).model_dump() for c in categories],
            message="Categories retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/categories/names", response_model=BaseResponse)
async def get_category_names(
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get all unique category names."""
    try:
        categories = await service.get_categories()
        return success_response(
            categories,
            message="Category names retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/categories/with-counts", response_model=BaseResponse)
async def get_categories_with_counts(
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get categories with item counts."""
    try:
        categories = await service.get_categories_with_counts()
        return success_response(
            categories,
            message="Categories with counts retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/categories/{category_id}", response_model=BaseResponse)
async def get_price_category(
    category_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get category by ID."""
    try:
        category = await service.get_category(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        return success_response(
            PriceListCategoryResponse.model_validate(category).model_dump(),
            message="Category retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/categories/by-name/{name}", response_model=BaseResponse)
async def get_category_by_name(
    name: str,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get category by name."""
    try:
        category = await service.get_category_by_name(name)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{name}' not found"
            )
        return success_response(
            PriceListCategoryResponse.model_validate(category).model_dump(),
            message="Category retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.patch("/categories/{category_id}", response_model=BaseResponse)
async def update_price_category(
    category_id: UUID,
    request: PriceListCategoryUpdate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Update a category."""
    try:
        category = await service.update_category(category_id, request)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        await service.db.commit()
        return success_response(
            PriceListCategoryResponse.model_validate(category).model_dump(),
            message="Category updated successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.delete("/categories/{category_id}", response_model=BaseResponse)
async def delete_price_category(
    category_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Delete a category."""
    try:
        result = await service.delete_category(category_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(category_id)},
            message="Category deleted successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# Discounts
# =============================================================================

@price_list_router.post("/discounts", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_discount(
    request: PriceListDiscountCreate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Create a new discount."""
    try:
        discount = await service.create_discount(request)
        await service.db.commit()
        return success_response(
            PriceListDiscountResponse.model_validate(discount).model_dump(),
            message="Discount created successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/discounts", response_model=BaseResponse)
async def list_discounts(
    service: PriceListService = Depends(get_service(PriceListService))
):
    """List all active discounts."""
    try:
        discounts = await service.list_discounts()
        return success_response(
            [PriceListDiscountResponse.model_validate(d).model_dump() for d in discounts],
            message="Discounts retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/discounts/{discount_id}", response_model=BaseResponse)
async def get_discount(
    discount_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get discount by ID."""
    discount = await service.get_discount(discount_id)
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discount not found"
        )
    return success_response(
        PriceListDiscountResponse.model_validate(discount).model_dump(),
        message="Discount retrieved successfully"
    )


@price_list_router.get("/discounts/by-code/{code}", response_model=BaseResponse)
async def get_discount_by_code(
    code: str,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get discount by code."""
    discount = await service.get_discount_by_code(code)
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discount code '{code}' not found"
        )
    return success_response(
        PriceListDiscountResponse.model_validate(discount).model_dump(),
        message="Discount retrieved successfully"
    )


@price_list_router.patch("/discounts/{discount_id}", response_model=BaseResponse)
async def update_discount(
    discount_id: UUID,
    request: PriceListDiscountUpdate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Update a discount."""
    try:
        discount = await service.update_discount(discount_id, request)
        if not discount:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discount not found"
            )
        await service.db.commit()
        return success_response(
            PriceListDiscountResponse.model_validate(discount).model_dump(),
            message="Discount updated successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.delete("/discounts/{discount_id}", response_model=BaseResponse)
async def delete_discount(
    discount_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Delete a discount."""
    try:
        result = await service.delete_discount(discount_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discount not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(discount_id)},
            message="Discount deleted successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.post("/discounts/{discount_id}/use", response_model=BaseResponse)
async def use_discount(
    discount_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Use a discount (increment used_count)."""
    try:
        discount = await service.use_discount(discount_id)
        if not discount:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discount not found"
            )
        await service.db.commit()
        return success_response(
            {
                "id": str(discount.id),
                "code": discount.code,
                "used_count": discount.used_count,
                "remaining_uses": discount.remaining_uses
            },
            message="Discount used successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/discounts/validate/{code}", response_model=BaseResponse)
async def validate_discount(
    code: str,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Validate a discount code."""
    try:
        result = await service.validate_discount(code)
        return success_response(
            result,
            message="Discount validated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/discounts/applicable", response_model=BaseResponse)
async def get_applicable_discounts(
    category: Optional[str] = Query(None, description="Category"),
    item_id: Optional[UUID] = Query(None, description="Item ID"),
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get discounts applicable to a specific item or category."""
    try:
        discounts = await service.get_applicable_discounts(category, item_id)
        return success_response(
            [PriceListDiscountResponse.model_validate(d).model_dump() for d in discounts],
            message="Applicable discounts retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# Custom Prices
# =============================================================================

@price_list_router.post("/custom-prices", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_price(
    request: CustomPriceCreate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Create custom price."""
    try:
        custom_price = await service.create_custom_price(request, created_by="system")
        await service.db.commit()
        return success_response(
            CustomPriceResponse.model_validate(custom_price).model_dump(),
            message="Custom price created successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/custom-prices/{custom_price_id}", response_model=BaseResponse)
async def get_custom_price(
    custom_price_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get custom price by ID."""
    try:
        # Get from repository directly
        custom_price = await service.repo.get_custom_prices_by_id(custom_price_id)
        if not custom_price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom price not found"
            )
        return success_response(
            CustomPriceResponse.model_validate(custom_price).model_dump(),
            message="Custom price retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.get("/items/{item_id}/custom-prices", response_model=BaseResponse)
async def get_item_custom_prices(
    item_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get all custom prices for an item."""
    try:
        custom_prices = await service.get_custom_prices(item_id)
        return success_response(
            [CustomPriceResponse.model_validate(cp).model_dump() for cp in custom_prices],
            message="Custom prices retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.patch("/custom-prices/{custom_price_id}", response_model=BaseResponse)
async def update_custom_price(
    custom_price_id: UUID,
    request: CustomPriceUpdate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Update custom price."""
    try:
        custom_price = await service.update_custom_price(custom_price_id, request)
        if not custom_price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom price not found"
            )
        await service.db.commit()
        return success_response(
            CustomPriceResponse.model_validate(custom_price).model_dump(),
            message="Custom price updated successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.delete("/custom-prices/{custom_price_id}", response_model=BaseResponse)
async def delete_custom_price(
    custom_price_id: UUID,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Delete custom price."""
    try:
        result = await service.delete_custom_price(custom_price_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom price not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(custom_price_id)},
            message="Custom price deleted successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# Bulk Operations
# =============================================================================

@price_list_router.post("/items/bulk", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_price_items(
    items: List[PriceListItemCreate],
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Bulk create price list items."""
    try:
        created_items = await service.bulk_create(items)
        await service.db.commit()
        return success_response(
            {
                "count": len(created_items),
                "ids": [str(item.id) for item in created_items]
            },
            message=f"{len(created_items)} items created successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@price_list_router.post("/items/bulk-update-prices", response_model=BaseResponse)
async def bulk_update_prices(
    request: PriceListBulkUpdate,
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Bulk update prices by percentage."""
    try:
        count = await service.bulk_update_prices(request)
        await service.db.commit()
        return success_response(
            {
                "updated_count": count,
                "category": request.category,
                "percentage": request.percentage
            },
            message=f"{count} items updated successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# Statistics
# =============================================================================

@price_list_router.get("/stats", response_model=BaseResponse)
async def get_price_list_stats(
    service: PriceListService = Depends(get_service(PriceListService))
):
    """Get price list statistics."""
    try:
        stats = await service.get_stats()
        return success_response(
            stats,
            message="Statistics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )