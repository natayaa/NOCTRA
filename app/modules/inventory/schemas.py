"""Pydantic schemas for the inventory module."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.inventory.constants import (
    MATERIAL_CATEGORIES,
    PURCHASE_ORDER_STATUSES,
    TRANSACTION_TYPES,
    UNITS,
)


# ════════════════════════════════════════════════════════════════
# SUPPLIERS
# ════════════════════════════════════════════════════════════════

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    contact_person: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=32)
    address: str | None = None
    tax_id: str | None = Field(None, max_length=64)
    payment_terms: str | None = Field(None, max_length=64)
    notes: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    payment_terms: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class SupplierListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    contact_person: str | None
    phone: str | None
    email: str | None
    is_active: bool


class SupplierDetail(SupplierListItem):
    address: str | None
    tax_id: str | None
    payment_terms: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# ════════════════════════════════════════════════════════════════
# MATERIALS
# ════════════════════════════════════════════════════════════════

class MaterialCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    sku: str | None = Field(None, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    brand: str | None = Field(None, max_length=100)
    category: str

    purchase_unit: str
    stock_unit: str
    stock_units_per_purchase: float = Field(..., gt=0)
    current_purchase_price: float = Field(0, ge=0)

    reorder_point: float = Field(0, ge=0)
    min_stock: float = Field(0, ge=0)

    preferred_supplier_id: UUID | None = None
    notes: str | None = None
    location: str | None = Field(None, max_length=64)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        if v not in MATERIAL_CATEGORIES:
            raise ValueError(f"category must be one of {MATERIAL_CATEGORIES}")
        return v

    @field_validator("purchase_unit", "stock_unit")
    @classmethod
    def _validate_unit(cls, v):
        if v not in UNITS:
            raise ValueError(f"unit must be one of {UNITS}")
        return v


class MaterialUpdate(BaseModel):
    sku: str | None = None
    name: str | None = Field(None, min_length=2, max_length=255)
    brand: str | None = None
    category: str | None = None
    purchase_unit: str | None = None
    stock_unit: str | None = None
    stock_units_per_purchase: float | None = Field(None, gt=0)
    reorder_point: float | None = Field(None, ge=0)
    min_stock: float | None = Field(None, ge=0)
    preferred_supplier_id: UUID | None = None
    notes: str | None = None
    location: str | None = None
    is_active: bool | None = None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v):
        if v is not None and v not in MATERIAL_CATEGORIES:
            raise ValueError(f"category must be one of {MATERIAL_CATEGORIES}")
        return v

    @field_validator("purchase_unit", "stock_unit")
    @classmethod
    def _validate_unit(cls, v):
        if v is not None and v not in UNITS:
            raise ValueError(f"unit must be one of {UNITS}")
        return v


class MaterialListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    brand: str | None
    category: str
    purchase_unit: str
    stock_unit: str
    stock_units_per_purchase: float
    current_purchase_price: float
    reorder_point: float
    min_stock: float
    location: str | None
    is_active: bool


class MaterialDetail(MaterialListItem):
    sku: str | None
    preferred_supplier_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MaterialWithStock(MaterialDetail):
    current_stock: float = 0.0
    cost_per_stock_unit: float = 0.0
    stock_value: float = 0.0


class MaterialUpdatePrice(BaseModel):
    """Record a price change; also updates the material's current price."""
    new_purchase_price: float = Field(..., ge=0)
    note: str | None = None


# ════════════════════════════════════════════════════════════════
# INVENTORY TRANSACTIONS
# ════════════════════════════════════════════════════════════════

class InventoryTransactionCreate(BaseModel):
    material_id: UUID
    transaction_type: str
    quantity: float = Field(..., gt=0)
    unit_cost: float | None = Field(None, ge=0)
    reference_type: str | None = None
    reference_id: UUID | None = None
    reference_note: str | None = Field(None, max_length=255)
    notes: str | None = None

    @field_validator("transaction_type")
    @classmethod
    def _validate_type(cls, v):
        if v not in TRANSACTION_TYPES:
            raise ValueError(f"transaction_type must be one of {TRANSACTION_TYPES}")
        return v


class InventoryTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    material_id: UUID
    transaction_type: str
    quantity: float
    unit_cost: float | None
    reference_type: str | None
    reference_id: UUID | None
    reference_note: str | None
    notes: str | None
    created_by_id: UUID | None
    created_at: datetime


# ════════════════════════════════════════════════════════════════
# PURCHASE ORDERS
# ════════════════════════════════════════════════════════════════

class PurchaseOrderItemCreate(BaseModel):
    material_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    notes: str | None = None


class PurchaseOrderItemUpdate(BaseModel):
    quantity: float | None = Field(None, gt=0)
    unit_price: float | None = Field(None, ge=0)
    notes: str | None = None


class PurchaseOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    material_id: UUID
    quantity: float
    unit_price: float
    quantity_received: float
    notes: str | None
    created_at: datetime


class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    order_date: date
    expected_date: date | None = None
    notes: str | None = None


class PurchaseOrderUpdate(BaseModel):
    expected_date: date | None = None
    notes: str | None = None


class PurchaseOrderListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    status: str
    supplier_id: UUID
    order_date: date
    expected_date: date | None
    total_amount: float
    created_at: datetime


class PurchaseOrderDetail(PurchaseOrderListItem):
    received_at: datetime | None
    notes: str | None
    updated_at: datetime
    items: list[PurchaseOrderItemOut] = Field(default_factory=list)


class PurchaseOrderReceiveItem(BaseModel):
    item_id: UUID
    quantity_received: float = Field(..., ge=0)


class PurchaseOrderReceive(BaseModel):
    """Receive a PO, optionally with per-item quantities."""
    received_items: list[PurchaseOrderReceiveItem] = Field(default_factory=list)
    note: str | None = None


# ════════════════════════════════════════════════════════════════
# CATALOG — dropdown options for the UI
# ════════════════════════════════════════════════════════════════

class InventoryCatalog(BaseModel):
    material_categories: list[str]
    material_category_labels: dict[str, str]
    units: list[str]
    transaction_types: list[str]
    transaction_type_labels: dict[str, str]
    purchase_order_statuses: list[str]
    purchase_order_status_labels: dict[str, str]