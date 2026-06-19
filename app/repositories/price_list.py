# repositories/price_list.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from uuid import UUID
from models.price_list import PriceListItem
from schemas.price_list import PriceListItemCreate, PriceListItemUpdate


class PriceListRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: PriceListItemCreate) -> PriceListItem:
        item = PriceListItem(**data.model_dump())
        self.db.add(item)
        await self.db.flush()
        return item

    async def get(self, item_id: UUID) -> PriceListItem | None:
        return await self.db.get(PriceListItem, item_id)

    async def list_paginated(self, category=None, search=None, active_only=True, page=1, limit=10):
        stmt = select(PriceListItem)
        count_stmt = select(func.count()).select_from(PriceListItem)

        filters = []
        if active_only:
            filters.append(PriceListItem.is_active == True)
        if category:
            filters.append(PriceListItem.category == category)
        if search:
            filters.append(
                or_(
                    PriceListItem.name.ilike(f"%{search}%"),
                    PriceListItem.description.ilike(f"%{search}%")
                )
            )
        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.order_by(PriceListItem.category, PriceListItem.name)
        stmt = stmt.offset((page - 1) * limit).limit(limit)

        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        return items, total

    async def update(self, item_id: UUID, data: PriceListItemUpdate) -> PriceListItem | None:
        item = await self.get(item_id)
        if not item:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await self.db.flush()
        return item

    async def delete(self, item_id: UUID) -> bool:
        item = await self.get(item_id)
        if not item:
            return False
        item.is_active = False
        await self.db.flush()
        return True