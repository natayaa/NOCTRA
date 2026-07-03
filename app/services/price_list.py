# services/price_list.py
from uuid import UUID
from typing import Optional, List, Tuple
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.price_list import PriceListRepository, PriceListCategoryRepository, PriceListDiscountRepository
from schemas.price_list import (
    PriceListItemCreate, PriceListItemUpdate, 
    PriceListCategoryCreate, PriceListDiscountCreate
)
from models.price_list import PriceListItem, PriceListCategory, PriceListDiscount


class PriceListService:
    """
    Service layer for Price List management.
    Handles business logic for price items (services, materials, labor, bike models).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PriceListRepository(db)
        self.category_repo = PriceListCategoryRepository(db)
        self.discount_repo = PriceListDiscountRepository(db)

    # ======================================================================
    # Price List Items
    # ======================================================================

    async def create(self, data: PriceListItemCreate) -> PriceListItem:
        """Create a new price list item."""
        # Set effective date if not provided
        if not data.effective_date:
            data.effective_date = date.today()
        return await self.repo.create(data)

    async def get(self, item_id: UUID) -> PriceListItem | None:
        """Retrieve a single price list item by ID."""
        return await self.repo.get(item_id)

    async def get_active(self, item_id: UUID) -> PriceListItem | None:
        """Retrieve an active price list item by ID."""
        return await self.repo.get_active(item_id)

    async def list_paginated(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        active_only: bool = True,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[PriceListItem], int]:
        """List price items with pagination and optional filters."""
        return await self.repo.list_paginated(
            category=category,
            search=search,
            active_only=active_only,
            vehicle_brand=vehicle_brand,
            vehicle_model=vehicle_model,
            page=page,
            limit=limit
        )

    async def get_by_category(self, category: str, active_only: bool = True) -> List[PriceListItem]:
        """Get all price items by category."""
        return await self.repo.get_by_category(category, active_only)

    async def get_by_vehicle(
        self,
        brand: str,
        model: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[PriceListItem]:
        """Get price items by vehicle brand and model."""
        return await self.repo.get_by_vehicle(brand, model, category)

    async def get_price_for_service(
        self,
        service_name: str,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None
    ) -> Optional[PriceListItem]:
        """Get price for a specific service with vehicle-specific pricing."""
        return await self.repo.get_price_for_service(service_name, vehicle_brand, vehicle_model)

    async def update(self, item_id: UUID, data: PriceListItemUpdate) -> PriceListItem | None:
        """Update an existing price list item."""
        return await self.repo.update(item_id, data)

    async def delete(self, item_id: UUID) -> bool:
        """Soft-delete a price list item (sets is_active=False)."""
        return await self.repo.delete(item_id)

    async def hard_delete(self, item_id: UUID) -> bool:
        """Permanently delete a price list item."""
        return await self.repo.hard_delete(item_id)

    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return await self.repo.get_categories()

    # ======================================================================
    # Categories
    # ======================================================================

    async def create_category(self, data: PriceListCategoryCreate) -> PriceListCategory:
        """Create a new price list category."""
        return await self.category_repo.create(data.model_dump())

    async def get_category(self, category_id: UUID) -> PriceListCategory | None:
        """Get a category by ID."""
        return await self.category_repo.get(category_id)

    async def get_category_by_name(self, name: str) -> PriceListCategory | None:
        """Get a category by name."""
        return await self.category_repo.get_by_name(name)

    async def list_categories(self) -> List[PriceListCategory]:
        """List all active categories."""
        return await self.category_repo.list_active()

    async def update_category(self, category_id: UUID, data: dict) -> PriceListCategory | None:
        """Update a category."""
        return await self.category_repo.update(category_id, data)

    # ======================================================================
    # Discounts
    # ======================================================================

    async def create_discount(self, data: PriceListDiscountCreate) -> PriceListDiscount:
        """Create a new discount."""
        return await self.discount_repo.create(data.model_dump())

    async def get_discount(self, discount_id: UUID) -> PriceListDiscount | None:
        """Get a discount by ID."""
        return await self.discount_repo.get(discount_id)

    async def get_discount_by_code(self, code: str) -> PriceListDiscount | None:
        """Get a discount by code (validates active and date range)."""
        return await self.discount_repo.get_by_code(code)

    async def list_active_discounts(self) -> List[PriceListDiscount]:
        """List all active discounts."""
        return await self.discount_repo.list_active()

    async def validate_discount(self, code: str) -> bool:
        """Validate if a discount code is valid."""
        return await self.discount_repo.validate_discount(code)

    async def use_discount(self, code: str) -> bool:
        """Mark a discount as used (increment used_count)."""
        return await self.discount_repo.use_discount(code)

    # ======================================================================
    # Bulk Operations
    # ======================================================================

    async def bulk_update_active_status(self, item_ids: List[UUID], is_active: bool) -> dict:
        """Bulk update active status for multiple items."""
        success_count = 0
        failed_ids = []
        
        for item_id in item_ids:
            try:
                item = await self.get(item_id)
                if item:
                    item.is_active = is_active
                    await self.db.flush()
                    success_count += 1
                else:
                    failed_ids.append(str(item_id))
            except Exception:
                failed_ids.append(str(item_id))
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids
        }

    async def get_price_for_items(self, item_names: List[str]) -> dict:
        """Get prices for multiple items by name."""
        result = {}
        for name in item_names:
            item = await self.repo.get_by_name(name)
            if item:
                result[name] = {
                    "id": str(item.id),
                    "price": float(item.price),
                    "unit": item.unit
                }
        return result