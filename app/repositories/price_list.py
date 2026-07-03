# repositories/price_list.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from uuid import UUID
from datetime import date
from typing import Optional, List, Tuple

from models.price_list import PriceListItem, PriceListCategory, PriceListDiscount
from schemas.price_list import PriceListItemCreate, PriceListItemUpdate


class PriceListRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: PriceListItemCreate) -> PriceListItem:
        item = PriceListItem(**data.model_dump())
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get(self, item_id: UUID) -> PriceListItem | None:
        return await self.db.get(PriceListItem, item_id)

    async def get_active(self, item_id: UUID) -> PriceListItem | None:
        stmt = select(PriceListItem).where(
            and_(
                PriceListItem.id == item_id,
                PriceListItem.is_active == True
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

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

    async def get_by_category(self, category: str, active_only: bool = True) -> List[PriceListItem]:
        stmt = select(PriceListItem).where(PriceListItem.category == category)
        if active_only:
            stmt = stmt.where(PriceListItem.is_active == True)
        stmt = stmt.order_by(PriceListItem.name)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_by_vehicle(
        self,
        brand: str,
        model: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[PriceListItem]:
        filters = [
            PriceListItem.vehicle_brand == brand,
            PriceListItem.is_active == True
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

        stmt = select(PriceListItem).where(and_(*filters))
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def update(self, item_id: UUID, data: PriceListItemUpdate) -> PriceListItem | None:
        item = await self.get(item_id)
        if not item:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def delete(self, item_id: UUID) -> bool:
        item = await self.get(item_id)
        if not item:
            return False
        item.is_active = False
        await self.db.flush()
        return True

    async def hard_delete(self, item_id: UUID) -> bool:
        item = await self.get(item_id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.flush()
        return True

    async def get_categories(self) -> List[str]:
        stmt = select(PriceListItem.category).distinct()
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_price_for_service(
        self,
        service_name: str,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None
    ) -> Optional[PriceListItem]:
        filters = [
            PriceListItem.name == service_name,
            PriceListItem.is_active == True,
            PriceListItem.effective_date <= date.today()
        ]
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
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()


class PriceListCategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> PriceListCategory:
        category = PriceListCategory(**data)
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def get(self, category_id: UUID) -> PriceListCategory | None:
        return await self.db.get(PriceListCategory, category_id)

    async def get_by_name(self, name: str) -> PriceListCategory | None:
        stmt = select(PriceListCategory).where(PriceListCategory.name == name)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_active(self) -> List[PriceListCategory]:
        stmt = select(PriceListCategory).where(PriceListCategory.is_active == True)
        stmt = stmt.order_by(PriceListCategory.sort_order)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def update(self, category_id: UUID, data: dict) -> PriceListCategory | None:
        category = await self.get(category_id)
        if not category:
            return None
        for key, value in data.items():
            if hasattr(category, key):
                setattr(category, key, value)
        await self.db.flush()
        await self.db.refresh(category)
        return category


class PriceListDiscountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> PriceListDiscount:
        discount = PriceListDiscount(**data)
        self.db.add(discount)
        await self.db.flush()
        await self.db.refresh(discount)
        return discount

    async def get(self, discount_id: UUID) -> PriceListDiscount | None:
        return await self.db.get(PriceListDiscount, discount_id)

    async def get_by_code(self, code: str) -> PriceListDiscount | None:
        stmt = select(PriceListDiscount).where(
            and_(
                PriceListDiscount.code == code,
                PriceListDiscount.is_active == True,
                PriceListDiscount.valid_from <= date.today(),
                or_(
                    PriceListDiscount.valid_until.is_(None),
                    PriceListDiscount.valid_until >= date.today()
                )
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_active(self) -> List[PriceListDiscount]:
        stmt = select(PriceListDiscount).where(
            and_(
                PriceListDiscount.is_active == True,
                PriceListDiscount.valid_from <= date.today(),
                or_(
                    PriceListDiscount.valid_until.is_(None),
                    PriceListDiscount.valid_until >= date.today()
                )
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def validate_discount(self, code: str) -> bool:
        discount = await self.get_by_code(code)
        if not discount:
            return False
        if discount.max_uses and discount.used_count >= discount.max_uses:
            return False
        return True

    async def use_discount(self, code: str) -> bool:
        discount = await self.get_by_code(code)
        if not discount:
            return False
        discount.used_count += 1
        await self.db.flush()
        return True