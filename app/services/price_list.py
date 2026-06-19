# services/price_list.py
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from repositories.price_list import PriceListRepository
from schemas.price_list import PriceListItemCreate, PriceListItemUpdate


class PriceListService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PriceListRepository(db)

    async def create(self, data: PriceListItemCreate):
        return await self.repo.create(data)

    async def get(self, item_id: UUID):
        return await self.repo.get(item_id)

    async def list_paginated(self, category=None, search=None, active_only=True, page=1, limit=10):
        return await self.repo.list_paginated(category, search, active_only, page, limit)

    async def update(self, item_id: UUID, data: PriceListItemUpdate):
        return await self.repo.update(item_id, data)

    async def delete(self, item_id: UUID):
        return await self.repo.delete(item_id)