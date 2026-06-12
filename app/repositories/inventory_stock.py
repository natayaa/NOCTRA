# app/repositories/inventory/stock_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.inventory_stock_movement import StockMovement


class StockMovementRepository:
    async def create(self, db: AsyncSession, obj: StockMovement):
        db.add(obj)
        await db.flush()
        return obj

    async def recent(self, db: AsyncSession, limit: int = 20):
        result = await db.execute(
            select(StockMovement).order_by(StockMovement.created_at.desc()).limit(limit)
        )
        return result.scalars().all()