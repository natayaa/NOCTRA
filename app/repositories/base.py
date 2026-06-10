from typing_extensions import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model
        
    async def create_(self, instance: ModelType) -> ModelType:
        self.db.add(instance=instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance
    
    async def get_by_id(self, pk: Any) -> ModelType | None:
        return await self.db.get(self.model, pk)
    
    async def all(self) -> list[ModelType]:
        result = await self.db.execute(select(self.model))
        return list(result.scalars().all())