# app/schemas/inventory/item.py
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal

from uuid import UUID


class CreateInventoryItem(BaseModel):
    name: str
    category: str
    unit: str
    current_stock: Decimal = Field(default=0, ge=0)
    min_stock_threshold: Decimal = Field(default=0, ge=0)
    cost_price: float = 0
    selling_price: Optional[float] = None
    


class UpdateInventoryItem(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    min_stock_threshold: Optional[int] = None
    status: Optional[str] = None


class InventoryItemResponse(BaseModel):
    id: UUID
    name: str
    category: str
    unit: str
    cost_price: float
    selling_price: Optional[float]
    current_stock: Decimal
    min_stock_threshold: Decimal
    status: str

    class Config:
        from_attributes = True
        
        
class CreateInventoryMaterialUsage(BaseModel):
    project_id: UUID 
    item_id: UUID
    quantity: Decimal = Field(..., gte=0, description="Jumlah dalam satuan unit (0.2 untuk 200ml) jika unit nya liter")
    note: str | None = None
    

class CreateInventoryStockMovement(BaseModel):
    item_id: str 
    type: str
    quantity: int
    reference_type: Optional[str]
    reference_id: Optional[str]
    note: Optional[str]
    
    class Config:
        from_attributes = True
        
        
class ProjectWorkshopCreate(BaseModel):
    unit_name: Optional[str] = None
    status: str = "pending"
    estimated_cost: float = 0
    
    
class ProjectWorkshopResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    unit_name: Optional[str] = None
    status: str
    estimated_cost: float
    actual_cost: float
    
    class Config:
        from_attributes = True