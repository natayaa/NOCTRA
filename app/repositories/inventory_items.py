# app/repositories/inventory/item_repo.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from models.inventory_items import InventoryItems


class ItemRepository:

    async def get(self, db: AsyncSession, item_id: str):
        result = await db.execute(
            select(InventoryItems).where(InventoryItems.id == item_id)
        )
        return result.scalar_one_or_none()

    async def list(self, db: AsyncSession, *, limit: int = 100, offset: int = 0):
        result = await db.execute(
            select(InventoryItems)
            .order_by(InventoryItems.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj: InventoryItems):
        db.add(obj)
        await db.flush()
        return obj

    async def update(
        self,
        db: AsyncSession,
        item_id: str,
        values: dict
    ):
        await db.execute(
            update(InventoryItems)
            .where(InventoryItems.id == item_id)
            .values(**values)
        )
        await db.flush()

        return await self.get(db, item_id)

    async def delete(self, db: AsyncSession, item_id: str):
        await db.execute(
            delete(InventoryItems).where(InventoryItems.id == item_id)
        )
        await db.flush()