# modules/price_list/repository.py
from uuid import UUID
from typing import Any, Optional, List, Tuple
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from core.base import BaseRepository
from .models import PriceListItem, PriceListCategory, PriceListDiscount, PriceHistory, CustomPrice


class PriceListRepository(BaseRepository[PriceListItem]):
    """Repository untuk Price List Item."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=PriceListItem)

    # ==================== READ ====================

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
        """List price items with pagination and filters."""
        stmt = select(PriceListItem)
        count_stmt = select(func.count()).select_from(PriceListItem)

        filters = []
        if active_only:
            filters.append(PriceListItem.is_active == True)
        if category:
            filters.append(PriceListItem.category == category)
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
        if search:
            filters.append(
                or_(
                    PriceListItem.name.ilike(f"%{search}%"),
                    PriceListItem.description.ilike(f"%{search}%"),
                    PriceListItem.sku.ilike(f"%{search}%"),
                )
            )

        # Validity filters
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

        stmt = stmt.order_by(
            PriceListItem.category,
            PriceListItem.vehicle_brand.desc().nulls_last(),
            PriceListItem.name
        )
        stmt = stmt.offset((page - 1) * limit).limit(limit)

        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        return items, total

    async def get_by_category(
        self,
        category: str,
        active_only: bool = True,
        vehicle_brand: Optional[str] = None
    ) -> List[PriceListItem]:
        """Get price items by category."""
        filters = [PriceListItem.category == category]

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
        category: Optional[str] = None
    ) -> List[PriceListItem]:
        """Get price items by vehicle brand and model."""
        filters = [
            PriceListItem.vehicle_brand == brand,
            PriceListItem.is_active == True,
            PriceListItem.effective_date <= date.today()
        ]

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
            PriceListItem.vehicle_model.desc().nulls_last()
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_sku(self, sku: str) -> Optional[PriceListItem]:
        """Get price item by SKU."""
        stmt = select(PriceListItem).where(PriceListItem.sku == sku)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_price_for_service(
        self,
        service_name: str,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None
    ) -> Optional[PriceListItem]:
        """Get price for a specific service with vehicle-specific pricing."""
        filters = [
            PriceListItem.name == service_name,
            PriceListItem.is_active == True,
            PriceListItem.effective_date <= date.today()
        ]

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
        stmt = stmt.order_by(
            PriceListItem.vehicle_brand.desc().nulls_last(),
            PriceListItem.vehicle_model.desc().nulls_last()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        stmt = select(PriceListItem.category).distinct().order_by(
            PriceListItem.category)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_active_count(self) -> int:
        """Get count of active items."""
        stmt = select(func.count()).select_from(PriceListItem).where(
            PriceListItem.is_active == True,
            PriceListItem.effective_date <= date.today(),
            or_(
                PriceListItem.expiry_date.is_(None),
                PriceListItem.expiry_date >= date.today()
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_with_price_history(self, item_id: UUID) -> Optional[PriceListItem]:
        """Get item with price history."""
        stmt = (
            select(PriceListItem)
            .where(PriceListItem.id == item_id)
            .options(
                selectinload(PriceListItem.price_history),
                selectinload(PriceListItem.custom_prices)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== UPDATE ====================

    async def toggle_active(self, item_id: UUID) -> Optional[PriceListItem]:
        """Toggle active status."""
        item = await self.get(item_id)
        if not item:
            return None

        item.is_active = not item.is_active
        await self.db.flush()
        await self.db.refresh(item)
        return item

    # ==================== PRICE HISTORY ====================

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
                "max_decrease": Decimal(0)
            }

        changes = []
        for h in history:
            diff = h.new_price - h.old_price
            changes.append(diff)

        return {
            "total_changes": len(history),
            "first_price": history[-1].old_price if history else None,
            "last_price": history[0].new_price if history else None,
            "current_price": history[0].new_price if history else None,
            "average_change": sum(changes) / len(changes) if changes else Decimal(0),
            "max_increase": max(changes) if changes else Decimal(0),
            "max_decrease": min(changes) if changes else Decimal(0)
        }

    # Tambahkan method get untuk PriceHistory
    async def get_price_history_entry(self, history_id: UUID) -> Optional[PriceHistory]:
        """Get price history entry by ID."""
        stmt = select(PriceHistory).where(PriceHistory.id == history_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # Override get untuk menangani history
    async def get(self, pk: Any) -> Optional[PriceListItem]:
        """Get by primary key."""
        if isinstance(pk, UUID):
            return await self.db.get(self.model, pk)
        return await super().get(pk)

    # Method untuk mendapatkan history
    async def get_history(self, history_id: UUID) -> Optional[PriceHistory]:
        """Get price history entry by ID."""
        stmt = select(PriceHistory).where(PriceHistory.id == history_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== CUSTOM PRICE ====================

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

    # ==================== BULK ====================

    async def bulk_create(self, items: List[dict]) -> List[PriceListItem]:
        """Bulk create price list items."""
        created_items = []
        for item_data in items:
            item = PriceListItem(**item_data)
            self.db.add(item)
            created_items.append(item)

        await self.db.flush()

        for item in created_items:
            await self.db.refresh(item)

        return created_items

    async def bulk_update_prices(
        self,
        category: str,
        percentage: float,
        vehicle_brand: Optional[str] = None
    ) -> int:
        """Bulk update prices by percentage for a category."""
        stmt = select(PriceListItem).where(
            PriceListItem.category == category,
            PriceListItem.is_active == True
        )
        if vehicle_brand:
            stmt = stmt.where(PriceListItem.vehicle_brand == vehicle_brand)

        result = await self.db.execute(stmt)
        items = result.scalars().all()

        for item in items:
            item.price += item.price * \
                (Decimal(str(percentage)) / Decimal(100))

        await self.db.flush()
        return len(items)


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
                PriceListItem.is_active == True
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
