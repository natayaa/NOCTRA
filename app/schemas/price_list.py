# schemas/price_list.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

class PriceListItemCreate(BaseModel):
    category: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: str | None = Field(None)
    price: Decimal = Field(..., ge=0)
    unit: str | None = Field(None, max_length=20)
    vehicle_brand: str | None = Field(None, max_length=50)
    vehicle_model: str | None = Field(None, max_length=100)
    effective_date: date | None = None
    is_active: bool = True

class PriceListItemUpdate(BaseModel):
    category: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    unit: str | None = Field(None, max_length=20)
    vehicle_brand: str | None = Field(None, max_length=50)
    vehicle_model: str | None = Field(None, max_length=100)
    effective_date: date | None = None
    is_active: bool | None = None

class PriceListItemResponse(BaseModel):
    id: UUID
    category: str
    name: str
    description: str | None
    price: Decimal
    unit: str | None
    vehicle_brand: str | None
    vehicle_model: str | None
    effective_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}