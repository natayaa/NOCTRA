# modules/inventory/router.py
"""
Inventory Router - COMPLETE

✅ Semua endpoint untuk Inventory management
✅ Item management (CRUD)
✅ Stock management (adjust, reserve, release)
✅ Material usage (consume, get, delete)
✅ Workshop jobs (create, update, calculate cost)
✅ Suppliers (CRUD)
✅ Purchase Orders (CRUD, receive)
✅ Dashboard (KPIs, statistics, alerts)
✅ Soft delete support
✅ Error handling dengan rollback
"""

from uuid import UUID
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status, Depends, Body

from core.base import BaseResponse, PaginatedResponse
from core.dependencies import InventoryQueryParams, success_response, get_service
from core.exceptions import NotFoundError, ValidationError, BusinessError, ConflictError
from modules.inventory.schemas import (
    # Item
    CreateInventoryItem,
    UpdateInventoryItem,
    InventoryItemResponse,
    # Material Usage
    CreateInventoryMaterialUsage,
    InventoryMaterialUsageResponse,
    # Stock Movement
    CreateInventoryStockMovement,
    InventoryStockMovementResponse,
    StockAdjustment,
    # Workshop
    ProjectWorkshopCreate,
    ProjectWorkshopUpdate,
    ProjectWorkshopResponse,
    # Supplier
    CreateSupplier,
    UpdateSupplier,
    SupplierResponse,
    SupplierWithCountResponse,
    # Purchase Order
    CreatePurchaseOrder,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    PurchaseOrderReceive,
    PurchaseOrderItemResponse,
    # Summary
    InventorySummaryResponse,
    StockAlertResponse,
    StockAlertCreate,
    StockAlertUpdate,
    StockOpnameCreate,
    StockOpnameUpdate,
    StockOpnameResponse,
    MaterialUsageSummaryResponse,
    InventoryStatisticsResponse,
    PurchaseOrderListResponse,
)
from modules.inventory.services import InventoryService


inventory_router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"]
)


# =============================================================================
# ⚠️ URUTAN ROUTE PENTING!
# Route STATIS (tanpa {parameter}) HARUS di ATAS route dengan path parameter
# =============================================================================


# =============================================================================
# 1. STATIC ROUTES (tanpa path parameter) - DULUAN
# =============================================================================

@inventory_router.get("/categories", response_model=BaseResponse)
async def get_categories(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get all unique categories."""
    try:
        categories = await service.get_categories()
        return success_response(categories, message="Categories retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/dashboard/kpis", response_model=BaseResponse)
async def get_kpis(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory KPIs for dashboard."""
    try:
        data = await service.get_kpis()
        return success_response(data, message="KPIs retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/statistics", response_model=BaseResponse)
async def get_statistics(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory statistics."""
    try:
        data = await service.get_statistics()
        return success_response(data, message="Statistics retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/alerts", response_model=BaseResponse)
async def get_stock_alerts(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get stock alerts."""
    try:
        alerts = await service.get_stock_alerts()
        return success_response(alerts, message="Alerts retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.post("/alerts/check", response_model=BaseResponse)
async def check_stock_alerts(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Check stock and create alerts if needed."""
    try:
        alerts = await service.check_stock_alerts()
        await service.db.commit()
        return success_response(
            {"created": len(alerts)},
            message=f"Created {len(alerts)} alerts"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/alerts/summary", response_model=BaseResponse)
async def get_stock_alerts_summary(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get summary of stock alerts."""
    try:
        summary = await service.get_stock_alerts_summary()
        return success_response(summary, message="Alerts summary retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 2. ITEM MANAGEMENT
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
            InventoryItemResponse.model_validate(item).model_dump(),
            message=f"Item '{item.name}' created successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/items", response_model=PaginatedResponse[InventoryItemResponse])
async def list_items(
    params: InventoryQueryParams = Depends(),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """List inventory items with filters."""
    try:
        items, total = await service.list_items(
            category=params.category,
            status=params.status,
            search=params.search,
            low_stock_only=params.low_stock_only,
            include_deleted=params.include_deleted,
            limit=params.limit,
            offset=params.offset
        )

        total_pages = (total + params.limit - 1) // params.limit if total > 0 else 0

        return PaginatedResponse(
            success=True,
            message="Items retrieved successfully",
            data=[InventoryItemResponse.model_validate(item).model_dump() for item in items],
            total=total,
            page=params.page,
            page_size=params.limit,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/items/{item_id}", response_model=BaseResponse)
async def get_item(
    item_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory item by ID."""
    try:
        item = await service.get_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        return success_response(
            InventoryItemResponse.model_validate(item).model_dump(),
            message="Item retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/items/sku/{sku}", response_model=BaseResponse)
async def get_item_by_sku(
    sku: str,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory item by SKU."""
    try:
        item = await service.get_item_by_sku(sku)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        return success_response(
            InventoryItemResponse.model_validate(item).model_dump(),
            message="Item retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/items/barcode/{barcode}", response_model=BaseResponse)
async def get_item_by_barcode(
    barcode: str,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get inventory item by barcode."""
    try:
        item = await service.get_item_by_barcode(barcode)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        return success_response(
            InventoryItemResponse.model_validate(item).model_dump(),
            message="Item retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        await service.db.commit()
        return success_response(
            InventoryItemResponse.model_validate(item).model_dump(),
            message="Item updated successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.delete("/items/{item_id}", response_model=BaseResponse)
async def delete_item(
    item_id: UUID,
    permanent: bool = Query(False, description="Permanent delete (cannot be undone)"),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Delete inventory item (soft delete by default)."""
    try:
        if permanent:
            result = await service.item_repo.hard_delete(item_id)
            message = "Item permanently deleted"
        else:
            result = await service.delete_item(item_id)
            message = "Item deleted successfully"

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(item_id)},
            message=message
        )
    except BusinessError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 3. STOCK MANAGEMENT
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
            InventoryStockMovementResponse.model_validate(movement).model_dump(),
            message="Stock adjusted successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
            {
                "id": str(item.id),
                "name": item.name,
                "reserved_stock": float(item.reserved_stock),
                "available_stock": float(item.available_stock)
            },
            message="Stock reserved successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
            {
                "id": str(item.id),
                "name": item.name,
                "reserved_stock": float(item.reserved_stock),
                "available_stock": float(item.available_stock)
            },
            message="Stock released successfully")
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 4. MATERIAL USAGE
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
            InventoryMaterialUsageResponse.model_validate(usage).model_dump(),
            message="Material consumed successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/usage/project/{project_id}", response_model=BaseResponse)
async def get_project_usage(
    project_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get material usage for a project."""
    try:
        usages = await service.get_material_usages_by_project(project_id)
        return success_response(
            [InventoryMaterialUsageResponse.model_validate(u).model_dump() for u in usages],
            message="Project usage retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/usage/project/{project_id}/summary", response_model=BaseResponse)
async def get_project_usage_summary(
    project_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get material usage summary for a project."""
    try:
        summary = await service.get_project_material_usage(project_id)
        return success_response(summary, message="Usage summary retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.delete("/usage/{usage_id}", response_model=BaseResponse)
async def delete_usage(
    usage_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Delete material usage."""
    try:
        result = await service.usage_repo.delete(usage_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usage not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(usage_id)},
            message="Material usage deleted successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 5. STOCK MOVEMENTS
# =============================================================================

@inventory_router.get("/movements/recent", response_model=BaseResponse)
async def get_recent_movements(
    limit: int = Query(10, ge=1, le=50),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get recent stock movements."""
    try:
        movements = await service.get_recent_movements(limit)
        return success_response(
            [InventoryStockMovementResponse.model_validate(m).model_dump() for m in movements],
            message="Recent movements retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/movements/item/{item_id}", response_model=BaseResponse)
async def get_item_movements(
    item_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get stock movements for an item."""
    try:
        movements = await service.get_item_movements(item_id, limit)
        return success_response(
            [InventoryStockMovementResponse.model_validate(m).model_dump() for m in movements],
            message="Item movements retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/movements/report", response_model=BaseResponse)
async def get_movement_report(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    movement_type: Optional[str] = Query(None, description="Filter by movement type"),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get detailed movement report."""
    try:
        movements = await service.get_movement_report(start_date, end_date, movement_type)
        return success_response(
            [InventoryStockMovementResponse.model_validate(m).model_dump() for m in movements],
            message="Movement report retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 6. WORKSHOP JOBS
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.get("/workshop/project/{project_id}", response_model=BaseResponse)
async def get_workshop_by_project(
    project_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get workshop job by project."""
    try:
        job = await service.get_workshop_job(project_id)
        if not job:
            return success_response(None, message="No workshop job found")
        return success_response(
            ProjectWorkshopResponse.model_validate(job).model_dump(),
            message="Workshop job retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/workshop/{job_id}", response_model=BaseResponse)
async def get_workshop_job(
    job_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get workshop job by ID."""
    try:
        job = await service.get_workshop_job_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workshop job not found"
            )
        return success_response(
            ProjectWorkshopResponse.model_validate(job).model_dump(),
            message="Workshop job retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.patch("/workshop/{job_id}", response_model=BaseResponse)
async def update_workshop_job(
    job_id: UUID,
    request: ProjectWorkshopUpdate,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Update workshop job."""
    try:
        job = await service.update_workshop_job_status(job_id, request.status, request.notes)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workshop job not found"
            )
        await service.db.commit()
        return success_response(
            ProjectWorkshopResponse.model_validate(job).model_dump(),
            message="Workshop job updated successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 7. SUPPLIERS
# =============================================================================

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
            SupplierResponse.model_validate(supplier).model_dump(),
            message="Supplier created successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@inventory_router.get("/suppliers", response_model=BaseResponse)
async def list_suppliers(
    active_only: bool = Query(True, description="Only active suppliers"),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """List all suppliers."""
    try:
        suppliers = await service.list_suppliers(active_only)
        return success_response(
            [SupplierResponse.model_validate(s).model_dump() for s in suppliers],
            message="Suppliers retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/suppliers/with-counts", response_model=BaseResponse)
async def list_suppliers_with_counts(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """List suppliers with item counts."""
    try:
        suppliers = await service.list_suppliers_with_count()
        return success_response(suppliers, message="Suppliers with counts retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/suppliers/{supplier_id}", response_model=BaseResponse)
async def get_supplier(
    supplier_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get supplier by ID."""
    try:
        supplier = await service.get_supplier(supplier_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found"
            )
        return success_response(
            SupplierResponse.model_validate(supplier).model_dump(),
            message="Supplier retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.patch("/suppliers/{supplier_id}", response_model=BaseResponse)
async def update_supplier(
    supplier_id: UUID,
    request: UpdateSupplier,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Update supplier."""
    try:
        supplier = await service.update_supplier(supplier_id, request)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found"
            )
        await service.db.commit()
        return success_response(
            SupplierResponse.model_validate(supplier).model_dump(),
            message="Supplier updated successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# 8. PURCHASE ORDERS
# =============================================================================

@inventory_router.post("/purchase-orders", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    request: CreatePurchaseOrder,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Create a new purchase order."""
    try:
        po = await service.create_purchase_order(request)
        await service.db.commit()
        return success_response(
            PurchaseOrderResponse.model_validate(po).model_dump(),
            message=f"Purchase order {po.po_number} created successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@inventory_router.get("/purchase-orders/generate-number", response_model=BaseResponse)
async def generate_po_number(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Generate a unique PO number."""
    try:
        number = await service.generate_po_number()
        return success_response(
            {"po_number": number},
            message="PO number generated"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/purchase-orders", response_model=BaseResponse)
async def list_purchase_orders(
    supplier_id: Optional[UUID] = Query(None, description="Filter by supplier"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """List purchase orders."""
    try:
        if supplier_id:
            pos = await service.list_purchase_orders_by_supplier(supplier_id, status, limit)
        else:
            pos = await service.po_repo.get_all(limit=limit)
        return success_response(
            [PurchaseOrderResponse.model_validate(po).model_dump() for po in pos],
            message="Purchase orders retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/purchase-orders/{po_id}", response_model=BaseResponse)
async def get_purchase_order(
    po_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get purchase order by ID."""
    try:
        po = await service.get_purchase_order(po_id)
        if not po:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase order not found"
            )
        return success_response(
            PurchaseOrderResponse.model_validate(po).model_dump(),
            message="Purchase order retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/purchase-orders/number/{po_number}", response_model=BaseResponse)
async def get_purchase_order_by_number(
    po_number: str,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get purchase order by PO number."""
    try:
        po = await service.get_purchase_order_by_number(po_number)
        if not po:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase order not found"
            )
        return success_response(
            PurchaseOrderResponse.model_validate(po).model_dump(),
            message="Purchase order retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase order not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(po.id), "status": po.status},
            message="Purchase order updated successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase order not found"
            )
        await service.db.commit()
        return success_response(
            PurchaseOrderResponse.model_validate(po).model_dump(),
            message=f"Purchase order {po.po_number} received successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BusinessError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 9. STOCK OPNAME
# =============================================================================

@inventory_router.post("/opname", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_opname(
    request: StockOpnameCreate,
    performed_by: str = Body("system", embed=True),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Create stock opname."""
    try:
        opname = await service.create_opname(request, performed_by)
        await service.db.commit()
        return success_response(
            StockOpnameResponse.model_validate(opname).model_dump(),
            message="Stock opname created successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/opname/item/{item_id}", response_model=BaseResponse)
async def get_opnames(
    item_id: UUID,
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get all opnames for an item."""
    try:
        opnames = await service.get_opnames(item_id)
        return success_response(
            [StockOpnameResponse.model_validate(o).model_dump() for o in opnames],
            message="Opnames retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.post("/opname/{opname_id}/approve", response_model=BaseResponse)
async def approve_opname(
    opname_id: UUID,
    approved_by: str = Body(..., embed=True),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Approve stock opname."""
    try:
        opname = await service.approve_opname(opname_id, approved_by)
        if not opname:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opname not found"
            )
        await service.db.commit()
        return success_response(
            StockOpnameResponse.model_validate(opname).model_dump(),
            message="Stock opname approved successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 10. STOCK ALERT CRUD
# =============================================================================

@inventory_router.get("/alerts/active", response_model=BaseResponse)
async def get_active_alerts(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get all active stock alerts."""
    try:
        alerts = await service.get_active_alerts()
        return success_response(
            [StockAlertResponse.model_validate(a).model_dump() for a in alerts],
            message="Active alerts retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.get("/alerts/critical", response_model=BaseResponse)
async def get_critical_alerts(
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Get critical stock alerts."""
    try:
        alerts = await service.get_critical_alerts()
        return success_response(
            [StockAlertResponse.model_validate(a).model_dump() for a in alerts],
            message="Critical alerts retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@inventory_router.post("/alerts/{alert_id}/resolve", response_model=BaseResponse)
async def resolve_alert(
    alert_id: UUID,
    resolved_by: str = Body("system", embed=True),
    resolution_note: Optional[str] = Body(None, embed=True),
    service: InventoryService = Depends(get_service(InventoryService))
):
    """Resolve stock alert."""
    try:
        alert = await service.resolve_alert(alert_id, resolved_by, resolution_note)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        await service.db.commit()
        return success_response(
            StockAlertResponse.model_validate(alert).model_dump(),
            message="Alert resolved successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))