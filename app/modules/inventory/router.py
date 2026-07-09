# modules/inventory/router.py
from uuid import UUID
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status, Depends, Body

from core.base import BaseResponse, PaginatedResponse
from core.dependencies import InventoryQueryParams, success_response, get_service
from core.exceptions import NotFoundError, ValidationError, BusinessError, ConflictError
from modules.inventory.schemas import (
    CreateInventoryItem,
    UpdateInventoryItem,
    InventoryItemResponse,
    CreateInventoryMaterialUsage,
    CreateInventoryStockMovement,
    InventoryStockMovementResponse,
    InventoryMaterialUsageResponse,
    ProjectWorkshopCreate,
    ProjectWorkshopUpdate,
    ProjectWorkshopResponse,
    CreateSupplier,
    UpdateSupplier,
    SupplierResponse,
    SupplierWithCountResponse,
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    PurchaseOrderReceive,
    InventorySummaryResponse,
    StockAlertResponse,
    StockAdjustment,
    MaterialUsageSummaryResponse,
)
from modules.inventory.services import InventoryService


inventory_router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"]
)


# =============================================================================
# Item Management
# =============================================================================

@inventory_router.post("/items", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    request: CreateInventoryItem,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Create a new inventory item."""
    try:
        item = await service.create_item(request)
        await service.db.commit()
        return success_response(
            {"id": str(item.id)},
            message="Item created successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.get("/items", response_model=PaginatedResponse[InventoryItemResponse])
async def list_items(
    params: InventoryQueryParams = Depends(),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """List inventory items with filters."""
    items, total = await service.list_items(
        category=params.category,
        status=params.status,
        search=params.search,
        low_stock_only=params.low_stock_only,
        limit=params.limit,
        offset=params.offset
    )

    return PaginatedResponse.from_paginated(
        items=[InventoryItemResponse.model_validate(
            item).model_dump() for item in items],
        total=total,
        page=params.page,
        page_size=params.limit,
        message="Items retrieved successfully"
    )


@inventory_router.get("/items/{item_id}", response_model=BaseResponse)
async def get_item(
    item_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory item by ID."""
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    return success_response(
        InventoryItemResponse.model_validate(item).model_dump(),
        message="Item retrieved successfully"
    )


@inventory_router.get("/items/sku/{sku}", response_model=BaseResponse)
async def get_item_by_sku(
    sku: str,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory item by SKU."""
    item = await service.get_item_by_sku(sku)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return success_response(
        InventoryItemResponse.model_validate(item).model_dump(),
        message="Item retrieved successfully"
    )


@inventory_router.patch("/items/{item_id}", response_model=BaseResponse)
async def update_item(
    item_id: UUID,
    request: UpdateInventoryItem,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Update inventory item."""
    try:
        item = await service.update_item(item_id, request)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        await service.db.commit()
        return success_response(
            {"id": str(item.id)},
            message="Item updated successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.delete("/items/{item_id}", response_model=BaseResponse)
async def delete_item(
    item_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Soft delete inventory item."""
    try:
        deleted = await service.delete_item(item_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        await service.db.commit()
        return success_response(
            {"id": str(item_id)},
            message="Item deleted successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.get("/categories", response_model=BaseResponse)
async def get_categories(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get all unique categories."""
    categories = await service.get_categories()
    return success_response(categories, message="Categories retrieved successfully")


# =============================================================================
# Stock Management
# =============================================================================

@inventory_router.post("/stock/adjust", response_model=BaseResponse)
async def adjust_stock(
    request: StockAdjustment,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Adjust stock."""
    try:
        movement = await service.adjust_stock(
            item_id=request.item_id,
            quantity=request.quantity,
            movement_type=request.movement_type,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            note=request.note,
            performed_by=request.performed_by
        )
        await service.db.commit()
        return success_response(
            {"id": str(movement.id)},
            message="Stock adjusted successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.post("/stock/reserve", response_model=BaseResponse)
async def reserve_stock(
    item_id: UUID = Body(..., embed=True),
    quantity: Decimal = Body(..., embed=True),
    reference_type: str = Body(..., embed=True),
    reference_id: UUID = Body(..., embed=True),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Reserve stock for a project or job."""
    try:
        item = await service.reserve_stock(
            item_id=item_id,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id
        )
        await service.db.commit()
        return success_response(
            {"id": str(item.id), "reserved_stock": float(item.reserved_stock)},
            message="Stock reserved successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.post("/stock/release", response_model=BaseResponse)
async def release_reserved_stock(
    item_id: UUID = Body(..., embed=True),
    quantity: Decimal = Body(..., embed=True),
    reference_type: str = Body(..., embed=True),
    reference_id: UUID = Body(..., embed=True),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Release reserved stock."""
    try:
        item = await service.release_reserved_stock(
            item_id=item_id,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id
        )
        await service.db.commit()
        return success_response(
            {"id": str(item.id), "reserved_stock": float(item.reserved_stock)},
            message="Stock released successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Stock Movements
# =============================================================================

@inventory_router.get("/movements/recent", response_model=BaseResponse)
async def get_recent_movements(
    limit: int = Query(10, ge=1, le=50),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get recent stock movements."""
    movements = await service.get_recent_movements(limit)
    return success_response([
        InventoryStockMovementResponse.model_validate(m).model_dump()
        for m in movements
    ], message="Recent movements retrieved successfully")


@inventory_router.get("/movements/item/{item_id}", response_model=BaseResponse)
async def get_item_movements(
    item_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get stock movements for an item."""
    movements = await service.get_item_movements(item_id, limit)
    return success_response([
        InventoryStockMovementResponse.model_validate(m).model_dump()
        for m in movements
    ], message="Item movements retrieved successfully")


@inventory_router.get("/movements/report", response_model=BaseResponse)
async def get_movement_report(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    movement_type: Optional[str] = Query(
        None, description="Filter by movement type"),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get detailed movement report."""
    movements = await service.get_movement_report(start_date, end_date, movement_type)
    return success_response([
        InventoryStockMovementResponse.model_validate(m).model_dump()
        for m in movements
    ], message="Movement report retrieved successfully")


# =============================================================================
# Material Usage
# =============================================================================

@inventory_router.post("/usage", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def consume_material(
    request: CreateInventoryMaterialUsage,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Consume material for a project."""
    try:
        usage = await service.consume_material(
            project_id=request.project_id,
            item_id=request.item_id,
            quantity=request.quantity,
            note=request.note,
            job_id=request.job_id,
            is_waste=request.is_waste,
            confirmed_by=request.confirmed_by
        )
        await service.db.commit()
        return success_response(
            {"id": str(usage.id)},
            message="Material consumed successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.get("/usage/project/{project_id}", response_model=BaseResponse)
async def get_project_usage(
    project_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get material usage for a project."""
    usages = await service.usage_repo.get_by_project(project_id)
    return success_response([
        InventoryMaterialUsageResponse.model_validate(u).model_dump()
        for u in usages
    ], message="Project usage retrieved successfully")


@inventory_router.get("/usage/project/{project_id}/summary", response_model=BaseResponse)
async def get_project_usage_summary(
    project_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get material usage summary for a project."""
    summary = await service.get_project_material_usage(project_id)
    return success_response(summary, message="Usage summary retrieved successfully")


@inventory_router.delete("/usage/{usage_id}", response_model=BaseResponse)
async def delete_usage(
    usage_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Delete material usage."""
    try:
        deleted = await service.usage_repo.delete(usage_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usage not found")
        await service.db.commit()
        return success_response(
            {"id": str(usage_id)},
            message="Material usage deleted successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Workshop Jobs
# =============================================================================

@inventory_router.post("/workshop", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_workshop_job(
    request: ProjectWorkshopCreate,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Create workshop job."""
    try:
        job = await service.workshop_repo.create(request.model_dump())
        await service.db.commit()
        return success_response(
            {"id": str(job.id)},
            message="Workshop job created successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.get("/workshop/project/{project_id}", response_model=BaseResponse)
async def get_workshop_by_project(
    project_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get workshop job by project."""
    job = await service.get_workshop_job(project_id)
    if not job:
        return success_response(None, message="No workshop job found")

    return success_response(
        ProjectWorkshopResponse.model_validate(job).model_dump(),
        message="Workshop job retrieved successfully"
    )


@inventory_router.patch("/workshop/{job_id}", response_model=BaseResponse)
async def update_workshop_job(
    job_id: UUID,
    request: ProjectWorkshopUpdate,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Update workshop job."""
    try:
        job = await service.workshop_repo.update(job_id, request.model_dump(exclude_unset=True))
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Workshop job not found")
        await service.db.commit()
        return success_response(
            {"id": str(job.id)},
            message="Workshop job updated successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.post("/workshop/{job_id}/calculate-cost", response_model=BaseResponse)
async def calculate_workshop_cost(
    job_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Calculate total cost for a workshop job."""
    try:
        cost = await service.calculate_workshop_cost(job_id)
        await service.db.commit()
        return success_response(
            {"job_id": str(job_id), "total_cost": float(cost)},
            message="Cost calculated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Suppliers
# =============================================================================

@inventory_router.get("/suppliers", response_model=BaseResponse)
async def list_suppliers(
    active_only: bool = Query(True, description="Only active suppliers"),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """List all suppliers."""
    suppliers = await service.list_suppliers(active_only)
    return success_response([
        SupplierResponse.model_validate(s).model_dump() for s in suppliers
    ], message="Suppliers retrieved successfully")


@inventory_router.get("/suppliers/with-counts", response_model=BaseResponse)
async def list_suppliers_with_counts(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """List suppliers with item counts."""
    suppliers = await service.list_suppliers_with_count()
    return success_response(suppliers, message="Suppliers with counts retrieved successfully")


@inventory_router.post("/suppliers", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    request: CreateSupplier,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Create a new supplier."""
    try:
        supplier = await service.create_supplier(request)
        await service.db.commit()
        return success_response(
            {"id": str(supplier.id)},
            message="Supplier created successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.get("/suppliers/{supplier_id}", response_model=BaseResponse)
async def get_supplier(
    supplier_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get supplier by ID."""
    supplier = await service.get_supplier(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return success_response(
        SupplierResponse.model_validate(supplier).model_dump(),
        message="Supplier retrieved successfully"
    )


@inventory_router.patch("/suppliers/{supplier_id}", response_model=BaseResponse)
async def update_supplier(
    supplier_id: UUID,
    request: UpdateSupplier,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Update supplier."""
    try:
        supplier = await service.supplier_repo.update(supplier_id, request.model_dump(exclude_unset=True))
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
        await service.db.commit()
        return success_response(
            {"id": str(supplier.id)},
            message="Supplier updated successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Purchase Orders
# =============================================================================

@inventory_router.post("/purchase-orders", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    request: PurchaseOrderCreate,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Create a new purchase order."""
    try:
        po = await service.create_purchase_order(request)
        await service.db.commit()
        return success_response(
            {"id": str(po.id), "po_number": po.po_number},
            message="Purchase order created successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.get("/purchase-orders/generate-number", response_model=BaseResponse)
async def generate_po_number(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Generate a unique PO number."""
    number = await service.generate_po_number()
    return success_response(
        {"po_number": number},
        message="PO number generated"
    )


@inventory_router.get("/purchase-orders/{po_id}", response_model=BaseResponse)
async def get_purchase_order(
    po_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get purchase order by ID."""
    po = await service.get_purchase_order(po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Purchase order not found")
    return success_response(
        PurchaseOrderResponse.model_validate(po).model_dump(),
        message="Purchase order retrieved successfully"
    )


@inventory_router.get("/purchase-orders/number/{po_number}", response_model=BaseResponse)
async def get_purchase_order_by_number(
    po_number: str,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get purchase order by PO number."""
    po = await service.get_purchase_order_by_number(po_number)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Purchase order not found")
    return success_response(
        PurchaseOrderResponse.model_validate(po).model_dump(),
        message="Purchase order retrieved successfully"
    )


@inventory_router.patch("/purchase-orders/{po_id}", response_model=BaseResponse)
async def update_purchase_order(
    po_id: UUID,
    request: PurchaseOrderUpdate,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Update purchase order."""
    try:
        po = await service.update_purchase_order_status(po_id, request.status, request.notes)
        if not po:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
        await service.db.commit()
        return success_response(
            {"id": str(po.id), "status": po.status},
            message="Purchase order updated successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.post("/purchase-orders/{po_id}/receive", response_model=BaseResponse)
async def receive_purchase_order(
    po_id: UUID,
    request: PurchaseOrderReceive,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Receive items in a purchase order."""
    try:
        po = await service.receive_purchase_order(
            po_id,
            request.received_items,
            request.received_by
        )
        if not po:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
        await service.db.commit()
        return success_response(
            {"id": str(po.id), "status": po.status},
            message="Purchase order received successfully"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Dashboard & Alerts
# =============================================================================

@inventory_router.get("/dashboard/kpis", response_model=BaseResponse)
async def get_kpis(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory KPIs for dashboard."""
    data = await service.get_kpis()
    return success_response(data, message="KPIs retrieved successfully")


@inventory_router.get("/statistics", response_model=BaseResponse)
async def get_statistics(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory statistics."""
    data = await service.get_statistics()
    return success_response(data, message="Statistics retrieved successfully")


@inventory_router.get("/alerts", response_model=BaseResponse)
async def get_stock_alerts(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get stock alerts."""
    alerts = await service.get_stock_alerts()
    return success_response(alerts, message="Alerts retrieved successfully")
