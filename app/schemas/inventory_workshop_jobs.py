# app/schemas/inventory/workshop_job.py
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class WorkshopJobCreate(BaseModel):
    unit_name: Optional[str] = None
    status: str = "pending"
    estimated_cost: float = 0


class WorkshopJobResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    unit_name: Optional[str] = None
    status: str
    estimated_cost: float
    actual_cost: float

    class Config:
        from_attributes = True