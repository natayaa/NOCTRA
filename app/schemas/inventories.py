# schemas/inventories.py
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from datetime import datetime

from schemas.constants import InventoryStatus, StockMovementType


class CreateInventoryItem(BaseModel):
    """Schema untuk membuat item inventory baru."""
    name: str = Field(..., min_length=1, max_length=255, description="Nama item")
    category: str = Field(..., min_length=1, max_length=100, description="Kategori")
    sub_category: Optional[str] = Field(None, max_length=100, description="Sub kategori")
    unit: str = Field(..., min_length=1, max_length=50, description="Satuan")
    base_unit: Optional[str] = Field(None, max_length=20, description="Unit dasar untuk conversi (liter, pcs, kg)")
    conversion_factor: Decimal = Field(ge=0, default=Decimal('1.000000'), description="Faktor konversi ke unit dasar")
    cost_price: Decimal = Field(default=0, ge=0, description="Harga beli")
    selling_price: Decimal = Field(default=0, ge=0, description="Harga jual")
    current_stock: Decimal = Field(default=0, ge=0, description="Stok saat ini")
    min_stock_threshold: Decimal = Field(default=0, ge=0, description="Minimum stok")
    max_stock_threshold: Decimal = Field(default=999999, ge=0, description="Maksimum stok")
    sku: Optional[str] = Field(None, max_length=50, description="SKU")
    barcode: Optional[str] = Field(None, max_length=50, description="Barcode")
    description: Optional[str] = Field(None, description="Deskripsi")
    location: Optional[str] = Field(None, max_length=100, description="Lokasi penyimpanan")
    supplier_id: Optional[UUID] = Field(None, description="ID supplier")
    weight: Optional[Decimal] = Field(None, ge=0, description="Berat")
    dimensions: Optional[str] = Field(None, max_length=100, description="Dimensi (PxLxT)")


class UpdateInventoryItem(BaseModel):
    """Schema untuk update item inventory."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    sub_category: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    selling_price: Optional[Decimal] = Field(None, ge=0)
    current_stock: Optional[Decimal] = Field(None, ge=0)
    min_stock_threshold: Optional[Decimal] = Field(None, ge=0)
    max_stock_threshold: Optional[Decimal] = Field(None, ge=0)
    status: Optional[str] = Field(None)
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
    min_stock_threshold: Decimal
    max_stock_threshold: Decimal
    status: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    supplier_id: Optional[UUID] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
    

class InventoryMaterialUsageRequest(BaseModel):
    project_id: UUID
    item_id: UUID
    quantity: Decimal = Field(..., gt=0)
    unit: Optional[str] = Field(None, description="Satuan yang digunakan (ml, liter, pcs, dll)")
    note: Optional[str] = None
    job_id: Optional[UUID] = None


class InventoryStockMovementCreate(BaseModel):
    """Schema untuk membuat pergerakan stock."""
    item_id: UUID = Field(..., description="ID item")
    type: str = Field(..., description="Tipe pergerakan")
    quantity: Decimal = Field(..., description="Jumlah")
    reference_type: str = Field(..., description="Tipe referensi")
    reference_id: Optional[UUID] = Field(None, description="ID referensi")
    note: Optional[str] = Field(None, description="Catatan")
    performed_by: Optional[str] = Field(None, description="Dilakukan oleh")


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

    model_config = {"from_attributes": True}


class InventoryMaterialUsageCreate(BaseModel):
    """Schema untuk membuat material usage."""
    project_id: UUID = Field(..., description="ID project")
    item_id: UUID = Field(..., description="ID item")
    quantity: Decimal = Field(..., gt=0, description="Jumlah (dalam unit item)")
    unit: Optional[str] = Field(None, description="Satuan yang digunakan (ml, liter, pcs, dll)")
    note: Optional[str] = Field(None, description="Catatan")
    job_id: Optional[UUID] = Field(None, description="ID workshop job")


class InventoryMaterialUsageResponse(BaseModel):
    """Response untuk material usage."""
    id: UUID
    project_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    item_id: UUID
    item_name: Optional[str] = None
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectWorkshopCreate(BaseModel):
    """Schema untuk membuat workshop job."""
    project_id: UUID = Field(..., description="ID project")
    unit_name: Optional[str] = Field(None, max_length=255, description="Nama unit")
    status: str = Field("pending", description="Status")
    estimated_cost: Decimal = Field(default=0, ge=0, description="Estimasi biaya")
    start_date: Optional[datetime] = Field(None, description="Tanggal mulai")
    end_date: Optional[datetime] = Field(None, description="Tanggal selesai")
    technician_name: Optional[str] = Field(None, max_length=100, description="Nama teknisi")
    notes: Optional[str] = Field(None, description="Catatan")


class ProjectWorkshopResponse(BaseModel):
    """Response untuk workshop job."""
    id: UUID
    project_id: Optional[UUID] = None
    unit_name: Optional[str] = None
    status: str
    estimated_cost: Decimal
    actual_cost: Decimal
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    technician_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierCreate(BaseModel):
    """Schema untuk membuat supplier."""
    name: str = Field(..., min_length=1, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


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
    created_at: datetime

    model_config = {"from_attributes": True}