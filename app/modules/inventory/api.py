"""REST endpoints for the inventory module."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.inventory.constants import (
    MATERIAL_CATEGORIES,
    MATERIAL_CATEGORY_LABELS,
    PURCHASE_ORDER_STATUSES,
    PURCHASE_ORDER_STATUS_LABELS,
    TRANSACTION_TYPES,
    TRANSACTION_TYPE_LABELS,
    UNITS,
)
from app.modules.inventory.repository import (
    InventoryTransactionRepository,
    MaterialRepository,
    PurchaseOrderRepository,
    SupplierRepository,
)
from app.modules.inventory.schemas import (
    InventoryCatalog,
    InventoryTransactionCreate,
    InventoryTransactionOut,
    MaterialCreate,
    MaterialDetail,
    MaterialListItem,
    MaterialUpdate,
    MaterialUpdatePrice,
    MaterialWithStock,
    PurchaseOrderCreate,
    PurchaseOrderDetail,
    PurchaseOrderItemCreate,
    PurchaseOrderItemOut,
    PurchaseOrderItemUpdate,
    PurchaseOrderListItem,
    PurchaseOrderReceive,
    PurchaseOrderUpdate,
    SupplierCreate,
    SupplierDetail,
    SupplierListItem,
    SupplierUpdate,
)
from app.modules.inventory.service import (
    InventoryService,
    MaterialService,
    PurchaseOrderService,
    SupplierService,
)

suppliers_router = APIRouter(prefix="/suppliers", tags=["suppliers"])
materials_router = APIRouter(prefix="/materials", tags=["materials"])
inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])
purchase_orders_router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


# ════════════════════════════════════════════════════════════════
# CATALOG
# ════════════════════════════════════════════════════════════════

@inventory_router.get("/catalog", response_model=InventoryCatalog)
async def inventory_catalog() -> InventoryCatalog:
    return InventoryCatalog(
        material_categories=MATERIAL_CATEGORIES,
        material_category_labels=MATERIAL_CATEGORY_LABELS,
        units=UNITS,
        transaction_types=TRANSACTION_TYPES,
        transaction_type_labels=TRANSACTION_TYPE_LABELS,
        purchase_order_statuses=PURCHASE_ORDER_STATUSES,
        purchase_order_status_labels=PURCHASE_ORDER_STATUS_LABELS,
    )


# ════════════════════════════════════════════════════════════════
# SUPPLIERS
# ════════════════════════════════════════════════════════════════

@suppliers_router.get("", response_model=Page[SupplierListItem])
async def list_suppliers(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    is_active: bool | None = Query(None),
    _=Depends(require_permission(PermissionCode.SUPPLIER_READ)),
) -> Page[SupplierListItem]:
    stmt = SupplierRepository(db).query(q=q, is_active=is_active)
    rows, meta = await paginate(db, stmt, params)
    return Page[SupplierListItem](
        items=[SupplierListItem.model_validate(r) for r in rows], meta=meta
    )


@suppliers_router.post("", response_model=SupplierDetail, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.SUPPLIER_WRITE)),
) -> SupplierDetail:
    supplier = await SupplierService(db).create(payload, actor=actor)
    return SupplierDetail.model_validate(supplier)


@suppliers_router.get("/{supplier_id}", response_model=SupplierDetail)
async def get_supplier(
    supplier_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.SUPPLIER_READ)),
) -> SupplierDetail:
    supplier = await SupplierRepository(db).get(supplier_id)
    if not supplier:
        raise NotFoundError("Supplier not found")
    return SupplierDetail.model_validate(supplier)


@suppliers_router.patch("/{supplier_id}", response_model=SupplierDetail)
async def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.SUPPLIER_WRITE)),
) -> SupplierDetail:
    supplier = await SupplierService(db).update(supplier_id, payload, actor=actor)
    return SupplierDetail.model_validate(supplier)


# ════════════════════════════════════════════════════════════════
# MATERIALS
# ════════════════════════════════════════════════════════════════

@materials_router.get("", response_model=Page[MaterialListItem])
async def list_materials(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None),
    is_active: bool | None = Query(True),
    _=Depends(require_permission(PermissionCode.INVENTORY_READ)),
) -> Page[MaterialListItem]:
    stmt = MaterialRepository(db).query(q=q, category=category, is_active=is_active)
    rows, meta = await paginate(db, stmt, params)
    return Page[MaterialListItem](
        items=[MaterialListItem.model_validate(r) for r in rows], meta=meta
    )


@materials_router.post("", response_model=MaterialDetail, status_code=status.HTTP_201_CREATED)
async def create_material(
    payload: MaterialCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_WRITE)),
) -> MaterialDetail:
    material = await MaterialService(db).create(payload, actor=actor)
    return MaterialDetail.model_validate(material)


@materials_router.get("/{material_id}", response_model=MaterialWithStock)
async def get_material(
    material_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.INVENTORY_READ)),
) -> MaterialWithStock:
    repo = MaterialRepository(db)
    material = await repo.get(material_id)
    if not material:
        raise NotFoundError("Material not found")

    stock = await repo.current_stock(material_id)
    detail = MaterialWithStock.model_validate(material)
    detail.current_stock = stock
    detail.cost_per_stock_unit = material.cost_per_stock_unit
    detail.stock_value = stock * material.cost_per_stock_unit
    return detail


@materials_router.patch("/{material_id}", response_model=MaterialDetail)
async def update_material(
    material_id: UUID,
    payload: MaterialUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_WRITE)),
) -> MaterialDetail:
    material = await MaterialService(db).update(material_id, payload, actor=actor)
    return MaterialDetail.model_validate(material)


@materials_router.post("/{material_id}/price", response_model=MaterialDetail)
async def update_material_price(
    material_id: UUID,
    payload: MaterialUpdatePrice,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_WRITE)),
) -> MaterialDetail:
    material = await MaterialService(db).update_price(
        material_id, payload.new_purchase_price, note=payload.note, actor=actor
    )
    return MaterialDetail.model_validate(material)


@materials_router.get("/{material_id}/transactions", response_model=Page[InventoryTransactionOut])
async def list_material_transactions(
    material_id: UUID,
    db: DbSession,
    params: PageParams = Depends(page_params),
    transaction_type: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.INVENTORY_READ)),
) -> Page[InventoryTransactionOut]:
    stmt = InventoryTransactionRepository(db).query(
        material_id=material_id, transaction_type=transaction_type,
    )
    rows, meta = await paginate(db, stmt, params)
    return Page[InventoryTransactionOut](
        items=[InventoryTransactionOut.model_validate(r) for r in rows], meta=meta
    )


# ════════════════════════════════════════════════════════════════
# INVENTORY — overview + transactions
# ════════════════════════════════════════════════════════════════

@inventory_router.get("/overview")
async def inventory_overview(
    db: DbSession,
    _=Depends(require_permission(PermissionCode.INVENTORY_READ)),
) -> dict:
    rows = await InventoryService(db).stock_overview()
    return {
        "items": [
            {
                "material_id": str(r["material"].id),
                "code": r["material"].code,
                "name": r["material"].name,
                "category": r["material"].category,
                "stock_unit": r["material"].stock_unit,
                "current_stock": r["current_stock"],
                "cost_per_stock_unit": r["cost_per_stock_unit"],
                "stock_value": r["stock_value"],
                "below_reorder": r["below_reorder"],
                "below_min": r["below_min"],
            }
            for r in rows
        ],
        "total_value": sum(r["stock_value"] for r in rows),
        "low_stock_count": sum(1 for r in rows if r["below_reorder"]),
    }


@inventory_router.get("/transactions", response_model=Page[InventoryTransactionOut])
async def list_transactions(
    db: DbSession,
    params: PageParams = Depends(page_params),
    material_id: UUID | None = Query(None),
    transaction_type: str | None = Query(None),
    reference_type: str | None = Query(None),
    reference_id: UUID | None = Query(None),
    since: datetime | None = Query(None),
    _=Depends(require_permission(PermissionCode.INVENTORY_READ)),
) -> Page[InventoryTransactionOut]:
    stmt = InventoryTransactionRepository(db).query(
        material_id=material_id,
        transaction_type=transaction_type,
        reference_type=reference_type,
        reference_id=reference_id,
        since=since,
    )
    rows, meta = await paginate(db, stmt, params)
    return Page[InventoryTransactionOut](
        items=[InventoryTransactionOut.model_validate(r) for r in rows], meta=meta
    )


@inventory_router.post(
    "/transactions",
    response_model=InventoryTransactionOut,
    status_code=status.HTTP_201_CREATED,
)
async def record_transaction(
    payload: InventoryTransactionCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_TRANSACT)),
) -> InventoryTransactionOut:
    tx = await InventoryService(db).record(payload, actor=actor)
    return InventoryTransactionOut.model_validate(tx)


# ════════════════════════════════════════════════════════════════
# PURCHASE ORDERS
# ════════════════════════════════════════════════════════════════

@purchase_orders_router.get("", response_model=Page[PurchaseOrderListItem])
async def list_purchase_orders(
    db: DbSession,
    params: PageParams = Depends(page_params),
    status_: str | None = Query(None, alias="status"),
    supplier_id: UUID | None = Query(None),
    _=Depends(require_permission(PermissionCode.INVENTORY_READ)),
) -> Page[PurchaseOrderListItem]:
    stmt = PurchaseOrderRepository(db).query(status=status_, supplier_id=supplier_id)
    rows, meta = await paginate(db, stmt, params)
    return Page[PurchaseOrderListItem](
        items=[PurchaseOrderListItem.model_validate(r) for r in rows], meta=meta
    )


@purchase_orders_router.post(
    "", response_model=PurchaseOrderDetail, status_code=status.HTTP_201_CREATED
)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> PurchaseOrderDetail:
    po = await PurchaseOrderService(db).create(payload, actor=actor)
    return PurchaseOrderDetail.model_validate(po)


@purchase_orders_router.get("/{po_id}", response_model=PurchaseOrderDetail)
async def get_purchase_order(
    po_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.INVENTORY_READ)),
) -> PurchaseOrderDetail:
    po = await PurchaseOrderRepository(db).get(po_id)
    if not po:
        raise NotFoundError("Purchase order not found")
    detail = PurchaseOrderDetail.model_validate(po)
    detail.items = [PurchaseOrderItemOut.model_validate(i) for i in po.items]
    return detail


@purchase_orders_router.patch("/{po_id}", response_model=PurchaseOrderDetail)
async def update_purchase_order(
    po_id: UUID,
    payload: PurchaseOrderUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> PurchaseOrderDetail:
    po = await PurchaseOrderService(db).update(po_id, payload, actor=actor)
    return PurchaseOrderDetail.model_validate(po)


@purchase_orders_router.post(
    "/{po_id}/items",
    response_model=PurchaseOrderItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_purchase_order_item(
    po_id: UUID,
    payload: PurchaseOrderItemCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> PurchaseOrderItemOut:
    item = await PurchaseOrderService(db).add_item(po_id, payload, actor=actor)
    return PurchaseOrderItemOut.model_validate(item)


@purchase_orders_router.patch(
    "/{po_id}/items/{item_id}",
    response_model=PurchaseOrderItemOut,
)
async def update_purchase_order_item(
    po_id: UUID,
    item_id: UUID,
    payload: PurchaseOrderItemUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> PurchaseOrderItemOut:
    item = await PurchaseOrderService(db).update_item(po_id, item_id, payload, actor=actor)
    return PurchaseOrderItemOut.model_validate(item)


@purchase_orders_router.delete(
    "/{po_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_purchase_order_item(
    po_id: UUID,
    item_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> None:
    await PurchaseOrderService(db).delete_item(po_id, item_id, actor=actor)


@purchase_orders_router.post("/{po_id}/send", response_model=PurchaseOrderDetail)
async def send_purchase_order(
    po_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> PurchaseOrderDetail:
    po = await PurchaseOrderService(db).send(po_id, actor=actor)
    return PurchaseOrderDetail.model_validate(po)


@purchase_orders_router.post("/{po_id}/receive", response_model=PurchaseOrderDetail)
async def receive_purchase_order(
    po_id: UUID,
    payload: PurchaseOrderReceive,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> PurchaseOrderDetail:
    po = await PurchaseOrderService(db).receive(po_id, payload, actor=actor)
    detail = PurchaseOrderDetail.model_validate(po)
    detail.items = [PurchaseOrderItemOut.model_validate(i) for i in po.items]
    return detail


@purchase_orders_router.post("/{po_id}/close", response_model=PurchaseOrderDetail)
async def close_purchase_order(
    po_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> PurchaseOrderDetail:
    po = await PurchaseOrderService(db).close(po_id, actor=actor)
    return PurchaseOrderDetail.model_validate(po)


@purchase_orders_router.post("/{po_id}/cancel", response_model=PurchaseOrderDetail)
async def cancel_purchase_order(
    po_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVENTORY_PURCHASE)),
) -> PurchaseOrderDetail:
    po = await PurchaseOrderService(db).cancel(po_id, actor=actor)
    return PurchaseOrderDetail.model_validate(po)