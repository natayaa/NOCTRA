# app/repositories/inventory/workshop_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.inventory_workshop_jobs import WorkshopJob


class WorkshopJobRepository:
    async def get(self, db: AsyncSession, job_id: str):
        result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, obj: WorkshopJob):
        db.add(obj)
        await db.flush()
        return obj