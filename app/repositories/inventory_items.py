# repositories/inventory.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from models.inventory_items import InventoryItems
from schemas.inventory_items import ItemCreate, ItemUpdate


class InventoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get(self, item_id: str):
        stmt = select(InventoryItems).where(InventoryItems.id == item_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self):
        stmt = select(InventoryItems).where(InventoryItems.status == "active")
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, request: ItemCreate):
        item = InventoryItems(**request.model_dump())
        self.db.add(item)
        await self.db.flush()
        return item

    async def update(self, item_id: UUID, request: ItemUpdate):
        item = await self.db.get(InventoryItems, item_id)
        if not item:
            return None
        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)
        await self.db.flush()
        return item

    async def delete(self, item_id: UUID):
        item = await self.db.get(InventoryItems, item_id)
        if not item:
            return False
        item.status = "inactive"
        await self.db.flush()
        return True