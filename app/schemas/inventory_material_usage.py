# schemas/inventory/material_usage.py
from pydantic import BaseModel
from uuid import UUID

class MaterialUsageCreate(BaseModel):
    project_id: UUID          # <-- we link directly to project, then find or create job
    item_id: UUID
    quantity: int
    note: str | None = None