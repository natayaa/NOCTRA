# modules/price_list/service.py
from uuid import UUID
from typing import Optional, List, Tuple
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessError, NotFoundError, ValidationError
from .models import PriceListItem, PriceListCategory, PriceListDiscount, PriceHistory, CustomPrice
from .repository import (
    PriceListRepository,
    PriceListCategoryRepository,
    PriceListDiscountRepository
)
from .schemas import (
    PriceListItemCreate,
    PriceListItemUpdate,
    PriceListCategoryCreate,
    PriceListCategoryUpdate,
    PriceListDiscountCreate,
    PriceListDiscountUpdate,
    PriceListBulkUpdate,
    PriceChangeRequest,
    PriceHistoryResponse,
    CustomPriceCreate,
    CustomPriceResponse,
    PriceRevertRequest,
)


class PriceListService:
    """Service untuk Price List management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PriceListRepository(db)
        self.category_repo = PriceListCategoryRepository(db)
        self.discount_repo = PriceListDiscountRepository(db)

    # =========================================================================
    # Price List Items
    # =========================================================================

    async def create_item(self, data: PriceListItemCreate) -> PriceListItem:
        """Create a new price list item."""
        # Convert Pydantic schema to dict
        item_data = data.model_dump()

        # Set effective date if not provided
        if not item_data.get('effective_date'):
            item_data['effective_date'] = date.today()

        # Check SKU uniqueness if provided
        if item_data.get('sku'):
            existing = await self.repo.get_by_sku(item_data['sku'])
            if existing:
                raise ValidationError(
                    f"SKU '{item_data['sku']}' already exists")

        # Create model instance
        db_item = PriceListItem(**item_data)

        # Use repository's create method
        return await self.repo.create(db_item)

    async def get_item(self, item_id: UUID) -> Optional[PriceListItem]:
        """Get price list item by ID."""
        return await self.repo.get(item_id)

    async def get_item_with_history(self, item_id: UUID) -> Optional[PriceListItem]:
        """Get price list item with price history."""
        return await self.repo.get_with_price_history(item_id)

    async def list_items(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        active_only: bool = True,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[PriceListItem], int]:
        """List price items with pagination and filters."""
        return await self.repo.list_paginated(
            category=category,
            search=search,
            active_only=active_only,
            vehicle_brand=vehicle_brand,
            vehicle_model=vehicle_model,
            page=page,
            limit=limit
        )

    async def update_item(
        self,
        item_id: UUID,
        data: PriceListItemUpdate
    ) -> Optional[PriceListItem]:
        """Update price list item."""
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        # Validate SKU uniqueness if updating
        if data.sku and data.sku != item.sku:
            existing = await self.repo.get_by_sku(data.sku)
            if existing:
                raise ValidationError(f"SKU '{data.sku}' already exists")

        if data.updated_by:
            update_data["updated_by"] = data.updated_by

        return await self.repo.update(item_id, update_data)

    async def delete_item(self, item_id: UUID) -> bool:
        """Soft delete price list item (set is_active=False)."""
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")
        return await self.repo.delete(item_id)

    async def toggle_item_active(self, item_id: UUID) -> Optional[PriceListItem]:
        """Toggle active status of a price list item."""
        return await self.repo.toggle_active(item_id)

    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return await self.repo.get_categories()

    async def toggle_item(self, item_id: UUID) -> Optional[PriceListItem]:
        """Toggle active status of a price list item."""
        return await self.repo.toggle_active(item_id)

    async def list_discounts(self) -> List[PriceListDiscount]:
        """List all active discounts."""
        return await self.discount_repo.list_active()

    async def get_price_for_service(
        self,
        service_name: str,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None
    ) -> Optional[PriceListItem]:
        """Get price for a specific service with vehicle-specific pricing."""
        return await self.repo.get_price_for_service(
            service_name, vehicle_brand, vehicle_model
        )

    async def get_active_count(self) -> int:
        """Get count of active items."""
        return await self.repo.get_active_count()

    async def bulk_create(self, items: List[PriceListItemCreate]) -> List[PriceListItem]:
        """Bulk create price list items."""
        item_dicts = []
        for item_data in items:
            if not item_data.effective_date:
                item_data.effective_date = date.today()
            item_dicts.append(item_data.model_dump())

        return await self.repo.bulk_create(item_dicts)

    async def bulk_update_prices(
        self,
        data: PriceListBulkUpdate
    ) -> int:
        """Bulk update prices by percentage."""
        return await self.repo.bulk_update_prices(
            category=data.category,
            percentage=data.percentage,
            vehicle_brand=data.vehicle_brand
        )

    # =========================================================================
    # Price History
    # =========================================================================

    async def update_price_with_history(
        self,
        item_id: UUID,
        data: PriceChangeRequest,
        changed_by: str
    ) -> Optional[PriceListItem]:
        """Update price with history tracking."""
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        old_price = item.price
        new_price = data.new_price

        if old_price == new_price:
            raise ValidationError(
                "New price must be different from current price")

        # Update price
        item.price = new_price
        await self.db.flush()

        # Add history
        await self.repo.add_price_history({
            "item_id": item_id,
            "old_price": old_price,
            "new_price": new_price,
            "changed_by": changed_by,
            "reason": data.reason
        })

        await self.db.refresh(item)
        return item

    async def get_price_history(self, item_id: UUID, limit: int = 50) -> List[PriceHistory]:
        """Get price history for an item."""
        return await self.repo.get_price_history(item_id, limit)

    async def get_price_change_summary(self, item_id: UUID) -> dict:
        """Get price change summary for an item."""
        return await self.repo.get_price_change_summary(item_id)

    async def change_price(
        self,
        item_id: UUID,
        data: PriceChangeRequest,
        changed_by: str = "system"
    ) -> Optional[PriceListItem]:
        """Change price with history tracking."""
        return await self.update_price_with_history(item_id, data, changed_by)

    async def revert_price(
        self,
        item_id: UUID,
        data: PriceRevertRequest,
        changed_by: str = "system"
    ) -> Optional[PriceListItem]:
        """Revert price to a historical price."""
        return await self._revert_price(
            item_id=item_id,
            history_id=data.history_id,
            changed_by=changed_by,
            reason=data.reason
        )

    async def _revert_price(
        self,
        item_id: UUID,
        history_id: UUID,
        changed_by: str,
        reason: Optional[str] = None
    ) -> Optional[PriceListItem]:
        """Internal method to revert price."""
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        # Get history entry
        history = await self.repo.get(history_id)
        if not history:
            raise NotFoundError(f"Price history {history_id} not found")

        # Check if history belongs to this item
        if history.item_id != item_id:
            raise ValidationError("History entry does not belong to this item")

        old_price = item.price
        new_price = history.old_price

        if old_price == new_price:
            raise ValidationError("Price is already at the historical price")

        # Update price
        item.price = new_price
        await self.db.flush()

        # Add new history entry
        await self.repo.add_price_history({
            "item_id": item_id,
            "old_price": old_price,
            "new_price": new_price,
            "changed_by": changed_by,
            "reason": reason or f"Reverted to price from {history.changed_at.strftime('%Y-%m-%d %H:%M')}"
        })

        await self.db.refresh(item)
        return item

    # =========================================================================
    # Custom Price
    # =========================================================================

    async def create_custom_price(
        self,
        data: CustomPriceCreate,
        created_by: str = "system"
    ) -> CustomPrice:
        """Create custom price."""
        # Validate item exists
        item = await self.repo.get(data.item_id)
        if not item:
            raise NotFoundError(f"Price item {data.item_id} not found")

        # Validate if customer or project is provided
        if not data.customer_id and not data.project_id:
            raise ValidationError(
                "Either customer_id or project_id must be provided")

        custom_price_data = data.model_dump()
        custom_price_data["created_by"] = created_by

        return await self.repo.create_custom_price(custom_price_data)

    async def get_custom_prices(self, item_id: UUID) -> List[CustomPrice]:
        """Get all custom prices for an item."""
        # Validate item exists
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        return await self.repo.get_custom_prices(item_id)

    async def delete_custom_price(self, custom_price_id: UUID) -> bool:
        """Delete custom price."""
        return await self.repo.delete_custom_price(custom_price_id)

    # =========================================================================
    # Categories
    # =========================================================================

    async def create_category(self, data: PriceListCategoryCreate) -> PriceListCategory:
        """Create a new price list category."""
        # Check if category already exists
        existing = await self.category_repo.get_by_name(data.name)
        if existing:
            raise ValidationError(f"Category '{data.name}' already exists")

        # Create category
        category_data = data.model_dump()
        return await self.category_repo.create(category_data)

    async def get_category(self, category_id: UUID) -> Optional[PriceListCategory]:
        """Get category by ID."""
        return await self.category_repo.get(category_id)

    async def get_categories_with_counts(self) -> List[dict]:
        """List categories with item counts."""
        return await self.category_repo.list_with_counts()

    async def get_category_by_name(self, name: str) -> Optional[PriceListCategory]:
        """Get category by name."""
        return await self.category_repo.get_by_name(name)

    async def list_categories(self) -> List[PriceListCategory]:
        """List all active categories."""
        return await self.category_repo.list_active()

    async def list_categories_with_counts(self) -> List[dict]:
        """List categories with item counts."""
        return await self.category_repo.list_with_counts()

    async def update_category(
        self,
        category_id: UUID,
        data: PriceListCategoryUpdate
    ) -> Optional[PriceListCategory]:
        """Update a category."""
        category = await self.category_repo.get(category_id)
        if not category:
            raise NotFoundError(f"Category {category_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        return await self.category_repo.update(category_id, update_data)

    async def delete_category(self, category_id: UUID) -> bool:
        """Delete a category."""
        category = await self.category_repo.get(category_id)
        if not category:
            return False

        # Check if category has items
        items = await self.repo.get_by_category(category.name)
        if items:
            raise ValidationError(
                f"Cannot delete category with {len(items)} items. "
                "Please reassign or delete the items first."
            )

        return await self.category_repo.delete(category_id)

    # =========================================================================
    # Discounts
    # =========================================================================

    async def list_discounts(self) -> List[PriceListDiscount]:
        """List all active discounts."""
        return await self.discount_repo.list_active()

    async def get_discount(self, discount_id: UUID) -> Optional[PriceListDiscount]:
        """Get discount by ID."""
        return await self.discount_repo.get(discount_id)

    async def create_discount(self, data: PriceListDiscountCreate) -> PriceListDiscount:
        """Create a new discount."""
        # Check if code already exists
        existing = await self.discount_repo.get_by_code(data.code)
        if existing:
            raise ValidationError(
                f"Discount code '{data.code}' already exists")

        # Validate date range
        if data.valid_until and data.valid_from > data.valid_until:
            raise ValidationError(
                "Valid from date must be before valid until date")

        discount_data = data.model_dump()
        return await self.discount_repo.create(discount_data)

    async def update_discount(
        self,
        discount_id: UUID,
        data: PriceListDiscountUpdate
    ) -> Optional[PriceListDiscount]:
        """Update a discount."""
        discount = await self.discount_repo.get(discount_id)
        if not discount:
            raise NotFoundError(f"Discount {discount_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        return await self.discount_repo.update(discount_id, update_data)

    async def validate_discount(self, code: str) -> dict:
        """Validate a discount code."""
        discount = await self.discount_repo.get_by_code(code)
        if not discount:
            raise NotFoundError(f"Discount code '{code}' not found")

        if not discount.is_valid:
            raise BusinessError(f"Discount code '{code}' is not valid")

        return {
            "valid": True,
            "code": discount.code,
            "discount_percentage": float(discount.discount_percentage),
            "discount_amount": float(discount.discount_amount) if discount.discount_amount else None,
            "name": discount.name,
            "description": discount.description
        }

    async def use_discount(self, discount_id: UUID) -> Optional[PriceListDiscount]:
        """Use a discount by ID."""
        discount = await self.discount_repo.get(discount_id)
        if not discount:
            raise NotFoundError(f"Discount {discount_id} not found")

        if not discount.is_valid:
            raise BusinessError(f"Discount '{discount.code}' is not valid")

        discount.used_count += 1
        await self.db.flush()
        await self.db.refresh(discount)
        return discount

    async def get_applicable_discounts(
        self,
        category: Optional[str] = None,
        item_id: Optional[UUID] = None
    ) -> List[PriceListDiscount]:
        """Get discounts applicable to a specific item or category."""
        return await self.discount_repo.get_applicable_discounts(category, item_id)

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict:
        """Get price list statistics."""
        active_items = await self.repo.get_active_count()
        categories = await self.repo.get_categories()
        discounts = await self.discount_repo.list_active()

        return {
            "total_active_items": active_items,
            "total_categories": len(categories),
            "categories": categories,
            "total_discounts": len(discounts) if discounts else 0,
            "active_discounts": len([d for d in (discounts or []) if d.is_active])
        }
