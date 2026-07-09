# modules/inventory/__init__.py - PERBAIKAN IMPORT

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
    CreatePurchaseOrder,           # <-- TAMBAHKAN
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    PurchaseOrderReceive,
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
    # Models
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
    # Schemas - Item
    "CreateInventoryItem",
    "UpdateInventoryItem",
    "InventoryItemResponse",
    # Schemas - Material Usage
    "CreateInventoryMaterialUsage",
    "InventoryMaterialUsageResponse",
    # Schemas - Stock Movement
    "CreateInventoryStockMovement",
    "InventoryStockMovementResponse",
    "StockAdjustment",
    # Schemas - Workshop
    "ProjectWorkshopCreate",
    "ProjectWorkshopUpdate",
    "ProjectWorkshopResponse",
    # Schemas - Supplier
    "CreateSupplier",
    "UpdateSupplier",
    "SupplierResponse",
    "SupplierWithCountResponse",
    # Schemas - Purchase Order
    "CreatePurchaseOrder",          # <-- TAMBAHKAN
    "PurchaseOrderUpdate",
    "PurchaseOrderResponse",
    "PurchaseOrderReceive",
    # Schemas - Summary
    "InventorySummaryResponse",
    "StockAlertResponse",
    "StockAlertCreate",
    "StockAlertUpdate",
    "StockOpnameCreate",
    "StockOpnameUpdate",
    "StockOpnameResponse",
    "MaterialUsageSummaryResponse",
    "InventoryStatisticsResponse",
    # Repositories
    "InventoryRepository",
    "InventoryMaterialUsageRepository",
    "InventoryStockMovementRepository",
    "ProjectWorkshopJobRepository",
    "SupplierRepository",
    "PurchaseOrderRepository",
    # Service
    "InventoryService",
    # Router
    "inventory_router",
]
