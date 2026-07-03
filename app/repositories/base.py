# repositories/base.py
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: type[ModelType],):
        self.db = db
        self.model = model

    # ==========================================
    # CREATE
    # ==========================================

    async def create(self, instance: ModelType,) -> ModelType:
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)

        return instance

    async def bulk_create(self, instances: list[ModelType],) -> list[ModelType]:
        self.db.add_all(instances)
        await self.db.flush()
        return instances

    # ==========================================
    # READ
    # ==========================================

    async def get(self, pk: Any,) -> ModelType | None:
        return await self.db.get(self.model, pk,)

    async def all(self,) -> list[ModelType]:
        result = await self.db.execute(
            select(self.model)
        )

        return list(result.scalars().all())

    async def count(self,) -> int:

        result = await self.db.execute(
            select(func.count())
            .select_from(self.model)
        )

        return result.scalar_one()

    async def find_one_by(self, **filters,) -> ModelType | None:
        stmt = select(self.model)

        for field, value in filters.items():
            stmt = stmt.where(
                getattr(self.model, field) == value
            )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def find_many_by(self, **filters,) -> list[ModelType]:
        stmt = select(self.model)

        for field, value in filters.items():
            stmt = stmt.where(
                getattr(self.model, field) == value
            )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def paginate(self, page: int = 1, page_size: int = 20,) -> list[ModelType]:

        stmt = (
            select(self.model)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(stmt)

        return list(
            result.scalars().all()
        )

    # ==========================================
    # UPDATE
    # ==========================================

    async def update(self, pk: Any, data: dict[str, Any],) -> ModelType | None:
        obj = await self.get(pk)
        if obj is None:
            return None

        model_fields = {
            column.name
            for column in self.model.__table__.columns
        }

        for key, value in data.items():
            if key in model_fields:
                setattr(obj, key, value)

        await self.db.flush()
        await self.db.refresh(obj)

        return obj

    async def patch(self, pk: Any, data: dict[str, Any],) -> ModelType | None:
        obj = await self.get(pk)
        if obj is None:
            return None

        model_fields = {
            column.name
            for column in self.model.__table__.columns
        }

        for key, value in data.items():
            if (
                key in model_fields
                and value is not None
            ):
                setattr(obj, key, value)

        await self.db.flush()
        await self.db.refresh(obj)

        return obj

    # ==========================================
    # DELETE
    # ==========================================

    async def delete(self, pk: Any,) -> bool:
        obj = await self.get(pk)
        if obj is None:
            return False

        await self.db.delete(obj)
        await self.db.flush()

        return True