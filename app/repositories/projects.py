from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from models.projects import Project


class ProjectRepository:

    async def create(self, db: AsyncSession, obj: Project) -> Project:
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def get(self, db: AsyncSession, project_id: str) -> Project | None:
        result = await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.tasks))  # penting untuk kanban
        )
        return result.scalar_one_or_none()

    async def list(self, db: AsyncSession) -> list[Project]:
        result = await db.execute(
            select(Project)
            .order_by(Project.created_at.desc())
        )
        return result.scalars().all()

    async def update_status(
        self,
        db: AsyncSession,
        project_id: str,
        status: str
    ) -> Project | None:

        await db.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(status=status)
            .execution_options(synchronize_session="fetch")
        )

        await db.flush()

        # return updated object biar aman untuk API response
        return await self.get(db, project_id)

    async def delete(self, db: AsyncSession, project_id: str) -> bool:
        result = await db.execute(
            delete(Project).where(Project.id == project_id)
        )

        await db.flush()

        return result.rowcount > 0