# app/schemas/inventory/workshop_job.py
from pydantic import BaseModel
from typing import Optional


class WorkshopJobCreate(BaseModel):
    unit_name: Optional[str] = None
    status: str = "pending"
    estimated_cost: float = 0


class WorkshopJobResponse(BaseModel):
    id: str
    unit_name: Optional[str]
    status: str
    estimated_cost: float
    actual_cost: float

    class Config:
        from_attributes = True