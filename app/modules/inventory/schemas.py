"""Pydantic schemas for the inventory module."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.types import Email

from app.modules.inventory.constants import (
    MANUAL_TRANSACTION_TYPES,
    MATERIAL_CATEGORIES,
    PURCHASE_ORDER_STATUSES,
    REFERENCE_TYPES,
    UNITS,
    ReferenceType,
)


_EMPTY = {"", "none", "null", "undefined", "nil"}


def _clean_optional(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in _EMPTY:
        return None
    return s


# ════════════════════════════════════════════════════════════════
# SUPPLIERS
# ════════════════════════════════════════════════════════════════

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    contact_person: str | None = Field(None, max_length=255)
    email: Email | None = None
    phone: str | None = Field(None, max_length=32)
    address: str | None = Field(None, max_length=2000)
    tax_id: str | None = Field(None, max_length=64)
    payment_terms: str | None = Field(None, max_length=64)
    notes: str | None = Field(None, max_length=5000)

    @field_validator("email", "phone", "address", "tax_id", "payment_terms", "notes",
                     mode="before")
    @classmethod
    def _clean_optional(cls, v):
        return _clean_optional(v)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v):
        # Strip BEFORE min_length — otherwise "  A  " (5 chars) passes
        # min_length=2 and is stored as "A" (1 char).
        if isinstance(v, str):
            return v.strip()
        return v


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    contact_person: str | None = None
    email: Email | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    payment_terms: str | None = None
    notes: str | None = None
    is_active: bool | None = None

    @field_validator("email", "phone", "address", "tax_id", "payment_terms", "notes",
                     mode="before")
    @classmethod
    def _clean_optional(cls, v):
        return _clean_optional(v)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("name")
    @classmethod
    def _non_nullable_name(cls, v):
        if v is None:
            raise ValueError("name cannot be null")
        return v


class SupplierListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    contact_person: str | None
    phone: str | None
    email: Email | None
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
    notes: str | None = Field(None, max_length=5000)
    location: str | None = Field(None, max_length=64)

    @field_validator("code", "name", mode="before")
    @classmethod
    def _strip_required(cls, v):
        # Strip BEFORE min_length — see SupplierCreate for rationale.
        if isinstance(v, str):
            return v.strip()
        return v

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

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

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

    @field_validator(
        "name", "category", "purchase_unit", "stock_unit",
        "stock_units_per_purchase", "reorder_point", "min_stock",
    )
    @classmethod
    def _non_nullable(cls, v):
        if v is None:
            raise ValueError("field cannot be null")
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
    new_purchase_price: float = Field(..., ge=0)
    note: str | None = Field(None, max_length=500)


# ════════════════════════════════════════════════════════════════
# INVENTORY TRANSACTIONS
# ════════════════════════════════════════════════════════════════

class InventoryTransactionCreate(BaseModel):
    material_id: UUID
    transaction_type: str
    quantity: float = Field(..., gt=0)
    unit_cost: float | None = Field(None, ge=0)
    reference_type: str | None = Field(None, max_length=32)
    reference_id: UUID | None = None
    reference_note: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=2000)

    @field_validator("transaction_type")
    @classmethod
    def _validate_type(cls, v):
        if v not in MANUAL_TRANSACTION_TYPES:
            raise ValueError(
                f"transaction_type must be one of {MANUAL_TRANSACTION_TYPES}. "
                f"PURCHASE and RETURN are reserved for the PO workflow."
            )
        return v

    @field_validator("reference_type")
    @classmethod
    def _validate_ref(cls, v):
        v = _clean_optional(v)
        if v is not None and v not in REFERENCE_TYPES:
            raise ValueError(f"reference_type must be one of {REFERENCE_TYPES}")
        return v

    @model_validator(mode="after")
    def _validate_reference_pair(self):
        # A reference_id only makes sense alongside its type.
        if self.reference_id is not None and self.reference_type is None:
            raise ValueError(
                "reference_id requires a reference_type"
            )
        # Entity-backed references need the target row. MANUAL movements are
        # recorded from the material page and legitimately have no id.
        if (
            self.reference_type in {
                ReferenceType.PURCHASE_ORDER.value,
                ReferenceType.PROJECT.value,
            }
            and self.reference_id is None
        ):
            raise ValueError(
                f"reference_id is required for {self.reference_type} references"
            )
        return self


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
    occurred_at: datetime
    created_by_id: UUID | None
    created_at: datetime


# ════════════════════════════════════════════════════════════════
# PURCHASE ORDERS
# ════════════════════════════════════════════════════════════════

class PurchaseOrderItemCreate(BaseModel):
    material_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    notes: str | None = Field(None, max_length=500)


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
    notes: str | None = Field(None, max_length=5000)


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
    supplier_name: str | None = None


class PurchaseOrderDetail(PurchaseOrderListItem):
    received_at: datetime | None
    notes: str | None
    updated_at: datetime
    items: list[PurchaseOrderItemOut] = Field(default_factory=list)


class PurchaseOrderReceiveItem(BaseModel):
    item_id: UUID
    quantity_received: float = Field(..., ge=0)


class PurchaseOrderReceive(BaseModel):
    """Receive a PO.

    Semantics:
      - `received_items = []`  → receive ALL remaining quantity for every
        item that still has room. This is the "receive everything" default.
      - `received_items` non-empty → receive ONLY the listed items at the
        given quantities. Items not mentioned are left untouched (0 this
        call). This is the "partial receipt" mode.

    The PO stays SENT until every item's `quantity_received` reaches its
    ordered `quantity`; at that point it becomes RECEIVED automatically.
    Call `POST /close` explicitly once the delivery is fully settled.
    """
    received_items: list[PurchaseOrderReceiveItem] = Field(default_factory=list)
    note: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _no_duplicate_items(self):
        seen: set[UUID] = set()
        for ri in self.received_items:
            if ri.item_id in seen:
                raise ValueError(
                    f"item_id {ri.item_id} appears more than once in "
                    f"received_items; the last entry would silently win"
                )
            seen.add(ri.item_id)
        return self


# ════════════════════════════════════════════════════════════════
# CATALOG
# ════════════════════════════════════════════════════════════════

class InventoryCatalog(BaseModel):
    material_categories: list[str]
    material_category_labels: dict[str, str]
    units: list[str]
    transaction_types: list[str]
    transaction_type_labels: dict[str, str]
    manual_transaction_types: list[str]
    purchase_order_statuses: list[str]
    purchase_order_status_labels: dict[str, str]