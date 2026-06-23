from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, delete, UUID
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import List, Dict, Optional

from models.inventory import (
    InventoryItem, InventoryMaterialUsage, 
    InventoryStockMovement,
    ProjectWorkshopTask
)
from schemas.inventories import CreateInventoryItem, UpdateInventoryItem


class InventoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, item_id: UUID) -> InventoryItem | None:
        stmt = select(InventoryItem).where(InventoryItem.id == item_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> InventoryItem | None:
        stmt = select(InventoryItem).where(InventoryItem.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> list[InventoryItem]:
        stmt = select(InventoryItem).where(InventoryItem.status == "active")
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, payload: CreateInventoryItem) -> InventoryItem:
        item = InventoryItem(**payload.model_dump())
        self.db.add(item)
        await self.db.flush()
        return item

    async def update(self, item_id: UUID, payload: UpdateInventoryItem) -> InventoryItem | None:
        item = await self.get_by_id(item_id)
        if not item:
            return None

        update_data = payload.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(item, key, value)

        await self.db.flush()
        return item

    async def soft_delete(self, item_id: UUID) -> bool:
        item = await self.get_by_id(item_id)
        if not item:
            return False

        item.status = "inactive"
        await self.db.flush()
        return True
    
    
class InventoryMaterialUsageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_project(self, project_id: str) -> List[InventoryMaterialUsage]:
        stmt = (
            select(InventoryMaterialUsage)
            .where(InventoryMaterialUsage.project_id == project_id)
            .options(selectinload(InventoryMaterialUsage.item))
            .order_by(InventoryMaterialUsage.created_at.desc())
        )
        
        res = await self.db.execute(stmt)
        return res.scalars().all()
    
    async def create_usage_material(self, usage: InventoryMaterialUsage) -> InventoryMaterialUsage:
        self.db.add(usage)
        await self.db.flush()
        return usage
    
    async def get_by_id(self, usage_id: UUID) -> InventoryMaterialUsage | None:
        stmt = select(InventoryMaterialUsage).where(InventoryMaterialUsage.id == usage_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
    
    async def delete_usage_material(self, usage_id: UUID) -> bool:
        stmt = delete(InventoryMaterialUsage).where(InventoryMaterialUsage.id == usage_id)
        
        res = await self.db.execute(stmt)
        await self.db.flush()
        
        return res.rowcount > 0
    
    
class InventoryStockMovementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_stock_movement(self, data_object: InventoryStockMovement):
        self.db.add(data_object)
        await self.db.flush()
        return data_object
    
    async def recent_stock_movement(self, limit: int = 10):
        stmt = (
            select(InventoryStockMovement)
            .options(selectinload(InventoryStockMovement.item))
            .order_by(InventoryStockMovement.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        movements = res.scalars().all()
        
        return [
            {
                "id": m.id,
                "type": m.type,
                "quantity": m.quantity,
                "item_name": m.item.name,        # akses melalui relasi yang sudah diload
                "created_at": m.created_at
            }
            for m in movements
        ]
        
class ProjectWorkshopJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_project_workshop(self, job_id: str):
        res = await self.db.execute(
            select(ProjectWorkshopTask)
            .where(ProjectWorkshopTask.id == job_id)
        )
        
        return res.scalar_one_or_none()
    
    async def create_history(self, object_data: ProjectWorkshopTask):
        self.db.add(object_data)
        await self.db.flush()
        return object_data