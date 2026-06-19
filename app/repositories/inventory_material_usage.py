from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, UUID
from sqlalchemy.orm import selectinload
from models.inventory_material_usage import JobMaterialUsage
from models.inventory_items import InventoryItems

class MaterialUsageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_project(self, project_id: str) -> list[JobMaterialUsage]:
        stmt = (
            select(JobMaterialUsage)
            .where(JobMaterialUsage.project_id == project_id)
            .options(selectinload(JobMaterialUsage.item))
            .order_by(JobMaterialUsage.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, usage: JobMaterialUsage) -> JobMaterialUsage:
        self.db.add(usage)
        await self.db.flush()
        return usage 
    
    async def get_by_id(self, usage_id: UUID) -> JobMaterialUsage | None:
        stmt = select(JobMaterialUsage).where(JobMaterialUsage.id == usage_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, usage_id: UUID) -> bool:
        stmt = delete(JobMaterialUsage).where(JobMaterialUsage.id == usage_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0