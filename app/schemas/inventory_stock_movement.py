# app/schemas/inventory/stock_movement.py
from pydantic import BaseModel
from typing import Optional


class StockMovementCreate(BaseModel):
    item_id: str
    type: str
    quantity: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    note: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: str
    item_id: str
    type: str
    quantity: int
    reference_type: Optional[str]
    reference_id: Optional[str]
    note: Optional[str]

    class Config:
        from_attributes = True