# app/repositories/inventory/stock_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.inventory_stock_movement import StockMovement
from models.inventory_items import InventoryItems


class StockMovementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create(self, db: AsyncSession, obj: StockMovement):
        db.add(obj)
        await db.flush()
        return obj

    async def recent(self, db, limit=10):
        stmt = (
            select(StockMovement, InventoryItems.name.label("item_name"))
            .join(InventoryItems, StockMovement.item_id == InventoryItems.id)
            .order_by(StockMovement.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()
        # Convert to dict list
        return [{"id": row.StockMovement.id, "type": row.StockMovement.type, "quantity": row.StockMovement.quantity, "item_name": row.item_name, "created_at": row.StockMovement.created_at} for row in rows]