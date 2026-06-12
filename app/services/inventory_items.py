# app/services/inventory/inventory_service.py
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.inventory_items import ItemRepository
from repositories.inventory_stock import StockMovementRepository
from models.inventory_stock_movement import StockMovement


class InventoryService:
    def __init__(self):
        self.item_repo = ItemRepository()
        self.stock_repo = StockMovementRepository()

    async def create_movement(
        self,
        db: AsyncSession,
        item_id: str,
        type: str,
        quantity: int,
        reference_type: str = None,
        reference_id: str = None,
        note: str = None,
    ):
        item = await self.item_repo.get(db, item_id)
        if not item:
            raise Exception("Item not found")

        if type == "IN":
            item.current_stock += quantity

        elif type in ("OUT", "USED_IN_WORKSHOP"):
            item.current_stock -= quantity
            if item.current_stock < 0:
                raise Exception("Stock cannot be negative")

        else:
            item.current_stock += quantity

        movement = StockMovement(
            item_id=item_id,
            type=type,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
        )

        await self.stock_repo.create(db, movement)

        return movement
    
    async def delete_item(self, db: AsyncSession, item_id: str):
        item = await self.item_repo.get(db, item_id)
        if not item: 
            raise Exception("Item not Found")
        await self.item_repo.delete(db, item_id)
        return True