# app/schemas/inventory/item.py
from pydantic import BaseModel
from typing import Optional

from uuid import UUID


class ItemCreate(BaseModel):
    name: str
    category: str
    unit: str
    cost_price: float = 0
    selling_price: Optional[float] = None
    min_stock_threshold: int = 0


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    min_stock_threshold: Optional[int] = None
    status: Optional[str] = None


class ItemResponse(BaseModel):
    id: UUID
    name: str
    category: str
    unit: str
    cost_price: float
    selling_price: Optional[float]
    current_stock: int
    min_stock_threshold: int
    status: str

    class Config:
        from_attributes = True