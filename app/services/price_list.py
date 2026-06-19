from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.price_list import PriceListRepository
from schemas.price_list import PriceListItemCreate, PriceListItemUpdate


class PriceListService:
    """
    Service layer for Price List management.
    Handles business logic for price items (services, materials, labor, bike models).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PriceListRepository(db)

    async def create(self, data: PriceListItemCreate):
        """
        Create a new price list item.
        
        Args:
            data: PriceListItemCreate schema with item details.
        
        Returns:
            The created PriceListItem instance.
        """
        return await self.repo.create(data)

    async def get(self, item_id: UUID):
        """
        Retrieve a single price list item by ID.
        
        Args:
            item_id: UUID of the price item.
        
        Returns:
            PriceListItem instance or None if not found.
        """
        return await self.repo.get(item_id)

    async def list_paginated(
        self,
        category: str | None = None,
        search: str | None = None,
        active_only: bool = True,
        page: int = 1,
        limit: int = 10
    ):
        """
        List price items with pagination and optional filters.
        
        Args:
            category: Filter by category (service, material, labor, bike_model).
            search: Search by name or description.
            active_only: Only return active items (default True).
            page: Page number (1-indexed).
            limit: Items per page (default 10).
        
        Returns:
            Tuple of (items_list, total_count).
        """
        return await self.repo.list_paginated(
            category=category,
            search=search,
            active_only=active_only,
            page=page,
            limit=limit
        )

    async def update(self, item_id: UUID, data: PriceListItemUpdate):
        """
        Update an existing price list item.
        
        Args:
            item_id: UUID of the item to update.
            data: PriceListItemUpdate schema with fields to update.
        
        Returns:
            Updated PriceListItem instance or None if not found.
        """
        return await self.repo.update(item_id, data)

    async def delete(self, item_id: UUID) -> bool:
        """
        Soft-delete a price list item (sets is_active=False).
        
        Args:
            item_id: UUID of the item to delete.
        
        Returns:
            True if successful, False if item not found.
        """
        return await self.repo.delete(item_id)