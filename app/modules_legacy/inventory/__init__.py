# modules/inventory/__init__.py
"""
Inventory Module

Module untuk mengelola:
- Inventory item management (CRUD)
- Stock management (adjust, reserve, release)
- Stock movements tracking
- Material usage for projects
- Workshop jobs management
- Supplier management
- Purchase order management
- Stock alerts (auto & manual)
- Stock opname
- Inventory valuation

✅ Soft delete support
✅ Integration with Price List, Projects, Payment
✅ Stock movement audit trail
✅ Auto stock alerts
"""

from .models import (
    InventoryItem,
    InventoryMaterialUsage,
    InventoryStockMovement,
    ProjectWorkshopTask,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    StockAlert,
    StockOpname,
    InventoryValuation,
)

from .schemas import (
    # Item
    CreateInventoryItem,
    UpdateInventoryItem,
    InventoryItemResponse,
    
    # Material Usage
    CreateInventoryMaterialUsage,
    InventoryMaterialUsageResponse,
    MaterialUsageSummaryResponse,
    
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
    PurchaseOrderListResponse,
    
    # Stock Alert
    StockAlertCreate,
    StockAlertUpdate,
    StockAlertResponse,
    
    # Stock Opname
    StockOpnameCreate,
    StockOpnameUpdate,
    StockOpnameResponse,
    
    # Summary
    InventorySummaryResponse,
    InventoryStatisticsResponse,
)

from .repository import (
    InventoryRepository,
    InventoryMaterialUsageRepository,
    InventoryStockMovementRepository,
    ProjectWorkshopJobRepository,
    SupplierRepository,
    PurchaseOrderRepository,
)

from .services import InventoryService
from .router import inventory_router


__all__ = [
    # ============ Models ============
    "InventoryItem",
    "InventoryMaterialUsage",
    "InventoryStockMovement",
    "ProjectWorkshopTask",
    "Supplier",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "StockAlert",
    "StockOpname",
    "InventoryValuation",
    
    # ============ Schemas - Item ============
    "CreateInventoryItem",
    "UpdateInventoryItem",
    "InventoryItemResponse",
    
    # ============ Schemas - Material Usage ============
    "CreateInventoryMaterialUsage",
    "InventoryMaterialUsageResponse",
    "MaterialUsageSummaryResponse",
    
    # ============ Schemas - Stock Movement ============
    "CreateInventoryStockMovement",
    "InventoryStockMovementResponse",
    "StockAdjustment",
    
    # ============ Schemas - Workshop ============
    "ProjectWorkshopCreate",
    "ProjectWorkshopUpdate",
    "ProjectWorkshopResponse",
    
    # ============ Schemas - Supplier ============
    "CreateSupplier",
    "UpdateSupplier",
    "SupplierResponse",
    "SupplierWithCountResponse",
    
    # ============ Schemas - Purchase Order ============
    "CreatePurchaseOrder",
    "PurchaseOrderUpdate",
    "PurchaseOrderResponse",
    "PurchaseOrderReceive",
    "PurchaseOrderItemResponse",
    "PurchaseOrderListResponse",
    
    # ============ Schemas - Stock Alert ============
    "StockAlertCreate",
    "StockAlertUpdate",
    "StockAlertResponse",
    
    # ============ Schemas - Stock Opname ============
    "StockOpnameCreate",
    "StockOpnameUpdate",
    "StockOpnameResponse",
    
    # ============ Schemas - Summary ============
    "InventorySummaryResponse",
    "InventoryStatisticsResponse",
    
    # ============ Repositories ============
    "InventoryRepository",
    "InventoryMaterialUsageRepository",
    "InventoryStockMovementRepository",
    "ProjectWorkshopJobRepository",
    "SupplierRepository",
    "PurchaseOrderRepository",
    
    # ============ Service ============
    "InventoryService",
    
    # ============ Router ============
    "inventory_router",
]