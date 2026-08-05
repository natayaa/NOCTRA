# modules/price_list/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List


# =============================================================================
# Price List Item Schemas
# =============================================================================

class PriceListItemCreate(BaseModel):
    """Schema untuk membuat price list item."""
    category: str = Field(..., max_length=50, description="Kategori")
    sub_category: Optional[str] = Field(None, max_length=50, description="Sub kategori")
    name: str = Field(..., max_length=255, description="Nama item")
    description: Optional[str] = Field(None, description="Deskripsi")
    price: Decimal = Field(..., ge=0, description="Harga")
    cost_price: Optional[Decimal] = Field(None, ge=0, description="Harga modal")
    unit: Optional[str] = Field(None, max_length=20, description="Satuan")
    sku: Optional[str] = Field(None, max_length=50, description="SKU")
    vehicle_brand: Optional[str] = Field(None, max_length=50, description="Brand kendaraan")
    vehicle_model: Optional[str] = Field(None, max_length=100, description="Model kendaraan")
    effective_date: date = Field(default_factory=date.today, description="Tanggal efektif")
    expiry_date: Optional[date] = Field(None, description="Tanggal kadaluarsa")
    is_active: bool = Field(default=True, description="Status aktif")
    min_quantity: Optional[int] = Field(None, ge=1, description="Quantity minimal")
    max_quantity: Optional[int] = Field(None, ge=1, description="Quantity maksimal")
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100, description="Diskon persentase")
    is_taxable: bool = Field(default=True, description="Kena pajak")
    is_discount_allowed: bool = Field(default=True, description="Diskon diperbolehkan")
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0, description="Estimasi durasi jam")
    created_by: Optional[str] = Field(None, max_length=100, description="Dibuat oleh")

    @field_validator("effective_date")
    @classmethod
    def validate_effective_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Effective date cannot be in the past")
        return v

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(cls, v: Optional[date], info) -> Optional[date]:
        if v and info.data.get('effective_date') and v < info.data['effective_date']:
            raise ValueError("Expiry date must be after effective date")
        return v

    @field_validator("min_quantity", "max_quantity")
    @classmethod
    def validate_quantities(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_quantity_range(self) -> "PriceListItemCreate":
        if self.min_quantity is not None and self.max_quantity is not None:
            if self.min_quantity > self.max_quantity:
                raise ValueError("Min quantity cannot be greater than max quantity")
        return self


class PriceListItemUpdate(BaseModel):
    """Schema untuk update price list item."""
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    sku: Optional[str] = Field(None, max_length=50)
    vehicle_brand: Optional[str] = Field(None, max_length=50)
    vehicle_model: Optional[str] = Field(None, max_length=100)
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_active: Optional[bool] = None
    min_quantity: Optional[int] = Field(None, ge=1)
    max_quantity: Optional[int] = Field(None, ge=1)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    is_taxable: Optional[bool] = None
    is_discount_allowed: Optional[bool] = None
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0)
    updated_by: Optional[str] = Field(None, max_length=100)

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(cls, v: Optional[date], info) -> Optional[date]:
        if v and info.data.get('effective_date') and v < info.data['effective_date']:
            raise ValueError("Expiry date must be after effective date")
        return v

    @model_validator(mode="after")
    def validate_quantity_range(self) -> "PriceListItemUpdate":
        if self.min_quantity is not None and self.max_quantity is not None:
            if self.min_quantity > self.max_quantity:
                raise ValueError("Min quantity cannot be greater than max quantity")
        return self


class PriceListItemResponse(BaseModel):
    """Response untuk price list item."""
    id: UUID
    category: str
    sub_category: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Decimal
    cost_price: Optional[Decimal] = None
    unit: Optional[str] = None
    sku: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    effective_date: date
    expiry_date: Optional[date] = None
    is_active: bool
    is_expired: bool = False
    is_effective: bool = True
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    discount_percentage: Optional[Decimal] = None
    is_taxable: bool
    is_discount_allowed: bool
    estimated_duration_hours: Optional[Decimal] = None
    price_change_count: int = 0
    display_price: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Price List Category Schemas
# =============================================================================

class PriceListCategoryCreate(BaseModel):
    """Schema untuk membuat kategori price list."""
    name: str = Field(..., max_length=50, description="Nama kategori (unique)")
    display_name: str = Field(..., max_length=100, description="Nama tampilan")
    description: Optional[str] = Field(None, description="Deskripsi")
    sort_order: int = Field(default=0, description="Urutan")
    is_active: bool = Field(default=True, description="Status aktif")
    icon: Optional[str] = Field(None, max_length=50, description="Icon untuk UI")
    parent_category: Optional[str] = Field(None, max_length=50, description="Kategori induk")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip().lower()


class PriceListCategoryUpdate(BaseModel):
    """Schema untuk update kategori price list."""
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    icon: Optional[str] = Field(None, max_length=50)
    parent_category: Optional[str] = Field(None, max_length=50)


class PriceListCategoryResponse(BaseModel):
    """Response untuk kategori price list."""
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool
    icon: Optional[str] = None
    parent_category: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceListCategoryWithCountResponse(BaseModel):
    """Response untuk kategori dengan jumlah item."""
    name: str
    display_name: str
    sort_order: int
    item_count: int


# =============================================================================
# Price List Discount Schemas
# =============================================================================

class PriceListDiscountCreate(BaseModel):
    """Schema untuk membuat diskon."""
    name: str = Field(..., max_length=100, description="Nama diskon")
    code: str = Field(..., max_length=50, description="Kode diskon (unique)")
    description: Optional[str] = Field(None, description="Deskripsi")
    discount_percentage: Decimal = Field(..., ge=0, le=100, description="Persentase diskon")
    discount_amount: Optional[Decimal] = Field(None, ge=0, description="Jumlah diskon (alternatif)")
    applies_to_category: Optional[str] = Field(None, max_length=50, description="Kategori yang berlaku")
    applies_to_item_id: Optional[UUID] = Field(None, description="ID item yang berlaku")
    applies_to_all: bool = Field(default=False, description="Berlaku untuk semua")
    valid_from: date = Field(default_factory=date.today, description="Tanggal mulai berlaku")
    valid_until: Optional[date] = Field(None, description="Tanggal berakhir")
    is_active: bool = Field(default=True, description="Status aktif")
    max_uses: Optional[int] = Field(None, ge=1, description="Maksimal penggunaan")

    @field_validator("valid_from")
    @classmethod
    def validate_valid_from(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Valid from date cannot be in the past")
        return v

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, v: Optional[date], info) -> Optional[date]:
        if v and info.data.get('valid_from') and v < info.data['valid_from']:
            raise ValueError("Valid until must be after valid from")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code cannot be empty")
        return v.strip().upper()

    @model_validator(mode="after")
    def validate_discount(self) -> "PriceListDiscountCreate":
        if self.discount_amount is None and self.discount_percentage is None:
            raise ValueError("Either discount_percentage or discount_amount must be provided")
        if self.discount_amount is not None and self.discount_amount <= 0:
            raise ValueError("Discount amount must be greater than 0")
        return self


class PriceListDiscountUpdate(BaseModel):
    """Schema untuk update diskon."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    applies_to_category: Optional[str] = Field(None, max_length=50)
    applies_to_item_id: Optional[UUID] = None
    applies_to_all: Optional[bool] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_active: Optional[bool] = None
    max_uses: Optional[int] = Field(None, ge=1)

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, v: Optional[date], info) -> Optional[date]:
        if v and info.data.get('valid_from') and v < info.data['valid_from']:
            raise ValueError("Valid until must be after valid from")
        return v


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
    applies_to_all: bool = False
    valid_from: date
    valid_until: Optional[date] = None
    is_active: bool
    is_valid: bool = True
    remaining_uses: Optional[int] = None
    is_fully_used: bool = False
    max_uses: Optional[int] = None
    used_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Price History Schemas
# =============================================================================

class PriceHistoryCreate(BaseModel):
    """Schema untuk membuat price history."""
    item_id: UUID
    old_price: Decimal = Field(..., ge=0)
    new_price: Decimal = Field(..., ge=0)
    changed_by: str = Field(..., max_length=100)
    reason: Optional[str] = None


class PriceHistoryResponse(BaseModel):
    """Response untuk price history."""
    id: UUID
    item_id: UUID
    item_name: Optional[str] = None
    old_price: Decimal
    new_price: Decimal
    price_change: Decimal
    price_change_percent: float
    is_increase: bool
    is_decrease: bool
    changed_by: str
    changed_at: datetime
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PriceChangeRequest(BaseModel):
    """Request untuk change price."""
    new_price: Decimal = Field(..., gt=0, description="New price")
    reason: Optional[str] = Field(None, description="Reason for price change")


class PriceRevertRequest(BaseModel):
    """Request untuk revert price."""
    history_id: UUID = Field(..., description="Price history ID to revert to")
    reason: Optional[str] = Field(None, description="Reason for revert")


# =============================================================================
# Custom Price Schemas
# =============================================================================

class CustomPriceCreate(BaseModel):
    """Schema untuk membuat custom price."""
    item_id: UUID = Field(..., description="ID price list item")
    customer_id: Optional[UUID] = Field(None, description="ID customer (optional)")
    project_id: Optional[UUID] = Field(None, description="ID project (optional)")
    custom_price: Decimal = Field(..., ge=0, description="Custom price")
    valid_from: date = Field(default_factory=date.today, description="Valid from date")
    valid_until: Optional[date] = Field(None, description="Valid until date")

    @field_validator("valid_from")
    @classmethod
    def validate_valid_from(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Valid from date cannot be in the past")
        return v

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, v: Optional[date], info) -> Optional[date]:
        if v and info.data.get('valid_from') and v < info.data['valid_from']:
            raise ValueError("Valid until must be after valid from")
        return v

    @model_validator(mode="after")
    def validate_customer_or_project(self) -> "CustomPriceCreate":
        if not self.customer_id and not self.project_id:
            raise ValueError("Either customer_id or project_id must be provided")
        return self


class CustomPriceUpdate(BaseModel):
    """Schema untuk update custom price."""
    custom_price: Optional[Decimal] = Field(None, ge=0)
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, v: Optional[date], info) -> Optional[date]:
        if v and info.data.get('valid_from') and v < info.data['valid_from']:
            raise ValueError("Valid until must be after valid from")
        return v


class CustomPriceResponse(BaseModel):
    """Response untuk custom price."""
    id: UUID
    item_id: UUID
    item_name: Optional[str] = None
    customer_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    custom_price: Decimal
    valid_from: date
    valid_until: Optional[date] = None
    is_valid: bool = True
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Bulk Update Schemas
# =============================================================================

class PriceListBulkUpdate(BaseModel):
    """Schema untuk bulk update harga."""
    category: str = Field(..., description="Kategori yang akan di-update")
    percentage: float = Field(..., description="Persentase perubahan harga (negatif untuk diskon)")
    vehicle_brand: Optional[str] = Field(None, max_length=50, description="Brand kendaraan (opsional)")

    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        if v < -100:
            raise ValueError("Percentage cannot be less than -100%")
        if v > 1000:
            raise ValueError("Percentage cannot be more than 1000%")
        return v


class PriceListItemListResponse(BaseModel):
    """Response untuk list price list items dengan pagination."""
    items: List[PriceListItemResponse]
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_previous: bool


# =============================================================================
# Statistics Schemas
# =============================================================================

class CategoryCountResponse(BaseModel):
    """Response untuk category count."""
    category: str
    count: int


class PriceListStatisticsResponse(BaseModel):
    """Response untuk statistics price list."""
    total_active_items: int
    total_categories: int
    categories: List[str]
    category_counts: List[CategoryCountResponse]
    total_discounts: int
    active_discounts: int
    total_price_items: int


# =============================================================================
# Price Calculation Schemas
# =============================================================================

class PriceCalculationResponse(BaseModel):
    """Response untuk price calculation."""
    item_id: str
    item_name: str
    category: str
    base_price: float
    quantity: float
    subtotal: float
    discount_percentage: float
    discount_amount: float
    discount_code: Optional[str] = None
    discount_id: Optional[str] = None
    final_price: float
    is_taxable: bool
    unit: Optional[str] = None


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Price List Items
    "PriceListItemCreate",
    "PriceListItemUpdate",
    "PriceListItemResponse",
    
    # Categories
    "PriceListCategoryCreate",
    "PriceListCategoryUpdate",
    "PriceListCategoryResponse",
    "PriceListCategoryWithCountResponse",
    
    # Discounts
    "PriceListDiscountCreate",
    "PriceListDiscountUpdate",
    "PriceListDiscountResponse",
    
    # Price History
    "PriceHistoryCreate",
    "PriceHistoryResponse",
    "PriceChangeRequest",
    "PriceRevertRequest",
    
    # Custom Prices
    "CustomPriceCreate",
    "CustomPriceUpdate",
    "CustomPriceResponse",
    
    # Bulk Operations
    "PriceListBulkUpdate",
    "PriceListItemListResponse",
    
    # Statistics
    "CategoryCountResponse",
    "PriceListStatisticsResponse",
    
    # Price Calculation
    "PriceCalculationResponse",
]