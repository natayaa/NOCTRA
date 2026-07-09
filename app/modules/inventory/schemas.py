# modules/inventory/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from uuid import UUID
from datetime import datetime, date

from core.constants import InventoryStatus, StockMovementType


# =============================================================================
# Inventory Item Schemas
# =============================================================================

class CreateInventoryItem(BaseModel):
    """Schema untuk membuat item inventory baru."""
    name: str = Field(..., min_length=1, max_length=255,
                      description="Nama item")
    category: str = Field(..., min_length=1,
                          max_length=100, description="Kategori")
    sub_category: Optional[str] = Field(
        None, max_length=100, description="Sub kategori")
    unit: str = Field(..., min_length=1, max_length=50, description="Satuan")
    base_unit: Optional[str] = Field(
        None, max_length=20, description="Unit dasar untuk konversi")
    conversion_factor: Decimal = Field(default=Decimal(
        '1.000000'), ge=0, description="Faktor konversi ke unit dasar")
    cost_price: Decimal = Field(default=0, ge=0, description="Harga beli")
    selling_price: Optional[Decimal] = Field(
        None, ge=0, description="Harga jual")
    current_stock: Decimal = Field(
        default=0, ge=0, description="Stok saat ini")
    min_stock_threshold: Decimal = Field(
        default=0, ge=0, description="Minimum stok")
    max_stock_threshold: Decimal = Field(
        default=999999, ge=0, description="Maksimum stok")
    sku: Optional[str] = Field(None, max_length=50, description="SKU")
    barcode: Optional[str] = Field(None, max_length=50, description="Barcode")
    description: Optional[str] = Field(None, description="Deskripsi")
    location: Optional[str] = Field(
        None, max_length=100, description="Lokasi penyimpanan")
    supplier_id: Optional[UUID] = Field(None, description="ID supplier")
    weight: Optional[Decimal] = Field(None, ge=0, description="Berat")
    dimensions: Optional[str] = Field(
        None, max_length=100, description="Dimensi (PxLxT)")


class UpdateInventoryItem(BaseModel):
    """Schema untuk update item inventory."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    sub_category: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    base_unit: Optional[str] = Field(None, max_length=20)
    conversion_factor: Optional[Decimal] = Field(None, ge=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    selling_price: Optional[Decimal] = Field(None, ge=0)
    current_stock: Optional[Decimal] = Field(None, ge=0)
    min_stock_threshold: Optional[Decimal] = Field(None, ge=0)
    max_stock_threshold: Optional[Decimal] = Field(None, ge=0)
    status: Optional[str] = Field(None, description="Status inventory")
    sku: Optional[str] = Field(None, max_length=50)
    barcode: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=100)
    supplier_id: Optional[UUID] = None
    weight: Optional[Decimal] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=100)


class InventoryItemResponse(BaseModel):
    """Response untuk item inventory."""
    id: UUID
    name: str
    category: str
    sub_category: Optional[str] = None
    unit: str
    base_unit: Optional[str] = None
    conversion_factor: Decimal = Decimal('1.000000')
    cost_price: Decimal
    selling_price: Optional[Decimal] = None
    current_stock: Decimal
    reserved_stock: Decimal = Decimal(0)
    available_stock: Decimal = Decimal(0)
    min_stock_threshold: Decimal
    max_stock_threshold: Decimal
    status: str
    is_low_stock: bool = False
    is_out_of_stock: bool = False
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    supplier_id: Optional[UUID] = None
    supplier_name: Optional[str] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Stock Movement Schemas
# =============================================================================

class CreateInventoryStockMovement(BaseModel):
    """Schema untuk membuat pergerakan stock."""
    item_id: UUID = Field(..., description="ID item")
    type: str = Field(..., description="Tipe pergerakan")
    quantity: Decimal = Field(..., description="Jumlah")
    reference_type: str = Field(..., description="Tipe referensi")
    reference_id: Optional[UUID] = Field(None, description="ID referensi")
    note: Optional[str] = Field(None, description="Catatan")
    performed_by: Optional[str] = Field(None, description="Dilakukan oleh")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = [t.value for t in StockMovementType]
        if v not in valid_types:
            raise ValueError(f"Type must be one of: {valid_types}")
        return v


class InventoryStockMovementResponse(BaseModel):
    """Response untuk pergerakan stock."""
    id: UUID
    item_id: UUID
    item_name: Optional[str] = None
    type: str
    quantity: Decimal
    previous_stock: Decimal
    new_stock: Decimal
    reference_type: str
    reference_id: Optional[UUID] = None
    note: Optional[str] = None
    performed_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockAdjustment(BaseModel):
    """Schema untuk adjustment stock."""
    item_id: UUID = Field(..., description="ID item")
    quantity: Decimal = Field(..., description="Jumlah adjustment")
    movement_type: str = Field(..., description="Tipe pergerakan")
    reference_type: str = Field(..., description="Tipe referensi")
    reference_id: Optional[UUID] = Field(None, description="ID referensi")
    note: Optional[str] = Field(None, description="Catatan")
    performed_by: Optional[str] = Field(None, description="Dilakukan oleh")


# =============================================================================
# Material Usage Schemas
# =============================================================================

class CreateInventoryMaterialUsage(BaseModel):
    """Schema untuk membuat material usage."""
    project_id: UUID = Field(..., description="ID project")
    item_id: UUID = Field(..., description="ID item")
    quantity: Decimal = Field(..., gt=0, description="Jumlah")
    note: Optional[str] = Field(None, description="Catatan")
    job_id: Optional[UUID] = Field(None, description="ID workshop job")
    is_waste: bool = Field(default=False, description="Apakah waste")
    confirmed_by: Optional[str] = Field(None, description="Dikonfirmasi oleh")


class InventoryMaterialUsageResponse(BaseModel):
    """Response untuk material usage."""
    id: UUID
    project_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    item_id: UUID
    item_name: Optional[str] = None
    item_unit: Optional[str] = None
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    note: Optional[str] = None
    is_waste: bool = False
    waste_percentage: Optional[Decimal] = None
    confirmed_by: Optional[str] = None
    used_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialUsageSummaryResponse(BaseModel):
    """Response untuk summary material usage."""
    total_items: int
    total_cost: Decimal
    items: List[Dict[str, Any]]


# =============================================================================
# Workshop Job Schemas
# =============================================================================

class ProjectWorkshopCreate(BaseModel):
    """Schema untuk membuat workshop job."""
    project_id: UUID = Field(..., description="ID project")
    unit_name: Optional[str] = Field(
        None, max_length=255, description="Nama unit")
    status: str = Field("pending", description="Status")
    estimated_cost: Decimal = Field(
        default=0, ge=0, description="Estimasi biaya")
    estimated_hours: Optional[Decimal] = Field(
        None, ge=0, description="Estimasi jam")
    start_date: Optional[datetime] = Field(None, description="Tanggal mulai")
    end_date: Optional[datetime] = Field(None, description="Tanggal selesai")
    technician_name: Optional[str] = Field(
        None, max_length=100, description="Nama teknisi")
    notes: Optional[str] = Field(None, description="Catatan")


class ProjectWorkshopUpdate(BaseModel):
    """Schema untuk update workshop job."""
    status: Optional[str] = Field(None, description="Status")
    unit_name: Optional[str] = Field(None, max_length=255)
    estimated_cost: Optional[Decimal] = Field(None, ge=0)
    estimated_hours: Optional[Decimal] = Field(None, ge=0)
    actual_hours: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    technician_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class ProjectWorkshopResponse(BaseModel):
    """Response untuk workshop job."""
    id: UUID
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    unit_name: Optional[str] = None
    status: str
    estimated_cost: Decimal
    actual_cost: Decimal
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    technician_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Supplier Schemas
# =============================================================================

class CreateSupplier(BaseModel):
    """Schema untuk membuat supplier."""
    name: str = Field(..., min_length=1, max_length=255,
                      description="Nama supplier")
    contact_person: Optional[str] = Field(
        None, max_length=100, description="Kontak person")
    phone: Optional[str] = Field(
        None, max_length=20, description="Nomor telepon")
    email: Optional[str] = Field(None, max_length=255, description="Email")
    address: Optional[str] = Field(None, description="Alamat")
    tax_id: Optional[str] = Field(None, max_length=50, description="NPWP")
    payment_terms: Optional[str] = Field(
        None, max_length=100, description="Syarat pembayaran")
    notes: Optional[str] = Field(None, description="Catatan")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating (1-5)")
    website: Optional[str] = Field(None, max_length=255, description="Website")


class UpdateSupplier(BaseModel):
    """Schema untuk update supplier."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    website: Optional[str] = Field(None, max_length=255)


class SupplierResponse(BaseModel):
    """Response untuk supplier."""
    id: UUID
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    is_active: bool
    notes: Optional[str] = None
    rating: Optional[int] = None
    website: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierWithCountResponse(BaseModel):
    """Response untuk supplier dengan jumlah item."""
    id: UUID
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    item_count: int


# =============================================================================
# Purchase Order Schemas
# =============================================================================

class PurchaseOrderItemCreate(BaseModel):
    """Schema untuk membuat item purchase order."""
    item_id: UUID = Field(..., description="ID item")
    quantity: Decimal = Field(..., gt=0, description="Jumlah")
    unit_price: Decimal = Field(..., ge=0, description="Harga per unit")
    notes: Optional[str] = Field(None, description="Catatan")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Unit price must be greater than or equal to 0")
        return v


class CreatePurchaseOrder(BaseModel):
    """Schema untuk membuat purchase order."""
    supplier_id: UUID = Field(..., description="ID supplier")
    po_number: Optional[str] = Field(
        None, max_length=50, description="Nomor PO (auto-generate jika kosong)"
    )
    order_date: Optional[datetime] = Field(None, description="Tanggal order")
    expected_delivery: Optional[datetime] = Field(
        None, description="Tanggal pengiriman yang diharapkan"
    )
    notes: Optional[str] = Field(None, description="Catatan")
    items: List[PurchaseOrderItemCreate] = Field(
        ..., min_length=1, description="Item PO"
    )

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[PurchaseOrderItemCreate]) -> List[PurchaseOrderItemCreate]:
        if not v:
            raise ValueError("At least one item is required")
        return v


# ALIAS untuk backward compatibility (opsional)
PurchaseOrderCreate = CreatePurchaseOrder


class PurchaseOrderUpdate(BaseModel):
    """Schema untuk update purchase order."""
    status: Optional[str] = Field(None, description="Status PO")
    expected_delivery: Optional[datetime] = Field(
        None, description="Tanggal pengiriman yang diharapkan"
    )
    notes: Optional[str] = Field(None, description="Catatan")
    approved_by: Optional[str] = Field(
        None, max_length=100, description="Disetujui oleh")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v:
            valid_statuses = ["draft", "ordered",
                              "received_partial", "completed", "cancelled"]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class PurchaseOrderItemResponse(BaseModel):
    """Response untuk item purchase order."""
    id: UUID
    purchase_order_id: UUID
    item_id: UUID
    item_name: Optional[str] = None
    item_unit: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    received_quantity: Decimal
    remaining_quantity: Decimal
    is_fully_received: bool = False
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderResponse(BaseModel):
    """Response untuk purchase order."""
    id: UUID
    supplier_id: UUID
    supplier_name: Optional[str] = None
    po_number: str
    order_date: datetime
    expected_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    status: str
    total_amount: Decimal
    notes: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    items: List[PurchaseOrderItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderReceive(BaseModel):
    """Schema untuk menerima purchase order."""
    received_items: Dict[UUID, Decimal] = Field(
        ..., description="Dict item_id -> quantity received"
    )
    received_by: str = Field(..., min_length=1, description="Diterima oleh")
    notes: Optional[str] = Field(None, description="Catatan")

    @field_validator("received_items")
    @classmethod
    def validate_received_items(cls, v: Dict[UUID, Decimal]) -> Dict[UUID, Decimal]:
        for item_id, qty in v.items():
            if qty <= 0:
                raise ValueError(
                    f"Quantity for item {item_id} must be greater than 0")
        return v


class PurchaseOrderListResponse(BaseModel):
    """Response untuk list purchase order."""
    items: List[PurchaseOrderResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# =============================================================================
# Dashboard/Summary Schemas
# =============================================================================

class InventorySummaryResponse(BaseModel):
    """Response untuk summary inventory dashboard."""
    total_skus: int
    total_inventory_value: float
    low_stock_items: int
    out_of_stock_items: int
    total_usage_cost: float


class StockAlertResponse(BaseModel):
    """Response untuk stock alert."""
    id: UUID
    name: str
    category: str
    current_stock: float
    min_stock_threshold: float
    unit: str
    status: str
    severity: str


class InventoryStatisticsResponse(BaseModel):
    """Response untuk statistics inventory."""
    total_items: int
    by_status: Dict[str, int]
    by_category: Dict[str, Dict[str, Any]]
    total_value: float
    low_stock_count: int
    out_of_stock_count: int


# modules/inventory/schemas.py - TAMBAHAN

# ============================================================================
# Stock Alert Schemas
# ============================================================================

class StockAlertCreate(BaseModel):
    """Schema untuk membuat stock alert."""
    item_id: UUID
    alert_type: str = Field(...,
                            description="low_stock, out_of_stock, expiring, overstock")
    current_stock: Decimal
    threshold: Decimal
    severity: str = Field(default="warning", description="warning, critical")
    message: Optional[str] = None


class StockAlertUpdate(BaseModel):
    """Schema untuk update stock alert."""
    status: Optional[str] = Field(
        None, description="active, resolved, ignored")
    resolution_note: Optional[str] = None


class StockAlertResponse(BaseModel):
    """Response untuk stock alert."""
    id: UUID
    item_id: UUID
    item_name: Optional[str] = None
    item_unit: Optional[str] = None
    alert_type: str
    current_stock: Decimal
    threshold: Decimal
    status: str
    severity: str
    message: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Stock Opname Schemas
# ============================================================================

class StockOpnameCreate(BaseModel):
    """Schema untuk membuat stock opname."""
    item_id: UUID
    physical_stock: Decimal = Field(..., ge=0, description="Stock fisik")
    adjustment_reason: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None


class StockOpnameUpdate(BaseModel):
    """Schema untuk update stock opname."""
    approved_by: Optional[str] = None
    notes: Optional[str] = None


class StockOpnameResponse(BaseModel):
    """Response untuk stock opname."""
    id: UUID
    item_id: UUID
    item_name: Optional[str] = None
    system_stock: Decimal
    physical_stock: Decimal
    difference: Decimal
    adjustment_reason: str
    performed_by: str
    performed_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
