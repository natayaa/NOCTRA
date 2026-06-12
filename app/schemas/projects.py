from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional


class ProjectCreate(BaseModel):
    inquiry_id: Optional[UUID] = None

    name: str = Field(min_length=1, max_length=255)
    customer_name: str = Field(min_length=1, max_length=255)
    vehicle_brand: str = Field(min_length=1, max_length=100)
    vehicle_model: str = Field(min_length=1, max_length=100)


class ProjectUpdateStatus(BaseModel):
    status: str = Field(min_length=1, max_length=50)


class ProjectResponse(BaseModel):
    id: UUID
    inquiry_id: Optional[UUID] = None

    name: str
    customer_name: str
    vehicle_brand: str
    vehicle_model: str

    status: str
    progress: int

    estimated_cost: float
    actual_cost: float
    estimated_revenue: float
    actual_revenue: float

    model_config = ConfigDict(from_attributes=True)