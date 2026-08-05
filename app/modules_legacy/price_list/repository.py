# modules/price_list/repository.py
from uuid import UUID
from typing import Any, Optional, List, Tuple
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, delete
from sqlalchemy.orm import selectinload

from core.base import BaseRepository
from .models import (
    PriceListItem,
    PriceListCategory,
    PriceListDiscount,
    PriceHistory,
    CustomPrice
)


class PriceListRepository(BaseRepository[PriceListItem]):
    """Repository untuk Price List Item."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=PriceListItem)

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def get(self, pk: Any, include_deleted: bool = False) -> Optional[PriceListItem]:
        """
        Get price list item by ID with optional soft delete filter.
        
        Args:
            pk: Primary key (UUID)
            include_deleted: Include soft-deleted records
        """
        if isinstance(pk, UUID):
            stmt = select(self.model).where(self.model.id == pk)
            if not include_deleted and hasattr(self.model, 'is_deleted'):
                stmt = stmt.where(self.model.is_deleted == False)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        return await super().get(pk)

    async def get_with_details(self, item_id: UUID) -> Optional[PriceListItem]:
        """
        Get price list item with all related data (price history, custom prices).
        """
        stmt = (
            select(PriceListItem)
            .where(
                PriceListItem.id == item_id,
                PriceListItem.is_deleted == False
            )
            .options(
                selectinload(PriceListItem.price_history),
                selectinload(PriceListItem.custom_prices),
                selectinload(PriceListItem.project_usages),
                selectinload(PriceListItem.invoice_items),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        active_only: bool = True,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        include_deleted: bool = False,
        page: int = 1,
        limit: int = 10,
        sort_by: str = "name",
        sort_order: str = "asc"
    ) -> Tuple[List[PriceListItem], int]:
        """
        List price items with pagination and filters.
        
        Args:
            category: Filter by category
            search: Search by name or description
            active_only: Only include active items
            vehicle_brand: Filter by vehicle brand
            vehicle_model: Filter by vehicle model
            include_deleted: Include soft-deleted records
            page: Page number
            limit: Items per page
            sort_by: Sort field (name, price, category, effective_date)
            sort_order: Sort order (asc, desc)
        """
        stmt = select(PriceListItem)
        count_stmt = select(func.count()).select_from(PriceListItem)

        filters = []

        # Soft delete filter
        if not include_deleted and hasattr(PriceListItem, 'is_deleted'):
            filters.append(PriceListItem.is_deleted == False)

        # Active filter
        if active_only:
            filters.append(PriceListItem.is_active == True)

        # Category filter
        if category:
            filters.append(PriceListItem.category == category)

        # Vehicle brand filter
        if vehicle_brand:
            filters.append(
                or_(
                    PriceListItem.vehicle_brand == vehicle_brand,
                    PriceListItem.vehicle_brand.is_(None)
                )
            )

        # Vehicle model filter
        if vehicle_model:
            filters.append(
                or_(
                    PriceListItem.vehicle_model == vehicle_model,
                    PriceListItem.vehicle_model.is_(None)
                )
            )

        # Search filter
        if search:
            filters.append(
                or_(
                    PriceListItem.name.ilike(f"%{search}%"),
                    PriceListItem.description.ilike(f"%{search}%"),
                    PriceListItem.sku.ilike(f"%{search}%"),
                    PriceListItem.category.ilike(f"%{search}%"),
                )
            )

        # Validity filters (effective date <= today, expiry >= today or null)
        today = date.today()
        filters.append(PriceListItem.effective_date <= today)
        filters.append(
            or_(
                PriceListItem.expiry_date.is_(None),
                PriceListItem.expiry_date >= today
            )
        )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        # Sorting
        sort_column = getattr(PriceListItem, sort_by, PriceListItem.name)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(asc(sort_column))

        # Secondary sort for consistency
        stmt = stmt.order_by(PriceListItem.category, PriceListItem.name)

        # Pagination
        stmt = stmt.offset((page - 1) * limit).limit(limit)

        # Execute queries
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        return items, total

    async def get_by_category(
        self,
        category: str,
        active_only: bool = True,
        vehicle_brand: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[PriceListItem]:
        """Get price items by category."""
        filters = [PriceListItem.category == category]

        if not include_deleted and hasattr(PriceListItem, 'is_deleted'):
            filters.append(PriceListItem.is_deleted == False)

        if active_only:
            filters.append(PriceListItem.is_active == True)

        if vehicle_brand:
            filters.append(
                or_(
                    PriceListItem.vehicle_brand == vehicle_brand,
                    PriceListItem.vehicle_brand.is_(None)
                )
            )

        today = date.today()
        filters.append(PriceListItem.effective_date <= today)
        filters.append(
            or_(
                PriceListItem.expiry_date.is_(None),
                PriceListItem.expiry_date >= today
            )
        )

        stmt = select(PriceListItem).where(and_(*filters))
        stmt = stmt.order_by(PriceListItem.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_vehicle(
        self,
        brand: str,
        model: Optional[str] = None,
        category: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[PriceListItem]:
        """Get price items by vehicle brand and model."""
        filters = [
            PriceListItem.vehicle_brand == brand,
            PriceListItem.is_active == True,
            PriceListItem.effective_date <= date.today()
        ]

        if not include_deleted and hasattr(PriceListItem, 'is_deleted'):
            filters.append(PriceListItem.is_deleted == False)

        if model:
            filters.append(
                or_(
                    PriceListItem.vehicle_model == model,
                    PriceListItem.vehicle_model.is_(None)
                )
            )

        if category:
            filters.append(PriceListItem.category == category)

        filters.append(
            or_(
                PriceListItem.expiry_date.is_(None),
                PriceListItem.expiry_date >= date.today()
            )
        )

        stmt = select(PriceListItem).where(and_(*filters))
        stmt = stmt.order_by(
            PriceListItem.vehicle_model.desc().nulls_last(),
            PriceListItem.name
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_sku(self, sku: str, include_deleted: bool = False) -> Optional[PriceListItem]:
        """Get price item by SKU."""
        stmt = select(PriceListItem).where(PriceListItem.sku == sku)
        if not include_deleted and hasattr(PriceListItem, 'is_deleted'):
            stmt = stmt.where(PriceListItem.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_price_for_service(
        self,
        service_name: str,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        include_deleted: bool = False
    ) -> Optional[PriceListItem]:
        """Get price for a specific service with vehicle-specific pricing."""
        filters = [
            PriceListItem.name == service_name,
            PriceListItem.is_active == True,
            PriceListItem.effective_date <= date.today()
        ]

        if not include_deleted and hasattr(PriceListItem, 'is_deleted'):
            filters.append(PriceListItem.is_deleted == False)

        filters.append(
            or_(
                PriceListItem.expiry_date.is_(None),
                PriceListItem.expiry_date >= date.today()
            )
        )

        if vehicle_brand:
            filters.append(
                or_(
                    PriceListItem.vehicle_brand == vehicle_brand,
                    PriceListItem.vehicle_brand.is_(None)
                )
            )

        if vehicle_model:
            filters.append(
                or_(
                    PriceListItem.vehicle_model == vehicle_model,
                    PriceListItem.vehicle_model.is_(None)
                )
            )

        stmt = select(PriceListItem).where(and_(*filters))
        # Prioritize specific vehicle match over generic
        stmt = stmt.order_by(
            PriceListItem.vehicle_brand.desc().nulls_last(),
            PriceListItem.vehicle_model.desc().nulls_last()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_categories(self, include_deleted: bool = False) -> List[str]:
        """Get all unique categories."""
        stmt = select(PriceListItem.category).distinct()
        if not include_deleted and hasattr(PriceListItem, 'is_deleted'):
            stmt = stmt.where(PriceListItem.is_deleted == False)
        stmt = stmt.order_by(PriceListItem.category)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_active_count(self) -> int:
        """Get count of active items."""
        today = date.today()
        stmt = select(func.count()).select_from(PriceListItem).where(
            PriceListItem.is_active == True,
            PriceListItem.is_deleted == False,
            PriceListItem.effective_date <= today,
            or_(
                PriceListItem.expiry_date.is_(None),
                PriceListItem.expiry_date >= today
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_by_category_with_counts(self) -> List[dict]:
        """Get categories with item counts."""
        stmt = (
            select(
                PriceListItem.category,
                func.count().label('count')
            )
            .where(
                PriceListItem.is_active == True,
                PriceListItem.is_deleted == False,
                PriceListItem.effective_date <= date.today()
            )
            .group_by(PriceListItem.category)
            .order_by(PriceListItem.category)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [{"category": row.category, "count": row.count} for row in rows]

    async def get_expired_items(self) -> List[PriceListItem]:
        """Get all expired items."""
        today = date.today()
        stmt = (
            select(PriceListItem)
            .where(
                PriceListItem.expiry_date.is_not(None),
                PriceListItem.expiry_date < today,
                PriceListItem.is_deleted == False
            )
            .order_by(PriceListItem.expiry_date)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_items_by_ids(self, ids: List[UUID]) -> List[PriceListItem]:
        """Get multiple items by IDs."""
        if not ids:
            return []
        stmt = (
            select(PriceListItem)
            .where(
                PriceListItem.id.in_(ids),
                PriceListItem.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================

    async def update(self, pk: Any, data: dict) -> Optional[PriceListItem]:
        """
        Update price list item with soft delete check.
        
        Args:
            pk: Primary key
            data: Data to update
        """
        item = await self.get(pk)
        if not item or item.is_deleted:
            return None

        for key, value in data.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)

        item.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def toggle_active(self, item_id: UUID) -> Optional[PriceListItem]:
        """Toggle active status."""
        item = await self.get(item_id)
        if not item:
            return None

        item.is_active = not item.is_active
        item.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def bulk_update_prices(
        self,
        category: str,
        percentage: float,
        vehicle_brand: Optional[str] = None
    ) -> int:
        """Bulk update prices by percentage for a category."""
        filters = [
            PriceListItem.category == category,
            PriceListItem.is_active == True,
            PriceListItem.is_deleted == False,
            PriceListItem.effective_date <= date.today()
        ]

        if vehicle_brand:
            filters.append(PriceListItem.vehicle_brand == vehicle_brand)

        stmt = select(PriceListItem).where(and_(*filters))
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        multiplier = Decimal(str(1 + (percentage / 100)))

        for item in items:
            old_price = item.price
            item.price = (item.price * multiplier).quantize(Decimal('0.01'))
            item.updated_at = datetime.now()

            # Add price history
            await self.add_price_history({
                "item_id": item.id,
                "old_price": old_price,
                "new_price": item.price,
                "changed_by": "system",
                "reason": f"Bulk update: {percentage}% change for category '{category}'"
            })

        await self.db.flush()
        return len(items)

    async def delete(self, pk: Any) -> bool:
        """
        Soft delete price list item.
        
        Args:
            pk: Primary key
        """
        item = await self.get(pk)
        if not item:
            return False

        # Check if item is used in any active project
        if item.project_usages:
            active_usages = [
                p for p in item.project_usages 
                if p.project and p.project.status not in ['completed', 'cancelled']
            ]
            if active_usages:
                raise ValueError(
                    f"Cannot delete item '{item.name}' because it is used in {len(active_usages)} active projects"
                )

        item.is_deleted = True
        item.deleted_at = datetime.now()
        item.is_active = False
        await self.db.flush()
        return True

    async def hard_delete(self, pk: Any) -> bool:
        """
        Hard delete price list item (permanent).
        Warning: This cannot be undone!
        
        Args:
            pk: Primary key
        """
        item = await self.get(pk, include_deleted=True)
        if not item:
            return False

        await self.db.delete(item)
        await self.db.flush()
        return True

    # =========================================================================
    # PRICE HISTORY OPERATIONS
    # =========================================================================

    async def get_price_history(self, item_id: UUID, limit: int = 50) -> List[PriceHistory]:
        """Get price history for an item."""
        stmt = (
            select(PriceHistory)
            .where(PriceHistory.item_id == item_id)
            .order_by(PriceHistory.changed_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_price_history_entry(self, history_id: UUID) -> Optional[PriceHistory]:
        """Get price history entry by ID."""
        stmt = select(PriceHistory).where(PriceHistory.id == history_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_price_history(self, data: dict) -> PriceHistory:
        """Add price history entry."""
        history = PriceHistory(**data)
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history

    async def get_price_change_summary(self, item_id: UUID) -> dict:
        """Get price change summary for an item."""
        history = await self.get_price_history(item_id, 100)

        if not history:
            return {
                "total_changes": 0,
                "first_price": None,
                "last_price": None,
                "current_price": None,
                "average_change": Decimal(0),
                "max_increase": Decimal(0),
                "max_decrease": Decimal(0),
                "total_increase": Decimal(0),
                "total_decrease": Decimal(0)
            }

        changes = []
        increases = []
        decreases = []

        for h in history:
            diff = h.new_price - h.old_price
            changes.append(diff)
            if diff > 0:
                increases.append(diff)
            elif diff < 0:
                decreases.append(diff)

        return {
            "total_changes": len(history),
            "first_price": history[-1].old_price if history else None,
            "last_price": history[0].new_price if history else None,
            "current_price": history[0].new_price if history else None,
            "average_change": sum(changes) / len(changes) if changes else Decimal(0),
            "max_increase": max(increases) if increases else Decimal(0),
            "max_decrease": min(decreases) if decreases else Decimal(0),
            "total_increase": sum(increases) if increases else Decimal(0),
            "total_decrease": sum(decreases) if decreases else Decimal(0)
        }

    # =========================================================================
    # CUSTOM PRICE OPERATIONS
    # =========================================================================

    async def get_custom_price(
        self,
        item_id: UUID,
        customer_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None
    ) -> Optional[CustomPrice]:
        """Get custom price for customer/project."""
        today = date.today()
        filters = [
            CustomPrice.item_id == item_id,
            CustomPrice.valid_from <= today,
            or_(
                CustomPrice.valid_until.is_(None),
                CustomPrice.valid_until >= today
            )
        ]

        if customer_id:
            filters.append(CustomPrice.customer_id == customer_id)
        if project_id:
            filters.append(CustomPrice.project_id == project_id)

        stmt = select(CustomPrice).where(and_(*filters))
        # Get most recent custom price
        stmt = stmt.order_by(CustomPrice.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_custom_prices(self, item_id: UUID) -> List[CustomPrice]:
        """Get all custom prices for an item."""
        stmt = (
            select(CustomPrice)
            .where(CustomPrice.item_id == item_id)
            .order_by(CustomPrice.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_custom_price(self, data: dict) -> CustomPrice:
        """Create custom price."""
        custom_price = CustomPrice(**data)
        self.db.add(custom_price)
        await self.db.flush()
        await self.db.refresh(custom_price)
        return custom_price

    async def update_custom_price(
        self,
        custom_price_id: UUID,
        data: dict
    ) -> Optional[CustomPrice]:
        """Update custom price."""
        stmt = select(CustomPrice).where(CustomPrice.id == custom_price_id)
        result = await self.db.execute(stmt)
        custom_price = result.scalar_one_or_none()

        if not custom_price:
            return None

        for key, value in data.items():
            if hasattr(custom_price, key) and value is not None:
                setattr(custom_price, key, value)

        await self.db.flush()
        await self.db.refresh(custom_price)
        return custom_price

    async def delete_custom_price(self, custom_price_id: UUID) -> bool:
        """Delete custom price."""
        stmt = select(CustomPrice).where(CustomPrice.id == custom_price_id)
        result = await self.db.execute(stmt)
        custom_price = result.scalar_one_or_none()

        if not custom_price:
            return False

        await self.db.delete(custom_price)
        await self.db.flush()
        return True

    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================

    async def bulk_create(self, items: List[dict]) -> List[PriceListItem]:
        """Bulk create price list items."""
        created_items = []

        for item_data in items:
            # Set default effective date if not provided
            if 'effective_date' not in item_data:
                item_data['effective_date'] = date.today()

            # Validate SKU uniqueness
            if item_data.get('sku'):
                existing = await self.get_by_sku(item_data['sku'])
                if existing:
                    raise ValueError(f"SKU '{item_data['sku']}' already exists")

            item = PriceListItem(**item_data)
            self.db.add(item)
            created_items.append(item)

        await self.db.flush()

        for item in created_items:
            await self.db.refresh(item)

        return created_items

 


# =============================================================================
# Price List Category Repository
# =============================================================================

class PriceListCategoryRepository(BaseRepository[PriceListCategory]):
    """Repository untuk Price List Category."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=PriceListCategory)

    async def get_by_name(self, name: str) -> Optional[PriceListCategory]:
        """Get category by name."""
        stmt = select(PriceListCategory).where(PriceListCategory.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> List[PriceListCategory]:
        """List all active categories."""
        stmt = (
            select(PriceListCategory)
            .where(PriceListCategory.is_active == True)
            .order_by(PriceListCategory.sort_order)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_with_counts(self) -> List[dict]:
        """List categories with item counts."""
        stmt = (
            select(
                PriceListCategory.name,
                PriceListCategory.display_name,
                PriceListCategory.sort_order,
                func.count(PriceListItem.id).label('item_count')
            )
            .join(PriceListItem, PriceListItem.category == PriceListCategory.name)
            .where(
                PriceListCategory.is_active == True,
                PriceListItem.is_active == True,
                PriceListItem.is_deleted == False
            )
            .group_by(PriceListCategory.name, PriceListCategory.display_name, PriceListCategory.sort_order)
            .order_by(PriceListCategory.sort_order)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "name": row.name,
                "display_name": row.display_name,
                "sort_order": row.sort_order,
                "item_count": row.item_count
            }
            for row in rows
        ]


# =============================================================================
# Price List Discount Repository
# =============================================================================

class PriceListDiscountRepository(BaseRepository[PriceListDiscount]):
    """Repository untuk Price List Discount."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=PriceListDiscount)

    async def get_by_code(self, code: str) -> Optional[PriceListDiscount]:
        """Get discount by code (validates active and date range)."""
        today = date.today()
        stmt = (
            select(PriceListDiscount)
            .where(
                and_(
                    PriceListDiscount.code == code,
                    PriceListDiscount.is_active == True,
                    PriceListDiscount.valid_from <= today,
                    or_(
                        PriceListDiscount.valid_until.is_(None),
                        PriceListDiscount.valid_until >= today
                    )
                )
            )
            .options(selectinload(PriceListDiscount.item))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> List[PriceListDiscount]:
        """List all active discounts."""
        today = date.today()
        stmt = (
            select(PriceListDiscount)
            .where(
                and_(
                    PriceListDiscount.is_active == True,
                    PriceListDiscount.valid_from <= today,
                    or_(
                        PriceListDiscount.valid_until.is_(None),
                        PriceListDiscount.valid_until >= today
                    )
                )
            )
            .order_by(PriceListDiscount.valid_until)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def validate_discount(self, code: str) -> bool:
        """Validate if a discount code is valid."""
        discount = await self.get_by_code(code)
        if not discount:
            return False
        if discount.max_uses and discount.used_count >= discount.max_uses:
            return False
        return True

    async def use_discount(self, code: str) -> bool:
        """Mark a discount as used (increment used_count)."""
        discount = await self.get_by_code(code)
        if not discount:
            return False

        if not await self.validate_discount(code):
            return False

        discount.used_count += 1
        await self.db.flush()
        return True

    async def get_applicable_discounts(
        self,
        category: Optional[str] = None,
        item_id: Optional[UUID] = None
    ) -> List[PriceListDiscount]:
        """Get discounts applicable to a specific item or category."""
        today = date.today()

        filters = [
            PriceListDiscount.is_active == True,
            PriceListDiscount.valid_from <= today,
            or_(
                PriceListDiscount.valid_until.is_(None),
                PriceListDiscount.valid_until >= today
            )
        ]

        if category:
            filters.append(
                or_(
                    PriceListDiscount.applies_to_category == category,
                    PriceListDiscount.applies_to_all == True,
                    PriceListDiscount.applies_to_category.is_(None)
                )
            )

        if item_id:
            filters.append(
                or_(
                    PriceListDiscount.applies_to_item_id == item_id,
                    PriceListDiscount.applies_to_all == True,
                    PriceListDiscount.applies_to_item_id.is_(None)
                )
            )

        stmt = select(PriceListDiscount).where(and_(*filters))
        result = await self.db.execute(stmt)
        return result.scalars().all()