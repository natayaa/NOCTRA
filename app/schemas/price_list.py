# schemas/price_list.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class PriceListItemCreate(BaseModel):
    """Schema untuk membuat price list item."""
    category: str = Field(..., max_length=50, description="Kategori (service, material, labor, bike_model)")
    sub_category: Optional[str] = Field(None, max_length=50, description="Sub kategori")
    name: str = Field(..., max_length=255, description="Nama item")
    description: Optional[str] = Field(None, description="Deskripsi")
    price: Decimal = Field(..., ge=0, description="Harga")
    unit: Optional[str] = Field(None, max_length=20, description="Satuan")
    vehicle_brand: Optional[str] = Field(None, max_length=50, description="Brand kendaraan")
    vehicle_model: Optional[str] = Field(None, max_length=100, description="Model kendaraan")
    effective_date: date = Field(default_factory=date.today, description="Tanggal efektif")
    expiry_date: Optional[date] = Field(None, description="Tanggal kadaluarsa")
    is_active: bool = Field(default=True, description="Status aktif")
    min_quantity: Optional[int] = Field(None, ge=1, description="Quantity minimal")
    max_quantity: Optional[int] = Field(None, ge=1, description="Quantity maksimal")
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100, description="Diskon persentase")
    is_taxable: bool = Field(default=True, description="Kena pajak")
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0, description="Estimasi durasi jam")


class PriceListItemUpdate(BaseModel):
    """Schema untuk update price list item."""
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    vehicle_brand: Optional[str] = Field(None, max_length=50)
    vehicle_model: Optional[str] = Field(None, max_length=100)
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_active: Optional[bool] = None
    min_quantity: Optional[int] = Field(None, ge=1)
    max_quantity: Optional[int] = Field(None, ge=1)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    is_taxable: Optional[bool] = None
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0)


class PriceListItemResponse(BaseModel):
    """Response untuk price list item."""
    id: UUID
    category: str
    sub_category: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Decimal
    unit: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    effective_date: date
    expiry_date: Optional[date] = None
    is_active: bool
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    discount_percentage: Optional[Decimal] = None
    is_taxable: bool
    estimated_duration_hours: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PriceListCategoryCreate(BaseModel):
    """Schema untuk membuat kategori price list."""
    name: str = Field(..., max_length=50, description="Nama kategori (unique)")
    display_name: str = Field(..., max_length=100, description="Nama tampilan")
    description: Optional[str] = Field(None, description="Deskripsi")
    sort_order: int = Field(default=0, description="Urutan")
    is_active: bool = Field(default=True, description="Status aktif")
    icon: Optional[str] = Field(None, max_length=50, description="Icon untuk UI")


class PriceListCategoryResponse(BaseModel):
    """Response untuk kategori price list."""
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool
    icon: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PriceListDiscountCreate(BaseModel):
    """Schema untuk membuat diskon."""
    name: str = Field(..., max_length=100, description="Nama diskon")
    code: str = Field(..., max_length=50, description="Kode diskon (unique)")
    description: Optional[str] = Field(None, description="Deskripsi")
    discount_percentage: Decimal = Field(..., ge=0, le=100, description="Persentase diskon")
    discount_amount: Optional[Decimal] = Field(None, ge=0, description="Jumlah diskon (alternatif)")
    applies_to_category: Optional[str] = Field(None, max_length=50, description="Kategori yang berlaku")
    applies_to_item_id: Optional[UUID] = Field(None, description="ID item yang berlaku")
    valid_from: date = Field(default_factory=date.today, description="Tanggal mulai berlaku")
    valid_until: Optional[date] = Field(None, description="Tanggal berakhir")
    is_active: bool = Field(default=True, description="Status aktif")
    max_uses: Optional[int] = Field(None, ge=1, description="Maksimal penggunaan")


class PriceListDiscountResponse(BaseModel):
    """Response untuk diskon."""
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    discount_percentage: Decimal
    discount_amount: Optional[Decimal] = None
    applies_to_category: Optional[str] = None
    applies_to_item_id: Optional[UUID] = None
    valid_from: date
    valid_until: Optional[date] = None
    is_active: bool
    max_uses: Optional[int] = None
    used_count: int
    created_at: datetime

    model_config = {"from_attributes": True}